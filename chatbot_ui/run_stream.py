import json
import os
import logging
import yaml
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


def convert_prompt_target_to_openai_format(target):
    tool = {
        "description": target["description"],
        "parameters": {"type": "object", "properties": {}, "required": []},
    }

    if "parameters" in target:
        for param_info in target["parameters"]:
            parameter = {
                "type": param_info["type"],
                "description": param_info["description"],
            }

            for key in ["default", "format", "enum", "items", "minimum", "maximum"]:
                if key in param_info:
                    parameter[key] = param_info[key]

            tool["parameters"]["properties"][param_info["name"]] = parameter

            required = param_info.get("required", False)
            if required:
                tool["parameters"]["required"].append(param_info["name"])

    return {"name": target["name"], "info": tool}


def get_prompt_targets():
    try:
        with open(os.getenv("ARCH_CONFIG", "arch_config.yaml"), "r") as file:
            config = yaml.safe_load(file)

            available_tools = []
            for target in config["prompt_targets"]:
                if not target.get("default", False):
                    available_tools.append(
                        convert_prompt_target_to_openai_format(target)
                    )

            return {tool["name"]: tool["info"] for tool in available_tools}
    except Exception as e:
        log.info(e)
        return None


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

    history.append({"role": "assistant", "content": "", "model": ""})
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

        if history[-1]["role"] != "tool" and message.content:
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
