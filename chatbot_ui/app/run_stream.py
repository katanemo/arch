# copied from https://www.gradio.app/guides/creating-a-chatbot-fast#a-streaming-example-using-openai

import os
from openai import OpenAI
import gradio as gr

api_key = os.getenv("OPENAI_API_KEY")
CHAT_COMPLETION_ENDPOINT = os.getenv(
    "CHAT_COMPLETION_ENDPOINT", "https://api.openai.com/v1"
)

client = OpenAI(api_key="--", base_url=CHAT_COMPLETION_ENDPOINT)


def predict(message, history):
    history_openai_format = []
    for human, assistant in history:
        history_openai_format.append({"role": "user", "content": human})
        history_openai_format.append({"role": "assistant", "content": assistant})
    history_openai_format.append({"role": "user", "content": message})

    stream = True
    raw_response = client.chat.completions.with_raw_response.create(
        model="gpt-3.5-turbo",
        messages=history_openai_format,
        temperature=1.0,
        stream=stream,
    )

    response = raw_response.parse()

    partial_message = ""
    if stream:
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                partial_message = partial_message + chunk.choices[0].delta.content
                yield partial_message
    else:
        partial_message = response.choices[0].message.content
        yield partial_message


gr.ChatInterface(predict).launch(server_name="0.0.0.0", server_port=8080)
