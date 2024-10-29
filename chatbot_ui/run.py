import json
import os
import logging
import yaml
from common import get_arch_messages
import gradio as gr

from typing import List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = logging.getLogger(__name__)

CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT")
log.info(f"CHAT_COMPLETION_ENDPOINT: {CHAT_COMPLETION_ENDPOINT}")


CSS_STYLE = """
.json-container {
    height: 95vh !important;
    overflow-y: auto !important;
}
.chatbot {
    height: calc(95vh - 100px) !important;
    overflow-y: auto !important;
}
footer {visibility: hidden}
"""

client = OpenAI(
    api_key="--",
    base_url=CHAT_COMPLETION_ENDPOINT,
)


def chat(query: Optional[str], conversation: Optional[List[Tuple[str, str]]], state):
    if "history" not in state:
        state["history"] = []

    history = state.get("history")
    history.append({"role": "user", "content": query})
    log.info(f"history: {history}")

    try:
        raw_response = client.chat.completions.with_raw_response.create(
            model="--",
            messages=history,
            temperature=1.0,
        )
    except Exception as e:
        history.pop()
        # remove last user message in case of exception
        log.error("Error calling gateway API: {}".format(e))
        raise gr.Error("Error calling gateway API: {}".format(e))

    log.error(f"raw_response: {raw_response.text}")
    response = raw_response.parse()

    # extract arch_state from metadata and store it in gradio session state
    # this state must be passed back to the gateway in the next request
    response_json = json.loads(raw_response.text)
    log.info(response_json)

    arch_messages = get_arch_messages(response_json)
    for arch_message in arch_messages:
        history.append(arch_message)

    content = response.choices[0].message.content

    history.append({"role": "assistant", "content": content, "model": response.model})

    # for gradio UI we don't want to show raw tool calls and messages from developer application
    # so we're filtering those out
    history_view = [h for h in history if h["role"] != "tool" and "content" in h]

    conversation = [
        (history_view[i]["content"], history_view[i + 1]["content"])
        for i in range(0, len(history_view) - 1, 2)
    ]

    yield "", conversation, state


def main():
    with gr.Blocks(
        theme=gr.themes.Default(
            font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "Arial", "sans-serif"]
        ),
        fill_height=True,
        css=CSS_STYLE,
    ) as demo:
        with gr.Row(equal_height=True):
            state = gr.State({})

            with gr.Column(scale=4):
                gr.JSON(
                    value=get_prompt_targets(),
                    open=True,
                    show_indices=False,
                    label="Available Tools",
                    scale=1,
                    min_height="95vh",
                    elem_classes="json-container",
                )
            with gr.Column(scale=6):
                chatbot = gr.Chatbot(
                    label="Arch Chatbot",
                    scale=1,
                    elem_classes="chatbot",
                )
                textbox = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    scale=1,
                    autofocus=True,
                )

            textbox.submit(chat, [textbox, chatbot, state], [textbox, chatbot, state])

    demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True, debug=True)


if __name__ == "__main__":
    main()
