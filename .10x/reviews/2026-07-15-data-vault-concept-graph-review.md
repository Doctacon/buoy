Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: 9fcb3e811297f80db61711dbe9e743017c04af5a
Verdict: concerns

# Review: Data Vault Cross-Namespace Concept Graph

## Target and method

Independently reviewed commit `9fcb3e811297f80db61711dbe9e743017c04af5a` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md`
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`
- the cited Buoy identity/provenance source
- cited upstream documentation, current open-source source files, license files, and GitHub repository metadata

The requested worktree-root `plan.md` and `progress.md` were absent. The governing `.10x` parent plan and executable ticket were available, so their absence did not require a scope assumption.

Read-only validation included the commit diff, ancestry, whitespace checks, local record/source inspection, and targeted upstream checks. In particular, current upstream source confirms Graphiti's `remove_episode` first-producing-episode behavior, GraphRAG's Parquet/source-ID/covariate fields, LlamaIndex's `triplet_source_id` and deletion primitives, and RAGFlow's asymmetric add/delete lifecycle. Current license files confirm Apache-2.0 for Cognee, Graphiti, and RAGFlow and MIT for GraphRAG and LlamaIndex. GitHub metadata confirms Kuzu is archived and MIT, Apache AGE/HugeGraph are Apache-2.0, and Neo4j is GPL-3.0. FalkorDB's repository metadata does not identify an SPDX license, supporting the record's decision not to admit it without a separate license review.

## Review

- **Correct:** Scope is bounded to research. The commit adds one research record and advances only the owning ticket from `open` to `active`; it selects no store, changes no product behavior, and performs no live mutation. This matches the ticket's research-only scope and explicit exclusions (`.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md:9-13,34-38`).
- **Correct:** Local identity claims are precise and consistent with the inspected source: the record distinguishes namespace, page/source hashes, applied `ts_*` row identity, intermediate `jf_*` chunk identity, embedding identity, plan/apply identity, and the per-namespace DuckDB ledger (`.10x/research/2026-07-15-data-vault-concept-graph.md:107-128`). This avoids promoting current structural tags or index coordinates into business identity.
- **Correct:** The comparison is unusually well bounded. It covers five open-source approaches plus proprietary Chief, names construction, retrieval, operational shape, update/deletion limits, and licenses, and distinguishes documented behavior from undocumented internals (`.10x/research/2026-07-15-data-vault-concept-graph.md:132-208`). Targeted primary-source checks support the material claims, including Graphiti deletion (`:164`), GraphRAG source-bearing tables (`:170-181`), LlamaIndex source pointers/deletion responsibility (`:185-189`), and RAGFlow regeneration after removal (`:193-195`).
- **Correct:** The Data Vault authority boundary is conservative and suitable for research. Derived candidates and assertions remain separate from imported read-only Hub/Link/Satellite references, and LLM output cannot mint, merge, or rewrite warehouse authority (`.10x/research/2026-07-15-data-vault-concept-graph.md:210-232`). The record also explicitly limits its authority because it inspected explanatory material rather than the full Data Vault 2.0 standard (`:232,469`).
- **Correct:** Provenance, contradictory assertions, temporal validity, migration, deletion, and ACL leakage are treated as first-order model concerns rather than retrieval afterthoughts. Exact evidence revisions and extraction runs are represented (`:240-270`), contradictions coexist (`:290-294`), three clocks are separated (`:296-306`), deletion walks all dependent projections (`:308-319`), and authorization precedes resolution/traversal/aggregation (`:321-335`).
- **Correct:** The record compares genuinely smaller alternatives—concept cards, inverted assignments, relational assertions, and batch community artifacts—and makes a full graph contingent on a named query workload beating those alternatives and current RRF (`.10x/research/2026-07-15-data-vault-concept-graph.md:337-379`). The relational-first/store-neutral posture is proportional and complies with the project's open-source-first constraint.
- **Correct:** The proposed eval covers all requested dimensions and adds useful safety controls: same-name false merges, evidence entailment, contradiction preservation, three temporal/lifecycle clocks, ACL canaries, stale projections, retrieval quality, latency/cost, and operational burden (`.10x/research/2026-07-15-data-vault-concept-graph.md:381-421`). The staged recommendation does not authorize an implementation or production store and has an explicit stop condition (`:433-444`).
- **Note (significant; correction required before ticket closure):** The candidate schema says assertions should be reified, but only `RelationshipAssertion` and `AliasAssertion` are actually defined as nodes. `MENTION_ASSERTION` is listed as an edge that merely says to “prefer a reified mention/assignment”; `ASSIGNED_TERM` refers to an undefined “assignment object”; and `MAPS_TO_VAULT_REF` depends on a `ResolutionAssertion` named earlier but omitted from the node table (`.10x/research/2026-07-15-data-vault-concept-graph.md:230,234-272`). This leaves mention and taxonomy/vault-resolution provenance, authority, ACL, temporal, review, and retraction fields without a coherent logical home. Correct the candidate model by defining the missing reified assertion/assignment node types (or explicitly mapping each to an existing assertion type), then make their subject/object/evidence/run/policy/lifecycle edges consistent. This is material to acceptance criterion 3 and the record's strongest recommendation at `:427`.
- **Note:** The Data Vault claims are responsibly limited but rely on one Databricks explanatory article rather than a primary formal Data Vault 2.0 authority (`.10x/research/2026-07-15-data-vault-concept-graph.md:88-103,212-232,468-469`). This does not invalidate the one-way/non-authoritative boundary, but no future loading, key, effectivity, record-source, or Business Vault behavior should derive from this record without the specialist/primary-authority review it already requires.
- **Note:** The synthetic eval is appropriate for a first experiment, but “zero observed leakage” is evidence only for the modeled principals, policies, query paths, and side channels—not proof of production noninterference. The record generally preserves this distinction by calling these candidate gates and blocking real policy semantics on ratification (`.10x/research/2026-07-15-data-vault-concept-graph.md:335,385-421,446-457`).
- **Note (status coherence):** `Status: done` on the research record while the executable ticket remains `active` is not inherently inconsistent. A temporal research artifact may be complete while its owning ticket remains active for independent review and closure reconciliation; the ticket explicitly records that intent (`.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md:1,48-51`). No correction is required solely to synchronize those statuses. The ticket should remain active until the significant schema finding above is corrected or explicitly accepted. The research record may remain `done` if “done” denotes completed investigation with reviewed limits, but its content still requires correction before the ticket can be closed.
- **Blocker:** None to preserving or reviewing this research branch. The significant schema gap blocks clean ticket closure, not the already bounded research comparison or later cross-track synthesis that treats the gap as unresolved.

