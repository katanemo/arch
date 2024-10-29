import json
import os
import logging
import yaml
from arch_util import get_arch_messages
import gradio as gr

from typing import List, Optional, Tuple
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

STREAM_RESPONSE = bool(os.getenv("STREAM_RESPOSE", True))

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
    # http_client=DefaultHttpxClient(headers={"accept-encoding": "*"}),
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
            stream=STREAM_RESPONSE,
        )
    except Exception as e:
        log.info(e)
        # remove last user message in case of exception
        history.pop()
        log.info("Error calling gateway API: {}".format(e))
        raise gr.Error("Error calling gateway API: {}".format(e))

    if STREAM_RESPONSE:
        response = raw_response.parse()
        history.append({"role": "assistant", "content": "", "model": ""})
        conversation.append((query, ""))
        # for gradio UI we don't want to show raw tool calls and messages from developer application
        # so we're filtering those out
        history_view = [h for h in history if h["role"] != "tool" and "content" in h]

        for chunk in response:
            print("chunk: " + str(chunk.to_dict()))
            if len(chunk.choices) > 0:
                if chunk.choices[0].delta.role:
                    # create new history item if role changes
                    # this is likely due to arch tool call and api response
                    if history[-1]["role"] != chunk.choices[0].delta.role:
                        history.append(
                            {
                                "role": chunk.choices[0].delta.role,
                                "content": chunk.choices[0].delta.content,
                                "model": chunk.model,
                                "tool_calls": chunk.choices[0].delta.tool_calls,
                            }
                        )

                history[-1]["model"] = chunk.model
                if chunk.choices[0].delta.content:
                    if not history[-1]["content"]:
                        history[-1]["content"] = ""
                    history[-1]["content"] = (
                        history[-1]["content"] + chunk.choices[0].delta.content
                    )
                if chunk.choices[0].delta.tool_calls:
                    history[-1]["tool_calls"] = chunk.choices[0].delta.tool_calls

                if history[-1]["role"] != "tool":
                    if chunk.model and chunk.choices[0].delta.content != "":
                        conversation[-1] = (
                            conversation[-1][0],
                            conversation[-1][1] + chunk.choices[0].delta.content,
                        )
                yield "", conversation, state
    else:
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

        history.append(
            {"role": "assistant", "content": content, "model": response.model}
        )

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
