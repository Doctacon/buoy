Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Approved Apply Catalog Registration

## Purpose and scope

Register or refresh one local production namespace card as part of successful approved apply while preventing remote writes from beginning when card generation/vector preparation is already known to fail.

This specification extends the current plan/apply workflow and is governed by `.10x/specs/production-local-namespace-catalog.md` and `.10x/decisions/production-routing-local-catalog.md`.

## Plan metadata

Catalog registration MUST preserve existing schema-version-1 plan compatibility rather than add required plan fields.

Verified plan authority is limited to fields already integrity-bound there: source URI/base URL, site ID, namespace, plan ID, embedding model, embedding precision (default `float32` for older supported plans), plan schema version, and page/chunk source metadata when present.

Apply MUST add `--region REGION` with the same override meaning as namespace discovery/retrieval. Apply resolves additional system fields at execution time:

- region from explicit apply `--region`, otherwise `TURBOPUFFER_REGION`, otherwise current default;
- vector dimensions as the current fixed schema value 384;
- ranking mode/profile/pool/aggregation from `ranking_defaults_for_namespace(namespace)` at apply time.

These apply-resolved values MUST be included in preflight output, pending-artifact integrity, and the committed card. They are not falsely described as verified-plan fields.

Source mapping MUST follow the complete table and contradiction rules in the catalog specification. Existing schema-v1 plans without source metadata use verified `base_url`: a valid `github.com/<owner>/<repo>` repository root becomes `github_repo` with full name from the URL; other HTTP(S) becomes `website`; and supported canonical `file://<source-id>` or current source-backed `pdf://<source-id>` document plans become `document`. A PDF filename comes only from verified `pdf_filename`, never the opaque URI. This preserves old-plan approved apply without guessing from namespace ID. An unsupported or contradictory URI remains an existing plan-verification error rather than a catalog-only reinterpretation.

`catalog upsert` is the sole manual semantic-edit path. Plan/apply add no catalog-title/summary/alias/tag flags. Apply always uses preserved existing manual semantics or deterministic generated defaults.

Plan remains local/dry-run: it MUST NOT load the routing model, mutate the catalog, read credentials, or contact Turbopuffer. Its summary MUST preview generated versus existing-manual-preserving registration using available verified metadata.

## Approved apply phases

When `apply --approve` runs, catalog registration MUST follow this order.

### 1. Verify plan/state/catalog and acquire the existing namespace lock

Use the existing verified-plan and state-diff checks. Resolve catalog path in exact precedence: apply `--catalog`, `BUOY_CATALOG_PATH`, then resolved state-root catalog. Load and validate existing catalog before credential lookup.

Approved apply MUST acquire the existing non-blocking `(site_id, namespace)` applied-state lock before catalog model construction, vector embedding, pending mutation, credential lookup, client construction, or remote writes. Refactor the current apply orchestration so the same lock remains held through pending creation, remote work, applied-state commit, pending confirmation, and catalog commit; nested acquisition is forbidden.

Global lock order is namespace lock first, then catalog lock. Reconciliation MUST use the same order. Catalog-only commands acquire only the catalog lock. No code path may acquire namespace lock while holding catalog lock.

If lock acquisition fails, perform no model, pending, credential, catalog, or remote work.

For every existing card, preserve its current enabled state through commit, including a disable concurrent with precompute. If an existing card is manual, also preserve its semantic fields; otherwise construct deterministic generated semantics.

### 2. Resolve pending collision and precompute before remote writes

The canonical pending root is `<resolved-state-root>/catalog-pending/`; it MUST be a real directory and MUST NOT be a symlink or non-directory. Pending creation MUST use that canonical directory without following a substituted parent outside the state root. The file is `<plan-id>.json`. Under the held namespace lock, inspect any existing pending path before replacement:

- a valid matching `remote_apply_confirmed=true` artifact MUST block approved apply before model/credential/remote work and print its exact reconcile command;
- a confirmed artifact whose plan/namespace/catalog/applied-state binding is mismatched or tampered MUST fail closed;
- any valid matching unconfirmed artifact MUST block approved apply before model/credential/remote work because a crash may have occurred after remote upserts; output MUST call the remote state indeterminate and provide only the explicit local abandonment command below;
- an unconfirmed mismatched/tampered artifact MUST fail closed;
- if the catalog already contains the exact confirmed card revision, apply still MUST NOT repeat remote work; reconciliation may idempotently finalize/remove the artifact.

