import asyncio
import json
from types import SimpleNamespace

import pytest
from agents import Agent, AgentOutputSchema, ModelSettings, RunConfig, Runner, function_tool
from agents.exceptions import ModelBehaviorError, ModelRefusalError
from anthropic.types import ThinkingBlock
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage
from pydantic import BaseModel

from spica_advisor.anthropic_model import (
    DEFAULT_MAX_TOKENS,
    AnthropicModel,
    build_request,
    to_messages,
    to_output,
    to_usage,
)


class Answer(BaseModel):
    value: str


@function_tool
def lookup(key: str) -> str:
    """Look up a value.

    Args:
        key: Key to look up.
    """
    return f"value-of-{key}"


def anthropic_usage(input_tokens=100, cache_read=None, cache_write=None, output_tokens=20, thinking=None):
    return SimpleNamespace(
        input_tokens=input_tokens,
        cache_read_input_tokens=cache_read,
        cache_creation_input_tokens=cache_write,
        output_tokens=output_tokens,
        output_tokens_details=None if thinking is None else SimpleNamespace(thinking_tokens=thinking),
    )


def text_block(text):
    return SimpleNamespace(type="text", text=text)


def tool_use_block(call_id, name, arguments):
    return SimpleNamespace(type="tool_use", id=call_id, name=name, input=arguments)


def anthropic_message(*content, usage=None, stop_reason="end_turn", stop_details=None):
    return SimpleNamespace(
        id="msg_1",
        content=list(content),
        usage=usage or anthropic_usage(),
        stop_reason=stop_reason,
        stop_details=stop_details,
        _request_id="req_1",
    )


def thinking_block(signature):
    return ThinkingBlock(type="thinking", thinking="", signature=signature)


class FakeMessages:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def create(self, **request):
        self.requests.append(request)
        return self.responses.pop(0)


class FakeClient:
    def __init__(self, *responses):
        self.messages = FakeMessages(responses)


def test_string_input_becomes_single_user_message():
    assert to_messages("hello") == [{"role": "user", "content": "hello"}]


