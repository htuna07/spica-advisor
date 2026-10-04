from urllib.error import HTTPError

import pytest

from spica_advisor.github import (
    ISSUE_LABEL,
    MAX_ISSUE_BODY_CHARS,
    GitHubIssues,
    append_step_summary,
    issue_body,
    report_metadata,
    step_summary_path,
)
from spica_advisor.markdown import MarkdownReport


class FakeApi:
    def __init__(self, open_issues=(), label_exists=False):
        self.open_issues = list(open_issues)
        self.label_exists = label_exists
        self.calls = []

    def __call__(self, method, path, payload=None):
        self.calls.append((method, path, payload))
        if method == "GET":
            return self.open_issues
        if path.endswith("/labels") and self.label_exists:
            raise HTTPError(path, 422, "Unprocessable Entity", {}, None)
        return {"number": 42}

    def writes(self):
        return [(method, path, payload) for method, path, payload in self.calls if method != "GET"]


def report(finding_count=1, complete=True):
    return MarkdownReport(text="report", finding_count=finding_count, complete=complete)


def test_creates_labeled_issue_when_findings_and_no_open_issue():
    api = FakeApi()

    GitHubIssues(api, "o/r").sync(report())

    assert api.writes() == [
        ("POST", "/repos/o/r/labels", {"name": ISSUE_LABEL, "color": "d93f0b",
                                       "description": "Findings from Spica Advisor"}),
        ("POST", "/repos/o/r/issues", {"title": "Spica Advisor report", "body": "report", "labels": [ISSUE_LABEL]}),
    ]


def test_existing_label_does_not_block_issue_creation():
    api = FakeApi(label_exists=True)

    GitHubIssues(api, "o/r").sync(report())

    assert api.writes()[-1][1] == "/repos/o/r/issues"


def test_updates_open_issue_instead_of_creating_another():
    api = FakeApi(open_issues=[{"number": 1, "pull_request": {}}, {"number": 7}])

    GitHubIssues(api, "o/r").sync(report())

    assert api.writes() == [("PATCH", "/repos/o/r/issues/7", {"body": "report"})]


def test_closes_open_issue_after_complete_clean_scan():
    api = FakeApi(open_issues=[{"number": 7}])

    GitHubIssues(api, "o/r").sync(report(finding_count=0))

    assert api.writes() == [("PATCH", "/repos/o/r/issues/7", {"body": "report", "state": "closed"})]


def test_keeps_issue_open_when_clean_scan_is_incomplete():
    api = FakeApi(open_issues=[{"number": 7}])

    GitHubIssues(api, "o/r").sync(report(finding_count=0, complete=False))

    assert api.writes() == [("PATCH", "/repos/o/r/issues/7", {"body": "report", "state": "open"})]


def test_clean_scan_without_open_issue_does_nothing():
    api = FakeApi()

    GitHubIssues(api, "o/r").sync(report(finding_count=0))

    assert api.writes() == []


def test_long_issue_body_is_truncated_with_link_to_run():
    body = issue_body("x" * (MAX_ISSUE_BODY_CHARS + 10), "https://run")

    assert len(body) == MAX_ISSUE_BODY_CHARS
    assert body.endswith("See the full report in the [workflow run](https://run).\n")


def test_issues_require_token_and_repository(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")

    with pytest.raises(RuntimeError, match="GITHUB_TOKEN"):
        GitHubIssues.from_env()


def test_metadata_links_to_project_dir_inside_workspace(monkeypatch, tmp_path):
    (tmp_path / "spica").mkdir()
    monkeypatch.setenv("GITHUB_WORKSPACE", str(tmp_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", "o/r")
    monkeypatch.setenv("GITHUB_SHA", "abc")
    monkeypatch.setenv("GITHUB_RUN_ID", "9")
    monkeypatch.delenv("GITHUB_SERVER_URL", raising=False)

    metadata = report_metadata("m", tmp_path / "spica")

    assert metadata.commit_url == "https://github.com/o/r/commit/abc"
    assert metadata.run_url == "https://github.com/o/r/actions/runs/9"
    assert metadata.source_url == "https://github.com/o/r/tree/abc/spica"
    assert report_metadata("m", tmp_path).source_url == "https://github.com/o/r/tree/abc"


def test_metadata_outside_github_has_no_links(monkeypatch):
    monkeypatch.delenv("GITHUB_REPOSITORY", raising=False)

    assert report_metadata("m", ".").source_url is None


def test_step_summary_is_appended(monkeypatch, tmp_path):
    summary = tmp_path / "summary.md"
    summary.write_text("earlier\n", encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    append_step_summary(step_summary_path(), "report\n")

    assert summary.read_text(encoding="utf-8") == "earlier\nreport\n"


def test_step_summary_requires_github_actions(monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    with pytest.raises(RuntimeError, match="GITHUB_STEP_SUMMARY"):
        step_summary_path()
