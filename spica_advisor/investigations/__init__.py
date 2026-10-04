from spica_advisor.investigations import broken_access_control, sensitive_env_vars


INVESTIGATIONS = [
    broken_access_control.build(),
    sensitive_env_vars.build(),
]
