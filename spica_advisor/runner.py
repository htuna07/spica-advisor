from agents import Agent, ModelSettings, RunConfig, Runner, set_default_openai_client
from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.shared import Reasoning

from spica_advisor.hooks import InteractionLoggingHooks


MODEL = "gpt-6-luna"


class AgentRunner:
    def __init__(self, model=MODEL):
        self.run_config = RunConfig(
            model=model,
            model_settings=ModelSettings(reasoning=Reasoning(summary="auto")),
        )
        self.hooks = InteractionLoggingHooks()

    @classmethod
    def from_env(cls):
        load_dotenv()
        set_default_openai_client(AsyncOpenAI())
        return cls()

    def run(self, agent: Agent, prompt, context=None):
        return Runner.run_sync(
            agent,
            prompt,
            context=context,
            hooks=self.hooks,
            auto_previous_response_id=True,
            run_config=self.run_config,
        ).final_output
