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
                                            "type": "int",
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
                        "arguments": {"location": "Seattle, WA", "days": 10},
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
                                            "type": "int",
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
                        "arguments": {"location": "Seattle, WA", "days": 5},
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
                            "content": "how is the weather in chicago for next 5 days?",
                        },
                        {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_3394",
                                    "type": "function",
                                    "function": {
                                        "name": "get_current_weather",
                                        "arguments": {
                                            "location": "Chicago, IL",
                                            "days": 5,
                                        },
                                    },
                                }
                            ],
                        },
                        {"role": "tool", "content": "--", "tool_call_id": "call_3394"},
                        {
                            "role": "assistant",
                            "content": "--",
                        },
                        {
                            "role": "user",
                            "content": "how is the weather in LA for next 5 days?",
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
                                            "type": "int",
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
                        "arguments": {"location": "Los Angeles, CA", "days": 5},
                    },
                },
            },
            id="multi turn, single tool, all params passed",
        ),
        pytest.param(
            {
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "how is the weather in chicago for next 5 days?",
                        },
                        {
                            "role": "assistant",
                            "tool_calls": [
                                {
                                    "id": "call_3394",
                                    "type": "function",
                                    "function": {
                                        "name": "get_current_weather",
                                        "arguments": {"city": "Chicago, IL", "days": 5},
                                    },
                                }
                            ],
                        },
                        {"role": "tool", "content": "--", "tool_call_id": "call_3394"},
                        {
                            "role": "assistant",
                            "content": "--",
                        },
                        {
                            "role": "user",
                            "content": "how is the weather in LA?",
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
                                            "type": "int",
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
                        "arguments": {"location": "Los Angeles, CA", "days": 5},
                    },
                },
            },
            id="multi turn, single tool, infer param from context",
        ),
        pytest.param(
            {
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": "how is the weather in seattle for 2 days?",
                            "tool_call_id": "",
                        },
                        {
                            "role": "assistant",
                            "content": "",
                            "tool_call_id": "",
                            "tool_calls": [
                                {
                                    "id": "call_7134",
                                    "type": "function",
                                    "function": {
                                        "name": "get_current_weather",
                                        "arguments": {
                                            "location": "Seattle, WA",
                                            "days": 2,
                                        },
                                    },
                                }
                            ],
                        },
                        {
                            "role": "tool",
                            "content": '{"location":"Seattle, WA","temperature":[{"date":"2024-12-19","temperature":{"min":74,"max":90},"units":"Farenheit","query_time":"2024-12-19 00:14:35.853372+00:00"},{"date":"2024-12-20","temperature":{"min":79,"max":88},"units":"Farenheit","query_time":"2024-12-19 00:14:35.853402+00:00"}],"units":"Farenheit"}',
                            "tool_call_id": "",
                        },
                        {
                            "role": "assistant",
                            "content": "The weather in Seattle for the next two days is as follows:\n\n- **December 19, 2024**: The temperature will range from a minimum of 74\u00b0F to a maximum of 90\u00b0F.\n- **December 20, 2024**: The temperature will range from a minimum of 79\u00b0F to a maximum of 88\u00b0F.\n\nIt seems to be quite warm for Seattle during these dates!",
                            "tool_call_id": "",
                        },
                        {
                            "role": "user",
                            "content": "what about weather in chicago?",
                            "tool_call_id": "",
                        },
                    ],
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "get_current_weather",
                                "description": "Get current weather at a location.",
                                "parameters": {
                                    "properties": {
                                        "days": {
                                            "type": "int",
                                            "description": "the number of days for the request",
                                        },
                                        "location": {
                                            "type": "str",
                                            "description": "The location to get the weather for",
                                            "format": "city, state",
                                        },
                                    },
                                    "required": ["days", "location"],
                                },
                            },
                        },
                        {
                            "type": "function",
                            "function": {
                                "name": "default_target",
                                "description": "This is the default target for all unmatched prompts.",
                                "parameters": {"properties": {}},
                            },
                        },
                    ],
                },
                "expected": {
                    "type": "function",
                    "function": {
                        "name": "get_current_weather",
                        "arguments": {"location": "Chicago, IL", "days": 2},
                    },
                },
            },
            id="multi turn, single tool, infer param from context 2nd try",
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
