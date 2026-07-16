Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit 763107cab7165174e220b69c6ed1d88d69ee78c0
Verdict: concerns

# Data Vault Namespace Catalog and Routing Review

## Target

Independent adversarial review of commit `763107cab7165174e220b69c6ed1d88d69ee78c0` against:

- `.10x/tickets/done/2026-07-15-research-data-vault-namespace-catalog-routing.md`;
- parent `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`;
- the active specifications, decisions, preliminary research, completed tickets, source, and documentation named by the research record; and
- spot checks of official Turbopuffer documentation and primary open-source repository metadata.

The requested worktree-root `plan.md` and `progress.md` were absent at review time, consistent with the research record's source-availability note. The durable owning ticket and parent plan were present. This review made no live Turbopuffer call, source-data mutation, or external-state change.

## Findings

### Significant — Two primary-source claims are factually wrong

Locations: `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:73-77`, `:158-168`.

1. The record labels Aurelio Labs `semantic-router` as Apache-2.0. The repository's current `LICENSE`, README license badge, and GitHub repository metadata all identify **MIT**. The project remains permissively open source, so this does not reverse the open-source recommendation, but it contradicts the record's claim that the listed licenses were observed at project roots.
2. Architecture B lists “no documented ... multi-document transaction” as a Turbopuffer failure mode. Official Turbopuffer guarantees explicitly document **Atomic Batches: all writes in an upsert are applied simultaneously**, as well as atomic conditional writes. The narrower defensible statement is that Turbopuffer does not provide general-purpose read/write transactions or relational constraints; the current wording overstates a limitation and makes the architecture comparison less reliable.

Primary-source evidence spot-checked:

- `https://raw.githubusercontent.com/aurelio-labs/semantic-router/HEAD/LICENSE` begins `MIT License`; GitHub API reports SPDX `MIT`.
- `https://turbopuffer.com/docs-md/guarantees.md` states “Atomic Batches. All writes in an upsert are applied simultaneously” and separately says general-purpose read-write transactions are unsupported.

Resolution required before treating the research as accepted: correct both claims and narrow Architecture B's failure analysis to the transaction semantics Turbopuffer actually lacks.

### Significant — The candidate model cannot represent relationships required by its own routing flow

Locations: `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:182-207`, `:224-236`.

The table defines `access_policy_ref` and `business_concept_ref` as standalone entities, but no field or relationship attaches either one to an `index_revision`, `namespace_card_revision`, source, or effective interval. Likewise, `index_revision` names an opaque “source revision set” instead of a modeled many-to-many relationship. Yet routing steps 2 and 4 require the catalog to determine the current policy for a revision and narrow by governed concept/source keys, and the access-policy lifecycle text requires a versioned effective relationship.

This is more than omitted SQL detail: the candidate model, as written, cannot express the ACL, concept assignment, effective history, or multi-source provenance predicates that the proposed router depends on. The record correctly refuses to invent policy semantics, but it still needs candidate relationship shapes and authority/effective-time fields without choosing those semantics. Consequently the ticket criterion to provide a candidate catalog model with Data Vault mapping, provenance, ACL, version, and embedding-contract fields is only partially met.

### Minor — The closest claimed Data Vault standards citation is not reproducible

Locations: `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:54-62`, `:355-363`.

`https://datavaultalliance.com/news/dv/standards-specifications/` returned HTTP 404 during independent review. No archived revision, retrieval artifact, quoted standard text, publication identifier, or version accompanies it. The record appropriately limits confidence and relies on additional explanatory sources for Hub/Link/Satellite claims, so this does not invalidate its conservative authority boundary. It does mean the “closest inspected standards authority” cannot currently be independently checked and falls short of the ticket's source/version reproducibility expectation.

### Minor — The proposed routing experiment lacks a held-out evaluation protocol

Locations: `.10x/research/2026-07-15-data-vault-namespace-catalog-routing.md:255-303`, `:315-336`.

The dataset slices, baselines, safety metrics, final-quality metrics, and no-live boundary are strong. However, semantic cards, top-K, thresholds, and routing variants could all be selected on the same 20–50-revision fixture used to report promotion results. The record requires predeclared gates but does not require a development/test split, frozen card/model versions, repeated runs where nondeterministic components exist, or confidence intervals. This leaves material overfitting risk for the proposed “beats exact-only” decision. A small experiment can remain small while reserving held-out queries and reporting uncertainty.

## Correct

