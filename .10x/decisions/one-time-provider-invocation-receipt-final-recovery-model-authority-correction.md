Status: active
Created: 2026-08-25
Updated: 2026-08-25
Supersedes: .10x/decisions/superseded/one-time-provider-invocation-receipt-final-recovery.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
Authority-Correction: .10x/evidence/2026-08-25-provider-invocation-receipt-model-authority-correction.md
Shaping-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-activation-review.md
Plan: .10x/tickets/2026-08-25-provider-invocation-receipt-final-recovery-plan.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Automatic-Retrieval: .10x/specs/automatic-multi-corpus-retrieval.md
Routing-Quality: .10x/specs/scalable-routing-quality.md
Evidence-Abstention: .10x/specs/automatic-retrieval-evidence-abstention.md
Routing-Activation: .10x/specs/bounded-prototype-routing-activation.md
Multi-Corpus-Decision: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md
Bounded-Routing-Decision: .10x/decisions/buoy-uses-bounded-prototype-routing.md
Routing-Activation-Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
Evidence-Decision: .10x/decisions/buoy-owns-automatic-retrieval-evidence-abstention.md
Candidate-Readiness: .10x/knowledge/provider-free-candidate-readiness-before-one-shot-authority.md
Package-Inheritance: .10x/knowledge/exact-reproduced-package-digests-inherit-reviewed-safety.md
Attempt-Accounting: .10x/knowledge/provider-budgets-distinguish-logical-operations-and-transport-attempts.md
Implementation-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Implementation-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md

# One-Time Provider Invocation Receipt Final Recovery: Corrected Model Authority

## Context

Three separately authorized canary preparations are consumed and permanently
ineligible under their own contracts:

- `.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`;
- `.10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md`;
  and
- `.10x/tickets/2026-08-25-run-provider-invocation-receipt-canary-fix-offline-one-live.md`.

Their immutable failure evidence and reviews establish, respectively, wrapper/
routing-inspector failure after exact wheel reproduction, a novel archive
classifier failure after exact wheel reproduction, and a VCS-version-discovery
failure plus global-cache boundary breach before a wheel existed. None
establishes a product defect or live behavior. No live command began and no
receipt exists, but unconsumed live authority in an ineligible ticket is not
reusable without new owner authority.

The owner supplied that new authority in
`.10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md`.
The exact receipt implementation remains independently reviewed at source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

The first final-recovery decision incorrectly narrowed the unchanged ordinary
automatic command to construction of only the pinned BGE model. The resulting
candidate NO-GO was correct against that one-model ticket, but its classification
as a product defect is superseded. Active production specifications, bounded-
routing and evidence decisions, and the exact reviewed source require the pinned
local MiniLM cross-encoder for ordinary automatic routing, multi-corpus
reranking/fallback, and evidence assessment. The owner authorized the unchanged
ordinary automatic command and did not authorize removal or bypass of its
production reranker. This is a governing-record defect, not a product defect.

## Decision

Authorize the non-executable parent plan
`.10x/tickets/2026-08-25-provider-invocation-receipt-final-recovery-plan.md`
and exactly its two sequential children.

### Phase 1: repeatable provider-free candidate preparation

Only
`.10x/tickets/done/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md`
may prepare the candidate. Its existing provider-free activation remains active;
this correction grants no new operational surface. Under that activation it
MUST:

1. use a local VCS-aware clone or checkout at exact reviewed commit/tree so the
   pinned Hatch-VCS flow sees exact version authority, without mutating any
   repository ref;
2. use only an owner-private UV cache for build and runtime work. It MAY seed
   that cache by read-only copying from the existing cache, but MUST NOT use the
   existing cache as a writable build cache; every build/runtime write remains
   inside owned temporary state;
3. iteratively build/rebuild and correct only provider-free harness/runtime
   material until the exact reviewed wheel is produced and every inherited
   package, routing, installation, and strict receipt check passes, or until
   sanitized evidence establishes a real product defect;
4. accept only exact filename
   `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`, version
   `0.5.2.dev87+g0b27c4eaa`, size 730602 bytes, the established 78 reviewed
   members, and SHA-256
   `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`;
5. reuse the exact integration package evidence cryptographically and MUST NOT
   author or run a novel archive member-type classifier;
6. inspect by provider-free filesystem reads the exact cache roots, refs, and
   assets for both authorized production models, and make the retained harness
   guard their exact identities/settings without constructing either; and
7. retain the complete accepted candidate, isolated runtime, and needed harness
   privately and immutably through independent review, while recording only
   sanitized evidence with no private path.

There is deliberately no one-build or no-rebuild limit in phase 1. Iteration
never permits source/test/specification/lock/routing changes, candidate identity
substitution, credential-value access, construction, loading, or inference by
either production model, provider/DNS/TLS/network access, telemetry database/
store/API/command behavior, retrieval, global installation/tool replacement,
ref mutation, or writes outside owned temporary state. The existing UV cache
may be read only for the permitted seed copy. Exact cache roots, refs, and assets
for both authorized models may be inspected provider-free by filesystem reads
only. All existing caches MUST remain unchanged. The retained harness MUST guard
the two exact identities and runtime settings below, reject every other model,
download, or substitution, and perform no model construction during preparation.

