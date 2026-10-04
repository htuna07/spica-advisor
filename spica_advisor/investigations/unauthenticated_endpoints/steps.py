from spica_advisor.investigations.unauthenticated_endpoints.agents import ENDPOINT_RISK_AGENT
from spica_advisor.investigations.unauthenticated_endpoints.context import UnauthenticatedEndpointsContext
from spica_advisor.investigations.unauthenticated_endpoints.prompts import endpoint_risk_input
from spica_advisor.log import LOGGER
from spica_advisor.resources import load_functions


def is_public_endpoint(trigger):
    return (
        trigger.get("type") == "http"
        and trigger.get("active") is True
        and not (trigger.get("options") or {}).get("authorize")
    )


def has_public_endpoint(schema):
    return any(is_public_endpoint(trigger) for trigger in (schema.get("triggers") or {}).values())


def read_functions(context: UnauthenticatedEndpointsContext):
    context.functions = load_functions(context.project)
    LOGGER.info("Discovered %d functions", len(context.functions))


def find_public_functions(context: UnauthenticatedEndpointsContext):
    context.public_functions = [
        function for function in context.functions
        if has_public_endpoint(function["schema"])
    ]
    LOGGER.info("Found %d functions with public endpoints", len(context.public_functions))


def prepare_for_analysis(context: UnauthenticatedEndpointsContext):
    context.analysis_inputs = [
        {"_id": function["_id"], "content": function["content"]}
        for function in context.public_functions
    ]


def analyze_endpoints(context: UnauthenticatedEndpointsContext):
    if not context.analysis_inputs:
        return
    response = context.runner.run(ENDPOINT_RISK_AGENT, endpoint_risk_input(context.analysis_inputs))
    context.function_risks = response.functions


def report_unauthenticated_endpoints(context: UnauthenticatedEndpointsContext):
    analyzed_ids = {function["_id"] for function in context.analysis_inputs}
    context.report = [
        function_risk.model_dump()
        for function_risk in context.function_risks
        if function_risk.function_id in analyzed_ids and function_risk.methods
    ]
    method_count = sum(len(function_risk["methods"]) for function_risk in context.report)
    LOGGER.info("Found %d unauthenticated endpoints in %d functions", method_count, len(context.report))
