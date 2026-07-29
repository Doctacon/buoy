Status: recorded
Created: 2026-07-28
Updated: 2026-07-28
Relates-To: .10x/tickets/done/2026-07-28-baseline-bounded-review-performance.md, .10x/tickets/done/2026-07-28-command-center-bounded-review-performance-plan.md, .10x/specs/command-center-bounded-inventory-transport.md, .10x/specs/command-center-coalesced-plan-review.md

# Command Center Bounded Review Performance Baseline

## What was observed

Unchanged production behavior at hosted-main base `4a4af8c1db8464893ea97ce2395842e25d861ed0` was measured through the production FastAPI app and `LocalInventoryService`. The disposable fixture contained 1,000 near-limit schema-v2 plan summaries across 1,000 namespaces, one fully valid selected delta with 100 changed rows and 100,000 stale rows, 999 unopened delta sentinels, and one one-row applied state. The checkout guard reported no changed production-behavior file.

The current frontend inventory request shape fetched every API page at limit 100. Plans and Namespaces each made 10 initial requests, transferred 1,000 records, and implied 1,000 rendered local rows. Against the ratified 50-row current-page target, this is 20× record/render multiplication. The current plan-review `Promise.all` shape made three requests and invoked three independent complete verifications on initial load, chunk pagination, and stale pagination.

No fixture database, raw JSON output, browser profile, log, build output, provider/model/source result, credential, or private artifact was retained in the repository.

## Host and runtime

- OS: `macOS-26.5.1-arm64-arm-64bit-Mach-O`
- Architecture: arm64; 10 logical CPUs
- Python: 3.13.0
- DuckDB: 1.5.4
- FastAPI: 0.139.2
- Starlette: 1.3.1
- httpx: 0.28.1
- Node: v24.6.0
- npm: 11.5.1

## Fixture

- Summary-qualified plans: 1,000; each `plan.json` exactly 131,072 bytes.
- Plan namespaces: 1,000; the selected namespace has one plan.
- Selected delta: 100 changed upserts and 100,000 stale rows.
- Other deltas: 999 fixed sentinel files.
- Applied state: one row in one database.
- Fixture lifecycle: one system temporary directory, deleted automatically.

## Browser/API transport baseline

JSON bytes are the summed exact UTF-8 API response bodies and exclude headers and transport framing. Wall time uses `time.perf_counter`; RSS is cumulative whole-process `ru_maxrss` normalized to bytes.

| Inventory | Initial requests | Records transferred | Approx. JSON bytes | Wall (ms) | Current rendered rows | Target current-page rows | Multiplication | Peak RSS (bytes) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Plans | 10 | 1,000 | 710,603 | 383.992 | 1,000 | 50 | 20× | 238,911,488 |
| Namespaces | 10 | 1,000 | 575,605 | 50.401 | 1,000 | 50 | 20× | 239,304,704 |

For both inventories the observed request offsets were exactly `0, 100, …, 900`, each with `limit=100`. The focused React test uses 1,000 Plans and 1,000 Namespaces and dynamically requires those exact ten requests and the final rendered rows; it does not infer the multiplication from source text.

## Selected-plan verifier baseline

The benchmark issued each current browser transition's three requests concurrently through FastAPI `TestClient`. Every synchronous route ran verification in Starlette's worker pool. For every transition the trace observed three distinct `AnyIO worker thread` IDs, all off the benchmark main thread. Each verifier used `materialize=False` and still performed complete linear verification.

| Transition | Browser requests | Complete verifier calls | Wall (ms) | Verifier durations sorted (ms) | Verifier p50 (ms) | Sum verifier time (ms) | Peak RSS (bytes) |
|---|---:|---:|---:|---|---:|---:|---:|
| Initial | 3 | 3 | 9,847.325 | 8,632.663; 9,708.841; 9,844.396 | 9,708.841 | 28,185.900 | 398,196,736 |
| Chunk pagination | 3 | 3 | 10,638.015 | 9,995.750; 10,036.755; 10,038.395 | 10,036.755 | 30,070.900 | 446,709,760 |
| Stale pagination | 3 | 3 | 10,616.837 | 8,597.248; 9,743.195; 10,037.583 | 9,743.195 | 28,378.026 | 446,709,760 |

