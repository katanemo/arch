from fastapi import FastAPI, Response
from bolt_handler import BoltHandler
from common import ChatMessage
import logging
from ollama import Client
import os

ollama_endpoint = os.getenv("OLLAMA_ENDPOINT", "localhost")
ollama_model = os.getenv("OLLAMA_MODEL", "Bolt-Function-Calling-1B:Q4_K_M")
logger = logging.getLogger('uvicorn.error')

logger.info(f"using model: {ollama_model}")
logger.info(f"using ollama endpoint: {ollama_endpoint}")

app = FastAPI()
handler = BoltHandler()

ollama_client = Client(host=ollama_endpoint)


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }


@app.post("/v1/chat/completions")
async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")
    tools_encoded = handler._format_system(req.tools)
    messages = []
    messages.append(
        {"role": "system", "content": tools_encoded}
    )
    messages.append({"role": "user", "content": req.messages[-1].content})

    resp = ollama_client.chat(messages=messages, model=ollama_model, stream=False)
    logger.info(f"response: {resp}")
    return resp
