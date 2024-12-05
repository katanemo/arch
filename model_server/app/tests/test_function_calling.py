import json
import pytest

from fastapi import Response
from unittest.mock import AsyncMock, MagicMock, patch
from app.commons.globals import handler_map
from app.model_handler.base_handler import (
    Message,
    ChatMessage,
    ChatCompletionResponse,
)


def sample_messages():
    # Ensure fields are explicitly set with valid data or empty values
    return [
        Message(role="user", content="Hello!", tool_calls=[], tool_call_id=""),
        Message(
            role="assistant",
            content="",
            tool_calls=[{"function": {"name": "sample_tool"}}],
            tool_call_id="sample_id",
        ),
        Message(
            role="tool", content="Response from tool", tool_calls=[], tool_call_id=""
        ),
    ]


def sample_request(sample_messages):
    return ChatMessage(
        messages=sample_messages,
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "sample_tool",
                    "description": "A sample tool",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            }
        ],
    )


@patch("app.commons.globals.handler_map")
def test_process_messages(mock_hanlder):
    messages = sample_messages()
    processed = handler_map["Arch-Function"]._process_messages(messages)

    assert len(processed) == 3
    assert processed[0] == {"role": "user", "content": "Hello!"}
    assert processed[1] == {
        "role": "assistant",
        "content": '<tool_call>\n{"name": "sample_tool"}\n</tool_call>',
    }
    assert processed[2] == {
        "role": "user",
        "content": f"<tool_response>\n{json.dumps('Response from tool')}\n</tool_response>",
    }


# [TODO] Review: Add tests for both `ArchIntentHandler` and `ArchFunctionHandler`. The following test may be outdated.


# [TODO] Review: Update the following test
@patch("app.commons.constants.arch_function_client")
@patch("app.commons.constants.arch_function_hanlder")
@pytest.mark.asyncio
async def test_chat_completion(mock_hanlder, mock_client):
    # Mock the model list return for client
    mock_client.models.list.return_value = MagicMock(
        data=[MagicMock(id="sample_model")]
    )
    request = sample_request(sample_messages())
    # Simulate stream response as list of tokens
    mock_response = AsyncMock()
    mock_response.__aiter__.return_value = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hi there!"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=""))]),  # end of stream
    ]
    mock_client.chat.completions.create.return_value = mock_response

    # Mock the tool formatter
    mock_hanlder._format_system.return_value = "<formatted_tools>"

    response = Response()
    chat_response = await chat_completion(request, response)

    assert isinstance(chat_response, ChatCompletionResponse)
    assert chat_response.choices[0].message.content is not None

    first_call_args = mock_client.chat.completions.create.call_args_list[0][1]
    assert first_call_args["stream"] == True
    assert "model" in first_call_args
    assert first_call_args["messages"][0]["content"] == "<formatted_tools>"

    # Check that the arguments for the second call to 'create' include the pre-fill completion
    second_call_args = mock_client.chat.completions.create.call_args_list[1][1]
    assert second_call_args["stream"] == False
    assert "model" in second_call_args
    assert second_call_args["messages"][-1]["content"] in const.PREFILL_LIST
