Status: recorded
Created: 2026-07-29
Updated: 2026-07-29
Relates-To: .10x/tickets/done/2026-07-29-command-center-bounded-review-hardening-plan.md, .10x/tickets/done/2026-07-29-validate-command-center-bounded-review-hardening.md, .10x/specs/command-center-artifact-error-diagnostics.md, .10x/specs/command-center-focused-review-request-guard.md, .10x/specs/command-center-unknown-source-filtering.md

# Command Center Bounded Review Hardening Validation

## Handoff and scope

Validation ran on `work/command-center-bounded-review-hardening` from hosted-main base `f2c97ece4dcdc8218542a5b10c0d408e591c8ad3`. Independent review and record closure passed before the final bounded commit. The exact commit hash is reported in the execution handoff because a commit cannot contain its own hash. The diff bounds ordinary artifact-error transport, adds read-only paginated diagnostics, serializes focused changed/stale requests within one Plan screen, and classifies source-less namespace summaries as `unknown` for filtering. It does not change compact-delta artifacts, verification, schemas, authority, provider/source operations, or mutations.

## Host and contracts

- Host: `macOS-26.5.1-arm64-arm-64bit-Mach-O`, arm64, 10 logical CPUs.
- Runtime: Python 3.13.0; DuckDB 1.5.4; FastAPI 0.139.2; Starlette 1.3.1; httpx 0.28.1; Node v24.6.0; npm 11.5.1.
- Artifact-error sample: deterministic first 20 errors in existing stable order on Dashboard, Plans, and Namespaces.
- Diagnostics: default offset 0, page size 50, maximum limit 100, query maximum 256 characters, filter-before-pagination over code/sanitized message/safe artifact ID.
- Plan guard: one accepted focused request per Plan screen at a time; no queue, replay, cancellation contract, cache, backend lock, or cross-tab coordination.

## Synthetic 10,000-error measurement

A disposable in-memory `SafeError` snapshot was injected through the real service/API; no malformed tree was written. Exact UTF-8 response-body bytes exclude headers and framing.

| Route | Total errors | Returned errors | Approximate bytes | Truncated |
|---|---:|---:|---:|---|
| Dashboard | 10,000 | 20 | 1,981 | true |
| Plans | 10,000 | 20 | 1,759 | true |
| Namespaces | 10,000 | 20 | 1,759 | true |
| Artifact diagnostics default | 10,000 | 50 | 4,199 | n/a |
| Artifact diagnostics `offset=5&limit=7&q=NEEDLE` | 100 filtered | 7 | 639 | n/a |

All responses were HTTP 200. The shared snapshot performed one plan scan, one state scan, and zero delta verifications. Focused tests additionally reject offset -1, limit 101, and a 257-character query with structured validation responses; prove stable ordering and matching by code/message/safe ID; directly prove one cached plan scan, one cached state scan, and zero delta verification; and separately prove subprocess import isolation for remote/provider/model/source-adapter modules.

React Testing Library used a 10,000-error synthetic response: ordinary screens rendered exactly 20 error list items; `/artifact-errors` rendered one 50-item page (51 table rows including the header). Next requested offset 100 only, Previous requested offset 50 only, and changing `q` requested offset 0. A deferred old response could not replace the newer query result. No show-all or mutation control exists.

## Focused request characterization

The deterministic same-render characterization invokes changed chunks twice and stale rows once before the first promise settles. Before the guard, all three invocations could pass (2 chunk + 1 stale focused request). After the guard, exactly one chunk request and zero stale requests are accepted (1 total); ignored invocations are not replayed. While either section is active, all four pagination controls and both focused Retry controls are disabled. Existing detail and both windows remain visible; only the active section shows its loading label. Success/failure clears the guard, failure permits exactly one retry, and a later request in the other section is accepted once.

Route-change coverage starts one old-plan focused request, changes plan ID, accepts exactly one new-plan focused request while the old server promise remains unfinished, and proves the old result cannot replace new-plan content. It does not claim server cancellation. Initial combined review remains one API request. The backend benchmark confirms one verifier call for each actual initial/chunk/stale payload request, always `materialize=False` on an `AnyIO worker thread`.

