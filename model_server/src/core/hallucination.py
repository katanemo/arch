import json
import math
import torch
import itertools


from typing import Dict, List, Tuple
from enum import Enum
import string

from src.commons.utils import get_model_server_logger

logger = get_model_server_logger()

# constants
FUNC_NAME_START_PATTERN = ('<tool_call>\n{"name":"', "<tool_call>\n{'name':'")
FUNC_NAME_END_TOKEN = ('",', "',")
TOOL_CALL_TOKEN = "<tool_call>"

FIRST_PARAM_NAME_START_PATTERN = ('"arguments":{"', "'arguments':{'")
PARAMETER_NAME_END_TOKENS = ('":', ':"', "':", ":'")
PARAMETER_NAME_START_PATTERN = (',"', ",'")
PARAMETER_VALUE_START_PATTERN = ('":', "':")
PARAMETER_VALUE_END_TOKEN = ('",', "}}\n", "',")

BRACKETS = {"(": ")", "{": "}", "[": "]"}


# Thresholds
class MaskToken(Enum):
    FUNCTION_NAME = "f"
    PARAMETER_VALUE = "v"
    PARAMETER_NAME = "p"
    NOT_USED = "e"
    TOOL_CALL = "t"


HALLUCINATION_THRESHOLD_DICT = {
    MaskToken.TOOL_CALL.value: {
        "entropy": 0.35,
        "varentropy": 1.7,
        "probability": 0.8,
    },
    MaskToken.PARAMETER_VALUE.value: {
        "entropy": 0.28,
        "varentropy": 1.2,
        "probability": 0.8,
    },
}


def check_threshold(
    entropy: float, varentropy: float, probability: float, thd: Dict
) -> bool:
    """
    Check if the given entropy or variance of entropy exceeds the specified thresholds.

    Args:
        entropy (float): The entropy value to check.
        varentropy (float): The variance of entropy value to check.
        thd (dict): A dictionary containing the threshold values with keys 'entropy' and 'varentropy'.

    Returns:
        bool: True if either the entropy or varentropy exceeds their respective thresholds, False otherwise.
    """
    if probability > thd["probability"]:
        return entropy > thd["entropy"] and varentropy > thd["varentropy"]
    else:
        return True


def calculate_uncertainty(log_probs: List[float]) -> Tuple[float, float]:
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
    return entropy.item(), varentropy.item(), token_probs[0].item()


