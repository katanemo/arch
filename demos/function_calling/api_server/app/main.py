import random
from fastapi import FastAPI, Response
from datetime import datetime, date, timedelta, timezone
import logging
from pydantic import BaseModel
import pytz

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

@app.get("/current_time")
async def current_time(timezone: str):
    tz = None
    try:
      timezone.strip('"')
      tz = pytz.timezone(timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        return {
            "error": "Invalid timezone: {}".format(timezone)
        }
    current_time = datetime.now(tz)
    return {
        "timezone": timezone,
        "current_time": current_time.strftime("%Y-%m-%d %H:%M:%S %Z")
    }
