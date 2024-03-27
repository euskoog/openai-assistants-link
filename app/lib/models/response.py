from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str


class SuccessResponse(BaseModel):
    data: Dict[str, Any]


class Response(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Union[List[Any], Dict[str, Any]]] = None
