Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Ticket: .10x/tickets/done/2026-08-27-default-compatible-retrieve-embeddings-to-worker.md
Decision: .10x/decisions/buoy-defaults-compatible-retrieve-embeddings-to-the-local-worker.md
Specification: .10x/specs/default-retrieve-embedding-worker.md
Prior-Live-Evidence: .10x/evidence/2026-08-27-experimental-retrieve-embedding-worker-ab.md

# Default Retrieve Embedding Worker Evidence

## Implemented boundary

`buoy retrieve` now selects the reviewed local embedding worker by default only for the exact default `BAAI/bge-small-en-v1.5` float32 identity on a capable POSIX host. It uses one command session with phase-specific adapters: the routing adapter falls back to the established pinned local routing factory, and the retrieval adapter falls back to `SentenceTransformerEmbedder` with the selected runtime config. One session owns the worker-failed and warning-emitted state, so the first worker failure prints exactly one bounded warning and all later embeddings in that command go directly in-process.

The worker is selected before credential values or provider construction. It still performs no model load or IPC until an embedding is requested. Automatic routing catalog reads are not replayed; content retrieval begins only after a successful worker or fallback embedding. Explicit retrieval constructs each provider namespace once and embeds once under the real retriever path.

`--no-embedding-worker` exists only on retrieve and forces the established in-process path. The experimental opt-in flag is removed without alias. Custom models, float16, unsupported capability, explicit dry-run, and opt-out short-circuit before importing the worker backend. Non-retrieve/help/version imports remain dormant. The prior live A/B harness is now explicitly retired and fails before credential/subprocess work, preserving its historical logic without authorizing stale experimental-flag calls.

No provider credential/client, catalog/content request, reranker, result, telemetry store, or rendering behavior moved into the worker. No telemetry schema or result payload marker was added.

## Changed paths for this ticket

Production and documentation:

- `src/buoy_search/cli/main.py` — default eligibility, lazy exact identity check, retrieve opt-out, shared command fallback session, phase-specific fallback factories, one redacted warning, and routing/retrieval injection.
- `docs/retrieval.md` — default, eligibility, memory/idle lifetime, opt-out, in-process selection, dry-run boundaries, and warning/fallback behavior.

Focused tests and historical harness safety:

- `tests/cli/test_cli.py`
- `tests/retrieval/test_automatic_routing.py`
- `tests/retrieval/test_automatic_routing_after_apply.py`
- `tests/retrieval/test_multi_namespace_retrieval.py`
- `tests/retrieval/test_routing_activation_cli.py`
- `tests/retrieval/test_embedding_worker.py`
- `tests/telemetry/test_retrieve_command_telemetry.py`
- `tests/fixtures/experimental_retrieve_worker_ab.py`

The optional embedder injection seams in `src/buoy_search/retrieval/retriever.py` and their tests were already implemented and reviewed by the closed experimental ticket; this ticket reuses them without changing their omitted-argument behavior.

## Focused coverage

Focused CLI/routing/retrieval/worker/telemetry coverage proves:

- opt-out is retrieve-only and the experimental flag is rejected;
- eligible explicit live retrieval injects the worker and embeds once;
- eligible automatic dry-run uses the worker only for routing;
- eligible automatic live uses one session for routing and retrieval;
- explicit dry-run, opt-out, custom model, float16, and unsupported capability create no worker selection/import/IPC and emit no fallback warning;
- the first worker failure is value-redacted, emits one exact warning, constructs each in-process fallback once, and prevents later worker calls;
- a typed in-process fallback-failure boundary maps fallback construction or encoding double failure to `model_error` before the generic provider/routing handlers, with one warning and bounded phase-specific messages;
- explicit fallback-construction double failure constructs the provider wrapper once but performs zero content operations; automatic fallback-encoding double failure performs one catalog read and zero content-retriever/content operations;
- automatic routing fallback uses the established routing embedder and later retrieval uses the established retrieval embedder without replaying catalog construction, retriever construction, or content retrieval;
- telemetry remains governed success telemetry with no worker detail/backend marker/query/vector/raw failure; and
- historical live harness execution is rejected before subprocess work.

