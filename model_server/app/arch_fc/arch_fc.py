import json
import random
from fastapi import FastAPI, Response
from .arch_handler import ArchHandler
from .bolt_handler import BoltHandler
from .common import ChatMessage
from app.utils import load_yaml_config
import logging
import yaml
from openai import OpenAI
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
params = load_yaml_config("openai_params.yaml")
ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "localhost")
ollama_model = os.getenv("OLLAMA_MODEL", "Arch-Function-Calling-1.5B-Q4_K_M")
fc_url = os.getenv("FC_URL", "https://arch-fc-free-trial-4mzywewe.uc.gateway.dev/v1")

mode = os.getenv("MODE", "cloud")
if mode not in ["cloud", "local-gpu", "local-cpu"]:
    raise ValueError(f"Invalid mode: {mode}")

handler = None
if ollama_model.startswith("Arch"):
    handler = ArchHandler()
else:
    handler = BoltHandler()

if mode == "cloud":
    client = OpenAI(
        base_url=fc_url,
        api_key="EMPTY",
    )
    models = client.models.list()
    chosen_model = models.data[0].id
    endpoint = fc_url
else:
    client = OpenAI(
        base_url="http://{}:11434/v1/".format(ollama_endpoint),
        api_key="ollama",
    )
    chosen_model = ollama_model
    endpoint = ollama_endpoint

logger.info(f"serving mode: {mode}")
logger.info(f"using model: {chosen_model}")
logger.info(f"using endpoint: {endpoint}")

async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")
    tools_encoded = handler._format_system(req.tools)
    # append system prompt with tools to messages
    messages = [{"role": "system", "content": tools_encoded}]
    for message in req.messages:
        messages.append({"role": message.role, "content": message.content})
    logger.info(f"request model: {chosen_model}, messages: {json.dumps(messages)}")
    completions_params = params["params"]
    resp = client.chat.completions.create(
        messages=messages,
        model=chosen_model,
        stream=False,
        extra_body=completions_params,
    )
    tools = handler.extract_tools(resp.choices[0].message.content)
    tool_calls = []
    for tool in tools:
        for tool_name, tool_args in tool.items():
            tool_calls.append(
                {
                    "id": f"call_{random.randint(1000, 10000)}",
                    "type": "function",
                    "function": {"name": tool_name, "arguments": tool_args},
                }
            )
    if tools:
        resp.choices[0].message.tool_calls = tool_calls
        resp.choices[0].message.content = None
    logger.info(f"response (tools): {json.dumps(tools)}")
    logger.info(f"response: {json.dumps(resp.to_dict())}")
    return resp
