import json
import pytest
import requests

from common import PROMPT_GATEWAY_ENDPOINT, get_data_chunks


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway(stream):
    body = {
        "messages": [
            {
                "role": "user",
                "content": "how is the weather in seattle for next 10 days",
            }
        ],
        "stream": stream,
    }
    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=body, stream=stream)
    assert response.status_code == 200
    if stream:
        chunks = get_data_chunks(response)
        assert len(chunks) > 0
        response_json = json.loads(chunks[0])
        # if its streaming we return tool call and api call in first two chunks
        assert response_json.get("model").startswith("Arch")
    else:
        response_json = response.json()
        assert response_json.get("model").startswith("gpt-4o-mini")


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway_param_gathering(stream):
    body = {
        "messages": [
            {
                "role": "user",
                "content": "how is the weather in seattle",
            }
        ],
        "stream": stream,
    }
    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=body, stream=stream)
    assert response.status_code == 200
    if stream:
        chunks = get_data_chunks(response, n=3)
        assert len(chunks) > 0
        response_json = json.loads(chunks[0])
        # if its streaming we return tool call and api call in first two chunks
        assert response_json.get("model").startswith("Arch")
    else:
        response_json = response.json()
        assert response_json.get("model").startswith("Arch")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        message = choices[0]["message"]["content"]
        assert "Could you provide the following details days" in message


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway_param_tool_call(stream):
    expected_tool_call = {
        "name": "weather_forecast",
        "arguments": {"city": "seattle", "days": 2},
    }
    body = {
        "messages": [
            {
                "role": "user",
                "content": "how is the weather in seattle",
            },
            {
                "role": "assistant",
                "content": "Could you provide the following details days ?",
                "model": "Arch-Function-1.5B",
            },
            {
                "role": "user",
                "content": "2 days",
            },
        ],
        "stream": stream,
    }
    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=body, stream=stream)
    assert response.status_code == 200
    if stream:
        chunks = get_data_chunks(response, n=3)
        assert len(chunks) > 0

        # first chunk is tool calls
        response_json = json.loads(chunks[0].lower())
        assert response_json.get("model").startswith("arch")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
        assert len(tool_calls) > 0
        tool_call = tool_calls[0]["function"]
        assert tool_call == expected_tool_call

        # second chunk is api call result
        response_json = json.loads(chunks[1])
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        role = choices[0]["delta"]["role"]
        assert role == "tool"

        # third..end chunk is summarization
        response_json = json.loads(chunks[2])
        # if its streaming we return tool call and api call in first two chunks
        assert response_json.get("model").startswith("gpt-4o-mini")

    else:
        response_json = response.json()
        assert response_json.get("model").startswith("gpt-4o-mini")


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway_default_target(stream):
    body = {
        "messages": [
            {
                "role": "user",
                "content": "hello, what can you do for me?",
            },
        ],
        "stream": stream,
    }
    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=body, stream=stream)
    assert response.status_code == 200
    if stream:
        chunks = get_data_chunks(response, n=3)
        assert len(chunks) > 0
        response_json = json.loads(chunks[0])
        assert response_json.get("model").startswith("api_server")
        response_json = json.loads(chunks[1])
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        content = choices[0]["delta"]["content"]
        assert (
            content == "I can help you with weather forecast or insurance claim details"
        )
    else:
        response_json = response.json()
        assert response_json.get("model").startswith("api_server")
