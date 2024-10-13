from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import re

app = FastAPI()

class StaffingType(Enum):
    CONTRACT = "contract"
    FTE = "fte"
    AGENCY = "agency"

# Define the request model
class HeadcountRequest(BaseModel):
    region: str
    staffing_type: str

class HeadcountResponseSummary(BaseModel):
    region: str
    headcount: int
    staffing_type: str

# Post method for device summary
@app.post("/agent/headcount")
def get_headcount(request: HeadcountRequest):
    """
    Endpoint to headcount data by region, staffing type over time range
    """
    staffing_type_value = request.staffing_type

    if re.match(r"(?i)contract", staffing_type_value):  # Case-insensitive regex match
        headcount = 500
    elif re.match(r"(?i)fte", staffing_type_value):
        headcount = 1000
    elif re.match(r"(?i)agency", staffing_type_value):
        headcount = 4000
    else:
        raise HTTPException(
            status_code=400, detail="staffing_type parameter is invalid."
        )

    response = {
            "region": request.region,
            "staffing_type": f"Staffing agency: {staffing_type_value}",
            "headcount" : f"Headcount: {headcount}"
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
