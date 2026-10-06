from spica_advisor.agent import Agent
from spica_advisor.investigations.unauthenticated_endpoints.models import FunctionRiskResponse
from spica_advisor.investigations.unauthenticated_endpoints.prompts import ENDPOINT_RISK_INSTRUCTIONS


ENDPOINT_RISK_AGENT = Agent(
    name="Unauthenticated endpoint risk analyst",
    instructions=ENDPOINT_RISK_INSTRUCTIONS,
    output_type=FunctionRiskResponse,
)
