import os
import json
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

app = FastAPI()
workforce_data_df = None

with open("workforce_data.json") as file:
    workforce_data = json.load(file)
    workforce_data_df = pd.json_normalize(
        workforce_data, record_path=["regions"], meta=["point_in_time", "satisfaction"]
    )


# Define the request model
class WorkforceRequset(BaseModel):
    region: str
    staffing_type: str
    point_in_time: Optional[int] = None


class SlackRequest(BaseModel):
    slack_message: str


class WorkforceResponse(BaseModel):
    region: str
    staffing_type: str
    headcount: int
    satisfaction: float


# Post method for device summary
@app.post("/agent/workforce")
def get_workforce(request: WorkforceRequset):
    """
    Endpoint to workforce data by region, staffing type at a given point in time.
    """
    region = request.region.lower()
    staffing_type = request.staffing_type.lower()
    point_in_time = request.point_in_time if request.point_in_time else 0

    response = {
        "region": region,
        "staffing_type": f"Staffing agency: {staffing_type}",
        "headcount": f"Headcount: {int(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['point_in_time']==point_in_time)][staffing_type].values[0])}",
        "satisfaction": f"Satisifaction: {float(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['point_in_time']==point_in_time)]['satisfaction'].values[0])}",
    }
    return response


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
    client = WebClient(token=slack_token)
    channel = "hr_agent_demo"

    try:
        # Send the message
        response = client.chat_postMessage(channel=channel, text=slack_message)
        return f"Message sent to {channel}: {response['message']['text']}"
    except SlackApiError as e:
        print(f"Error sending message: {e.response['error']}")


@app.post("/agent/hr_qa")
async def general_hr_qa():
    """
    This method handles Q/A related to general issues in HR.
    It forwards the conversation to the OpenAI client via a local proxy and returns the response.
    """
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I am a helpful HR agent, and I can help you plan for workforce related questions",
                },
                "finish_reason": "completed",
                "index": 0,
            }
        ],
        "model": "hr_agent",
        "usage": {"completion_tokens": 0},
    }


if __name__ == "__main__":
    app.run(debug=True)
