from pathlib import Path

import yaml


RESOURCES_ROOT = Path("resources")
FUNCTION_EXTENSIONS = ("mjs", "js", "ts")


def read_schema(schema_path):
    with open(schema_path, encoding="utf-8") as file:
        return yaml.safe_load(file)


def load_schemas(path):
    schemas = []
    for schema_path in Path(path).rglob("schema.yaml"):
        schema = read_schema(schema_path)
        if schema:
            schemas.append(schema)
    return schemas


def read_function_source(folder):
    return "\n".join(
        path.read_text(encoding="utf-8")
        for extension in FUNCTION_EXTENSIONS
        for path in sorted(folder.glob(f"*.{extension}"))
    )


def load_functions(project):
    definitions = []
    for schema_path in (RESOURCES_ROOT / project / "function").rglob("schema.yaml"):
        schema = read_schema(schema_path)
        if schema:
            definitions.append({
                "_id": schema.get("_id"),
                "name": schema.get("name"),
                "schema": schema,
                "content": read_function_source(schema_path.parent),
            })
    return definitions


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
