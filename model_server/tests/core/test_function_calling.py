import os

from src.commons.globals import handler_map
from src.core.model_utils import ChatMessage, Message
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.main import app
from src.commons.globals import handler_map

# define function
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

# get_data class return request, intent, hallucination, parameter_gathering


def get_hallucination_data_complex():
    # Create instances of the Message class
    message1 = Message(role="user", content="How is the weather in Seattle?")
    message2 = Message(
        role="assistant", content="Can you specify the unit you want the weather in?"
    )
    message3 = Message(role="user", content="In celcius please!")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1, message2, message3], tools=tools)

    return req, True, True, True


def get_hallucination_data_easy():
    # Create instances of the Message class
    message1 = Message(role="user", content="How is the weather in Seattle?")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    # model will hallucinate
    return req, True, True, True


def get_hallucination_data_medium():
    # Create instances of the Message class
    message1 = Message(role="user", content="How is the weather in?")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    # first token will not be tool call
    return req, True, True, True


def get_complete_data_2():
    # Create instances of the Message class
    message1 = Message(
        role="user",
        content="what is the weather forecast for seattle in the next 10 days?",
    )

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    return req, True, False, False


def get_complete_data():
    # Create instances of the Message class
    message1 = Message(role="user", content="How is the weather in Seattle in 7 days?")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    return req, True, False, False


def get_irrelevant_data():
    # Create instances of the Message class
    message1 = Message(role="user", content="What is 1+1?")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    return req, False, False, False


def get_greeting_data():
    # Create instances of the Message class
    message1 = Message(role="user", content="Hello how are you?")

    # Create a list of tools
    tools = [get_weather_api]

    # Create an instance of the ChatMessage class
    req = ChatMessage(messages=[message1], tools=tools)

    return req, False, False, False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "get_data_func",
    [
        get_hallucination_data_complex,
        get_hallucination_data_easy,
        get_complete_data,
        get_irrelevant_data,
        get_complete_data_2,
    ],
)
async def test_function_calling(get_data_func):
    req, intent, hallucination, parameter_gathering = get_data_func()

    intent_response = await handler_map["Arch-Intent"].chat_completion(req)

    assert handler_map["Arch-Intent"].detect_intent(intent_response) == intent

    if intent:
        function_calling_response = await handler_map["Arch-Function"].chat_completion(
            req
        )
        assert handler_map["Arch-Function"].hallu_handler.hallucination == hallucination
        response_txt = function_calling_response.choices[0].message.content

        if parameter_gathering:
            prefill_prefix = handler_map["Arch-Function"].prefill_prefix
            assert any(
                response_txt.startswith(prefix) for prefix in prefill_prefix
            ), f"Response '{response_txt}' does not start with any of the prefixes: {prefill_prefix}"
