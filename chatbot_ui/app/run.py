import os
from openai import OpenAI
import gradio as gr

OPEN_API_KEY=os.getenv("OPENAI_API_KEY")
CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")

client = OpenAI(api_key=OPEN_API_KEY, base_url=CHAT_COMPLETION_ENDPOINT)

def predict(message, history):
    # history_openai_format = []
    # for human, assistant in history:
    #     history_openai_format.append({"role": "user", "content": human })
    #     history_openai_format.append({"role": "assistant", "content":assistant})
    history.append({"role": "user", "content": message})

    try:
      response = client.chat.completions.create(model='gpt-3.5-turbo',
        messages= history,
        temperature=1.0
      )
    except Exception as e:
      print(e)
      # remove last user message in case of exception
      history.pop()
      raise gr.Error("Error with OpenAI API: {}".format(e.message))

    # for chunk in response:
    #     if chunk.choices[0].delta.content is not None:
    #           partial_message = partial_message + chunk.choices[0].delta.content
    #           yield partial_message
    choices = response.choices
    message = choices[0].message
    content = message.content
    history.append({"role": "assistant", "content": content})
    history[-1]["model"] = response.model

    messages = [(history[i]["content"], history[i+1]["content"]) for i in range(0, len(history)-1, 2)]
    return messages, history


with gr.Blocks(fill_height=True, css="footer {visibility: hidden}") as demo:
    print("Starting Demo...")
    chatbot = gr.Chatbot(label="Bolt Chatbot", scale=1)
    state = gr.State([])
    with gr.Row():
        txt = gr.Textbox(show_label=False, placeholder="Enter text and press enter", scale=1, autofocus=True)

    txt.submit(predict, [txt, state], [chatbot, state])

demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True)
