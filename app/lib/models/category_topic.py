from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.lib.models.topic import Topic


class CategoryTopicBase(BaseModel):
    topicId: str
    categoryId: str


class CategoryTopic(BaseModel):
    id: str
    topic: Optional[Topic]
    topicId: Optional[str]
    categoryId: str
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
    deletedAt: Optional[datetime]


class CreateCategoryTopic(CategoryTopicBase):
    pass


class CreateCategoryTopicsFromExisting(BaseModel):
    categoryId: str
    topicIds: List[str]


class CreateCategoryTopicResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[CategoryTopic]


class CreateCategoryTopicsResponseFromExisting(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[List[CategoryTopic]]


class ListCategoryTopicsResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[List[CategoryTopic]]
