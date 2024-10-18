from typing import List
import pytest
import json
from app.function_calling.model_utils import Message, process_messages

test_input_history = """
[
    {
      "role": "user",
      "content": "how is the weather in chicago for next 5 days?"
    },
    {
      "role": "assistant",
      "model": "Arch-Function-1.5B",
      "tool_calls": [
        {
          "id": "call_3394",
          "type": "function",
          "function": {
            "name": "weather_forecast",
            "arguments": { "city": "Chicago", "days": 5 }
          }
        }
      ]
    },
    {
      "role": "tool",
      "content": "--",
      "tool_call_id": "call_3394"
    },
    {
      "role": "assistant",
      "content": "--",
      "model": "gpt-3.5-turbo-0125"
    },
    {
      "role": "user",
      "content": "how is the weather in chicago for next 5 days?"
    },
    {
      "role": "assistant",
      "tool_calls": [
        {
          "id": "call_5306",
          "type": "function",
          "function": {
            "name": "weather_forecast",
            "arguments": { "city": "Chicago", "days": 5 }
          }
        }
      ]
    }
  ]
  """


def test_update_fc_history():
    history = json.loads(test_input_history)
    message_history = []
    for h in history:
        message_history.append(Message(**h))

    updated_history = process_messages(message_history)
    assert len(updated_history) == 6
    # ensure that tool role does not exist anymore
    assert all([h["role"] != "tool" for h in updated_history])
