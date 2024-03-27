from datetime import datetime
import logging

from fastapi import APIRouter, Depends
from openai import OpenAI
from app.lib.models.assistant_datasource import (
    CreateAssistantDatasource,
    CreateAssistantDatasourceResponse,
    ListAssistantDatasourcesResponse,
    prisma_to_pydantic_assistant_datasource,
)
from app.lib.openai import get_openai_client
from app.lib.prisma import prisma
from app.lib.models.response import Response
from app.lib.openai.openai_tool import OpenAICodeInterpreterTool, OpenAIRetrievalTool

logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/assistant-datasources",
    tags=["assistant-datasources"],
    responses={404: {"description": "Not found"}},
)


@router.get(
    "/{assistantId}",
    name="List assistant datasources",
    description="List all assistant datasources",
    response_model=ListAssistantDatasourcesResponse,
)
async def read_assistant_datasources(assistantId: str):
    """List assistant datasources endpoint"""

    logger.info(f"Listing assistant id {assistantId} datasources")
    try:
        assistant_datasources = prisma.assistantdatasource.find_many(
            where={"assistantId": assistantId},
            include={"datasource": True},
            order={"createdAt": "desc"},
        )

        formatted_assistant_datasources = [
            prisma_to_pydantic_assistant_datasource(assistant_datasource)
            for assistant_datasource in assistant_datasources
        ]

        logger.info(
            f"Assistant id {assistantId} datasources listed successfully")
        response_data = ListAssistantDatasourcesResponse(
            success=True, data=formatted_assistant_datasources
        )
    except Exception as e:
        logger.error("Error listing datasources", exc_info=e)
        response_data = ListAssistantDatasourcesResponse(
            success=False, error=str(e))

    return response_data


@router.post(
    "/",
    name="Create assistant datasource",
    description="Create assistant datasource",
    response_model=CreateAssistantDatasourceResponse,
)
async def create_assistant_datasource(
    body: CreateAssistantDatasource,
    openai_client: OpenAI = Depends(get_openai_client),
):
    """Create assistant datasource endpoint"""

    logger.info(f"Creating assistant id {body.assistantId} datasource")
    try:
        # first, retrieve the datasource
        datasource = prisma.datasource.find_unique(
            where={
                "id": body.datasourceId,
            }
        )

        if datasource.type == "DOCUMENT":
            metadata = datasource.metadata

            # check if metadata has a key called 'openai'
            if metadata and metadata.get("openai"):
                openai_metadata = metadata.get("openai")
                if openai_metadata:
                    file_id = openai_metadata.get("id")
                    if file_id:
                        assistant = prisma.assistant.find_unique(
                            where={"id": body.assistantId}
                        )

                        if assistant:
                            assistant_metadata = assistant.metadata or {}

                            if assistant_metadata and assistant_metadata.get("openai"):
                                assistant_openai_metadata = assistant_metadata.get(
                                    "openai"
                                )
                                openai_assistant_id = assistant_openai_metadata.get(
                                    "assistantId"
                                )
                                openai_assistant = (
                                    openai_client.beta.assistants.retrieve(
                                        assistant_id=openai_assistant_id
                                    )
                                )

                                # add file to assistant
                                existing_files = openai_assistant.file_ids
                                existing_files.append(file_id)

                                # add retrieval tool to assistant if it doesn't exist
                                existing_tools = openai_assistant.tools

                                # add retrieval tool if it doesn't exist
                                for existing_tool in existing_tools:
                                    if existing_tool.type == "retrieval":
                                        # remove it since we cant serialize whatever type it comes back as from openai
                                        existing_tools.remove(existing_tool)
                                        break

                                existing_tools.append(
                                    OpenAIRetrievalTool.to_dict())

                                # if the file extension is csv, also add the code interpreter tool
                                if metadata["content_type"] == "text/csv":
                                    existing_tools.append(
                                        OpenAICodeInterpreterTool.to_dict()
                                    )

                                openai_client.beta.assistants.update(
                                    assistant_id=openai_assistant_id,
                                    tools=existing_tools,
                                    file_ids=existing_files,
                                )

        assistant_datasource = prisma.assistantdatasource.create(
            data={"assistantId": body.assistantId,
                  "datasourceId": body.datasourceId}
        )
        logger.info(
            f"Assistant id {body.assistantId} datasource created successfully")

        response_data = CreateAssistantDatasourceResponse(
            success=True, data=prisma_to_pydantic_assistant_datasource(assistant_datasource)
        )
    except Exception as e:
        logger.error("Error creating datasource", exc_info=e)
        response_data = CreateAssistantDatasourceResponse(
            success=False, error=str(e))

    return response_data


@router.delete(
    "/{assistantDatasourceId}",
    name="Delete assistant datasource",
    description="Delete assistant datasource",
    response_model=Response,
)
async def delete_assistant_datasource(
    assistantDatasourceId: str,
    openai_client: OpenAI = Depends(get_openai_client),
):
    """Delete assistant datasource endpoint"""

    logger.info(f"Deleting assistant datasource id {assistantDatasourceId}")
    try:
        now = datetime.now()

        # find the record and update the deletedAt field
        assistant_datasource = prisma.assistantdatasource.update(
            where={"id": assistantDatasourceId},
            data={"deletedAt": now},
            include={"assistant": True, "datasource": True},
        )

        # find the datasource and update the deletedAt field
        prisma.datasource.update(
            where={"id": assistant_datasource.datasourceId},
            data={"deletedAt": now},
        )

        # remove the openai file from the openai assistant
        if assistant_datasource.datasource.type == "DOCUMENT":

            # get associated assistant ids from assistant metadata
            assistant_metadata = assistant_datasource.datasource.metadata
            openai_assistant_id = assistant_metadata.get(
                "openai").get("assistantId")
            openai_file_id = assistant_metadata.get("openai").get("id")

            openai_client.beta.assistants.files.delete(
                assistant_id=openai_assistant_id, file_id=openai_file_id
            )

        logger.info(
            f"Assistant datasource id {assistantDatasourceId} deleted successfully"
        )
        response_data = Response(success=True)
    except Exception as e:
        logger.error("Error deleting datasource", exc_info=e)
        response_data = Response(success=False, error=str(e))

    return response_data
