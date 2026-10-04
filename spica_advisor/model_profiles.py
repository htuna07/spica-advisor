from dataclasses import dataclass
from typing import Literal

from agents import ModelSettings
from openai.types.shared import Reasoning

from spica_advisor.anthropic_model import AnthropicModel


@dataclass(frozen=True)
class ModelProfile:
    name: str
    provider: Literal["openai", "anthropic"]
    model_id: str
    settings: ModelSettings

    @property
    def uses_responses_api(self):
        return self.provider == "openai"

    def build_model(self):
        if self.provider == "openai":
            return self.model_id
        return AnthropicModel(self.model_id)


MODEL_PROFILES = {
    profile.name: profile
    for profile in (
        ModelProfile(
            name="gpt-6-luna",
            provider="openai",
            model_id="gpt-6-luna",
            settings=ModelSettings(reasoning=Reasoning(summary="auto")),
        ),
        ModelProfile(
            name="gpt-6.1-sol",
            provider="openai",
            model_id="gpt-6.1-sol",
            settings=ModelSettings(reasoning=Reasoning(summary="auto")),
        ),
        ModelProfile(
            name="claude-haiku-4-5",
            provider="anthropic",
            model_id="claude-haiku-4-5",
            settings=ModelSettings(max_tokens=8192),
        ),
        ModelProfile(
            name="claude-sonnet-5-5",
            provider="anthropic",
            model_id="claude-sonnet-5-5",
            settings=ModelSettings(max_tokens=16000),
        ),
    )
}

DEFAULT_MODEL = "gpt-6-luna"
