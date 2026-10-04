from spica_advisor.investigations import broken_access_control, sensitive_env_vars, unauthenticated_endpoints


INVESTIGATIONS = [
    broken_access_control.build(),
    sensitive_env_vars.build(),
    unauthenticated_endpoints.build(),
]
