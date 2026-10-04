from typing import Literal

from pydantic import BaseModel


class FileReference(BaseModel):
    file_name: str
    line_numbers: list[int]


class Report(BaseModel):
    policy_id: str
    policy_name: str
    attachment_files: list[str]
    references: list[FileReference]


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
