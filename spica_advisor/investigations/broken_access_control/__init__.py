from spica_advisor.investigation import InvestigationBuilder
from spica_advisor.investigations.broken_access_control.context import BrokenAccessControlContext
from spica_advisor.investigations.broken_access_control.steps import (
    evaluate_bucket_rules,
    find_bucket_accesses,
    find_policy_attachments,
    load_relevant_policies,
    map_findings_to_policies,
    read_functions,
)


def build():
    return (
        InvestigationBuilder("broken-access-control")
        .with_context(BrokenAccessControlContext)
        .step("read functions", read_functions)
        .step("find policy attachments", find_policy_attachments)
        .step("load relevant policies", load_relevant_policies)
        .step("find bucket accesses", find_bucket_accesses)
        .step("evaluate bucket rules", evaluate_bucket_rules)
        .step("map findings to policies", map_findings_to_policies)
        .build()
    )
