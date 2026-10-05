import re

from agents import RunContextWrapper, function_tool


CONTEXT_LINES = 3
MAX_MATCH_CHARS = 500
TRUNCATION_MARKER = "... [truncated, narrow your pattern]"


def truncate(snippet):
    if len(snippet) <= MAX_MATCH_CHARS:
        return snippet
    return snippet[:MAX_MATCH_CHARS] + TRUNCATION_MARKER


def line_ranges(regex, content, line_count):
    for match in regex.finditer(content):
        first = content.count("\n", 0, match.start())
        last = content.count("\n", 0, match.end())
        yield max(0, first - CONTEXT_LINES), min(line_count, last + CONTEXT_LINES + 1)


def merge_ranges(ranges):
    merged = []
    for start, end in sorted(ranges):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def matching_code(pattern, content):
    regex = re.compile(pattern, re.MULTILINE)
    lines = content.split("\n")
    return [
        truncate("\n".join(lines[start:end]))
        for start, end in merge_ranges(line_ranges(regex, content, len(lines)))
    ]


def find_function(functions, function_id_or_name):
    for function in functions:
        if function_id_or_name in (function["_id"], function["name"]):
            return function
    raise ValueError(f"Function not found: {function_id_or_name}")


def report_error(ctx: RunContextWrapper, error: Exception) -> str:
    return f"Error: {error}"


@function_tool(failure_error_function=report_error)
def search_all_code(ctx: RunContextWrapper[list[dict]], pattern: str) -> list[dict]:
    """Search all functions with a regex and return the matching code lines per function.

    Args:
        pattern: Python regular expression, matched in multiline mode.
    """
    return [
        {"function_id": function["_id"], "function_name": function["name"], "matches": matches}
        for function in ctx.context
        if (matches := matching_code(pattern, function["content"]))
    ]


@function_tool(failure_error_function=report_error)
def search_function_code(ctx: RunContextWrapper[list[dict]], function: str, pattern: str) -> list[str]:
    """Search a single function with a regex and return the matching code lines.

    Args:
        function: Function id or name.
        pattern: Python regular expression, matched in multiline mode.
    """
    return matching_code(pattern, find_function(ctx.context, function)["content"])
