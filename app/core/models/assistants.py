from typing import List, Optional, Any
from pydantic import BaseModel


class AssistantBase(BaseModel):
    name: str
    instructions: str
    model: str = "gpt-4-1106-preview"


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
