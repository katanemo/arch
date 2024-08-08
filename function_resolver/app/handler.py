import json
import re
from typing import Any, Dict, List, Optional, Tuple
from common import Message

import torch
from template import KFCTemplate
from transformers import PreTrainedTokenizer


SYSTEM_PROMPT = """<|im_start|>system
You are a function calling AI assistant. You have access to the following tools and you should focus on serving the user's needs as best you can. You may call one or more functions to assist with the user query. However, you should:
- ONLY use the tools available to you.
- DO NOT ANSWER UNRELATED QUESTIONS.
- return a JSON object with function name and arguments for each function call.

{tool_text}

Use the following format if using tools:

Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can be repeated zero or more times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question<|im_end|>
"""


TOOL_DESC = (
    "{name}: Call this tool to interact with the {name} API. "
    "What is the {name} API useful for? {description} Parameters: {parameters}"
)


class KFCHandler:
    def __init__(self, model, temperature=0.01, top_p=0.2, top_k=50, max_new_tokens=512) -> None:
        self.model = model

        self.gen_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "max_new_tokens": max_new_tokens,
        }

    def generate(
        self,
        tokenizer: "PreTrainedTokenizer",
        template: "KFCTemplate",
        messages: List[List[int]],
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        paired_messages = messages + [Message(role="assistant", content="")]

        prompt_ids, _ = template.encode_oneturn(tokenizer=tokenizer, messages=paired_messages, tools=tools)

        print(f"device = {self.model.device}")
        model_inputs = torch.tensor([prompt_ids], device=self.model.device)
        attention_mask = torch.ones_like(model_inputs, dtype=torch.bool)

        decoded_input = tokenizer.batch_decode(model_inputs, skip_special_tokens=False)[0]
        print(f"[Model Input]\n{decoded_input}")

        generate_output = self.model.generate(
            model_inputs, attention_mask=attention_mask, **self.gen_kwargs
        )

        response_ids = generate_output[:, len(prompt_ids) :]
        response = tokenizer.batch_decode(response_ids, skip_special_tokens=True, clean_up_tokenization_spaces=True)[0]

        return response

    def extract_tools(self, content: str):
        regex = re.compile(
            r"Action:\s*([a-zA-Z0-9_\.]+)\s*Action Input:\s*(.+?)(?=\s*Action:|\s*$|\n)",
            re.DOTALL,
        )

        action_match: List[Tuple[str, str]] = re.findall(regex, content)

        if not action_match:
            return content

        extracted_tools = []
        for match in action_match:
            tool_name = match[0].strip()
            tool_input = match[1].strip().strip('"').strip("```")
            try:
                arguments = json.loads(tool_input)
                extracted_tools.append({"name": tool_name, "arguments": arguments})
            except json.JSONDecodeError:
                pass

        return extracted_tools

    def _format_system(self, tools: List[Dict[str, Any]]):
        tool_text, tool_names = self._format_tools(tools)
        return [SYSTEM_PROMPT.format(tool_text=tool_text, tool_names=tool_names)]

    def _format_user(self, content):
        return [f"<|im_start|>user\n{content}<|im_end|>\n<|im_start|>assistant\n"]

    def _format_assistant(self, content):
        return [f"{content}<|im_end|>\n"]

    def _format_function(self, content):
        return [f"{content}\n"]

    def _format_observation(self, content):
        return [f"{content}\n"]

    def _format_tools(self, tools: List[Dict[str, Any]]) -> str:
        tool_text, tool_names = [], []
        # ===================================================================================================
        for tool in tools:
            parameters = []
            print(tool.parameters)
            print(tool.parameters["properties"])
            for name, param in tool.parameters["properties"].items():
                parameters.append(
                    {
                        "name": name,
                        "type": param.get("type", ""),
                        "description": param.get("description", ""),
                        "required": param.get("required", False),
                    }
                )

                # required = tool.parameters.get("required", [])

                # if isinstance(required, bool):
                #     parameters[-1]["required"] = required
                # elif isinstance(required, list) and name in required:
                #     parameters[-1]["required"] = True
                # else:
                #     parameters[-1]["required"] = False

                if param.get("default", None):
                    parameters[-1]["default"] = param["default"]

                if param.get("enum", None):
                    parameters[-1]["enum"] = param["enum"]

                if param.get("items", None):
                    parameters[-1]["items"] = param["items"].get("type", "")

            tool_text.append(
                TOOL_DESC.format(
                    name=tool.name, description=tool.description, parameters=json.dumps(parameters)
                )
            )

            tool_names.append(tool.name)
        # ===================================================================================================
        tool_text = "\n\n".join(tool_text)
        tool_names = ", ".join(tool_names)

        return tool_text, tool_names
