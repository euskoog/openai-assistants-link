from typing import Optional
from pydantic import BaseModel

from app.lib.models.conversations import Message


class AssistantResponseData(BaseModel):
    message: Message
    conversation_id: str


class AssistantResponse(BaseModel):
    success: bool
    data: Optional[AssistantResponseData]
    error: Optional[str] = None