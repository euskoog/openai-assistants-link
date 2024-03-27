from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


# Convert Prisma datasource to Pydantic Datasource model
def prisma_to_pydantic_datasource(prisma_datasource):
    # Create the Pydantic Datasource model
    pydantic_datasource = Datasource(
        id=prisma_datasource.id,
        name=prisma_datasource.name,
        description=prisma_datasource.description,
        type=prisma_datasource.type,
        metadata=prisma_datasource.metadata,
        createdAt=prisma_datasource.createdAt,
        updatedAt=prisma_datasource.updatedAt,
    )
    
    return pydantic_datasource


class Datasource(BaseModel):
    id: str
    name: str
    description: str = None
    type: str
    metadata: dict | None = None
    createdAt: datetime
    updatedAt: datetime

    class Config:
        orm_mode = True

class CreateDatasourceResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[Datasource]


class ListDatasourcesResponse(BaseModel):
    success: bool
    error: Optional[str] = None
    data: Optional[List[Datasource]]
