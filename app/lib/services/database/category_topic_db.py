from datetime import datetime
import logging

from app.lib.prisma import prisma

logger = logging.getLogger(__name__)


class CategoryTopicDBService:
    def get(self, category_id: str, topic_id: str):
        """Gets a category_topic from the database"""

        logger.info(
            f"Getting category_topic for category ID: {category_id} and topic ID: {topic_id}")

        try:
            category_topic = prisma.categorytopic.find_first(
                where={"categoryId": category_id, "topicId": topic_id, "deletedAt": None}, include={"topic": True, "category": True})
            return category_topic
        except Exception as e:
            logger.error(f"Error getting category_topic: {e}")
            return None

    def get_by_category_id(self, category_id: str):
        """Gets a category_topic from the database"""

        logger.info(
            f"Getting category_topic for category ID: {category_id}")

        try:
            category_topic = prisma.categorytopic.find_many(
                where={"categoryId": category_id, "deletedAt": None}, include={"topic": True, "category": True})
            return category_topic
        except Exception as e:
            logger.error(f"Error getting category_topic: {e}")
            return None

    def get_by_topic_id(self, topic_id: str):
        """Gets a category_topic from the database"""

        logger.info(
            f"Getting category_topic for topic ID: {topic_id}")

        try:
            category_topic = prisma.categorytopic.find_many(
                where={"topicId": topic_id, "deletedAt": None}, include={"topic": True, "category": True})
            return category_topic
        except Exception as e:
            logger.error(f"Error getting category_topic: {e}")
            return None

    def get_all(self):
        """Gets all category_topics from the database"""

        logger.info("Getting all category_topics")

        try:
            category_topics = prisma.categorytopic.find_many(
                where={"deletedAt": None})
            return category_topics
        except Exception as e:
            logger.error(f"Error getting category_topics: {e}")
            return None

    def create(self, category_id: str, topic_id: str):
        """Creates a new category_topic in the database"""

        logger.info(
            f"Creating category_topic for category ID: {category_id} and topic ID: {topic_id}")

        try:
            category_topic = prisma.categorytopic.create(
                data={"categoryId": category_id, "topicId": topic_id})
        except Exception as e:
            logger.error(f"Error creating category_topic: {e}")
            return None

        return category_topic

    def delete(self, category_topic_id: str):
        """Deletes a category_topic in the database"""

        logger.info(
            f"Deleting category_topic for category_topic ID: {category_topic_id}")

        try:
            category_topic = prisma.categorytopic.update(where={"id": category_topic_id}, data={
                "deletedAt": datetime.now()})
        except Exception as e:
            logger.error(f"Error deleting category_topic: {e}")
            return None

        return category_topic


def get_category_topic_db_service() -> CategoryTopicDBService:
    return CategoryTopicDBService()
