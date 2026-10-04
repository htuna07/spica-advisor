from agents import Agent

from spica_advisor.investigations.broken_access_control.models import BucketAclReport, ReportResponse
from spica_advisor.investigations.broken_access_control.prompts import ATTACHMENT_INSTRUCTIONS, BUCKET_ACL_INSTRUCTIONS


POLICY_ATTACHMENT_AGENT = Agent(
    name="Policy attachment finder",
    instructions=ATTACHMENT_INSTRUCTIONS,
    output_type=ReportResponse,
)

BUCKET_ACL_AGENT = Agent(
    name="Bucket ACL evaluator",
    instructions=BUCKET_ACL_INSTRUCTIONS,
    output_type=BucketAclReport,
)
