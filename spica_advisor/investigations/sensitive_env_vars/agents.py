from agents import Agent

from spica_advisor.investigations.sensitive_env_vars.models import SensitivenessResponse
from spica_advisor.investigations.sensitive_env_vars.prompts import SENSITIVENESS_INSTRUCTIONS


SENSITIVENESS_AGENT = Agent(
    name="Env var sensitiveness classifier",
    instructions=SENSITIVENESS_INSTRUCTIONS,
    output_type=SensitivenessResponse,
)
