import json
import ast
import os
import json
import math
import torch
import random
from typing import Any, Dict, List, Tuple
import app.commons.constants as const
import itertools


def check_threshold(entropy: float, varentropy: float, thd: Dict) -> bool:
    """
    Check if the given entropy or variance of entropy exceeds the specified thresholds.

    Args:
        entropy (float): The entropy value to check.
        varentropy (float): The variance of entropy value to check.
        thd (dict): A dictionary containing the threshold values with keys 'entropy' and 'varentropy'.

    Returns:
        bool: True if either the entropy or varentropy exceeds their respective thresholds, False otherwise.
    """
    return entropy > thd["entropy"] or varentropy > thd["varentropy"]


def calculate_entropy(log_probs: List[float]) -> Tuple[float, float]:
    """
    Calculate the entropy and variance of entropy (varentropy) from log probabilities.

    Args:
        log_probs (list of float): A list of log probabilities.

    Returns:
        tuple: A tuple containing:
            - log_probs (list of float): The input log probabilities as a list.
            - entropy (float): The calculated entropy.
            - varentropy (float): The calculated variance of entropy.
    """
    log_probs = torch.tensor(log_probs)
    token_probs = torch.exp(log_probs)
    entropy = -torch.sum(log_probs * token_probs, dim=-1) / math.log(2, math.e)
    varentropy = torch.sum(
        token_probs * (log_probs / math.log(2, math.e)) + entropy.unsqueeze(-1) ** 2,
        dim=-1,
    )
    return entropy.item(), varentropy.item()


def is_parameter_property(
    function_description: Dict, parameter_name: str, property_name: str
) -> bool:
    """
    Check if a parameter in an API description has a specific property.

    Args:
        function_description (dict): The API description in JSON format.
        parameter_name (str): The name of the parameter to check.
        property_name (str): The property to look for (e.g., 'format', 'default').

    Returns:
        bool: True if the parameter has the specified property, False otherwise.
    """
    parameters = function_description.get("properties", {})
    parameter_info = parameters.get(parameter_name, {})

    return property_name in parameter_info


