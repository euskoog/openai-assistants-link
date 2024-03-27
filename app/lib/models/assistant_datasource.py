from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.lib.models.datasource import Datasource, prisma_to_pydantic_datasource

def prisma_to_pydantic_assistant_datasource(prisma_assistant_datasource):
    pydantic_assistant_datasource = AssistantDatasource(
        id=prisma_assistant_datasource.id,
        datasource=prisma_to_pydantic_datasource(
            prisma_assistant_datasource.datasource) if prisma_assistant_datasource.datasource else None,
        datasourceId=prisma_assistant_datasource.datasourceId,
        assistantId=prisma_assistant_datasource.assistantId,
        createdAt=prisma_assistant_datasource.createdAt,
        updatedAt=prisma_assistant_datasource.updatedAt,
        deletedAt=prisma_assistant_datasource.deletedAt,
    )

    return pydantic_assistant_datasource
    


class AssistantDatasourceBase(BaseModel):
    datasourceId: str
    assistantId: str


class AssistantDatasource(BaseModel):
    id: str
    datasource: Optional[Datasource]
    datasourceId: Optional[str]
    assistantId: str
    createdAt: Optional[datetime]
    updatedAt: Optional[datetime]
    deletedAt: Optional[datetime]


class CreateAssistantDatasource(AssistantDatasourceBase):
    pass


class CreateAssistantDatasourceResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[AssistantDatasource]


class ListAssistantDatasourcesResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[List[AssistantDatasource]]
