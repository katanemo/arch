import json
import random
import builtins
import textwrap

from openai import OpenAI
from typing import Any, Dict, List
from overrides import override
from src.commons.utils import get_model_server_logger
from src.core.model_utils import (
    Message,
    ChatMessage,
    Choice,
    ChatCompletionResponse,
    ArchBaseHandler,
)
from src.core.hallucination import HallucinationStateHandler

logger = get_model_server_logger()


class ArchIntentConfig:
    TASK_PROMPT = textwrap.dedent(
        """
    You are a helpful assistant.
    """
    ).strip()

    TOOL_PROMPT_TEMPLATE = textwrap.dedent(
        """
    You task is to check if there are any tools that can be used to help the last user message in conversations according to the available tools listed below.

    <tools>
    {tool_text}
    </tools>
    """
    ).strip()

    FORMAT_PROMPT = textwrap.dedent(
        """
    Provide your tool assessment for ONLY THE LAST USER MESSAGE in the above conversation:
    - First line must read 'Yes' or 'No'.
    - If yes, a second line must include a comma-separated list of tool indexes.
    """
    ).strip()

    EXTRA_INSTRUCTION = "Are there any tools can help?"

    GENERATION_PARAMS = {
        "temperature": 0.01,
        "max_tokens": 1,
        "stop_token_ids": [151645],
    }


class ArchIntentHandler(ArchBaseHandler):
    def __init__(self, client: OpenAI, model_name: str, config: ArchIntentConfig):
        """
        Initializes the intent handler.

        Args:
            client (OpenAI): An OpenAI client instance.
            model_name (str): Name of the model to use.
            config (ArchIntentConfig): The configuration for Arch-Intent.
        """

        super().__init__(
            client,
            model_name,
            config.TASK_PROMPT,
            config.TOOL_PROMPT_TEMPLATE,
            config.FORMAT_PROMPT,
            config.GENERATION_PARAMS,
        )

        self.extra_instruction = config.EXTRA_INSTRUCTION

    @override
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> str:
        """
        Converts a list of tools into a JSON-like format with indexed keys.

        Args:
            tools (List[Dict[str, Any]]): A list of tools represented as dictionaries.

        Returns:
            str: A string representation of converted tools.
        """

        converted = [
            json.dumps({"index": f"T{idx}"} | tool) for idx, tool in enumerate(tools)
        ]
        return "\n".join(converted)

    def detect_intent(self, content: str) -> bool:
        """
        Detect if any intent match with prompts

        Args:
            content: str: Model response that contains intent detection results

        Returns:
            bool: A boolean value to indicate if any intent match with prompts or not
        """
        if hasattr(content.choices[0].message, "content"):
            return content.choices[0].message.content == "Yes"
        else:
            return False

    @override
    async def chat_completion(self, req: ChatMessage) -> ChatCompletionResponse:
        """
        Generates a chat completion for a given request.

        Args:
            req (ChatMessage): A chat message request object.

        Returns:
            ChatCompletionResponse: The model's response to the chat request.

        Note:
            Currently only support vllm inference
        """

        # In the case that no tools are available, simply return `No` to avoid making a call
        if len(req.tools) == 0:
            model_response = Message(content="No", tool_calls=[])
        else:
            messages = self._process_messages(
                req.messages, req.tools, self.extra_instruction
            )

            model_response = self.client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                stream=False,
                extra_body=self.generation_params,
            )

            logger.info("arch_intent response: %s", json.dumps(model_response.dict()))

            model_response = Message(
                content=model_response.choices[0].message.content, tool_calls=[]
            )

        chat_completion_response = ChatCompletionResponse(
            choices=[Choice(message=model_response)], model=self.model_name
        )

        return chat_completion_response


# =============================================================================================================


