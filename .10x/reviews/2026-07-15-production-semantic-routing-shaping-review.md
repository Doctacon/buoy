Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commit `b5641d177d0846c2640e42d6d2e5ae54f3ec4418`
Verdict: pass

# Production Semantic Routing Shaping Review

## Target

Independent adversarial review of:

- `.10x/decisions/superseded/production-routing-local-catalog.md`;
- `.10x/specs/production-local-namespace-catalog.md`;
- `.10x/specs/approved-apply-catalog-registration.md`;
- `.10x/specs/superseded/automatic-production-namespace-routing.md`;
- the production parent plan and three sequential executable children.

The reviewer compared the records to current plan/apply locking, old-plan compatibility, source metadata, catalog experiment evidence, explicit multi-namespace retrieval, and CLI/source behavior.

## Findings and resolution

### Pending lifecycle and duplicate remote work

Initial drafts allowed an unconfirmed pending artifact to be replaced, which could repeat remote writes after an indeterminate crash. The final contract requires every confirmed or unconfirmed pending artifact to block apply rerun before model, credential, or remote work. Confirmed state uses reconciliation; unconfirmed state requires explicit approved local abandonment and warns that a later apply may use existing idempotent repeat-upsert semantics.

Pending state now binds catalog path, state root, applied-state database, site ID, namespace, plan ID, apply-resolved contracts, card/prior revisions, schema, confirmation state, and canonical hash. Reconcile/abandon require regular in-root non-symlink artifacts and exact bound catalog identity.

### Locking and apply ordering

The final contract acquires the existing namespace lock before model construction, pending mutation, credentials, remote work, state commit, confirmation, or catalog commit and retains it across the complete lifecycle. Global order is namespace lock then catalog lock. Busy contention performs no model/pending/credential/remote work.

### Plan authority and compatibility

Existing schema-v1 plan hashes remain valid. Integrity-bound plan fields remain plan authority; region and ranking defaults are explicitly apply-resolved and bound into pending/card state. Apply adds `--region`.

Source mapping is exact: verified metadata values map to repository/document kinds; absent supported legacy metadata uses canonical GitHub repository-root URL, ordinary HTTP(S), or supported `file:` identity. Metadata-free legacy document plans use verified site ID as the generated-title fallback and never treat opaque `file://<source-id>` as a filename.

### Card ownership and deterministic projection

`catalog upsert` is the sole manual semantic-edit path. Apply preserves manual semantic fields and enabled state.

The catalog spec now defines exact stable JSON hashing, passage formatting, routing-contract JSON, and golden semantic/vector hashes. Retrieval dimensions are fixed at the current 384-dimensional schema. Source kinds, filenames, aliases, tags, and contradiction failures are complete.

### CLI and routed retrieval

Catalog/apply/retrieve catalog-path precedence, empty values, JSON/stderr behavior, command syntax, route-only flag rejection, and `--include-vector` are explicit. Catalog mutations consistently support `--catalog` and `--json`.

Automatic routing retains eligibility-before-score, local-only preview, fixed pinned route model, hybrid RRF using current `RRF_K`, default top three, selected route order, and existing downstream multi-namespace RRF. Per-ranking-field CLI overrides are independent; unsupplied fields remain card-specific, while candidates/doc-kind apply per namespace and top-k remains global.

## Correct

- The decision matches every behavior explicitly selected by the user.
- The three specifications are focused, source-compatible, and regeneration-grade.
- The child graph is linear to avoid conflicting CLI/state writers.
- Every child has bounded exclusions, acceptance criteria, evidence expectations, and a separate worktree.
- No implementation, test, dependency, live service operation, or unrelated mutation occurred in shaping.
- `git diff --check` passed.

## Verdict

Pass. No execution-critical semantic or lifecycle blocker remains. The first catalog child may begin only after this shaping branch integrates into `develop` and in a later turn.

## Residual risk

- This is intentionally production implementation without a quality promotion threshold; the user will judge routing through live personal use.
- Unconfirmed crash recovery cannot know remote row state without remote inspection. The specified default blocks repeat writes until explicit local abandonment.
- Local catalog authority is single-machine/single-user; remote synchronization and ACLs require future decisions.
- Existing uncataloged remote namespaces require manual upsert or a future successful apply before routing can select them.
