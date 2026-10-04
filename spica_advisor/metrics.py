from dataclasses import dataclass

from agents import ToolCallItem


OK_STATUS = "ok"
SUMMED_FIELDS = (
    "wall_seconds",
    "requests",
    "tool_calls",
    "input_tokens",
    "cached_input_tokens",
    "cache_write_tokens",
    "output_tokens",
    "reasoning_tokens",
)


@dataclass(frozen=True)
class CallRecord:
    agent: str
    model: str
    status: str
    wall_seconds: float
    requests: int
    tool_calls: int
    input_tokens: int
    cached_input_tokens: int
    cache_write_tokens: int
    output_tokens: int
    reasoning_tokens: int

    @classmethod
    def from_run(cls, agent, model, status, wall_seconds, usage, items):
        return cls(
            agent=agent,
            model=model,
            status=status,
            wall_seconds=round(wall_seconds, 3),
            requests=usage.requests,
            tool_calls=sum(isinstance(item, ToolCallItem) for item in items),
            input_tokens=usage.input_tokens,
            cached_input_tokens=usage.input_tokens_details.cached_tokens,
            cache_write_tokens=usage.input_tokens_details.cache_write_tokens,
            output_tokens=usage.output_tokens,
            reasoning_tokens=usage.output_tokens_details.reasoning_tokens,
        )


def totals(calls):
    return {
        "calls": len(calls),
        "failed_calls": sum(call.status != OK_STATUS for call in calls),
        **{name: round(sum(getattr(call, name) for call in calls), 3) for name in SUMMED_FIELDS},
    }