class ArchFunctionConfig:
    TASK_PROMPT = textwrap.dedent(
        """
    You are a helpful assistant.
    """
    ).strip()

    TOOL_PROMPT_TEMPLATE = textwrap.dedent(
        """
    # Tools

    You may call one or more functions to assist with the user query.

    You are provided with function signatures within <tools></tools> XML tags:
    <tools>
    {tool_text}
    </tools>
    """
    ).strip()

    FORMAT_PROMPT = textwrap.dedent(
        """
    For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
    <tool_call>
    {"name": <function-name>, "arguments": <args-json-object>}
    </tool_call>
    """
    ).strip()

    GENERATION_PARAMS = {
        "temperature": 0.6,
        "top_p": 1.0,
        "top_k": 10,
        "max_tokens": 512,
        "stop_token_ids": [151645],
        "logprobs": True,
        "top_logprobs": 10,
    }

    PREFILL_CONFIG = {
        "prefill_params": {
            "continue_final_message": True,
            "add_generation_prompt": False,
        },
        "prefill_prefix": [
            "May",
            "Could",
            "Sure",
            "Definitely",
            "Certainly",
            "Of course",
            "Can",
        ],
    }

    SUPPORT_DATA_TYPES = ["int", "float", "bool", "str", "list", "tuple", "set", "dict"]


