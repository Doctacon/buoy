Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Target: .10x/tickets/2026-08-24-run-local-telemetry-v2-canary.md, .10x/evidence/2026-08-24-local-telemetry-v2-canary.md, commit b1a34e26e7b16aec897d15d829dee929b459f0ad
Verdict: fail

# Local Telemetry V2 Canary Combined Review

## Review inputs and method

This record reconciles two independent review responses against the ticket,
sanitized evidence, exact integrated source, focused source test, and current Git
metadata without rerunning any canary or telemetry operation.

- The correctness/privacy reviewer initially detached for supervisor-provided
  sanitized Git/status facts, then completed with **FAIL**. It accepted the
  candidate identity, migration, backup, v1 preservation, four observations,
  timing/graph behavior, privacy, model/global invariance, and cleanup, but found
  the physical provider-call bound unsupported.
- The acceptance/side-effects reviewer independently returned **FAIL** on the
  same provider-call evidence gap while accepting the other mapped criteria.
- Read-only source inspection confirmed that `run_multi_query` in
  `src/buoy_search/retriever.py` first attempts server-side fusion and, for the
  governed unsupported-form error, issues a second physical provider request
  inside the same logical namespace operation.
- Read-only test inspection confirmed the compatibility path expects two
  namespace-client invocations for one retrieval operation in
  `tests/test_retriever.py`.
- Read-only Git inspection confirmed the bounded task head and unchanged
  `develop` and `main` identities. After the detached reviewer requested
  parent-observed facts, the parent rebuilt the exact candidate offline in a
  private temporary environment and ran only documented read-only status and
  database/count inspection. No migration, retrieve, flush, provider/model,
  credential, global-tool, or hosted mutation was rerun, and the review
  environment was removed.

## Findings

### Significant blocker: physical provider-call bound is unsupported

The evidence originally treated five `buoy.namespace.query` spans as five
content-provider calls. That inference is invalid. A span represents one
logical namespace operation, while exact integrated source may issue two
physical requests in that span when server-side fusion is unsupported and the
client compatibility path is selected.

The retained telemetry does not record fusion mode or physical invocation
count. The raw result and temporary runtime artifacts were deleted as required,
and there is no independent provider-call receipt. Five logical spans therefore
do not prove at most six physical calls; under the implementation's bounded
fallback shape they could represent more than six. This does not prove the
limit was exceeded. It proves the required upper bound is not established.

The ticket's provider-call acceptance criterion is consequently unsatisfied.
The execution cannot repair this evidence gap because migration and all four
workload authorities are consumed and retries are explicitly prohibited.

### Significant blocker: independent review gate is unmet

Both independent reviewers returned **FAIL** on the unsupported physical
provider-call ceiling. The acceptance criterion requiring PASS or resolved
findings is unsatisfied. There is no authority to resolve the provider-call
finding through another canary operation.

### Record inconsistency resolved

The ticket previously ended with “has not begun” despite append-only progress
showing completed migration and workloads. Reconciliation replaces that stale
blocker text with the exact review blockers and marks the ticket `blocked`.

### Evidence correction

The canary evidence now describes the observed count as five namespace spans,
not five provider calls, and explicitly states that the physical call ceiling
is unsupported. This correction narrows the claim; it does not alter or rerun
any observation.

## Ticket acceptance-criterion mapping

| Ticket criterion | Result | Evidence / limit |
| --- | --- | --- |
| Exact candidate commit/tree, source identities, wheel, installed package, and Hatch-VCS version | Supported | Sanitized artifact and installed-package identities are recorded. Ephemeral artifacts were removed as required, so hashes remain executor attestations. |
| Global executable identity unchanged | Supported | Complete content-free pre/post package and uv-tool identities match; direct Git review found no related repository change. |
| Fresh schema-v1, 12-run, empty-queue, no-active-writer/migration gate | Supported | Sanitized preflight facts are recorded; no rerun was attempted. |
| Single successful migration, immutable backup, schema v2, preserved v1 history/views, safe state | Supported | Backup byte identity and ordered v1 semantic/view digests are recorded. |
| Exactly four attributable v2 observations in the four required modes | Supported | Four content-free command rows and mode order are recorded. |
| Truthful command/pipeline timing, graph, status, and automatic fanout at most three | Supported | Preview/live nullability, duration enclosure, graph reachability, success, and fanout two are recorded. |
| Four zero-exit commands with no retry | Supported | Four zero exits and once-only executor account are recorded; raw outputs were removed as required. |
| At most six content-provider calls plus bounded catalog reads; no writes | **Unsupported / FAIL** | Five namespace spans do not bound physical calls because one span may make two requests. Catalog accounting remains source-bounded; no write path is identified. |
| No model/network download; pinned local assets only | Supported | Complete model-cache manifest is byte-identical pre/post under recorded offline settings. |
| Prohibited values absent from new telemetry artifacts | Supported | Sanitized literal/file/database-scalar scan passed; the correctness/privacy reviewer accepted the privacy evidence while failing the separate provider-call criterion. |
| Temporary runtime/raw output removed; backup retained; source/refs/global/unrelated state unchanged | Supported | Cleanup and content-free global/ref comparisons are recorded and current Git metadata is coherent. |
| Independent review PASS or all findings resolved | **Unsatisfied / FAIL** | Both independent reviewers failed the unsupported provider-call criterion; the finding is unresolved. |

## Verdict

**FAIL.** Most canary behavior and side-effect criteria are supported, but the
at-most-six physical content-provider-call criterion and mandatory review gate
are not. Both independent reviewers substantively agree on that blocker. The
ticket must remain blocked and must not move to `done`.

The one-time decision is superseded by consumption and moved to
`.10x/decisions/superseded/one-time-local-telemetry-v2-canary.md`. That record
is historical provenance only and grants no retry or repair authority.

## Residual risks and limits

- Actual physical content-provider invocation count is unknown and cannot be
  reconstructed from retained telemetry. The blocked ticket owns this gap.
- Exact catalog request accounting remains intentionally source-bounded rather
  than independently observed.
- Ephemeral wheel/runtime/raw artifacts were deleted as required, so artifact
  hashes, shape checks, and once-only operation counts remain executor
  attestations backed by the sanitized record rather than retained raw files.
- Both independent reviews are complete and fail on the same unsupported
  physical-call-count criterion; neither claims that the limit was exceeded.
- No evidence shows provider writes or unrelated mutation; this review does not
  turn source-contract absence into independent network-level proof.
