from types import SimpleNamespace

import pytest
from agents import Agent, ModelSettings, Runner

from spica_advisor.anthropic_model import AnthropicModel
from spica_advisor.model_profiles import MODEL_PROFILES, ModelProfile
from spica_advisor.runner import AgentRunner


AGENT = Agent(name="Test agent")
OPENAI_PROFILE = ModelProfile("openai-test", "openai", "gpt-test", ModelSettings())
ANTHROPIC_PROFILE = ModelProfile("anthropic-test", "anthropic", "claude-test", ModelSettings())


class FakeRunSync:
    def __init__(self, result):
        self.result = result
        self.kwargs = None

    def __call__(self, agent, prompt, **kwargs):
        self.kwargs = kwargs
        return self.result


@pytest.fixture
def fake_anthropic_model(monkeypatch):
    monkeypatch.setattr(ModelProfile, "build_model", lambda profile: f"built:{profile.model_id}")


@pytest.mark.parametrize(
    ("profile", "uses_previous_response_id"),
    [(OPENAI_PROFILE, True), (ANTHROPIC_PROFILE, False)],
)
def test_previous_response_id_is_only_used_with_responses_api(
    monkeypatch, fake_anthropic_model, profile, uses_previous_response_id
):
    run_sync = FakeRunSync(SimpleNamespace(final_output="done"))
    monkeypatch.setattr(Runner, "run_sync", run_sync)

    assert AgentRunner(profile).run(AGENT, "prompt") == "done"
    assert run_sync.kwargs["auto_previous_response_id"] is uses_previous_response_id


def test_openai_profile_builds_model_name():
    assert OPENAI_PROFILE.build_model() == "gpt-test"


def test_anthropic_profile_builds_native_anthropic_model(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    model = ANTHROPIC_PROFILE.build_model()

    assert isinstance(model, AnthropicModel)
    assert model.model == "claude-test"


def test_registered_profiles_are_keyed_by_name():
    assert all(name == profile.name for name, profile in MODEL_PROFILES.items())
