import logging

from app.lib.prisma import prisma

from app.lib.models.response import Response

logger = logging.getLogger(__name__)


class AnalyticsService:
    @staticmethod
    def format_tuple_for_sql(values: list):
        if not values:
            return "('')"
        return tuple(values) if len(values) > 1 else f"('{values[0]}')"

    def get_categories_for_assistants(self, assistant_ids: list):
        try:
            categories = prisma.query_raw(f"""
                SELECT
                    c.id,
                    c.name,
                    ac."assistantId"
                FROM
                    "Category" c
                JOIN
                    "AssistantCategory" ac ON c.id = ac."categoryId"
                WHERE
                    ac."assistantId" IN {self.format_tuple_for_sql(assistant_ids)}
                UNION
                SELECT
                    c.id,
                    c.name,
                    NULL AS assistantId
                FROM
                    "Category" c
                WHERE
                    c.type = 'DEFAULT'
            """)

            return categories
        except Exception as e:
            logger.error("Error getting categories for assistants", exc_info=e)
            return Response(success=False, error=str(e))

    def get_topics_count(self, assistant_ids: list):
        try:
            topics = prisma.query_raw(f"""
                SELECT
                    c."assistantId",
                    cat.id AS "categoryId",
                    cat.name AS "categoryName",
                    t.id AS "topicId",
                    t.name AS "topicName",
                    COUNT(m.id) AS "topicCount",
                    SUM(CASE WHEN m.metadata->>'classification' = 'Answered' THEN 1 ELSE 0 END) AS "numAnswered",
                    SUM(CASE WHEN m.metadata->>'classification' = 'Not Answered' THEN 1 ELSE 0 END) AS "numNotAnswered",
                    SUM(CASE WHEN m.metadata->>'classification' = 'Not Allowed' THEN 1 ELSE 0 END) AS "numNotAllowed"
                FROM
                    "Conversation" c
                JOIN
                    "Message" m ON c.id = m."conversationId"
                JOIN
                    "Category" cat ON m."categoryId" = cat.id
                JOIN
                    "Topic" t ON m."topicId" = t.id
                WHERE
                    c."assistantId" IN {self.format_tuple_for_sql(assistant_ids)}
                GROUP BY
                    c."assistantId", cat.id, cat.name, t.id, t.name;
            """)

        except Exception as e:
            logger.error("Error getting topic count", exc_info=e)
            return Response(success=False, error=str(e))

        return topics

    def get_topic_messages(
        self,
        topic_id: str,
        assistant_ids: list,
        category_id: str,
        answer_types: list,
    ):
        try:
            messages = prisma.query_raw(f"""
                SELECT
                    m.id,
                    m.content,
                    m.timestamp,
                    m.metadata->>'classification' AS classification,
                    m.metadata->>'sentiment' AS sentiment,
                    m."conversationId" AS "conversationId",
                    c."assistantId" AS "assistantId"
                FROM
                    "Conversation" c
                JOIN
                    "Message" m ON c.id = m."conversationId"
                JOIN
                    "Category" cat ON m."categoryId" = cat.id
                WHERE
                    cat.id = '{category_id}'
                    AND c."assistantId" IN {self.format_tuple_for_sql(assistant_ids)}
                    AND m."topicId" = '{topic_id}'
                    AND m.metadata->>'classification' IN {self.format_tuple_for_sql(answer_types)}
                ORDER BY
                    m."timestamp" DESC
            """)

            return messages

        except Exception as e:
            logger.error("Error getting topic messages", exc_info=e)
            return Response(success=False, error=str(e))


def get_analytics_service() -> AnalyticsService:
    return AnalyticsService()
