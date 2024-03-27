from datetime import datetime
import logging

from app.lib.prisma import prisma

logger = logging.getLogger(__name__)


class CategoryDBService:
    def get(self, category_id: str):
        """Gets a category from the database"""

        logger.info(f"Getting category for category ID: {category_id}")

        try:
            category = prisma.category.find_unique(
                where={"id": category_id, "deletedAt": None})
            return category
        except Exception as e:
            logger.error(f"Error getting category: {e}")
            return None

    def get_all(self):
        """Gets all categories from the database"""

        logger.info("Getting all categories")

        try:
            categories = prisma.category.find_many(where={"deletedAt": None})
            return categories
        except Exception as e:
            logger.error(f"Error getting categories: {e}")
            return None
        
    def get_defaults(self):
        """Gets all default categories from the database"""

        logger.info("Getting all default categories")

        try:
            categories = prisma.category.find_many(
                where={"deletedAt": None, "type": "DEFAULT"})
            return categories
        except Exception as e:
            logger.error(f"Error getting default categories: {e}")
            return None

    def create(self, category_name: str, category_description: str, category_type: str = "CUSTOM"):
        """Creates a new category in the database"""

        logger.info(f"Creating category: '{category_name}'")

        try:
            category = prisma.category.create(
                data={"name": category_name, "description": category_description, "type": category_type, "createdAt": datetime.now(), "updatedAt": datetime.now()})
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            return None

        return category

    def update(self, category_id: str, category_name: str, category_description: str):
        """Updates a category in the database"""

        logger.info(f"Updating category: '{category_name}'")

        try:
            category = prisma.category.update(where={"id": category_id}, data={
                                              "name": category_name, "description": category_description, "updatedAt": datetime.now()})
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            return None

        return category

    def delete(self, category_id: str):
        """Deletes a category in the database"""

        logger.info(f"Deleting category for category ID: {category_id}")

        try:
            category = prisma.category.update(where={"id": category_id}, data={
                                              "deletedAt": datetime.now()})
        except Exception as e:
            logger.error(f"Error deleting category: {e}")
            return None

        return category


def get_category_db_service() -> CategoryDBService:
    return CategoryDBService()
