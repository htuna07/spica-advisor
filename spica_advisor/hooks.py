from agents import RunHooks

from spica_advisor.log import LOGGER


class InteractionLoggingHooks(RunHooks):
    async def on_llm_start(self, context, agent, system_prompt, input_items):
        LOGGER.debug("LLM call started by %s", agent.name, extra={"payload": {
            "agent": agent.name,
            "system_prompt": system_prompt,
            "input_items": input_items,
        }})

    async def on_llm_end(self, context, agent, response):
        LOGGER.debug("LLM call finished for %s", agent.name, extra={"payload": {
            "agent": agent.name,
            "output_items": [item.model_dump(exclude_none=True) for item in response.output],
            "usage": response.usage,
        }})

    async def on_tool_start(self, context, agent, tool):
        LOGGER.debug("Tool %s called by %s", tool.name, agent.name, extra={"payload": {
            "agent": agent.name,
            "tool": tool.name,
            "call_id": getattr(context, "tool_call_id", None),
            "arguments": getattr(context, "tool_arguments", None),
        }})

    async def on_tool_end(self, context, agent, tool, result):
        LOGGER.debug("Tool %s returned to %s", tool.name, agent.name, extra={"payload": {
            "agent": agent.name,
            "tool": tool.name,
            "call_id": getattr(context, "tool_call_id", None),
            "result": result,
        }})

    async def on_agent_end(self, context, agent, output):
        LOGGER.debug("Agent %s produced final output", agent.name, extra={"payload": {
            "agent": agent.name,
            "output": output,
        }})
