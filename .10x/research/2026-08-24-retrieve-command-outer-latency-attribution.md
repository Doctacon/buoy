Status: done
Created: 2026-08-24
Updated: 2026-08-24

# Retrieve Command Outer-Latency Attribution

## Question

Which measured command phases account for the large gap between near-shell
`command_duration_ms` and nested `pipeline_duration_ms` in the retained
telemetry-v2 canary and installed-`v0.6.3` pilot, what remains unmeasured, and
is another live provider campaign needed before deciding the next action?

## Sources and methods

### Durable authority inspected

- `.10x/specs/retrieve-command-telemetry.md`
- `.10x/specs/local-telemetry-v2-storage-and-migration.md`
- `.10x/specs/local-telemetry-writer.md`
- `.10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md`
- `.10x/evidence/2026-08-24-local-telemetry-v2-canary.md`
- `.10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md`
- `.10x/reviews/2026-08-24-v0-6-3-installed-telemetry-pilot-review.md`
- exact timing and construction boundaries in `src/buoy_search/entrypoint.py`,
  `src/buoy_search/cli.py`, `src/buoy_search/telemetry.py`,
  `src/buoy_search/retriever.py`, `src/buoy_search/chunker.py`, and
  `src/buoy_search/telemetry_store.py`

### Read-only retained-store procedure

The canonical private DuckDB was opened with `duckdb.connect(...,
read_only=True)`. Bounded queries used only:

- command order, execution/retrieval mode, outcome, bounded package/model labels,
  command duration, and pipeline duration;
- governed stage name, parent relationship, duration, and millisecond offsets
  from command start; and
- direct-root-child intervals required for interval-union coverage.

Trace/span IDs were used only for joins and ordering and were not emitted or
retained. Queries did not select attributes, query text, arguments, namespaces,
credentials, errors, URLs, paths, content, provider responses, or result data.
No telemetry command, writer, queue, migration, export, copy, checkpoint,
provider/model operation, or new sample ran.

Seven existing command-v2 rows were inspected: one canary preview and six live
rows split evenly between the canary candidate and installed `v0.6.3` pilot.
For each row, direct children of `buoy.retrieve.command` were sorted and merged
as intervals. Their interval union—not a sum of nested spans—was subtracted from
the authoritative command duration to calculate uncovered in-root time.
Automatic prepare substage coverage used the same interval-union method within
`buoy.retrieve.prepare`.

Before and after the read-only connection, the canonical store remained exactly
5,779,456 bytes with SHA-256
`3eef4252e758b041f5826da7e0fd4b51ed12e025ae8c94e2ff04b55006791268`.

## Findings

### The gap is measured prepare time, not missing telemetry

All six live rows have the same direct-root-child shape: bootstrap, prepare,
pipeline, and render. Values below are authoritative span intervals in
milliseconds. `In-root uncovered` is command duration minus the union of those
direct child intervals.

| Campaign / mode | Command | Bootstrap | Prepare | Pipeline | Render | In-root uncovered | Prepare / outer command |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Canary explicit single | 43,997.248 | 292.345 | 41,279.406 | 2,402.982 | 0.451 | 22.064 | 99.24% |
| Canary explicit multi | 12,571.450 | 328.046 | 8,959.771 | 3,255.380 | 0.386 | 27.867 | 96.18% |
| Canary automatic | 12,762.722 | 321.548 | 11,046.451 | 1,367.358 | 0.374 | 26.991 | 96.94% |
| Installed explicit single | 47,845.827 | 290.857 | 45,933.901 | 1,572.189 | 0.585 | 48.295 | 99.27% |
| Installed explicit multi | 9,887.648 | 294.002 | 8,423.542 | 1,130.154 | 0.355 | 39.595 | 96.19% |
| Installed automatic | 11,067.981 | 296.651 | 9,859.359 | 874.174 | 0.332 | 37.465 | 96.72% |

“Outer command” here is the measured `command_duration_ms -
pipeline_duration_ms`, not an inferred shell total. Prepare alone explains
96.18%–99.27% of that measured outer interval in every live observation.
In-root uncovered time is only 22.064–48.295 ms (0.050%–0.400% of command
duration). Bootstrap is 290.857–328.046 ms and render is below 0.6 ms, so
neither is the dominant live latency boundary.

The canary preview reinforces the boundary distinction without loading a live
retriever: 456.779 ms command, 428.871 ms bootstrap, 0.049 ms prepare, 0.128 ms
render, and 27.731 ms in-root uncovered. Thus CLI import/argument bootstrap on
this retained sample is below half a second; the multi-second live gap appears
only when live preparation constructs retrieval components.

### Automatic preparation is already finely attributable

Automatic rows contain non-overlapping governed children inside prepare:

| Campaign | Prepare | Routing-model interval union | Catalog | Route select | Prepare not covered by these children |
| --- | ---: | ---: | ---: | ---: | ---: |
| Canary | 11,046.451 | 8,525.683 (77.18%) | 2,130.466 (19.29%) | 182.512 (1.65%) | 207.790 (1.88%) |
| Installed | 9,859.359 | 7,414.078 (75.20%) | 2,087.009 (21.17%) | 184.423 (1.87%) | 173.849 (1.76%) |

Source order makes the first approximately 1.3 ms routing-model child the
confidence artifact load and the second 7.4–8.5 s child the routing embedder
factory (`cli.py:1601-1606` and `1652-1658`). Catalog read and eligibility are
inside `buoy.routing.catalog` (`cli.py:1633-1647`), and route selection is
inside `buoy.routing.select` (`cli.py:1711-1729`). The remaining 174–208 ms
also contains selected-config/options construction and live
`MultiNamespaceRetriever.from_configs` after route selection
(`cli.py:1734-1779`); the retained graph does not split those operations.

