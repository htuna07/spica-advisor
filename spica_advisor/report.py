import json
from pathlib import Path

from spica_advisor.log import LOGGER


OUTPUT_ROOT = Path("output")


def output_dir(project, model):
    return OUTPUT_ROOT / project / model


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %s", path)


def write_report(project, model, investigation_name, report):
    write_json(output_dir(project, model) / f"{investigation_name}.json", report)

