from dataclasses import dataclass, field

from spica_advisor.investigation import InvestigationContext
from spica_advisor.investigations.unauthenticated_endpoints.models import FunctionRisk


@dataclass
class UnauthenticatedEndpointsContext(InvestigationContext):
    functions: list[dict] = field(default_factory=list)
    public_functions: list[dict] = field(default_factory=list)
    analysis_inputs: list[dict] = field(default_factory=list)
    function_risks: list[FunctionRisk] = field(default_factory=list)
