from spica_advisor.investigation import InvestigationBuilder
from spica_advisor.investigations.sensitive_env_vars.context import SensitiveEnvVarsContext
from spica_advisor.investigations.sensitive_env_vars.steps import (
    assess_sensitiveness,
    read_env_vars,
    report_sensitive_env_vars,
)


def build():
    return (
        InvestigationBuilder("sensitive-env-vars")
        .with_context(SensitiveEnvVarsContext)
        .step("read env vars", read_env_vars)
        .step("assess sensitiveness", assess_sensitiveness)
        .step("report sensitive env vars", report_sensitive_env_vars)
        .build()
    )
