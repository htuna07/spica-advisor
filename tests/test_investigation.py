from dataclasses import dataclass, field

import pytest

from spica_advisor.investigation import InvestigationBuilder, InvestigationContext


@dataclass
class RecordingContext(InvestigationContext):
    calls: list[str] = field(default_factory=list)


def record(name):
    def step(context):
        context.calls.append(name)
    return step


def test_build_requires_context_type():
    with pytest.raises(ValueError, match="no context type"):
        InvestigationBuilder("demo").step("first", record("first")).build()


def test_build_requires_at_least_one_step():
    with pytest.raises(ValueError, match="no steps"):
        InvestigationBuilder("demo").with_context(RecordingContext).build()


def test_build_rejects_duplicate_step_names():
    builder = (
        InvestigationBuilder("demo")
        .with_context(RecordingContext)
        .step("same", record("a"))
        .step("same", record("b"))
    )
    with pytest.raises(ValueError, match="duplicate steps: \\['same'\\]"):
        builder.build()


def test_run_executes_steps_in_order_on_shared_context_and_returns_report():
    def finish(context):
        context.report = {"project": context.project, "calls": list(context.calls)}

    investigation = (
        InvestigationBuilder("demo")
        .with_context(RecordingContext)
        .step("first", record("first"))
        .step("second", record("second"))
        .step("finish", finish)
        .build()
    )

    report = investigation.run("some-project", llm=None)

    assert report == {"project": "some-project", "calls": ["first", "second"]}


def test_each_run_gets_a_fresh_context():
    def finish(context):
        context.report = list(context.calls)

    investigation = (
        InvestigationBuilder("demo")
        .with_context(RecordingContext)
        .step("first", record("first"))
        .step("finish", finish)
        .build()
    )

    assert investigation.run("p", llm=None) == ["first"]
    assert investigation.run("p", llm=None) == ["first"]
