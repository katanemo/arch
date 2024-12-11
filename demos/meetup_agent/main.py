import os
import json
import gradio as gr
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from common import create_gradio_app

app = FastAPI()
profile_data = None
demo_description = """This demo showcases how the **Arch** can be used to build a meetup agent that can look up profile information about attendees and store meetup notes via Slack"""

with open("profile.json") as file:
    profile_data = json.load(file)

profile_dict = {
    entry["name"]: {
        "professional": entry["professional"],
        "personal": entry["personal"],
    }
    for entry in profile_data
}


# Define the request model
class ProfileRequest(BaseModel):
    name: str
    interest: str


class ProfileResponse(BaseModel):
    details: str


class SlackRequest(BaseModel):
    slack_message: str


@app.get("/agenty/get_profile")
def get_profile(request: ProfileRequest):
    name = request.name
    interests = request.interest

    if name not in profile_dict["name"]:
        details = f"Sorry I don't have any profile information for {name}. Looks like you'll have to chat with this person to get more info"
    else:
        profile_dict_details = profile_dict[name]

    return details


@app.post("/agent/send_notes")
def send_slack_message(request: SlackRequest):
    """
    Endpoint that sends slack message
    """
    slack_message = request.slack_message

    # Load the bot token from an environment variable or replace it directly
    slack_token = os.getenv(
        "SLACK_BOT_TOKEN"
    )  # Replace with your token if needed: 'xoxb-your-token'

    if slack_token is None:
        print(f"Message for slack: {slack_message}")
    else:
        client = WebClient(token=slack_token)
        channel = "ai-tinkerers-channel"
        try:
            # Send the message
            response = client.chat_postMessage(channel=channel, text=slack_message)
            return f"Message sent to {channel}: {response['message']['text']}"
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")


CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT")
client = OpenAI(
    api_key="--",
    base_url=CHAT_COMPLETION_ENDPOINT,
)

gr.mount_gradio_app(
    app, create_gradio_app(demo_description, client), path="/agent/chat"
)

if __name__ == "__main__":
    app.run(debug=True)
