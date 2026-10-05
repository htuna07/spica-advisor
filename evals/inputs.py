import re

from spica_advisor.investigations.unauthenticated_endpoints.prompts import batch_by_size
from spica_advisor.investigations.unauthenticated_endpoints.steps import is_public_endpoint


DEFAULT_EXPORT = "default"
DECLARED_EXPORT = re.compile(r"\bexport\s+(?:async\s+)?(?:function\s*\*?|const|let|var|class)\s+(\w+)")
EXPORT_LIST = re.compile(r"\bexport\s*\{([^}]*)\}")
DEFAULT_EXPORT_DECLARATION = re.compile(r"\bexport\s+default\b")


def public_handler_names(schema):
    return sorted(name for name, trigger in (schema.get("triggers") or {}).items() if is_public_endpoint(trigger))


def exported_names(source):
    names = set(DECLARED_EXPORT.findall(source))
    for exports in EXPORT_LIST.findall(source):
        # "handler as alias" exports the alias, which is the name Spica looks up.
        names.update(item.split()[-1] for item in exports.split(",") if item.strip())
    if DEFAULT_EXPORT_DECLARATION.search(source):
        names.add(DEFAULT_EXPORT)
    return names


def served_handler_names(function):
    exported = exported_names(function["content"])
    return [name for name in public_handler_names(function["schema"]) if name in exported]


def handler_label(name):
    # Spica serves a function's default export under the trigger name "default".
    return f"{name} (the default export)" if name == DEFAULT_EXPORT else name


def format_function_with_handlers(function):
    return f"""function_id: {function["_id"]}
http_handlers: {", ".join(handler_label(name) for name in function["handlers"])}
```
{function["content"]}
```"""


def endpoint_prompts_with_handler_names(context):
    functions = []
    for function in context.public_functions:
        handlers = served_handler_names(function)
        # A trigger whose handler is not exported runs no code, so a function left without handlers has no endpoint.
        if handlers:
            functions.append({"_id": function["_id"], "content": function["content"], "handlers": handlers})
    return [
        "Functions:\n" + "\n\n".join(format_function_with_handlers(function) for function in batch)
        for batch in batch_by_size(functions)
    ]
