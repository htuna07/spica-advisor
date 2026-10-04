import argparse
from pathlib import Path

from evals.cases import EXPECTED_ROOT, RESOURCES_ROOT, find_cases
from evals.harness import new_run_dir, resolve_matrix, run_matrix, validated_cases
from evals.storage import read_json, write_json
from evals.summary import write_summary
from evals.validation import check_case
from evals.workspace import export_cases, import_cases
from spica_advisor.log import configure_logging


def parse_args():
    parser = argparse.ArgumentParser(prog="python -m evals")
    commands = parser.add_subparsers(dest="command", required=True)

    check = commands.add_parser("check", help="validate eval cases and their labels")
    check.add_argument("cases", nargs="*", metavar="CASE", help="case names; checks all cases when omitted")

    run = commands.add_parser("run", help="run the agents over the cases and summarize the results")
    run.add_argument("--models", nargs="+", metavar="MODEL", help="overrides evals/matrix.yaml")
    run.add_argument("--cases", nargs="+", metavar="CASE", help="overrides evals/matrix.yaml")
    run.add_argument("--tasks", nargs="+", metavar="TASK", help="overrides evals/matrix.yaml")
    run.add_argument("--repeats", type=int, help="overrides evals/matrix.yaml")

    report = commands.add_parser("report", help="re-score a finished run with the current labels and prices")
    report.add_argument("run_dir", type=Path)

    export = commands.add_parser("export-cases", help="write every case as JSON for the cases page")
    export.add_argument("output", type=Path)

    imported = commands.add_parser("import-cases", help="apply cases edited on the cases page to the local files")
    imported.add_argument("input", type=Path)
    return parser.parse_args()


def report_case(case, problems):
    if not problems:
        print(f"{case.name}: ok")
        return
    print(f"{case.name}: {len(problems)} problem(s)")
    for problem in problems:
        print(f"  - {problem}")


def check(names):
    failed = False
    for case in find_cases(EXPECTED_ROOT, RESOURCES_ROOT, names):
        problems = check_case(case)
        report_case(case, problems)
        failed = failed or bool(problems)
    if failed:
        raise SystemExit(1)


def run(args):
    configure_logging(debug=False, log_file=None, log_format="text")
    matrix = resolve_matrix(models=args.models, cases=args.cases, repeats=args.repeats, tasks=args.tasks)
    cases = validated_cases(matrix.cases)
    run_dir = new_run_dir()
    print(f"Writing results to {run_dir}")
    run_matrix(matrix, run_dir, cases)
    print(f"Summary: {write_summary(run_dir)}")


def report(run_dir):
    print(f"Summary: {write_summary(run_dir)}")


def main():
    args = parse_args()
    try:
        if args.command == "check":
            check(args.cases)
        elif args.command == "run":
            run(args)
        elif args.command == "report":
            report(args.run_dir)
        elif args.command == "export-cases":
            write_json(args.output, export_cases())
            print(f"Exported cases to {args.output}")
        else:
            print(f"Imported cases: {import_cases(read_json(args.input))}")
    except ValueError as error:
        raise SystemExit(str(error))
