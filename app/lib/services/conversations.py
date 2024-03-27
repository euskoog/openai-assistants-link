import logging

from app.lib.models.conversations import ConversationCreate, Message
from prisma.models import Conversation

from app.lib.services.database.conversation_db import get_conversation_db_service
from app.lib.services.evaluations import get_evaluation_service

logger = logging.getLogger(__name__)

class ConversationService:
    def __init__(self) -> None:
        self.db_service = get_conversation_db_service()
        self.evaluation_service = get_evaluation_service()

    def read_conversation(
        self,
        conversationId: str,
    ) -> Conversation | None:
        try:
            result: Conversation = None

            db_result = self.db_service.read(conversationId)

            # return None if not found
            if db_result is None:
                result = None
            else:
                result = db_result

            return result
        except Exception as e:
            logger.error("Error reading conversation", exc_info=e)
            return None

    def create_conversation(self, body: ConversationCreate):
        """
        Create a new conversation with an existing thread ID as the conversation ID
        """
        try:
            return self.db_service.create(body)
        except Exception as e:
            logger.error("Error creating conversation", exc_info=e)
            return None

    def load_conversation(
        self, conversation_id: str
    ) -> Conversation | None:
        logger.info(f"==>> Loading conversation_id: {conversation_id}")
        
        conversation = self.read_conversation(conversation_id)

        return conversation

    def get_conversations_by_assistant(self, assistantId: str) -> list[Conversation] | None:
        try:
            conversations = self.db_service.read_all_by_assistant(assistantId)

            if not conversations:
                return []

            return conversations

        except Exception as e:
            logger.error("Error reading conversations", exc_info=e)
            return []


    def add_message_to_conversation(self, conversation_id: str, message: Message):
        try:
            new_message = self.db_service.add_message(
                conversation_id=conversation_id, message=message
            )
            return new_message
        except Exception as e:
            logger.error("Error adding message to conversation", exc_info=e)
            return None

    def add_messages_to_conversation(
        self, conversation_id: str, messages: list[Message]
    ):
        try:
            for message in messages:
                new_message = self.add_message_to_conversation(
                    conversation_id=conversation_id, message=message
                )
                if new_message is None:
                    raise Exception("Failed to add message to conversation")

        except Exception as e:
            logger.error("Error adding messages to conversation", exc_info=e)
            return None

    def update_conversation(
        self,
        conversation_id: str,
        new_messages: list[Message],
    ):
        try:
            # first, add the new messages to the conversation, then return the updated conversation
            self.add_messages_to_conversation(
                conversation_id=conversation_id, messages=new_messages
            )

            return self.read_conversation(conversationId=conversation_id)

        except Exception as e:
            logger.error("Error saving conversation", exc_info=e)
            return None

    def create_and_update_conversation(
        self,
        assistantId: str,
        conversation_id: str,
        messages: list[Message],
    ):
        new_conversation = self.create_conversation(
            body=ConversationCreate(
                assistantId=assistantId,
                conversation_id=conversation_id,
            )
        )

        self.update_conversation(new_conversation.id, messages)

    def update_conversation_with_evals(
        self,
        conversation_id: str,
        new_messages: list[Message],
        assistant_id: str,
    ):
        try:
            message_selection = 2
            previous_messages = self.db_service.get_last_n_messages(conversation_id, message_selection)
            previous_messages.reverse() # reverse to read in conversational order

            # first, add the new messages to the conversation, then return the updated conversation
            self.add_messages_to_conversation(
                conversation_id=conversation_id, messages=new_messages
            )

            # then, run the analytics evaluation pipeline
            self.evaluation_service.run(
                user_message=new_messages[0],
                response_message=new_messages[1],
                assistant_id=assistant_id,
                previous_messages=previous_messages,
            )

            return self.read_conversation(conversationId=conversation_id)

        except Exception as e:
            logger.error("Error saving conversation with evals", exc_info=e)
            return None


def get_conversation_service() -> ConversationService:
    """Returns a conversation service"""
    return ConversationService()
