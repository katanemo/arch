import json
import pytest
from app.arch_fc.arch_fc import process_state
from app.arch_fc.common import ChatMessage, Message
# test process_state

arch_state = '[[{"key": "cafbda799879e1dce6cd3de3c3e8a40052a93addec457bda0b2f21f8c86b3424", "message": {"role": "user", "content": "how is the weather in chicago?"}, "tool_call": {"name": "weather_forecast", "arguments": {"city": "Chicago"}}, "tool_response": "{\\"city\\":\\"Chicago\\",\\"temperature\\":[{\\"date\\":\\"2024-10-05\\",\\"temperature\\":{\\"min\\":51,\\"max\\":70},\\"query_time\\":\\"2024-10-05 08:18:00.264171+00:00\\"},{\\"date\\":\\"2024-10-06\\",\\"temperature\\":{\\"min\\":77,\\"max\\":88},\\"query_time\\":\\"2024-10-05 08:18:00.264186+00:00\\"},{\\"date\\":\\"2024-10-07\\",\\"temperature\\":{\\"min\\":66,\\"max\\":84},\\"query_time\\":\\"2024-10-05 08:18:00.264190+00:00\\"},{\\"date\\":\\"2024-10-08\\",\\"temperature\\":{\\"min\\":77,\\"max\\":94},\\"query_time\\":\\"2024-10-05 08:18:00.264209+00:00\\"},{\\"date\\":\\"2024-10-09\\",\\"temperature\\":{\\"min\\":76,\\"max\\":92},\\"query_time\\":\\"2024-10-05 08:18:00.264518+00:00\\"},{\\"date\\":\\"2024-10-10\\",\\"temperature\\":{\\"min\\":56,\\"max\\":68},\\"query_time\\":\\"2024-10-05 08:18:00.264550+00:00\\"},{\\"date\\":\\"2024-10-11\\",\\"temperature\\":{\\"min\\":73,\\"max\\":88},\\"query_time\\":\\"2024-10-05 08:18:00.264559+00:00\\"}],\\"unit\\":\\"F\\"}"}]]'


def test_process_state():
  history = []
  history.append(Message(role="user", content="how is the weather in chicago?"))
  updated_history = process_state(arch_state, history)
  print(json.dumps(updated_history, indent=2))

if __name__ == "__main__":
    pytest.main()
