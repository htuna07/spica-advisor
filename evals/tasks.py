from collections.abc import Callable
from dataclasses import dataclass

from agents import Agent

from spica_advisor.investigations.broken_access_control.agents import BUCKET_ACL_AGENT, POLICY_ATTACHMENT_AGENT
from spica_advisor.investigations.broken_access_control.context import BrokenAccessControlContext
from spica_advisor.investigations.broken_access_control.prompts import bucket_acl_input
from spica_advisor.investigations.broken_access_control.steps import find_policy_attachments
from spica_advisor.investigations.broken_access_control.steps import read_functions as read_all_functions
from spica_advisor.investigations.sensitive_env_vars.agents import SENSITIVENESS_AGENT
from spica_advisor.investigations.sensitive_env_vars.context import SensitiveEnvVarsContext
from spica_advisor.investigations.sensitive_env_vars.steps import assess_sensitiveness, read_env_vars
from spica_advisor.investigations.unauthenticated_endpoints.agents import ENDPOINT_RISK_AGENT
from spica_advisor.investigations.unauthenticated_endpoints.context import UnauthenticatedEndpointsContext
from spica_advisor.investigations.unauthenticated_endpoints.steps import (
    analyze_endpoints,
    find_public_functions,
    has_public_endpoint,
    prepare_for_analysis,
)
from spica_advisor.investigations.unauthenticated_endpoints.steps import read_functions as read_endpoint_functions
from spica_advisor.log import LOGGER
from spica_advisor.resources import load_buckets, load_env_vars, load_functions


@dataclass(frozen=True)
class AgentTask:
    name: str
    agent: Agent
    has_input: Callable
    predict: Callable


def predict_sensitive_env_vars(case, labels, runner):
    context = SensitiveEnvVarsContext(project_dir=case.project_dir, runner=runner)
    read_env_vars(context)
    assess_sensitiveness(context)
    return context.sensitiveness_reports


def predict_unauthenticated_endpoints(case, labels, runner):
    context = UnauthenticatedEndpointsContext(project_dir=case.project_dir, runner=runner)
    for step in (read_endpoint_functions, find_public_functions, prepare_for_analysis, analyze_endpoints):
        step(context)
    return [function_risk.model_dump() for function_risk in context.function_risks]


def predict_policy_attachments(case, labels, runner):
    context = BrokenAccessControlContext(project_dir=case.project_dir, runner=runner)
    read_all_functions(context)
    find_policy_attachments(context)
    return [report.model_dump() for report in context.attachment_reports]


def predict_bucket_acl(case, labels, runner):
    buckets = load_buckets(case.project_dir)
    predictions = {}
    # One failed call should not discard the other buckets' answers; the runner still records the failure.
    for bucket_id in labels.bucket_acl:
        try:
            predictions[bucket_id] = runner.run(BUCKET_ACL_AGENT, bucket_acl_input(buckets[bucket_id])).model_dump()
        except Exception:
            LOGGER.exception("Bucket ACL evaluation failed for %s", bucket_id)
    return predictions


TASKS = {
    task.name: task
    for task in (
        AgentTask(
            name="sensitive_env_vars",
            agent=SENSITIVENESS_AGENT,
            has_input=lambda case, labels: bool(load_env_vars(case.project_dir)),
            predict=predict_sensitive_env_vars,
        ),
        AgentTask(
            name="unauthenticated_endpoints",
            agent=ENDPOINT_RISK_AGENT,
            has_input=lambda case, labels: any(
                has_public_endpoint(function["schema"]) for function in load_functions(case.project_dir)
            ),
            predict=predict_unauthenticated_endpoints,
        ),
        AgentTask(
            name="policy_attachments",
            agent=POLICY_ATTACHMENT_AGENT,
            has_input=lambda case, labels: bool(load_functions(case.project_dir)),
            predict=predict_policy_attachments,
        ),
        AgentTask(
            name="bucket_acl",
            agent=BUCKET_ACL_AGENT,
            has_input=lambda case, labels: bool(labels.bucket_acl),
            predict=predict_bucket_acl,
        ),
    )
}
