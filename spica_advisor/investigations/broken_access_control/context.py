from dataclasses import dataclass, field

from spica_advisor.investigation import InvestigationContext
from spica_advisor.investigations.broken_access_control.models import Report


@dataclass
class BrokenAccessControlContext(InvestigationContext):
    functions: list[dict] = field(default_factory=list)
    attachment_reports: list[Report] = field(default_factory=list)
    policies: list[dict] = field(default_factory=list)
    buckets: dict[str, dict] = field(default_factory=dict)
    bucket_ids: list[str] = field(default_factory=list)
    bucket_acl_reports: dict[str, dict] = field(default_factory=dict)
