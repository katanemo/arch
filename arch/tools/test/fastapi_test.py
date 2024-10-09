from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Dict, Set

app = FastAPI()


class User(BaseModel):
    name: str = Field(
        "John Doe", description="The name of the user."
    )  # Default value and description for name
    location: int = None
    age: int = Field(
        30, description="The age of the user."
    )  # Default value and description for age
    tags: Set[str] = Field(
        default_factory=set, description="A set of tags associated with the user."
    )  # Default empty set and description for tags
    metadata: Dict[str, int] = Field(
        default_factory=dict,
        description="A dictionary storing metadata about the user, with string keys and integer values.",
    )  # Default empty dict and description for metadata


@app.get("/agent/default")
async def default(request: User):
    """
    This endpoint handles information extraction queries.
    It can summarize, extract details, and perform various other information-related tasks.
    """
    return {"info": f"Query: {request.name}, Count: {request.age}"}


@app.post("/agent/action")
async def reboot_network_device(device_id: str, confirmation: str):
    """
    This endpoint reboots a network device based on the device ID.
    Confirmation is required to proceed with the reboot.

    Args:
        device_id: The device_id that you want to reboot.
        confirmation: The confirmation that the user wants to reboot.
        metadata: Ignore this parameter
    """
    return {"status": "Device rebooted", "device_id": device_id}
