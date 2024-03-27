import logging

from app.lib.services.database.category_topic_db import CategoryTopicDBService, get_category_topic_db_service
from app.lib.services.database.topic_db import TopicDBService, get_topic_db_service

logger = logging.getLogger(__name__)


class TopicService:
    def __init__(self, topic_db_service: TopicDBService = None, category_topic_db_service: CategoryTopicDBService = None):
        self.topic_db_service = topic_db_service or get_topic_db_service()
        self.category_topic_db_service = category_topic_db_service or get_category_topic_db_service()

    def handle_generated_topic(self, topic_name: str, category_id: str):
        """Handles a new topic being created, either by creating a new topic or returning an existing one and assigning it to the category"""

        try:
            db_topic = self.topic_db_service.get_by_name(topic_name)

            if not db_topic:
                # create a new topic for that name
                db_topic = self.topic_db_service.create(topic_name)

            db_category_topics = self.category_topic_db_service.get(
                topic_id=db_topic.id, category_id=category_id)

            if not db_category_topics:
                # create a new category_topic for the category and topic
                db_category_topics = self.category_topic_db_service.create(
                    category_id, db_topic.id)

            return db_topic

        except Exception as e:
            logger.error(f"Error handling generated topic: {e}")
            return None

    def get_existing_topics_from_category(self, category_id: str):
        """Gets a list of existing topics from the database by category ID"""

        logger.info(f"Getting topics for category ID: {category_id}")

        try:
            category_topics = self.category_topic_db_service.get_by_category_id(
                category_id)

            if not category_topics:
                logger.info(f"No topics found for category ID: {category_id}")
                return []

            topics = [
                category_topic.topic.name for category_topic in category_topics]
            print(f"Topics: {topics}")

            return topics
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return None


def get_topic_service() -> TopicService:
    return TopicService()
