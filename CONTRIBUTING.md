# Contributing to Buoy

Thanks for helping make source-grounded search safer and easier to use.

## Setup

Buoy requires Python 3.11 or newer and [uv](https://docs.astral.sh/uv/):

```bash
uv sync --locked
uv run buoy --help
```

## Validate a change

Run the complete local checks before opening a pull request:

```bash
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
uv build --out-dir /tmp/buoy-build
```

Keep changes narrow, update tests for behavior changes, and update the focused document that owns any affected user contract. `README.md` stays a short landing page; detailed indexing, retrieval, evaluation, migration, and release material belongs under `docs/`.

## Safety boundaries

- Planning may fetch a public source but must not contact Turbopuffer.
- Never include API keys, tokens, private data, local state, generated plans, or model caches in a commit.
- Do not run approved applies, live retrieval/evals, namespace deletion, releases, or other external mutations as routine validation.
- Preserve existing plan, row-ID, namespace, and DuckDB compatibility unless a reviewed migration explicitly changes them.

## Pull requests

Open ordinary change pull requests against `develop`; maintainers squash-merge them after all required CI checks pass. `main` accepts reviewed release pull requests from `develop`, merged with a merge commit so release ancestry remains coherent. Both long-lived branches are protected from direct pushes.

Explain the user-visible outcome, list validation performed, and call out compatibility or external-side-effect risks.

By contributing, you agree that your contribution is licensed under Apache-2.0.
