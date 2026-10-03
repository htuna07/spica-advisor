# Repository Instructions

## Secrets and sensitive configuration

- Never read `.env` unless the user explicitly authorizes reading it in the current request.

## Git commits

- Every Git commit created in this repository must use the Conventional Commits format: `type(scope): imperative summary`.
- Valid types are `build`, `chore`, `ci`, `docs`, `feat`, `fix`, `perf`, `refactor`, `revert`, `style`, and `test`.
- Before committing, choose the type that describes the change and write a concise, lowercase imperative summary without a trailing period. Do not create a commit with a nonconforming message.
- For the detailed commit workflow, follow [the semantic-commits skill](.agents/skills/semantic-commits/SKILL.md).

## Code Style

- Code must be self-explanatory.
- Follow single responsibility, KISS, DRY, separation of concerns, modularity, and readability principles.

## Comment Lines
- Do NOT add comment lines to the code unless absolutely necessary for understanding.
- Even if it's necessary, keep it short and clear, and explain WHY, not WHAT.