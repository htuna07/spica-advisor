import json

from agents import FunctionTool, Model, ModelResponse, Usage
from anthropic import AsyncAnthropic
from openai.types.responses import ResponseFunctionToolCall, ResponseOutputMessage, ResponseOutputText
from openai.types.responses.response_usage import InputTokensDetails, OutputTokensDetails


DEFAULT_MAX_TOKENS = 8192
TEXT_PART_TYPES = {"input_text", "output_text"}


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part["text"] for part in content if part.get("type") in TEXT_PART_TYPES)


def to_block(item):
    item_type = item.get("type", "message")
    if item_type == "message":
        role = "assistant" if item["role"] == "assistant" else "user"
        return role, {"type": "text", "text": text_of(item["content"])}
    if item_type == "function_call":
        return "assistant", {
            "type": "tool_use",
            "id": item["call_id"],
            "name": item["name"],
            "input": json.loads(item["arguments"] or "{}"),
        }
    if item_type == "function_call_output":
        return "user", {
            "type": "tool_result",
            "tool_use_id": item["call_id"],
            "content": text_of(item["output"]),
        }
    raise ValueError(f"Unsupported input item type: {item_type}")


def to_messages(input):
    if isinstance(input, str):
        return [{"role": "user", "content": input}]
    messages = []
    for item in input:
        role, block = to_block(item)
        if messages and messages[-1]["role"] == role:
            messages[-1]["content"].append(block)
        else:
            messages.append({"role": role, "content": [block]})
    return messages


def to_tool(tool):
    if not isinstance(tool, FunctionTool):
        raise ValueError(f"Unsupported tool type: {type(tool).__name__}")
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.params_json_schema,
        "strict": tool.strict_json_schema,
    }


def build_request(model, system_instructions, input, model_settings, tools, output_schema):
    request = {
        "model": model,
        "max_tokens": model_settings.max_tokens or DEFAULT_MAX_TOKENS,
        "messages": to_messages(input),
    }
    if system_instructions:
        request["system"] = system_instructions
    if tools:
        request["tools"] = [to_tool(tool) for tool in tools]
    if output_schema and not output_schema.is_plain_text():
        request["output_config"] = {
            "format": {"type": "json_schema", "schema": output_schema.json_schema()},
        }
    if model_settings.temperature is not None:
        request["temperature"] = model_settings.temperature
    return request


def to_output(message):
    output = []
    text = "".join(block.text for block in message.content if block.type == "text")
    if text:
        output.append(ResponseOutputMessage(
            id=message.id,
            type="message",
            role="assistant",
            status="completed",
            content=[ResponseOutputText(type="output_text", text=text, annotations=[])],
        ))
    output.extend(
        ResponseFunctionToolCall(
            type="function_call",
            call_id=block.id,
            name=block.name,
            arguments=json.dumps(block.input),
        )
        for block in message.content
        if block.type == "tool_use"
    )
    return output


def to_usage(usage):
    cache_read = usage.cache_read_input_tokens or 0
    cache_write = usage.cache_creation_input_tokens or 0
    # Anthropic excludes cached tokens from input_tokens while OpenAI includes them
    input_tokens = usage.input_tokens + cache_read + cache_write
    thinking_tokens = usage.output_tokens_details.thinking_tokens if usage.output_tokens_details else 0
    return Usage(
        requests=1,
        input_tokens=input_tokens,
        input_tokens_details=InputTokensDetails(cached_tokens=cache_read, cache_write_tokens=cache_write),
        output_tokens=usage.output_tokens,
        output_tokens_details=OutputTokensDetails(reasoning_tokens=thinking_tokens),
        total_tokens=input_tokens + usage.output_tokens,
    )


class AnthropicModel(Model):
    def __init__(self, model, client=None):
        self.model = model
        self.client = client or AsyncAnthropic()

    async def get_response(
        self,
        system_instructions,
        input,
        model_settings,
        tools,
        output_schema,
        handoffs,
        tracing,
        *,
        previous_response_id,
        conversation_id,
        prompt,
    ):
        if handoffs:
            raise ValueError("Handoffs are not supported by AnthropicModel")
        message = await self.client.messages.create(**build_request(
            self.model, system_instructions, input, model_settings, tools, output_schema,
        ))
        return ModelResponse(
            output=to_output(message),
            usage=to_usage(message.usage),
            response_id=None,
            request_id=message._request_id,
        )

    def stream_response(self, *args, **kwargs):
        raise NotImplementedError("Streaming is not supported by AnthropicModel")
