from spica_advisor.investigations.unauthenticated_endpoints.prompts import batch_by_size
from spica_advisor.investigations.unauthenticated_endpoints.steps import is_public_endpoint


def public_handler_names(schema):
    return sorted(name for name, trigger in (schema.get("triggers") or {}).items() if is_public_endpoint(trigger))


DEFAULT_EXPORT = "default"


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
    functions = [
        {"_id": function["_id"], "content": function["content"], "handlers": public_handler_names(function["schema"])}
        for function in context.public_functions
    ]
    return [
        "Functions:\n" + "\n\n".join(format_function_with_handlers(function) for function in batch)
        for batch in batch_by_size(functions)
    ]
