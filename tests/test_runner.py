from types import SimpleNamespace

import pytest
from agents import Agent, MaxTurnsExceeded, ModelSettings, Runner, ToolCallItem, Usage
from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails

from spica_advisor.anthropic_model import AnthropicModel
from spica_advisor.metrics import CallRecord, totals
from spica_advisor.model_profiles import MODEL_PROFILES, ModelProfile
from spica_advisor.runner import AgentRunner


AGENT = Agent(name="Test agent")
OPENAI_PROFILE = ModelProfile("openai-test", "openai", "gpt-test", ModelSettings())
ANTHROPIC_PROFILE = ModelProfile("anthropic-test", "anthropic", "claude-test", ModelSettings())


def usage(requests=2, input_tokens=100, cached=40, cache_write=10, output_tokens=30, reasoning=5):
    return Usage(
        requests=requests,
        input_tokens=input_tokens,
        input_tokens_details=InputTokensDetails(cached_tokens=cached, cache_write_tokens=cache_write),
        output_tokens=output_tokens,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=reasoning),
        total_tokens=input_tokens + output_tokens,
    )


def tool_call():
    return ToolCallItem(agent=AGENT, raw_item={})


def run_progress(run_usage, items):
    return SimpleNamespace(context_wrapper=SimpleNamespace(usage=run_usage), new_items=items)


class FakeRunSync:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.kwargs = None

    def __call__(self, agent, prompt, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.result


@pytest.fixture
def fake_anthropic_model(monkeypatch):
    monkeypatch.setattr(ModelProfile, "build_model", lambda profile: f"built:{profile.model_id}")


def test_run_returns_final_output_and_records_usage(monkeypatch):
    result = SimpleNamespace(final_output="done", **vars(run_progress(usage(), [tool_call(), tool_call()])))
    monkeypatch.setattr(Runner, "run_sync", FakeRunSync(result=result))
    runner = AgentRunner(OPENAI_PROFILE)

    assert runner.run(AGENT, "prompt") == "done"

    [call] = runner.calls
    assert call.agent == "Test agent"
    assert call.model == "openai-test"
    assert call.status == "ok"
    assert call.wall_seconds >= 0
    assert (call.requests, call.tool_calls) == (2, 2)
    assert (call.input_tokens, call.cached_input_tokens, call.cache_write_tokens) == (100, 40, 10)
    assert (call.output_tokens, call.reasoning_tokens) == (30, 5)


def test_failed_run_records_usage_spent_before_failure_and_reraises(monkeypatch):
    error = MaxTurnsExceeded("too many turns")
    error.run_data = run_progress(usage(requests=10), [tool_call()])
    monkeypatch.setattr(Runner, "run_sync", FakeRunSync(error=error))
    runner = AgentRunner(OPENAI_PROFILE)

    with pytest.raises(MaxTurnsExceeded):
        runner.run(AGENT, "prompt")

    [call] = runner.calls
    assert call.status == "MaxTurnsExceeded"
    assert (call.requests, call.tool_calls, call.input_tokens) == (10, 1, 100)


def test_failed_run_without_progress_records_zero_usage(monkeypatch):
    monkeypatch.setattr(Runner, "run_sync", FakeRunSync(error=ConnectionError("offline")))
    runner = AgentRunner(OPENAI_PROFILE)

    with pytest.raises(ConnectionError):
        runner.run(AGENT, "prompt")

    [call] = runner.calls
    assert call.status == "ConnectionError"
    assert (call.requests, call.input_tokens, call.output_tokens) == (0, 0, 0)


@pytest.mark.parametrize(
    ("profile", "uses_previous_response_id"),
    [(OPENAI_PROFILE, True), (ANTHROPIC_PROFILE, False)],
)
def test_previous_response_id_is_only_used_with_responses_api(
    monkeypatch, fake_anthropic_model, profile, uses_previous_response_id
):
    result = SimpleNamespace(final_output="done", **vars(run_progress(usage(), [])))
    run_sync = FakeRunSync(result=result)
    monkeypatch.setattr(Runner, "run_sync", run_sync)

    AgentRunner(profile).run(AGENT, "prompt")

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


def test_totals_sum_calls_and_count_failures():
    calls = [
        CallRecord.from_run("a", "m", "ok", 1.25, usage(), [tool_call()]),
        CallRecord.from_run("b", "m", "MaxTurnsExceeded", 2.5, usage(requests=1), []),
    ]

    assert totals(calls) == {
        "calls": 2,
        "failed_calls": 1,
        "wall_seconds": 3.75,
        "requests": 3,
        "tool_calls": 1,
        "input_tokens": 200,
        "cached_input_tokens": 80,
        "cache_write_tokens": 20,
        "output_tokens": 60,
        "reasoning_tokens": 10,
    }
