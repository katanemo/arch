import json
import pytest
from app.arch_fc.arch_fc import process_state
from app.arch_fc.common import ChatMessage, Message
# test process_state

arch_state = '[[{"key":"02ea8ec721b130dc30ec836b79ec675116cd5889bca7d63720bc64baed994fc1","message":{"role":"user","content":"how is the weather in new york?"},"tool_call":{"name":"weather_forecast","arguments":{"city":"new york"}},"tool_response":"{\\"city\\":\\"new york\\",\\"temperature\\":[{\\"date\\":\\"2024-10-07\\",\\"temperature\\":{\\"min\\":68,\\"max\\":79}},{\\"date\\":\\"2024-10-08\\",\\"temperature\\":{\\"min\\":70,\\"max\\":76}},{\\"date\\":\\"2024-10-09\\",\\"temperature\\":{\\"min\\":71,\\"max\\":84}},{\\"date\\":\\"2024-10-10\\",\\"temperature\\":{\\"min\\":61,\\"max\\":79}},{\\"date\\":\\"2024-10-11\\",\\"temperature\\":{\\"min\\":86,\\"max\\":91}},{\\"date\\":\\"2024-10-12\\",\\"temperature\\":{\\"min\\":85,\\"max\\":90}},{\\"date\\":\\"2024-10-13\\",\\"temperature\\":{\\"min\\":72,\\"max\\":89}}],\\"unit\\":\\"F\\"}"}],[{"key":"566b9a2197cba89f35c1e3fbeee55882772ae7627fcf4411dae90282f98a1067","message":{"role":"user","content":"how is the weather in chicago?"},"tool_call":{"name":"weather_forecast","arguments":{"city":"chicago"}},"tool_response":"{\\"city\\":\\"chicago\\",\\"temperature\\":[{\\"date\\":\\"2024-10-07\\",\\"temperature\\":{\\"min\\":54,\\"max\\":64}},{\\"date\\":\\"2024-10-08\\",\\"temperature\\":{\\"min\\":84,\\"max\\":99}},{\\"date\\":\\"2024-10-09\\",\\"temperature\\":{\\"min\\":85,\\"max\\":100}},{\\"date\\":\\"2024-10-10\\",\\"temperature\\":{\\"min\\":50,\\"max\\":62}},{\\"date\\":\\"2024-10-11\\",\\"temperature\\":{\\"min\\":79,\\"max\\":85}},{\\"date\\":\\"2024-10-12\\",\\"temperature\\":{\\"min\\":88,\\"max\\":100}},{\\"date\\":\\"2024-10-13\\",\\"temperature\\":{\\"min\\":56,\\"max\\":61}}],\\"unit\\":\\"F\\"}"}]]'

def test_process_state():
  history = []
  history.append(Message(role="user", content="how is the weather in new york?"))
  history.append(Message(role="user", content="how is the weather in chicago?"))
  updated_history = process_state(arch_state, history)
  print(json.dumps(updated_history, indent=2))


if __name__ == "__main__":
    pytest.main()
