import json
import logging
import os
import yaml

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = logging.getLogger(__name__)


def process_stream_chunk(chunk, history):
    delta = chunk.choices[0].delta
    if delta.role and delta.role != history[-1]["role"]:
        # create new history item if role changes
        # this is likely due to arch tool call and api response
        history.append({"role": delta.role})

    history[-1]["model"] = chunk.model
    # append tool calls to history if there are any in the chunk
    if delta.tool_calls:
        history[-1]["tool_calls"] = delta.tool_calls

    if delta.content:
        # append content to the last history item
        history[-1]["content"] = history[-1].get("content", "") + delta.content
        # yield content if it is from assistant
        if history[-1]["role"] == "assistant":
            return delta.content

    return None


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
