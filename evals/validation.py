import re

import yaml
from pydantic import ValidationError

from evals.cases import LABEL_FILES
from spica_advisor.investigations.unauthenticated_endpoints.handlers import has_public_endpoint, public_handler_names
from spica_advisor.resources import load_buckets, load_env_vars, load_functions


PLACEHOLDER_MARKER = "REPLACE_ME"
SCANNED_SUFFIXES = {".yaml", ".mjs", ".js", ".ts"}
IGNORED_DIRS = {"node_modules"}


def placeholder_problems(case):
    return [
        f"placeholder: {path}"
        for root in (case.project_dir, case.expected_dir)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and path.suffix in SCANNED_SUFFIXES
        and not IGNORED_DIRS.intersection(path.parts)
        and PLACEHOLDER_MARKER in path.read_text(encoding="utf-8", errors="ignore")
    ]


def missing_label_files(case):
    return [
        f"missing label file: {case.label_path(field)}"
        for field in LABEL_FILES
        if not case.label_path(field).exists()
    ]


def label_validation_problems(error: ValidationError):
    return [
        f"{LABEL_FILES[detail['loc'][0]]}: {'.'.join(map(str, detail['loc'][1:])) or '<root>'}: {detail['msg']}"
        for detail in error.errors()
    ]


def key_problems(field, kind, labeled, required, allowed):
    file = LABEL_FILES[field]
    return [
        *(f"{file}: missing label for {kind} {key}" for key in sorted(required - labeled)),
        *(f"{file}: unexpected {kind} {key}" for key in sorted(labeled - allowed)),
    ]


def check_sensitive_env_vars(labels, env_vars):
    names = [env_var["name"] for env_var in env_vars]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    return [
        *(f"env var name is not unique: {name}" for name in duplicates),
        *key_problems("sensitive_env_vars", "env var", set(labels.sensitive_env_vars), set(names), set(names)),
    ]


def appears_in(name, source):
    return re.search(rf"\b{re.escape(name)}\b", source) is not None


def check_unauthenticated_endpoints(labels, functions):
    public_functions = {function["_id"]: function for function in functions if has_public_endpoint(function["schema"])}
    labeled = labels.unauthenticated_endpoints
    file = LABEL_FILES["unauthenticated_endpoints"]
    problems = key_problems(
        "unauthenticated_endpoints", "public function", set(labeled), set(public_functions), set(public_functions),
    )
    for function_id, methods in labeled.items():
        function = public_functions.get(function_id)
        if function is None:
            continue
        handlers = public_handler_names(function["schema"])
        for method in sorted(methods):
            if method not in handlers:
                problems.append(f"{file}: {function_id}.{method} is not a public http trigger "
                                f"(public triggers: {', '.join(handlers)})")
            elif not appears_in(method, function["content"]):
                problems.append(f"{file}: {function_id}.{method} not found in function source")
    return problems


def check_policy_attachments(labels, functions):
    function_ids = {function["_id"] for function in functions}
    file = LABEL_FILES["policy_attachments"]
    return [
        f"{file}: [{index}] unknown function {attachment.function_id}"
        for index, attachment in enumerate(labels.policy_attachments)
        if attachment.function_id not in function_ids
    ]


def check_bucket_acl(labels, buckets):
    return key_problems("bucket_acl", "bucket", set(labels.bucket_acl), set(), set(buckets))


def check_case(case):
    if not case.project_dir.is_dir():
        return [f"missing resources: {case.project_dir}"]
    missing_files = missing_label_files(case)
    problems = [*missing_files, *placeholder_problems(case)]
    if missing_files:
        return problems
    try:
        labels = case.load_labels()
        functions = load_functions(case.project_dir)
        buckets = load_buckets(case.project_dir)
        env_vars = load_env_vars(case.project_dir)
    except ValidationError as error:
        return problems + label_validation_problems(error)
    except (OSError, yaml.YAMLError) as error:
        return problems + [f"could not read case: {error}"]
    return [
        *problems,
        *check_sensitive_env_vars(labels, env_vars),
        *check_unauthenticated_endpoints(labels, functions),
        *check_policy_attachments(labels, functions),
        *check_bucket_acl(labels, buckets),
    ]
