import time
from dataclasses import asdict, dataclass, field
from itertools import count
from datetime import UTC, datetime
from pathlib import Path

import yaml

from evals.cases import EXPECTED_ROOT, RESOURCES_ROOT, find_cases
from evals.prompts import BASELINE, BASELINE_VARIANT, PROMPTS_ROOT, describe_variant, fingerprint, load_variants
from evals.storage import append_jsonl, write_json
from evals.tasks import TASKS
from evals.validation import check_case
from spica_advisor.log import LOGGER
from spica_advisor.metrics import OK_STATUS
from spica_advisor.model_profiles import MODEL_PROFILES
from spica_advisor.runner import AgentRunner


MATRIX_PATH = Path("evals/matrix.yaml")
RUNS_ROOT = Path("evals/runs")
ALL = "all"


@dataclass(frozen=True)
class Matrix:
    models: list[str]
    cases: list[str]
    repeats: int
    tasks: list[str]
    prompts: dict[str, list[str]] = field(default_factory=dict)

    def prompts_for(self, task):
        return self.prompts.get(task, [BASELINE])


def prompt_problems(prompts, tasks, prompts_root):
    problems = []
    for task, names in prompts.items():
        if task not in tasks:
            problems.append(f"prompts given for {task}, which is not in the run")
            continue
        available = load_variants(task, prompts_root)
        problems += [f"unknown prompt {task}:{name} (available: {', '.join(available)})"
                     for name in names if name not in available]
        if len(set(names)) != len(names) or not names:
            problems.append(f"prompts for {task} must be a non-empty list without duplicates")
    return problems


def resolve_matrix(path=MATRIX_PATH, models=None, cases=None, repeats=None, tasks=None, prompts=None,
                   prompts_root=PROMPTS_ROOT):
    defaults = yaml.safe_load(path.read_text(encoding="utf-8"))
    matrix = Matrix(
        models=models or defaults["models"],
        cases=cases or expand(defaults["cases"], [case.name for case in find_cases(EXPECTED_ROOT, RESOURCES_ROOT)]),
        repeats=repeats or defaults["repeats"],
        tasks=tasks or expand(defaults["tasks"], list(TASKS)),
        prompts=prompts or defaults.get("prompts") or {},
    )
    unknown_models = sorted(set(matrix.models) - set(MODEL_PROFILES))
    unknown_tasks = sorted(set(matrix.tasks) - set(TASKS))
    if unknown_models or unknown_tasks or matrix.repeats < 1:
        raise ValueError(
            f"invalid matrix: unknown models {unknown_models}, unknown tasks {unknown_tasks}, repeats {matrix.repeats}"
        )
    problems = prompt_problems(matrix.prompts, matrix.tasks, prompts_root)
    if problems:
        raise ValueError("invalid prompts: " + "; ".join(problems))
    return matrix


def expand(value, everything):
    return everything if value == ALL else value


def new_run_dir(root=RUNS_ROOT):
    base = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    for suffix in count(1):
        candidate = root / (base if suffix == 1 else f"{base}-{suffix}")
        try:
            candidate.mkdir(parents=True)
            return candidate
        except FileExistsError:
            continue


def output_path(run_dir, model, case, repeat, task, prompt=BASELINE):
    file_name = f"{task}.json" if prompt == BASELINE else f"{task}--{prompt}.json"
    return run_dir / "outputs" / model / case / f"r{repeat}" / file_name


class VariantRunner:
    def __init__(self, runner, agent, replacement):
        self.runner = runner
        self.agent = agent
        self.replacement = replacement

    def run(self, agent, prompt, context=None):
        return self.runner.run(self.replacement if agent is self.agent else agent, prompt, context=context)


def validated_cases(names, expected_root=EXPECTED_ROOT, resources_root=RESOURCES_ROOT):
    cases = find_cases(expected_root, resources_root, names)
    invalid = {case.name: problems for case in cases if (problems := check_case(case))}
    if invalid:
        details = "; ".join(f"{name}: {len(problems)} problem(s)" for name, problems in invalid.items())
        raise ValueError(f"fix these cases first (python -m evals check): {details}")
    return cases


def run_task(run_dir, runner, case, labels, repeat, task, variant=BASELINE_VARIANT):
    if not task.has_input(case, labels):
        return
    tags = {"model": runner.profile.name, "case": case.name, "repeat": repeat, "task": task.name,
            "prompt": variant.name}
    first_call = len(runner.calls)
    variant_runner = VariantRunner(runner, task.agent, variant.agent_for(task.agent))
    started = time.perf_counter()
    try:
        prediction = task.predict(case, labels, variant_runner, task.input_builder(variant.input))
        status = OK_STATUS
    except Exception as error:
        LOGGER.exception("Task %s failed for %s", task.name, case.name)
        prediction, status = None, type(error).__name__
    wall_seconds = round(time.perf_counter() - started, 3)
    calls = runner.calls[first_call:]

    write_json(output_path(run_dir, **tags), {"status": status, "prediction": prediction})
    append_jsonl(run_dir / "runs.jsonl", {**tags, "status": status, "wall_seconds": wall_seconds, "calls": len(calls)})
    for call in calls:
        append_jsonl(run_dir / "calls.jsonl", {**tags, **asdict(call)})
    LOGGER.info("[%s] %s r%d %s (%s): %s, %d calls, %.1fs",
                tags["model"], case.name, repeat, task.name, variant.name, status, len(calls), wall_seconds)


def agent_metadata(matrix, task, variants):
    agent = TASKS[task].agent
    return {
        "name": agent.name,
        "prompt_fingerprint": fingerprint(agent.instructions),
        "instructions": agent.instructions,
        "prompts": {name: describe_variant(task, variants[name]) for name in matrix.prompts_for(task)},
    }


def run_metadata(matrix, variants):
    return {
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model_profiles": {
            model: {"provider": MODEL_PROFILES[model].provider, "model_id": MODEL_PROFILES[model].model_id}
            for model in matrix.models
        },
        "agents": {task: agent_metadata(matrix, task, variants[task]) for task in matrix.tasks},
    }


def run_matrix(matrix, run_dir, cases, create_runner=AgentRunner.from_env, prompts_root=PROMPTS_ROOT):
    variants = {task: load_variants(task, prompts_root) for task in matrix.tasks}
    write_json(run_dir / "matrix.json", {**asdict(matrix), "metadata": run_metadata(matrix, variants)})
    for model in matrix.models:
        runner = create_runner(MODEL_PROFILES[model])
        for case in cases:
            labels = case.load_labels()
            for repeat in range(1, matrix.repeats + 1):
                for task_name in matrix.tasks:
                    for prompt in matrix.prompts_for(task_name):
                        run_task(run_dir, runner, case, labels, repeat, TASKS[task_name], variants[task_name][prompt])
