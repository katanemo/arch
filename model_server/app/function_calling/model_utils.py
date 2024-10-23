import json
import hashlib
import app.commons.constants as const

from fastapi import Response
from pydantic import BaseModel
from app.commons.utilities import get_model_server_logger
from typing import Any, Dict, List


logger = get_model_server_logger()


class Message(BaseModel):
    role: str
    content: str = ""
    tool_calls: List[Dict[str, Any]] = []
    tool_call_id: str = ""


class ChatMessage(BaseModel):
    messages: list[Message]
    tools: List[Dict[str, Any]]


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

    resp = const.arch_function_client.chat.completions.create(
        messages=messages,
        model=client_model_name,
        stream=False,
        extra_body=const.arch_function_generation_params,
    )

    tool_calls = const.arch_function_hanlder.extract_tool_calls(
        resp.choices[0].message.content
    )

    if tool_calls:
        resp.choices[0].message.tool_calls = tool_calls
        resp.choices[0].message.content = None

    logger.info(
        f"model_server <= arch_function: (tools): {json.dumps([tool_call['function'] for tool_call in tool_calls])}"
    )
    logger.info(
        f"model_server <= arch_function: response body: {json.dumps(resp.to_dict())}"
    )

    return resp
