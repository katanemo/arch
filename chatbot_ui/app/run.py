import json
import os
from openai import OpenAI, DefaultHttpxClient
import gradio as gr
import logging
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = logging.getLogger(__name__)

CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT")
ARCH_STATE_HEADER = "x-arch-state"
log.info(f"CHAT_COMPLETION_ENDPOINT: {CHAT_COMPLETION_ENDPOINT}")

client = OpenAI(
    api_key="--",
    base_url=CHAT_COMPLETION_ENDPOINT,
    http_client=DefaultHttpxClient(headers={"accept-encoding": "*"}),
)


def predict(message, state):
    if "history" not in state:
        state["history"] = []
    history = state.get("history")
    history.append({"role": "user", "content": message})
    log.info(f"history: {history}")

    # Custom headers
    custom_headers = {
        "x-arch-deterministic-provider": "openai",
    }

    try:
        raw_response = client.chat.completions.with_raw_response.create(
            model="--",
            messages=history,
            temperature=1.0,
            # metadata=metadata,
            extra_headers=custom_headers,
        )
    except Exception as e:
        log.info(e)
        # remove last user message in case of exception
        history.pop()
        log.info("Error calling gateway API: {}".format(e.message))
        raise gr.Error("Error calling gateway API: {}".format(e.message))

    log.error(f"raw_response: {raw_response.text}")
    response = raw_response.parse()

    # extract arch_state from metadata and store it in gradio session state
    # this state must be passed back to the gateway in the next request
    response_json = json.loads(raw_response.text)
    arch_state = {}
    if response_json:
        metadata = response_json.get("metadata", {})
        if metadata:
            arch_state_str = metadata.get(ARCH_STATE_HEADER, "{}")
            arch_state = json.loads(arch_state_str)
    if arch_state:
        state["arch_state"] = arch_state

    arch_messages_str = arch_state.get("messages", "[]")
    arch_messages = json.loads(arch_messages_str)

    content = response.choices[0].message.content

    for message in arch_messages:
        # arch_msg = {"role": message["role"], "content": message.get("content", None), "model": message.get("model", None), "tool_calls": message.get("tool_calls", None), "tool_call_id": message.get("tool_call_id", None)}
        history.append(message)
    history.append({"role": "assistant", "content": content, "model": response.model})
    history_view = [h for h in history if h["role"] != "tool" and "content" in h]
    messages = [
        (history_view[i]["content"], history_view[i + 1]["content"])
        for i in range(0, len(history_view) - 1, 2)
    ]
    return messages, state


with gr.Blocks(fill_height=True, css="footer {visibility: hidden}") as demo:
    print("Starting Demo...")
    chatbot = gr.Chatbot(label="Arch Chatbot", scale=1)
    state = gr.State({})
    with gr.Row():
        txt = gr.Textbox(
            show_label=False,
            placeholder="Enter text and press enter",
            scale=1,
            autofocus=True,
        )

    txt.submit(predict, [txt, state], [chatbot, state])

demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True, debug=True)
