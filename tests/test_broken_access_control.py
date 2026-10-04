from spica_advisor.investigations import broken_access_control
from spica_advisor.investigations.broken_access_control.context import BrokenAccessControlContext
from spica_advisor.investigations.broken_access_control.steps import map_findings_to_policies


def write_schema(project_dir, folder, content):
    path = project_dir / folder / "schema.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(content, encoding="utf-8")


def test_reports_buckets_without_effective_row_level_security_whatever_their_sensitivity(tmp_path):
    context = BrokenAccessControlContext(project_dir=tmp_path, runner=None)
    context.policies = [{"_id": "p1", "statement": [
        {"module": "bucket:data", "action": "bucket:data:update", "resource": {"include": ["b1", "b2", "b3"]}},
    ]}]
    context.buckets = {bucket_id: {"_id": bucket_id} for bucket_id in ("b1", "b2", "b3")}
    context.bucket_acl_reports = {
        bucket_id: {"includes_sensitive_information": False,
                    "write": {"row_level_security_status": status, "reason": "r"}}
        for bucket_id, status in (("b1", "not_applied"), ("b2", "applied_but_in_risk"), ("b3", "applied"))
    }

    map_findings_to_policies(context)

    [policy] = context.report
    [statement] = policy["affected_statements"]
    assert [bucket["_id"] for bucket in statement["affected_buckets"]] == ["b1", "b2"]


def test_findings_name_policies_and_buckets_with_their_paths(tmp_path):
    write_schema(tmp_path, "policy/Customer", "_id: p1\nname: Customer Policy\n")
    write_schema(tmp_path, "bucket/Payment-Methods", "_id: b1\ntitle: Payment Methods\n")
    context = BrokenAccessControlContext(project_dir=tmp_path, runner=None)
    context.policies = [{"_id": "p1", "statement": [
        {"module": "bucket:data", "action": "bucket:data:index", "resource": {"include": ["b1"]}},
    ]}]
    context.buckets = {"b1": {"_id": "b1"}}
    context.bucket_acl_reports = {"b1": {
        "includes_sensitive_information": True,
        "read": {"row_level_security_status": "not_applied", "reason": "no filter"},
        "write": {"row_level_security_status": "applied", "reason": "owner only"},
    }}

    map_findings_to_policies(context)

    assert context.report == [{
        "policy_id": "p1",
        "policy_name": "Customer Policy",
        "path": "policy/Customer",
        "affected_statements": [{"statement_index": 0, "affected_buckets": [{
            "_id": "b1",
            "name": "Payment Methods",
            "path": "bucket/Payment-Methods",
            "report": {
                "access": "read",
                "row_level_security_status": "not_applied",
                "reason": "no filter",
                "includes_sensitive_information": True,
            },
        }]}],
    }]


class FailingRunner:
    def run(self, *args, **kwargs):
        raise AssertionError("agent should not run")


def test_skips_agents_when_project_has_no_functions(tmp_path):
    write_schema(tmp_path, "policy/Customer", "_id: p1\nname: Customer\n")
    write_schema(tmp_path, "bucket/Orders", "_id: b1\ntitle: Orders\n")

    assert broken_access_control.build().run(tmp_path, FailingRunner()) == []
