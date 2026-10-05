from spica_advisor.investigations.unauthenticated_endpoints.agents import ENDPOINT_RISK_AGENT
from spica_advisor.investigations.unauthenticated_endpoints.context import UnauthenticatedEndpointsContext
from spica_advisor.investigations.unauthenticated_endpoints.prompts import endpoint_risk_inputs
from spica_advisor.log import LOGGER
from spica_advisor.resources import load_functions, resource_locations


def is_public_endpoint(trigger):
    return (
        trigger.get("type") == "http"
        and trigger.get("active") is True
        and not (trigger.get("options") or {}).get("authorize")
    )


def has_public_endpoint(schema):
    return any(is_public_endpoint(trigger) for trigger in (schema.get("triggers") or {}).values())


def read_functions(context: UnauthenticatedEndpointsContext):
    context.functions = load_functions(context.project_dir)
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


def endpoint_risk_prompts(context: UnauthenticatedEndpointsContext):
    return endpoint_risk_inputs(context.analysis_inputs)


def analyze_endpoints(context: UnauthenticatedEndpointsContext, build_prompts=endpoint_risk_prompts):
    prompts = build_prompts(context)
    if len(prompts) > 1:
        LOGGER.info("Analyzing %d functions in %d batches", len(context.analysis_inputs), len(prompts))
    for prompt in prompts:
        response = context.runner.run(ENDPOINT_RISK_AGENT, prompt)
        context.function_risks.extend(response.functions)


def function_report(function_risk, location):
    return {
        "function_id": function_risk.function_id,
        "function_name": location.get("name"),
        "path": location.get("path"),
        "methods": [method.model_dump() for method in function_risk.methods],
    }


def report_unauthenticated_endpoints(context: UnauthenticatedEndpointsContext):
    analyzed_ids = {function["_id"] for function in context.analysis_inputs}
    locations = resource_locations(context.project_dir, "function")
    context.report = [
        function_report(function_risk, locations.get(function_risk.function_id, {}))
        for function_risk in context.function_risks
        if function_risk.function_id in analyzed_ids and function_risk.methods
    ]
    method_count = sum(len(function_risk["methods"]) for function_risk in context.report)
    LOGGER.info("Found %d unauthenticated endpoints in %d functions", method_count, len(context.report))
