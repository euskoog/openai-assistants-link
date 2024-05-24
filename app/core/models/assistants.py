from typing import List, Optional, Any
from pydantic import BaseModel


class AssistantBase(BaseModel):
    name: str
    instructions: str
    model: str = "gpt-3.5-turbo"
    temperature: Optional[float] = 1.0


class CreateAssistantResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Any]


class ReadAssisantResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Any]


class ListAssistantsResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[List[Any]] = []
