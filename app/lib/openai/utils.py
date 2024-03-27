from typing import Any

from prisma.models import Message


class CancelRun(Exception):
    """
    A special exception that can be raised in a tool to end the run immediately.
    """

    def __init__(self, data: Any = None):
        self.data = data


def combine_strings(*args):
    """
    Combine multiple string arguments into a single string.
    :param args: Variable number of string arguments.
    :return: Combined string.
    """
    # Convert all arguments to strings (in case some aren't)
    str_args = [str(arg) for arg in args]

    # Using join for efficient concatenation
    return "".join(str_args)

def clean_quotes(string: str):
    """
    Clean surrounding quotes from a string.
    :param string: The string to clean.
    :return: The cleaned string.
    """
    # If the string is surrounded by quotes, remove them
    if string[0] == string[-1] and string[0] in ["'", '"']:
        return string[1:-1]
    return string

def format_prompt_messages(messages: list[Message]):
    return "\n".join(
        f"Role: {message.role}\n"
        f"Message: {message.content}\n" +
        (f"Category: {message.category.name}\n" if message.category else "") +
        (f"Topic: {message.topic.name}\n" if message.topic else "") +
        (f'Classification: {message.metadata.get("classification")}\n' if message.metadata.get("classification") else "")
        for message in messages
    )