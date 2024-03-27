import asyncio
from logging import getLogger
from typing import Callable, Optional, Union
from pydantic import BaseModel, Field
from app.lib.openai import get_openai_client
from .openai_assistant import OpenAIAssistant
from .openai_thread import OpenAIThread

from app.lib.openai.openai_tool import (
    ExposeSyncMethodsMixin,
    OpenAITool,
    call_function_tool,
    expose_sync_method,
)
from app.lib.openai.utils import CancelRun
from openai.types.beta.threads.run import Run
from openai.types.beta.threads.runs import RunStep as OpenAIRunStep

logger = getLogger("Runs")


class OpenAIRun(BaseModel, ExposeSyncMethodsMixin):
    thread: OpenAIThread
    assistant: OpenAIAssistant
    instructions: Optional[str] = Field(
        None, description="Replacement instructions to use for the run."
    )
    additional_instructions: Optional[str] = Field(
        None,
        description=(
            "Additional instructions to append to the assistant's instructions."
        ),
    )
    tools: Optional[list[Union[OpenAITool, Callable]]] = Field(
        None, description="Replacement tools to use for the run."
    )
    additional_tools: Optional[list[OpenAITool]] = Field(
        None,
        description="Additional tools to append to the assistant's tools. ",
    )
    run: Run = None
    data: dict = {}
    steps: list[OpenAIRunStep] = []

    @expose_sync_method("refresh")
    async def refresh_async(self):
        """Refreshes the run."""
        client = get_openai_client()
        self.run = client.beta.threads.runs.retrieve(
            run_id=self.run.id, thread_id=self.thread.id
        )

    @expose_sync_method("cancel")
    async def cancel_async(self):
        """Cancels the run."""
        client = get_openai_client()
        client.beta.threads.runs.cancel(run_id=self.run.id, thread_id=self.thread.id)

    @expose_sync_method("refresh_run_steps")
    async def refresh_run_steps_async(self):
        """
        Asynchronously refreshes and updates the run steps list.

        This function fetches the latest run steps up to a specified limit and
        checks if the latest run step in the current run steps list
        (`self.steps`) is included in the new batch. If the latest run step is
        missing, it continues to fetch additional run steps in batches, up to a
        maximum count, using pagination. The function then updates
        `self.steps` with these new run steps, ensuring any existing run steps
        are updated with their latest versions and new run steps are appended in
        their original order.
        """
        # fetch up to 100 run steps
        max_fetched = 100
        limit = 50
        max_attempts = max_fetched / limit + 2

        # Fetch the latest run steps
        client = get_openai_client()

        response = client.beta.threads.runs.steps.list(
            run_id=self.run.id,
            thread_id=self.thread.id,
            limit=limit,
        )
        run_steps = list(reversed(response.data))

        if not run_steps:
            return

        # Check if the latest run step in self.steps is in the new run steps
        latest_step_id = self.steps[-1].id if self.steps else None
        missing_latest = (
            latest_step_id not in {rs.id for rs in run_steps}
            if latest_step_id
            else True
        )

        # If the latest run step is missing, fetch additional run steps
        total_fetched = len(run_steps)
        attempts = 0
        while (
            run_steps
            and missing_latest
            and total_fetched < max_fetched
            and attempts < max_attempts
        ):
            attempts += 1
            response = client.beta.threads.runs.steps.list(
                run_id=self.run.id,
                thread_id=self.thread.id,
                limit=limit,
                # because this is a raw API call, "after" refers to pagination
                # in descnding chronological order
                after=run_steps[0].id,
            )
            paginated_steps = list(reversed(response.data))

            total_fetched += len(paginated_steps)
            # prepend run steps
            run_steps = paginated_steps + run_steps
            if any(rs.id == latest_step_id for rs in paginated_steps):
                missing_latest = False

        # Update self.steps with the latest data
        new_steps_dict = {rs.id: rs for rs in run_steps}
        for i in range(len(self.steps) - 1, -1, -1):
            if self.steps[i].id in new_steps_dict:
                self.steps[i] = new_steps_dict.pop(self.steps[i].id)
            else:
                break
        # Append remaining new run steps at the end in their original order
        self.steps.extend(new_steps_dict.values())

    def get_steps(self) -> list[OpenAIRunStep]:
        if self.steps is None:
            self.steps = []
        return self.steps

    def get_instructions(self) -> str:
        if self.instructions is None:
            instructions = self.assistant.get_instructions() or ""
        else:
            instructions = self.instructions

        if self.additional_instructions is not None:
            instructions = "\n\n".join([instructions, self.additional_instructions])

        return instructions

    def get_tools(self) -> list[OpenAITool]:
        tools = []
        if self.tools is None:
            tools.extend(self.assistant.get_tools())
        else:
            tools.extend(self.tools)
        if self.additional_tools is not None:
            tools.extend(self.additional_tools)

        return tools

    async def _handle_step_requires_action(self):
        client = get_openai_client()
        if self.run.status != "requires_action":
            return
        if self.run.required_action.type == "submit_tool_outputs":
            tool_outputs = []
            tools = self.get_tools()

            for tool_call in self.run.required_action.submit_tool_outputs.tool_calls:
                try:
                    output = call_function_tool(
                        tools=tools,
                        function_name=tool_call.function.name,
                        function_arguments_json=tool_call.function.arguments,
                        return_string=True,
                    )
                except CancelRun as exc:
                    logger.debug(f"Ending run with data: {exc.data}")
                    raise
                except Exception as exc:
                    output = f"Error calling function {tool_call.function.name}: {exc}"
                    logger.error(output)
                tool_outputs.append(
                    dict(tool_call_id=tool_call.id, output=output or "")
                )

                self.data["tool_outputs"] = tool_outputs

            client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id, run_id=self.run.id, tool_outputs=tool_outputs
            )

    async def run_async(self) -> "OpenAIRun":
        """Excutes a run asynchronously."""
        client = get_openai_client()

        create_kwargs = {}

        if self.instructions is not None or self.additional_instructions is not None:
            create_kwargs["instructions"] = self.get_instructions()

        create_kwargs["tools"] = self.get_tools()

        # async with self.assistant:
        self.run = client.beta.threads.runs.create(
            thread_id=self.thread.id,
            assistant_id=self.assistant.id,
            **create_kwargs,
        )

        # self.assistant.pre_run_hook(run=self.run)

        try:
            while self.run.status in ("queued", "in_progress", "requires_action"):
                if self.run.status == "requires_action":
                    await self._handle_step_requires_action()
                await asyncio.sleep(0.1)
                await self.refresh_async()
        except CancelRun as exc:
            logger.debug(f"`CancelRun` raised; ending run with data: {exc.data}")
            client.beta.threads.runs.cancel(
                run_id=self.run.id, thread_id=self.thread.id
            )
            self.data = exc.data
            self.refresh_async()

        if self.run.status == "failed":
            logger.debug(f"Run failed. Last error was: {self.run.last_error}")

        # self.assistant.post_run_hook(run=self.run)
        return self


