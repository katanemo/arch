import os
import json
import pandas as pd
import gradio as gr
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from enum import Enum
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from openai import OpenAI
from common import get_prompt_targets, process_stream_chunk

app = FastAPI()
workforce_data_df = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

log = logging.getLogger(__name__)

CHAT_COMPLETION_ENDPOINT = os.getenv("CHAT_COMPLETION_ENDPOINT")
log.info(f"CHAT_COMPLETION_ENDPOINT: {CHAT_COMPLETION_ENDPOINT}")

GRADIO_CSS_STYLE = """
.json-container {
    height: 95vh !important;
    overflow-y: auto !important;
}
.chatbot {
    height: calc(95vh - 100px) !important;
    overflow-y: auto !important;
}
footer {visibility: hidden}
"""

client = OpenAI(
    api_key="--",
    base_url=CHAT_COMPLETION_ENDPOINT,
)

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


# Post method for device summary
@app.post("/agent/workforce")
def get_workforce(request: WorkforceRequset):
    """
    Endpoint to workforce data by region, staffing type at a given point in time.
    """
    region = request.region.lower()
    staffing_type = request.staffing_type.lower()
    data_snapshot_days_ago = (
        request.data_snapshot_days_ago if request.data_snapshot_days_ago else 0
    )

    response = {
        "region": region,
        "staffing_type": f"Staffing agency: {staffing_type}",
        "headcount": f"Headcount: {int(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['data_snapshot_days_ago']==data_snapshot_days_ago)][staffing_type].values[0])}",
        "satisfaction": f"Satisifaction: {float(workforce_data_df[(workforce_data_df['region']==region) & (workforce_data_df['data_snapshot_days_ago']==data_snapshot_days_ago)]['satisfaction'].values[0])}",
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


def chat(
    query: Optional[str],
    conversation: Optional[List[Tuple[str, str]]],
    history: List[dict],
):
    history.append({"role": "user", "content": query})

    try:
        response = client.chat.completions.create(
            # we select model from arch_config file
            model="--",
            messages=history,
            temperature=1.0,
            stream=True,
        )
    except Exception as e:
        # remove last user message in case of exception
        history.pop()
        log.info("Error calling gateway API: {}".format(e))
        raise gr.Error("Error calling gateway API: {}".format(e))

    conversation.append((query, ""))

    for chunk in response:
        tokens = process_stream_chunk(chunk, history)
        if tokens:
            conversation[-1] = (
                conversation[-1][0],
                conversation[-1][1] + tokens,
            )

            yield "", conversation, history


def create_gradio_app():
    with gr.Blocks(
        theme=gr.themes.Default(
            font_mono=[gr.themes.GoogleFont("IBM Plex Mono"), "Arial", "sans-serif"]
        ),
        fill_height=True,
        css=GRADIO_CSS_STYLE,
    ) as demo:
        with gr.Row(equal_height=True):
            history = gr.State([])

            with gr.Column(scale=1):
                with gr.Accordion("See available tools", open=False):
                    with gr.Column(scale=1):
                        gr.JSON(
                            value=get_prompt_targets(),
                            show_indices=False,
                            elem_classes="json-container",
                            min_height="95vh",
                        )

            with gr.Column(scale=2):
                chatbot = gr.Chatbot(
                    label="Arch Chatbot",
                    elem_classes="chatbot",
                )
                textbox = gr.Textbox(
                    show_label=False,
                    placeholder="Enter text and press enter",
                    autofocus=True,
                    elem_classes="textbox",
                )

            textbox.submit(
                chat, [textbox, chatbot, history], [textbox, chatbot, history]
            )

    return demo


gr.mount_gradio_app(app, create_gradio_app(), path="/agent/chat")

if __name__ == "__main__":
    app.run(debug=True)
