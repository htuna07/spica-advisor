from agents import Agent, RunConfig, Runner, set_default_openai_client
from dotenv import load_dotenv
from openai import AsyncOpenAI


MODEL = "gpt-6-luna"


class AgentRunner:
    def __init__(self, model=MODEL):
        self.run_config = RunConfig(model=model)

    @classmethod
    def from_env(cls):
        load_dotenv()
        set_default_openai_client(AsyncOpenAI())
        return cls()

    def run(self, agent: Agent, prompt):
        return Runner.run_sync(agent, prompt, run_config=self.run_config).final_output
