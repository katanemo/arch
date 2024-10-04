import json
import random
from fastapi import FastAPI, Response
from datetime import datetime, date, timedelta, timezone
import logging
from pydantic import BaseModel


logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.INFO)

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

class WeatherRequest(BaseModel):
  city: str


@app.post("/weather")
async def weather(req: WeatherRequest, res: Response):

    weather_forecast = {
        "city": req.city,
        "temperature": [],
        "unit": "F",
    }
    for i in range(7):
       min_temp = random.randrange(50,90)
       max_temp = random.randrange(min_temp+5, min_temp+20)
       weather_forecast["temperature"].append({
           "date": str(date.today() + timedelta(days=i)),
           "temperature": {
              "min": min_temp,
              "max": max_temp
           }
       })

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
   arch_messages: list

@app.post("/default_target")
async def default_target(req: DefaultTargetRequest, res: Response):
    logger.info(f"Received arch_messages: {req.arch_messages}")
    resp = {
            "choices": [
              {
                "message": {
                  "role": "assistant",
                  "content": "hello world from api server"
                },
                "finish_reason": "completed",
                "index": 0
              }
            ],
            "model": "api_server",
            "usage": {
              "completion_tokens": 0
            }
          }
    logger.info(f"sending response: {json.dumps(resp)}")
    return resp
