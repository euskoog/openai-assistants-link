import asyncio
from logging import getLogger
from typing import Any, Callable, Optional
from pydantic import BaseModel, Field, PrivateAttr
from openai.types.beta.threads import (
    Message as ThreadMessage,
)
from app.lib.openai import get_openai_client
from app.lib.openai.formatting import pprint_message

from app.lib.openai.openai_tool import (
    ExposeSyncMethodsMixin,
    expose_sync_method,
)

logger = getLogger("Threads")


class OpenAIThread(BaseModel, ExposeSyncMethodsMixin):
    """
    The Thread class represents a conversation thread with an assistant.

    Attributes:
        id (Optional[str]): The unique identifier of the thread. None if the thread
                            hasn't been created yet.
        metadata (dict): Additional data about the thread.
    """

    id: Optional[str] = None
    metadata: dict = {}
    messages: list[ThreadMessage] = Field([], repr=False)

    default_run: Any = Field(None, repr=False)

    def __init__(self, id: Optional[str] = None, metadata: dict = {}, **kwargs):
        super().__init__(id=id, metadata=metadata, **kwargs)

        if self.id is None:
            self.create(**kwargs)

    def create(self, messages: list[str] = None):
        """
        Creates a thread.
        """
        if self.id is not None:
            print("Thread has already been created.")
            raise ValueError("Thread has already been created.")
        if messages is not None:
            messages = [{"role": "user", "content": message} for message in messages]
        client = get_openai_client()

        response = client.beta.threads.create(messages=messages)
        self.id = response.id

        return self

    def add(self, message: str, role: str = "user") -> ThreadMessage:
        """
        Add a user message to the thread.
        """
        client = get_openai_client()

        if self.id is None:
            self.create()

        response = client.beta.threads.messages.create(
            thread_id=self.id, role=role, content=message
        )
        response.status = "completed" # else returns as NoneType
        return ThreadMessage(**response.model_dump())

    def get_messages(
        self,
        limit: int = None,
        before_message: Optional[str] = None,
        after_message: Optional[str] = None,
    ) -> list[ThreadMessage]:
        """
        Asynchronously retrieves messages from the thread.

        Args:
            limit (int, optional): The maximum number of messages to return.
            before_message (str, optional): The ID of the message to start the list from,
                                             retrieving messages sent before this one.
            after_message (str, optional): The ID of the message to start the list from,
                                            retrieving messages sent after this one.


        Returns:
            list[ThreadMessage]: A list of messages from the thread.
        """

        if self.id is None:
            self.create()

        client = get_openai_client()

        response = client.beta.threads.messages.list(
            thread_id=self.id,
            # note that because messages are returned in descending order,
            # we reverse "before" and "after" to the API
            before=after_message,
            after=before_message,
            limit=limit,
            order="desc",
        )

        response = reversed(response.data)

        response_messages: list[ThreadMessage] = []

        for message in response:
            response_messages.append(message)

        return response_messages

    @expose_sync_method("create_default_run")
    async def create_default_run_async(self, assistant: "OpenAIAssistant"):
        """
        Creates and returns a `Run` of this thread with the provided assistant.

        Args:
            assistant (Assistant): The assistant to run the thread with.
            run_kwargs: Additional keyword arguments to pass to the Run constructor.
        """
        from .openai_run import OpenAIRun

        run = OpenAIRun(assistant=assistant, thread=self)

        self.default_run = run

    @expose_sync_method("run")
    async def run_async(self, assistant: "OpenAIAssistant", **run_kwargs):
        """
        Creates and returns a `Run` of this thread with the provided assistant.

        Args:
            assistant (Assistant): The assistant to run the thread with.
            run_kwargs: Additional keyword arguments to pass to the Run constructor.
        """
        if self.id is None:
            self.create()

        from .openai_run import OpenAIRun

        run = OpenAIRun(assistant=assistant, thread=self, **run_kwargs)
        return await run.run_async()


class ThreadMonitor(BaseModel, ExposeSyncMethodsMixin):
    """
    The ThreadMonitor class represents a monitor for a specific thread.

    Attributes:
        thread_id (str): The unique identifier of the thread being monitored.
        last_message_id (Optional[str]): The ID of the last message received in the thread.
        on_new_message (Callable): A callback function that is called when a new message
                                   is received in the thread.
    """

    thread_id: str
    last_message_id: Optional[str] = None
    on_new_message: Callable = Field(default=pprint_message)
    _thread: OpenAIThread = PrivateAttr()
    _stop: bool = PrivateAttr(default=False)

    @property
    def thread(self):
        return self._thread

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._thread = OpenAIThread(id=kwargs["thread_id"])

    def run_once(self):
        messages = self.get_latest_messages()
        for msg in messages:
            if self.on_new_message:
                self.on_new_message(msg)

    @expose_sync_method("run")
    async def run_async(self, interval_seconds: int = None):
        """
        Run the thread monitor in a loop, checking for new messages every `interval_seconds`.

        Args:
            interval_seconds (int, optional): The number of seconds to wait between
                                              checking for new messages. Default is 1.
        """
        print("Running thread monitor...")
        if interval_seconds is None:
            interval_seconds = 1
        if interval_seconds < 1:
            raise ValueError("Interval must be at least 1 second.")

        while not self._stop:
            try:
                self.run_once()
            except KeyboardInterrupt:
                logger.debug("Keyboard interrupt received; exiting thread monitor.")
                break
            except Exception as exc:
                logger.error(f"Error refreshing thread: {exc}")
            await asyncio.sleep(interval_seconds)

    def get_latest_messages(self) -> list[ThreadMessage]:
        limit = 20

        # Loop to get all new messages in batches of 20
        while True:
            messages = self.thread.get_messages(
                after_message=self.last_message_id, limit=limit
            )

            # often the API will retrieve messages that have been created but
            # not populated with text. We filter out these empty messages.
            filtered_messages = []
            for i, msg in enumerate(messages):
                skip_message = False
                for c in msg.content:
                    if getattr(getattr(c, "text", None), "value", None) == "":
                        skip_message = True
                if not skip_message:
                    filtered_messages.append(msg)

            if filtered_messages:
                self.last_message_id = filtered_messages[-1].id

            if len(messages) < limit:
                break

        return filtered_messages

    def stop(self):
        """
        Stops the thread monitor.
        """
        self._stop = True


def get_text_content_from_thread_message(message: ThreadMessage):
    """
    Returns the content of a ThreadMessage as a string.

    Args:
        message (ThreadMessage): A message object

    Returns:
        str: The content of the message.
    """
    content = ""

    for item in message.content:
        if item.type == "text":
            content += item.text.value + "\n\n"

    return content


def get_text_content_from_thread_messages(messages: list[ThreadMessage]):
    """
    Returns the content of a list of ThreadMessages as a string.

    Args:
        messages (list[ThreadMessage]): A list of message objects

    Returns:
        str: The content of the messages.
    """
    content = ""

    for message in messages:
        content += get_text_content_from_thread_message(message) + "\n\n"

    return content
