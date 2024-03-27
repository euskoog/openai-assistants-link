import re
from openai.types.beta.threads import (
    Message as ThreadMessage,
)
from app.lib.openai import get_openai_client


def remove_annotation_tags(text):
    """
    Removes annotation tags like [16 source] from the provided text.

    Args:
    text (str): The text from which annotation tags need to be removed.

    Returns:
    str: Text with annotation tags removed.
    """
    # Define the regular expression pattern for matching annotation tags
    # This pattern matches anything that starts with '[', followed by any number of digits,
    # a space, any word characters, and ends with ']'
    pattern = r"【\d+†\w+】"

    # Use re.sub() to replace the found patterns with an empty string
    cleaned_text = re.sub(pattern, "", text)

    return cleaned_text


class OpenAIAnnotations:
    def remove_from_message(message: ThreadMessage) -> str:
        message_content = message.content[0].text
        annotations = message_content.annotations
        cleaned_message_content = message_content.value

        # Iterate over the annotations and remove them from the text
        for index, annotation in enumerate(annotations):
            # Remove the annotated text
            cleaned_message_content = cleaned_message_content.replace(
                annotation.text, ""
            )

        # just in case OpenAI returns content with an annotation but does not supply the annotation object,
        # we remove any remaining annotation tags manually
        # THIS REGEX PROCESS TAKES A LONG TIME TO RUN SO WE ARE COMMENTING IT OUT FOR NOW
        # cleaned_message_content = remove_annotation_tags(cleaned_message_content)

        return cleaned_message_content

    def extract_from_message(message: ThreadMessage) -> list[dict]:
        annotations = []

        try:
            client = get_openai_client()
            message_content = message.content[0].text
            message_annotations = message_content.annotations

            # Iterate over the annotations and remove them from the text
            for index, annotation in enumerate(message_annotations):
                # Gather citations as dictionaries based on annotation attributes
                if file_citation := getattr(annotation, "file_citation", None):
                    if file_citation.file_id and file_citation.file_id != "":
                        cited_file = client.files.retrieve(file_citation.file_id)
                        citation_text = (
                            f"{file_citation.quote} from {cited_file.filename}"
                        )
                        annotations.append(
                            {
                                "type": "file_citation",
                                "value": citation_text,
                                "annotation": annotation.model_dump(),
                            }
                        )
                elif file_path := getattr(annotation, "file_path", None):
                    if file_path.file_id and file_path.file_id != "":
                        cited_file = client.files.retrieve(file_path.file_id)
                        citation_text = (
                            f"Click <here> to download {cited_file.filename}"
                        )
                        annotations.append(
                            {
                                "type": "file_download",
                                "value": citation_text,
                                "annotation": annotation,
                            }
                        )
        except Exception as e:
            # We just want to make sure that this simple process that we arent even using right now doesnt break the whole app
            print("Error extracting annotations from thread message", message)
            print(e)
            return []

        return annotations

    def remove_and_extract_from_message(message: ThreadMessage) -> dict:
        """Removes annotations from a message and returns the annotations as a list of dictionaries

        Returns
        {
            "content":str = Message content without annotations
            "annotations": list[dict] = List of dictionaries containing the type, value, and original annotation object
        }
        """
        try:
            # get cleaned message content (without annotation markers)
            cleaned_message_content: str = OpenAIAnnotations.remove_from_message(
                message
            )

            # get annotations from message (as a list of dictionaries)
            annotations = []
            found_annotations = OpenAIAnnotations.extract_from_message(message)
            if found_annotations and len(found_annotations) > 0:
                for found_annotation in found_annotations:
                    annotations.append(found_annotation)

            return {"content": cleaned_message_content, "annotations": annotations}
        except Exception as e:
            print("Error occurred while removing and extracting from message:", e)
            return {"content": message.content[0].text.value, "annotations": []}
