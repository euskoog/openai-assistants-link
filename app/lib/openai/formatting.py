import tempfile
from datetime import datetime

import openai
from openai.types.beta.threads import Message as ThreadMessage
from rich import box
from rich.console import Console
from rich.panel import Panel

from app.lib.models.evaluations import Evaluation


def download_temp_file(file_id: str, suffix: str = None):
    """
    Downloads a file from OpenAI's servers and saves it to a temporary file.

    Args:
        file_id: The ID of the file to be downloaded.
        suffix: The file extension to be used for the temporary file.

    Returns:
        The file path of the downloaded temporary file.
    """

    client = openai.Client()
    file_content_response = client.files.with_raw_response.retrieve_content(file_id)

    # Create a temporary file with a context manager to ensure it's cleaned up
    # properly
    with tempfile.NamedTemporaryFile(
        delete=False, mode="wb", suffix=f"{suffix}"
    ) as temp_file:
        temp_file.write(file_content_response.content)
        temp_file_path = temp_file.name  # Save the path of the temp file

    return temp_file_path


def pprint_message(message: ThreadMessage):
    """
    Pretty-prints a single message using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        message (ThreadMessage): A message object
    """
    console = Console()
    role_colors = {
        "user": "green",
        "assistant": "blue",
    }

    color = role_colors.get(message.role, "red")
    timestamp = datetime.fromtimestamp(message.created_at).strftime("%I:%M:%S %p")

    content = ""
    for item in message.content:
        if item.type == "text":
            content += item.text.value + "\n\n"
        elif item.type == "image_file":
            # Use the download_temp_file function to download the file and get
            # the local path
            local_file_path = download_temp_file(item.image_file.file_id, suffix=".png")
            # Add a clickable hyperlink to the content
            file_url = f"file://{local_file_path}"
            content += (
                "[bold]Attachment[/bold]:"
                f" [blue][link={file_url}]{local_file_path}[/link][/blue]\n\n"
            )

    for file_id in message.file_ids:
        content += f"Attached file: {file_id}\n"

    # Create the panel for the message
    panel = Panel(
        content.strip(),
        title=f"[bold]{message.role.capitalize()}[/]",
        subtitle=f"[dim]{message.thread_id}[/] - [dim]{message.id}[/] - [italic]{timestamp}[/]",
        title_align="left",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        width=100,  # Fixed width for all panels
        expand=True,  # Panels always expand to the width of the console
        padding=(1, 2),
    )

    # Printing the panel
    console.print(panel)


def pprint_eval(evaluation: Evaluation):
    """
    Pretty-prints a single message using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        evaluation (Evaluation): A evaluation object with analytics details
    """
    console = Console()

    color = "orange3"
    timestamp = (datetime.now()).strftime("%I:%M:%S %p")

    content = f"Query: {evaluation.query}\n\nResponse: {evaluation.response}\n\n{'Classification: '.ljust(20)}{evaluation.classification.rjust(74)}\n\n{'Category: '.ljust(20)}{evaluation.category.rjust(74)}\n\n{'Sentiment: '.ljust(20)}{str(evaluation.sentiment).rjust(74)}\n\n{'Topic: '.ljust(20)}{evaluation.topic.rjust(74)}\n"

    # Create the panel for the message
    panel = Panel(
        content.strip(),
        title="[bold]ANALYTICS EVALUATION[/]",
        subtitle=f"[dim]- [italic]{timestamp}[/]",
        title_align="left",
        subtitle_align="right",
        border_style=color,
        box=box.ROUNDED,
        width=100,  # Fixed width for all panels
        expand=True,  # Panels always expand to the width of the console
        padding=(1, 2),
    )

    # Printing the panel
    console.print(panel)


def pprint_messages(messages: list[ThreadMessage]):
    """
    Iterates over a list of messages and pretty-prints each one.

    Messages are pretty-printed using the rich library, highlighting the
    speaker's role, the message text, any available images, and the message
    timestamp in a panel format.

    Args:
        messages (list[ThreadMessage]): A list of ThreadMessage objects to be
            printed.
    """
    for message in messages:
        pprint_message(message)
