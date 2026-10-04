import json
from pathlib import Path

from spica_advisor.log import LOGGER


OUTPUT_ROOT = Path("output")


def write_report(project, investigation_name, report):
    report_path = OUTPUT_ROOT / project / f"{investigation_name}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote report to %s", report_path)
