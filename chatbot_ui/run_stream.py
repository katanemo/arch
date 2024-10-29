import json
import os
import logging
import yaml
import gradio as gr

from typing import List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

from common import get_prompt_targets, process_stream_chunk

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


def chat(
    query: Optional[str],
    conversation: Optional[List[Tuple[str, str]]],
    history: List[dict],
):
    history.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            # we select model from arch_config file
            model="--",
            messages=history,
            temperature=1.0,
            stream=True,
        )
    except Exception as e:
        # remove last user message in case of exception
        history.pop()
        log.info("Error calling gateway API: {}".format(e))
        raise gr.Error("Error calling gateway API: {}".format(e))

    conversation.append((query, ""))

    for chunk in response:
        tokens = process_stream_chunk(chunk, history)
        if tokens:
            conversation[-1] = (
                conversation[-1][0],
                conversation[-1][1] + tokens,
            )

            yield "", conversation, history


def main():
    with gr.Blocks(
        theme=gr.themes.Default(
            font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "Arial", "sans-serif"]
        ),
        fill_height=True,
        css=CSS_STYLE,
    ) as demo:
        with gr.Row(equal_height=True):
            state = gr.State([])

            with gr.Column(scale=1):
                with gr.Accordion("See available tools", open=False):
                    with gr.Column(scale=1):
                        gr.JSON(
                            value=get_prompt_targets(),
                            show_indices=False,
                            elem_classes="json-container",
                            min_height="95vh",
                        )

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Arch Chatbot",
                    elem_classes="chatbot",
                )
                textbox = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    autofocus=True,
                    elem_classes="textbox",
                )

            textbox.submit(chat, [textbox, chatbot, state], [textbox, chatbot, state])

    demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True, debug=True)


if __name__ == "__main__":
    main()
