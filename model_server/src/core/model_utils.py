import json

from openai import OpenAI
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from overrides import final


class Message(BaseModel):
    role: Optional[str] = ""
    content: Optional[str] = ""
    tool_call_id: Optional[str] = ""
    tool_calls: Optional[List[Dict[str, Any]]] = []


class ChatMessage(BaseModel):
    messages: list[Message]
    tools: List[Dict[str, Any]]


class Choice(BaseModel):
    id: Optional[int] = 0
    message: Message
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: Optional[int] = 0
    object: Optional[str] = "chat_completion"
    created: Optional[str] = ""
    choices: List[Choice]
    model: str
    metadata: Optional[Dict[str, str]] = {}


class GuardRequest(BaseModel):
    input: str
    task: str


class GuardResponse(BaseModel):
    prob: List
    verdict: bool
    sentence: List
    latency: float = 0


# ================================================================================================


class ArchBaseHandler:
    def __init__(
        self,
        client: OpenAI,
        model_name: str,
        task_prompt: str,
        tool_prompt_template: str,
        format_prompt: str,
        generation_params: Dict,
    ):
        """
        Initializes the base handler.

        Args:
            client (OpenAI): An OpenAI client instance.
            model_name (str): Name of the model to use.
            task_prompt (str): The main task prompt for the system.
            tool_prompt (str): A prompt to describe tools.
            format_prompt (str): A prompt specifying the desired output format.
            generation_params (Dict): Generation parameters for the model.
        """
        self.client = client
        self.model_name = model_name

        self.task_prompt = task_prompt
        self.tool_prompt_template = tool_prompt_template
        self.format_prompt = format_prompt

        self.generation_params = generation_params

    def _convert_tools(self, tools: List[Dict[str, Any]]) -> str:
        """
        Converts a list of tools into the desired internal representation.

        Args:
            tools (List[Dict[str, Any]]): A list of tools represented as dictionaries.

        Raises:
            NotImplementedError: Method should be overridden in subclasses.
        """

        raise NotImplementedError()

    @final
    def _format_system_prompt(self, tools: List[Dict[str, Any]]) -> str:
        """
        Formats the system prompt using provided tools.

        Args:
            tools (List[Dict[str, Any]]): A list of tools represented as dictionaries.

        Returns:
            str: A formatted system prompt.
        """

        tool_text = self._convert_tools(tools)

        system_prompt = (
            self.task_prompt
            + "\n\n"
            + self.tool_prompt_template.format(tool_text=tool_text)
            + "\n\n"
            + self.format_prompt
        )

        return system_prompt

    @final
    def _process_messages(
        self,
        messages: List[Message],
        tools: List[Dict[str, Any]] = None,
        extra_instruction: str = None,
    ):
        """
        Processes a list of messages and formats them appropriately.

        Args:
            messages (List[Message]): A list of message objects.
            tools (List[Dict[str, Any]], optional): A list of tools to include in the system prompt.
            extra_instruction (str, optional): Additional instructions to append to the last user message.

        Returns:
            List[Dict[str, Any]]: A list of processed message dictionaries.
        """

        processed_messages = []

        if tools:
            processed_messages.append(
                {"role": "system", "content": self._format_system_prompt(tools)}
            )

        for message in messages:
            role, content, tool_calls = (
                message.role,
                message.content,
                message.tool_calls,
            )

            if tool_calls:
                # [TODO] Extend to support multiple function calls
                role = "assistant"
                content = f"<tool_call>\n{json.dumps(tool_calls[0]['function'])}\n</tool_call>"
            elif message.role == "tool":
                role = "user"
                content = (
                    f"<tool_response>\n{json.dumps(message.content)}\n</tool_response>"
                )

            processed_messages.append({"role": role, "content": content})

        assert processed_messages[-1]["role"] == "user"

        if extra_instruction:
            processed_messages[-1]["content"] += extra_instruction

        return processed_messages

    async def chat_completion(self, req: ChatMessage) -> ChatCompletionResponse:
        """
        Abstract method for generating chat completions.

        Args:
            req (ChatMessage): A chat message request object.

        Raises:
            NotImplementedError: Method should be overridden in subclasses.
        """

        raise NotImplementedError()
