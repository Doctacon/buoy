Status: done
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: None

# C2: Research Code-Aware Embedding Candidate

## Scope

Perform read-only feasibility research for at most one primary and one fallback open-source/local code-aware embedding candidate. Do not preselect a model. Use authoritative model repositories and current Buoy source/dependencies to determine whether a candidate can fit the existing experiment boundary.

## Acceptance criteria

- For each retained candidate, record OSI license evidence, immutable model revision, SentenceTransformer compatibility, query/document prefixes, pooling and normalization contract, vector dimension, maximum input, model/download size, expected disk/RAM/device needs, whether remote code is required, and telemetry/offline controls.
- Prefer a 384-dimensional candidate that works through the installed `sentence-transformers` path and does not require `trust_remote_code`.
- Record current compatibility boundaries: 384-dimensional content/catalog vectors, current default `BAAI/bge-small-en-v1.5`, and automatic routing/catalog implications.
- Provide at most one primary and one fallback with an evidence-backed compatibility/cost table; do not imply user approval of either.
- Produce `.10x/research/2026-07-19-code-aware-embedding-candidate.md` as the research output.

## Stop conditions

- If no credible 384-dimensional candidate meets the local/open-source/no-remote-code boundary, stop C4 and request a separate decision on dynamic content-vector dimensions. Do not widen this work into a catalog/routing dimension migration.
- Reject proprietary APIs, unclear/non-open licenses, mutable-only model references, and candidates requiring unreviewed remote code.
- Do not download/install a model or dependency, load model weights, run inference, read credentials, call a live service, or mutate source/tests/lockfiles.

## Evidence expectations

Authoritative URLs/revisions, inspected current source paths, compatibility table, explicit unknowns, and a no-download/no-live-call statement.

## Blockers

None. Independent review passed repaired PR #58 head `7ec84b628bbc043453f12a9da4db151a4d1cdb7f`.

## Explicit exclusions

Model download/inference; benchmark execution; dependency/source/test changes; public CLI or plan surface; namespace writes; catalog/default changes; candidate promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `.10x/research/2026-07-19-code-aware-embedding-candidate.md`
- `.10x/evidence/2026-07-19-code-aware-embedding-feasibility-research.md`
- `.10x/reviews/2026-07-20-code-aware-embedding-candidate-review.md`
- `.10x/tickets/done/2026-07-20-shape-dynamic-content-vector-dimensions.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/apply.py`
- `src/buoy_search/catalog.py`
- `src/buoy_search/plan_artifacts.py`

## Progress and notes

- 2026-07-19: Opened as an independent read-only research child. No model identity, revision, budget, or download was ratified during decomposition.
- 2026-07-19: Completed authoritative read-only screening. No credible native 384-dimensional candidate met all open-source/local/SentenceTransformer/no-remote-code constraints. Retained only `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52` as a dynamic-dimension decision candidate, not as C4-compatible or approved; no fallback retained. Research: `.10x/research/2026-07-19-code-aware-embedding-candidate.md`; evidence: `.10x/evidence/2026-07-19-code-aware-embedding-feasibility-research.md`.
- 2026-07-19: C4 must remain blocked under its 384-dimensional stop condition. This ticket remains active pending independent review; no model/dependency download/install, model load, inference, credentials, source/test/lockfile mutation, namespace/catalog operation, or live service call occurred.
- 2026-07-20: Repaired independent-review completeness findings by reproducing and dispositioning the full 14-result discovery roster. Fully screened `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` and retained it as the fallback dynamic-dimension decision candidate: authoritative Apache-2.0, standard SentenceTransformer/no remote code, single 768-dimensional CLS vector, no prefix, 1,024-token maximum, and 611,525,163 listed bytes. It remains incompatible with C4's exact 384-dimensional contract.
- 2026-07-20: Qualified Nomic resources: current construct-then-`.half()` initialization requires more than 26.34 GiB float32 weights plus overhead; 24 GiB applies only after separately authorized direct-half/loading plumbing. C2 remains active pending a new independent review. C4 remains stopped; no model/dependency download/install, model load, inference, source/test/lockfile mutation, namespace/catalog operation, credential access, or Buoy live service call occurred.
- 2026-07-20: Independent review passed repaired PR #58 head `7ec84b6`. C2 closed with the complete 14-model screen, no credible native 384-dimensional candidate, the 3,584-dimensional Nomic primary and 768-dimensional Crow-Plus fallback retained only for a later decision, and C4 still blocked under its stop condition.
- 2026-07-20: The user explicitly approved separate shaping for dynamic content-vector dimensions. That shaping is owned by `.10x/tickets/done/2026-07-20-shape-dynamic-content-vector-dimensions.md`; it does not activate behavior, authorize either model, or authorize downloads, source changes, model loading, inference, namespace/card/catalog writes, or default changes.

## Closure mapping

- **Retained-candidate contract:** The research compatibility/cost table and evidence record map each retained model to immutable revision, OSI license, SentenceTransformer/remote-code boundary, prefixes, pooling, normalization, dimensions, maximum input, listed bytes, analytical resources, and pin/offline/telemetry controls.
- **384-dimensional preference and stop:** The complete contemporaneous 14-result roster plus three supplemental authoritative candidates records every disposition and supports the bounded conclusion that no credible candidate meets C4's native 384-dimensional contract. C4 therefore remains blocked and stopped.
- **Current compatibility:** The research records the fixed 384-dimensional content schema, cards, remote compatibility, and routing vectors; the unchanged `BAAI/bge-small-en-v1.5` default; and why 768/3,584 dimensions require separate shaping.
- **Bounded recommendation:** Nomic is the sole primary and Crow-Plus the sole fallback, both explicitly decision-only and C4-incompatible. No candidate was approved or promoted.
- **Required artifact and safety:** `.10x/research/2026-07-19-code-aware-embedding-candidate.md` and its evidence/source snapshot are complete. No model/dependency download or install, model load, inference, credential access, live Buoy call, source/test/lockfile mutation, or namespace/catalog operation occurred.
- **Review:** `.10x/reviews/2026-07-20-code-aware-embedding-candidate-review.md` records an independent pass at `7ec84b628bbc043453f12a9da4db151a4d1cdb7f` with no blockers.

## Retrospective

The repair showed that a bounded discovery conclusion is reviewable only when the exact contemporaneous predicate, full result roster, immutable metadata, and every disposition are preserved together; the research record and source snapshot now retain that method and result. It also exposed construct-then-cast peak memory as materially different from steady half-precision size. The separately approved dynamic-dimension shaping work has a durable owner, so C2 closes without silently expanding into architecture, implementation, downloads, or remote writes.
