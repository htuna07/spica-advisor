import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from spica_advisor.log import LOGGER
from spica_advisor.markdown import REPORT_TITLE, ReportMetadata


DEFAULT_SERVER_URL = "https://github.com"
DEFAULT_API_URL = "https://api.github.com"
ISSUE_LABEL = "spica-advisor"
LABEL_COLOR = "d93f0b"
# GitHub rejects issue bodies over 65,536 characters; the margin covers characters it counts as more than one.
MAX_ISSUE_BODY_CHARS = 60000
REQUEST_TIMEOUT_SECONDS = 30


def source_url(repository_url, sha, project_dir):
    workspace = Path(os.environ.get("GITHUB_WORKSPACE", ".")).resolve()
    try:
        relative = Path(project_dir).resolve().relative_to(workspace).as_posix()
    except ValueError:
        return None
    tree_url = f"{repository_url}/tree/{sha}"
    return tree_url if relative == "." else f"{tree_url}/{quote(relative)}"


def report_metadata(model, project_dir, effort=None):
    repository = os.environ.get("GITHUB_REPOSITORY")
    sha = os.environ.get("GITHUB_SHA")
    if not (repository and sha):
        return ReportMetadata(model=model, effort=effort)
    repository_url = f"{os.environ.get('GITHUB_SERVER_URL', DEFAULT_SERVER_URL)}/{repository}"
    run_id = os.environ.get("GITHUB_RUN_ID")
    return ReportMetadata(
        model=model,
        effort=effort,
        commit=sha,
        commit_url=f"{repository_url}/commit/{sha}",
        run_url=f"{repository_url}/actions/runs/{run_id}" if run_id else None,
        source_url=source_url(repository_url, sha, project_dir),
    )


def step_summary_path():
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        raise RuntimeError("GITHUB_STEP_SUMMARY is not set; job summaries are only available in GitHub Actions")
    return Path(path)


def append_step_summary(path, markdown):
    with path.open("a", encoding="utf-8") as file:
        file.write(markdown)
    LOGGER.info("Appended the report to the job summary")


def issue_body(markdown, run_url):
    if len(markdown) <= MAX_ISSUE_BODY_CHARS:
        return markdown
    full_report = f"[workflow run]({run_url})" if run_url else "job summary"
    notice = f"\n\n…\n\n> ⚠️ The report is too long for an issue. See the full report in the {full_report}.\n"
    return markdown[:MAX_ISSUE_BODY_CHARS - len(notice)] + notice


def github_api(api_url, token):
    def request(method, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        with urlopen(Request(f"{api_url}{path}", data=data, method=method, headers=headers),
                     timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return json.load(response)
    return request


class GitHubIssues:
    def __init__(self, api, repository):
        self.api = api
        self.repository = repository

    @classmethod
    def from_env(cls):
        token = os.environ.get("GITHUB_TOKEN")
        repository = os.environ.get("GITHUB_REPOSITORY")
        if not (token and repository):
            raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required to publish the report issue")
        return cls(github_api(os.environ.get("GITHUB_API_URL", DEFAULT_API_URL), token), repository)

    def sync(self, report, run_url=None):
        issue = self.find_open_issue()
        body = issue_body(report.text, run_url)
        if report.finding_count:
            if issue:
                self.update(issue, body=body)
            else:
                self.create(body)
        elif issue:
            # A failed investigation may have missed findings, so only a complete clean scan closes the issue.
            self.update(issue, body=body, state="closed" if report.complete else "open")

    def find_open_issue(self):
        issues = self.api("GET", f"/repos/{self.repository}/issues?labels={ISSUE_LABEL}&state=open&per_page=100")
        return next((issue for issue in issues if "pull_request" not in issue), None)

    def create(self, body):
        self.ensure_label()
        issue = self.api("POST", f"/repos/{self.repository}/issues",
                         {"title": REPORT_TITLE, "body": body, "labels": [ISSUE_LABEL]})
        LOGGER.info("Created issue #%d", issue["number"])

    def update(self, issue, **fields):
        self.api("PATCH", f"/repos/{self.repository}/issues/{issue['number']}", fields)
        LOGGER.info("Updated issue #%d%s", issue["number"], " and closed it" if fields.get("state") == "closed" else "")

    def ensure_label(self):
        try:
            self.api("POST", f"/repos/{self.repository}/labels",
                     {"name": ISSUE_LABEL, "color": LABEL_COLOR, "description": "Findings from Spica Advisor"})
        except HTTPError as error:
            # 422 means the label already exists.
            if error.code != 422:
                raise
