from datetime import datetime
import logging

from fastapi import HTTPException

from app.lib.prisma import prisma

logger = logging.getLogger(__name__)


class AssistantCategoryDBService:
    def create(self, assistant_id: str, category_id: str):
        """Creates a new assistant_category in the database"""

        logger.info(
            f"Creating assistant_category for assistant ID: {assistant_id} and category ID: {category_id}")

        try:
            assistant_category = prisma.assistantcategory.create(
                data={"assistantId": assistant_id, "categoryId": category_id})
        except Exception as e:
            logger.error(f"Error creating assistant_category: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to create assistant category"
            )

        return assistant_category

    def get_by_assistant_id(self, assistant_id: str):
        """Gets a assistant_category from the database"""

        logger.info(
            f"Getting assistant_category for assistant ID: {assistant_id}")

        try:
            assistant_category = prisma.assistantcategory.find_unique(
                where={"assistantId": assistant_id, "deletedAt": None})
            return assistant_category
        except Exception as e:
            logger.error(f"Error getting assistant_category: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to get assistant category"
            )

    def get_all(self):
        """Gets all assistant_categories from the database"""

        logger.info("Getting all assistant_categories")

        try:
            assistant_categories = prisma.assistantcategory.find_many(
                where={"deletedAt": None})
            return assistant_categories
        except Exception as e:
            logger.error(f"Error getting assistant_categories: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to get assistant categories"
            )

    def delete(self, assistant_category_id: str):
        """Deletes a assistant_category in the database"""

        logger.info(
            f"Deleting assistant_category for assistant_category ID: {assistant_category_id}")

        try:
            assistant_category = prisma.assistantcategory.update(where={"id": assistant_category_id}, data={
                "deletedAt": datetime.now()})
        except Exception as e:
            logger.error(f"Error deleting assistant_category: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to delete assistant category"
            )

        return assistant_category


def get_assistant_category_db_service() -> AssistantCategoryDBService:
    return AssistantCategoryDBService()
