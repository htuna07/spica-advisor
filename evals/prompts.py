import difflib
import hashlib
import re
from dataclasses import replace
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from evals.tasks import DEFAULT_INPUT, TASKS


PROMPTS_ROOT = Path("evals/prompts")
BASELINE = "baseline"
VARIANT_NAME = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
BASELINE_DESCRIPTION = "The prompt the advisor ships with."


class PromptVariant(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    description: str = ""
    instructions: str | None = None
    input: str = DEFAULT_INPUT

    def instructions_for(self, agent):
        return self.instructions if self.instructions is not None else agent.instructions

    def agent_for(self, agent):
        return agent if self.instructions is None else replace(agent, instructions=self.instructions)


BASELINE_VARIANT = PromptVariant(name=BASELINE, description=BASELINE_DESCRIPTION)


def read_variant(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return PromptVariant.model_validate({**data, "name": path.stem})


def variant_problems(task_name, variant):
    task = TASKS[task_name]
    problems = []
    if not VARIANT_NAME.match(variant.name):
        problems.append(f"invalid variant name {variant.name!r}: use lowercase letters, digits and dashes")
    if variant.input != DEFAULT_INPUT and variant.input not in task.inputs:
        known = ", ".join([DEFAULT_INPUT, *task.inputs])
        problems.append(f"unknown input {variant.input!r} (available: {known})")
    if variant.instructions is not None and not variant.instructions.strip():
        problems.append("instructions are empty")
    return [f"{task_name}/{variant.name}: {problem}" for problem in problems]


def load_variants(task_name, root=PROMPTS_ROOT):
    variants = {BASELINE: BASELINE_VARIANT}
    folder = Path(root) / task_name
    if not folder.is_dir():
        return variants
    problems = []
    for path in sorted(folder.glob("*.yaml")):
        if path.stem == BASELINE:
            problems.append(f"{task_name}/{BASELINE}: reserved for the production prompt")
            continue
        variant = read_variant(path)
        problems += variant_problems(task_name, variant)
        variants[variant.name] = variant
    if problems:
        raise ValueError("invalid prompt variants: " + "; ".join(problems))
    return variants


def all_variants(root=PROMPTS_ROOT):
    return {task_name: load_variants(task_name, root) for task_name in TASKS}


def fingerprint(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def instructions_diff(baseline, instructions):
    return list(difflib.unified_diff(
        baseline.strip().splitlines(), instructions.strip().splitlines(),
        fromfile=BASELINE, tofile="variant", lineterm="", n=2,
    ))


def describe_variant(task_name, variant):
    agent = TASKS[task_name].agent
    instructions = variant.instructions_for(agent)
    return {
        "description": variant.description,
        "input": variant.input,
        "prompt_fingerprint": fingerprint(instructions),
        "instructions": instructions,
        "diff": instructions_diff(agent.instructions, instructions),
    }
