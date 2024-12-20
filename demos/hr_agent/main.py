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

app = FastAPI()
workforce_data_df = None

with open("workforce_data.json") as file:
    workforce_data = json.load(file)
    workforce_data_df = pd.json_normalize(
        workforce_data,
        record_path=["regions"],
        meta=["data_snapshot_days_ago", "satisfaction"],
    )


# Define the request model
class WorkforceRequest(BaseModel):
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
def get_workforce(request: WorkforceRequest):
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
        "satisfaction": f"Satisfaction: {float(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['data_snapshot_days_ago']==data_snapshot_days_ago)]['satisfaction'].values[0])}",
    }
    return response


if __name__ == "__main__":
    app.run(debug=True)
