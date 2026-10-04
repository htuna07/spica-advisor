import json
from spica_advisor.log import LOGGER


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote %s", path)


def write_report(output_dir, investigation_name, report):
    write_json(output_dir / f"{investigation_name}.json", report)
