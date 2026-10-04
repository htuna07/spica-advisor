# Spica Advisor

Spica Advisor reviews Spica resources like functions, buckets, secrets, policies,
and finds potential security issues, improvements, and optimizations. 
It then provides practical suggestions for addressing them.

## GitHub Action

Add a workflow to the repository that holds your Spica resources:

```yaml
name: Spica Advisor

on:
  schedule:
    - cron: "0 6 * * 1"
  workflow_dispatch:

permissions:
  contents: read
  issues: write

jobs:
  advise:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: htuna07/spica-advisor@main
        with:
          model: claude-sonnet-5-5
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Each run writes the report to the job summary and keeps it in one issue labeled
`spica-advisor`. The issue is created when there are findings, updated on later
runs, and closed when a complete run finds nothing. Set `issue: false` to skip it.

| Input | Default | Description |
| --- | --- | --- |
| `model` | `gpt-6-luna` | `gpt-6-luna`, `gpt-6.1-sol`, `claude-haiku-4-5` or `claude-sonnet-5-5` |
| `project-dir` | `.` | Directory holding the Spica resources |
| `output-dir` | `output` | Directory for the JSON and Markdown reports |
| `investigations` | all | Comma-separated subset to run |
| `issue` | `true` | Keep the report in a single issue |
| `openai-api-key` | | Required for OpenAI models |
| `anthropic-api-key` | | Required for Claude models |
| `github-token` | `github.token` | Token used to manage the issue |
