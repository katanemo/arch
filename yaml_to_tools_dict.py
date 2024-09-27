import yaml
import json
import os
from function_resolver.app.arch_handler import ArchHandler

def convert_yaml_to_tools_dict(yaml_file_path):
    with open(yaml_file_path, 'r') as file:
        yaml_content = yaml.safe_load(file)

    tools = []

    for function in yaml_content.get('prompt_targets', []):
        tool = {
            "type": "function",
            "function": {
                "name": function["name"],
                "description": function["description"],
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                    "additionalProperties": False,
                },
            }
        }

        for param in function.get("parameters", []):
            param_dict = {
                "description": param["description"] if "description" in param else ""
            }

            tool["function"]["parameters"]["properties"][param["name"]] = param_dict

            if "type" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["type"] = param["type"]

            if "enum" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["enum"] = param["enum"]

            if "default" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["default"] = param["default"]

            if "minimum" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["minimum"] = param["minimum"]

            if "maximum" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["maximum"] = param["maximum"]

            if "items" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["items"] = param["items"]

            if "format" in param:
                tool["function"]["parameters"]["properties"][param["name"]]["format"] = param["format"]

            if param.get("required", False):
                tool["function"]["parameters"]["required"].append(param["name"])

        tools.append(tool)

    return tools


if __name__ == '__main__':
    yaml_file_path = os.path.abspath('demos/employee_details_copilot/bolt_config.yaml')
    tools_dict = convert_yaml_to_tools_dict(yaml_file_path)

    print(json.dumps(tools_dict, indent=2), "\n\n\n")

    arch = ArchHandler()

    system_prompt = arch._format_system(tools_dict)

    print(system_prompt)