Phase 1 closes only after an independent reviewer records explicit fresh
**PASS/GO** bound to the complete sanitized preparation evidence commit/tree and
the exact retained immutable candidate/runtime. Drift, deletion, incomplete
evidence, real product defect, unresolved side effect, qualified/stale review,
or NO-GO
forbids phase 2.

### Phase 2: exactly one automatic live command

Only
`.10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md`
may execute live. It begins blocked and inactive, depends on phase 1, and
receives only the already prepared immutable candidate/runtime plus the exact
fresh PASS/GO. It MUST NOT build, rebuild, correct a harness, substitute a
candidate,
or rerun preparation.

After confirming candidate/GO/current-state identity, phase 2 may privately use
only:

- case `m01-dagster-turbopuffer-quality` from dataset
  `automatic-multi-corpus-retrieval-v1` at SHA-256
  `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`;
- cached model `BAAI/bge-small-en-v1.5` at revision
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, with unchanged
  production automatic-device behavior and offline/no-download controls;
- cached model `cross-encoder/ms-marco-MiniLM-L-6-v2` at revision
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU-only, local-files-only,
  safetensors-only, remote code disabled, max-length 512, batch 8, and offline/
  no-download controls; and
- the existing intended credential source inside the private child without
  exposing its value.

The live child may construct or reuse those two exact models only as the
unchanged ordinary automatic routing/retrieval path requires. It MUST NOT
preload a model merely to satisfy this decision and MUST NOT construct, load,
download, or substitute any other model. It then runs exactly one ordinary
automatic command through the private receipt scope. Telemetry remains disabled.
Provider operations are only current strong catalog reads and selected content
reads. Receipt acceptance requires catalog invocation count at most 5 and
content invocation count at most 18. There is no preview, explicit command,
alternate case/dataset/model/candidate, substitution, second command, provider
retry, command retry, or receipt retry. Command start consumes all live
authority regardless of outcome.

PASS requires a known successful original command outcome preserved truthfully
and separately, plus one terminal strict canonical compact UTF-8 content-free
receipt satisfying both active specifications with every represented operation
and attempt successful. Missing, incomplete, observer-failed, malformed,
noncanonical, over-bound, error, or interrupted receipt fails without inference
or retry.

Post-state MUST prove exact equality for repository/ref/worktree, retained
candidate until cleanup, owner-private and source UV caches, both exact model
cache roots/refs/assets, telemetry filesystem, credential source, global tools,
processes, and unrelated state. Provider activity MUST reconcile as read-only.
Cleanup and retention MUST follow the active lifecycle spec: on PASS retain only
the canonical sanitized
receipt and bounded content-free evidence; on failure retain no receipt or
partial ledger; delete all private/raw/runtime material after evidence is safe.
Independent final correctness, privacy, side-effect, receipt, and cleanup review
is required before closure.

The receipt proves only governed Buoy application-boundary invocations. Neither
phase may claim physical wire sends, SDK-internal retries, provider billing,
cost, or rate-limit behavior.

## Predecessor disposition and compatibility

All three consumed tickets remain `Status: blocked`, `Activation: consumed`,
and `Eligibility: ineligible`; they grant no build, preparation, GO, retry, or
live authority and are not edited or reopened by this decision.

The consumed decision is canonical history at
`.10x/decisions/superseded/one-time-provider-invocation-receipt-canary-fix-offline-one-live.md`.
The flawed one-model final-recovery decision is canonical history at
`.10x/decisions/superseded/one-time-provider-invocation-receipt-final-recovery.md`.
Each former active path remains only a relative compatibility link resolving to
its `Status: superseded` record. Historical references therefore continue to
resolve but grant no current authority. The immutable candidate preparation and
repair evidence remain unchanged; the focused authority-correction evidence
supersedes only the repair record's product-defect classification.

## Alternatives considered

### Reopen a consumed ticket

Rejected because it would erase consumed preparation authority and immutable
failure history.

### Keep build and live execution in one ticket

Rejected because candidate readiness and independent PASS/GO must exist before
one-shot live authority becomes eligible.

### Restore a one-build/no-rebuild limit

Rejected. The known failures show that provider-free environment and harness
correction must be repeatable before immutable candidate review; live authority
remains exactly one command with no retry.

### Use a metadata-free export or the existing UV cache directly

Rejected. The pinned VCS backend requires VCS-aware source, and direct cache use
would repeat the unowned global-write risk.

### Preserve the one-model boundary or disable MiniLM

Rejected. Active production authority and the exact source require MiniLM in
ordinary automatic routing, multi-corpus reranking/fallback, and evidence
assessment. Disabling or substituting that reranker would change the owner-
authorized ordinary automatic command.

## Consequences

Preparation may safely iterate inside owned provider-free state while source and
accepted candidate identity remain exact. It must reprove provider-free cache/
ref/asset readiness and harness guards for both exact production models without
constructing either. Live authority cannot begin until the retained candidate
independently receives a fresh PASS/GO. The final live operation remains
singular, read-only, telemetry-off, content-free, and fail-closed, and may use
only the two exact production models as ordinary automatic behavior requires.
