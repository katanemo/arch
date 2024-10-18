from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import re

app = FastAPI()


class StaffingType(Enum):
    FTE = "fte"
    AGENCY = "agency"
    CONTRACT = "contract"


class RegionType(Enum):
    ASIA = "asia"
    EUROPE = "europe"
    AMERICAS = "americas"


# Define the request model
class HeadcountRequest(BaseModel):
    region: RegionType
    staffing_type: str


class HeadcountResponseSummary(BaseModel):
    region: str
    headcount: int
    staffing_type: str


HEADCOUNT = {
    ASIA: {CONTRACT: 100, FTE: 150, AGENCY: 2000},
    EUROPE: {CONTRACT: 80, FTE: 120, AGENCY: 2500},
    AMERICAS: {CONTRACT: 90, FTE: 200, AGENCY: 3000},
}


# Post method for device summary
@app.post("/agent/headcount")
def get_headcount(request: HeadcountRequest):
    """
    Endpoint to headcount data by region, staffing type over time range
    """
    headcount = HEADCOUNT[request.region][request.staffing_type]

    response = {
        "region": request.region.value,
        "staffing_type": f"Staffing agency: {staffing_type}",
        "headcount": f"Headcount: {headcount}",
    }

    return response


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
