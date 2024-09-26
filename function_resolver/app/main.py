import json
import random
from fastapi import FastAPI, Response
from arch_handler import ArchHandler
from common import ChatMessage
import logging
from openai import OpenAI
import os

ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "localhost")
ollama_model = os.getenv("OLLAMA_MODEL", "Arch-Function-Calling-1.5B-Q4_K_M")
logger = logging.getLogger('uvicorn.error')

logger.info(f"using model: {ollama_model}")
logger.info(f"using ollama endpoint: {ollama_endpoint}")

app = FastAPI()

handler = ArchHandler()

client = OpenAI(
    base_url='http://{}:11434/v1/'.format(ollama_endpoint),

    # required but ignored
    api_key='ollama',
)

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }


@app.post("/v1/chat/completions")
async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")
    tools_encoded = handler._format_system(req.tools)
    # append system prompt with tools to messages
    messages = [{"role": "system", "content": tools_encoded}]
    for message in req.messages:
        messages.append({"role": message.role, "content": message.content})
    logger.info(f"request model: {ollama_model}, messages: {json.dumps(messages)}")
    resp = client.chat.completions.create(messages=messages, model=ollama_model, stream=False)
    tools = handler.extract_tools(resp.choices[0].message.content)
    tool_calls = []
    for tool in tools:
       for tool_name, tool_args in tool.items():
          tool_calls.append({
              "id": f"call_{random.randint(1000, 10000)}",
              "type": "function",
              "function": {
                "name": tool_name,
                "arguments": tool_args
              }
          })
    if tools:
      resp.choices[0].message.tool_calls = tool_calls
      resp.choices[0].message.content = None
    logger.info(f"response (tools): {json.dumps(tools)}")
    logger.info(f"response: {json.dumps(resp.to_dict())}")
    return resp
