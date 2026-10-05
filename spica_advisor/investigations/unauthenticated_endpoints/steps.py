from spica_advisor.investigations.unauthenticated_endpoints.agents import ENDPOINT_RISK_AGENT
from spica_advisor.investigations.unauthenticated_endpoints.context import UnauthenticatedEndpointsContext
from spica_advisor.investigations.unauthenticated_endpoints.handlers import has_public_endpoint, served_handler_names
from spica_advisor.investigations.unauthenticated_endpoints.prompts import endpoint_risk_inputs
from spica_advisor.log import LOGGER
from spica_advisor.resources import load_functions, resource_locations


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
    context.analysis_inputs = []
    for function in context.public_functions:
        handlers = served_handler_names(function)
        if handlers:
            context.analysis_inputs.append({"_id": function["_id"], "content": function["content"], "handlers": handlers})
    skipped = len(context.public_functions) - len(context.analysis_inputs)
    if skipped:
        LOGGER.info("Skipped %d functions whose public triggers have no exported handler", skipped)


def endpoint_risk_prompts(context: UnauthenticatedEndpointsContext):
    return endpoint_risk_inputs(context.analysis_inputs)


def analyze_endpoints(context: UnauthenticatedEndpointsContext, build_prompts=endpoint_risk_prompts):
    prompts = build_prompts(context)
    if len(prompts) > 1:
        LOGGER.info("Analyzing %d functions in %d batches", len(context.analysis_inputs), len(prompts))
    for prompt in prompts:
        response = context.runner.run(ENDPOINT_RISK_AGENT, prompt)
        context.function_risks.extend(response.functions)


def function_report(function_risk, location, handlers):
    return {
        "function_id": function_risk.function_id,
        "function_name": location.get("name"),
        "path": location.get("path"),
        "methods": [method.model_dump() for method in function_risk.methods if method.name in handlers],
    }


def report_unauthenticated_endpoints(context: UnauthenticatedEndpointsContext):
    handlers = {function["_id"]: set(function["handlers"]) for function in context.analysis_inputs}
    locations = resource_locations(context.project_dir, "function")
    reports = [
        function_report(function_risk, locations.get(function_risk.function_id, {}), handlers[function_risk.function_id])
        for function_risk in context.function_risks
        if function_risk.function_id in handlers
    ]
    context.report = [report for report in reports if report["methods"]]
    method_count = sum(len(function_risk["methods"]) for function_risk in context.report)
    LOGGER.info("Found %d unauthenticated endpoints in %d functions", method_count, len(context.report))
