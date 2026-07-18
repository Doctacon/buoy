Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-build-production-local-namespace-catalog.md, .10x/specs/superseded/production-local-namespace-catalog.md

# Production Local Namespace Catalog Implementation Evidence

## What was observed

- The focused catalog model/persistence/CLI suite passed 32 tests.
- The complete repository suite passed 324 tests, including existing explicit single- and multi-namespace retrieval coverage.
- The fixed stable-JSON passage fixture produced semantic hash `94093fa7c81ea1549f6ef7005110dbc9adc4defa2d8fc4b60043fd231986a85f`; the injected `[1.0, 0.0, ...]` 384-dimensional vector produced hash `ba682adfaa5fe942ba23457dbe6188c5ebd9f2fb0fa009e7a8cab5773452fae8`.
- A bounded cached-model run, forced offline with `HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1`, loaded exact revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` locally and produced one finite 384-dimensional vector with norm `1.00000005` and vector hash `a5820500abac680a92ee4a8ef8faa93bcbd2b53b5e4af465c080e1426aec080f` for the golden passage.
- Focused tests cover strict unknown-field/schema/revision/vector failures, exact model constructor arguments with `local_files_only=True`, missing-cache fail-closed behavior, canonical ordering and hashes, duplicate namespaces, atomic old-byte preservation, lock contention, deterministic source mapping/contradictions, manual merge preservation/idempotent commit, every requested catalog CLI lifecycle operation, vector hiding, JSON/stderr separation, path precedence/legacy warnings, no-credential/no-Turbopuffer sentinels, and explicit retrieval regression.
- `git diff --check` and Python compilation completed without output.
- `pyproject.toml` and `uv.lock` were unchanged; no dependency was added.

## Procedure

```text
uv run python -m unittest tests.test_catalog tests.test_catalog_cli
................................
Ran 32 tests in 0.116s
OK

uv run python -m unittest discover -s tests -p 'test_*.py'
Ran 324 tests in 6.841s
OK

uv run python -m py_compile src/buoy_search/catalog.py src/buoy_search/catalog_cli.py src/buoy_search/cli.py
# no output

git diff --check
# no output

HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 uv run python <bounded catalog passage encode script>
dimensions=384 finite=True norm=1.00000005
vector_hash=a5820500abac680a92ee4a8ef8faa93bcbd2b53b5e4af465c080e1426aec080f
```

## Post-review blocker repair verification

Independent review identified strictness and evidence gaps. The bounded repair added paired persisted lineage enforcement plus an explicitly non-persistable prospective-card helper, exact JSON-integer validation, non-string source-kind rejection, source-kind-aware URI validation, direct file/directory `fsync` assertions, an environment credential-read sentinel, the catalog-specific both-root diagnostic, and corrected explicit retrieval documentation.

```text
uv run python -m unittest tests.test_catalog tests.test_catalog_cli
.....................................
Ran 37 tests in 0.141s
OK

uv run python -m unittest discover -s tests -p 'test_*.py'
Ran 329 tests in 7.055s
OK

uv run python -m py_compile src/buoy_search/catalog.py src/buoy_search/catalog_cli.py src/buoy_search/cli.py
# no output

git diff --check
# no output
```

The focused repair tests directly exercise generated/manual lineage mismatches and prospective persistence rejection; `1.0`/`384.0`/`20.0` corruption; non-string source kinds; whitespace, malformed host/port, opaque scheme, and source-kind URI contradictions; one file plus one directory `fsync` call and best-effort directory failure; and an environment mapping that raises immediately if `TURBOPUFFER_API_KEY` is queried.

## What this supports

This supports the child ticket's local catalog schema, hashing, persistence/locking, pinned local-only vector, generated-semantics, manual-preservation merge/commit, CLI lifecycle, compatibility, and local-only side-effect claims.

No command contacted Turbopuffer, read a Turbopuffer credential, downloaded or substituted a model, mutated remote state, or changed applied state. The only model evidence run used an already cached exact revision with both Hugging Face and Transformers offline modes enabled.

## Limits

- This is implementation evidence, not an independent review and not ticket closure.
- No apply registration, pending reconcile/abandon command, or automatic routing behavior was implemented or exercised; those remain later child tickets.
- The cached-model vector hash is environment/library serialization evidence, not a new golden contract. The specification's injected-vector golden hash remains the stable required fixture.
- Filesystem atomicity and locking are covered by local unit behavior; no power-loss or multi-host filesystem test was performed.