Exact request and response observations:

- Initial: detail `1,305` bytes/zero delta rows, chunks offset 0 `2,635` bytes/10 changed rows, stale offset 0 `1,978` bytes/10 stale rows.
- Chunk pagination: detail `1,305` bytes/zero delta rows, chunks offset 10 `2,646` bytes/10 changed rows, stale offset 0 `1,978` bytes/10 stale rows.
- Stale pagination: detail `1,305` bytes/zero delta rows, chunks offset 10 `2,646` bytes/10 changed rows, stale offset 10 `1,989` bytes/10 stale rows.
- The verifier trace independently matched materialization: detail `(0 upsert, 0 stale)`, chunks `(10 upsert, 0 stale)`, stale rows `(0 upsert, 10 stale)` for every transition.
- The React characterization test dynamically requires the exact three paths on initial load, the same three with chunk offset 10 after chunk pagination, and the same three with stale offset 10 after stale pagination.

These concurrent complete-verification durations are intentionally not compared to the earlier isolated single-route benchmark: three verifiers contend for CPU, memory, and DuckDB resources, while prior selected-route measurements ran one request at a time.

## Procedure and commands

From the repository root:

```bash
uv sync --locked --extra ui
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/benchmark_command_center_bounded_review.py > /tmp/buoy-bounded-review-baseline-final.json
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_command_center_inventory_benchmark tests.test_command_center_bounded_review_benchmark -v
cd web && npm ci && npm test -- --run src/App.test.tsx
```

The benchmark validates every HTTP status, pagination metadata, transferred total, request/verifier count, verifier window, and fixture total before emitting JSON. Its complete raw JSON was used only in `/tmp` for evidence extraction and was removed after recording. The two Python benchmark modules passed six tests; the API integration test observed exactly three complete verifier calls. The frontend file passed all 37 tests, including the 1,000-row inventory and exact three-request transition characterization.

## What this supports

- Current Plans initial load is 10 API requests, 1,000 transferred records, 710,603 response bytes, and 1,000 rendered rows for this fixture.
- Current Namespaces initial load is 10 API requests, 1,000 transferred records, 575,605 response bytes, and 1,000 rendered local rows for this fixture.
- A 50-row current page would bound each to one twentieth of the transferred/rendered record count.
- Current selected-plan initial load and both pagination transitions each multiply one complete linear verification into three concurrent complete verifications.
- Each bounded response materializes only its requested row window, but complete verification time remains linear in the full 100,100-row delta.
- The synchronous FastAPI routes place the blocking work in the bounded AnyIO worker pool rather than the event-loop thread.

## Side-effect and artifact attestation

The fixture builder and benchmark performed zero provider, source, model-load, plan, apply, catalog/namespace-mutation, and turbopuffer-write operations. The app used an inert disposable managed-plan service solely to avoid creating managed job roots during TestClient lifespan. No live crawl, clone, source adapter, database provider, remote refresh/search, embedding model, apply, push, merge, PR, publish, or release operation ran.

`/tmp/buoy-bounded-review-baseline.json` and `/tmp/buoy-bounded-review-baseline-final.json` were raw disposable output only and were deleted after evidence extraction. `web/node_modules` was also removed after focused validation. No `.duckdb`, `.db`, `.sqlite`, `.log`, browser profile, `dist`, generated static asset, or credential is part of this change.

## Limits

- TestClient executes the production ASGI app without a network socket or graphical browser. Frontend tests bind the measured request shapes to current React/API behavior.
- Filesystem caches were not dropped. Results are host- and fixture-observational, not portable CI thresholds.
- Three simultaneous verifiers contend for host resources; their individual durations are not isolated single-request latency.
- Peak RSS is cumulative whole-process peak, not operation-attributed incremental memory.
- Exact JSON bytes vary if response fields or fixture metadata change; the benchmark tests keep pagination and materialization semantics synchronized.
- The fixture is a deterministic stress shape, not a distribution model of production namespace titles or changed-content sizes.
