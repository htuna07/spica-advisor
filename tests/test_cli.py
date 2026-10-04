import sys

import pytest

from spica_advisor.cli import parse_args
from spica_advisor.model_profiles import DEFAULT_MODEL


def parse(monkeypatch, *argv):
    monkeypatch.setattr(sys, "argv", ["spica-advisor", *argv])
    return parse_args()


def test_empty_model_uses_default(monkeypatch):
    assert parse(monkeypatch, "--model", "").model == DEFAULT_MODEL


def test_unknown_model_is_rejected(monkeypatch):
    with pytest.raises(SystemExit):
        parse(monkeypatch, "--model", "gpt-unknown")


def test_empty_investigations_runs_all(monkeypatch):
    assert parse(monkeypatch, "--investigations", "").investigations is None
