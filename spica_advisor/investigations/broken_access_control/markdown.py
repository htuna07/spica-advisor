from spica_advisor.markdown import Row, Section, code, escape, table


SEVERITIES = {
    ("not_applied", True): "high",
    ("not_applied", False): "medium",
    ("applied_but_in_risk", True): "medium",
    ("applied_but_in_risk", False): "low",
}
STATUS_LABELS = {"not_applied": "Not applied", "applied_but_in_risk": "Applied, but at risk"}
MAX_SNIPPET_CHARS = 150
ATTACHMENT_COLUMNS = ("Policy", "Attached in", "Attaching code", "Defined in", "Defining code")


def severity(access_report):
    return SEVERITIES[access_report["row_level_security_status"], access_report["includes_sensitive_information"]]


def snippet(text):
    line = " ".join(text.split())
    return line if len(line) <= MAX_SNIPPET_CHARS else line[:MAX_SNIPPET_CHARS - 1] + "…"


def code_cells(location, links):
    return links.resource(location["function_name"], location["path"]), escape(code(snippet(location["match"])))


def attachments_table(report, links):
    rows = [
        [
            links.resource(policy["policy_name"], policy["path"]),
            *code_cells(attachment["attachment"], links),
            *code_cells(attachment["definition"], links),
        ]
        for policy in report
        for attachment in policy["attachments"]
    ]
    if not rows:
        return ""
    return "#### Where these policies are attached to users\n\n" + table(ATTACHMENT_COLUMNS, rows)


def rows(report, links):
    return [
        Row(severity(bucket["report"]), (
            links.resource(policy["policy_name"], policy["path"]),
            code(f"statement[{statement['statement_index']}]"),
            links.resource(bucket["name"], bucket["path"]),
            bucket["report"]["access"].capitalize(),
            "Yes" if bucket["report"]["includes_sensitive_information"] else "No",
            STATUS_LABELS[bucket["report"]["row_level_security_status"]],
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
    columns=("Policy", "Statement", "Bucket", "Access", "Sensitive data", "Row-level security", "Why"),
    rows=rows,
    appendix=attachments_table,
)