Before reading `TURBOPUFFER_API_KEY`, constructing a Turbopuffer client, or writing remote rows:

- validate the complete prospective card;
- load the pinned local-only routing model;
- reuse or compute its normalized card vector;
- atomically create the pending registration artifact;
- bind `pending_schema_version=1`, normalized absolute catalog path, normalized state root, exact applied-state database path, site ID, namespace, plan ID, prospective card, prior catalog/card revisions, the exact prior applied plan/apply identity (or both null on first apply), apply-resolved region/ranking contract, `remote_apply_confirmed=false`, and a compact canonical payload hash;
- exclude credentials, chunk content, query text, and secrets.

A failure in this phase MUST abort with no remote or catalog mutation. The pending file MUST be atomically written and may remain for diagnosis; it MUST be marked `remote_apply_confirmed=false` and MUST NOT be reconcilable or automatically replaced.

`buoy catalog abandon-pending --pending PATH --catalog PATH --approve` is the only supported way to remove a valid unconfirmed artifact. It MUST apply the same bound-root/catalog/symlink/hash checks as reconcile, acquire the namespace lock, re-read and require the same payload hash/file identity, verify that applied state does not claim the pending plan/apply as successful, require explicit approval, warn that a later approved apply may repeat idempotent remote upserts after an indeterminate crash, and immediately revalidate that same expected artifact before removing only the validated local pending file. Without `--approve` it is preview-only. It reads no credentials and contacts no remote service.

### 3. Execute existing remote apply

After precomputation succeeds, execute existing approved remote writes, stale-deletion policy, and applied-state save without changing their semantics.

If remote/apply-state execution fails:

- the canonical catalog MUST remain unchanged;
- the pending artifact MUST remain non-reconcilable or be removed;
- output MUST use existing apply failure behavior and MUST NOT claim catalog registration.

### 4. Confirm and commit catalog registration

After remote writes and applied-state persistence succeed:

- atomically update the pending artifact with `remote_apply_confirmed=true`, `apply_id`, and applied-state identity sufficient for reconciliation, then recompute its canonical payload hash over the confirmed content;
- acquire the catalog lock;
- reload and validate current catalog;
- reject an unexpected conflicting manual semantic change only if merging cannot preserve it;
- commit an idempotent card upsert using current manual-field/enabled preservation rules;
- remove the pending artifact after catalog commit succeeds;
- continue normal successful-plan cleanup.

The committed card MUST retain the successful `plan_id` and `apply_id`.

## Post-apply catalog commit failure

A pending-confirmation write, catalog lock, disk, conflict, atomic-save, or post-commit pending-cleanup failure after remote/applied-state success is a **partial success**, not a rollback of remote data. If pending confirmation itself fails, the still-valid unconfirmed artifact plus its prior applied-state identity MUST remain locally recoverable: reconciliation MAY promote it only when the exact bound applied-state database proves a new matching successful plan/apply identity distinct from the bound prior identity. This is not the indeterminate unconfirmed-remote-failure case. If catalog commit succeeds but pending cleanup fails, output MUST truthfully retain `catalog_updated=true`, catalog/card revisions, `pending_cleanup=false`, pending path, and the exact reconcile command; reconciliation MUST idempotently verify the committed revision and remove the artifact without remote work.

The command MUST:

- return exit code 2;
- preserve the confirmed pending artifact;
- preserve successful applied state and remote rows;
- print/return `remote_apply_succeeded=true`, plus truthful `catalog_updated` and `pending_cleanup` values for the phase reached;
- include the exact pending path;
- include the exact repair command `buoy catalog reconcile --pending <path> --catalog <bound-catalog-path>`;
- avoid normal plan-directory cleanup when that cleanup would remove required reconciliation provenance.

It MUST NOT retry remote writes automatically.

## Reconciliation

`buoy catalog reconcile --pending PATH --catalog PATH` MUST:

1. read no credentials and contact no remote service;
2. normalize paths; require pending to be a regular non-symlink file directly under the bound resolved `catalog-pending` root; require supplied catalog path to equal the normalized target bound in the payload;
3. validate pending schema/hash and require `remote_apply_confirmed=true`, except that a valid unconfirmed artifact MAY continue only for interrupted-confirmation recovery when step 4 proves a new matching applied-state success distinct from its bound prior identity;
4. acquire the bound namespace lock, then re-read the pending regular file and revalidate its path, binding, payload hash, and file identity against the pre-lock snapshot before loading applied state from the exact bound database path; require matching site ID, namespace, plan ID, and apply ID; for the narrow interrupted-confirmation exception, derive the final apply ID only from that exact applied state;
5. apply the same current manual-semantic/all-existing-enabled preservation merge under the catalog lock;
6. be idempotent when the exact card revision is already committed;
7. immediately before removal, revalidate the same expected payload hash and file identity so a pathname replacement is rejected; remove only that validated artifact and only after successful/idempotent catalog completion;
8. clearly reject stale, indeterminate-unconfirmed, mismatched, tampered, symlinked, out-of-root, or superseded pending state.

