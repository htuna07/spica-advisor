import time

from agents import Agent, RunConfig, Runner, Usage, set_default_openai_client
from dotenv import load_dotenv
from openai import AsyncOpenAI

from spica_advisor.hooks import InteractionLoggingHooks
from spica_advisor.metrics import OK_STATUS, CallRecord
from spica_advisor.model_profiles import ModelProfile


MAX_TURNS = 10


def failed_run_progress(error):
    run_data = getattr(error, "run_data", None)
    if run_data is None:
        return Usage(), []
    return run_data.context_wrapper.usage, run_data.new_items


class AgentRunner:
    def __init__(self, profile: ModelProfile):
        self.profile = profile
        self.run_config = RunConfig(
            model=profile.build_model(),
            model_settings=profile.settings,
        )
        self.hooks = InteractionLoggingHooks()
        self.calls: list[CallRecord] = []

    @classmethod
    def from_env(cls, profile):
        load_dotenv()
        set_default_openai_client(AsyncOpenAI())
        return cls(profile)

    def run(self, agent: Agent, prompt, context=None):
        started = time.perf_counter()
        try:
            result = Runner.run_sync(
                agent,
                prompt,
                context=context,
                hooks=self.hooks,
                auto_previous_response_id=self.profile.uses_responses_api,
                max_turns=MAX_TURNS,
                run_config=self.run_config,
            )
        except Exception as error:
            usage, items = failed_run_progress(error)
            self._record(agent, type(error).__name__, started, usage, items)
            raise
        self._record(agent, OK_STATUS, started, result.context_wrapper.usage, result.new_items)
        return result.final_output

    def _record(self, agent, status, started, usage, items):
        self.calls.append(CallRecord.from_run(
            agent=agent.name,
            model=self.profile.name,
            status=status,
            wall_seconds=time.perf_counter() - started,
            usage=usage,
            items=items,
        ))
