Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: .10x/research/2026-08-24-retrieve-command-outer-latency-attribution.md, .10x/tickets/done/2026-08-24-investigate-retrieve-command-outer-latency.md, commit 8fe2b06ed907460c2858f6e3779bc29e56c657ef
Verdict: pass

# Retrieve Command Outer-Latency Attribution Review

## Target and method

An independent reviewer inspected exact candidate commit
`8fe2b06ed907460c2858f6e3779bc29e56c657ef`, tree
`5e18d137ef302b774e48e8a7eda1c9d9644eb985`, the governing ticket and
research record, cited production boundaries, telemetry-store schema/views, and
graph tests. The review performed no database, provider, model, credential,
network, telemetry, global-tool, source, or test mutation.

Closure reconciliation independently confirmed that the candidate diff from
activation commit `ae1749a86d5f30d03e09895365abb669f5c3b98b` changes only the
research and two ticket records, has no diff-check error, and remains clean at
the reviewed commit.

## Findings

### Correct attribution and arithmetic

The research uses direct-root interval unions rather than sums of nested spans.
Its 22.064–48.295 ms direct-root residuals and 96.18%–99.27% prepare/outer
ratios are arithmetically sound. The retained graph therefore establishes that
`buoy.retrieve.prepare` owns nearly all measured live command time outside the
pipeline; it does not attribute residual time by assumption.

Source attribution is consistent with implementation:

- command timing begins before CLI import in `src/buoy_search/entrypoint.py`;
- bootstrap and command-root boundaries are established in
  `src/buoy_search/cli.py`;
- explicit retriever construction is wholly inside prepare;
- automatic confidence, catalog, embedder, selection, and retriever-construction
  boundaries match the research;
- explicit constructors synchronously construct `SentenceTransformerEmbedder`
  before namespace clients; and
- the telemetry-store schema and views expose the authoritative command,
  pipeline, stage, parent, timestamp, and duration fields used by the method.

Existing tests enforce direct-root ancestry, ordering, and pipeline placement.

### Truthful limits and privacy

The research correctly narrows explicit-mode preparation to model,
provider-client, and configuration construction without assigning its
8.4–45.9 seconds to one component. Cold/warm and mode effects remain confounded;
no distribution, percentile, target, or mode comparison is claimed.

The bounded read-only queries excluded attributes and prohibited content,
emitted no identifiers, and performed no telemetry/provider/model operation.
The store's size and SHA-256 remained unchanged across the read-only procedure.

## Acceptance mapping

1. **Content-free stage mapping without nested summation — PASS.** Direct-child
   and category interval unions are used.
2. **Measured versus unmeasured time — PASS.** Root residual, automatic
   residual, and the explicit coarse boundary are separated.
3. **Cold/warm, runtime, mode, cache, and sample limits — PASS.** One host, two
   identically ordered campaigns, fresh processes, unknown host-cache state,
   and version-continuity limits are explicit.
4. **Separate authority before further effects — PASS.** The provider-free
   probe and optional live campaign are explicitly unratified.
5. **Optimization boundary and safeguards — PASS.** No optimization is proposed
   yet; offline model, routing, privacy, timing, and verification invariants are
   named for any later work.

## Findings by severity

- **Critical:** None.
- **Significant:** None.
- **Minor, resolved in closure:** The recommended provider-free construction
  probe required a separate durable owner before closure. It is now owned by
  `.10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md`,
  which remains blocked and grants no execution authority.

## Verdict

**PASS.** The read-only research satisfies every ticket criterion and supports
closure. No new live provider measurement is needed. Repeating the same ordered
live campaign would preserve the existing mode/order confounding.

The only justified next measurement is a separately authorized provider-free
construction probe. This review grants no model/cache operation, new retrieval,
provider access, telemetry mutation, source change, optimization, or live
campaign.

## Residual risk

- Explicit preparation still does not separate model import/load from client and
  configuration construction.
- Mode and campaign order remain confounded, so cold/warm distributions and
  performance targets are not established.
- The blocked follow-up requires exact model/cache and measurement semantics to
  be ratified before activation.
