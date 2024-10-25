import json


ARCH_STATE_HEADER = "x-arch-state"


def get_arch_messages(response_json):
    arch_messages = []
    if response_json and "metadata" in response_json:
        # load arch_state from metadata
        arch_state_str = response_json.get("metadata", {}).get(ARCH_STATE_HEADER, "{}")
        # parse arch_state into json object
        arch_state = json.loads(arch_state_str)
        # load messages from arch_state
        arch_messages_str = arch_state.get("messages", "[]")
        # parse messages into json object
        arch_messages = json.loads(arch_messages_str)
        # append messages from arch gateway to history
        return arch_messages
    return []
