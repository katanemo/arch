from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

app = FastAPI()

# Define the request model
class DeviceSummaryRequest(BaseModel):
    device_ids: List[int]
    time_range: Optional[int] = Field(default=7, description="Time range in days, defaults to 7")

# Define the response model
class DeviceStatistics(BaseModel):
    device_id: int
    time_range: str
    data: str

class DeviceSummaryResponse(BaseModel):
    statistics: List[DeviceStatistics]

    # Request model for device reboot
class DeviceRebootRequest(BaseModel):
    device_ids: List[int]
    time_range: Optional[int] = Field(default=7, description="Time range in days, defaults to 7")

# Response model for the device reboot
class CoverageResponse(BaseModel):
    status: str
    summary: dict

@app.post("/agent/device_reboot", response_model=CoverageResponse)
def reboot_network_device(request_data: DeviceRebootRequest):
    """
    Endpoint to reboot network devices based on device IDs and an optional time range.
    """

    # Access data from the Pydantic model
    device_ids = request_data.device_ids
    time_range = request_data.time_range

    # Validate 'device_ids' (This is already validated by Pydantic, but additional logic can be added if needed)
    if not device_ids:
        raise HTTPException(status_code=400, detail="'device_ids' parameter is required")

    # Validate 'time_range' (already validated by Pydantic, but more logic can be added)
    if not isinstance(time_range, int):
        raise HTTPException(status_code=400, detail="'time_range' must be an integer")

    # Simulate reboot operation and return the response
    statistics = []
    for device_id in device_ids:
        # Placeholder for actual data retrieval or device reboot logic
        stats = {
            "device_id": device_id,
            "time_range": f"Last {time_range} days",
            "data": f"Device {device_id} has been successfully rebooted."
        }
        statistics.append(stats)

    # Return the response with a summary
    return CoverageResponse(status="success", summary={"device_ids": device_ids, "time_range": time_range})

# Post method for device summary
@app.post("/agent/device_summary", response_model=DeviceSummaryResponse)
def get_device_summary(request: DeviceSummaryRequest):
    """
    Endpoint to retrieve device statistics based on device IDs and an optional time range.
    """

    # Extract 'device_ids' and 'time_range' from the request
    device_ids = request.device_ids
    time_range = request.time_range

    # Simulate retrieving statistics for the given device IDs and time range
    statistics = []
    for device_id in device_ids:
        stats = {
            "device_id": device_id,
            "time_range": f"Last {time_range} days",
            "data": f"Statistics data for device {device_id} over the last {time_range} days.",
        }
        statistics.append(DeviceStatistics(**stats))

    return DeviceSummaryResponse(statistics=statistics)

@app.post("/agent/network_summary")
async def policy_qa():
    """
    This method handles Q/A related to general issues in networks.
    It forwards the conversation to the OpenAI client via a local proxy and returns the response.
    """
    return {
            "choices": [
              {
                "message": {
                  "role": "assistant",
                  "content": "I am a helpful networking agent, and I can help you get status for network devices or reboot them"
                },
                "finish_reason": "completed",
                "index": 0
              }
            ],
            "model": "network_agent",
            "usage": {
              "completion_tokens": 0
            }
          }

if __name__ == "__main__":
    app.run(debug=True)