## Acceptance-criterion assessment

| Ticket criterion | Assessment | Evidence |
| --- | --- | --- |
| Inspect current Buoy identity/hash/provenance and preliminary research | Satisfied | Local authority list and precise identity analysis at `.10x/research/2026-07-15-data-vault-concept-graph.md:19-31,107-128`. |
| Compare at least three open-source approaches with behavior, license, cost, updates, and retrieval | Satisfied | Five open-source approaches are individually analyzed and summarized at `:144-208`; material licenses and lifecycle claims were independently checked upstream. |
| Define candidate nodes/edges with explicit authority and provenance | Partially satisfied; correction required | Core evidence, relationship, concept, vault-reference, and extraction-run classes are strong at `:234-272`, but mention, taxonomy assignment, and vault-resolution reification are internally incomplete. |
| Analyze resolution, aliases, contradictions, time, deletion, migration, and ACL leakage | Satisfied | `.10x/research/2026-07-15-data-vault-concept-graph.md:274-335`. |
| Compare full graph with smaller alternatives | Satisfied | `.10x/research/2026-07-15-data-vault-concept-graph.md:337-379`. |
| Propose requested evals | Satisfied | `.10x/research/2026-07-15-data-vault-concept-graph.md:381-421`. |
| Recommend a bounded experiment, not implementation/store selection | Satisfied | `.10x/research/2026-07-15-data-vault-concept-graph.md:423-457`. |
| Record evidence, licenses, null findings, undocumented internals, and confidence/limits | Satisfied with residual Data Vault authority limitation | Sources and explicit limits at `.10x/research/2026-07-15-data-vault-concept-graph.md:13-103,459-471`. |

## Verdict

**Concerns.** The research is factual, appropriately licensed/caveated, proportional, and substantially satisfies the ticket. One material internal-model gap prevents a clean pass: mention, taxonomy assignment, and Vault mapping are described as reified but do not have defined assertion objects consistent with the record's own provenance/ACL/temporal requirements. Correct that model before closing the active ticket. No status-only correction is required.

## Residual risk

- Upstream default-branch behavior and licenses can change; the record is a dated screen, not a dependency or legal approval.
- Data Vault mapping remains preliminary until checked against primary/formal Data Vault 2.0 authority by a qualified practitioner.
- No framework was installed or benchmarked, and no real corpus, ACL topology, deletion SLA, extraction quality, or graph utility was measured.
- Synthetic canaries cannot exhaustively establish production side-channel noninterference.
