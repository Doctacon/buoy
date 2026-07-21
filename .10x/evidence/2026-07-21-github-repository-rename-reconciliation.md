Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Relates-To: .10x/tickets/done/2026-07-21-reconcile-github-repository-rename.md, .10x/decisions/buoy-product-and-repository-identity.md, .10x/specs/develop-to-main-release-readiness.md, .10x/specs/main-push-automatic-github-release.md

# GitHub Repository Rename Reconciliation

## What was observed

Execution started from exact `develop` commit `0c7f333d45622ff2ffea62e5ac9e0b00a109a4d1` in isolated branch/worktree `work/reconcile-github-repository-rename`. The local `origin` fetch and push URLs were already directly canonical at `git@github.com:Doctacon/buoy.git`; no redirect is required. Read-only `gh repo view Doctacon/buoy` reported exact public repository `Doctacon/buoy`, URL `https://github.com/Doctacon/buoy`, and default branch `main`.

The bounded implementation:

- changes release/readiness current repository authority to exact `Doctacon/buoy`;
- introduces separate `LEGACY_V040_REPOSITORY = "Doctacon/buoy-search"` and uses it only for the exact pinned v0.4.0 no-op provenance plan;
- updates active README/security/project/changelog/release-documentation URLs and current-identity catalog/fake-host test fixtures;
- adds fail-closed tests proving readiness rejects `Doctacon/buoy-search:develop`, future provenance rejects the old repository, and exact legacy v0.4.0 provenance rejects the canonical repository;
- preserves distribution `buoy-search`, import `buoy_search`, CLI `buoy`, and all product behavior.

## Old-identity occurrence classification

A repository-wide `rg` inventory classified old occurrences as follows:

1. **Active current identity — updated:** `scripts/release_automation.py` current authority/error, release tests and fake-host attestation fixture, current catalog fixture, `README.md`, `SECURITY.md`, `pyproject.toml`, all active `CHANGELOG.md` comparison/release links, and `docs/releasing.md` current release authority.
2. **Exact immutable v0.4.0 legacy provenance — preserved explicitly:** `LEGACY_V040_REPOSITORY`, the exact legacy state-machine tests, and the release documentation's legacy exception.
3. **Immutable experiment/source pin — preserved:** `src/buoy_search/experimental_baseline.py` and `tests/test_experimental_baseline.py` retain exact `Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac` identity and URLs.
4. **Historical records/evidence/source artifacts — preserved:** old URLs and repository values under `.10x/evidence`, `.10x/reviews`, terminal tickets, superseded decisions, storage snapshots, and historical active records were not rewritten.

After implementation, non-`.10x` old-identity occurrences are limited to the explicit release legacy pin/docs/tests and the immutable experimental source pin/tests.

## Procedure and validation

- `uv sync --locked --python 3.11`, release validation, ranking-contract validation, C6 validation, and the complete test suite passed: **535 tests**.
- `uv sync --locked --python 3.13`, the same validators, and the complete test suite passed: **535 tests**.
- Focused release/catalog tests passed: **44 tests**.
- Two builds using exact HEAD commit timestamp as `SOURCE_DATE_EPOCH`, plus `PYTHONHASHSEED=0`, `TZ=UTC`, and `LC_ALL=C`, produced byte-identical wheel and sdist files and identical artifact manifests.
- Artifact inspection accepted exact names, metadata, inventory, entry point, and bundled tokenizer. Wheel and sdist metadata both expose only canonical project URLs.
- A fresh isolated wheel install passed `buoy --version` (`0.4.1`), `buoy --help`, `python -m buoy_search --help`, and exact bundled-tokenizer smoke count `9`.
- Deterministic artifact SHA-256 values were:
  - `buoy_search-0.4.1-py3-none-any.whl`: `46b5ce010845141463dd25e05e55a2a431dee8e20dfe1f574fb66a6ecfa231ca`
  - `buoy_search-0.4.1.tar.gz`: `5b680d24082cecedbafed25a95c18b2d3308e16bb88cdae6ee251a7d582ba10e`
- Exact live read-only v0.4 inspection queried the canonical repository API, observed annotated tag `v0.4.0` peeling to `c49dc0582bf3f06a16eafdcca0707d1e64e1c58d`, exact Release/assets/digests, and both provenance subjects under historical `Doctacon/buoy-search`, `release.yml`, `refs/tags/v0.4.0`, and the exact source commit. The resulting plan was exactly `noop` with legacy repository/source-ref identity.

The first direct system-Python live inspection attempt failed before observation because the local framework certificate store could not verify GitHub. Retrying the same read-only script with `SSL_CERT_FILE` set to the locked environment's `certifi` bundle succeeded. No implementation change or hosted mutation was needed.

## Hosted handoff

Implementation and evidence were committed as `310d37f27eeef74806356d8925dc5f9f9035ba58`, pushed only to `work/reconcile-github-repository-rename`, and opened as protected PR [#95](https://github.com/Doctacon/buoy/pull/95) targeting `develop`. Exact-head hosted CI run [29873714541](https://github.com/Doctacon/buoy/actions/runs/29873714541) passed all three protected checks: Python 3.11 job `88779477470`, Python 3.13 job `88779477439`, and Build distributions job `88779832414`.

## What this supports

This supports the claims that current/future release policy and provenance use canonical `Doctacon/buoy`, the sole exact legacy v0.4.0 no-op remains bound to `Doctacon/buoy-search`, cross-use fails closed, current public/package links are canonical, deterministic distributions remain valid, local/hosted identity inspection is read-only, and the implementation passed protected hosted CI.

## Limits

Independent review and final integration are not yet recorded here. This evidence does not authorize or prove any `main`, tag, Release, asset, provenance, PyPI, Turbopuffer, protection, or product mutation. No such mutation occurred during the recorded procedure.
