from flask import Flask, request, jsonify
from datetime import datetime
import uuid

app = Flask(__name__)

# Global dictionary to keep track of user conversations
user_conversations = {}

def get_user_conversation(user_id):
    """
    Retrieve the user's conversation history.
    If the user does not exist, initialize their conversation data.
    """
    if user_id not in user_conversations:
        user_conversations[user_id] = {
            'messages': []
        }
    return user_conversations[user_id]

def update_user_conversation(user_id, client_messages, intent_changed):
    """
    Update the user's conversation history with new messages.
    Each message is augmented with a UUID, timestamp, and intent change marker.
    Only new messages are added to avoid duplication.
    """
    user_data = get_user_conversation(user_id)

    # Existing messages in the user's conversation
    stored_messages = user_data['messages']

    # Determine the number of stored messages
    num_stored_messages = len(stored_messages)

    # Check for out-of-sync messages
    if num_stored_messages > len(client_messages):
        return jsonify({'error': 'Client messages are out of sync with server'}), 400

    # Determine new messages by slicing the client messages
    new_messages = client_messages[num_stored_messages:]

    # Process each new message
    for index, message in enumerate(new_messages):
        message_entry = {
            'uuid': str(uuid.uuid4()),
            'timestamp': datetime.utcnow().isoformat(),
            'role': message.get('role'),
            'content': message.get('content'),
            'intent_changed': False  # Default value
        }
        # Mark the intent change on the last message if detected
        if intent_changed and index == len(new_messages) - 1:
            message_entry['intent_changed'] = True
        user_data['messages'].append(message_entry)

    return user_data

def get_messages_since_last_intent(messages):
    """
    Retrieve messages from the last intent change onwards.
    """
    messages_since_intent = []
    for message in reversed(messages):
        messages_since_intent.insert(0, message)
        if message.get('intent_changed'):
            break
    return messages_since_intent

def forward_to_llm(messages):
    """
    Simulate forwarding messages to an upstream LLM.
    Replace this with the actual API call to the LLM.
    """
    # For demonstration purposes, we'll return a placeholder response
    return "LLM response based on provided messages."

@app.route('/process_rag', methods=['POST'])
def process_rag():
    # Extract JSON data from the request
    data = request.get_json()

    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    client_messages = data.get('messages')
    if not client_messages or not isinstance(client_messages, list):
        return jsonify({'error': 'Messages array is required'}), 400

    # Extract the intent change marker from Arch's headers if present for the current prompt
    intent_changed_header = request.headers.get('x-arch-intent-marker', '').lower()
    if intent_changed_header in ['', 'false']:
        intent_changed = False
    elif intent_changed_header == 'true':
        intent_changed = True
    else:
        # Invalid value provided
        return jsonify({'error': 'Invalid value for x-arch-prompt-intent-change header'}), 400

    # Update user conversation based on intent change
    user_data = update_user_conversation(user_id, client_messages, intent_changed)

    # Retrieve messages since last intent change for LLM
    messages_for_llm = get_messages_since_last_intent(user_data['messages'])

    # Forward messages to upstream LLM
    llm_response = forward_to_llm(messages_for_llm)

    # Prepare the response
    response = {
        'user_id': user_id,
        'messages': user_data['messages'],
        'llm_response': llm_response
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(debug=True)
