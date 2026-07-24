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

Keep changes narrow, update tests for behavior changes, and update the focused document that owns any affected user contract. `README.md` stays a short landing page; detailed indexing, retrieval, evaluation, migration, release, and Command Center material belongs under `docs/`.

For Command Center work, use the pinned frontend lockfile and verify that generated assets stay synchronized:

```bash
cd web
npm ci
npm test -- --run
npm run build
cd ..
git diff --exit-code -- src/buoy_search/command_center_static
uv sync --locked --extra ui
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests/test_planning_service.py tests/test_command_center_jobs.py tests/test_command_center_local.py tests/test_command_center_remote.py tests/test_command_center_api.py tests/test_command_center_cli.py -q
uv sync --locked
```

Commit the hashed output under `src/buoy_search/command_center_static/` with its matching `web/` source changes. Do not commit `web/node_modules/` or hand-edit generated assets. Node is a frontend development dependency only; the commands above test the optional Python UI runtime and then restore the locked core environment.

## Safety boundaries

- Planning may fetch a public source but must not contact Turbopuffer.
- Never include API keys, tokens, private data, local state, generated plans, or model caches in a commit.
- Do not run approved applies, live retrieval/evals, namespace deletion, releases, or other external mutations as routine validation.
- Preserve existing plan, row-ID, namespace, and DuckDB compatibility unless a reviewed migration explicitly changes them.

## Pull requests

Open ordinary change pull requests against `develop`; maintainers squash-merge them after all required CI checks pass. `main` accepts reviewed release pull requests from `develop`, merged with a merge commit so release ancestry remains coherent. Both long-lived branches are protected from direct pushes.

Explain the user-visible outcome, list validation performed, and call out compatibility or external-side-effect risks.

By contributing, you agree that your contribution is licensed under Apache-2.0.
