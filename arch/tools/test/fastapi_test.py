from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class DefaultRequest(BaseModel):
    query: str
    count: int


@app.get("/agent/default")
async def default(request: DefaultRequest):
    """
    This endpoint handles information extraction queries.
    It can summarize, extract details, and perform various other information-related tasks.
    """
    return {"info": f"Query: {query}, Count: {count}"}

@app.post("/agent/action")
async def reboot_network_device(device_id: str, confirmation: int):
    """
    This endpoint reboots a network device based on the device ID.
    Confirmation is required to proceed with the reboot.
    """
    return {"status": "Device rebooted", "device_id": device_id}