The automatic evidence is sufficient to say that routing-model construction
and catalog reading—not the nested retrieval pipeline—dominate automatic
command time in these two observations.

### Explicit preparation reaches one coarse source boundary

For explicit modes, the whole live setup is one `buoy.retrieve.prepare` span
(`cli.py:1545-1599`). Inside it, source synchronously constructs either
`HybridRetriever.from_config` or `MultiNamespaceRetriever.from_configs`.
Both paths instantiate the same `SentenceTransformerEmbedder` and then create
one or more provider namespace clients (`retriever.py:667-685` and
`887-924`). `SentenceTransformerEmbedder.__init__` imports
`sentence_transformers` and synchronously constructs the local
`SentenceTransformer` model (`chunker.py:532-553`).

No retained explicit-mode child span separates model import/load from namespace
client construction or the small configuration work. The source therefore
identifies a narrow candidate set, but the telemetry cannot truthfully assign
41.3–45.9 s (single) or 8.4–9.0 s (multi) to one member of that set. Model load
is source-reachable and plausibly dominant; it is not proven as the exact
explicit-mode duration by these rows.

### Cold/warm interpretation is order-confounded

All live rows used the same governed embedding-model and float32 precision
labels. Each command was a separate Python process. In both campaigns,
explicit single was the first command that constructed a live retrieval model;
its prepare interval was 41.279 s and 45.934 s. Explicit multi followed and
prepared in 8.960 s and 8.424 s. Automatic followed that and spent 7.414 s and
8.526 s in its routing-model interval union.

This repeated shape is consistent with a process-cold constructor benefiting
from host-level file/dynamic-library/model caches after the first live load.
However, mode and order were identical in both campaigns, cache residency was
not observed, and no cache-clearing or counterbalanced run exists. Every
process was process-cold while host cache state was unknown. The data therefore
cannot distinguish a single-mode cost from first-live-command/host-cache cost,
and it does not establish cold or steady-state distributions.

### Near-shell time outside the command root is bounded separately

The installed pilot retained parent-observed wall timing. Wall minus command
root was 788.310 ms for explicit single, 787.789 ms for explicit multi, and
751.686 ms for automatic. This includes harness/shell work, Python pre-entry,
and post-return teardown that the governing specification explicitly excludes
from `command_duration_ms`. The canary did not retain equivalent external wall
values. These sub-second intervals are real but do not explain the 8.8–46.3 s
measured command-minus-pipeline gap.

## Conclusions

1. Existing telemetry is sufficient for coarse attribution: live
   `buoy.retrieve.prepare` owns 96.18%–99.27% of measured command time outside
   the pipeline. The dominant gap is not an OpenTelemetry clock error and is
   not hidden in the 22–48 ms in-root residual.
2. Automatic attribution is actionable at current granularity: routing-model
   construction contributes 75.20%–77.18% of prepare and catalog reading
   contributes 19.29%–21.17%.
3. Explicit attribution stops at retriever construction. Current rows cannot
   separate local model construction, provider-client construction, and minor
   configuration work.
4. The two repeated campaign sequences suggest but do not prove a host-cache
   effect. They cannot support mode comparisons, percentile claims, a latency
   target, or an optimization acceptance threshold.
5. No additional live provider measurement is needed now. Repeating the same
   ordered workloads would reproduce the confounding without locating the
   explicit prepare sub-boundary.

## Recommendation

Do not open an optimization implementation ticket yet. First shape and
separately authorize a provider-free attribution experiment:

- use exact installed-release source, pinned local model assets, enforced
  offline settings, and a fake/injected provider client so no credential or
  network access is possible;
- instrument a temporary test-only probe around sentence-transformer import,
  local model construction, and provider-client/retriever construction without
  changing production telemetry semantics;
- run every observation in a fresh process; discard one host-warmup result and
  retain five ordered measurements for the remaining process-cold/host-warm
  condition;
- retain command and component intervals independently rather than summing
  nested measurements;
- bind runtime/host/model/cache-manifest identities before and after, prohibit
  model download and cache mutation, and record only content-free timings; and
- use the historical first-live rows only as cold-state observations unless a
  safe, separately ratified cold-host procedure exists. Do not clear OS or model
  caches merely to manufacture a cold sample.

If that provider-free probe proves local model construction dominates, a later
bounded implementation ticket can evaluate one named loading/lifecycle change
while preserving offline operation, model correctness, routing behavior,
privacy, and command/pipeline semantics. If end-to-end mode distributions are
then acceptance-critical, propose a separate live campaign rather than reuse
this ticket. A candidate balanced design is six three-command blocks containing
all six mode orders once (18 commands total), one fresh process per command,
with exact logical and physical-attempt budgets, model/cache state, privacy,
and retention ratified first. That live design is intentionally not authorized
or recommended before provider-free attribution.

## Limits

- One macOS arm64 host, two campaign sequences, one preview, and six live rows.
- Candidate and released package versions differ, although accepted runtime
  source identities were continuous.
- No CPU, memory, device utilization, import profile, model-load subspan, cache
  residency, packet trace, or physical provider-attempt receipt was retained.
- Timestamps establish intervals and ancestry, not causal resource utilization.
- The read-only investigation made no new behavior, performance, cost, or
  product-surface decision.
