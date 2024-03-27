from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.lib.models.conversations import Message

class TopicBase(BaseModel):
    name: str


class Topic(BaseModel):
    id: str
    name: str
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
    deletedAt: Optional[datetime]
    message: Optional[List["Message"]] = None
