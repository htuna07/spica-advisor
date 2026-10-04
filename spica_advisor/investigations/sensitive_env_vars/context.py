from dataclasses import dataclass, field

from spica_advisor.investigation import InvestigationContext


@dataclass
class SensitiveEnvVarsContext(InvestigationContext):
    env_vars: list[dict] = field(default_factory=list)
    sensitiveness_reports: dict[str, dict] = field(default_factory=dict)
