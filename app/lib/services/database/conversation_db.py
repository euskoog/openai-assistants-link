from prisma import Json
from app.lib.models.conversations import ConversationCreate, Message
from app.lib.models.evaluations import MessageAnalyticsUpdate
from app.lib.prisma import prisma


class ConversationDBService:       
    def read(self, conversation_id: str):
        return prisma.conversation.find_unique_or_raise(
            where={"id": conversation_id},
            include={"message": {"orderBy": {"timestamp": "asc"}}},
        )

    def read_all_by_assistant(self, assistantId: str):
        return prisma.conversation.find_many(
            where={"assistantId": assistantId, "deletedAt": None},
        )

    def create(self, body: ConversationCreate):
        metadata = {
            "openai": {
                "thread_id": body.conversation_id,
            }
        }

        return prisma.conversation.create(
            data={
                "id": body.conversation_id,
                "assistantId": body.assistant_id,
                "metadata": Json(metadata),
            }
        )

    def add_message(self, conversation_id: str, message: Message):
        data = {
            "conversationId": conversation_id,
            "role": message.role,
            "content": message.content,
            "metadata": Json(message.metadata)
            if message.metadata is not None
            else Json({}),
        }
        if message.id != "":
            data["id"] = message.id

        return prisma.message.create(data=data)
    
    def update_message_analytics(self, message_id: str, analytics: MessageAnalyticsUpdate):
        message = prisma.message.find_unique(
            where={"id": message_id})

        message_metadata = message.metadata

        new_metadata = {"sentiment": analytics.sentiment, "classification": analytics.classification,
                        "responseMessageId": analytics.response_message_id}

        prisma.message.update(where={"id": message_id}, data={"categoryId": analytics.category_id,
                                                              "topicId": analytics.topic_id,  "metadata": Json({**message_metadata, **new_metadata})})
        
    def get_last_n_messages(self, conversation_id: str, n: int):
        return prisma.message.find_many(
            where={"conversationId": conversation_id},
            order={"timestamp": "desc"},
            take=n,
            include={"category": True, "topic": True},
        )


def get_conversation_db_service() -> ConversationDBService:
    return ConversationDBService()
