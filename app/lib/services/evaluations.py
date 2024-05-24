from typing import List
from fastapi import Depends
from jinja2 import Template
from textblob import TextBlob

from app.lib.models.evaluations import Evaluation, MessageAnalyticsUpdate
from app.lib.models.category import Category
from app.lib.models.conversations import Message

from app.lib.llms.chat_completion import ChatCompletion
from app.lib.llms.classification import Classification
from app.lib.openai.formatting import pprint_eval
from app.lib.openai.utils import clean_quotes, format_prompt_messages
from app.lib.prisma import prisma
from app.lib.services.database.category_db import CategoryDBService, get_category_db_service
from app.lib.services.database.conversation_db import ConversationDBService, get_conversation_db_service
from app.lib.services.topic import TopicService, get_topic_service


class EvaluationService:
    def __init__(self, category_db_service: CategoryDBService = None, topic_service: TopicService = None, conversation_db_service: ConversationDBService = None):
        self.category_db_service = category_db_service or get_category_db_service()
        self.topic_service = topic_service or get_topic_service()
        self.conversation_db_service = conversation_db_service or get_conversation_db_service()

    def get_classification(self, instructions: str, query: str, response: str):
        """Determines if the response satisfies the query, based on the instructions provided by the assistant"""

        try:
            classification_template = """
            ## Response Classification Task

            **Objective**: Assess and categorize the following response based on its accuracy, completeness, and appropriateness relative to the input query. Use the options provided to assign the most fitting category.

            ### Assistant Instructions
            {{ instructions }}

            ### Options and Descriptions
            - **Answered**: Use when the response accurately and completely addresses the query. Applicable even for vague questions if the response remains helpful.
            - **Not Answered**: Select this when the assistant fails to provide a relevant answer, or cannot utilize its tools effectively. This is also the choice for operational failures.
            - **Not Allowed**: Appropriate for responses outside the assistant's scope or domain. Use this for queries about real-time knowledge or events that the assistant cannot address with available tools.

            ### Input Query
            Please classify the following query/response pair:
            """

            template = Template(classification_template)
            prompt = template.render(instructions=instructions)

            options = ["Answered", "Not Answered", "Not Allowed"]
            input = f"Query: {query}\nResponse: {response}"

            classification = Classification(
                name="Validate response", description=prompt, options=options)
            result = classification.run(input=input)

            return result
        except Exception as e:
            print(f"Error getting classification: {e}")

    def categorize(self, instructions: str, query: str, categories: List[Category], previous_messages: list[Message],):
        """Assigns a category to a query based on a list of pre-determined categories"""

        category_names = [category.name for category in categories]
        categories_described = "\n".join(
            f"{category.name}: {category.description}" for category in categories)

        previous_messages_formatted = format_prompt_messages(previous_messages)

        print(f"Categories described:\n---------------------\n{categories_described}")

        categorization_prompt_template = """
        ## Query Categorization Task

        **Objective**: Categorize the following input query based on the descriptions provided for each category. Choose the most fitting category for the query.

        ### Instructions
        - **Read through the assistant's instructions** carefully to understand how to categorize queries.
        - **Review the categories and their descriptions** to familiarize yourself with the available options.
        - If the query fits into an existing category, assign it to that category.
        - Ensure the chosen category accurately reflects the query's content.
        - If previous messages exist, you may use them to build context for the query.

        ### Assistant Instructions
        {{ instructions }}

        ### Previous Messages
        {{ previous_messages }}

        ### Categories and Descriptions
        {{ categories_described }}

        ### Input Query
        Please categorize the following query:
        """

        template = Template(categorization_prompt_template)

        rendered_prompt = template.render(
            instructions=instructions,
            categories_described=categories_described,
            previous_messages=previous_messages_formatted
        )

        classification = Classification(
            name="Categorization", description=rendered_prompt, options=category_names)
        result = classification.run(input=query)

        # return the entry from categories[] that matches the result
        selected_category = next(
            (category for category in categories if category.name == result), None)

        return selected_category

    def get_sentiment(self, query: str):
        """Get the sentiment of a query using TextBlob"""

        blob = TextBlob(query)

        # Get the sentiment polarity (positive: 1, negative: -1, neutral: 0)
        sentiment_polarity = blob.sentiment.polarity

        return sentiment_polarity

    def get_topic(self, query: str, category: Category, previous_messages: list[Message], topic_service: TopicService = Depends(get_topic_service)):
        """Assigns a topic to a query based on a list of pre-determined topics"""

        category_name = category.name
        category_topics = topic_service.get_existing_topics_from_category(
            category.id)
        
        previous_messages_formatted = format_prompt_messages(previous_messages)

        topic_assignment_prompt = """
        ## Topic Assignment

        **Objective**: Assign an appropriate topic to the following input query within the specified category.

        ### Context
        Existing Topics (if applicable) for {{ category_name }}:
        {{ category_topics }}

        If the query can be matched with an existing topic within the specified category, assign that topic. If not, create a new topic based on the query. If you are assigning a new topic, be as general as possible. Try to limit topics to one word unless absolutely necessary- the more concise the better. Remember, the topic cannot be the same as the category.

        Example:
        User Query: "Who is the current president"
        Category: Other
        Assigned Topic: Politics

        User Query: "Where can I edit my profile avatar?"
        Category: Profile
        Assigned Topic: Avatar

        Remeber that under NO circumstance can the topic be the same as the category. Do not add quotes or any other characters alongside the generated topic. Please assign a short and concise topic to the following query:

        ### Previous Messages
        {{ previous_messages }}

        ### Data
        User Query: {{ query }}
        Category: {{ category_name }}
        Assigned Topic:
        """

        template = Template(topic_assignment_prompt)

        rendered_prompt = template.render(
            query=query, category_name=category_name, category_topics=category_topics, previous_messages=previous_messages_formatted
        )

        completion = ChatCompletion(llm_model="gpt-3.5-turbo")
        result = completion.run(
            messages=[{"role": "system", "content": rendered_prompt}])

        # Clean the result if necessary
        cleaned_result = clean_quotes(result)

        return cleaned_result

    def run(self, user_message: Message, response_message: Message, assistant_id: str, previous_messages: List[Message] = None):
        """Run the full evaluation pipeline"""

        try:
            assistant = prisma.assistant.find_unique(
                where={"id": assistant_id}, include={"assistantCategory": {"include": {"category": True}}})

            assistant_categories = assistant.assistantCategory
            instructions = assistant.instructions

            default_categories = get_category_db_service().get_defaults()
            other_category = next(
                (category for category in default_categories if category.name == "Other"), None)

            # If an assistant doesn't have categories, use the default categories
            categories = default_categories if len(
                assistant_categories) < 1 else [category.category for category in assistant_categories]  # will need to change

            # 1. Get the classification of the query and response
            classification = self.get_classification(instructions=instructions,
                                                     query=user_message.content, response=response_message.content)

            # 2. Get the sentiment of the query
            sentiment = self.get_sentiment(query=user_message.content)

            # 3. Categorize the query
            category = other_category if classification == "Not Allowed" else self.categorize(instructions=instructions,
                                                                                              query=user_message.content, categories=categories, previous_messages=previous_messages)

            # 4. Assign a topic to the query
            topic = self.get_topic(
                query=user_message.content, category=category, topic_service=self.topic_service, previous_messages=previous_messages)

            # 5. Link the topic to the category, return the topic as an object
            db_topic = self.topic_service.handle_generated_topic(
                topic_name=topic, category_id=category.id)

            pprint_eval(Evaluation(
                query=user_message.content, response=response_message.content, classification=classification, category=category.name, sentiment=sentiment, topic=topic
            ))

            # 6. Update the message in the database with the assistant ID
            self.conversation_db_service.update_message_analytics(
                message_id=user_message.id, analytics=MessageAnalyticsUpdate(
                    sentiment=sentiment, classification=classification, category_id=category.id, topic_id=db_topic.id, response_message_id=response_message.id
                )
            )

        except Exception as e:
            print(f"Error evaluating messages: {e}")


def get_evaluation_service() -> EvaluationService:
    return EvaluationService()