- **Authority boundaries are conservative and substantially correct.** The record separates physical namespace address, governed source identity, governed Data Vault business concepts, and technical indexed revisions (`:115-126`); it explicitly prevents namespace text, vector content, or inferred concepts from minting Raw Vault authority; and Architecture C remains blocked unless an enterprise Raw Vault, business keys, loading rules, and owner exist (`:170-180`).
- **Official Turbopuffer behavior is otherwise accurately characterized.** Spot checks confirmed namespace-local queries and same-namespace multi-query, isolated namespace containers, identifier-only namespace listing, metadata fields, unlimited/250M+ namespace claims, schema dimensional consistency, application-filtered row/document permissions, and the explicit empty-permission-means-no-access warning. The record correctly distinguishes client-generated embedding semantics from remotely observable vector shape.
- **Open-source posture is proportionate despite the license error.** Canonical authority is recommended in self-hosted PostgreSQL or local SQLite/DuckDB; DataHub, OpenMetadata, OpenLineage, Marquez, LlamaIndex, Haystack, and `semantic-router` are all open source according to primary repository metadata; no proprietary managed catalog is selected. Turbopuffer is limited to an optional disposable derived card index, and the smallest experiment uses local fixtures and local/precomputed vectors.
- **ACL design is fail-closed.** Authorization precedes semantic scoring, unauthorized card metadata is treated as sensitive, namespace-local enforcement is required again, stale policy/card versions fail closed, and ACL violations have a zero-tolerance eval target (`:91-97`, `:202-207`, `:228-244`, `:259-292`). The unresolved principal/group/public/policy contract is correctly blocked rather than invented.
- **History and deletion are treated as separate governed concerns.** Rename, reindex, model migration, stale sources, policy changes, remote deletion, routing tombstones, catalog history, and privacy erasure are distinguished (`:200-207`, `:338-353`). The record also correctly observes that compact applied state and immediately cleaned plan artifacts cannot provide complete historical revision lineage.
- **Recommendation proportionality is good.** Three architectures are compared; the recommendation is only a hypothesis for a fixture-backed offline experiment, not a production selection. It avoids a catalog platform, service, live write, or Data Vault loading architecture until evidence and semantic ratification exist.

## Criterion assessment

### Owning ticket acceptance

1. **Inspect current namespace discovery, retrieval, artifacts, state, decisions/specs — met.** The named records and source support the local observations; source spot checks confirmed single embedding, shared region/model/precision, sequential retrieval, all-or-nothing failure, namespace-qualified RRF, compact per-namespace current state, and ephemeral successful plan artifacts.
2. **Use official Turbopuffer documentation and primary/open-source examples — partially met.** The breadth is adequate and most spot checks pass, but the `semantic-router` license is wrong, the Turbopuffer transaction statement is overbroad, and the claimed Data Vault standards URL is dead and unpinned.
3. **At least two viable architectures, authority boundaries, failure modes, migration paths — met with correction required.** Three are present and appropriately bounded; Architecture B's transaction failure mode must be corrected.
4. **Candidate catalog model with Data Vault mapping, provenance, ACL, version, embedding fields — not fully met.** Entity fields are broad, but missing policy/concept/source-revision relationship shapes prevent the model from executing its own predicates and history rules.
5. **Routing flow, compatibility, fallback, non-goals — met.** The flow is bounded, gate-before-score, revalidated, auditable, and explicitly avoids all-namespace fallback.
6. **Offline evals for recall, over-selection, latency, cost, ACL, answer quality — met with minor concern.** Required cases and metrics are present; held-out evaluation and uncertainty reporting should be added before promotion evidence is trusted.
7. **State what is testable without live Turbopuffer — met.** Offline and unmeasured live-only claims are clearly separated.
8. **Recommend the smallest experiment, not implementation — met.** The recommendation is local, fixture-backed, reversible, and explicitly separately authorized.

### Parent-plan shared invariants

The record meets the parent invariants for Data Vault/vector authority separation, chunk-level provenance, ACL/isolation analysis, self-hostable alternatives, comparison against exact metadata/vector-only routing, lifecycle/cost/reprocessing discussion, measurable evals, local inspection, and no live mutation. The two significant findings prevent an unqualified acceptance of the child research record, but they do not indicate architecture implementation or scope widening.

## Verdict

**Concerns.** Commit `763107cab7165174e220b69c6ed1d88d69ee78c0` is well scoped, conservative, and mostly evidence-backed, but ticket acceptance is not yet complete. The two factual errors require correction, and the candidate catalog needs explicit policy/concept/source-revision relationship shapes before it satisfies the catalog-model criterion. No blocker requires abandoning the recommended offline experiment or changing the authority boundary.

## Residual risk

- No live Turbopuffer account or corpus was used, so latency, filter behavior at Buoy scale, schema drift, service cost, and end-answer gains remain unmeasured.
- Public Data Vault material remains incomplete relative to the full proprietary Data Vault 2.0 body of knowledge; any actual Raw Vault mapping still requires enterprise business-key and loading authority.
- Exact project releases, commit SHAs, transitive licenses, deployment editions, and security posture were not pinned or audited; repository-root license checks establish only current top-level licensing.
- ACL safety remains a proposed invariant, not an implemented guarantee. Current Buoy rows lack the proposed governed policy and indexed-revision identifiers.
- The recommended relational/card design still needs empirical evidence that semantic cards add value over exact taxonomy/source routing without unsafe or costly over-selection.