## Unknown-source filtering

A disposable attributable malformed applied-state database produces namespace `broken-namespace` with `local_status=error` and `source=None`. Service/API regressions observe:

- `source_kind=unknown`: total 1, returns `broken-namespace`;
- `source_kind=unknown&local_status=error`: total 1, same source-less error row;
- known filters exclude that row; in the mixed API fixture totals are website 1 (the separate valid plan), GitHub 0, document 0, database 0.

The URL-backed frontend test requests `source_kind=unknown`, preserves it with `local_status=error`, and renders `Unknown source` without synthetic provenance.

## Large selected-delta benchmark

The existing disposable benchmark used 1,000 plans/namespaces plus one selected delta with 100 changed and 100,000 stale rows. Plans returned 50 records in 35,599 bytes; Namespaces returned 50 in 28,849 bytes. Selected review results:

| Transition | Browser requests | Verifier calls | Materialized rows | Verifier / wall |
|---|---:|---:|---:|---:|
| Initial combined | 1 | 1 | 10 changed + 10 stale | 2,669.599 / 2,672.290 ms |
| Changed page | 1 | 1 | 10 changed | 2,669.102 / 3,034.680 ms |
| Stale page | 1 | 1 | 10 stale | 2,709.848 / 3,077.343 ms |

Peak RSS was 275,791,872 bytes. These observations are host-specific and retain filesystem caches; complete verification remains intentionally linear and several seconds at this size.

## Validation commands and exact results

1. `git diff --check` — passed before, after static build, and before evidence recording.
2. `uv sync --locked`; `uv lock --check` — passed in the core environment; resolved 157 packages and removed FastAPI/Starlette/Uvicorn.
3. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — passed: 13 datasets/folds, 90 composite identities, 369 judgments, bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
4. `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — passed at SHA-256 `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`; tokenizer readiness remained false.
5. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q` — passed 808 tests in 90.054 seconds with 39 expected core-environment skips.
6. `uv sync --locked --extra ui` — passed; installed locked FastAPI 0.139.2, Starlette 1.3.1, and Uvicorn 0.51.0.
7. `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_local tests.test_command_center_api tests.test_command_center_inventory_benchmark tests.test_command_center_bounded_review_benchmark tests.test_release_automation -q` — passed 106 tests in 11.539 seconds.
8. `cd web && npm ci` — passed: 214 packages installed, 215 audited. The existing documented React Router advisory remains two high audit findings; dependencies were unchanged.
9. `cd web && npm test -- --run` — the first run had one transient unrelated old-EventSource test failure (`oldSource` undefined); an immediate unchanged complete rerun passed all 50 tests in 2.397 seconds. The focused rapid-request test separately passed 1 test with 49 skipped.
10. `cd web && npm run build` — passed TypeScript and Vite 7.3.6, 42 modules. Output: 632-byte HTML, 288,781-byte JS, 11,191-byte CSS.
11. Static reference/orphan/hash check — passed with `/buoy.svg`, `/assets/index-IKQ18Gxc.js`, and `/assets/index-0ugYq-Qa.css`; exactly one JS and CSS asset and no orphan. SHA-256: HTML `bfac21e6742d53ba39c88be23f259faad78b9268f22a17074d84d94cc2a3fade`; JS `5da07fab61e70aff75251e9e88b24360d4b20069bea8064f80d58871ec5d4c8a`; CSS `8aa90744893ad97ca4fcfd03fc1fec818967a36e6bff22c8e894663959f39be3`; SVG `f791c77f25e202a0556d2688ec9180e7d78c983f220f84b097c1fdc8894edcef`.
12. The disposable diagnostics measurement and `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/benchmark_command_center_bounded_review.py` — passed with the measurements above. The benchmark report also emitted fixed zero-valued side-effect attestation fields; those fields are declarations, not instrumented operation counters.
13. `uv build --out-dir dist` — passed, producing `buoy_search-0.4.1.dev121+gf2c97ece4.d20260729` wheel and sdist.
14. Standard-library archive inventory — passed: wheel 69 files with synchronized HTML and exactly one hashed JS/CSS; sdist 161 files containing intended docs, both benchmark scripts, Python tests, frontend source/test/lockfile. Neither archive contains `node_modules`, `.10x`, database/DuckDB, log, profile, or `.env` content.
15. Isolated installed-wheel smoke — passed from a removed temporary venv/fixture. API and static SPA routes for Dashboard, Plans, Namespaces, artifact diagnostics, namespace detail, and plan review all returned HTTP 200; dashboard found three plans; diagnostics returned zero fixture errors; no provider/model/source-specific adapter, apply, remote, planning-service, or retrieval module loaded.
16. `rm -rf dist web/node_modules`; `uv sync --locked`; `uv lock --check`; ordinary-package core import isolation; final `git diff --check`, staged-name, generated-directory, database/log artifact, and status checks — passed. The default core environment removed FastAPI/Starlette/Uvicorn; importing `buoy_search` loaded no UI/provider/model/remote/retrieval module; FastAPI and Uvicorn were unavailable; no staged file or disallowed generated artifact remained.

