Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: repair commit `0cb3b41df9c27efe4d462e792fbd91acb660513b`; three active pilot specs; parent plan; five child tickets
Verdict: pass

# Semantic Routing Offline Pilot Shaping Re-review

## Target and method

Re-reviewed the exact `0cb3b41^..0cb3b41` repair diff against:

- the original fail review at `.10x/reviews/2026-07-15-semantic-routing-offline-pilot-shaping-review.md`;
- all three active pilot specs;
- the parent plan and all five current child tickets;
- the user-approved direction in `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`;
- the active Data Vault scope decision, namespace-ranking decision, and explicit multi-namespace retrieval spec;
- the four focused 2026-07-15 research records and preliminary synthesis; and
- current compatibility/RRF source and tests at `src/buoy_search/config.py:14-18`, `src/buoy_search/retriever.py:18-31,429-524`, and `tests/test_multi_namespace_retrieval.py:71-112`.

The worktree was clean at `0cb3b41` before this review file was created. The repair changes only the three specs and ticket graph named by the failed review; it changes no product source, test, dependency, or external state. `git diff --check 0cb3b41^ 0cb3b41` passed.

## Review

### Correct

- The focused catalog, taxonomy, and evaluator boundaries remain coherent, the parent remains explicitly non-executable, and Data Vault, graph, live-service, production-store, and architecture-promotion work remains excluded (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:9-13,54-65`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:193-202`).
- Source compatibility claims match current code: precision is `float32|float16`, ranking profile is `none|repo_code`, live multi-namespace compatibility includes region/model/precision, and downstream RRF is `1/(60+rank)` with namespace-order/source-rank/row-ID ties (`src/buoy_search/config.py:14-18`; `src/buoy_search/retriever.py:28-31,441-446,504-524`).
- No new semantic surface or scope creep was introduced. The added freeze child is a control boundary required by the failed review, not a new product capability.

### Fixed

1. **Critical provenance classification — resolved.** Each spec now separates user-ratified direction, record/source-backed invariants, synthetic pilot-only mechanics, and unresolved production semantics (`.10x/specs/superseded/controlled-taxonomy-pilot.md:13-32`; `.10x/specs/superseded/semantic-namespace-catalog-pilot.md:13-32`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:13-33`). The parent and every child carry matching compact provenance, and all children remain blocked until this re-review is accepted (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:24-40,63-65`; child ticket provenance/blocker sections).

2. **Taxonomy normalization and global collisions — resolved.** NFKC, Unicode casefolding, non-alphanumeric run replacement, whitespace collapse, trimming, token-boundary matching, examples, global label/synonym uniqueness, overlap/repetition behavior, and deterministic phrase/term ordering are all regeneration-grade (`.10x/specs/superseded/controlled-taxonomy-pilot.md:47-95`). The global-collision and punctuation/Unicode scenarios make the original contradictory identity contract testable (`:107-135`).

3. **Revision coherence and compatibility domains — resolved.** The catalog binds its taxonomy revision to the loaded taxonomy, validates tags against it, canonically sorts tag IDs, and includes catalog/taxonomy/namespace/revision identity on cards (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:34-65,96-116`). The complete exact-gated tuple now includes region, model, dimensions, precision, schema version, and ranking profile, with closed precision/profile/source-kind domains grounded in current source (`:42-63,84-94`). Removal of the evidence-tag arm eliminates the prior unbound tagged-evidence revision problem.

4. **Vector/config validation and routing algorithms — resolved.** Positive route/evidence limits and fixed `rrf_k=60` are configuration inputs; cases carry the complete compatibility tuple and validated labels; vectors reject empty, wrong-dimension, boolean, non-finite, and zero-norm values before evaluation (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:35-69`). Exact and semantic ranks have deterministic ties, and hybrid route RRF now defines one-based ranks, per-strategy contributions, namespace aggregation, one-list membership, and post-fusion limiting (`:77-109`).