A successful reconciliation MUST report local-only completion and leave remote/applied state untouched.

## Existing cards and manual metadata

- Manual semantic fields and enabled state MUST survive every apply.
- Generated cards MAY refresh generated title/summary/aliases/tags from verified source metadata.
- Source identity, retrieval contract, plan/apply IDs, and system timestamps MUST refresh from the successful apply.
- A disabled card MUST remain disabled after apply.
- Semantic/vector recomputation MUST follow semantic-hash rules; unchanged valid vectors MUST be reused.
- Apply MUST NOT remove other catalog cards.

## Preflight and output

Apply without `--approve` MUST remain non-mutating and MUST NOT load a model. Its text/JSON summary MUST add a `catalog_registration` preview containing:

- catalog path;
- namespace;
- whether the card is new, generated-update, or manual-preserving update;
- semantic origin;
- no vector values.

Successful approved apply output MUST include catalog path, catalog revision, namespace, card revision, and `catalog_updated=true`.

## Acceptance scenarios

### Namespace contention

Given another approved apply holds the namespace lock, when approved apply begins, then it fails before model construction, pending mutation, credential lookup, or remote work.

### Confirmed pending collision

Given a matching confirmed pending registration remains after remote success, when approved apply is retried, then it performs no model/credential/remote work and points only to the exact reconcile command. A tampered/mismatched confirmed artifact fails closed.

### Unconfirmed pending collision

Given any valid matching unconfirmed pending artifact, when approved apply is retried, then it performs no model/credential/remote work and reports indeterminate remote state plus the explicit approved abandonment command. Only after separately approved abandonment may a later apply use existing idempotent repeat-upsert semantics.

### Precompute failure

Given the pinned routing model is not locally available, when approved apply begins under the namespace lock, then it fails before credential lookup or remote writes and the canonical catalog is unchanged.

### First successful apply

Given no existing card, when remote apply and applied-state save succeed, then one enabled generated card is committed and the pending artifact is removed.

### Preserve manual fields

Given an enabled or disabled manual card, when later approved apply succeeds, then its semantic fields and enabled state remain unchanged while system/retrieval/apply fields refresh.

### Remote failure

Given pending card preparation succeeded but remote apply fails, then the catalog is unchanged and reconciliation cannot commit the unconfirmed pending card.

### Local post-apply failure

Given remote apply and applied state succeed but pending confirmation, catalog save, or pending cleanup fails, then the command reports truthful partial success, retains one recoverable pending artifact, gives the exact repair command, and performs no second remote write. A confirmation-write failure may leave the artifact unconfirmed only when its bound prior identity plus exact applied state safely prove the new success during reconciliation. A cleanup-only failure reports the committed catalog/card revisions with `catalog_updated=true` and `pending_cleanup=false`.

### Reconcile

Given a regular in-root confirmed pending registration binds the supplied catalog and current applied state, when reconcile runs, then it acquires namespace-before-catalog locks, atomically commits the card locally without credentials or Turbopuffer access, removes only that artifact, and is idempotent.

### Abandon unconfirmed

Given a valid in-root unconfirmed artifact and no matching successful applied-state identity, when abandonment runs without approval it previews only; with approval it removes only that local artifact, warns about possible repeat idempotent upserts, and performs no credential/remote work.

### Existing schema-v1 plan

Given a supported older plan without embedding precision/source metadata, when approved apply runs, then it preserves the original plan hash, uses float32, derives source kind only from the verified URI mapping, and uses apply-resolved region/current ranking defaults.

## Explicit exclusions

- catalog mutation during plan or unapproved apply preflight;
- remote catalog writes;
- remote rollback after a local catalog failure;
- automatic registration of unrelated visible namespaces;
- overwriting manual semantic fields or re-enabling disabled cards;
- new stale-deletion semantics;
- shared/multi-user catalog synchronization;
- taxonomy, graph, or concept extraction.
