import argparse
import logging
from pathlib import Path
from pprint import pformat

from spica_advisor.investigations import INVESTIGATIONS
from spica_advisor.log import LOGGER, configure_logging
from spica_advisor.report import write_report
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


def run_investigation(investigation, project, runner):
    report = investigation.run(project, runner)
    write_report(project, investigation.name, report)
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug("Full %s report:\n%s",
                     investigation.name, pformat(report))


def run():
    args = parse_args()
    configure_logging(args.debug, args.log_file, args.log_format)
    try:
        runner = AgentRunner.from_env()
    except Exception:
        LOGGER.exception("Failed to initialize agent runner")
        raise SystemExit(1)

    failed = []
    for investigation in selected_investigations(args.investigations):
        try:
            run_investigation(investigation, args.project, runner)
        except Exception:
            LOGGER.exception("Investigation %s failed", investigation.name)
            failed.append(investigation.name)

    if failed:
        LOGGER.error("Failed investigations: %s", ", ".join(failed))
        raise SystemExit(1)
