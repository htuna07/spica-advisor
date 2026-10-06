import sys

from spica_advisor.cli import parse_args


def parse(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["spica-advisor", *argv])
    return parse_args()


def test_empty_investigations_runs_all(monkeypatch):
    assert parse(monkeypatch, "--investigations", "").investigations is None
