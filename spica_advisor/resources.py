import glob
from pathlib import Path

import yaml


RESOURCES_ROOT = Path("resources")
FUNCTION_EXTENSIONS = ("mjs", "js", "ts")


def load_schemas(path):
    schemas = []
    for schema_path in Path(path).rglob("schema.yaml"):
        with open(schema_path, encoding="utf-8") as file:
            schema = yaml.safe_load(file)
        if schema:
            schemas.append(schema)
    return schemas


def load_functions(project):
    files = [
        file
        for extension in FUNCTION_EXTENSIONS
        for file in glob.glob(f"{RESOURCES_ROOT}/{project}/function/**/*.{extension}", recursive=True)
    ]
    functions = []
    for file in files:
        with open(file, encoding="utf-8") as source:
            functions.append({"file": file, "content": source.read()})
    return functions


def load_policies(project):
    return load_schemas(RESOURCES_ROOT / project / "policy")


def load_env_vars(project):
    return [
        {"_id": env_var.get("_id"), "name": env_var.get("key")}
        for env_var in load_schemas(RESOURCES_ROOT / project / "env-var")
    ]


def load_buckets(project):
    return {
        bucket["_id"]: bucket
        for bucket in load_schemas(RESOURCES_ROOT / project / "bucket")
        if bucket.get("_id")
    }
