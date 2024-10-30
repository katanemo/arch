import os
import json
import pandas as pd
import gradio as gr
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from typing import List, Optional, Tuple
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI
from common import create_gradio_app

app = FastAPI()
workforce_data_df = None
demo_description = """This demo showcases how the **Arch** can be used to build an
HR agent to manage workforce-related inquiries, workforce planning, and communication via Slack.
It intelligently routes incoming prompts to the correct targets, providing concise and useful responses
tailored for HR and workforce decision-making. """

with open("workforce_data.json") as file:
    workforce_data = json.load(file)
    workforce_data_df = pd.json_normalize(
        workforce_data,
        record_path=["regions"],
        meta=["data_snapshot_days_ago", "satisfaction"],
    )


# Define the request model
class WorkforceRequset(BaseModel):
    region: str
    staffing_type: str
    data_snapshot_days_ago: Optional[int] = None


class SlackRequest(BaseModel):
    slack_message: str


class WorkforceResponse(BaseModel):
    region: str
    staffing_type: str
    headcount: int
    satisfaction: float


@app.post("/agent/slack_message")
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
        channel = "hr_agent_demo"
        try:
            # Send the message
            response = client.chat_postMessage(channel=channel, text=slack_message)
            return f"Message sent to {channel}: {response['message']['text']}"
        except SlackApiError as e:
            print(f"Error sending message: {e.response['error']}")


# Post method for device summary
@app.post("/agent/workforce")
def get_workforce(request: WorkforceRequset):
    """
    Endpoint to workforce data by region, staffing type at a given point in time.
    """
    region = request.region.lower()
    staffing_type = request.staffing_type.lower()
    data_snapshot_days_ago = (
        request.data_snapshot_days_ago
        if request.data_snapshot_days_ago
        else 0  # this param is not required.
    )

    response = {
        "region": region,
        "staffing_type": f"Staffing agency: {staffing_type}",
        "headcount": f"Headcount: {int(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['data_snapshot_days_ago']==data_snapshot_days_ago)][staffing_type].values[0])}",
        "satisfaction": f"Satisifaction: {float(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['data_snapshot_days_ago']==data_snapshot_days_ago)]['satisfaction'].values[0])}",
    }
    return response


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
