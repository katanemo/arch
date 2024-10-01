import json
import random
from fastapi import FastAPI, Response
from arch_handler import ArchHandler
from bolt_handler import BoltHandler
from common import ChatMessage
import logging
import yaml
from openai import OpenAI
import os


with open("openai_params.yaml") as f:
    params = yaml.safe_load(f)

ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "localhost")
ollama_model = os.getenv("OLLAMA_MODEL", "Arch-Function-Calling-1.5B-Q4_K_M")
fc_url = os.getenv("FC_URL", ollama_endpoint)
mode = os.getenv("MODE", "cloud")
if mode not in ["cloud", "local-gpu", "local-cpu"]:
    raise ValueError(f"Invalid mode: {mode}")
arch_api_key = os.getenv("ARCH_API_KEY", "")
logger = logging.getLogger("uvicorn.error")

handler = None
if ollama_model.startswith("Arch"):
    handler = ArchHandler()
else:
    handler = BoltHandler()


app = FastAPI()

if mode == "cloud":
    client = OpenAI(
        base_url=fc_url,
        api_key=arch_api_key,
    )
    models = client.models.list()
    model = models.data[0].id
    chosen_model = model
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


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.post("/v1/chat/completions")
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
