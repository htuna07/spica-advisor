from spica_advisor.investigations.sensitive_env_vars.context import SensitiveEnvVarsContext
from spica_advisor.investigations.sensitive_env_vars.models import SensitivenessResponse
from spica_advisor.investigations.sensitive_env_vars.prompts import sensitiveness_prompt
from spica_advisor.log import LOGGER
from spica_advisor.resources import load_env_vars


REPORTED_LEVELS = {"medium", "high"}


def read_env_vars(context: SensitiveEnvVarsContext):
    context.env_vars = load_env_vars(context.project)
    LOGGER.info("Discovered %d env vars", len(context.env_vars))


def assess_sensitiveness(context: SensitiveEnvVarsContext):
    if not context.env_vars:
        return
    names = [env_var["name"] for env_var in context.env_vars]
    response = context.llm.parse(sensitiveness_prompt(names), SensitivenessResponse)
    context.sensitiveness_reports = {
        assessment.name: assessment.model_dump(exclude={"name"})
        for assessment in response.env_vars
    }


def report_sensitive_env_vars(context: SensitiveEnvVarsContext):
    context.report = [
        {"_id": env_var["_id"], "report": report}
        for env_var in context.env_vars
        if (report := context.sensitiveness_reports.get(env_var["name"]))
        and report["sensitiveness_level"] in REPORTED_LEVELS
    ]
    LOGGER.info("Found %d sensitive env vars", len(context.report))
