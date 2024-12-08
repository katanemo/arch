from src.commons.globals import handler_map
from src.core.function_calling import Message


test_input_history = [
    {"role": "user", "content": "how is the weather in chicago for next 5 days?"},
    {
        "role": "assistant",
        "model": "Arch-Function",
        "tool_calls": [
            {
                "id": "call_3394",
                "type": "function",
                "function": {
                    "name": "weather_forecast",
                    "arguments": {"city": "Chicago", "days": 5},
                },
            }
        ],
    },
    {"role": "tool", "content": "--", "tool_call_id": "call_3394"},
    {"role": "assistant", "content": "--", "model": "gpt-3.5-turbo-0125"},
    {"role": "user", "content": "how is the weather in chicago for next 5 days?"},
    {
        "role": "assistant",
        "tool_calls": [
            {
                "id": "call_5306",
                "type": "function",
                "function": {
                    "name": "weather_forecast",
                    "arguments": {"city": "Chicago", "days": 5},
                },
            }
        ],
    },
    {"role": "tool", "content": "--", "tool_call_id": "call_5306"},
]


def test_update_fc_history():
    message_history = []

    for h in test_input_history:
        message_history.append(Message(**h))

    updated_history = handler_map["Arch-Function"]._process_messages(message_history)
    assert len(updated_history) == 7
    # ensure that tool role does not exist anymore
    assert all([h["role"] != "tool" for h in updated_history])
