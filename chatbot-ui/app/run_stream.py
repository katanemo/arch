# copied from https://www.gradio.app/guides/creating-a-chatbot-fast#a-streaming-example-using-openai

import os
from openai import OpenAI
import gradio as gr

api_key = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)

def predict(message, history):
    history_openai_format = []
    for human, assistant in history:
        history_openai_format.append({"role": "user", "content": human })
        history_openai_format.append({"role": "assistant", "content":assistant})
    history_openai_format.append({"role": "user", "content": message})

    response = client.chat.completions.create(model='gpt-3.5-turbo',
    messages= history_openai_format,
    temperature=1.0,
    stream=True)

    partial_message = ""
    for chunk in response:
        if chunk.choices[0].delta.content is not None:
              partial_message = partial_message + chunk.choices[0].delta.content
              yield partial_message

gr.ChatInterface(predict).launch(server_name="0.0.0.0", server_port=8080)
