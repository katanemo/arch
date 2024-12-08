import json
import pytest
import os


from src.core.hallucination_handler import HallucinationStateHandler


# Get the directory of the current file
current_dir = os.path.dirname(__file__)

# Construct the full path to the JSON file
json_file_path = os.path.join(current_dir, "test_cases.json")

with open(json_file_path) as f:
    test_cases = json.load(f)

get_weather_api = {
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get current weather at a location.",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "str",
                    "description": "The location to get the weather for",
                    "format": "City, State",
                },
                "unit": {
                    "type": "str",
                    "description": "The unit to return the weather in.",
                    "enum": ["celsius", "fahrenheit"],
                    "default": "celsius",
                },
                "days": {
                    "type": "str",
                    "description": "the number of days for the request.",
                },
            },
            "required": ["location", "days"],
        },
    },
}
function_description = get_weather_api["function"]
if type(function_description) != list:
    function_description = [get_weather_api["function"]]


# [TODO] Review: update the following code
@pytest.mark.parametrize("case", test_cases)
def test_hallucination(case):
    state = HallucinationStateHandler(
        response_iterator=None, function=function_description
    )
    for token, logprob in zip(case["tokens"], case["logprobs"]):
        if token != "</tool_call>":
            state.append_and_check_token_hallucination(token, logprob)
            if state.hallucination:
                break
    assert state.hallucination == case["expect"]


# [TODO] Review: update the following code
@pytest.mark.parametrize("is_hallucinate_sample", [True, False])
def test_hallucination_prompt(is_hallucinate_sample):
    TASK_PROMPT = """
    You are a helpful assistant.
    """.strip()

    TOOL_PROMPT = """
    # Tools

    You may call one or more functions to assist with the user query.

    You are provided with function signatures within <tools></tools> XML tags:
    <tools>
    {tool_text}
    </tools>
    """.strip()

    FORMAT_PROMPT = """
    For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
    <tool_call>
    {"name": <function-name>, "arguments": <args-json-object>}
    </tool_call>
    """.strip()

    def convert_tools(tools):
        return "\n".join([json.dumps(tool) for tool in tools])

    def format_prompt(tools):
        tool_text = convert_tools(tools)

        return (
            TASK_PROMPT
            + "\n\n"
            + TOOL_PROMPT.format(tool_text=tool_text)
            + "\n\n"
            + FORMAT_PROMPT
            + "\n"
        )

    openai_format_tools = [get_weather_api]

    system_prompt = format_prompt(openai_format_tools)

    from openai import OpenAI

    client = OpenAI(base_url="https://api.fc.archgw.com/v1", api_key="EMPTY")

    # List models API
    model = client.models.list().data[0].id
    assert model == "Arch-Function"
    if not is_hallucinate_sample:
        messages = [
            {"role": "system", "content": system_prompt},
            # {"role": "user", "content": "can you help me check weather?"},
            {"role": "user", "content": "How is the weather in Seattle in 7 days?"},
            # {"role": "assistant", "content": "Of course!"},
            # {"role": "user", "content": "Seattle please"}
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            # {"role": "user", "content": "can you help me check weather?"},
            {"role": "user", "content": "How is the weather in Seattle in days?"},
            # {"role": "assistant", "content": "Of course!"},
            # {"role": "user", "content": "Seattle please"}
        ]

    extra_body = {
        "temperature": 0.6,
        "top_p": 1.0,
        "top_k": 50,
        # "continue_final_message": True,
        # "add_generation_prompt": False,
        "logprobs": True,
        "top_logprobs": 10,
    }

    resp = client.chat.completions.create(
        model="Arch-Function", messages=messages, extra_body=extra_body, stream=True
    )

    hallu = HallucinationStateHandler(
        response_iterator=resp, function=function_description
    )

    for token in hallu:
        assert len(hallu.tokens) >= 0
    assert hallu.hallucination == is_hallucinate_sample
