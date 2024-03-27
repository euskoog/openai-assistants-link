from datetime import datetime
import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from openai import OpenAI
from prisma import Json
from app.lib.models.chat import AssistantChatRequest
from app.lib.prisma import prisma
from app.core.models.assistants import (
    AssistantBase,
    CreateAssistantResponse,
    ListAssistantsResponse,
    ReadAssisantResponse,
)
from app.lib.models.response import Response
from app.lib.services.chat import ChatService, get_chat_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistants",
    tags=["assistants"],
    responses={404: {"description": "Not found"}},
)


@router.post(
    "/",
    name="Create assistant",
    description="Create a new assistant",
    response_model=CreateAssistantResponse,
)
async def create_assistant(
    body: AssistantBase,
):
    """Create assistant endpoint"""
    logger.info(f"Creating assistant: {body}")

    try:
        openAIClient: OpenAI = OpenAI()

        # first, create an OpenAI assistant
        openai_assistant = openAIClient.beta.assistants.create(
            name=body.name, instructions=body.instructions, model=body.model
        )

        metadata = {
            "openai": {
                "assistantId": openai_assistant.id,
            }
        }

        assistant = prisma.assistant.create(
            {
                "name": body.name,
                "instructions": body.instructions,
                "model": body.model,
                "metadata": Json(metadata),
            }
        )

        response_data = CreateAssistantResponse(success=True, data=assistant)
        logger.info("Assistant created successfully")
    except Exception as e:
        logger.error("Error creating assistant", exc_info=e)
        response_data = CreateAssistantResponse(success=False, error=str(e))

    return response_data


@router.get(
    "/",
    name="List assistants",
    description="List all assistants",
    response_model=ListAssistantsResponse,
)
async def read_assistants():
    """List assistants endpoint"""
    logger.info("Listing assistants:")

    try:
        assistants = prisma.assistant.find_many(where={"deletedAt": None})

        response_data = ListAssistantsResponse(success=True, data=assistants)
        logger.info("Assistants listed successfully")

    except Exception as e:
        logger.error("Error listing assistants", exc_info=e)
        response_data = ListAssistantsResponse(success=False, error=str(e))

    print(f"response_data: {response_data}")
    return response_data


@router.put(
    "/{assistantId}",
    name="Update assistant",
    description="Update assistant",
    response_model=ReadAssisantResponse,
)
async def update_assistant(
    assistantId: str,
    body: AssistantBase,
):
    """Update assistant endpoint"""
    logger.info(f"Updating assistant by id: {assistantId}")

    try:
        openAIClient: OpenAI = OpenAI()

        assistant = prisma.assistant.update(
            where={"id": assistantId},
            data={
                "name": body.name,
                "instructions": body.instructions,
                "model": body.model,
            },
        )

        metadata = assistant.metadata

        if "openai" in metadata:
            openai_assistantId = metadata["openai"]["assistantId"]

            openAIClient.beta.assistants.update(
                openai_assistantId,
                name=body.name,
                instructions=body.instructions,
                model=body.model,
            )

        response_data = ReadAssisantResponse(success=True, data=assistant)

        logger.info("Assistant updated successfully")
    except Exception as e:
        logger.error("Error updating assistant", exc_info=e)
        response_data = ReadAssisantResponse(success=False, error=str(e))

    return response_data


@router.delete(
    "/{assistantId}",
    name="Delete assistant",
    description="Delete assistant",
    response_model=Response,
)
async def delete_assistant(
    assistantId: str,
):
    """Delete assistant endpoint"""
    logger.info(f"Deleting assistant by id: {assistantId}")

    try:
        openAIClient: OpenAI = OpenAI()

        # Initialize current time for soft deletion
        now = datetime.now()

        # Fetch the assistant to be deleted
        assistant = prisma.assistant.find_unique(where={"id": assistantId})
        if not assistant:
            raise HTTPException(status_code=404, detail="Assistant not found")

        metadata = assistant.metadata

        if "openai" in metadata:
            openai_assistantId = metadata["openai"]["assistantId"]
            openAIClient.beta.assistants.delete(openai_assistantId)

        # Update the deletedAt field for the assistant
        prisma.assistant.update(where={"id": assistantId}, data={"deletedAt": now})

        # Fetch the assistant again to return it in the response
        assistant = prisma.assistant.find_unique(where={"id": assistantId})

        response_data = Response(success=True, data=assistant)
        logger.info("Assistant deleted successfully")
    except Exception as e:
        logger.error("Error deleting assistant", exc_info=e)
        response_data = Response(success=False, error=str(e))

    return response_data


@router.post(
    "/{assistantId}/chat",
    name="Chat with an assistant",
    description="Chat with an assistant",
)
async def assistant_chat(
    assistant_id: str,
    body: AssistantChatRequest,
    background_tasks: BackgroundTasks,
    chat_service: ChatService = Depends(get_chat_service),
):
    """
    Engage in a conversation with an assistant identified by `assistant_id`.

    Args:

        assistant_id (str): A unique identifier for the assistant to converse with.
            This can be found in the AI Platform admin application that is used to create the assistant.
            Note: This is a path parameter.

        body (AssistantChatRequest): The payload containing details of the chat request, encapsulated as an `AssistantChatRequest` object.
            - `message` (MessageRequest): Contains the chat message details, including:
                * `content` (str): The main content of the message as a string. This is the text that the assistant will process.
                * `metadata` (Optional[dict], default=None): An optional dictionary containing additional data about the message. This can include Device information, location, etc.
                   - example: { DEVICE: "MOBILE", MY_LOCATION: "Seattle, WA" }
            - `conversation_id` (Optional[str]): An identifier for the chat conversation, if the assistant has memory enabled and you want to continue a conversation.

    Returns:

        AssistantResponse: An object detailing the outcome of the chat interaction.
            - `success` (bool): Indicates if the chat interaction was successfully processed.
            - `data` (Optional[AssistantResponseData]): Contains the assistant's message and conversation ID, if the interaction was successful.
            - `error` (Optional[str]): Contains an error message detailing what went wrong during the processing, if applicable.
    """
    logger.info(f"Assistant chat with assistant id: {assistant_id} and body: {body}")

    return await chat_service.chat(
        background_tasks=background_tasks,
        assistant_id=assistant_id,
        conversation_id=body.conversation_id,
        message=body.message,
    )
