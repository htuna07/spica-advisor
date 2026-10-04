import json
from spica_advisor.log import LOGGER


MARKDOWN_REPORT = "report.md"


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    LOGGER.info("Wrote %s", path)


def write_json(path, data):
    write_text(path, json.dumps(data, indent=2) + "\n")


def write_report(output_dir, investigation_name, report):
    write_json(output_dir / f"{investigation_name}.json", report)


def write_markdown(output_dir, markdown):
    write_text(output_dir / MARKDOWN_REPORT, markdown)
