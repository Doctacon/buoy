Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-source-pin-and-execute-experimental-buoy-baseline.md, .10x/evidence/2026-07-20-experimental-buoy-baseline-approval-a-grant.md, .10x/specs/experimental-buoy-baseline-executor.md

# Experimental Buoy Baseline Approval A Source Pin

## What was observed

Step 1 pins `src/buoy_search/experimental_baseline.py` only to the exact checked-in Approval A grant:

- grant record SHA-256: `46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec`;
- provenance: `{"source_system":"pi","conversation_id":"runtime-id-not-exposed","message_id":"sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74"}`.

The checked-in grant remained exactly 2,627 UTF-8 bytes with the pinned record hash. The checked-in `APPROVAL_A_TEXT` remained exactly 2,206 UTF-8 bytes and `APPROVAL_A_TEXT_SHA256` remained `bafc2500292bc8fcfc4aa806873782d43689330c704620f8981684a3796bfa10`. No executor behavior, operation budget, dependency, lockfile, default, ordinary path, live CLI, or grant-record byte changed.

`tests/test_experimental_baseline.py` now validates the exact checked-in grant and source pins, flips each of the 2,627 grant-record bytes individually and confirms every resulting record fails closed, and confirms independently altered provenance fields and Approval A text still fail even when the test temporarily substitutes the mutated record hash. These tests call only `validate_approval_a_record`; they do not call the live entry point.

## Procedure and validation output

1. Focused CPython 3.11 exactness/mutation suite: 3 tests passed, including all 2,627 one-byte mutations.
2. `uv sync --locked --python 3.11` — passed with 106 locked packages checked.
3. `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python scripts/validate_ranking_contract.py` — passed: 13 datasets, 90 composite identities, 369 judgments, 13 folds; Buoy remained `pending_baseline_approval`.
4. `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q` — passed, 495 tests.
5. `uv sync --locked --python 3.13` — passed with locked `turbopuffer==2.4.0` among 106 packages.
6. The same ranking-contract command under CPython 3.13 — passed with identical hashes and counts; Buoy remained `pending_baseline_approval`.
7. The same full unittest discovery under CPython 3.13 — passed, 495 tests.
8. `uv build --python 3.13 --out-dir /tmp/buoy-source-pin-dist` — passed, producing the wheel and source distribution outside the repository.
9. `git diff --check` — passed.
10. Implementation commit `c7c644a5955bc38e52c536a92401c4bc0a954ef1` was pushed to `work/source-pin-baseline-approval` and opened as PR #73: `https://github.com/Doctacon/buoy-search/pull/73`.
11. GitHub Actions run `29787994002` passed Python 3.11, Python 3.13, and Build distributions for implementation commit `c7c644a5955bc38e52c536a92401c4bc0a954ef1`.

The full suites emitted the two previously recorded temporary plan-cleanup warning lines per interpreter and completed successfully.

## No-live and state boundary

No validation command invoked `execute_experimental_baseline`, read a credential or `TURBOPUFFER_API_KEY`, imported/loaded/downloaded a model, constructed a provider client, contacted a provider, read the retained plan/cache/credential/state inputs, or touched a namespace, card, catalog, pending record, or DuckDB applied state. Tests used only the checked-in immutable Approval A JSON and temporary mutation files. No Step 2 activity occurred.

## What this supports

This supports Step 1 source-pin exactness, local CI-equivalent validation, and passing hosted CI on the exact implementation commit in PR #73. Independent implementation review and separate integration remain required.

## Limits

This record does not establish independent review, integration into `develop`, execution authority from an integrated commit, a live attempt, baseline compatibility, Approval B, or C3 retrieval. Step 1 remains pending review and separate integration; Step 2 remains blocked and unperformed.