The initial focused six-module runs passed 220 tests on Python 3.11 and 3.13. After independent review found the fallback double-failure taxonomy gap, focused CLI/automatic-routing/telemetry suites passed 133 tests on each runtime, including explicit construction-failure and automatic encoding-failure regressions.

## Full validation

Final suites after the independent-review repair and all source/test edits:

- Python 3.13: `Ran 1243 tests in 92.750s` / `OK`.
- Python 3.11: `Ran 1243 tests in 115.990s` / `OK`.

Only the established two plan-cleanup warnings and upstream lxml deprecation warning appeared.

Provider-free exact-model validation under removed provider credential names and offline controls reported:

- worker startup: 8,959.374 ms;
- first fresh client: 1,863.091 ms;
- second fresh client: 33.883 ms;
- maximum vector delta: 0.0;
- ranking order equal: true;
- one worker PID reused: true;
- fresh clients imported Sentence Transformers: false;
- worker RSS: 524,812,288 bytes, below 4 GiB;
- source manifest unchanged: true;
- exact model-cache manifest unchanged: true;
- provider/network/telemetry operations: zero; and
- validated cleanup: true.

Passed:

- Python 3.11/3.13 `py_compile` over every changed source/test module;
- `scripts/validate_ranking_contract.py`;
- `scripts/validate_ranking_promotion.py --base-ref HEAD` (authority unchanged);
- `scripts/c6_syntax_forecast.py validate`;
- wheel and sdist builds;
- isolated Python 3.13 wheel install;
- isolated root/retrieve help with `--no-embedding-worker` present and experimental flag absent;
- isolated no-worker CLI import and explicit opt-out dry-run with no `.buoy` state;
- isolated custom-model, opt-out, and unsupported-capability selection proving no worker module import;
- wheel inventory including `buoy_search/retrieval/embedding_worker.py`;
- `git diff --check`; and
- no staged files.

One parallel dual-runtime focused invocation failed because concurrent `uv run` processes replaced the shared `.venv`; both runtimes were rerun sequentially and passed. Initial focused/full runs exposed stale tests that intentionally asserted in-process routing without opting out; those fixtures now explicitly select unsupported/opt-out behavior, while dedicated default-worker tests cover the new path. An initial promotion-validator invocation omitted its required comparison event/base; the corrected local command with `--base-ref HEAD` passed. No validation failure was hidden or retried as a governed measurement.

## Acceptance mapping

1. Governing default spec: implemented as mapped above.
2. Eligible default: explicit and automatic tests prove exact worker injection/session reuse.
3. Opt-out: parser, live selection, dry-run, isolated install, and dormancy checks pass.
4. Experimental flag: removed from parser/help without alias; historical harness retired.
5. Custom/float16/unsupported: direct in-process selection with no worker side effect/warning tested.
6. Fallback: exactly one redacted warning, command-wide switch, phase-specific established factories, fallback success, typed construction/encoding double-failure `model_error`, bounded explicit/automatic messages, no provider replay/content operation, and telemetry privacy tested.
7. Live/dry-run/help/non-retrieve boundaries: focused and full suites pass.
8. Dual runtime and exact parity: 1,243 tests per runtime plus delta 0.0/equal ranking validation.
9. Validators/package/isolated/diff/no-staged gates: passed.
10. Independent review: passed at `.10x/reviews/2026-08-27-default-retrieve-embedding-worker-review.md` after the double-failure phase-taxonomy P1 was repaired and independently rereviewed.
11. Prohibited operations: no live provider, global install, release, deployment, or publication operation occurred.

## Residual limits

- Default live latency remains supported by the prior three-run Darwin arm64 evidence, not a new campaign or distribution.
- Worker real-model validation remains Darwin arm64; unsupported platforms select in-process by design.
- A failed worker followed by fallback may make one command slower before succeeding.
- Same-effective-user processes remain inside the documented Unix-socket boundary.
- Offline/network absence is procedure/source-controlled rather than packet-traced.
