import gradio as gr

import asyncio
import httpx
import async_timeout

from loguru import logger
from typing import Optional, List
from pydantic import BaseModel
from dotenv import load_dotenv

import os
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT", "https://api.openai.com/v1/chat/completions")

class Message(BaseModel):
    role: str
    content: str
    model: str
    resolver: str

async def make_completion(messages:List[Message], nb_retries:int=3, delay:int=120) -> Optional[str]:
    """
    Sends a request to the ChatGPT API to retrieve a response based on a list of previous messages.
    """
    header = {
        "Content-Type": "application/json",
    }

    if OPENAI_API_KEY is not None and OPENAI_API_KEY != "":
        header["Authorization"] = f"Bearer {OPENAI_API_KEY}"

    if OPENAI_API_KEY is None or OPENAI_API_KEY == "":
        if CHAT_COMPLETION_ENDPOINT.startswith("https://api.openai.com"):
          logger.error("No OpenAI API Key found. Please create .env file and set OPENAI_API_KEY env var !")
          return None
    try:
        async with async_timeout.timeout(delay=delay):
            async with httpx.AsyncClient(headers=header) as aio_client:
                counter = 0
                keep_loop = True
                while keep_loop:
                    logger.debug(f"Chat/Completions Nb Retries : {counter}")
                    try:
                        resp = await aio_client.post(
                            url = CHAT_COMPLETION_ENDPOINT,
                            json = {
                                "model": "gpt-3.5-turbo",
                                "messages": messages
                            },
                            timeout=delay
                        )
                        logger.debug(f"Status Code : {resp.status_code}")
                        if resp.status_code == 200:
                            resp_json = resp.json()
                            model = resp_json["model"]
                            msg = {}
                            msg["role"] = "assistant"
                            msg["model"] = model
                            if "resolver_name" in resp_json:
                                msg["resolver"] = resp_json["resolver_name"]
                            if "choices" in resp_json:
                                msg["content"] = resp_json["choices"][0]["message"]["content"]
                                return msg
                            elif "message" in resp_json:
                                msg["content"] = resp_json["message"]["content"]
                                return msg
                            keep_loop = False
                        else:
                            logger.warning(resp.content)
                            keep_loop = False
                    except Exception as e:
                        logger.error(e)
                        counter = counter + 1
                        keep_loop = counter < nb_retries
    except asyncio.TimeoutError as e:
        logger.error(f"Timeout {delay} seconds !")
    return None

async def predict(input, history):
    """
    Predict the response of the chatbot and complete a running list of chat history.
    """
    history.append({"role": "user", "content": input})
    response = await make_completion(history)
    print(response)
    if response is not None:
      history.append(response)
    messages = [(history[i]["content"], history[i+1]["content"]) for i in range(0, len(history)-1, 2)]
    return messages, history

"""
Gradio Blocks low-level API that allows to create custom web applications (here our chat app)
"""
with gr.Blocks(fill_height=True, css="footer {visibility: hidden}") as demo:
    logger.info("Starting Demo...")
    chatbot = gr.Chatbot(label="Bolt Chatbot", scale=1)
    state = gr.State([])
    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter", scale=1)
    txt.submit(predict, [txt, state], [chatbot, state])

demo.launch(server_name="0.0.0.0", server_port=8080)
