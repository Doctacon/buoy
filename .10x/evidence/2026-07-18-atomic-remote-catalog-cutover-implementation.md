Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/2026-07-18-atomic-remote-catalog-cutover.md

# Atomic Remote Catalog Cutover Implementation

## What was implemented

The reviewed inert backend is now wired as one public authority transition in code:

- `buoy catalog` reads and mutates exact `buoy-routing-catalog-v1`; local path authority/options are removed;
- `migrate-local` validates and holds the exact source descriptor/inode through approved writes and reports truthful initial/final state, intended/affected IDs, counts, revisions, requests, and available billing;
- approved apply precomputes and persists remote-bound intent before content writes, conditionally registers after local state commit, and retains truthful pending recovery across conflicts, snapshot failures, and cleanup failures;
- reconcile supports ordinary commit, safe rebase, first-apply manual race, and exact two-independent-read operator acceptance without content replay;
- no CLI namespace defaults to authenticated live namespace/card intersection and deterministic routing; explicit repeatable namespaces bypass the remote catalog; `TURBOPUFFER_NAMESPACE` is ignored for retrieval and `--auto-route` is a compatibility no-op;
- preview/live outputs distinguish read-only routing from content retrieval, and provider payloads remain redacted from messages and tracebacks;
- public documentation/help/changelog describe remote authority and permission boundaries.

## Validation

Credential-free local commands on reviewed HEAD `1ff74c8`:

```text
Python 3.11: 392 tests passed
Python 3.13: 392 tests passed
uv build: wheel and sdist passed
git diff --check: passed
```

Focused checkpoints covered 36 catalog CLI/backend tests, 22 pending/recovery tests, 62 routing/CLI tests, and 74 apply/pending/catalog tests. All newly introduced temporary skips were removed. Hard client sentinels and process environments without `TURBOPUFFER_API_KEY`/`TURBOPUFFER_NAMESPACE` prevented real provider calls.

## Side-effect boundary

No implementation or test command created a provider client against live state, wrote/read credentials, mutated Turbopuffer, queried content namespaces, or changed canonical `.buoy/catalog.json`. One earlier incomplete test-harness run attempted namespace listing with inherited dummy credentials and failed at authentication before any query result or write; the harness was replaced with injected fakes and hard sentinels before validation.

## Initial live provider finding

After PR #32's initial hosted checks passed, read-only preflight in the cards' exact `gcp-us-central1` region classified the remote catalog as absent and listed four content namespaces. The first approved migration created exact `buoy-routing-catalog-v1` schema and both intended card rows, then post-write verification failed because Turbopuffer 2.4.0 omits absent nullable row extras instead of returning explicit nulls. A catalog-only strong raw inspection observed exactly the two intended deterministic row IDs, 384-dimensional vectors, and every non-null attribute; no content namespace was queried or mutated.

Commit `e83fe90` normalizes omission of exactly `last_plan_id` and `last_apply_id` to application null while preserving strict rejection of every other missing/extra field. The next controlled retry reached metadata validation and failed before writes because Turbopuffer omits `filterable:false` only from returned vector metadata. Raw catalog metadata confirmed exact `[384]f32` type and cosine ANN. Commits `27b36db` and `48b4021` normalize that omission only for exact attribute `vector` with exact `[384]f32` type; all scalar flags, wrong vector dimensions, wrong ANN, and extra attributes remain strict failures. The next read-only preview reached row integrity and exposed decimal rendering drift: provider values differed by at most `1.47e-8`, while rounding both local and remote values to IEEE-754 f32 produced identical bytes and the exact stored vector hashes. Commit `647e65f` canonicalizes only incoming remote vector values to f32 before strict vector/card hash validation; outgoing and local cards remain unchanged. Forty-seven focused unittests and independent review passed. The freeze remains active and hosted checks must pass before another read-only preview.

## What this supports

This supports a hosted-check-gated verification retry against the exact already-created two-card remote state. It does not authorize local catalog deletion before integration and post-merge verification.
