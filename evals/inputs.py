from spica_advisor.investigations.unauthenticated_endpoints.prompts import batch_by_size


def format_source_only(function):
    return f"""function_id: {function["_id"]}
```
{function["content"]}
```"""


def endpoint_prompts_without_handler_names(context):
    # Rebuilds the input the endpoint agent had before it was given handler names, for the legacy variant.
    functions = [{"_id": function["_id"], "content": function["content"]} for function in context.public_functions]
    return [
        "Functions:\n" + "\n\n".join(format_source_only(function) for function in batch)
        for batch in batch_by_size(functions, format_source_only)
    ]
