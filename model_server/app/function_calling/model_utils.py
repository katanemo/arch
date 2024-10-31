import json
import hashlib
import app.commons.constants as const

from fastapi import Response
from pydantic import BaseModel
from app.commons.utilities import get_model_server_logger
from typing import Any, Dict, List, Optional


logger = get_model_server_logger()


class Message(BaseModel):
    role: Optional[str] = ""
    content: Optional[str] = ""
    tool_calls: Optional[List[Dict[str, Any]]] = []
    tool_call_id: Optional[str] = ""


class ChatMessage(BaseModel):
    messages: list[Message]
    tools: List[Dict[str, Any]]


class Choice(BaseModel):
    message: Message


class ChatCompletionResponse(BaseModel):
    choices: List[Choice]


def process_messages(history: list[Message]):
    updated_history = []
    for hist in history:
        if hist.tool_calls:
            if len(hist.tool_calls) > 1:
                error_msg = f"Only one tool call is supported, tools counts: {len(hist.tool_calls)}"
                logger.error(error_msg)
                raise ValueError(error_msg)
            tool_call_str = json.dumps(hist.tool_calls[0]["function"])
            updated_history.append(
                {
                    "role": "assistant",
                    "content": f"<tool_call>\n{tool_call_str}\n</tool_call>",
                }
            )
        elif hist.role == "tool":
            updated_history.append(
                {
                    "role": "user",
                    "content": f"<tool_response>\n{hist.content}\n</tool_response>",
                }
            )
        else:
            updated_history.append({"role": hist.role, "content": hist.content})
    return updated_history


async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")

    tools_encoded = const.arch_function_hanlder._format_system(req.tools)

    messages = [{"role": "system", "content": tools_encoded}]

    updated_history = process_messages(req.messages)
    for message in updated_history:
        messages.append({"role": message["role"], "content": message["content"]})

    client_model_name = const.arch_function_client.models.list().data[0].id

    logger.info(
        f"model_server => arch_function: {client_model_name}, messages: {json.dumps(messages)}"
    )

    try:
        resp = const.arch_function_client.chat.completions.create(
            messages=messages,
            model=client_model_name,
            stream=True,
            extra_body=const.arch_function_generation_params,
        )
    except Exception as e:
        logger.error(f"model_server <= arch_function: error: {e}")
        raise

    # Retrieve the first token, handling the Stream object carefully
    first_token_content = ""
    try:
        while True:
            first_token = next(resp)  # Synchronously retrieve tokens
            first_token_content = first_token.choices[
                0
            ].delta.content.strip()  # Clean up the content
            if first_token_content:  # Break if it's non-empty
                break
    except StopIteration:
        print("No non-empty tokens found.")
        return None

    # Check if the first token requires tool call handling
    if first_token_content != "<tool_call>":
        # Engage pre-filling response if no tool call is indicated
        logger.info("Tool call is not found! Engage pre filling")
        messages.append({"role": "assistant", "content": "Sure!"})

        # Send a new completion request with the updated messages
        pre_fill_resp = const.arch_function_client.chat.completions.create(
            messages=messages,
            model=client_model_name,
            stream=False,
            extra_body=const.arch_function_generation_params,
        )
        full_response = pre_fill_resp.choices[0].message.content
    else:
        # Initialize full response and iterate over tokens to gather the full response
        full_response = "<tool_call>"
        try:
            while True:
                token = next(resp)  # Retrieve each token synchronously
                if hasattr(token.choices[0].delta, "content"):
                    full_response += token.choices[0].delta.content
        except StopIteration:
            pass  # End of stream

    tool_calls = const.arch_function_hanlder.extract_tool_calls(full_response)

    if tool_calls:
        message = Message(content="", tool_calls=tool_calls)
    else:
        message = Message(content=full_response, tool_calls=[])
    choice = Choice(message=message)
    chat_completion_response = ChatCompletionResponse(choices=[choice])

    logger.info(
        f"model_server <= arch_function: (tools): {json.dumps([tool_call['function'] for tool_call in tool_calls])}"
    )
    logger.info(
        f"model_server <= arch_function: response body: {json.dumps(chat_completion_response.dict())}"
    )

    return chat_completion_response
