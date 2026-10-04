import argparse
import logging
from dataclasses import asdict
from pathlib import Path
from pprint import pformat

from spica_advisor.investigations import INVESTIGATIONS
from spica_advisor.log import LOGGER, configure_logging
from spica_advisor.metrics import totals
from spica_advisor.model_profiles import DEFAULT_MODEL, MODEL_PROFILES
from spica_advisor.report import write_metrics, write_report
from spica_advisor.resources import RESOURCES_ROOT
from spica_advisor.runner import AgentRunner


DEFAULT_PROJECT = "spica-orchestrator"


def investigation_names(value):
    known = {investigation.name for investigation in INVESTIGATIONS}
    names = [name.strip() for name in value.split(",") if name.strip()]
    unknown = [name for name in names if name not in known]
    if not names or unknown:
        raise argparse.ArgumentTypeError(
            f"invalid investigation(s): {', '.join(unknown) or value!r} "
            f"(choose from {', '.join(sorted(known))})"
        )
    return names


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument(
        "--log-format", choices=("text", "json"), default="text")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--model", choices=sorted(MODEL_PROFILES), default=DEFAULT_MODEL)
    parser.add_argument(
        "--investigations",
        type=investigation_names,
        metavar="NAME[,NAME...]",
        help=(
            "comma-separated; runs all investigations when omitted; "
            f"available: {', '.join(investigation.name for investigation in INVESTIGATIONS)}"
        ),
    )
    return parser.parse_args()


def selected_investigations(names):
    if not names:
        return INVESTIGATIONS
    return [investigation for investigation in INVESTIGATIONS if investigation.name in names]


def run_investigation(investigation, context, project, model):
    investigation.execute(context)
    write_report(project, model, investigation.name, context.report)
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug("Full %s report:\n%s",
                     investigation.name, pformat(context.report))


def investigation_metrics(context, calls):
    return {
        "step_seconds": context.step_seconds,
        "totals": totals(calls),
        "calls": [asdict(call) for call in calls],
    }


def log_totals(investigation_name, usage):
    LOGGER.info(
        "[%s] %d LLM calls (%d failed), %d requests, %d input tokens (%d cached), "
        "%d output tokens (%d reasoning), %.1fs waiting on LLM",
        investigation_name,
        usage["calls"],
        usage["failed_calls"],
        usage["requests"],
        usage["input_tokens"],
        usage["cached_input_tokens"],
        usage["output_tokens"],
        usage["reasoning_tokens"],
        usage["wall_seconds"],
    )


def run():
    args = parse_args()
    configure_logging(args.debug, args.log_file, args.log_format)
    try:
        runner = AgentRunner.from_env(MODEL_PROFILES[args.model])
    except Exception:
        LOGGER.exception("Failed to initialize agent runner")
        raise SystemExit(1)

    failed = []
    metrics = {}
    for investigation in selected_investigations(args.investigations):
        context = investigation.create_context(RESOURCES_ROOT / args.project, runner)
        first_call = len(runner.calls)
        try:
            run_investigation(investigation, context, args.project, args.model)
        except Exception:
            LOGGER.exception("Investigation %s failed", investigation.name)
            failed.append(investigation.name)
        metrics[investigation.name] = investigation_metrics(context, runner.calls[first_call:])
        log_totals(investigation.name, metrics[investigation.name]["totals"])

    write_metrics(args.project, args.model, metrics)
    if failed:
        LOGGER.error("Failed investigations: %s", ", ".join(failed))
        raise SystemExit(1)
