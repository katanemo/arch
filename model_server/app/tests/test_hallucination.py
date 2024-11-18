import json
from app.function_calling.hallucination_handler import hallucination_detect
import pytest


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

parameter_names = {}
for func in function_description:
    func_name = func["name"]
    parameters = func["parameters"]["properties"]
    parameter_names[func_name] = list(parameters.keys())

with open("test_cases.json") as f:
    test_cases = json.load(f)


@pytest.mark.parametrize("case", test_cases)
def test_hallucination(case):
    current_state = {
        "state": "start",
        "tool_call": "",
        "entropy": [],
        "varentropy": [],
        "logprobs": [],
        "tokens": [],
        "content": "",
        "hallucination": False,
        "parameter_names": parameter_names,
        "function_description": function_description,
    }
    for token_content, logprobs in zip(case["tokens"], case["logprobs"]):
        result = hallucination_detect(token_content, logprobs, current_state, 0.7, 4)
    assert result == case["expect"]
