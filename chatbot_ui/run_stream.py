import json
import os
import logging
import yaml
import gradio as gr

from typing import List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

from common import get_prompt_targets

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
    overflow-y: auto !important;
}
.chatbot {
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
        message = chunk.choices[0].delta
        if message.role and message.role != history[-1]["role"]:
            # create new history item if role changes
            # this is likely due to arch tool call and api response
            history.append(
                {
                    "role": message.role,
                }
            )

        history[-1]["model"] = chunk.model
        if message.tool_calls:
            history[-1]["tool_calls"] = message.tool_calls

        if message.content:
            history[-1]["content"] = history[-1].get("content", "") + message.content

        # message.content is none for tool calls
        # when "role = tool" content would contain api call response
        if message.content and history[-1]["role"] != "tool":
            conversation[-1] = (
                conversation[-1][0],
                conversation[-1][1] + message.content,
            )
        yield "", conversation, state


def main():
    with gr.Blocks(
        theme=gr.themes.Default(
            font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "Arial", "sans-serif"]
        ),
        fill_height=True,
        css=CSS_STYLE,
    ) as demo:
        with gr.Row():
            state = gr.State({})

            with gr.Column():
                chatbot = gr.Chatbot(
                    label="Arch Chatbot",
                    elem_classes="chatbot",
                )
                textbox = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    autofocus=True,
                )

            textbox.submit(chat, [textbox, chatbot, state], [textbox, chatbot, state])

        with gr.Row():
            with gr.Accordion("See available tools", open=False):
                with gr.Column(scale=1):
                    gr.JSON(
                        value=get_prompt_targets(),
                        show_indices=False,
                        label="Available Tools",
                        elem_classes="json-container",
                    )

    demo.launch(server_name="0.0.0.0", server_port=8080, show_error=True, debug=True)


if __name__ == "__main__":
    main()