class HallucinationStateHandler:
    """
    A class to handle the state of hallucination detection in token processing.

    Attributes:
        tokens (list): List of tokens processed.
        logprobs (list): List of log probabilities for each token.
        state (str): Current state of the handler.
        mask (list): List of masks indicating the type of each token.
        parameter_name_done (bool): Flag indicating if parameter name extraction is done.
        hallucination (bool): Flag indicating if a hallucination is detected.
        hallucination_message (str): Message describing the hallucination.
        parameter_name (list): List of extracted parameter names.
        function_description (dict): Description of functions and their parameters.
        token_probs_map (list): List mapping tokens to their entropy and variance of entropy.
        current_token (str): The current token being processed.
    """

    def __init__(self, response_iterator=None, function=None):
        """
        Initializes the HallucinationStateHandler with default values.
        """
        self.tokens = []
        self.logprobs = []
        self.state = None
        self.mask = []
        self.parameter_name_done = False
        self.hallucination = False
        self.hallucination_message = ""
        self.parameter_name = []

        self.token_probs_map = []
        self.current_token = None
        self.response_iterator = response_iterator
        self.process_function(function)

    def process_function(self, function):
        self.function = function
        if self.function is None:
            raise ValueError("API descriptions not set.")
        parameter_names = {}
        for func in self.function:
            func_name = func["name"]
            parameters = func["parameters"]["properties"]
            parameter_names[func_name] = list(parameters.keys())
        self.function_description = parameter_names
        self.function_properties = {x["name"]: x["parameters"] for x in self.function}

    def check_token_hallucination(self, token, logprob):
        """
        Check if the given token is hallucinated based on the log probability.

        Args:
            token (str): The token to check.
            logprob (float): The log probability of the token.

        Returns:
            bool: True if the token is hallucinated, False otherwise.
        """
        self.current_token = token
        self.tokens.append(token)
        self.logprobs.append(logprob)
        self.process_token()
        return self.hallucination

    def __iter__(self):
        return self

    def __next__(self):
        if self.response_iterator is not None:
            try:
                r = next(self.response_iterator)
                if hasattr(r.choices[0].delta, "content"):
                    token_content = r.choices[0].delta.content
                    if token_content:
                        logprobs = [
                            p.logprob
                            for p in r.choices[0].logprobs.content[0].top_logprobs
                        ]
                        self.check_token_hallucination(token_content, logprobs)
                        return token_content
            except StopIteration:
                raise StopIteration

    def process_token(self):
        """
        Processes the current token and updates the state and mask accordingly.
        Detects hallucinations based on the token type and log probabilities.
        """
        content = "".join(self.tokens).replace(" ", "")
        if self.current_token == "<tool_call>":
            self.mask.append("t")
            self.check_logprob()

        # Function name extraction logic
        # If the state is function name and the token is not an end token, add to the mask
        if self.state == "function_name":
            if self.current_token not in const.FUNC_NAME_END_TOKEN:
                self.mask.append("f")
            else:
                self.state = None
                self.is_function_name_hallucinated()

        # Check if the token is a function name start token, change the state
        if content.endswith(const.FUNC_NAME_START_PATTERN):
            print("function name entered")
            self.state = "function_name"

        # Parameter name extraction logic
        # if the state is parameter name and the token is not an end token, add to the mask
        if self.state == "parameter_name" and not content.endswith(
            const.PARAMETER_NAME_END_TOKENS
        ):
            self.mask.append("p")
        # if the state is parameter name and the token is an end token, change the state, check hallucination and set the flag parameter name done
        # The need for parameter name done is to allow the check of parameter value pattern
        elif self.state == "parameter_name" and content.endswith(
            const.PARAMETER_NAME_END_TOKENS
        ):
            self.state = None
            self.is_parameter_name_hallucinated()
            self.parameter_name_done = True
        # if the parameter name is done and the token is a parameter name start token, change the state
        elif self.parameter_name_done and content.endswith(
            const.PARAMETER_NAME_START_PATTERN
        ):
            self.state = "parameter_name"

        # if token is a first parameter value start token, change the state
        if content.endswith(const.FIRST_PARAM_NAME_START_PATTERN):
            self.state = "parameter_name"

        # Parameter value extraction logic
        # if the state is parameter value and the token is not an end token, add to the mask
        if self.state == "parameter_value" and not content.endswith(
            const.PARAMETER_VALUE_END_TOKEN
        ):
            # checking if the token is a value token and is not empty
            if self.current_token.strip() not in ['"', ""]:
                self.mask.append("v")
                # checking if the parameter doesn't have default and the token is the first parameter value token
                if (
                    len(self.mask) > 1
                    and self.mask[-2] != "v"
                    and not is_parameter_property(
                        self.function_properties[self.function_name],
                        self.parameter_name[-1],
                        "default",
                    )
                ):
                    self.check_logprob()
            else:
                self.mask.append("e")
        # if the state is parameter value and the token is an end token, change the state
        elif self.state == "parameter_value" and content.endswith(
            const.PARAMETER_VALUE_END_TOKEN
        ):
            self.state = None
        # if the parameter name is done and the token is a parameter value start token, change the state
        elif self.parameter_name_done and content.endswith(
            const.PARAMETER_VALUE_START_PATTERN
        ):
            self.state = "parameter_value"

        # Maintain consistency between stack and mask
        # If the mask length is less than tokens, add an not used (e) token to the mask
        if len(self.mask) != len(self.tokens):
            self.mask.append("e")

    def check_logprob(self):
        """
        Checks the log probability of the current token and updates the token probability map.
        Detects hallucinations based on entropy and variance of entropy.
        """
        probs = self.logprobs[-1]
        entropy, varentropy = calculate_entropy(probs)
        self.token_probs_map.append((self.tokens[-1], entropy, varentropy))

        if check_threshold(
            entropy, varentropy, const.HALLUCINATION_THRESHOLD_DICT[self.mask[-1]]
        ):
            self.hallucination = True
            self.hallucination_message = f"Token '{self.current_token}' is uncertain."

    def count_consecutive_token(self, token="v") -> int:
        """
        Counts the number of consecutive occurrences of a given token in the mask.

        Args:
            token (str): The token to count in the mask.

        Returns:
            int: The number of consecutive occurrences of the token.
        """
        return (
            len(list(itertools.takewhile(lambda x: x == token, reversed(self.mask))))
            if self.mask and self.mask[-1] == token
            else 0
        )

    def is_function_name_hallucinated(self):
        """
        Checks the extracted function name against the function descriptions.
        Detects hallucinations if the function name is not found.
        """
        f_len = self.count_consecutive_token("f")
        self.function_name = "".join(self.tokens[:-1][-f_len:])
        if self.function_name not in self.function_description.keys():
            self.hallucination = True
            self.hallucination_message = f"Function name '{self.function_name}' not found in given function descriptions."

    def is_parameter_name_hallucinated(self):
        """
        Checks the extracted parameter name against the function descriptions.
        Detects hallucinations if the parameter name is not found.
        """
        p_len = self.count_consecutive_token("p")
        parameter_name = "".join(self.tokens[:-1][-p_len:])
        self.parameter_name.append(parameter_name)
        if parameter_name not in self.function_description[self.function_name]:
            self.hallucination = True
            self.hallucination_message = f"Parameter name '{parameter_name}' not found in given function descriptions."
