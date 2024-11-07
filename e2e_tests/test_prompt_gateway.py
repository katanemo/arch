import json
import pytest
import requests
from deepdiff import DeepDiff

from common import (
    PROMPT_GATEWAY_ENDPOINT,
    PREFILL_LIST,
    get_arch_messages,
    get_data_chunks,
)


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway(stream):
    expected_tool_call = {
        "name": "weather_forecast",
        "arguments": {"city": "seattle", "days": 10},
    }

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
        chunks = get_data_chunks(response, n=20)
        assert len(chunks) > 2

        # first chunk is tool calls (role = assistant)
        response_json = json.loads(chunks[0])
        assert response_json.get("model").startswith("Arch")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "assistant"
        tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
        assert len(tool_calls) > 0
        tool_call = tool_calls[0]["function"]
        diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
        assert not diff

        # second chunk is api call result (role = tool)
        response_json = json.loads(chunks[1])
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "tool"

        # third..end chunk is summarization (role = assistant)
        response_json = json.loads(chunks[2])
        assert response_json.get("model").startswith("gpt-4o-mini")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "assistant"

    else:
        response_json = response.json()
        assert response_json.get("model").startswith("gpt-4o-mini")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["message"]
        assert choices[0]["message"]["role"] == "assistant"
        # now verify arch_messages (tool call and api response) that are sent as response metadata
        arch_messages = get_arch_messages(response_json)
        assert len(arch_messages) == 2
        tool_calls_message = arch_messages[0]
        tool_calls = tool_calls_message.get("tool_calls", [])
        assert len(tool_calls) > 0
        tool_call = tool_calls[0]["function"]
        diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
        assert not diff


@pytest.mark.parametrize("stream", [True, False])
def test_prompt_gateway_arch_direct_response(stream):
    body = {
        "messages": [
            {
                "role": "user",
                "content": "how is the weather",
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
        # make sure arch responded directly
        assert response_json.get("model").startswith("Arch")
        # and tool call is null
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
        assert len(tool_calls) == 0
        response_json = json.loads(chunks[1])
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        message = choices[0]["delta"]["content"]
    else:
        response_json = response.json()
        assert response_json.get("model").startswith("Arch")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        message = choices[0]["message"]["content"]

        assert "Could you provide the following details days" not in message
    assert any(
        message.startswith(word) for word in PREFILL_LIST
    ), f"Expected assistant message to start with one of {PREFILL_LIST}, but got '{assistant_message}'"


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
        # make sure arch responded directly
        assert response_json.get("model").startswith("Arch")
        # and tool call is null
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
        assert len(tool_calls) == 0
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
        chunks = get_data_chunks(response, n=20)
        assert len(chunks) > 2

        # first chunk is tool calls (role = assistant)
        response_json = json.loads(chunks[0])
        assert response_json.get("model").startswith("Arch")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "assistant"
        tool_calls = choices[0].get("delta", {}).get("tool_calls", [])
        assert len(tool_calls) > 0
        tool_call = tool_calls[0]["function"]
        diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
        assert not diff

        # second chunk is api call result (role = tool)
        response_json = json.loads(chunks[1])
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "tool"

        # third..end chunk is summarization (role = assistant)
        response_json = json.loads(chunks[2])
        assert response_json.get("model").startswith("gpt-4o-mini")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["delta"]
        role = choices[0]["delta"]["role"]
        assert role == "assistant"

    else:
        response_json = response.json()
        assert response_json.get("model").startswith("gpt-4o-mini")
        choices = response_json.get("choices", [])
        assert len(choices) > 0
        assert "role" in choices[0]["message"]
        assert choices[0]["message"]["role"] == "assistant"
        # now verify arch_messages (tool call and api response) that are sent as response metadata
        arch_messages = get_arch_messages(response_json)
        assert len(arch_messages) == 2
        tool_calls_message = arch_messages[0]
        tool_calls = tool_calls_message.get("tool_calls", [])
        assert len(tool_calls) > 0
        tool_call = tool_calls[0]["function"]
        diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
        assert not diff


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
        assert len(response_json.get("choices", [])) > 0
        assert response_json.get("choices")[0]["delta"]["role"] == "assistant"

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
        assert len(response_json.get("choices")) > 0
        assert response_json.get("choices")[0]["message"]["role"] == "assistant"
        assert (
            response_json.get("choices")[0]["message"]["content"]
            == "I can help you with weather forecast or insurance claim details"
        )
