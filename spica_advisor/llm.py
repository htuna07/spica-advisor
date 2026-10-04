from dotenv import load_dotenv
from openai import OpenAI


MODEL = "gpt-6-luna"


class LLM:
    def __init__(self, client, model=MODEL):
        self.client = client
        self.model = model

    @classmethod
    def from_env(cls):
        load_dotenv()
        return cls(OpenAI())

    def parse(self, prompt, schema):
        response = self.client.responses.parse(
            model=self.model,
            input=prompt,
            text_format=schema,
        )
        return response.output_parsed
