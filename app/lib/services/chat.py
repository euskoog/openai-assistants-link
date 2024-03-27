import logging
import time
from typing import Callable, Optional

from app.lib.models.assistant import AssistantResponse, AssistantResponseData
from app.lib.models.chat import MessageRequest
from app.lib.models.conversations import ConversationCreate, Message, Role
from app.lib.models.datasource import Datasource
from app.lib.openai.openai_assistant import OpenAIAssistant
from app.lib.openai.openai_tool import (
    OpenAICodeInterpreterTool,
    OpenAIRetrievalTool,
    OpenAITool,
)
from app.lib.prisma import prisma
from app.lib.services.conversations import get_conversation_service
from prisma.models import Assistant

from fastapi import BackgroundTasks
from openai.types.beta.threads import (
    Run,
)

logger = logging.getLogger(__name__)


def format_time_diff(start_time, end_time):
    time_diff = float("{:.2f}".format(end_time - start_time))
    return time_diff


class ChatService:
    def __init__(self):
        self.conversation_service = get_conversation_service()

    def _load_assistant(self, assistant_id: str):
        try:
            start_time = time.time()
            assistant = prisma.assistant.find_unique(where={"id": assistant_id}, include={"assistantDatasource": True})
            end_time = time.time()
            logger.debug(f"==>> Assistant: {assistant}")
            logger.info(
                f"==>> It took {format_time_diff(start_time, end_time)} seconds to load the assistant."
            )
            return assistant
        except Exception as e:
            logger.error("Error loading assistant", exc_info=e)
            return None

    def _load_conversation(self, conversation_id: str):
        start_time = time.time()
        conversation = self.conversation_service.load_conversation(
            conversation_id=conversation_id,
        )
        end_time = time.time()
        logger.debug(f"==>> Conversation: {conversation}")
        logger.info(
            f"==>> It took {format_time_diff(start_time, end_time)} seconds to load the conversation."
        )

        return conversation

    def _create_new_conversation_from_thread_id(
        self, thread_id: str, assistant_id: str
    ):
        start_time = time.time()
        conversation = self.conversation_service.create_conversation(
            body=ConversationCreate(
                conversation_id=thread_id,
                assistant_id=assistant_id,
            )
        )
        end_time = time.time()
        logger.info(
            f"==>> It took {format_time_diff(start_time, end_time)} seconds to create a new conversation."
        )

        return conversation

    def _load_tools_and_file_ids_from_datasources(
        self,
        datasources: list[Datasource],
    ) -> tuple[list[OpenAITool], list[str]]:
        """
        Load tools and file ids from the assistant datasources.
        Check if the datasource is a document and if it is, determine if it requires a code interpreter tool or 
        a retrieval tool. Only add tool types once to the list of tools.
        """

        tools: list[OpenAITool] = []
        file_ids: list[str] = []

        if not datasources:
            return tools, file_ids

        for datasource in datasources:
            if datasource.type == "DOCUMENT":
                file_content_type = datasource.metadata.get("content_type", None)
                openai_metadata = datasource.metadata.get("openai", None)
                openai_file_id = (
                    openai_metadata.get("id", None) if openai_metadata else None
                )

                if openai_file_id is not None:
                    file_ids.append(openai_file_id)

                # if the file is a type that requires code_interpreter tool, add it
                if file_content_type == "text/csv":
                    # if code interpreter tool is not in the list of tools, add it
                    if not any(
                        tool.type == "code_interpreter" for tool in tools
                    ):  # if there is no code interpreter tool in the list of tools
                        tools.append(OpenAICodeInterpreterTool)
                else:
                    # only add the retrieval tool once - and only if the document is not a type that requires retrieval tool
                    if not any(
                        tool.type == "retrieval" for tool in tools
                    ):  # if there is no retrieval tool in the list of tools
                        tools.append(OpenAIRetrievalTool)

        return tools, file_ids

    def _load_ai_assistant(self, assistant: Assistant):
        start_time = time.time()

        # get the openai assistant id from the assistant metadata
        metadata = assistant.metadata if assistant.metadata else None

        if metadata is None:
            return None

        openai = metadata.get("openai", None)
        openai_assistantId = openai.get("assistantId", None) if openai else None

        if openai_assistantId is None:
            # The best way to handle this would be to create the assistant in OpenAI and then save the assistant id in the assistant metadata
            return None

        ai_assistant: OpenAIAssistant = None

        if openai_assistantId is not None:
            ai_assistant = OpenAIAssistant.from_id(openai_assistantId)

        asst_datasources = prisma.assistantdatasource.find_many(where={"assistantId": assistant.id}, include={"datasource": True})
        datasources = [asst_datasource.datasource for asst_datasource in asst_datasources]
            

        # gather tools and file_ids from the assistant datasources
        tools, file_ids = self._load_tools_and_file_ids_from_datasources(
            datasources or []
        )

        ai_assistant.tools = tools or []
        ai_assistant.file_ids = file_ids or []
        end_time = time.time()
        logger.debug(f"==>> AI Assistant: {ai_assistant}")
        logger.info(
            f"==>> It took {format_time_diff(start_time, end_time)} seconds to load the ai assistant."
        )

        return ai_assistant

    async def chat(
        self,
        background_tasks: BackgroundTasks,
        assistant_id: str,
        conversation_id: Optional[str] = None,
        message: MessageRequest = None,
        pre_run_hook_callback: Optional[Callable[[Run], None]] = None,
    ):
        try:
            # start tracking the time it takes to load all information before an llm call
            load_chat_details_start_time = time.time()

            # load assistant
            assistant = self._load_assistant(assistant_id)

            if assistant is None:
                error_message = Message(
                    role=Role.ASSISTANT.value,
                    content="Error loading the Assistant. It may not exist - please verify the assistant id and environment.",
                )

                return AssistantResponse(
                    success=False,
                    data=AssistantResponseData(
                        message=error_message,
                        conversation_id="",
                    ),
                    error="Error loading the Assistant. It may not exist - please verify the assistant id and environment.",
                )

            # load ai assistant
            ai_assistant: OpenAIAssistant = self._load_ai_assistant(assistant)

            if ai_assistant is None:
                error_message = Message(
                    role=Role.ASSISTANT.value,
                    content="Error loading the AI Assistant from OpenAI. It may not exist or this is probably an old assistant that needs to be recreated.",
                )

                return AssistantResponse(
                    success=False,
                    data=AssistantResponseData(
                        message=error_message,
                        conversation_id="",
                    ),
                    error="Error loading the AI Assistant from OpenAI. It may not exist or this is probably an old assistant that needs to be recreated.",
                )

            # if there is a conversation id, but its not a valid conversation, return an appropriate error message
            if conversation_id is not None and conversation_id != "":
                conversation = self._load_conversation(conversation_id)

                if conversation is None:
                    logger.warning(
                        "==>> Error loading the Conversation. It may not exist - please verify the conversation id and environment."
                    )
                    error_message = Message(
                        role=Role.ASSISTANT.value,
                        content="Error loading the conversation. It may not exist - please verify the conversation id and environment. If the issue persists, please try creating a new conversation.",
                    )

                    return AssistantResponse(
                        success=False,
                        data=AssistantResponseData(
                            message=error_message,
                            conversation_id="",
                        ),
                        error="Error loading the Conversation. It may not exist - please verify the conversation id and environment.",
                    )

            # if conversation_id is None or empty, create a new conversation and set the conversation_id to the new conversation id
            if conversation_id is None or conversation_id == "":
                logger.info(
                    "==>> Creating new conversation because the conversation_id is None or empty."
                )

                ai_assistant_default_thread_id = ai_assistant.default_thread.id
                new_conversation = self._create_new_conversation_from_thread_id(
                    ai_assistant_default_thread_id, assistant_id
                )
                conversation_id = new_conversation.id

            load_chat_details_end_time = time.time()
            logger.info(
                f"==>> It took {format_time_diff(load_chat_details_start_time, load_chat_details_end_time)} seconds to load all user/assistant details before an initial llm call."
            )

            # track time it takes to get response from ai assistant
            start_time = time.time()

            # gather assistant datasources
            # TODO: get assistant datasources from the assistant

            # ai_assistant.pre_run_hook_callback = pre_run_hook_callback

            (
                assistant_response_message,
                user_response_message,
            ) = await ai_assistant.chat_async(
                message=message.content,
                thread_id=conversation_id,
                additional_instructions="",
            )
            end_time = time.time()

            logger.info(
                f"==>> It took {format_time_diff(start_time, end_time)} seconds to get response from ai assistant."
            )

            # save conversation
            conversation_id = assistant_response_message.metadata["conversation_id"]

            response_data = AssistantResponseData(
                message=assistant_response_message,
                conversation_id=conversation_id,
            )
            new_messages = [user_response_message, assistant_response_message]

            background_tasks.add_task(
                self.conversation_service.update_conversation_with_evals,
                conversation_id,
                new_messages,
                assistant_id,
            )

            return AssistantResponse(success=True, data=response_data)
        except Exception as e:
            logger.error("Error querying assistant", exc_info=e)

            error_message = "Oops! It seems like we're experiencing technical difficulties right now. Our team is actively working to resolve the issue. Please check back shortly. Thank you for your patience."

            response_message = Message(
                role=Role.ASSISTANT.value,
                content=error_message,
                metadata={"error": str(e)},
            )

            response_data = AssistantResponseData(
                message=response_message,
                conversation_id=conversation_id or "",
            )

            return AssistantResponse(success=False, data=response_data)


def get_chat_service() -> ChatService:
    return ChatService()
