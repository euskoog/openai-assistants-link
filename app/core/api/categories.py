from enum import Enum
import logging
from fastapi import APIRouter

from app.lib.models.response import Response
from app.lib.services.database.category_db import get_category_db_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/categories",
    tags=["categories"],
    responses={404: {"description": "Not found"}},
)

class CategoryType(Enum):
    CUSTOM = "CUSTOM"
    DEFAULT = "DEFAULT"


@router.get("/")
async def get_all_categories():
    """Gets all categories"""
    logger.info("Getting all categories")
    category_service = get_category_db_service()

    try:
        categories = category_service.get_all()
        return Response(data=categories, success=True)
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return Response(success=False, error=str(e))
    
@router.get("/defaults")
async def get_default_categories():
    """Gets all default categories"""
    logger.info("Getting all default categories")
    category_service = get_category_db_service()

    try:
        categories = category_service.get_defaults()
        return Response(data=categories, success=True)
    except Exception as e:
        logger.error(f"Error getting default categories: {e}")
        return Response(success=False, error=str(e))

@router.post("/", name="Create category")
async def create_category(name: str, description: str, type: CategoryType = "DEFAULT"):
    """Creates a new category"""
    logger.info(f"Creating category: '{name}'")
    category_service = get_category_db_service()

    try:
        category = category_service.create(name, description, type)
        return Response(data=category, success=True)
    except Exception as e:
        logger.error(f"Error creating category: {e}")
        return Response(success=False, error=str(e))


@router.put("/{category_id}", name="Update category")
async def update_category(category_id: str, name: str, description: str):
    """Updates a category"""
    logger.info(f"Updating category: '{name}'")
    category_service = get_category_db_service()

    try:
        category = category_service.update(category_id, name, description)
        return Response(data=category, success=True)
    except Exception as e:
        logger.error(f"Error updating category: {e}")
        return Response(success=False, error=str(e))


@router.delete("/{category_id}", name="Delete category")
async def delete_category(category_id: str):
    """Deletes a category"""
    logger.info(f"Deleting category: '{category_id}'")
    category_service = get_category_db_service()

    try:
        category = category_service.delete(category_id)
        return Response(data=category, success=True)
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        return Response(success=False, error=str(e))
