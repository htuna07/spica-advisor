import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from agents import Agent
from pydantic import BaseModel, ValidationError

from spica_advisor import claude_cli_runner
from spica_advisor.claude_cli_runner import ClaudeCliError, ClaudeCliRunner
from spica_advisor.model_profiles import MODEL_PROFILES, ModelProfile
from spica_advisor.runner import MAX_TURNS, AgentRunner
from spica_advisor.runners import create_runner
from spica_advisor.tools import search_all_code


class Answer(BaseModel):
    label: str


PROFILE = ModelProfile("claude-cli-test", "claude-cli", "claude-test")
AGENT = Agent(name="Classifier", instructions="Classify.", output_type=Answer)
TOOL_AGENT = Agent(name="Searcher", instructions="Search.", output_type=Answer, tools=[search_all_code])
FUNCTIONS = [{"_id": "fn/1", "name": "Orders", "content": "export const a = 1;"}]


def assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def tool_use(name):
    return {"type": "tool_use", "name": name, "input": {}}


def result(structured_output=None, is_error=False, subtype="success", **extra):
    return {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "num_turns": 3,
        "structured_output": structured_output,
        "modelUsage": {
            "claude-test": {"inputTokens": 5, "outputTokens": 40, "cacheReadInputTokens": 100,
                            "cacheCreationInputTokens": 20, "thinkingTokens": 7},
            "claude-helper": {"inputTokens": 1, "outputTokens": 2},
        },
        **extra,
    }


def stream(*events):
    return "\n".join(json.dumps(event) for event in events) + "\n"


class FakeSubprocess:
    def __init__(self, stdout="", stderr="", error=None):
        self.stdout = stdout
        self.stderr = stderr
        self.error = error
        self.command = None
        self.kwargs = None
        self.workspace_files = {}

    def __call__(self, command, **kwargs):
        self.command = command
        self.kwargs = kwargs
        self.workspace_files = {path.name: path.read_text() for path in Path(kwargs["cwd"]).iterdir()}
        if self.error:
            raise self.error
        return SimpleNamespace(stdout=self.stdout, stderr=self.stderr, returncode=0)


@pytest.fixture
def fake_subprocess(monkeypatch):
    def install(**kwargs):
        fake = FakeSubprocess(**kwargs)
        monkeypatch.setattr(claude_cli_runner.subprocess, "run", fake)
        return fake
    return install


def flag(command, name):
    return command[command.index(name) + 1]


def test_run_returns_validated_output_and_records_usage(fake_subprocess):
    fake = fake_subprocess(stdout=stream(
        {"type": "system", "subtype": "init"},
        assistant(tool_use("Grep"), tool_use("Read")),
        assistant(tool_use("StructuredOutput")),
        result({"label": "pos"}),
    ))
    runner = ClaudeCliRunner(PROFILE)

    assert runner.run(AGENT, "I love it") == Answer(label="pos")

    [call] = runner.calls
    assert (call.agent, call.model, call.status) == ("Classifier", "claude-cli-test", "ok")
    assert (call.requests, call.tool_calls) == (3, 2)
    assert (call.input_tokens, call.cached_input_tokens, call.cache_write_tokens) == (126, 100, 20)
    assert (call.output_tokens, call.reasoning_tokens) == (42, 7)
    assert fake.kwargs["input"] == "I love it"


def test_command_passes_agent_instructions_schema_model_and_turn_limit(fake_subprocess):
    fake = fake_subprocess(stdout=stream(result({"label": "pos"})))

    ClaudeCliRunner(PROFILE).run(AGENT, "prompt")

    command = fake.command
    assert command[:2] == ["claude", "-p"]
    assert {"--safe-mode", "--restricted", "--no-session-persistence"} <= set(command)
    assert flag(command, "--system-prompt") == "Classify."
    assert json.loads(flag(command, "--json-schema")) == Answer.model_json_schema()
    assert flag(command, "--model") == "claude-test"
    assert flag(command, "--max-turns") == str(MAX_TURNS)
    assert flag(command, "--tools") == ""
    assert fake.workspace_files == {}


def test_api_key_is_removed_so_the_cli_uses_the_subscription(fake_subprocess, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "paid-key")
    monkeypatch.setenv("CLAUDE_CODE_OAUTH_TOKEN", "subscription-token")
    fake = fake_subprocess(stdout=stream(result({"label": "pos"})))

    ClaudeCliRunner(PROFILE).run(AGENT, "prompt")

    assert "ANTHROPIC_API_KEY" not in fake.kwargs["env"]
    assert fake.kwargs["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "subscription-token"


def test_agent_with_tools_searches_function_files_with_file_tools(fake_subprocess):
    fake = fake_subprocess(stdout=stream(result({"label": "pos"})))

    ClaudeCliRunner(PROFILE).run(TOOL_AGENT, "Search the functions.", context=FUNCTIONS)

    assert flag(fake.command, "--tools") == "Grep,Glob,Read"
    assert fake.workspace_files == {"fn_1.js": "export const a = 1;"}
    assert fake.kwargs["input"].startswith("Search the functions.\n\n")
    assert "- fn_1.js: function_id fn/1, name Orders" in fake.kwargs["input"]


def test_error_result_raises_and_records_usage(fake_subprocess):
    fake_subprocess(stdout=stream(result(is_error=True, subtype="error_max_turns", errors=["Reached max turns"])))
    runner = ClaudeCliRunner(PROFILE)

    with pytest.raises(ClaudeCliError, match="error_max_turns"):
        runner.run(AGENT, "prompt")

    [call] = runner.calls
    assert call.status == "ClaudeCliError"
    assert (call.requests, call.input_tokens) == (3, 126)


def test_missing_result_raises_with_stderr(fake_subprocess):
    fake_subprocess(stdout="not json\n", stderr="Not logged in")
    runner = ClaudeCliRunner(PROFILE)

    with pytest.raises(ClaudeCliError, match="Not logged in"):
        runner.run(AGENT, "prompt")

    [call] = runner.calls
    assert (call.status, call.requests, call.input_tokens) == ("ClaudeCliError", 0, 0)


def test_output_that_breaks_the_schema_raises(fake_subprocess):
    fake_subprocess(stdout=stream(result({"wrong": "field"})))
    runner = ClaudeCliRunner(PROFILE)

    with pytest.raises(ValidationError):
        runner.run(AGENT, "prompt")

    assert runner.calls[0].status == "ValidationError"


def test_timeout_is_recorded_and_reraised(fake_subprocess):
    fake_subprocess(error=TimeoutError("timed out"))
    runner = ClaudeCliRunner(PROFILE)

    with pytest.raises(TimeoutError):
        runner.run(AGENT, "prompt")

    assert runner.calls[0].status == "TimeoutError"


def test_from_env_requires_the_cli(monkeypatch):
    monkeypatch.setattr(claude_cli_runner.shutil, "which", lambda name: None)

    with pytest.raises(RuntimeError, match="Claude Code CLI"):
        ClaudeCliRunner.from_env(PROFILE)


def test_create_runner_picks_the_runner_for_the_profile(monkeypatch):
    monkeypatch.setattr(ClaudeCliRunner, "from_env", classmethod(lambda cls, profile: "cli"))
    monkeypatch.setattr(AgentRunner, "from_env", classmethod(lambda cls, profile: "sdk"))

    assert create_runner(MODEL_PROFILES["claude-cli-sonnet-5-5"]) == "cli"
    assert create_runner(MODEL_PROFILES["gpt-6-luna"]) == "sdk"
    assert create_runner(MODEL_PROFILES["claude-sonnet-5-5"]) == "sdk"
