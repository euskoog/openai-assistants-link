import logging
from fastapi import APIRouter

from app.lib.models.response import Response
from app.lib.services.database.assistant_category_db import get_assistant_category_db_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/assistant-categories",
    tags=["assistant-categories"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def get_all_assistant_categories():
    """Gets all assistant categories"""
    logger.info("Getting all assistant categories")
    assistant_category_service = get_assistant_category_db_service()

    try:
        assistant_categories = assistant_category_service.get_all()
        return Response(data=assistant_categories, success=True)
    except Exception as e:
        logger.error(f"Error getting assistant categories: {e}")
        return Response(success=False, error=str(e))


@router.post("/", name="Create assistant category")
async def create_assistant_category(assistant_id: str, category_id: str):
    """Creates a new assistant category"""
    logger.info(f"Creating assistant category: '{assistant_id}'")
    assistant_category_service = get_assistant_category_db_service()

    try:
        assistant_category = assistant_category_service.create(
            assistant_id, category_id)
        return Response(data=assistant_category, success=True)
    except Exception as e:
        logger.error(f"Error creating assistant category: {e}")
        return Response(success=False, error=str(e))
