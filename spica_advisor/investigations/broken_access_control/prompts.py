import yaml


ATTACHMENT_INSTRUCTIONS = (
    "Find attached policies to users on the given javascript functions and return result in desired format. "
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
    "attachment operation itself was found. Do not include files that only define or reference the policy."
)

BUCKET_ACL_INSTRUCTIONS = """
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
"""


def attachment_input(functions):
    return f"Here are the functions: {functions}"


def bucket_acl_input(bucket):
    return f"Bucket schema:\n{yaml.safe_dump(bucket, sort_keys=False)}"
