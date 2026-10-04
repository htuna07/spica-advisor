from agents import Agent, RunConfig, Runner, set_default_openai_client
from dotenv import load_dotenv
from openai import AsyncOpenAI

from spica_advisor.hooks import InteractionLoggingHooks
from spica_advisor.model_profiles import ModelProfile


MAX_TURNS = 10


class AgentRunner:
    def __init__(self, profile: ModelProfile):
        self.profile = profile
        self.run_config = RunConfig(
            model=profile.build_model(),
            model_settings=profile.settings,
        )
        self.hooks = InteractionLoggingHooks()

    @classmethod
    def from_env(cls, profile):
        load_dotenv()
        set_default_openai_client(AsyncOpenAI())
        return cls(profile)

    def run(self, agent: Agent, prompt, context=None):
        return Runner.run_sync(
            agent,
            prompt,
            context=context,
            hooks=self.hooks,
            auto_previous_response_id=self.profile.uses_responses_api,
            max_turns=MAX_TURNS,
            run_config=self.run_config,
        ).final_output
