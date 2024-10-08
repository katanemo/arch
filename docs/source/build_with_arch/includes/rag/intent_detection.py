from flask import Flask, request, jsonify
from datetime import datetime
import uuid
from langchain.memory import ConversationBufferMemory
from langchain.schema import AIMessage, HumanMessage
from langchain import OpenAI

app = Flask(__name__)

# Global dictionary to keep track of user memories
user_memories = {}


def get_user_conversation(user_id):
    """
    Retrieve the user's conversation memory using LangChain.
    If the user does not exist, initialize their conversation memory.
    """
    if user_id not in user_memories:
        user_memories[user_id] = ConversationBufferMemory(return_messages=True)
    return user_memories[user_id]


def update_user_conversation(user_id, client_messages, intent_changed):
    """
    Update the user's conversation memory with new messages using LangChain.
    Each message is augmented with a UUID, timestamp, and intent change marker.
    Only new messages are added to avoid duplication.
    """
    memory = get_user_conversation(user_id)
    stored_messages = memory.chat_memory.messages

    # Determine the number of stored messages
    num_stored_messages = len(stored_messages)
    new_messages = client_messages[num_stored_messages:]

    # Process each new message
    for index, message in enumerate(new_messages):
        role = message.get("role")
        content = message.get("content")
        metadata = {
            "uuid": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "intent_changed": False,  # Default value
        }

        # Mark the intent change on the last message if detected
        if intent_changed and index == len(new_messages) - 1:
            metadata["intent_changed"] = True

        # Create a new message with metadata
        if role == "user":
            memory.chat_memory.add_message(
                HumanMessage(content=content, additional_kwargs={"metadata": metadata})
            )
        elif role == "assistant":
            memory.chat_memory.add_message(
                AIMessage(content=content, additional_kwargs={"metadata": metadata})
            )
        else:
            # Handle other roles if necessary
            pass

    return memory


def get_messages_since_last_intent(messages):
    """
    Retrieve messages from the last intent change onwards using LangChain.
    """
    messages_since_intent = []
    for message in reversed(messages):
        # Insert message at the beginning to maintain correct order
        messages_since_intent.insert(0, message)
        metadata = message.additional_kwargs.get("metadata", {})
        # Break if intent_changed is True
        if metadata.get("intent_changed", False) == True:
            break

    return messages_since_intent


def forward_to_llm(messages):
    """
    Forward messages to an upstream LLM using LangChain.
    """
    # Convert messages to a conversation string
    conversation = ""
    for message in messages:
        role = "User" if isinstance(message, HumanMessage) else "Assistant"
        content = message.content
        conversation += f"{role}: {content}\n"
    # Use LangChain's LLM to get a response. This call is proxied through Arch for end-to-end observability and traffic management
    llm = OpenAI()
    # Create a prompt that includes the conversation
    prompt = f"{conversation}Assistant:"
    response = llm(prompt)
    return response


@app.route("/process_rag", methods=["POST"])
def process_rag():
    # Extract JSON data from the request
    data = request.get_json()

    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"error": "User ID is required"}), 400

    client_messages = data.get("messages")
    if not client_messages or not isinstance(client_messages, list):
        return jsonify({"error": "Messages array is required"}), 400

    # Extract the intent change marker from Arch's headers if present for the current prompt
    intent_changed_header = request.headers.get("x-arch-intent-marker", "").lower()
    if intent_changed_header in ["", "false"]:
        intent_changed = False
    elif intent_changed_header == "true":
        intent_changed = True
    else:
        # Invalid value provided
        return jsonify(
            {"error": "Invalid value for x-arch-prompt-intent-change header"}
        ), 400

    # Update user conversation based on intent change
    memory = update_user_conversation(user_id, client_messages, intent_changed)

    # Retrieve messages since last intent change for LLM
    messages_for_llm = get_messages_since_last_intent(memory.chat_memory.messages)

    # Forward messages to upstream LLM
    llm_response = forward_to_llm(messages_for_llm)

    # Prepare the messages to return
    messages_to_return = []
    for message in memory.chat_memory.messages:
        role = "user" if isinstance(message, HumanMessage) else "assistant"
        content = message.content
        metadata = message.additional_kwargs.get("metadata", {})
        message_entry = {
            "uuid": metadata.get("uuid"),
            "timestamp": metadata.get("timestamp"),
            "role": role,
            "content": content,
            "intent_changed": metadata.get("intent_changed", False),
        }
        messages_to_return.append(message_entry)

    # Prepare the response
    response = {
        "user_id": user_id,
        "messages": messages_to_return,
        "llm_response": llm_response,
    }

    return jsonify(response), 200


if __name__ == "__main__":
    app.run(debug=True)
