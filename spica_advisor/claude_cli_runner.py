import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from spica_advisor.log import LOGGER
from spica_advisor.metrics import OK_STATUS, CallRecord
from spica_advisor.model_profiles import ModelProfile
from spica_advisor.runner import MAX_TURNS
from spica_advisor.tools import write_function_files


CLI = "claude"
FILE_TOOLS = ("Grep", "Glob", "Read")
STRUCTURED_OUTPUT_TOOL = "StructuredOutput"
CALL_TIMEOUT_SECONDS = 900
# The CLI bills this key instead of the signed-in subscription whenever it is set.
API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"


class ClaudeCliError(RuntimeError):
    pass


def subscription_env():
    return {name: value for name, value in os.environ.items() if name != API_KEY_ENV_VAR}


def read_events(stdout):
    return [json.loads(line) for line in stdout.splitlines() if line.startswith("{")]


def result_event(events):
    return next((event for event in reversed(events) if event.get("type") == "result"), None)


def tool_uses(events):
    return [
        block
        for event in events if event.get("type") == "assistant"
        for block in event["message"]["content"] if block.get("type") == "tool_use"
    ]


def structured_output(agent, events, stderr):
    result = result_event(events)
    if result is None:
        raise ClaudeCliError(stderr.strip() or "the CLI returned no result")
    if result.get("is_error") or result.get("structured_output") is None:
        details = result.get("errors") or [result.get("result")]
        raise ClaudeCliError(f"{result.get('subtype')}: {details}")
    return agent.output_type.model_validate(result["structured_output"])


def call_record(agent, model, status, wall_seconds, events):
    result = result_event(events) or {}
    usages = (result.get("modelUsage") or {}).values()

    def total(key):
        return sum(usage.get(key, 0) for usage in usages)

    cached, cache_write = total("cacheReadInputTokens"), total("cacheCreationInputTokens")
    return CallRecord(
        agent=agent,
        model=model,
        status=status,
        wall_seconds=round(wall_seconds, 3),
        requests=result.get("num_turns", 0),
        tool_calls=sum(tool_use["name"] != STRUCTURED_OUTPUT_TOOL for tool_use in tool_uses(events)),
        input_tokens=total("inputTokens") + cached + cache_write,
        cached_input_tokens=cached,
        cache_write_tokens=cache_write,
        output_tokens=total("outputTokens"),
        reasoning_tokens=total("thinkingTokens"),
    )


class ClaudeCliRunner:
    def __init__(self, profile: ModelProfile):
        self.profile = profile
        self.calls: list[CallRecord] = []

    @classmethod
    def from_env(cls, profile):
        if not shutil.which(CLI):
            raise RuntimeError(f"{profile.name} requires the Claude Code CLI ({CLI}) on PATH, signed in")
        return cls(profile)

    def command(self, agent, tools):
        return [
            CLI, "-p", "--safe-mode", "--restricted", "--no-session-persistence",
            "--output-format", "stream-json", "--verbose",
            "--max-turns", str(MAX_TURNS),
            "--model", self.profile.model_id,
            "--tools", ",".join(tools),
            "--system-prompt", agent.instructions,
            "--json-schema", json.dumps(agent.output_type.model_json_schema()),
        ]

    def execute(self, agent, prompt, context):
        # An empty working directory keeps the CLI's file tools away from everything but the given sources.
        with tempfile.TemporaryDirectory() as workspace:
            tools = ()
            if agent.tools:
                prompt = f"{prompt}\n\n{write_function_files(context, Path(workspace))}"
                tools = FILE_TOOLS
            return subprocess.run(
                self.command(agent, tools),
                input=prompt,
                cwd=workspace,
                env=subscription_env(),
                capture_output=True,
                text=True,
                timeout=CALL_TIMEOUT_SECONDS,
            )

    def run(self, agent, prompt, context=None):
        started = time.perf_counter()
        events = []
        try:
            completed = self.execute(agent, prompt, context)
            events = read_events(completed.stdout)
            output = structured_output(agent, events, completed.stderr)
        except Exception as error:
            self._record(agent, type(error).__name__, started, events)
            raise
        self._record(agent, OK_STATUS, started, events)
        return output

    def _record(self, agent, status, started, events):
        LOGGER.debug("Claude CLI call finished for %s", agent.name, extra={"payload": {
            "agent": agent.name,
            "status": status,
            "events": events,
        }})
        self.calls.append(call_record(agent.name, self.profile.name, status, time.perf_counter() - started, events))