5. **Evidence tag filter/boost arm — resolved by removal.** The taxonomy and evaluator both state that no chunk/evidence filter or boost exists, define false exclusion through required namespaces/evidence, and exclude public tag behavior (`.10x/specs/superseded/controlled-taxonomy-pilot.md:97-105,144-150`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:134-136,200-202`). The pre-existing retrieval-tag drift remains separately owned (`.10x/specs/superseded/controlled-taxonomy-pilot.md:11`).

6. **Downstream namespace-qualified RRF — resolved.** Routed namespace order is explicitly the downstream selection order. The spec requires direct reuse or exact reproduction of `cross_namespace_rrf`, including `1/(60+one_based_source_rank)`, namespace-order/source-rank/row-ID tie order, cutoff handling, and preservation of equal row IDs across namespaces (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:117-136`). This matches current source and its duplicate-ID/tie test.

7. **Exact metrics and oracle control — resolved.** Required/acceptable/forbidden namespace sets are disjoint; required/acceptable namespaces are eligible; oracle order, membership, uniqueness, and limit are validated; required evidence is namespace-qualified and non-empty (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:46-59,81-83`). Every requested metric has a formula and denominator rule, aggregates are macro rather than micro, safety counts remain visible, and fixed oracle/exact/semantic/hybrid ordering separates downstream cached-retrieval loss from automatic-routing loss (`:138-152`). Canonical case/strategy/rank ordering and exact JSON serialization make byte-level comparison auditable (`:170-180`).

8. **Auditable freeze boundary — resolved.** A separate freeze child owns source-grouped splits, fixture/card/vector/evidence/label/config inputs, the implementation pin, SHA-256 manifest, preregistration, and independent review; the run child may only verify and execute those frozen inputs (`.10x/tickets/cancelled/2026-07-15-freeze-offline-semantic-routing-fixture.md:9-23,38-48`; `.10x/tickets/cancelled/2026-07-15-run-offline-semantic-routing-pilot.md:9-24,30-45`). Any edit invalidates the freeze and requires a new manifest/review, and claims are explicitly limited to synthetic deterministic plumbing evidence (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:154-168`).

9. **Dependency graph and ACL ownership — resolved.** The graph is now linear and integration-safe: taxonomy → catalog → evaluator → freeze → run (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:42-52` and each child `Depends-On`). Catalog owns group validation, authorization, compatibility, and integrated taxonomy references; evaluator owns the highest-relevance/exact-match unauthorized canary. Taxonomy retains only the structural invariant that matching cannot become authorization (`.10x/specs/superseded/controlled-taxonomy-pilot.md:97-105,133-141`; `.10x/specs/superseded/semantic-namespace-catalog-pilot.md:67-82,122-137`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:71-75,182-197`).

10. **Synthetic groups, leakage, and no-network tests — resolved.** Group syntax, lowercase/case-sensitive semantics, duplicate rejection, empty-principal behavior, public/private contradictions, and exact overlap are defined (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:67-82`). Adversarial unauthorized ID/title/tag/high-relevance canaries and redacted internal safety output cover metadata leakage (`:80-82,122-137`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:71-75,182-197`). Fail-fast sentinels cover sockets/network, credentials, model construction/download, Turbopuffer SDK construction, live retrieval/write, and persistence outside temporary paths (`.10x/specs/superseded/semantic-namespace-catalog-pilot.md:133-138`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:193-198`).

### Blocker

None remains in the shaping semantics. A cold-start executor can implement the first child without inventing product behavior, and downstream children have explicit, correctly ordered integration dependencies.

### Note

All five child records still have `Status: blocked` because this review was expressly forbidden from editing tickets. After this pass is reconciled into the ticket graph, the taxonomy child has no remaining substantive blocker; the other children should remain blocked only on their declared predecessor integrations. Production semantics, real ACLs, real routing quality, thresholds, and architecture promotion remain intentionally out of scope rather than execution gaps in this synthetic pilot.

## Verdict

**Pass.** Repair commit `0cb3b41df9c27efe4d462e792fbd91acb660513b` resolves every critical, significant, and minor finding from the original shaping review without weakening safety boundaries or introducing scope creep. No semantic execution blocker remains. The only immediate administrative gate is reconciling this pass into the still-blocked child ticket statuses; normal downstream dependency blockers then remain by design.
