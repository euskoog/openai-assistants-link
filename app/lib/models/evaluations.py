from pydantic import BaseModel


class MessageAnalyticsUpdate(BaseModel):
    sentiment: float
    classification: str
    category_id: str
    topic_id: str
    response_message_id: str

class Evaluation(BaseModel):
    query: str
    response: str
    sentiment: float
    classification: str
    category: str
    topic: str