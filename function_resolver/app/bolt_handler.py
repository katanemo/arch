import json
from typing import Any, Dict, List


SYSTEM_PROMPT = """
[BEGIN OF TASK INSTRUCTION]
You are a function calling assistant with access to the following tools. You task is to assist users as best as you can.
For each user query, you may need to call one or more functions to to better generate responses.
If none of the functions are relevant, you should point it out.
If the given query lacks the parameters required by the function, you should ask users for clarification.
The users may execute functions and return results as `Observation` to you. In the case, you MUST generate responses by summarizing it.
[END OF TASK INSTRUCTION]
""".strip()

TOOL_PROMPT = """
[BEGIN OF AVAILABLE TOOLS]
{tool_text}
[END OF AVAILABLE TOOLS]
""".strip()

FORMAT_PROMPT = """
[BEGIN OF FORMAT INSTRUCTION]
You MUST use the following JSON format if using tools.
The example format is as follows. DO NOT use this format if no function call is needed.
```
{
  "tool_calls": [
    {"name": "func_name1", "arguments": {"argument1": "value1", "argument2": "value2"}},
    ... (more tool calls as required)
  ]
}
```
[END OF FORMAT INSTRUCTION]
""".strip()


class BoltHandler:
    def _format_system(self, tools: List[Dict[str, Any]]):
        tool_text = self._format_tools(tools=tools)
        return (
            SYSTEM_PROMPT
            + "\n\n"
            + TOOL_PROMPT.format(tool_text=tool_text)
            + "\n\n"
            + FORMAT_PROMPT
            + "\n"
        )

    def _format_tools(self, tools: List[Dict[str, Any]]):
        TOOL_DESC = "> Tool Name: {name}\nTool Description: {desc}\nTool Args:\n{args}"

        tool_text = []
        for tool in tools:
            param_text = self.get_param_text(tool.parameters)
            tool_text.append(
                TOOL_DESC.format(
                    name=tool.name, desc=tool.description, args=param_text
                )
            )

        return "\n".join(tool_text)

    def extract_tools(self, content, executable=False):
        # retrieve `tool_calls` from model responses
        try:
            content_json = json.loads(content)
        except Exception:
            fixed_content = self.fix_json_string(content)
            try:
                content_json = json.loads(fixed_content)
            except json.JSONDecodeError:
                return content

        if isinstance(content_json, list):
            tool_calls = content_json
        elif isinstance(content_json, dict):
            tool_calls = content_json.get("tool_calls", [])
        else:
            tool_calls = []

        if not isinstance(tool_calls, list):
            return content

        # process and extract tools from `tool_calls`
        extracted = []

        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                try:
                    if not executable:
                        extracted.append({tool_call["name"]: tool_call["arguments"]})
                    else:
                        name, arguments = (
                            tool_call.get("name", ""),
                            tool_call.get("arguments", {}),
                        )

                        for key, value in arguments.items():
                            if value == "False" or value == "false":
                                arguments[key] = False
                            elif value == "True" or value == "true":
                                arguments[key] = True

                        args_str = ", ".join(
                            [f"{key}={repr(value)}" for key, value in arguments.items()]
                        )

                        extracted.append(f"{name}({args_str})")

                except Exception:
                    continue

        return extracted

    def get_param_text(self, parameter_dict, prefix=""):
        param_text = ""

        for name, param in parameter_dict["properties"].items():
            param_type = param.get("type", "")

            required, default, param_format, properties, enum, items = (
                "",
                "",
                "",
                "",
                "",
                "",
            )

            if name in parameter_dict.get("required", []):
                required = ", required"

            required_param = parameter_dict.get("required", [])

            if isinstance(required_param, bool):
                required = ", required" if required_param else ""
            elif isinstance(required_param, list) and name in required_param:
                required = ", required"
            else:
                required = ", optional"

            default_param = param.get("default", None)
            if default_param:
                default = f", default: {default_param}"

            format_in = param.get("format", None)
            if format_in:
                param_format = f", format: {format_in}"

            desc = param.get("description", "")

            if "properties" in param:
                arg_properties = self.get_param_text(param, prefix + "  ")
                properties += "with the properties:\n{}".format(arg_properties)

            enum_param = param.get("enum", None)
            if enum_param:
                enum = "should be one of [{}]".format(", ".join(enum_param))

            item_param = param.get("items", None)
            if item_param:
                item_type = item_param.get("type", None)
                if item_type:
                    items += "each item should be the {} type ".format(item_type)

                item_properties = item_param.get("properties", None)
                if item_properties:
                    item_properties = self.get_param_text(item_param, prefix + "  ")
                    items += "with the properties:\n{}".format(item_properties)

            illustration = ", ".join(
                [x for x in [desc, properties, enum, items] if len(x)]
            )

            param_text += (
                prefix
                + "- {name} ({param_type}{required}{param_format}{default}): {illustration}\n".format(
                    name=name,
                    param_type=param_type,
                    required=required,
                    param_format=param_format,
                    default=default,
                    illustration=illustration,
                )
            )

        return param_text

    def fix_json_string(self, json_str):
        # Remove any leading or trailing whitespace or newline characters
        json_str = json_str.strip()

        # Stack to keep track of brackets
        stack = []

        # Clean string to collect valid characters
        fixed_str = ""

        # Dictionary for matching brackets
        matching_bracket = {")": "(", "}": "{", "]": "["}

        # Dictionary for the opposite of matching_bracket
        opening_bracket = {v: k for k, v in matching_bracket.items()}

        for char in json_str:
            if char in "{[(":
                stack.append(char)
                fixed_str += char
            elif char in "}])":
                if stack and stack[-1] == matching_bracket[char]:
                    stack.pop()
                    fixed_str += char
                else:
                    # Ignore the unmatched closing brackets
                    continue
            else:
                fixed_str += char

        # If there are unmatched opening brackets left in the stack, add corresponding closing brackets
        while stack:
            unmatched_opening = stack.pop()
            fixed_str += opening_bracket[unmatched_opening]

        # Attempt to parse the corrected string to ensure it’s valid JSON
        return fixed_str
