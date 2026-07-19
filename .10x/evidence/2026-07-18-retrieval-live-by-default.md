Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md, .10x/specs/default-remote-namespace-routing.md, .10x/specs/apply-to-retrieval-handoff.md

# Retrieval Live-by-Default Validation

## What was observed

Retrieval now executes live when invoked plainly in automatic or explicit namespace mode. `--live` produces byte-identical output to plain live invocation in fake-backed automatic and explicit tests. `--dry-run` and `--plan` produce preview behavior. Generated apply handoff commands now omit `--live` for live retrieval and append `--dry-run` for preview while retaining POSIX shell token safety.

Focused fake-backed tests recorded the established automatic live trace as two stable namespace-list calls, one catalog namespace selection, one metadata request, two strong card-query pages, and one ordered content-retriever call. Explicit preview tests rejected any credential read, remote client/catalog call, or routing-model load. Automatic preview tests made the catalog reads but rejected content retriever construction. Selected namespace failure tests emitted no partial stdout.

No catalog or apply write path was changed. The only apply implementation change is generated retrieval command text in `build_retrieval_commands`; apply approval, state, embedding, content write, catalog registration, and cleanup behavior are untouched.

## Procedure

From branch `work/make-retrieval-live-by-default`:

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_automatic_routing tests.test_multi_namespace_retrieval tests.test_cli tests.test_apply_cli tests.test_cutover_isolation -q
# Ran 107 tests in 5.315s — OK (Python 3.13.0)

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_automatic_routing tests.test_multi_namespace_retrieval tests.test_cli tests.test_apply_cli tests.test_cutover_isolation -q
# Ran 107 tests in 19.881s — OK (Python 3.11.5)

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 405 tests in 12.713s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 405 tests in 25.591s — OK

rm -rf dist && uv build --out-dir dist
# Successfully built dist/buoy_search-0.3.0.tar.gz
# Successfully built dist/buoy_search-0.3.0-py3-none-any.whl

uv run python scripts/release_checks.py assets --dist dist
# exit 0

git fetch origin develop
git merge-base --is-ancestor origin/develop HEAD
# exit 0; origin/develop e27de0d is already incorporated by pre-change HEAD f1adf33

gh pr checks 34 --watch --interval 10
# Python 3.11 — pass (40s), job 88157565805
# Python 3.13 — pass (56s), job 88157565799
# Build distributions — pass (12s), job 88157629794
```

The unittest runs emitted one existing non-fatal warning from a cleanup-path test about a temporary plan artifact directory; every run completed `OK`.

## What this supports or challenges

This supports the ticket's focused/full Python 3.11/3.13, parser/help, exact routing boundary, preview safety, all-or-nothing, generated command tokenization, documentation, distribution-build, hosted-CI, and no-write acceptance claims. Hosted run `29673894066` for pull request `#34` passed both versioned test jobs and the dependent distribution build. Independent review remains a separate required gate.

## PR #34 automatic-preview truthfulness correction

Independent review found that routed automatic preview inherited explicit-preview top-level safety fields from `MultiNamespaceRetrievalPlan.to_dict()`, producing `credentials_required=false`, `turbopuffer_api_calls=false`, and `api_calls_occurred=false` even though the nested routing object truthfully reported credentialed read-only catalog calls. `RoutedRetrievalPlan.to_dict()` now replaces those three top-level fields with command-level routing facts while preserving the explicit preview plan's credential/API-free fields and both preview modes' `content_retrieval_occurred=false` value. No field was added or removed, and live serialization and execution paths were not changed.

Focused regression assertions cover the three top-level automatic-preview fields, the nested credential/read-only call fields, both top-level and nested no-content-retrieval fields, and the explicit-preview credential/API-free contract.

```text
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_automatic_routing tests.test_multi_namespace_retrieval -q
# Ran 26 tests in 0.632s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_automatic_routing tests.test_multi_namespace_retrieval -q
# Ran 26 tests in 0.389s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 405 tests in 25.147s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 405 tests in 27.249s — OK

git diff --check
# exit 0
```

The full unittest runs emitted the same existing non-fatal cleanup-path warning about a temporary plan artifact directory and completed `OK`.

## Limits

All remote interactions were deterministic fakes; no real Turbopuffer account was contacted. This evidence does not constitute independent review and does not close the ticket.
