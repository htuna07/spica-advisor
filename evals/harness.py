import hashlib
import time
from dataclasses import asdict, dataclass
from itertools import count
from datetime import UTC, datetime
from pathlib import Path

import yaml

from evals.cases import EXPECTED_ROOT, RESOURCES_ROOT, find_cases
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


def resolve_matrix(path=MATRIX_PATH, models=None, cases=None, repeats=None, tasks=None):
    defaults = yaml.safe_load(path.read_text(encoding="utf-8"))
    matrix = Matrix(
        models=models or defaults["models"],
        cases=cases or expand(defaults["cases"], [case.name for case in find_cases(EXPECTED_ROOT, RESOURCES_ROOT)]),
        repeats=repeats or defaults["repeats"],
        tasks=tasks or expand(defaults["tasks"], list(TASKS)),
    )
    unknown_models = sorted(set(matrix.models) - set(MODEL_PROFILES))
    unknown_tasks = sorted(set(matrix.tasks) - set(TASKS))
    if unknown_models or unknown_tasks or matrix.repeats < 1:
        raise ValueError(
            f"invalid matrix: unknown models {unknown_models}, unknown tasks {unknown_tasks}, repeats {matrix.repeats}"
        )
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


def output_path(run_dir, model, case, repeat, task):
    return run_dir / "outputs" / model / case / f"r{repeat}" / f"{task}.json"


def validated_cases(names, expected_root=EXPECTED_ROOT, resources_root=RESOURCES_ROOT):
    cases = find_cases(expected_root, resources_root, names)
    invalid = {case.name: problems for case in cases if (problems := check_case(case))}
    if invalid:
        details = "; ".join(f"{name}: {len(problems)} problem(s)" for name, problems in invalid.items())
        raise ValueError(f"fix these cases first (python -m evals check): {details}")
    return cases


def run_task(run_dir, runner, case, labels, repeat, task):
    if not task.has_input(case, labels):
        return
    tags = {"model": runner.profile.name, "case": case.name, "repeat": repeat, "task": task.name}
    first_call = len(runner.calls)
    started = time.perf_counter()
    try:
        prediction, status = task.predict(case, labels, runner), OK_STATUS
    except Exception as error:
        LOGGER.exception("Task %s failed for %s", task.name, case.name)
        prediction, status = None, type(error).__name__
    wall_seconds = round(time.perf_counter() - started, 3)
    calls = runner.calls[first_call:]

    write_json(output_path(run_dir, **tags), {"status": status, "prediction": prediction})
    append_jsonl(run_dir / "runs.jsonl", {**tags, "status": status, "wall_seconds": wall_seconds, "calls": len(calls)})
    for call in calls:
        append_jsonl(run_dir / "calls.jsonl", {**tags, **asdict(call)})
    LOGGER.info("[%s] %s r%d %s: %s, %d calls, %.1fs",
                tags["model"], case.name, repeat, task.name, status, len(calls), wall_seconds)


def prompt_fingerprint(instructions):
    return hashlib.sha256(instructions.encode("utf-8")).hexdigest()[:12]


def run_metadata(matrix):
    return {
        "started_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "model_profiles": {
            model: {"provider": MODEL_PROFILES[model].provider, "model_id": MODEL_PROFILES[model].model_id}
            for model in matrix.models
        },
        "agents": {
            task: {
                "name": TASKS[task].agent.name,
                "prompt_fingerprint": prompt_fingerprint(TASKS[task].agent.instructions),
                "instructions": TASKS[task].agent.instructions,
            }
            for task in matrix.tasks
        },
    }


def run_matrix(matrix, run_dir, cases, create_runner=AgentRunner.from_env):
    write_json(run_dir / "matrix.json", {**asdict(matrix), "metadata": run_metadata(matrix)})
    for model in matrix.models:
        runner = create_runner(MODEL_PROFILES[model])
        for case in cases:
            labels = case.load_labels()
            for repeat in range(1, matrix.repeats + 1):
                for task_name in matrix.tasks:
                    run_task(run_dir, runner, case, labels, repeat, TASKS[task_name])
