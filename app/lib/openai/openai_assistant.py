from logging import getLogger
from typing import Callable, List, Optional, Dict
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from openai import OpenAI
from openai.types.beta.threads import (
    TextContentBlock as MessageContentText,
    Message as ThreadMessage,
)
from app.lib.models.conversations import Message, Role
from app.lib.openai import get_openai_client
from app.lib.openai.formatting import pprint_messages
from app.lib.openai.utils import combine_strings
from .openai_thread import (
    OpenAIThread,
    get_text_content_from_thread_message,
)
from .openai_annotations import OpenAIAnnotations

from app.lib.openai.openai_tool import (
    ExposeSyncMethodsMixin,
    OpenAITool,
    expose_sync_method,
)

logger = getLogger("Assistants")

load_dotenv()


class OpenAIAssistant(BaseModel, ExposeSyncMethodsMixin):
    """Assistant that can run tools"""

    id: Optional[str] = None
    name: str
    model: str = "gpt-3.5-turbo-1106"
    instructions: Optional[str] = None
    tools: List[OpenAITool] = []
    file_ids: List[str] = []
    metadata: Dict[str, str] = {}
    client: OpenAI = None

    default_thread: OpenAIThread = Field(
        default_factory=OpenAIThread,
        repr=False,
        description="A default thread for the assistant.",
    )

    # arbitrary types allowed
    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        name: str,
        id: Optional[str] = None,
        instructions: Optional[str] = None,
        tools: List[OpenAITool] = [],
        sync_on_init: bool = True,
        file_ids: List[str] = [],
    ):
        client = get_openai_client()
        super().__init__(
            id=id,
            name=name,
            instructions=instructions,
            tools=tools,
            client=client,
            file_ids=file_ids,
        )

        self.create(sync_on_init)

    def clear_default_thread(self):
        self.default_thread = OpenAIThread()

    def get_instructions(self) -> str:
        return self.instructions or ""

    def get_tools(self) -> list[OpenAITool]:
        return [
            (tool if isinstance(tool, OpenAITool) else OpenAITool.from_function(tool))
            for tool in self.tools
        ]

    @staticmethod
    def from_id(id: str):
        client = get_openai_client()
        assistant = client.beta.assistants.retrieve(assistant_id=id)

        return OpenAIAssistant(
            id=assistant.id,
            name=assistant.name,
            instructions=assistant.instructions,
            tools=[],
            sync_on_init=False,
            file_ids=[],
        )

    def create(self, sync_on_init: bool = True):
        client = self.client
        # first check if assistant exists by id if the id is not none
        assistant = None
        if self.id is not None:
            try:
                assistant = client.beta.assistants.retrieve(assistant_id=self.id)
            except Exception:
                pass

        if assistant is None or self.id is None:
            print(f"==>> creating assistant: {self.name}")
            # create assistant
            assistant = client.beta.assistants.create(
                # exclude id and client
                **self.dict(
                    exclude={"id", "client", "default_thread"}
                ),
            )
            self.id = assistant.id

        else:
            if sync_on_init:
                # update assistant to make sure its in sync
                assistant = client.beta.assistants.update(
                    assistant_id=self.id,
                    **self.dict(
                        exclude={
                            "id",
                            "client",
                            "default_thread",
                        }
                    ),
                )

    @expose_sync_method("greet")
    async def greet_async(
        self,
        greeting: Optional[str] = "Greet me by name",
        additional_instructions: Optional[str] = None,
        print_messages: Optional[bool] = True,
    ) -> tuple[OpenAIThread, list[ThreadMessage], any]:
        """Convenience method to add a greeting message to the default thread and return the assistant response"""
        # get the default thread (which is created on init as a new thread)
        thread = self.default_thread

        # add user greeting message to thread
        user_message = thread.add(message=greeting)

        # run the thread
        run = await thread.run_async(
            assistant=self, additional_instructions=additional_instructions
        )

        # get the thread messages
        thread_messages: list[ThreadMessage] = thread.get_messages(
            after_message=user_message.id
        )

        if print_messages:
            pprint_messages(messages=thread_messages)

        return thread, thread_messages, run

    @expose_sync_method("say")
    async def say_async(
        self,
        message: str,
        additional_instructions: Optional[str] = None,
        thread_id: Optional[str] = None,
        print_messages: Optional[bool] = True,
    ) -> tuple[OpenAIThread, list[ThreadMessage], ThreadMessage, any]:
        """Convenience method to add a user message to a thread and return the response"""

        try: 
            # get the thread
            thread: OpenAIThread = None
            if thread_id is None or thread_id == "":
                thread = self.default_thread
            else:
                thread = OpenAIThread(id=thread_id)

            # add user message to thread
            user_message = thread.add(message=message)

            # run the thread
            run = await thread.run_async(
                assistant=self, additional_instructions=additional_instructions
            )

            # get the thread messages
            thread_messages: list[ThreadMessage] = thread.get_messages(
                after_message=user_message.id
            )

            if print_messages:
                pprint_messages(messages=[user_message] + thread_messages)

            return thread, thread_messages, user_message, run
        except Exception as e:
            print(f"==>> error: {e}")
    
    # def pre_run_hook(self, run: any):
    #     """Hook that runs before the run is executed"""

    #     if self.pre_run_hook_callback:
    #         self.pre_run_hook_callback(run)

    # def post_run_hook(self, run: any):
    #     pass

    @expose_sync_method("say_fn")
    async def say_fn_async(self, message: str) -> str:
        thread = self.default_thread

        # add user message to thread
        user_message = thread.add(message=message)

        # run the thread
        await thread.run_async(assistant=self, additional_instructions=None)

        # get the thread messages
        thread_messages: list[ThreadMessage] = thread.get_messages(
            after_message=user_message.id
        )

        cleaned_message_contents: list[str] = []
        annotations: list[dict] = []
        for thread_message in thread_messages:
            result = OpenAIAnnotations.remove_and_extract_from_message(thread_message)
            content = result["content"]
            message_annotations = result["annotations"]

            # if found_annotations and list length > 0
            if message_annotations:
                annotations.extend(message_annotations)

            cleaned_message_contents.append(content)

        assistant_response_content: str = combine_strings(*cleaned_message_contents)

        return assistant_response_content

    def format_response_message(self, message: ThreadMessage):
        """Extracts the annotations from a message."""
        client = self.client

        message_content = message.content

        # message_content is an array of MessageContent objects - one for text and one for file
        # first, get the text message content
        message_content_text: MessageContentText = None

        response = {
            "id": "",
            "value": "",
            "cited_value": "",
            "citations": [],
            "file": {"file_id": "", "file_url": ""},
            "thread_message": message.dict(),
        }

        for content in message_content:
            if content.type == "text":
                message_content_text = content
            elif content.type == "image_file":
                message_content_file = content

        if message_content_text is not None:
            annotations = message_content_text.text.annotations
            print(f"==>> annotations: {annotations}")
            citations = []

            cited_content = ""

            # Iterate over the annotations and add footnotes
            for index, annotation in enumerate(annotations):
                # Replace the text with a footnote
                cited_content = message_content_text.text.value.replace(
                    annotation.text, f" [{index}]"
                )

                # replace the text with an empty string
                message_content_text.text.value = (
                    message_content_text.text.value.replace(annotation.text, "")
                )

                # Gather citations based on annotation attributes
                if file_citation := getattr(annotation, "file_citation", None):
                    cited_file = client.files.retrieve(file_citation.file_id)
                    citations.append(
                        f"[{index}] {file_citation.quote} from {cited_file.filename}"
                    )
                elif file_path := getattr(annotation, "file_path", None):
                    cited_file = client.files.retrieve(file_path.file_id)
                    citations.append(
                        f"[{index}] Click <here> to download {cited_file.filename}"
                    )
                    # Note: File download functionality not implemented above for brevity

            # Add footnotes to the end of the message before displaying to user
            message_content_value = message_content_text.text.value

            response["id"] = message.id
            response["value"] = message_content_value
            response["cited_value"] = cited_content
            response["citations"] = citations

        return response

    def as_tool(
        self, name: Optional[str] = None, description: Optional[str] = ""
    ) -> OpenAITool:
        """Converts the assistant into a tool"""
        # remove spaces from name and replace wit '_'
        name = name if name else self.name.replace(" ", "_")

        return OpenAITool.from_function(
            self.say_fn_async, name=name, description=description
        )

    @expose_sync_method("start_chat")
    async def start_chat_async(
        self,
        additional_instructions: Optional[str] = None,
        should_greet: bool = False,
    ) -> Message:
        try:
            if not should_greet:
                thread = self.default_thread

                metadata = {
                    "conversation_id": thread.id,
                    "greeting": False,
                    "openai": {
                        "thread_id": thread.id,
                    },
                }

                response_message = Message(
                    role=Role.ASSISTANT.value,
                    content="",
                    metadata=metadata,
                )

                return response_message

            thread, assistant_thread_messages, run = await self.greet_async(
                additional_instructions=additional_instructions, print_messages=True
            )

            assistant_response_thread_message = assistant_thread_messages[0]

            content = get_text_content_from_thread_message(
                assistant_response_thread_message
            )

            metadata = {
                "conversation_id": thread.id,
                "greeting": True,
                "openai": {
                    "thread_id": thread.id,
                    "thread_message": assistant_response_thread_message.model_dump(),
                    "additional_instructions": additional_instructions,
                },
            }

            response_message = Message(
                id=assistant_response_thread_message.id,
                role=Role.ASSISTANT.value,
                content=content,
                metadata=metadata,
            )

            return response_message

        except Exception as e:
            print(f"==>> error: {e}")

            error_message = "Oops! It seems like we're experiencing technical difficulties right now. Our team is actively working to resolve the issue. Please check back shortly. Thank you for your patience."
            metadata = {"error": str(e)}

            message = Message(
                role=Role.ASSISTANT.value,
                content=error_message,
                metadata=metadata,
            )

            return message

    @expose_sync_method("chat")
    async def chat_async(
        self,
        message: str,
        thread_id: Optional[str] = None,
        additional_instructions: Optional[str] = None,
    ) -> tuple[Message, Message]:
        try:
            (
                thread,
                assistant_thread_messages,
                user_thread_message,
                run
            ) = await self.say_async(
                message=message,
                thread_id=thread_id,
                additional_instructions=additional_instructions,
            )
            last_assistant_thread_message = assistant_thread_messages[-1]

            # PROCESS THREAD MESSAGES INTO ASSISTANT RESPONSE
            cleaned_message_contents: list[str] = []
            annotations: list[dict] = []
            for thread_message in assistant_thread_messages:
                result = OpenAIAnnotations.remove_and_extract_from_message(
                    thread_message
                )
                content = result["content"]
                message_annotations = result["annotations"]

                # if found_annotations and list length > 0
                if message_annotations and len(message_annotations) > 0:
                    for found_annotation in message_annotations:
                        annotations.append(found_annotation)

                cleaned_message_contents.append(content)

            assistant_response_content: str = combine_strings(*cleaned_message_contents)

            assistant_response_metadata = {
                "conversation_id": thread.id,
                "greeting": False,
                "openai": {
                    "additional_instructions": additional_instructions,
                    "annotations": annotations,
                    "thread_id": thread_id,
                    "thread_messages": [
                        m.model_dump() for m in assistant_thread_messages
                    ],
                },
            }

            # cleaned_last_assistant_thread_message_content = get_text_content_from_thread_message(
            clean_final_assistant_message = OpenAIAnnotations.remove_and_extract_from_message(
                    last_assistant_thread_message
                )

            assistant_response_message = Message(
                id=last_assistant_thread_message.id,
                role=Role.ASSISTANT.value,
                content=clean_final_assistant_message["content"],
                metadata=assistant_response_metadata,
            )

            user_response_message = Message(
                id=user_thread_message.id,
                role=Role.USER.value,
                content=message,
                metadata={
                    "conversation_id": thread.id,
                    "openai": {
                        "thread_id": thread_id,
                        "thread_messages": [user_thread_message.model_dump()],
                        "additional_instructions": additional_instructions,
                    },
                },
            )

            return assistant_response_message, user_response_message

        except Exception as e:
            print(f"==>> error: {e}")

            error_message = "Oops! It seems like we're experiencing technical difficulties right now. Our team is actively working to resolve the issue. Please check back shortly. Thank you for your patience."
            metadata = {"error": str(e)}

            message = Message(
                role=Role.ASSISTANT.value,
                content=error_message,
                metadata=metadata,
            )

            user_response_message = Message(
                id=user_thread_message.id,
                role=Role.USER.value,
                content=message,
                metadata={
                    "conversation_id": thread.id,
                    "openai": {
                        "thread_id": thread_id,
                        "thread_messages": [user_thread_message.model_dump()],
                        "additional_instructions": additional_instructions,
                    },
                },
            )

            return message
