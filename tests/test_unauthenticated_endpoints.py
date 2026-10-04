from spica_advisor import resources
from spica_advisor.investigations import unauthenticated_endpoints
from spica_advisor.investigations.unauthenticated_endpoints.agents import ENDPOINT_RISK_AGENT
from spica_advisor.investigations.unauthenticated_endpoints.models import (
    FunctionRisk,
    FunctionRiskResponse,
    MethodRisk,
)


def write_function(root, project, function_id, triggers, content):
    folder = root / project / "function" / function_id
    folder.mkdir(parents=True)
    (folder / "schema.yaml").write_text(
        f"_id: {function_id}\nname: {function_id}\ntriggers:\n{triggers}",
        encoding="utf-8",
    )
    (folder / "index.mjs").write_text(content, encoding="utf-8")


PUBLIC_HTTP = """  handler:
    type: http
    active: true
    options:
      method: Get
      path: /public
      authorize: false
"""

PUBLIC_HTTP_WITHOUT_AUTHORIZE = """  handler:
    type: http
    active: true
    options:
      method: Get
      path: /public
"""

AUTHORIZED_HTTP = """  handler:
    type: http
    active: true
    options:
      method: Get
      path: /private
      authorize: true
"""

INACTIVE_HTTP = """  handler:
    type: http
    active: false
    options:
      method: Get
      path: /inactive
"""

SCHEDULE = """  handler:
    type: schedule
    active: true
    options:
      frequency: "* * * * *"
"""


class FakeRunner:
    def __init__(self, response):
        self.response = response
        self.agents = []
        self.prompts = []

    def run(self, agent, prompt):
        self.agents.append(agent)
        self.prompts.append(prompt)
        return self.response


def test_load_function_definitions_includes_id_schema_and_content(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "RESOURCES_ROOT", tmp_path)
    write_function(tmp_path, "demo", "fn-1", PUBLIC_HTTP, "export function handler() {}")

    [definition] = resources.load_function_definitions("demo")

    assert definition["_id"] == "fn-1"
    assert definition["schema"]["triggers"]["handler"]["type"] == "http"
    assert definition["content"] == "export function handler() {}"


def test_sends_only_public_functions_without_schema_to_agent(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "RESOURCES_ROOT", tmp_path)
    write_function(tmp_path, "demo", "public", PUBLIC_HTTP, "// public source")
    write_function(tmp_path, "demo", "no-authorize", PUBLIC_HTTP_WITHOUT_AUTHORIZE, "// no authorize source")
    write_function(tmp_path, "demo", "authorized", AUTHORIZED_HTTP, "// authorized source")
    write_function(tmp_path, "demo", "inactive", INACTIVE_HTTP, "// inactive source")
    write_function(tmp_path, "demo", "scheduled", SCHEDULE, "// scheduled source")
    runner = FakeRunner(FunctionRiskResponse(functions=[]))

    unauthenticated_endpoints.build().run("demo", runner)

    assert runner.agents == [ENDPOINT_RISK_AGENT]
    [prompt] = runner.prompts
    assert "// public source" in prompt
    assert "// no authorize source" in prompt
    assert "// authorized source" not in prompt
    assert "// inactive source" not in prompt
    assert "// scheduled source" not in prompt
    assert "/public" not in prompt


def test_reports_method_risks_grouped_by_analyzed_function(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "RESOURCES_ROOT", tmp_path)
    write_function(tmp_path, "demo", "fn-1", PUBLIC_HTTP, "export function handler(req, res) {}")
    write_function(tmp_path, "demo", "fn-2", PUBLIC_HTTP, "export function handler(req, res) {}")
    runner = FakeRunner(FunctionRiskResponse(functions=[
        FunctionRisk(function_id="fn-1", methods=[
            MethodRisk(name="handler", risk_level="high", reason="writes bucket"),
            MethodRisk(name="health", risk_level="low", reason="returns OK"),
        ]),
        FunctionRisk(function_id="fn-2", methods=[]),
        FunctionRisk(function_id="unknown", methods=[
            MethodRisk(name="other", risk_level="low", reason="hallucinated"),
        ]),
    ]))

    report = unauthenticated_endpoints.build().run("demo", runner)

    assert report == [
        {
            "function_id": "fn-1",
            "methods": [
                {"name": "handler", "risk_level": "high", "reason": "writes bucket"},
                {"name": "health", "risk_level": "low", "reason": "returns OK"},
            ],
        },
    ]


def test_skips_agent_when_no_public_functions(tmp_path, monkeypatch):
    monkeypatch.setattr(resources, "RESOURCES_ROOT", tmp_path)
    write_function(tmp_path, "demo", "authorized", AUTHORIZED_HTTP, "// authorized source")
    runner = FakeRunner(response=None)

    assert unauthenticated_endpoints.build().run("demo", runner) == []
    assert runner.prompts == []
