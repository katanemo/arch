import json
import pytest
import requests
from deepdiff import DeepDiff
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

from pytest_httpserver import HTTPServer, RequestMatcher


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return ("0.0.0.0", 51001)


from common import (
    PROMPT_GATEWAY_ENDPOINT,
    TEST_CASE_FIXTURES,
    get_arch_messages,
)


def test_prompt_gateway(httpserver: HTTPServer):
    simple_fixture = TEST_CASE_FIXTURES["SIMPLE"]
    input = simple_fixture["input"]
    model_server_response = simple_fixture["model_server_response"]
    api_server_response = simple_fixture["api_server_response"]

    expected_tool_call = {
        "name": "get_current_weather",
        "arguments": {"location": "seattle, wa", "days": "2"},
    }

    # setup mock response from model_server
    httpserver.expect_request("/function_calling").respond_with_data(
        json.dumps(model_server_response)
    )

    # setup mock response from api_server
    httpserver.expect_request("/weather").respond_with_data(
        json.dumps(api_server_response)
    )

    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=input)
    assert response.status_code == 200

    httpserver.assert_request_made(
        RequestMatcher(uri="/function_calling", method="POST")
    )
    httpserver.assert_request_made(RequestMatcher(uri="/weather", method="POST"))

    response_json = response.json()
    assert response_json.get("model").startswith("gpt-4o-mini")
    choices = response_json.get("choices", [])
    assert len(choices) > 0
    assert "message" in choices[0]
    assistant_message = choices[0]["message"]
    assert "role" in assistant_message
    assert assistant_message["role"] == "assistant"
    assert "content" in assistant_message
    assert "weather" in assistant_message["content"]
    # now verify arch_messages (tool call and api response) that are sent as response metadata
    arch_messages = get_arch_messages(response_json)
    assert len(arch_messages) == 2
    tool_calls_message = arch_messages[0]
    tool_calls = tool_calls_message.get("tool_calls", [])
    assert len(tool_calls) > 0
    tool_call = tool_calls[0]["function"]
    diff = DeepDiff(tool_call, expected_tool_call, ignore_string_case=True)
    assert not diff


def test_prompt_gateway_api_server_404(httpserver: HTTPServer):
    simple_fixture = TEST_CASE_FIXTURES["SIMPLE"]
    input = simple_fixture["input"]
    model_server_response = simple_fixture["model_server_response"]

    # setup mock response from model_server
    httpserver.expect_request("/function_calling").respond_with_data(
        json.dumps(model_server_response)
    )

    # setup mock response from model_server
    httpserver.expect_request("/weather").respond_with_data(status=404)

    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=input)
    assert response.status_code == 404

    httpserver.assert_request_made(
        RequestMatcher(uri="/function_calling", method="POST")
    )

    httpserver.assert_request_made(RequestMatcher(uri="/weather", method="POST"))
    assert (
        response.text
        == "upstream application error host=weather_forecast_service, path=/weather, status=404, body="
    )


def test_prompt_gateway_model_server_500(httpserver: HTTPServer):
    simple_fixture = TEST_CASE_FIXTURES["SIMPLE"]
    input = simple_fixture["input"]

    # setup mock response from model_server
    httpserver.expect_request("/function_calling").respond_with_data(status=500)

    response = requests.post(PROMPT_GATEWAY_ENDPOINT, json=input)
    assert response.status_code == 500

    httpserver.assert_request_made(
        RequestMatcher(uri="/function_calling", method="POST")
    )

    assert (
        response.text
        == "upstream application error host=arch_internal, path=/function_calling, status=500, body="
    )
