from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.lib.models.category_topic import CategoryTopic
from app.lib.models.conversations import Message



class CategoryBase(BaseModel):
    name: str
    description: str = None


class Category(BaseModel):
    id: str
    name: str
    description: str = None
    type: str
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
    deletedAt: Optional[datetime]
    CategoryTopic: Optional[List["CategoryTopic"]]
    message: Optional[List["Message"]] = None