Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/done/2026-07-18-build-remote-routing-backend.md, .10x/specs/namespace-routing-card-contract.md, .10x/specs/remote-turbopuffer-routing-catalog.md, .10x/specs/approved-apply-remote-catalog-registration.md

# Remote Routing Backend Implementation

## What was implemented

Added inert `src/buoy_search/remote_catalog.py` without importing it into CLI/apply/retrieve/local catalog paths. It provides:

- exact independent 29-attribute remote schema plus implicit string ID normalization and application nullability checks;
- deterministic 64-byte hash IDs and provider-neutral complete card row round-trip;
- injected SDK protocols and an explicit-value client adapter that never reads environment;
- two complete auto-paginated namespace-list passes, metadata validation, two strong ordered card passes at 100 rows, advancing-ID protection, snapshot stability, billing redaction, intersection classification, and exact count precedence;
- conditional create/update/delete with exact affected IDs and two strong verification reads;
- absent/empty/partial/exact/conflict migration classification and partial-race detection;
- safe manual/enabled rebase with unchanged-projection verification or injected local recomputation, first-apply manual-card race validation, and two-read exact-revision accept-remote validation with no clock ordering;
- 10,000-page bounds, repeated cursor/signature and duplicate detection with SDK-shaped pages;
- provider failures reduced to phase plus safe class/status only, with suppressed exception context so neither messages nor formatted tracebacks expose raw token/vector/body payloads;
- generic zero-eligible management snapshots plus actionable routing-facing `require_eligible` failure.

`tests/test_remote_catalog.py` adds 23 injected-fake tests. Existing active card parsing/vector/hash/generated semantics remain reused and covered by the pre-existing catalog suite.

## Validation

Commands from the task worktree:

```text
uv run --python 3.13 python -m unittest tests.test_remote_catalog -q
Ran 23 tests ... OK

uv run python -m unittest tests.test_catalog tests.test_catalog_pending tests.test_automatic_routing -q
Ran 59 tests ... OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 382 tests ... OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 382 tests ... OK

uv run --python 3.13 python -m compileall -q src tests
passed

git diff --check
passed

uv build --out-dir /tmp/buoy-remote-backend-dist-final
built wheel and sdist; wheel contains buoy_search/remote_catalog.py
```

Before review repair, both supported-Python full matrices passed 382 tests and emitted only the existing temporary plan-cleanup warning. After the narrowly scoped review repairs, the 23-test remote backend suite and 59-test catalog/pending/routing compatibility suite passed, followed by compile, build, reference, and diff checks. The final traceback-only repair reran the 23 focused tests plus compile/diff. Per handoff, the unchanged broader matrices were not rerun.

## Scope and side-effect evidence

Before commit, the tracked behavior diff is limited to the new inert module, new focused tests, ticket, and this evidence. `src/buoy_search/cli.py`, `apply.py`, `catalog.py`, `catalog_cli.py`, `routing.py`, docs, and README have zero diff.

No test constructs a real client except a patched fake module; no API key is read, no network/live Turbopuffer call occurs, and no `.buoy` path is accessed by the new module. Canonical `/Users/crlough/Code/personal/turbo-search/.buoy/catalog.json` remains 26,063 bytes, mode 0600, SHA-256 `aafe3e6752671badef9da1aa0150903056bb856666289c271e0a67cef7a5ab1a`; lock remains absent.

## What this supports

This supports every backend ticket acceptance criterion except hosted CI and final independent re-review, which remain closure gates after commit/PR. It does not support public cutover or live provider behavior; those remain owned by the blocked atomic-cutover child.

## Limits

Turbopuffer server normalization and conditional-write behavior are tested against official SDK/API contracts with exact fakes, not live calls. SDK-internal four-retry/timeout behavior is relied upon rather than reimplemented; Buoy adds no enclosing retry. The later cutover must validate hosted behavior fail-closed before migration.
