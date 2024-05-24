import os
from typing import List, Literal, Optional
from openai import OpenAI
from pydantic import BaseModel

# load env vars
from dotenv import load_dotenv

load_dotenv()


class ChatCompletionMessage(BaseModel):
    role: Literal["user", "system"]
    content: str


class ChatCompletion:
    def __init__(
        self,
        llm_model: Optional[
            Literal["gpt-3.5-turbo"]
        ] = "gpt-3.5-turbo",
    ):
        self.client = OpenAI()
        self.client.api_key = os.environ.get("OPENAI_API_KEY")
        self.llm_model = llm_model

    def run(
        self, messages: List[ChatCompletionMessage] = [], raw_response: bool = False
    ):
        """Run chat completion

        Args:
            messages (List[ChatCompletionMessage], optional): List of messages. Defaults to [].
            raw_response (bool, optional): If true, returns raw openai chat completion response. If false, simply returns the message content. Defaults to False.

        Examples:
            >>> completion = ChatCompletion(llm_model="gpt-3.5-turbo")
            >>> completion.run(messages=[{"role": "user", "content": "Hello, I'm looking for a new job. Can you help me?"}])
        """

        response = self.client.chat.completions.create(
            model=self.llm_model,
            messages=messages,
        )

        if raw_response:
            return response
        else:
            return response.choices[0].message.content