class RunMonitor(BaseModel, ExposeSyncMethodsMixin):
    run_id: str
    thread_id: str
    steps: list[OpenAIRunStep] = []

    def __init__(self, thread_id: str, run_id: str):
        super().__init__(
            thread_id=thread_id,
            run_id=run_id,
        )

    def refresh_run_steps_async(self):
        """
        Asynchronously refreshes and updates the run steps list.

        This function fetches the latest run steps up to a specified limit and
        checks if the latest run step in the current run steps list
        (`self.steps`) is included in the new batch. If the latest run step is
        missing, it continues to fetch additional run steps in batches, up to a
        maximum count, using pagination. The function then updates
        `self.steps` with these new run steps, ensuring any existing run steps
        are updated with their latest versions and new run steps are appended in
        their original order.
        """
        # fetch up to 100 run steps
        max_fetched = 100
        limit = 50
        max_attempts = max_fetched / limit + 2

        # Fetch the latest run steps
        client = get_openai_client()

        response = client.beta.threads.runs.steps.list(
            run_id=self.run_id,
            thread_id=self.thread_id,
            limit=limit,
        )
        run_steps = list(reversed(response.data))

        # Check if the latest run step in self.steps is in the new run steps
        latest_step_id = self.steps[-1].id if self.steps else None
        missing_latest = (
            latest_step_id not in {rs.id for rs in run_steps}
            if latest_step_id
            else True
        )

        # If the latest run step is missing, fetch additional run steps
        total_fetched = len(run_steps)
        attempts = 0
        while (
            run_steps
            and missing_latest
            and total_fetched < max_fetched
            and attempts < max_attempts
        ):
            attempts += 1
            response = client.beta.threads.runs.steps.list(
                run_id=self.run_id,
                thread_id=self.thread_id,
                limit=limit,
                # because this is a raw API call, "after" refers to pagination
                # in descnding chronological order
                after=run_steps[0].id,
            )
            paginated_steps = list(reversed(response.data))

            total_fetched += len(paginated_steps)
            # prepend run steps
            run_steps = paginated_steps + run_steps
            if any(rs.id == latest_step_id for rs in paginated_steps):
                missing_latest = False

        # Update self.steps with the latest data
        new_steps_dict = {rs.id: rs for rs in run_steps}
        for i in range(len(self.steps) - 1, -1, -1):
            if self.steps[i].id in new_steps_dict:
                self.steps[i] = new_steps_dict.pop(self.steps[i].id)
            else:
                break
        # Append remaining new run steps at the end in their original order
        self.steps.extend(new_steps_dict.values())
