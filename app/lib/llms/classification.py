import logging
from jinja2 import Template

from app.lib.llms.chat_completion import ChatCompletion

logger = logging.getLogger(__name__)

class Classification:
    def __init__(self, options, name, description):
        self.name = name
        self.description= description
        self.options = options
        self.prompt_template = """
        ## Classifier Service: {{ name }}

        **Objective**: You are an expert classifier that always chooses correctly.

        ### Context
        {{ _doc }}

        ### Response Format
        You must classify the user provided data into one of the following classes:
        {% for option in options %}
        - Class {{ option }}
        {% endfor %}
        \n\nASSISTANT: ### Data
        The user provided the following data:
        {{ input }}
        \n\nASSISTANT: The most likely class label for the data and context provided above is Class
        """

    def _generate_prompt(self, input):
        """Generate the prompt for the classification task."""

        template = Template(self.prompt_template)

        rendered_prompt = template.render(
            name=self.name, _doc=self.description, options=self.options, input=input
        )

        return rendered_prompt
    
    def run(self, input):
        """A custom AI classification request

        Args:
            input (str): The input to classify.

        Returns:
            str: The name of the classification.

        Examples:
            >>> classification = Classification(name="Sentiment", description="Conduct a sentiment analysis of the given input.", values=["POSITIVE", "NEUTRAL", "NEGATIVE"])
            >>> classification.run("I love clouds!")
            'POSITIVE'
        """
            
        prompt = self._generate_prompt(input)

        completion = ChatCompletion()
        result = completion.run(messages=[{"role": "system", "content": prompt}])

        return result


         
