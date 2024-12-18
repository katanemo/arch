import json
import os
import pytest
import requests
from deepdiff import DeepDiff
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MODEL_SERVER_ENDPOINT = os.getenv(
    "MODEL_SERVER_ENDPOINT", "http://localhost:51000/function_calling"
)


@pytest.mark.parametrize(
    "test_data",
    [
        pytest.param(
            {
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "what is the weather forecast for seattle in the next 10 days?",
                        }
                    ],
                    "tools": [
                        {
                            "id": "weather-112",
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
                                        "days": {
                                            "type": "str",
                                            "description": "the number of days for the request.",
                                        },
                                    },
                                    "required": ["location", "days"],
                                },
                            },
                        }
                    ],
                },
                "expected": {
                    "type": "function",
                    "function": {
                        "name": "get_current_weather",
                        "arguments": {"location": "Seattle, WA", "days": "10"},
                    },
                },
            },
            id="single turn, single tool, all parameters",
        ),
        pytest.param(
            {
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "what is the weather in Seattle?",
                        },
                        {
                            "role": "assistant",
                            "content": "May I know the location and number of days you want to get the weather for?",
                            "model": "Arch-Function",
                        },
                        {
                            "role": "user",
                            "content": "5 days",
                        },
                    ],
                    "tools": [
                        {
                            "id": "weather-112",
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
                                        "days": {
                                            "type": "str",
                                            "description": "the number of days for the request.",
                                        },
                                    },
                                    "required": ["location", "days"],
                                },
                            },
                        }
                    ],
                },
                "expected": {
                    "type": "function",
                    "function": {
                        "name": "get_current_weather",
                        "arguments": {"location": "Seattle, WA", "days": "5"},
                    },
                },
            },
            id="single turn, single tool, param gathering",
        ),
        pytest.param(
            {
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "what is the weather in Seattle?",
                        },
                        {
                            "role": "assistant",
                            "content": "May I know the location and number of days you want to get the weather for?",
                            "model": "Arch-Function",
                        },
                        {
                            "role": "user",
                            "content": "5 days",
                        },
                        {
                            "role": "assistant",
                            "content": "Based on the weather data, the weather in Seattle for the next 5 days between 100f and 95f.",
                        },
                        {
                            "role": "tool",
                            "content": "seattle wa, 2014-10-10, 100f\n seattle wa, 2014-10-11, 87f\n seattle wa, 2014-10-12, 80f\n seattle wa, 2014-10-13, 90f\n seattle wa, 2014-10-14, 95f",
                        },
                        {
                            "role": "user",
                            "content": "What about LA?",
                        },
                    ],
                    "tools": [
                        {
                            "id": "weather-112",
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
                                        "days": {
                                            "type": "str",
                                            "description": "the number of days for the request.",
                                        },
                                    },
                                    "required": ["location", "days"],
                                },
                            },
                        }
                    ],
                },
                "expected": {
                    "type": "function",
                    "function": {
                        "name": "get_current_weather",
                        "arguments": {"location": "Los Angeles, WA", "days": "5"},
                    },
                },
            },
            id="multi turn, single tool",
        ),
    ],
)
def test_model_server(test_data):
    input = test_data["input"]
    expected = test_data["expected"]

    response = requests.post(MODEL_SERVER_ENDPOINT, json=input)
    assert response.status_code == 200
    print(json.dumps(response.json()))
    # ensure that response is json
    assert response.headers["content-type"] == "application/json"
    response_json = response.json()
    assert response_json
    choices = response_json.get("choices", [])
    assert len(choices) == 1
    choice = choices[0]
    assert "message" in choice
    message = choice["message"]
    assert "tool_calls" in message
    tool_calls = message["tool_calls"]
    assert len(tool_calls) == 1
    tool_call = tool_calls[0]
    assert "id" in tool_call
    del tool_call["id"]
    # ensure that the tool call matches the expected tool call
    diff = DeepDiff(tool_call, expected, ignore_string_case=True)
    assert not diff
