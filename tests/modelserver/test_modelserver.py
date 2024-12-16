import json
import os
import requests
from deepdiff import DeepDiff
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MODEL_SERVER_ENDPOINT = os.getenv(
    "MODEL_SERVER_ENDPOINT", "http://localhost:51000/function_calling"
)


def test_model_server():
    expected_tool_call = {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "arguments": {"location": "Seattle, WA", "days": "10"},
        },
    }
    input = {
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
    }

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
    diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
    assert not diff
