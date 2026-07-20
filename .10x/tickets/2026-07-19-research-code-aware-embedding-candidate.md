Status: open
Created: 2026-07-19
Updated: 2026-07-19
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

None. This child is executable as read-only research only.

## Explicit exclusions

Model download/inference; benchmark execution; dependency/source/test changes; public CLI or plan surface; namespace writes; catalog/default changes; candidate promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/apply.py`
- `src/buoy_search/catalog.py`
- `src/buoy_search/plan_artifacts.py`

## Progress and notes

- 2026-07-19: Opened as an independent read-only research child. No model identity, revision, budget, or download was ratified during decomposition.
