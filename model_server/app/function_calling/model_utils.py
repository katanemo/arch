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
    content: str


class ChatMessage(BaseModel):
    messages: list[Message]
    tools: List[Dict[str, Any]]

    # TODO: make it default none
    metadata: Dict[str, str] = {}


def process_state(arch_state, history: list[Message]):
    logger.info("state: {}".format(arch_state))
    state_json = json.loads(arch_state)

    state_map = {}
    if state_json:
        for tools_state in state_json:
            for tool_state in tools_state:
                state_map[tool_state["key"]] = tool_state

    logger.info(f"state_map: {json.dumps(state_map)}")

    sha_history = []
    updated_history = []
    for hist in history:
        updated_history.append({"role": hist.role, "content": hist.content})
        if hist.role == "user":
            sha_history.append(hist.content)
            sha256_hash = hashlib.sha256()
            joined_key_str = ("#.#").join(sha_history)
            sha256_hash.update(joined_key_str.encode())
            sha_key = sha256_hash.hexdigest()
            logger.info(f"sha_key: {sha_key}")
            if sha_key in state_map:
                tool_call_state = state_map[sha_key]
                if "tool_call" in tool_call_state:
                    tool_call_str = json.dumps(tool_call_state["tool_call"])
                    updated_history.append(
                        {
                            "role": "assistant",
                            "content": f"<tool_call>\n{tool_call_str}\n</tool_call>",
                        }
                    )
                if "tool_response" in tool_call_state:
                    tool_resp = tool_call_state["tool_response"]
                    # TODO: try with role = user as well
                    updated_history.append(
                        {
                            "role": "user",
                            "content": f"<tool_response>\n{tool_resp}\n</tool_response>",
                        }
                    )
                # we dont want to match this state with any other messages
                del state_map[sha_key]

    return updated_history


async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")

    tools_encoded = const.arch_function_hanlder._format_system(req.tools)

    messages = [{"role": "system", "content": tools_encoded}]

    metadata = req.metadata
    arch_state = metadata.get("x-arch-state", "[]")

    updated_history = process_state(arch_state, req.messages)
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
