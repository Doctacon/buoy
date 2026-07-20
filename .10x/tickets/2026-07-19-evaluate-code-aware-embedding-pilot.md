Status: blocked
Created: 2026-07-19
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md, .10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md

# C4: Evaluate Code-Aware Embedding Pilot

## Scope

Conditionally add the minimum experiment-only model-selection plumbing and run an isolated paired code-aware embedding pilot. Compare the C2 candidate against `BAAI/bge-small-en-v1.5` using identical source commits, selected files, fixed-line chunks, BM25 configuration, and current final ranking.

Pilot repositories are Buoy, pytest, and Ruff. Candidate and paired baseline use new namespace patterns only; exact names, rows, writes, model contract, and resource needs must come from C1/C2/local plan evidence rather than this ticket.

## Acceptance criteria

- C2 identifies a revision-pinned, open-source/local, 384-dimensional candidate compatible with the existing local model path and no remote code.
- Any plumbing is the smallest experiment-only mechanism, preserves the default model, validates exactly 384 dimensions before any write/query, and records model revision/prefix/pooling/normalization/precision in plans/evidence.
- A supported public CLI/config/catalog model selector is not implied; any such surface requires separate ratification.
- Candidate and baseline plans use identical source commits/corpora/chunks and report exact rows, new namespaces, writes, model bytes, disk/RAM/device estimate, and embedding work before approval.
- New namespaces only; zero stale/namespace deletes; no existing namespace mutation; no catalog/default change.
- Primary metrics are per-repo score and P@5. Report NDCG@10, Recall@10, MRR@10, per-query deltas, embedding throughput, query p50/p95, model disk/RAM, and rows/storage without inventing pass thresholds for unratified budgets.
- Pilot experiment-escalation gate: no pilot repo score or P@5 regression, positive average score, and at least two of three repos improve. Passing permits only a request for separately approved full-basket experimentation; this three-repo rule is not active promotion policy or promotion authority.
- Full-basket expansion requires a new exact ten-repo row/write forecast and separate approval. Only the full-basket keep gate is governed by the active distribution policy. Passing means promotion-candidate evidence only.
- Source changes, if authorized, have focused/full tests and wrong-dimension failure coverage before remote writes.

## Approval gate

C2 is complete but found no candidate satisfying this ticket's exact 384-dimensional condition, so this checkpoint cannot currently be filled. If that stop condition is ever superseded through separately ratified behavior, the separate Buoy contract correction/baseline requirements and local plans must also be complete before asking:

> Approve download of pinned open-source model `<model>@<revision>` (`<bytes>`, `<RAM/device estimate>`) and up to `<rows>/<new namespaces>/<estimated writes>` for the Buoy/pytest/Ruff paired pilot, with zero deletes and no catalog/default change?

The approval must separately cover the model download and remote writes. Prior model/namespace approvals do not carry forward.

## Stop conditions

- Stop if C2 finds no compatible 384-dimensional candidate; do not widen into dynamic vector dimensions, routing-model changes, or catalog schema migration.
- Stop before download/write on absent approval or incomplete exact estimates.
- Stop on dimension/model-contract incompatibility, failed pilot gate, unapproved resource use, or observed use exceeding the approved bound.
- Stop before full expansion until its exact incremental forecast is separately approved.

## Evidence expectations

Approval provenance, pinned model/license contract, local plans/preflights, exact writes/deletes, paired compatibility, metrics/resources, tests, review, and explicit no-promotion conclusion.

## Blockers

- C2 is complete and found no credible native 384-dimensional code-aware candidate satisfying the open-source/local/SentenceTransformer/no-remote-code boundary. Its 3,584-dimensional primary and 768-dimensional fallback remain decision candidates only, so C4 is stopped under its existing condition.
- The user's approval to shape dynamic content-vector dimensions is separately owned by `.10x/tickets/2026-07-20-shape-dynamic-content-vector-dimensions.md`. It does not supersede this ticket, make either candidate C4-compatible, or authorize C4 execution.
- The separately owned Buoy judgment removal/rehash is complete, but Buoy remains insufficient pending an approved and verified compatible same-source baseline.
- No model/download/resource/new-namespace approval exists.

## Explicit exclusions

Dynamic vector dimensions; default model/ranking changes; routing/catalog migration or mutation; baseline namespace mutation/deletion; proprietary APIs; automatic promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md`
- `.10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md`
- `.10x/research/2026-07-19-code-aware-embedding-candidate.md`
- `.10x/evidence/2026-07-19-code-aware-embedding-feasibility-research.md`
- `.10x/reviews/2026-07-20-code-aware-embedding-candidate-review.md`
- `.10x/tickets/2026-07-20-shape-dynamic-content-vector-dimensions.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened blocked. No model identity, budget, surface, download, namespace, source, test, or promotion was authorized or created.
- 2026-07-20: Clarified that the three-repo rule is an experiment escalation gate only, not active promotion policy.
- 2026-07-20: C1 closed with Buoy explicitly insufficient. C4 remains blocked on the separate Buoy correction/baseline work, C2, and exact model/resource/write approval; no download or namespace operation was authorized.
- 2026-07-20: C2's repaired complete 14-model screen passed independent review at `7ec84b6` and closed with no credible native 384-dimensional candidate. C4 remains blocked and stopped; Nomic at 3,584 dimensions and Crow-Plus at 768 dimensions cannot enter this ticket.
- 2026-07-20: The user explicitly approved separate dynamic content-vector dimension shaping. That open shaping owner does not unblock or widen C4, activate behavior, approve a model, or authorize downloads, source changes, model loading, inference, namespace/card/catalog writes, or defaults.
- 2026-07-20: The separate Buoy judgment-removal/rehash owner closed after review, but baseline approval/compatibility remains unresolved. C4 also remains stopped on C2's native 384-dimensional condition; dynamic-dimension shaping ownership is unchanged.
