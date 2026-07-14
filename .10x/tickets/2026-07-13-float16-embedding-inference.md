Status: open
Created: 2026-07-13
Updated: 2026-07-14
Parent: None
Depends-On: .10x/tickets/done/2026-07-12-approved-apply-throughput-measurement.md, .10x/tickets/done/2026-07-14-buoy-release-integration-validation.md

# Add Opt-In Float16 Embedding Inference

## Scope

Implement `.10x/specs/embedding-inference-precision.md` across plan, apply, retrieval, eval/autoresearch runtime configuration, documentation, and operational skills.

## Acceptance criteria

- Satisfy every behavior, compatibility, integrity, and verification requirement in the governing specification.
- Keep float32 as the default and preserve old plan verification without rewriting old artifacts.
- Prove precision changes drive re-embedding without changing row IDs.
- Run the specified real-chunk local parity/throughput benchmark without credentials or remote calls and record raw/summarized evidence.
- Run focused and complete test suites; record independent review.

## Explicit exclusions

- Live Turbopuffer apply/retrieval/evals, changing defaults, backend/model/chunk changes, concurrency, retries, and automatic remote precision discovery.

## References

- `.10x/specs/embedding-inference-precision.md`
- `.10x/research/2026-07-12-approved-apply-throughput-options.md`
- `.10x/evidence/2026-07-13-live-dagster-throughput-benchmark.md`

## Evidence expectations

Focused tests, full-suite output, real-chunk no-write vector/ranking parity, host-specific throughput measurements, docs/skill consistency, and independent review.

## Progress and notes

- 2026-07-13: User authorized implementation and selected explicit precision configuration: plans govern apply; retrieval/evals use a CLI flag or environment setting.
- 2026-07-14: Blocked behind the Buoy package rebrand to avoid implementing and then mechanically renaming the same cross-cutting plan/apply/retrieval surface. The governing spec now targets `buoy_search`, `buoy`, and `BUOY_EMBEDDING_PRECISION` with the 0.2 legacy environment contract.
- 2026-07-14: Buoy release integration closed with pass review; this ticket is unblocked and remains separately executable after the rebrand plan.

## Blockers

- None.
