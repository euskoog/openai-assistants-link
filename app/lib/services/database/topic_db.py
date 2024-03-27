from datetime import datetime
import logging

from app.lib.prisma import prisma

logger = logging.getLogger(__name__)


class TopicDBService:
    def get(self, topic_id: str):
        """Gets a topic from the database"""

        logger.info(f"Getting topic for topic ID: {topic_id}")

        try:
            topic = prisma.topic.find_unique(
                where={"id": topic_id, "deletedAt": None})
            return topic
        except Exception as e:
            logger.error(f"Error getting topic: {e}")
            return None

    def get_by_name(self, topic_name: str):
        """Gets a topic from the database by name"""

        logger.info(f"Checking for topic: '{topic_name}'")

        try:
            topic = prisma.topic.find_first(
                where={"name": topic_name, "deletedAt": None})
            return topic
        except Exception as e:
            logger.info(f"Error getting topic: {e}")
            return None

    def get_all(self):
        """Gets all topics from the database"""

        logger.info("Getting all topics")

        try:
            topics = prisma.topic.find_many(where={"deletedAt": None})
            return topics
        except Exception as e:
            logger.error(f"Error getting topics: {e}")
            return None

    def create(self, topic_name: str):
        """Creates a new topic in the database"""

        logger.info(f"Creating topic: '{topic_name}'")

        try:
            # create a topic only if one for the given name does not already exist
            topic = self.get_by_name(topic_name)
            if topic:
                logger.info(f"Topic '{topic_name}' already exists")
                return topic
            topic = prisma.topic.create(data={"name": topic_name})
            return topic
        except Exception as e:
            logger.error(f"Error creating topic: {e}")
            return None

    def update(self, topic_id: str, topic_name: str):
        """Updates an existing topic in the database"""

        logger.info(f"Updating topic: '{topic_id}'")

        try:
            topic = prisma.topic.update(where={"id": topic_id}, data={
                                        "name": topic_name, "updatedAt": datetime.now()})
            return topic
        except Exception as e:
            logger.error(f"Error updating topic: {e}")
            return None

    def delete(self, topic_id: str):
        """Deletes a topic from the database"""

        logger.info(f"Deleting topic: '{topic_id}'")

        try:
            topic = prisma.topic.update(where={"id": topic_id}, data={
                                        "deletedAt": datetime.now()})
            return topic
        except Exception as e:
            logger.error(f"Error deleting topic: {e}")
            return None


def get_topic_db_service() -> TopicDBService:
    return TopicDBService()