## Validation repairs and deviations

- The first complete frontend run hit a pre-existing timing-sensitive EventSource regression (`oldSource` undefined). No source changed; the immediate complete rerun passed 50/50. This remains a test-harness flake observation, not evidence of a product failure.
- The first static inventory invocation used unavailable bare `python`; the exact same standard-library check passed through `uv run python`.
- The first installed-wheel harness used a nonexistent fixture key; the corrected harness used the fixture's documented `namespace` key. A second preliminary harness over-broadly prohibited generic `crawler` and `database_relation` modules after complete plan verification; the accepted check uses the established provider/model/source-specific forbidden set, while diagnostics inertness is separately enforced by patched tests. These were harness corrections, not source repairs.
- The first core-import harness imported the CLI and over-broadly prohibited its established retrieval-module import. The accepted ordinary-package check imports `buoy_search`, which is the core import-inertness boundary, and proved UI/provider/model/remote/retrieval modules absent in the restored core environment.
- Wheel installation resolved compatible current dependencies in an isolated temporary venv (including FastAPI 0.140.13 and DuckDB 1.5.5), while repository validation used locked versions shown above.

## Changed surface

Backend: `src/buoy_search/command_center_local.py`, `src/buoy_search/command_center_api.py`. Frontend: `web/src/App.tsx`, `web/src/api.ts`, `web/src/types.ts`, `web/src/App.test.tsx`. Tests: `tests/test_command_center_local.py`, `tests/test_command_center_api.py`. Docs/static: `docs/command-center.md`, packaged `index.html`, new `index-IKQ18Gxc.js`, removal of obsolete `index-DAM_87xf.js`. Durable records: three focused specs, terminal parent/four child tickets, this evidence, and `.10x/reviews/2026-07-29-command-center-bounded-review-hardening-final-review.md`.

## Limits and residual risk

- TestClient and React Testing Library are not a live graphical-browser run.
- Complete selected-delta verification remains linear and took about 2.67–2.71 seconds for 100,100 rows; the frontend guard bounds one screen only and does not coordinate or cancel other tabs/routes/processes.
- JSON bytes depend on deterministic fixture text and exclude transport framing. RSS is cumulative whole-process peak.
- The existing React Router audit disposition remains unchanged.
- Independent review and ticket closure passed. The bounded commit hash is intentionally supplied only in the execution handoff; default-environment restoration is complete.

## Side-effect attestation

No live crawl, clone, document/database source adapter, provider, remote refresh/search, embedding/model load, credential read, apply/approved apply, catalog/namespace mutation, turbopuffer operation, push, merge, PR, publish, or release ran. Tests and measurements used fakes or disposable local temporary artifacts. Build, isolated install, fixture, benchmark JSON, temporary logs, `dist`, and `web/node_modules` were removed.
