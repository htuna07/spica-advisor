import argparse
import glob
import json
import logging
import re
import sys
from copy import deepcopy
from pathlib import Path
from pprint import pformat
from typing import Literal

import yaml
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


MODEL = "gpt-6-luna"
LOGGER = logging.getLogger("spica_advisor")


class JsonFormatter(logging.Formatter):
    def format(self, record):
        event = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
        }
        if hasattr(record, "payload"):
            event["payload"] = record.payload
        if record.exc_info:
            event["exception"] = self.formatException(record.exc_info)
        return json.dumps(event, default=str)


class FileReference(BaseModel):
    file_name: str
    line_numbers: list[int]


class Report(BaseModel):
    policy_id: str
    policy_name: str
    attachment_files: list[str]
    references: list[FileReference]


class ReportResponse(BaseModel):
    reports: list[Report]


class RowLevelSecurityReport(BaseModel):
    row_level_security_status: Literal[
        "applied",
        "applied_but_in_risk",
        "not_applied",
    ]
    reason: str


class BucketAclReport(BaseModel):
    includes_sensitive_information: bool
    read: RowLevelSecurityReport
    write: RowLevelSecurityReport


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--log-file", type=Path)
    parser.add_argument(
        "--log-format", choices=("text", "json"), default="text")
    return parser.parse_args()


def configure_logging(args):
    handler = (
        logging.FileHandler(args.log_file, encoding="utf-8")
        if args.log_file
        else logging.StreamHandler(sys.stdout)
    )
    handler.setFormatter(
        JsonFormatter()
        if args.log_format == "json"
        else logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    LOGGER.handlers.clear()
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if args.debug else logging.INFO)
    LOGGER.propagate = False


