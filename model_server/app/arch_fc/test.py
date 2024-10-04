import json

test_state = '[[{\"id\":\"chatcmpl-AERkCCOn5QprULBXeWpQLREWJJ1C8\",\"message\":{\"role\":\"user\",\"content\":\"how is the weather in new york?\"},\"tool_call\":{\"name\":\"weather_forecast\",\"arguments\":{\"city\":\"New York\"}},\"tool_response\":\"{\\\"city\\\":\\\"New York\\\",\\\"temperature\\\":[{\\\"date\\\":\\\"2024-10-04\\\",\\\"temperature\\\":{\\\"min\\\":55,\\\"max\\\":69},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781454+00:00\\\"},{\\\"date\\\":\\\"2024-10-05\\\",\\\"temperature\\\":{\\\"min\\\":89,\\\"max\\\":104},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781509+00:00\\\"},{\\\"date\\\":\\\"2024-10-06\\\",\\\"temperature\\\":{\\\"min\\\":51,\\\"max\\\":65},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781554+00:00\\\"},{\\\"date\\\":\\\"2024-10-07\\\",\\\"temperature\\\":{\\\"min\\\":77,\\\"max\\\":94},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781564+00:00\\\"},{\\\"date\\\":\\\"2024-10-08\\\",\\\"temperature\\\":{\\\"min\\\":72,\\\"max\\\":91},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781570+00:00\\\"},{\\\"date\\\":\\\"2024-10-09\\\",\\\"temperature\\\":{\\\"min\\\":52,\\\"max\\\":67},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781574+00:00\\\"},{\\\"date\\\":\\\"2024-10-10\\\",\\\"temperature\\\":{\\\"min\\\":82,\\\"max\\\":88},\\\"query_time\\\":\\\"2024-10-04 01:50:03.781578+00:00\\\"}],\\\"unit\\\":\\\"F\\\"}\"}]]'

def process_state(state, history):
    print("state: {}".format(state))
    state = json.loads(state)
    state_map = {}
    for tools_state in state:
        for tool_state in tools_state:
            state_map[tool_state['message']['content']] = tool_state

    updated_history = []
    for hist in history[::-1]:
        if hist.role == 'user':
            if hist.content in state_map:
                tool_call_state = state_map[hist.content]
                if 'tool_response' in tool_call_state:
                    tool_resp = tool_call_state['tool_response']
                    updated_history.append(ChatMessage(role="user", content=f"<tool_response>\n{tool_resp}\n</tool_response>"))
                if 'tool_call' in tool_call_state:
                    tool_call_str = json.dumps(tool_call_state['tool_call'])
                    updated_history.append(ChatMessage(role="assistant", content=f"<tool_call>\n{tool_call_str}\n</tool_call>"))
                # we dont want to match this state with any other messages
                del(state_map[hist.content])
        updated_history.append(hist)
    return updated_history[::-1]

# main function
if __name__ == "__main__":
    h = process_state(test_state, [{"role": "user", "content": "hello"}, {"role": "user", "content": "how is the weather in new york?"}])
    print(json.dumps(h))
