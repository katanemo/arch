import json
from app.function_calling.hallucination_handler import HallucinationStateHandler
import pytest
import os

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


@pytest.mark.parametrize("case", test_cases)
def test_hallucination(case):
    state = HallucinationStateHandler()
    state.process_function(function_description)
    for token, logprob in zip(case["tokens"], case["logprobs"]):
        if token != "</tool_call>":
            state.current_token = token
            state.tokens.append(token)
            state.logprobs.append(logprob)
            state.process_token()
    assert state.hallucination == case["expect"]
