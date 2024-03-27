from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class Role(Enum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    FUNCTION_REQUEST = "FUNCTION_REQUEST"
    FUNCTION_RESPONSE = "FUNCTION_RESPONSE"

class Message(BaseModel):
    id: str = ""
    content: str = ""
    conversation_id: str = ""
    role: str = Role.USER
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now())
    metadata: dict = {}

class Conversation(BaseModel):
    id: str
    assistant_id: str
    metadata: dict
    messages: Optional[List[Message]]

class ConversationCreate(BaseModel):
    conversation_id: str
    assistant_id: str

