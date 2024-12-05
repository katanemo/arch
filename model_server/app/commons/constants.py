# ========================== Arch-Intent Default Params ==========================
ARCH_INTENT_MODEL_ALIAS = "Arch-Intent"
ARCH_INTENT_INSTRUCTION = "Are there any tools can help?"

ARCH_INTENT_TASK_PROMPT = """
You are a helpful assistant.
"""


ARCH_INTENT_TOOL_PROMPT_TEMPLATE = """
You task is to check if there are any tools that can be used to help the last user message in conversations according to the available tools listed below.

<tools>
{tool_text}
</tools>
"""


ARCH_INTENT_FORMAT_PROMPT = """
Provide your tool assessment for ONLY THE LAST USER MESSAGE in the above conversation:
- First line must read 'Yes' or 'No'.
- If yes, a second line must include a comma-separated list of tool indexes.
"""


ARCH_INTENT_GENERATION_CONFIG = {
    "generation_params": {
        "stop_token_ids": [151645],
        "max_tokens": 1,
        "guided_choice": ["Yes", "No"],
    }
}


# ========================== Arch-Function Default Params ==========================
ARCH_FUNCTION_MODEL_ALIAS = "Arch-Function"

ARCH_FUNCTION_TASK_PROMPT = """
You are a helpful assistant.
"""


ARCH_FUNCTION_TOOL_PROMPT_TEMPLATE = """
# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{tool_text}
</tools>
"""


ARCH_FUNCTION_FORMAT_PROMPT = """
For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
"""

ARCH_FUNCTION_GENERATION_CONFIG = {
    "generation_params": {
        "temperature": 0.2,
        "top_p": 1.0,
        "top_k": 50,
        "max_tokens": 512,
        "stop_token_ids": [151645],
    },
    "prefill_params": {
        "continue_final_message": True,
        "add_generation_prompt": False,
    },
    "prefill_prefix": [
        "May",
        "Could",
        "Sure",
        "Definitely",
        "Certainly",
        "Of course",
        "Can",
    ],
}
