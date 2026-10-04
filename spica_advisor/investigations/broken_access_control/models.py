from typing import Literal

from pydantic import BaseModel


class CodeLocation(BaseModel):
    function_id: str
    match: str


class Report(BaseModel):
    attachment: CodeLocation
    definition: CodeLocation
    policy_id: str | None
    policy_name: str | None


class ReportResponse(BaseModel):
    reports: list[Report]


class RowLevelSecurityReport(BaseModel):
    row_level_security_status: Literal[
        "applied",
        "applied_but_in_risk",
        "not_applied",
    ]
    reason: str


class BucketAclReport(BaseModel):
    includes_sensitive_information: bool
    read: RowLevelSecurityReport
    write: RowLevelSecurityReport
