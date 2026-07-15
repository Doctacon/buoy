Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit a4bfce8125aadf589e0373d2a75a8e82d630e47e
Verdict: pass

# Data Vault Namespace Catalog and Routing Re-review

## Target

Independent re-review of repair commit `a4bfce8125aadf589e0373d2a75a8e82d630e47e` against:

- owning ticket `.10x/tickets/done/2026-07-15-research-data-vault-namespace-catalog-routing.md`;
- parent plan `.10x/tickets/2026-07-15-semantic-retrieval-research-plan.md`;
- research `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md`;
- prior review `.10x/reviews/2026-07-15-data-vault-namespace-catalog-routing-review.md`; and
- the exact repair diff from `a4bfce8^` to `a4bfce8`.

The requested worktree-root `plan.md` and `progress.md` were absent, as already disclosed by the ticket and research. Their durable owning ticket and parent plan were present and inspected. The worktree was clean before this review file was created. This re-review made no live Turbopuffer call and no source, product, or external-state mutation.

## Findings

No blocker, significant, minor, or nitpick finding remains from the prior review. The repair is confined to the research and owning ticket, preserves the research-only boundary, and introduces no contradictory product semantics.

### Prior finding 1 — factual primary-source claims: resolved

- The `semantic-router` entry now identifies the repository-root license as MIT and links the license directly (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:73-79`). A fresh fetch returned HTTP 200 and began `MIT License`.
- Architecture B now distinguishes atomic upsert batches and conditional writes from the absent general-purpose transaction, relational-constraint, cross-namespace, and multi-system guarantees (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:160-170`). A fresh fetch of Turbopuffer's guarantees documentation confirmed both “All writes in an upsert are applied simultaneously” and that general-purpose read/write transactions are unsupported.

### Prior finding 2 — missing routing relationships: resolved

The candidate model now contains:

- governed concept assignment through `source_revision_concept_ref` (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:192-193`);
- explicit many-to-many source provenance through `index_revision_source_revision` (`:195-196`); and
- versioned, effective policy assignment through `index_revision_access_policy` (`:200-201`).

The access-policy lifecycle and the exact card-to-policy/source/concept joins are also stated (`:205-214`). Importantly, the repair supplies relationship shape and provenance without inventing temporal-overlap, cardinality, policy-conflict, or business-key semantics; those remain explicitly blocked. The candidate model can therefore represent the predicates required by routing steps 2 and 4 without laundering a default into the research.

### Prior finding 3 — unreproducible Data Vault citation: resolved

The dead standards URL was replaced with two accessible Data Vault Alliance sources, and their authority is narrowly qualified as publisher-hosted process/explanatory material rather than a public normative specification (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:55-64`). Fresh fetches returned HTTP 200; the overview identifies Daniel Linstedt. The record explicitly states that no accessible public normative specification was established, preserving the original conservative confidence boundary.

### Prior finding 4 — held-out evaluation: resolved

The research now requires development/held-out separation, grouped leakage prevention, frozen labels/cards/fixtures/model/code/seeds/parameters, an untouched final test slice, exact safety counts, per-query output, bootstrap confidence intervals, repeated nondeterministic runs, identical-baseline comparison, and a new untouched set after post-test tuning (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:301-305`). This closes the overfitting and uncertainty-reporting gap without expanding the proposed offline experiment into implementation.

## Correct

- The repair retains three viable architectures with explicit authority boundaries, failure modes, migration paths, and proportionate assessments (`.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:146-182`).
- The repaired model now meets the ticket's Data Vault mapping, provenance, ACL, version, and embedding-contract requirement while continuing to separate physical namespaces, governed identities, and technical revisions (`:184-214`).
- Routing remains deterministic gate-before-score, bounded, compatible, fail-closed, and non-fan-out; no repair weakens authorization or lifecycle safeguards.
- Evaluation still covers selection recall, over-selection, ACL and compatibility safety, latency, cost/load, lifecycle behavior, and final retrieval/answer quality (`:262-316`).
- The smallest experiment remains fixture-backed, offline, local/open-source, separately authorized, and explicitly not a production architecture selection (`:330-349`).
- Architecture and implementation semantics remain blocked for later authority/user ratification rather than being inferred by the repair (`:351-366`).

## Ticket acceptance

1. **Current local records/source inspected — supported.** The research names the active contracts, decisions, completed tickets, relevant source, and documentation inspected; the prior independent review spot-checked the resulting local observations, and this repair does not alter them.
2. **Official Turbopuffer and primary/open-source examples — supported.** The two incorrect claims are corrected and freshly reproduced; the Data Vault source limit is now explicit and reproducible.
3. **At least two viable architectures — supported.** Three architectures retain authority boundaries, failure modes, migration paths, and bounded assessments.
4. **Candidate catalog model — supported.** The repaired relationships close the sole structural gap while retaining Data Vault, provenance, ACL, version, and embedding-contract fields.
5. **Routing, compatibility, fallback, non-goals — supported.** These sections are unchanged and were accepted by the prior review.
6. **Offline eval cases and metrics — supported.** The prior metric coverage remains, now with a credible held-out and uncertainty protocol.
7. **No-live test boundary — supported.** Testable offline claims and unmeasured live claims remain explicitly separated (`:307-316`).
8. **Smallest experiment, not implementation — supported.** The proposal remains local, fixture-backed, reversible, and deferred to a separately authorized ticket (`:338-349`).

Parent-plan invariants remain supported: Data Vault authority is separate from derived indexes, provenance reaches namespace/chunk identity, ACL/isolation is fail-closed, recommendations prefer self-hostable/open-source components, exact routing remains the baseline, lifecycle and cost are covered, evaluation is measurable, local source was inspected, and no live mutation occurred.

## Verdict

**Pass.** Repair commit `a4bfce8125aadf589e0373d2a75a8e82d630e47e` resolves every prior finding without regression. The owning research ticket's acceptance criteria are supported. There is no remaining review or research-ticket closure blocker.

Architecture selection and implementation remain intentionally blocked by the unresolved semantics already owned in the research record; those are downstream product-shaping gates, not blockers to accepting or closing this research ticket. This review does not itself change ticket status or perform closure.

## Residual risk

- No live Turbopuffer account/corpus was used, so account behavior, scale performance, service cost, schema drift, and end-answer gains remain unmeasured.
- Public Data Vault material remains incomplete relative to the proprietary body of knowledge; actual Raw Vault mappings still require enterprise authority.
- Repository-root license checks do not audit exact future releases, transitive dependencies, deployment editions, or security posture.
- The catalog/router is a research proposal, not an implemented ACL or routing guarantee; empirical value over exact-only routing remains to be established by a separately ratified experiment.

These limits are already disclosed by the research and do not prevent acceptance of the research deliverable.
