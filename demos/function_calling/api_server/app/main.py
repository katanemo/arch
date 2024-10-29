import json
import random
from fastapi import FastAPI, Response
from datetime import datetime, date, timedelta, timezone
import logging
from pydantic import BaseModel


logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

app = FastAPI()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


class WeatherRequest(BaseModel):
    city: str
    days: int = 7
    units: str = "Farenheit"


@app.post("/weather")
async def weather(req: WeatherRequest, res: Response):
    weather_forecast = {
        "city": req.city,
        "temperature": [],
        "units": req.units,
    }
    for i in range(req.days):
        min_temp = random.randrange(50, 90)
        max_temp = random.randrange(min_temp + 5, min_temp + 20)
        if req.units.lower() == "celsius" or req.units.lower() == "c":
            min_temp = (min_temp - 32) * 5.0 / 9.0
            max_temp = (max_temp - 32) * 5.0 / 9.0
        weather_forecast["temperature"].append(
            {
                "date": str(date.today() + timedelta(days=i)),
                "temperature": {"min": min_temp, "max": max_temp},
                "units": req.units,
                "query_time": str(datetime.now(timezone.utc)),
            }
        )

    return weather_forecast


class InsuranceClaimDetailsRequest(BaseModel):
    policy_number: str


@app.post("/insurance_claim_details")
async def insurance_claim_details(req: InsuranceClaimDetailsRequest, res: Response):
    claim_details = {
        "policy_number": req.policy_number,
        "claim_status": "Approved",
        "claim_amount": random.randrange(1000, 10000),
        "claim_date": str(date.today() - timedelta(days=random.randrange(1, 30))),
        "claim_reason": "Car Accident",
    }

    return claim_details


class DefaultTargetRequest(BaseModel):
    messages: list


@app.post("/default_target")
async def default_target(req: DefaultTargetRequest, res: Response):
    logger.info(f"Received arch_messages: {req.messages}")
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I can help you with weather forecast or insurance claim details",
                },
                "finish_reason": "completed",
                "index": 0,
            }
        ],
        "model": "api_server",
        "usage": {"completion_tokens": 0},
    }
    logger.info(f"sending response: {json.dumps(resp)}")
    return resp
