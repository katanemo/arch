import json
import random
import builtins

from openai import OpenAI
from typing import Any, Dict, List, Tuple, Union
from overrides import override
from app.model_handler.base_handler import (
    Message,
    ChatMessage,
    Choice,
    ChatCompletionResponse,
    ArchBaseHandler,
)


SUPPORT_DATA_TYPES = ["int", "float", "bool", "str", "list", "tuple", "set", "dict"]


class ArchIntentHandler(ArchBaseHandler):
    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        task_prompt: str,
        tool_prompt_template: str,
        format_prompt: str,
        extra_instruction: str,
        generation_params: Dict,
    ):
        """
        Initializes the intent handler.

        Args:
            client (OpenAI): An OpenAI client instance.
            model_name (str): Name of the model to use.
            task_prompt (str): The main task prompt for the system.
            tool_prompt_template (str): A prompt to describe tools.
            format_prompt (str): A prompt specifying the desired output format.
            extra_instruction (str): Instructions specific to intent handling.
            generation_params (Dict): Generation parameters for the model.
        """

        super().__init__(
            client,
            model_name,
            task_prompt,
            tool_prompt_template,
            format_prompt,
            generation_params,
        )

        self.extra_instruction = extra_instruction

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

        messages = self._process_messages(
            req.messages, req.tools, self.extra_instruction
        )

        model_response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            stream=False,
            extra_body=self.generation_params,
        )

        model_response = Message(
            content=model_response.choices[0].message.content, tool_calls=[]
        )

        chat_completion_response = ChatCompletionResponse(
            choices=[Choice(message=model_response)], model=self.model_name
        )

        return chat_completion_response


class ArchFunctionHandler(ArchBaseHandler):
    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        task_prompt: str,
        tool_prompt_template: str,
        format_prompt: str,
        generation_params: Dict,
        prefill_params: Dict,
        prefill_prefix: List,
    ):
        """
        Initializes the function handler.

        Args:
            client (OpenAI): An OpenAI client instance.
            model_name (str): Name of the model to use.
            task_prompt (str): The main task prompt for the system.
            tool_prompt_template (str): A prompt to describe tools.
            format_prompt (str): A prompt specifying the desired output format.
            generation_params (Dict): Generation parameters for the model.
            prefill_params (Dict): Additional parameters for prefilling responses.
            prefill_prefix (List[str]): List of prefixes for prefill responses.
        """

        super().__init__(
            client,
            model_name,
            task_prompt,
            tool_prompt_template,
            format_prompt,
            generation_params,
        )

        self.prefill_params = prefill_params
        self.prefill_prefix = prefill_prefix

        # Predefine data types for verification. Only support Python for now.
        # [TODO] Extend the list of support data types
        self.support_data_types = {
            type_name: getattr(builtins, type_name) for type_name in SUPPORT_DATA_TYPES
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

    def _extract_tool_calls(
        self, content: str
    ) -> Tuple[List[Dict[str, Any]], bool, Union[str, Exception]]:
        """
        Extracts tool call information from a given string.

        Args:
            content (str): The content string containing potential tool call information.

        Returns:
            Tuple[List[Dict[str, Any]], bool, Union[str, Exception]]:
                - A list of tool call dictionaries.
                - A boolean indicating if the extraction was valid.
                - An error message or exception if extraction failed.
        """

        tool_calls, is_valid, error_message = [], True, ""

        flag = False
        for line in content.split("\n"):
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
                            return tool_calls, is_valid, error_message

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

        return tool_calls, is_valid, error_message

    def _verify_tool_calls(
        self, tools: List[Dict[str, Any]], tool_calls: List[Dict[str, Any]]
    ) -> Tuple[bool, Union[Dict[str, Any], None], str]:
        """
        Verifies the validity of extracted tool calls against the provided tools.

        Args:
            tools (List[Dict[str, Any]]): A list of available tools.
            tool_calls (List[Dict[str, Any]]): A list of tool calls to verify.

        Returns:
            Tuple[bool, Union[Dict[str, Any], None], str]:
                - A boolean indicating if the tool calls are valid.
                - The invalid tool call dictionary if any.
                - An error message.
        """

        is_valid, error_tool_call, error_message = True, None, ""

        functions = {}
        for tool in tools:
            if tool["type"] == "function":
                functions[tool["function"]["name"]] = tool["function"]["parameters"]

        for tool_call in tool_calls:
            func_name, func_args = (
                tool_call["function"]["name"],
                tool_call["function"]["arguments"],
            )

            # Check whether the function is available or not
            if func_name not in functions:
                is_valid = False
                error_message = f"{func_name} is not defined!"
                return is_valid, error_message
            else:
                # Check if all the requried parameters can be found in the tool calls
                for required_param in functions[func_name].get("required", []):
                    if required_param not in func_args:
                        is_valid = False
                        error_tool_call = tool_call
                        error_message = f"`{required_param}` is requiried by the function `{func_name}` but not found in the tool call!"
                        return is_valid, error_tool_call, error_message

                # Verify the data type of each parameter in the tool calls
                for param_name, param_value in func_args:
                    data_type = functions[func_name]["properties"][param_name]["type"]

                    if data_type in self.support_data_types:
                        if not isinstance(
                            param_value, self.support_data_types[data_type]
                        ):
                            is_valid = False
                            error_tool_call = tool_call
                            error_message = f"Parameter `{param_name}` is expected to have the data type `{self.support_data_types[data_type]}`, but got `{type(param_value)}`."
                            return is_valid, error_tool_call, error_message

        return is_valid, error_tool_call, error_message

    @override
    async def chat_completion(
        self, req: ChatMessage, enable_prefilling=True
    ) -> ChatCompletionResponse:
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

        # Retrieve the first token, handling the Stream object carefully
        response = self.client.chat.completions.create(
            messages=messages,
            model=self.model_name,
            stream=enable_prefilling,
            extra_body=self.generation_params,
        )

        model_response = ""

        if enable_prefilling:
            has_tool_call = None

            model_response = ""
            for token in response:
                token_content = token.choices[0].delta.content.strip()

                if token_content:
                    if has_tool_call is None and token_content != "<tool_call>":
                        has_tool_call = False
                        response.close()
                        break
                    else:
                        has_tool_call = True

                    if has_tool_call is True:
                        model_response += token_content

            # start parameter gathering if the model is not generating a tool call
            if has_tool_call is False:
                messages.append(
                    {
                        "role": "assistant",
                        "content": random.choice(self.prefill_prefix),
                    }
                )

                prefill_response = self.client.chat.completions.create(
                    messages=messages,
                    model=self.model_name,
                    stream=False,
                    extra_body={
                        **self.generation_params,
                        **self.prefill_params,
                    },
                )

                model_response = prefill_response.choices[0].message.content
        else:
            model_response = response.choices[0].message.content

        (
            tool_calls,
            extraction_status,
            extraction_error_message,
        ) = self._extract_tool_calls(model_response)

        if tool_calls:
            # [TODO] Review: define the behavior in the case that tool call extraction fails
            # if not extraction_status:

            (
                verification_status,
                invalid_tool_call,
                verification_error_message,
            ) = self._verify_tool_calls(tools=req.tools, tool_calls=tool_calls)

            # [TODO] Review: In the case that tool calls are invalid, define the protocol to collect debugging output and the behavior to handle it appropriately
            if verification_status:
                model_response = Message(content="", tool_calls=tool_calls)
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
