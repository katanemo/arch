import pytest
from app.arch_fc.arch_fc import process_state
from app.arch_fc.common import ChatMessage, Message
# test process_state

arch_state = '[[{"key":"2e93258626cc49038b8a39d6e461b1af32daef6900b6b3bc533ccd2ecf6f5bde","message":{"role":"user","content":"how is the weather in chicago?"},"tool_call":{"name":"weather_forecast","arguments":{"city":"Chicago"}},"tool_response":"{\\"city\\":\\"Chicago\\",\\"temperature\\":[{\\"date\\":\\"2024-10-04\\",\\"temperature\\":{\\"min\\":54,\\"max\\":59},\\"query_time\\":\\"2024-10-04 19:54:13.305059+00:00\\"},{\\"date\\":\\"2024-10-05\\",\\"temperature\\":{\\"min\\":87,\\"max\\":103},\\"query_time\\":\\"2024-10-04 19:54:13.305075+00:00\\"},{\\"date\\":\\"2024-10-06\\",\\"temperature\\":{\\"min\\":61,\\"max\\":69},\\"query_time\\":\\"2024-10-04 19:54:13.305091+00:00\\"},{\\"date\\":\\"2024-10-07\\",\\"temperature\\":{\\"min\\":79,\\"max\\":85},\\"query_time\\":\\"2024-10-04 19:54:13.305104+00:00\\"},{\\"date\\":\\"2024-10-08\\",\\"temperature\\":{\\"min\\":55,\\"max\\":61},\\"query_time\\":\\"2024-10-04 19:54:13.305121+00:00\\"},{\\"date\\":\\"2024-10-09\\",\\"temperature\\":{\\"min\\":63,\\"max\\":82},\\"query_time\\":\\"2024-10-04 19:54:13.305126+00:00\\"},{\\"date\\":\\"2024-10-10\\",\\"temperature\\":{\\"min\\":54,\\"max\\":61},\\"query_time\\":\\"2024-10-04 19:54:13.305144+00:00\\"}],\\"unit\\":\\"F\\"}"}]]'


def test_process_state():
  history = []
  history.append(Message(role="user", content="how is the weather in chicago?"))
  process_state(arch_state, history)

if __name__ == "__main__":
    pytest.main()