class ArchFunctionHandler(ArchBaseHandler):
    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        config: ArchFunctionConfig,
    ):
        """
        Initializes the function handler.

        Args:
            client (OpenAI): An OpenAI client instance.
            model_name (str): Name of the model to use.
            config (ArchFunctionConfig): The configuration for Arch-Function
        """

        super().__init__(
            client,
            model_name,
            config.TASK_PROMPT,
            config.TOOL_PROMPT_TEMPLATE,
            config.FORMAT_PROMPT,
            config.GENERATION_PARAMS,
        )

        self.prefill_params = config.PREFILL_CONFIG["prefill_params"]
        self.prefill_prefix = config.PREFILL_CONFIG["prefill_prefix"]

        # Predefine data types for verification. Only support Python for now.
        # [TODO] Extend the list of support data types
        self.support_data_types = {
            type_name: getattr(builtins, type_name)
            for type_name in config.SUPPORT_DATA_TYPES
        }

    @override
    def _convert_tools(self, tools: List[Dict[str, Any]]) -> str:
        """
        Converts a list of tools into JSON format.

        Args:
            tools (List[Dict[str, Any]]): A list of tools represented as dictionaries.

        Returns:
            str: A string representation of converted tools.
        """

        converted = [json.dumps(tool) for tool in tools]
        return "\n".join(converted)

    def _fix_json_string(self, json_str: str) -> str:
        """
        Fixes malformed JSON strings by ensuring proper bracket matching.

        Args:
            json_str (str): A JSON string that might be malformed.

        Returns:
            str: A corrected JSON string.
        """

        # Remove any leading or trailing whitespace or newline characters
        json_str = json_str.strip()

        # Stack to keep track of brackets
        stack = []

        # Clean string to collect valid characters
        fixed_str = ""

        # Dictionary for matching brackets
        matching_bracket = {")": "(", "}": "{", "]": "["}

        # Dictionary for the opposite of matching_bracket
        opening_bracket = {v: k for k, v in matching_bracket.items()}

        for char in json_str:
            if char in "{[(":
                stack.append(char)
                fixed_str += char
            elif char in "}])":
                if stack and stack[-1] == matching_bracket[char]:
                    stack.pop()
                    fixed_str += char
                else:
                    # Ignore the unmatched closing brackets
                    continue
            else:
                fixed_str += char

        # If there are unmatched opening brackets left in the stack, add corresponding closing brackets
        while stack:
            unmatched_opening = stack.pop()
            fixed_str += opening_bracket[unmatched_opening]

        # Attempt to parse the corrected string to ensure it’s valid JSON
        return fixed_str.replace("'", '"')

    def _extract_tool_calls(self, content: str) -> Dict[str, any]:
        """
        Extracts tool call information from a given string.

        Args:
            content (str): The content string containing potential tool call information.

        Returns:
            Dict: A dictionary of extraction, including:
                - "result": A list of tool call dictionaries.
                - "status": A boolean indicating if the extraction was valid.
                - "message": An error message or exception if extraction failed.
        """

        tool_calls, is_valid, error_message = [], True, ""

        flag = False
        for line in content.split("\n"):
            if not is_valid:
                break

            if "<tool_call>" == line:
                flag = True
            elif "</tool_call>" == line:
                flag = False
            else:
                if flag:
                    try:
                        tool_content = json.loads(line)
                    except Exception as e:
                        fixed_content = self._fix_json_string(line)
                        try:
                            tool_content = json.loads(fixed_content)
                        except Exception:
                            tool_calls, is_valid, error_message = [], False, e
                            break

                    tool_calls.append(
                        {
                            "id": f"call_{random.randint(1000, 10000)}",
                            "type": "function",
                            "function": {
                                "name": tool_content["name"],
                                "arguments": tool_content["arguments"],
                            },
                        }
                    )

                flag = False

        return {"result": tool_calls, "status": is_valid, "message": error_message}

    def _correcting_type(self, value, target_type):
        try:
            if target_type == float and isinstance(value, int):
                return float(value)
            elif target_type == list and isinstance(value, str):
                return ast.literal_eval(value)
            # Add more conversion rules as needed
        except (ValueError, TypeError, json.JSONDecodeError):
            pass
        return value

    def _verify_tool_calls(
        self, tools: List[Dict[str, Any]], tool_calls: List[Dict[str, Any]]
    ) -> Dict[str, any]:
        """
        Verifies the validity of extracted tool calls against the provided tools.

        Args:
            tools (List[Dict[str, Any]]): A list of available tools.
            tool_calls (List[Dict[str, Any]]): A list of tool calls to verify.

        Returns:
            Dict: A dictionary of verification, including:
                - "status": A boolean indicating if the tool calls are valid.
                - "invalid_tool_call": A dictionary of the invalid tool call if any.
                - "message": An error message.
        """

        is_valid, invalid_tool_call, error_message = True, None, ""

        functions = {}
        for tool in tools:
            if tool["type"] == "function":
                functions[tool["function"]["name"]] = tool["function"]["parameters"]

        for tool_call in tool_calls:
            if not is_valid:
                break

            func_name = tool_call["function"]["name"]
            func_args = tool_call["function"]["arguments"]

            # Check whether the function is available or not
            if func_name not in functions:
                is_valid = False
                invalid_tool_call = tool_call
                error_message = f"{func_name} is not defined!"
                break

            else:
                # Check if all the requried parameters can be found in the tool calls
                for required_param in functions[func_name].get("required", []):
                    if required_param not in func_args:
                        is_valid = False
                        invalid_tool_call = tool_call
                        error_message = f"`{required_param}` is requiried by the function `{func_name}` but not found in the tool call!"
                        break

                # Verify the data type of each parameter in the tool calls
                for param_name in func_args:
                    param_value = func_args[param_name]
                    data_type = functions[func_name]["properties"][param_name]["type"]

                    if data_type in self.support_data_types:
                        if not isinstance(
                            param_value,
                            self.support_data_types[data_type],
                        ) and not isinstance(
                            self._correcting_type(
                                param_value, self.support_data_types[data_type]
                            ),
                            self.support_data_types[data_type],
                        ):
                            is_valid = False
                            invalid_tool_call = tool_call
                            error_message = f"Parameter `{param_name}` is expected to have the data type `{self.support_data_types[data_type]}`, but got `{type(param_value)}`."
                            break

        return {
            "status": is_valid,
            "invalid_tool_call": invalid_tool_call,
            "message": error_message,
        }

    def _add_prefill_message(self, messages: List[Dict[str, str]]):
        """
        Update messages and generation params for prompt prefilling

        Args:
            messages (List[Dict[str, str]]): A list of messages.

        Returns:
            prefill_messages (List[Dict[str, str]]): A list of messages.
        """

        return messages + [
            {
                "role": "assistant",
                "content": random.choice(self.prefill_prefix),
            }
        ]

    def _engage_parameter_gathering(self, messages: List[Dict[str, str]]):
        """
        Engage parameter gathering for tool calls
        """

        # TODO: log enaging parameter gathering
        prefill_response = self.client.chat.completions.create(
            messages=self._add_prefill_message(messages),
            model=self.model_name,
            extra_body={
                **self.generation_params,
                **self.prefill_params,
            },
        )

        # logger.info("prefill response: %s", json.dumps(prefill_response.dict()))

        return prefill_response

    def _check_length_and_pop_messages(self, messages, max_tokens=4096):
        """
        Trims the `messages` list to ensure the total token count does not exceed `max_tokens`.

        Args:
            messages (list): List of message dictionaries.
            max_tokens (int): Maximum allowed token count.

        Returns:
            list: Trimmed list of messages.
        """

        def estimate_token_length(messages):
            """Estimate the total token length of the messages."""
            total_tokens = 0
            for message in messages:
                # Approximate token length: assuming ~4 characters per token on average
                total_tokens += len(message["content"]) // 4
            return total_tokens

        # Calculate initial token length
        total_tokens = estimate_token_length(messages)

        # Trim messages if token count exceeds the limit
        while total_tokens > max_tokens and len(messages) >= 3:
            # Find the first non-system message pair
            for i in range(len(messages)):
                if messages[i]["role"] != "system":
                    # Remove the 'user'/'assistant' pair
                    if i + 1 < len(messages) and messages[i + 1]["role"] in [
                        "user",
                        "assistant",
                    ]:
                        del messages[i : i + 2]
                    else:
                        del messages[i]
                    break
            # Recalculate token length
            total_tokens = estimate_token_length(messages)

        return messages

    @override
    async def chat_completion(self, req: ChatMessage) -> ChatCompletionResponse:
        """
        Generates a chat completion response for a given request.

        Args:
            req (ChatMessage): A chat message request object.
            enable_prefilling (bool, optional): Whether to enable prefill responses. Defaults to True.
        Returns:
            ChatCompletionResponse: The model's response to the chat request.

        Note:
            Currently only support vllm inference
        """

        messages = self._process_messages(req.messages, req.tools)
        messages = self._check_length_and_pop_messages(messages)

        # always enable `stream=True` to collect model responses
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            stream=True,
            extra_body=self.generation_params,
        )

        # initialize the hallucination handler, which is an iterator
        self.hallu_handler = HallucinationStateHandler(
            response_iterator=response, function=req.tools
        )

        model_response, self.has_tool_call = "", None

        for _ in self.hallu_handler:
            # check if the first token is <tool_call>
            if len(self.hallu_handler.tokens) > 0 and self.has_tool_call is None:
                if self.hallu_handler.tokens[0] == "<tool_call>":
                    self.has_tool_call = True
                else:
                    self.has_tool_call = False
                    break

            # if the model is hallucinating, start parameter gathering
            if self.hallu_handler.hallucination is True:
                # [TODO] - Review: remove the following code
                print(
                    f"Hallucination detected for the following response, start parameter gathering: \n{''.join(self.hallu_handler.tokens)}"
                )
                print(
                    f"Token entropy/varentropy map: {self.hallu_handler.token_probs_map}"
                )
                prefill_response = self._engage_parameter_gathering(messages)
                model_response = prefill_response.choices[0].message.content
                break

        if self.has_tool_call and self.hallu_handler.hallucination is False:
            # [TODO] - Review: remove the following code
            print("Tool call found, no hallucination detected!")
            model_response = "".join(self.hallu_handler.tokens)

        # start parameter gathering if the model is not generating tool calls
        if self.has_tool_call is False:
            # [TODO] - Review: remove the following code
            print("No tool call found, start parameter gathering")
            print(f"Token entropy/varentropy map: {self.hallu_handler.token_probs_map}")
            prefill_response = self._engage_parameter_gathering(messages)
            model_response = prefill_response.choices[0].message.content

        # Extract tool calls from model response
        extracted = self._extract_tool_calls(model_response)
        # [TODO] - Review: remvoe the following code
        # print(f"[Extracted] - {extracted}")

        if len(extracted["result"]) and extracted["status"]:
            # [TODO] Review: define the behavior in the case that tool call extraction fails
            # if not extracted["status"]:

            verified = self._verify_tool_calls(
                tools=req.tools, tool_calls=extracted["result"]
            )
            # [TODO] - Review: remvoe the following code
            # print(f"[Verified] - {verified}")

            # [TODO] Review: In the case that tool calls are invalid, define the protocol to collect debugging output and the behavior to handle it appropriately
            if verified["status"]:
                model_response = Message(content="", tool_calls=extracted["result"])
            # else:

        else:
            model_response = Message(content=model_response, tool_calls=[])

        chat_completion_response = ChatCompletionResponse(
            choices=[Choice(message=model_response)], model=self.model_name
        )

        # [TODO] Review: define the protocol to collect debugging output
        # logger.info(
        #     f"model_server <= arch_function: (tool_calls): {json.dumps([tool_call['function'] for tool_call in tool_calls])}"
        # )
        # logger.info(
        #     f"model_server <= arch_function: response body: {json.dumps(chat_completion_response.dict())}"
        # )

        return chat_completion_response
