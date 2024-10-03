import json
import os
from openai import OpenAI
import gradio as gr
import logging as log
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

log.info("CHAT_COMPLETION_ENDPOINT: ", CHAT_COMPLETION_ENDPOINT)

client = OpenAI(api_key=OPENAI_API_KEY, base_url=CHAT_COMPLETION_ENDPOINT)

def predict(message, history):
    history.append({"role": "user", "content": message})
    log.info("CHAT_COMPLETION_ENDPOINT: ", CHAT_COMPLETION_ENDPOINT)
    log.info("history: ", history)

    # Custom headers
    custom_headers = {
        'x-arch-openai-api-key': f"{OPENAI_API_KEY}",
        'x-arch-mistral-api-key': f"{MISTRAL_API_KEY}",
        'x-arch-deterministic-provider': 'openai',
    }

    updated_history = []
    for h in history.copy():
        updated_history.append(h)
        if 'tool_calls' in h:
            tool_calls = h.pop('tool_calls')
            updated_history.append({"role": "assistant", "content": tool_calls})
    try:
      raw_response = client.chat.completions.with_raw_response.create(model=MODEL_NAME,
        messages = updated_history,
        temperature=1.0,
        extra_headers=custom_headers
      )
    except Exception as e:
      log.info(e)
      # remove last user message in case of exception
      history.pop()
      log.info("CHAT_COMPLETION_ENDPOINT: ", CHAT_COMPLETION_ENDPOINT)
      log.info("Error calling gateway API: {}".format(e.message))
      raise gr.Error("Error calling gateway API: {}".format(e.message))

    response = raw_response.parse()
    headers = raw_response.headers

    choices = response.choices
    message = choices[0].message
    content = message.content

    history.append({"role": "assistant", "content": content})
    history[-1]["model"] = response.model
    if 'x-arch-tool-calls' in headers:
        tool_calls_str = headers['x-arch-tool-calls']
        tool_calls = json.loads(tool_calls_str)
        history[-1]['tool_calls'] = f"<tool_call>\n{json.dumps(tool_calls[0]['function'])}\n</tool_call>"

    messages = [(history[i]["content"], history[i+1]["content"]) for i in range(0, len(history)-1, 2)]
    return messages, history

with gr.Blocks(fill_height=True, css="footer {visibility: hidden}") as demo:
    print("Starting Demo...")
    chatbot = gr.Chatbot(label="Arch Chatbot", scale=1)
    state = gr.State([])
    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter", scale=1, autofocus=True)

    txt.submit(predict, [txt, state], [chatbot, state])

demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True, debug=True)
