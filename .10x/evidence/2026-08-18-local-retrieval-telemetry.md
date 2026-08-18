Status: recorded
Created: 2026-08-18
Updated: 2026-08-18
Ticket: .10x/tickets/done/2026-08-18-implement-local-retrieval-telemetry.md
Decision: .10x/decisions/buoy-records-opt-in-local-retrieval-telemetry.md
Specification: .10x/specs/local-retrieval-telemetry.md
Review: .10x/reviews/2026-08-18-local-retrieval-telemetry-review.md

# Local Retrieval Telemetry Evidence

## Initial observation

The implementation session began from exact
`origin/develop@df8b82eef61ed36275773273f0648d29763acd65` in isolated worktree
`/private/tmp/buoy-local-retrieval-telemetry` on
`work/local-retrieval-telemetry`. The original `develop` worktree was clean
and was not used for implementation.

The approved first increment records only content-free operational retrieval
traces. It is disabled by default, uses no Collector or remote exporter, and
writes only to `~/.buoy/telemetry/telemetry.duckdb` when the user explicitly
sets `BUOY_TELEMETRY=local`. Existing state, catalog, content, and artifact
databases are out of scope and were neither opened nor migrated.

## Implementation identity and scope

The reviewed implementation is exact commit
`3a9aa15db39829171d5c9fc74754d48b9629e224`, tree
`3b58627d4279f48bf9418156bd86f5e6a2ec1de2`, with sole parent and exact
`develop` base `df8b82eef61ed36275773273f0648d29763acd65`.

The implementation changes exactly 11 owned paths: six additions and five
modifications, totaling 3,296 insertions and 34 deletions. It adds the
decision, specification, ticket, telemetry module, focused test module, and
user documentation; instruments only the retrieval boundary; adds the
OpenTelemetry SDK dependency; and updates the lock and changelog. It does not
change release workflows, provider clients, catalog/state schemas, routing
algorithms, evidence algorithms, ranking fixtures, or command behavior.

The certified `cli.py`, `evidence.py`, `routing.py`, and
`routing_quality.py` files are byte-identical to the base. Their SHA-256
receipts remain, respectively,
`92c49e943ed5918df7fe65294ff89717e2654a8e9d76317979b63198f1b98ee9`,
`78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`,
`e0711bc40a90c364ca52c7a9884d29342be21e3df43950ec26033a70c2b6e9fd`,
and `5d53624613bf5a80ad80e6d103d07cb0fab2d2a6ae2a1456e6c2709147d67aa7`.

## Behavioral and privacy proof

Focused tests prove exact opt-in and kill-switch behavior, no disabled-mode
filesystem activity, private `0700` directories and `0600` files, one root
trace across namespace worker threads, and preservation of unrelated caller
context. A private OpenTelemetry provider is always-on and isolated from the
process-wide provider and current context, so Buoy's local trace cannot be
exported by ambient instrumentation or appear in an outbound `traceparent`.
SDK construction is lazy and all telemetry setup, instrumentation, shutdown,
locking, schema, and persistence failures degrade to a no-op without changing
retrieval results, errors, call counts, order, fallback, or output.

Every persisted span, event, and attribute passes a second sink-side
allowlist. Adversarial exact-byte scans prove that queries, content, namespace
identifiers, URLs, paths, credentials, raw exceptions, command arguments,
vectors, provider payloads, ambient resource attributes, and unrelated
`ContextVar` values are absent. Automatic exception events and stack traces
are disabled. Widening events are accepted only from the root span.

The DuckDB sink buffers one completed trace, takes a nonblocking private lock,
and appends it in one transaction. First-store creation is atomic. Existing
stores are opened with external access and extension installation/loading
disabled, then validated through qualified DuckDB system catalogs without
binding persisted views. Ordered table shapes and code-owned canonical view
digests reject malformed, forged, shadow-macro, external-file, or incompatible
stores without rewriting them. UTC-naive bindings preserve exact epochs even
when the DuckDB session time zone is `America/Phoenix`.

## Validation receipts

- The exact implementation commit passed 21 telemetry tests and a 137-test
  combined telemetry/retrieval/evidence/automatic basket.
- Python 3.11 and Python 3.13 each passed all 904 discovered tests. Enabled
  retrieval-equivalence runs also preserved established behavior.
- The independent privacy review reproduced ambient-context/header isolation,
  unrelated-context isolation, invalid OpenTelemetry-environment silence,
  atomic first creation, incompatible-store preservation, schema shadowing
  resistance, external-view nonbinding, canonical-view authentication, and
  exact non-UTC timestamp behavior.
- Source validation passed with active routing artifact
  `745cdb76c894ef1770f6daf3d303f2b6d0ba6905098924f1cb1a8fa40e738fea`
  and canary suite
  `0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
- Ranking validation passed 13 datasets, 369 judgments, and 90 composite
  identities. C6 passed with digest
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`
  and its expected non-release-ready state.
- The 157-package offline lock check, in-memory compilation of 92 Python files
  on both runtimes, certified-file comparison, and `git diff --check` passed.
- Both runtimes produced and validated byte-identical distributions for
  `0.5.2.dev35+g3a9aa15db`: the 71-file, 658,105-byte wheel SHA-256 is
  `3614b7adaa40e269401a4fa479535a523a13daf55971450c83a0c849959942ea`;
  the 147-file, 1,163,239-byte sdist SHA-256 is
  `90f3c1f676d2240cd8a461a81400bddfab3b853e468487e9eb4400afa724d960`.
- A clean Python 3.13 wheel install passed console version/help checks. Its
  disabled trace remained a silent no-op even with an invalid SDK span-limit
  environment value. Its enabled trace persisted one successful run and two
  spans to an isolated private DuckDB with `0700` directories and `0600`
  database/lock files, then returned the expected analytical row.

## Compatibility and external effects

With telemetry absent or disabled, live retrieval remains behaviorally
equivalent and creates no telemetry path. Enabling it adds only a best-effort
post-retrieval local append, bounded temporary in-memory spans, and a
nonblocking local lock attempt. The v1 store has no retention or purge policy;
users may delete their own telemetry database while Buoy is not writing it.

Validation used only isolated temporary homes, databases, virtual
environments, loopback fixture servers, and distribution directories. The
clean-wheel dependency install used package-network access but did not replace
the global `uv` tool or modify a user environment. No real-home telemetry,
existing local asset, credential, provider/catalog/content state, model cache,
package publication, tag, Release, branch protection, `main`, or release
artifact was changed. Durable effects at evidence time are limited to the
isolated task branch/worktree and its bounded implementation commit; the
explicitly authorized branch push, pull request, and separately reviewed
squash integration into `develop` follow the task handoff.
