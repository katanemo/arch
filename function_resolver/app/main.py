from fastapi import FastAPI, Response
from transformers import AutoModelForCausalLM, AutoTokenizer
from common import ChatMessage
from handler import KFCHandler
from template import KFCTemplate
import logging

import torch
if torch.backends.mps.is_available():
    mps_device = torch.device("mps")
    x = torch.ones(1, device=mps_device)
    print (x)
else:
    print ("MPS device not found.")

# torch.set_default_device("mps:0")

logger = logging.getLogger('uvicorn.error')

MODEL_NAME = "katanemolabs/KFC-1B"

logger.info(f"Loading model: {MODEL_NAME}")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
logger.info("Model loaded")
hanlder = KFCHandler(model)
template = KFCTemplate(hanlder)

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

@app.post("/v1/chat/completions")
async def chat_completion(req: ChatMessage, res: Response):
    logger.info("starting request")
    response = hanlder.generate(tokenizer, template, req.messages, req.tools)
    # logger.info (f"response: {response}")
    extracted_tools = hanlder.extract_tools(response)
    # logger.info(f"extracted_tools: {extracted_tools}")
    return {
        "response": response,
        "extracted_tools": extracted_tools,
    }
