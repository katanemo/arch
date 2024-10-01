from typing import Any, Dict, List
from pydantic import BaseModel


class Message(BaseModel):
    role: str
    content: str


class ChatMessage(BaseModel):
    messages: list[Message]
    tools: List[Dict[str, Any]]