def write_report(report):
    report_path = Path("output/report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(
        report, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote report to %s", report_path)


def clean(value):
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def load_schemas(path):
    schemas = []
    for schema_path in Path(path).rglob("schema.yaml"):
        with open(schema_path, encoding="utf-8") as file:
            schema = yaml.safe_load(file)
        if schema:
            schemas.append(schema)
    return schemas


def load_buckets(target_project):
    return {
        bucket["_id"]: bucket
        for bucket in load_schemas(f"resources/{target_project}/bucket")
        if bucket.get("_id")
    }


def affected_bucket_ids(statement, buckets):
    resource = statement.get("resource", {})
    include = resource.get("include", [])
    exclude = set(resource.get("exclude", []))
    if "*" in include:
        return [bucket_id for bucket_id in buckets if bucket_id not in exclude]
    return [bucket_id for bucket_id in include if bucket_id in buckets and bucket_id not in exclude]


def acl_rule_for_action(action):
    if action in {"bucket:data:stream", "bucket:data:index", "bucket:data:show"}:
        return "read"
    if action in {"bucket:data:update", "bucket:data:delete"}:
        return "write"
    return None


def analyze_bucket_acl(client, bucket):
    prompt = f"""
Evaluate both the read and write bucket ACL rules for row-level security.

For each rule, set row_level_security_status to exactly one of:
- applied: every allowed access path requires a unique request-owner value
  (auth._id, auth.username, or another unique auth field) to equal a target
  document field, including any field defined in the bucket schema and could
  be specific to the user.
- applied_but_in_risk: an owner-to-document comparison exists, but a
  privileged condition could bypass the owner-to-document comparison.
- not_applied: no request-owner-to-document comparison exists, or access can
  be allowed unconditionally, such as with `|| true==true`.

Set includes_sensitive_information to True when the bucket title and/or schema
fields indicate personal or sensitive data, such as Users, Customers for titles, 
and msisdn, email, password, address, identity, for fields. Set it to False
for operational/configuration data, such as Maintenance, Status, or
Configuration for titles and fields like status, version, or in_use etc.

Each reason must identify the specific ACL expression and give a very short
explanation of the decision.

Bucket schema:
{yaml.safe_dump(bucket, sort_keys=False)}
"""
    response = client.responses.parse(
        model=MODEL,
        input=prompt,
        text_format=BucketAclReport,
    )
    return response.output_parsed.model_dump()


def build_attachment_prompt(functions):
    return (
        "Find attached policies to users on the javascript functions and return result in desired format. "
        "First you need to find where policies were attached to users, search code for following patterns: "
        "1. devkit/database <db|database>.collection(\"user\").<updateOne|updateMany|insertOne|insertMany> "
        "and relevant argument should include \"policies:[<policyids>]\" "
        "2. devkit/auth <Auth|auth>.policy.attach(<userid>, <policyid>) "
        "3. pure http call post request to the passport/user/<userid>/policy/<policyid>, with libraries like axios, fetch, etc. "
        "When you identified this kind of policy attachment, follow the references to determine where policies were defined. "
        "They could be \"process.env.<ENVIRONMENT_NAME>\", put name of them to the result if so, "
        "and also they could be hardcoded \"POLICY_ID\", put id of them to the result if so. "
        "I need file names and line numbers from where the policies were attached to users to where they were defined, including references. "
        "For each report, include attachment_files: the JavaScript or TypeScript function file paths where a policy "
        "attachment operation itself was found. Do not include files that only define or reference the policy. "
        f"Here are the functions: {functions}"
    )


def main():
    target_project = "spica-orchestrator"
    file_patterns = [
        f"resources/{target_project}/function/**/*.mjs",
        f"resources/{target_project}/function/**/*.js",
        f"resources/{target_project}/function/**/*.ts",
    ]
    all_files = [file for pattern in file_patterns for file in glob.glob(
        pattern, recursive=True)]
    LOGGER.debug("Discovered %d function files", len(all_files))
    functions = []
    for file in all_files:
        with open(file, encoding="utf-8") as source:
            functions.append({"file": file, "content": source.read()})

    load_dotenv()
    client = OpenAI()
    LOGGER.info("Finding functions that attach policies to users")
    response = client.responses.parse(
        model=MODEL,
        input=build_attachment_prompt(functions),
        text_format=ReportResponse,
    )
    attachment_files = {
        file
        for report in response.output_parsed.reports
        for file in report.attachment_files
    }
    LOGGER.info("Found %d functions that attach policies to users",
                len(attachment_files))

    LOGGER.info("Analyzing policies")
    policies = load_schemas(f"resources/{target_project}/policy")
    relevant_policies = [
        policy for policy in policies
        if any(
            policy.get("_id") == report.policy_id
            or clean(policy.get("name")) == clean(report.policy_name)
            for report in response.output_parsed.reports
        )
        and any(statement.get("module") == "bucket:data" for statement in policy.get("statement", []))
    ]
    LOGGER.debug("Loaded %d policies; %d are relevant",
                 len(policies), len(relevant_policies))
    LOGGER.info("Found %d policies that have access to buckets",
                len(relevant_policies))

    buckets = load_buckets(target_project)
    unique_affected_bucket_ids = []
    for policy in relevant_policies:
        for statement in policy.get("statement", []):
            if statement.get("module") != "bucket:data" or not acl_rule_for_action(statement.get("action")):
                continue
            for bucket_id in affected_bucket_ids(statement, buckets):
                if bucket_id not in unique_affected_bucket_ids:
                    unique_affected_bucket_ids.append(bucket_id)

    LOGGER.info("Analyzing ACLs for %d affected buckets",
                len(unique_affected_bucket_ids))
    bucket_reports = {
        bucket_id: analyze_bucket_acl(client, buckets[bucket_id])
        for bucket_id in unique_affected_bucket_ids
    }

    report = []
    affected_buckets_with_risks = []
    for policy in relevant_policies:
        affected_statements = []
        for statement_index, statement in enumerate(policy.get("statement", [])):
            action = statement.get("action")
            acl_rule = acl_rule_for_action(action)
            if statement.get("module") != "bucket:data" or not acl_rule:
                continue

            affected_buckets = []
            for bucket_id in affected_bucket_ids(statement, buckets):
                bucket_report = bucket_reports[bucket_id]
                access_report = {
                    "row_level_security_status": (
                        bucket_report[acl_rule]["row_level_security_status"]
                    ),
                    "reason": bucket_report[acl_rule]["reason"],
                    "includes_sensitive_information": (
                        bucket_report["includes_sensitive_information"]
                    ),
                }
                if access_report["row_level_security_status"] != "applied" and access_report["includes_sensitive_information"]:
                    affected_buckets.append({
                        "_id_": bucket_id,
                        "report": access_report,
                    })
                    affected_buckets_with_risks.append({
                        "policy_id": policy.get("_id"),
                        "policy_name": policy.get("name"),
                        "statement_index": statement_index,
                        "statement": deepcopy(statement),
                        "bucket_id": bucket_id,
                        "bucket_name": buckets[bucket_id].get("title"),
                        "access": acl_rule,
                        "report": access_report,
                    })

            if affected_buckets:
                affected_statements.append({
                    "statement_index": statement_index,
                    "affected_buckets": affected_buckets,
                })

        if affected_statements:
            report.append({
                "policy_id": policy.get("_id"),
                "affected_statements": affected_statements,
            })

    buckets_with_acl_issues = {finding["bucket_id"]
                               for finding in affected_buckets_with_risks}
    LOGGER.info("Found %d buckets with ACL issues",
                len(buckets_with_acl_issues))
    LOGGER.info("Generating final report")
    write_report(report)
    if LOGGER.isEnabledFor(logging.DEBUG):
        LOGGER.debug("Full policy bucket analysis:\n%s", pformat(report))


if __name__ == "__main__":
    args = parse_args()
    configure_logging(args)
    try:
        main()
    except Exception:
        LOGGER.exception("Analysis failed")
        raise SystemExit(1)