def is_parameter_required(
    function_description: Dict,
    parameter_name: str,
) -> bool:
    """
    Check if a parameter in required list

    Args:
        function_description (dict): The API description in JSON format.
        parameter_name (str): The name of the parameter to check.

    Returns:
        bool: True if the parameter has the specified property, False otherwise.
    """
    required_parameters = function_description.get("required", {})

    return parameter_name in required_parameters


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
        token_probs_map (list): List mapping tokens to their entropy and variance of entropy.
    """

    def __init__(self, response_iterator=None, function=None):
        """
        Initializes the HallucinationStateHandler with default values.
        """
        self.tokens: List[str] = []
        self.logprobs: List[float] = []
        self.state: str = None
        self.mask: List[str] = []
        self.parameter_name_done: bool = False
        self.hallucination: bool = False
        self.error_message: str = ""
        self.error_type: str = ""
        self.parameter_name: List[str] = []
        self.token_probs_map: List[Tuple[str, float, float]] = []
        self.response_iterator = response_iterator
        self._process_function(function)
        self.open_bracket = False
        self.bracket = None
        self.check_parameter_name = {}
        self.HALLUCINATION_THRESHOLD_DICT = HALLUCINATION_THRESHOLD_DICT

    def _process_function(self, function):
        self.function = function
        if self.function is None:
            raise ValueError("API descriptions not set.")
        self.function_properties = {
            x["function"]["name"]: x["function"]["parameters"] for x in self.function
        }

    def append_and_check_token_hallucination(self, token, logprob):
        """
        Check if the given token is hallucinated based on the log probability.

        Args:
            token (str): The token to check.
            logprob (float): The log probability of the token.

        Returns:
            bool: True if the token is hallucinated, False otherwise.
        """
        self.tokens.append(token)
        self.logprobs.append(logprob)
        self._process_token()
        return self.hallucination

    def __iter__(self):
        return self

    def __next__(self):
        if self.response_iterator is not None:
            try:
                r = next(self.response_iterator)
                logger.info("prefill stream response: %s", json.dumps(r.dict()))
                if hasattr(r.choices[0].delta, "content"):
                    token_content = r.choices[0].delta.content
                    if token_content:
                        try:
                            logprobs = [
                                p.logprob
                                for p in r.choices[0].logprobs.content[0].top_logprobs
                            ]
                        except Exception as e:
                            raise ValueError(
                                f"Error extracting logprobs from response: {e}"
                            )
                        self.append_and_check_token_hallucination(
                            token_content, logprobs
                        )
                        return token_content
            except StopIteration:
                raise StopIteration

    def _process_token(self):
        """
        Processes the current token and updates the state and mask accordingly.
        Detects hallucinations based on the token type and log probabilities.
        """
        content = "".join(self.tokens).replace(" ", "")
        if self.tokens[-1] == TOOL_CALL_TOKEN:
            self.mask.append(MaskToken.TOOL_CALL)
            self._check_logprob()

        # Function name extraction logic
        # If the state is function name and the token is not an end token, add to the mask
        if self.state == "function_name":
            if self.tokens[-1] not in FUNC_NAME_END_TOKEN:
                self.mask.append(MaskToken.FUNCTION_NAME)
            else:
                self.state = None
                self._get_function_name()

        # Check if the token is a function name start token, change the state
        if content.endswith(FUNC_NAME_START_PATTERN):
            self.state = "function_name"

        # Parameter name extraction logic
        # if the state is parameter name and the token is not an end token, add to the mask
        if self.state == "parameter_name" and not content.endswith(
            PARAMETER_NAME_END_TOKENS
        ):
            self.mask.append(MaskToken.PARAMETER_NAME)
        # if the state is parameter name and the token is an end token, change the state, check hallucination and set the flag parameter name done
        # The need for parameter name done is to allow the check of parameter value pattern
        elif self.state == "parameter_name" and content.endswith(
            PARAMETER_NAME_END_TOKENS
        ):
            self.state = None
            self.parameter_name_done = True
            self._get_parameter_name()
        # if the parameter name is done and the token is a parameter name start token, change the state
        elif (
            self.parameter_name_done
            and self.open_bracket == False
            and content.endswith(PARAMETER_NAME_START_PATTERN)
        ):
            self.state = "parameter_name"

        # if token is a first parameter value start token, change the state
        if content.endswith(FIRST_PARAM_NAME_START_PATTERN):
            self.state = "parameter_name"

        # Parameter value extraction logic
        # if the state is parameter value and the token is not an end token, add to the mask
        if self.state == "parameter_value" and not content.endswith(
            PARAMETER_VALUE_END_TOKEN
        ):
            # checking if the token is a value token and is not empty
            open_brackets = [
                char for char in self.tokens[-1].strip() if char in BRACKETS
            ]
            if open_brackets:
                self.open_bracket = True
                self.bracket = open_brackets[0]

            if self.open_bracket and BRACKETS[self.bracket] in self.tokens[-1].strip():
                self.open_bracket = False
                self.bracket = None

            if (
                not all(
                    char in set(string.punctuation) for char in self.tokens[-1].strip()
                )
                and self.tokens[-1].strip() != ""
            ):
                self.mask.append(MaskToken.PARAMETER_VALUE)

                # [TODO] Review: update the following code: `is_parameter_property` should not be here, move to `ArchFunctionHandler`
                # checking if the parameter doesn't have default and the token is the first parameter value token
                if (
                    len(self.mask) > 1
                    and self.mask[-2] != MaskToken.PARAMETER_VALUE
                    and is_parameter_required(
                        self.function_properties[self.function_name],
                        self.parameter_name[-1],
                    )
                ):
                    if self.parameter_name[-1] not in self.check_parameter_name:
                        self._check_logprob()
                        self.check_parameter_name[self.parameter_name[-1]] = True
            else:
                self.mask.append(MaskToken.NOT_USED)
        # if the state is parameter value and the token is an end token, change the state
        elif (
            self.state == "parameter_value"
            and self.open_bracket == False
            and content.endswith(PARAMETER_VALUE_END_TOKEN)
        ):
            self.state = None
        # if the parameter name is done and the token is a parameter value start token, change the state
        elif self.parameter_name_done and content.endswith(
            PARAMETER_VALUE_START_PATTERN
        ):
            self.state = "parameter_value"

        # Maintain consistency between stack and mask
        # If the mask length is less than tokens, add an not used (e) token to the mask
        if len(self.mask) != len(self.tokens):
            self.mask.append(MaskToken.NOT_USED)

    def _check_logprob(self):
        """
        Checks the log probability of the current token and updates the token probability map.
        Detects hallucinations based on entropy and variance of entropy.
        """
        probs = self.logprobs[-1]
        entropy, varentropy, probability = calculate_uncertainty(probs)
        self.token_probs_map.append((self.tokens[-1], entropy, varentropy, probability))

        if check_threshold(
            entropy,
            varentropy,
            probability,
            self.HALLUCINATION_THRESHOLD_DICT[self.mask[-1].value],
        ):
            self.hallucination = True
            self.error_type = "Hallucination"
            self.error_message = (
                f"Hallucination: token '{self.tokens[-1]}' is uncertain."
            )

            # [TODO] - Review: remove the following code
            # print(f"[Hallucination] - Hallucination detected: {self.error_message}")

    def _count_consecutive_token(self, token=MaskToken.PARAMETER_VALUE) -> int:
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

    def _get_parameter_name(self):
        """
        Get the parameter name from the tokens.

        Returns:
            str: The extracted parameter name.
        """
        p_len = self._count_consecutive_token(MaskToken.PARAMETER_NAME)
        parameter_name = "".join(self.tokens[:-1][-p_len:])
        self.parameter_name.append(parameter_name)

    def _get_function_name(self):
        """
        Get the function name from the tokens.

        Returns:
            str: The extracted function name.
        """
        f_len = self._count_consecutive_token(MaskToken.FUNCTION_NAME)
        self.function_name = "".join(self.tokens[:-1][-f_len:])
