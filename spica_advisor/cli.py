import argparse
import logging
from pathlib import Path
from pprint import pformat

from spica_advisor.investigations import INVESTIGATIONS
from spica_advisor.llm import LLM
from spica_advisor.log import LOGGER, configure_logging
from spica_advisor.report import write_report


DEFAULT_PROJECT = "spica-orchestrator"


def parse_args():
    investigation_names = [investigation.name for investigation in INVESTIGATIONS]
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--log-format", choices=("text", "json"), default="text")
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument(
        "--investigation",
        action="append",
        choices=investigation_names,
        dest="investigations",
        help="repeatable; runs all investigations when omitted",
    )
    return parser.parse_args()


def selected_investigations(names):
    if not names:
        return INVESTIGATIONS
    return [investigation for investigation in INVESTIGATIONS if investigation.name in names]


def run_investigation(investigation, project, llm):
    report = investigation.run(project, llm)
    write_report(project, investigation.name, report)
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug("Full %s report:\n%s", investigation.name, pformat(report))


def run():
    args = parse_args()
    configure_logging(args.debug, args.log_file, args.log_format)
    try:
        llm = LLM.from_env()
    except Exception:
        LOGGER.exception("Failed to initialize LLM client")
        raise SystemExit(1)

    failed = []
    for investigation in selected_investigations(args.investigations):
        try:
            run_investigation(investigation, args.project, llm)
        except Exception:
            LOGGER.exception("Investigation %s failed", investigation.name)
            failed.append(investigation.name)

    if failed:
        LOGGER.error("Failed investigations: %s", ", ".join(failed))
        raise SystemExit(1)
