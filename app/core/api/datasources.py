from datetime import datetime
import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form
from openai import OpenAI
from prisma import Json
from app.lib.models.datasource import (
    CreateDatasourceResponse,
    ListDatasourcesResponse,
    prisma_to_pydantic_datasource,
)
from app.lib.models.response import Response
from app.lib.openai import get_openai_client
from app.lib.prisma import prisma


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/datasources",
    tags=["datasources"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/document",
    name="Create document datasource",
    description="Create a new document datasource",
    response_model=CreateDatasourceResponse,
)
async def create_document_datasource(
    file: Annotated[UploadFile, File(description="A file read as UploadFile")],
    name: Annotated[str, Form(..., description="Display name of the document")],
    description: Annotated[
        Optional[str], Form(..., description="Description of the document")
    ],
    openai_client: OpenAI = Depends(get_openai_client),
):
    print(f"==>> file: {file}")
    logger.info(f"Creating document datasource: {name}")

    try:
        #  process document
        if not file:
            response_data = CreateDatasourceResponse(
                success=False, error="No file provided"
            )
            logger.error(
                "Error creating document datasource. No file provided")
            return response_data

        openai_file = openai_client.files.create(
            file=(name, file.file), purpose="assistants"
        )
        print(f"==>> Created new OpenAI file: {openai_file}")

        metadata = {
            "filename": file.filename,
            "content_type": file.content_type,
            "openai": openai_file.model_dump(),
        }

        datasource = prisma.datasource.create(
            {
                "name": name.replace(" ", ""),
                "description": description,
                "type": "DOCUMENT",
                "metadata": Json(metadata),
            }
        )

        response_data = CreateDatasourceResponse(success=True, data=prisma_to_pydantic_datasource(datasource))
        logger.info("Datasource created successfully")

        return response_data
    except Exception as e:
        logger.error("Error creating datasource", exc_info=e)
        response_data = CreateDatasourceResponse(success=False, error=str(e))

    return response_data


# update document datasource
@router.put(
    "/document/{datasource_id}",
    name="Update document datasource",
    description="Update a document datasource",
    response_model=CreateDatasourceResponse,
)
async def update_document_datasource(
    datasource_id: str,
    name: Annotated[str, Form(..., description="Display name of the document")],
    description: Annotated[
        Optional[str], Form(..., description="Description of the document")
    ],
):
    logger.info(f"Updating document datasource: {datasource_id}")

    try:
        # get the original datasource
        datasource = prisma.datasource.find_unique(where={"id": datasource_id})

        #  only update name and description
        updated_datasource = prisma.datasource.update(
            where={"id": datasource_id},
            data={
                "name": name.replace(" ", ""),
                "description": description,
                "metadata": Json(datasource.metadata),
            },
        )

        logger.info(f"Updated datasource: {updated_datasource}")

        response_data = CreateDatasourceResponse(
            success=True, data=updated_datasource)
        logger.info("Datasource updated successfully")
    except Exception as e:
        logger.error("Error updating datasource", exc_info=e)
        response_data = CreateDatasourceResponse(success=False, error=str(e))

    return response_data


@router.get(
    "/",
    name="List datasources",
    description="List all datasources",
    response_model=ListDatasourcesResponse,
)
async def list_datasources():
    logger.info("Listing datasources")

    try:
        datasources = prisma.datasource.find_many()

        formatted_datasources = [prisma_to_pydantic_datasource(datasource)
                                    for datasource in datasources]

        response_data = ListDatasourcesResponse(success=True, data=formatted_datasources)
        logger.info("Datasources listed successfully")
    except Exception as e:
        logger.error("Error listing datasources", exc_info=e)
        response_data = ListDatasourcesResponse(success=False, error=str(e))

    return response_data


# get specific datasource
@router.get(
    "/{datasource_id}",
    name="Get datasource",
    description="Get a specific datasource",
    response_model=CreateDatasourceResponse,
)
async def get_datasource(datasource_id: str):
    logger.info(f"Getting datasource: {datasource_id}")

    try:
        datasource = prisma.datasource.find_unique(where={"id": datasource_id})

        response_data = CreateDatasourceResponse(success=True, data=prisma_to_pydantic_datasource(datasource))
        logger.info("Datasource retrieved successfully", datasource)
    except Exception as e:
        logger.error("Error retrieving datasource", exc_info=e)
        response_data = CreateDatasourceResponse(success=False, error=str(e))

    return response_data


@router.delete(
    "/{datasource_id}",
    name="Delete datasource",
    description="Delete a datasource",
    response_model=Response,
)
async def delete_datasource(
    datasource_id: str, openai_client: OpenAI = Depends(get_openai_client)
):
    logger.info(f"Deleting datasource: {datasource_id}")

    try:
        datasource = prisma.datasource.find_unique(where={"id": datasource_id})

        # update the deletedAt field
        prisma.datasource.update(
            where={"id": datasource.id}, data={"deletedAt": datetime.now()}
        )

        response_data = Response(success=True)
        logger.info("Datasource deleted successfully")

        if datasource.type == "DOCUMENT":
            # delete the openai file
            print(
                f"==>> Deleting OpenAI file: {datasource.metadata['openai']['id']}")
            openai_client.files.delete(
                file_id=datasource.metadata["openai"]["id"])
            print("==>> OpenAI file deleted")

    except Exception as e:
        logger.error("Error deleting datasource", exc_info=e)
        response_data = Response(success=False, error=str(e))

    return response_data
