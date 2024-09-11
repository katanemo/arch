from pydantic import BaseModel

class Tool(BaseModel):
    name: str
    description: str
    parameters: dict

class Message(BaseModel):
    role: str
    content: str

class ChatMessage(BaseModel):
    messages: list[Message]
    tools: list[Tool]