def test_conversation_items_become_alternating_messages_with_merged_blocks():
    items = [
        {"role": "user", "content": "find it"},
        {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Searching"}]},
        {"type": "function_call", "call_id": "toolu_1", "name": "lookup", "arguments": '{"key": "a"}'},
        {"type": "function_call", "call_id": "toolu_2", "name": "lookup", "arguments": '{"key": "b"}'},
        {"type": "function_call_output", "call_id": "toolu_1", "output": "value-a"},
        {"type": "function_call_output", "call_id": "toolu_2", "output": [{"type": "input_text", "text": "value-b"}]},
    ]

    assert to_messages(items) == [
        {"role": "user", "content": [{"type": "text", "text": "find it"}]},
        {"role": "assistant", "content": [
            {"type": "text", "text": "Searching"},
            {"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"key": "a"}},
            {"type": "tool_use", "id": "toolu_2", "name": "lookup", "input": {"key": "b"}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "value-a"},
            {"type": "tool_result", "tool_use_id": "toolu_2", "content": "value-b"},
        ]},
    ]


def test_unsupported_input_item_is_rejected():
    with pytest.raises(ValueError, match="reasoning"):
        to_messages([{"type": "reasoning", "summary": []}])


def test_request_includes_tools_system_and_native_output_format():
    request = build_request(
        "claude-test", "Be precise.", "hi", ModelSettings(max_tokens=1000), [lookup], AgentOutputSchema(Answer),
    )

    assert request["model"] == "claude-test"
    assert request["max_tokens"] == 1000
    assert request["system"] == "Be precise."
    assert request["tools"] == [{
        "name": "lookup",
        "description": "Look up a value.",
        "input_schema": lookup.params_json_schema,
        "strict": True,
    }]
    assert request["output_config"] == {
        "format": {"type": "json_schema", "schema": AgentOutputSchema(Answer).json_schema()},
    }
    assert "tool_choice" not in request


def test_plain_request_omits_optional_fields_and_uses_default_max_tokens():
    request = build_request("claude-test", None, "hi", ModelSettings(), [], None)

    assert request == {
        "model": "claude-test",
        "max_tokens": DEFAULT_MAX_TOKENS,
        "messages": [{"role": "user", "content": "hi"}],
    }


def test_output_maps_text_and_tool_use_blocks():
    output = to_output(anthropic_message(
        text_block("Let me check."),
        tool_use_block("toolu_1", "lookup", {"key": "a"}),
    ))

    message, tool_call = output
    assert isinstance(message, ResponseOutputMessage)
    assert message.content[0].text == "Let me check."
    assert isinstance(tool_call, ResponseFunctionToolCall)
    assert (tool_call.call_id, tool_call.name, json.loads(tool_call.arguments)) == ("toolu_1", "lookup", {"key": "a"})


def test_usage_counts_cached_tokens_as_input_like_openai():
    usage = to_usage(anthropic_usage(input_tokens=100, cache_read=300, cache_write=50, output_tokens=20, thinking=7))

    assert usage.requests == 1
    assert usage.input_tokens == 450
    assert usage.input_tokens_details.cached_tokens == 300
    assert usage.input_tokens_details.cache_write_tokens == 50
    assert usage.output_tokens == 20
    assert usage.output_tokens_details.reasoning_tokens == 7
    assert usage.total_tokens == 470


def test_usage_without_cache_or_thinking_details():
    usage = to_usage(anthropic_usage(input_tokens=100, output_tokens=20))

    assert (usage.input_tokens, usage.input_tokens_details.cached_tokens, usage.output_tokens_details.reasoning_tokens) == (100, 0, 0)


def test_get_response_returns_model_response_from_client():
    client = FakeClient(anthropic_message(text_block('{"value": "x"}')))
    model = AnthropicModel("claude-test", client)

    response = asyncio.run(model.get_response(
        None, "hi", ModelSettings(), [], None, [], None,
        previous_response_id=None, conversation_id=None, prompt=None,
    ))

    assert response.output[0].content[0].text == '{"value": "x"}'
    assert response.request_id == "req_1"
    assert response.usage.input_tokens == 100


def test_agent_can_call_tools_before_returning_structured_output():
    client = FakeClient(
        anthropic_message(tool_use_block("toolu_1", "lookup", {"key": "a"})),
        anthropic_message(text_block('{"value": "value-of-a"}')),
    )
    agent = Agent(name="Finder", instructions="Use tools.", tools=[lookup], output_type=Answer)

    result = Runner.run_sync(
        agent,
        "find a",
        run_config=RunConfig(model=AnthropicModel("claude-test", client), tracing_disabled=True),
    )

    assert result.final_output == Answer(value="value-of-a")
    first_request, second_request = client.messages.requests
    assert "output_config" in first_request and "tool_choice" not in first_request
    assert second_request["messages"][1:] == [
        {"role": "assistant", "content": [{"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"key": "a"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "toolu_1", "content": "value-of-a"}]},
    ]
    assert result.context_wrapper.usage.requests == 2


def get_response(client):
    return asyncio.run(AnthropicModel("claude-test", client).get_response(
        None, "hi", ModelSettings(), [], None, [], None,
        previous_response_id=None, conversation_id=None, prompt=None,
    ))


def test_output_keeps_block_order_and_merges_adjacent_text():
    output = to_output(anthropic_message(
        thinking_block("sig-1"),
        text_block("Checking "),
        text_block("now."),
        tool_use_block("toolu_1", "lookup", {"key": "a"}),
    ))

    assert [item.type for item in output] == ["reasoning", "message", "function_call"]
    assert json.loads(output[0].encrypted_content) == {"type": "thinking", "thinking": "", "signature": "sig-1"}
    assert output[1].content[0].text == "Checking now."


def test_thinking_blocks_are_sent_back_unchanged_before_their_tool_call():
    client = FakeClient(
        anthropic_message(thinking_block("sig-1"), tool_use_block("toolu_1", "lookup", {"key": "a"})),
        anthropic_message(thinking_block("sig-2"), text_block('{"value": "value-of-a"}')),
    )
    agent = Agent(name="Finder", instructions="Use tools.", tools=[lookup], output_type=Answer)

    result = Runner.run_sync(
        agent,
        "find a",
        run_config=RunConfig(model=AnthropicModel("claude-test", client), tracing_disabled=True),
    )

    assert result.final_output == Answer(value="value-of-a")
    assistant_turn = client.messages.requests[1]["messages"][1]
    assert assistant_turn == {"role": "assistant", "content": [
        {"type": "thinking", "thinking": "", "signature": "sig-1"},
        {"type": "tool_use", "id": "toolu_1", "name": "lookup", "input": {"key": "a"}},
    ]}


def test_refusal_raises_model_refusal_error_with_category():
    client = FakeClient(anthropic_message(
        stop_reason="refusal", stop_details=SimpleNamespace(type="refusal", category="cyber", explanation=None),
    ))

    with pytest.raises(ModelRefusalError, match="cyber"):
        get_response(client)


def test_response_cut_off_at_max_tokens_raises_model_behavior_error():
    client = FakeClient(anthropic_message(text_block('{"value": "trunc'), stop_reason="max_tokens"))

    with pytest.raises(ModelBehaviorError, match="max_tokens"):
        get_response(client)
