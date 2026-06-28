Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md
Depends-On: .loom/specs/turbopuffer-jellyfish-rag.md, .loom/research/2026-06-20-turbopuffer-markdown-rag-research.md, .loom/decisions/turbopuffer-jellyfish-rag-baseline.md

# Create Python/uv prototype scaffold

## Scope

Create the minimal local Python project structure needed for indexing and retrieval scripts.

In scope:

- `pyproject.toml` managed by `uv`.
- Source package, recommended `src/turbo_search/`.
- CLI entry points or module commands for indexing and retrieval.
- Dependencies needed for the baseline:
  - `turbopuffer`
  - `sentence-transformers`
  - YAML/frontmatter parsing library or a small local parser
  - tokenization/chunking helpers if chosen
  - test tooling if needed
- `.gitignore` entries for caches, local env files, model/cache artifacts, and generated output.
- README or docs section with non-secret setup instructions.

Out of scope:

- Proton Pass credential retrieval.
- Turbopuffer API calls.
- Full indexing/retrieval behavior beyond stubs or dry-run wiring.

## Acceptance criteria

- `uv sync` or the documented equivalent can install dependencies.
- A basic CLI/module invocation exists and prints help without requiring credentials.
- Project files do not contain secrets.
- Scaffolding is small and easy to inspect.

## Progress and notes

- 2026-06-20: Ticket created only. No files changed outside `.loom/`.
- 2026-06-20: User confirmed Python/uv + local BGE as the implementation baseline.
- 2026-06-20: Activated for execution under `/loom-driver` after config ticket completed.
- 2026-06-20: Added minimal `uv` Python scaffold with `src/turbo_search/` package, dry-run CLI commands, non-secret README setup docs, `.gitignore`, and stdlib CLI tests.
- 2026-06-20: Validated safe module help, dry-run index/retrieve commands, unittest suite, and syntax compilation without credential access or turbopuffer API calls. Evidence: `.loom/evidence/2026-06-20-python-prototype-scaffold-validation.md`.

## Blockers

- None.
