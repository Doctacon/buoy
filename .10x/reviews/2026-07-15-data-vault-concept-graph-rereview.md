Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: 06ba7779b4b768f03ee82adc6d990dff335a4536
Verdict: pass

# Re-review: Data Vault Cross-Namespace Concept Graph

## Target and method

Re-reviewed repair commit `06ba7779b4b768f03ee82adc6d990dff335a4536` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md`
- `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/research/2026-07-15-data-vault-concept-graph.md`
- `.10x/research/2026-07-15-metadata-tagging-graphs-and-data-vault.md`
- `.10x/reviews/2026-07-15-data-vault-concept-graph-review.md`
- `.10x/specs/explicit-multi-namespace-retrieval.md`

The requested worktree-root `plan.md` and `progress.md` were absent. The governing `.10x` parent plan, executable ticket, research record, and prior review were available, so no scope or behavioral premise had to be invented.

Read-only validation covered the complete repair diff and parent/current model text, record ancestry, whitespace, worktree state, and the authority, provenance, temporal, ACL, correction/deletion, and assertion-model implications of all three repaired assertion types.

## Review

- **Correct:** The prior significant finding is resolved. `DerivedAssertion` now gives `MentionAssertion`, `TaxonomyAssignmentAssertion`, and `VaultResolutionAssertion` one coherent logical contract for immutable opaque identity, typed subject/object roles, exact evidence support, extraction-run provenance, policy/security partition, three-clock temporal state, governed review, and retraction/supersession (`.10x/research/2026-07-15-data-vault-concept-graph.md:238-248`). The model explicitly remains storage-neutral rather than weakening that contract into optional edge properties (`:271-288`).
- **Correct:** `MentionAssertion` has a precise evidence-to-candidate endpoint contract, source span/normalization fields, mandatory support by the subject revision, and deterministic retraction when that revision is deleted (`.10x/research/2026-07-15-data-vault-concept-graph.md:261`). Its optional convenience edge must mirror `ASSERTS_SUBJECT` and carries no independent authority (`:280`).
- **Correct:** `TaxonomyAssignmentAssertion` keeps inferred assignment separate from the imported governed taxonomy term. It supports evidence-, candidate-, or concept-level subjects, requires exact evidence/run provenance through the common contract, and handles taxonomy migration by creating and superseding assertions rather than mutating term authority (`.10x/research/2026-07-15-data-vault-concept-graph.md:262,266,278-281,322-329`).
- **Correct:** `VaultResolutionAssertion` defines kind-specific endpoint pairs for Hub, Link, and Observation references. Imported Vault objects remain read-only authority; approval activates only a derived mapping projection, and approval, correction, retraction, or deletion cannot create, ratify, merge, or mutate a Hub, Link, Observation, key, or warehouse relationship (`.10x/research/2026-07-15-data-vault-concept-graph.md:220-232,263,267,282,329`). This is consistent with the ticket's prohibition on creating Vault authority from LLM output (`.10x/tickets/done/2026-07-15-research-data-vault-concept-graph.md:34-38`).
- **Correct:** Provenance is complete at the logical-model level: every machine assertion requires exact `SUPPORTED_BY` evidence and exactly one `DERIVED_FROM_RUN`; optional mention, taxonomy, and Vault convenience edges mirror the assertion role edges and cannot replace the reified record (`.10x/research/2026-07-15-data-vault-concept-graph.md:243-244,277-288`). A manual-assertion provenance contract is explicitly left undefined and therefore not silently authorized (`:244`).
- **Correct:** Temporal and lifecycle behavior is internally consistent. Event validity, system knowledge time, and index revision time remain distinct; corrections produce new IDs linked by `SUPERSEDED_BY`; deletion retracts support, recomputes visibility, invalidates derived projections, and preserves only policy-permitted audit lineage (`.10x/research/2026-07-15-data-vault-concept-graph.md:242-248,312-335`).
- **Correct:** ACL behavior remains conservative. Assertion visibility intersects assertion policy with valid support; authorization precedes resolution and traversal; hidden items cannot influence expansion, aggregation, ranking, or summaries; and revocation invalidates all named projection families (`.10x/research/2026-07-15-data-vault-concept-graph.md:278,337-351`). The three repaired assertion types inherit these controls rather than defining weaker subtype-specific paths.
- **Correct:** The repair does not regress the broader research. Commit `06ba777` changes only the candidate assertion model and the owning ticket's append-only progress note; it selects no store, changes no product behavior, and remains within the research-only scope. The branch still descends from the recorded `develop` base, and `git diff --check 06ba777^ 06ba777` passes.
- **Note:** The pre-existing Data Vault authority limit remains explicit: the research used explanatory material rather than the full formal Data Vault 2.0 standard, so loading, key, effectivity, record-source, and Business Vault behavior still requires specialist/primary-authority review before implementation (`.10x/research/2026-07-15-data-vault-concept-graph.md:232,481`). This is a declared implementation blocker/limit, not a defect in the repaired derived-assertion model.
- **Note:** Synthetic zero-observed-leakage gates cannot prove production noninterference beyond the modeled principals, policies, query paths, and side channels. The research correctly keeps exact ACL policy, deletion SLA, and side-channel semantics blocked on later synthesis and ratification (`.10x/research/2026-07-15-data-vault-concept-graph.md:407-423,463-474`).
- **Blocker:** None.

## Prior-finding disposition

| Prior finding | Disposition | Evidence |
| --- | --- | --- |
| Missing coherent reified mention assertion | Resolved | Common contract at `.10x/research/2026-07-15-data-vault-concept-graph.md:238-248`; subtype and mirror edge at `:261,280`. |
| Undefined taxonomy assignment object | Resolved | `TaxonomyAssignmentAssertion` authority/endpoints/migration at `:262,266`; support/run and edge contract at `:278-281`. |
| Undefined Vault resolution assertion | Resolved | One-way authority boundary at `:220-232`; kind-specific subtype and projection constraints at `:263,267,282,329`. |

## Verdict

**Pass.** Repair commit `06ba777` resolves the prior significant model gap without widening scope or weakening authority, provenance, temporal, ACL, correction/deletion, or general assertion invariants. The concept-graph research now satisfies the ticket's candidate node/edge authority-and-provenance criterion. No blocker remains from this review.

## Residual risk

- Data Vault mapping remains preliminary until reviewed against primary/formal Data Vault 2.0 authority by a qualified practitioner.
- No framework, physical schema, real corpus, ACL topology, deletion SLA, extraction quality, or graph utility was implemented or measured; the record correctly leaves those for separately ratified work.
- Synthetic ACL canaries provide bounded evidence, not exhaustive production side-channel proof.
