def format_function(function):
    return f"""function_id: {function["_id"]}
```
{function["content"]}
```"""


def endpoint_risk_prompt(functions):
    sources = "\n\n".join(format_function(function) for function in functions)
    return f"""
Analyze javascript/typescript functions to find unauthenticated public endpoints
and evaluate their risk, return report in desired format.

1- Check ONLY exported functions, which receive request and response objects.
2- Check whether their implementation starts with any authentication or
   authorization checks. Don't dive into auth implementations, just determine
   any sign of auth checks.
3- Filter if they don't have auth implementation explained in step 2.
4- Evaluate their risk by the following criteria:
   - high: Code performs CRUD on any database, bucket, storage etc.
   - medium: Code performs some calculations, tries to validate some logic,
     spica behavior, or interacts with non-critical resources like sending an
     http request to another testing purpose spica, or google.com.
     Or code read somethings but never return them.
   - low: Code just returns some dummy data like "OK", json array, nothing that
     harms spica or other critical resources.
5- Write a very short explanation of the risk evaluation to reason.

Return one entry per function with it's id, methods object array including
method name, risk level, and reason.

Functions:
{sources}
"""
