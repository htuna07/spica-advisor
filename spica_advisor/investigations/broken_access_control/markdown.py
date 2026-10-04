from spica_advisor.markdown import Row, Section, code, escape


SEVERITIES = {
    ("not_applied", True): "high",
    ("not_applied", False): "medium",
    ("applied_but_in_risk", True): "medium",
    ("applied_but_in_risk", False): "low",
}
STATUS_LABELS = {"not_applied": "Not applied", "applied_but_in_risk": "Applied, but at risk"}


def severity(access_report):
    return SEVERITIES[access_report["row_level_security_status"], access_report["includes_sensitive_information"]]


def rows(report, links):
    return [
        Row(severity(bucket["report"]), (
            links.resource(policy["policy_name"], policy["path"]),
            code(f"statement[{statement['statement_index']}]"),
            links.resource(bucket["name"], bucket["path"]),
            bucket["report"]["access"].capitalize(),
            STATUS_LABELS[bucket["report"]["row_level_security_status"]],
            "Yes" if bucket["report"]["includes_sensitive_information"] else "No",
            escape(bucket["report"]["reason"]),
        ))
        for policy in report
        for statement in policy["affected_statements"]
        for bucket in statement["affected_buckets"]
    ]


SECTION = Section(
    title="Broken access control",
    description=(
        "Policies attached to users that can reach buckets without effective row-level security. "
        "Buckets holding sensitive data rank higher."
    ),
    columns=("Policy", "Statement", "Bucket", "Access", "Row-level security", "Sensitive data", "Why"),
    rows=rows,
)
