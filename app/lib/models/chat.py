from typing import Optional

from pydantic import BaseModel


class MessageRequest(BaseModel):
    content: str
    metadata: Optional[dict] = None

class AssistantChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: Optional[MessageRequest] = None