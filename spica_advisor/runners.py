from typing import Protocol

from agents import Agent

from spica_advisor.claude_cli_runner import ClaudeCliRunner
from spica_advisor.metrics import CallRecord
from spica_advisor.model_profiles import ModelProfile
from spica_advisor.runner import AgentRunner


class LLMRunner(Protocol):
    profile: ModelProfile
    calls: list[CallRecord]

    def run(self, agent: Agent, prompt, context=None): ...


def create_runner(profile: ModelProfile) -> LLMRunner:
    if profile.is_claude_cli:
        return ClaudeCliRunner.from_env(profile)
    return AgentRunner.from_env(profile)
