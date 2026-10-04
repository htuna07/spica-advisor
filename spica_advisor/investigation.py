from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Self

from spica_advisor.llm import LLM
from spica_advisor.log import LOGGER


@dataclass
class InvestigationContext:
    project: str
    llm: LLM
    report: Any = None


Step = Callable[[InvestigationContext], None]


@dataclass(frozen=True)
class Investigation:
    name: str
    context_type: type[InvestigationContext]
    steps: tuple[tuple[str, Step], ...]

    def run(self, project, llm):
        context = self.context_type(project=project, llm=llm)
        for step_name, step in self.steps:
            LOGGER.info("[%s] %s", self.name, step_name)
            step(context)
        return context.report


class InvestigationBuilder:
    def __init__(self, name):
        self._name = name
        self._context_type = None
        self._steps = []

    def with_context(self, context_type) -> Self:
        self._context_type = context_type
        return self

    def step(self, name, step) -> Self:
        self._steps.append((name, step))
        return self

    def build(self) -> Investigation:
        if self._context_type is None:
            raise ValueError(f"Investigation {self._name!r} has no context type")
        if not self._steps:
            raise ValueError(f"Investigation {self._name!r} has no steps")
        step_names = [name for name, _ in self._steps]
        duplicates = sorted({name for name in step_names if step_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"Investigation {self._name!r} has duplicate steps: {duplicates}")
        return Investigation(self._name, self._context_type, tuple(self._steps))
