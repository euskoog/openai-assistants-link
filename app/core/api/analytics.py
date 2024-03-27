import logging
from typing import List
from fastapi import APIRouter, Depends

from app.lib.prisma import prisma

from app.lib.models.response import Response
from app.lib.services.analytics import AnalyticsService, get_analytics_service
from app.lib.services.conversations import ConversationService, get_conversation_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
    responses={404: {"description": "Not found"}},
)


@router.get("/conversation", description="Get conversation with assistant data")
def get_conversation(
    conversation_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    try:
        conversation = conversation_service.read_conversation(
            conversationId=conversation_id
        )
        assistant = prisma.assistant.find_unique(where={"id": conversation.assistantId})

        conversation.assistant = assistant
        return {"data": conversation, "success": True}
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return Response(success=False, error=str(e))


@router.post(
    "/categories", description="Get all categories for a list of assistant IDs"
)
def get_categories(
    assistant_ids: List[str] = [],
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    try:
        categories = analytics_service.get_categories_for_assistants(
            assistant_ids=assistant_ids
        )
        return {"data": categories, "success": True}
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return Response(success=False, error=str(e))


@router.post("/topics/count", description="Get total topics for all assistants")
def get_topics_count(
    assistant_ids: List[str] = [],
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    try:
        total_topics = analytics_service.get_topics_count(
            assistant_ids=assistant_ids
        )

        return {"data": total_topics, "success": True}
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return Response(success=False, error=str(e))


@router.post("/topic/messages", description="Get messages for a topic")
def get_topic_messages(
    topic_id: str,
    assistant_ids: List[str],
    category_id: str,
    answer_types: List[str] = ["Answered", "Not Answered", "Not Allowed"],
    analytics_service: AnalyticsService = Depends(get_analytics_service),
):
    try:
        messages = analytics_service.get_topic_messages(
            topic_id=topic_id,
            assistant_ids=assistant_ids,
            category_id=category_id,
            answer_types=answer_types,
        )

        return {"data": messages, "success": True}
    except Exception as e:
        logger.error(f"Error getting topic messages: {e}")
        return Response(success=False, error=str(e))
