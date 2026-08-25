Status: open
Created: 2026-08-25
Updated: 2026-08-25
Parent: None
Depends-On: None
Execution: non-executable
Activation: not-applicable
Decision: .10x/decisions/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
Authority-Correction: .10x/evidence/2026-08-25-provider-invocation-receipt-model-authority-correction.md
Shaping-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-activation-review.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md

# Provider Invocation Receipt Final Recovery Plan

## Aggregate outcome

Prepare and independently approve one exact immutable provider-free candidate,
then use only that candidate for exactly one independently gated automatic live
command and one strict canonical content-free receipt. This parent is a plan,
not an executable ticket, and grants no activation, build, cache access, model,
credential, telemetry, provider/network, retrieval, GO, or live authority.

## Child sequence and dependencies

1. `.10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md`
   is the only provider-free preparation owner. It is active under its existing
   separate provider-free activation and retains the exact candidate/runtime.
   It must complete exact cache/ref/assets inspection and harness guards for both
   authorized models without constructing either. It closes only with complete
   sanitized evidence and a fresh independent candidate **PASS/GO** against the
   retained immutable candidate/runtime, or reaches a truthful blocked outcome.
2. `.10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md`
   depends on child 1 and begins blocked/inactive. It becomes eligible only when
   child 1 has corrected exact preparation evidence and fresh independent
   PASS/GO. It receives
   the existing candidate and GO only, performs no build or harness correction,
   and owns the sole live-command authority.

The children are strictly sequential. Phase-1 activation is not live GO.
Independent candidate review is not final execution review.

## Integration points and side-effect boundaries

Both children are governed by the active accounting and lifecycle
specifications and the focused knowledge linked from the active decision. The
reviewed implementation/package authority is exact source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, with integration evidence/review
linked by the decision.

Preparation writes only owned private temporary state and retains the accepted
candidate privately through review. It may inspect both exact model cache roots,
refs, and assets by provider-free filesystem reads only, without constructing a
model or mutating either cache. Live execution may read the intended credential
and construct or reuse only the exact pinned BGE and MiniLM models after GO, and
only as unchanged ordinary automatic routing/retrieval requires. It may perform
only provider catalog/content reads reached by the single ordinary automatic
command. Telemetry stays disabled throughout. Neither child changes source,
tests, specs, package locks,
routing data, repository refs, global tools, existing caches, provider data, or
unrelated state.

All three prior attempts remain blocked, consumed, and ineligible. They are
historical inputs only and are not children of this plan.

## Aggregate acceptance criteria

- The provider-free child uses exact VCS-aware source, an owned isolated UV
  cache, repeatable preparation, and the exact reviewed wheel identity without
  novel archive classification or prohibited access; it proves exact cache/ref/
  asset readiness and harness guards for both authorized models without
  constructing either.
- Fresh independent PASS/GO binds complete sanitized corrected preparation
  evidence and the privately retained immutable candidate/runtime before live
  eligibility.
- The live child receives only that candidate and exact GO, begins exactly one
  automatic command under the established case/dataset/two-model and receipt
  scope, and performs no preparation or retry. It permits no other model,
  download, or substitution.
- The original command succeeds truthfully; one canonical content-free all-
  success receipt passes catalog <=5/content <=18 and both active specs.
- Exact post-state equality, bounded retention, raw/private cleanup, and
  independent final review pass without wire/SDK-retry/billing claims.
- Ticket statuses, dependencies, evidence, reviews, and predecessor disposition
  remain coherent.

## Evidence expectations

Child 1 records bounded preparation identities, attempts/corrections, exact
candidate/runtime identity, owned-cache and no-prohibited-access proofs, exact
filesystem-only cache/ref/assets inspection and harness guards for both models,
side-effect equality, retention, privacy, and fresh independent PASS/GO. Child 2
records exact GO/candidate receipt, one command start/terminal outcome, strict
receipt verdict/counts, post-state equality, read-only inventory, cleanup,
retention, privacy, and independent final review. Records contain no private
path or prohibited value.

## Explicit exclusions

Parent execution; concurrent children; reopening predecessors; source/test/spec/
lock/routing change; public receipt activation; telemetry-v2 change; global
install/tool/cache mutation; provider write/management; any model beyond the two
exact production models; model download/cache mutation or substitution; release/
deployment/publication/push/ref mutation; transport interception; physical-wire,
SDK-retry, billing, cost, or rate-limit claim.

## Blockers

None at the parent-planning level. Child 1 is active under its existing
provider-free activation. Child 2 has the blockers recorded in its own ticket.

## Progress and notes

- 2026-08-25: Created records-only at clean shaping baseline HEAD
  `da928dd1ef339e16d525ba6c95f2bf42e90ab667`, tree
  `5eaf0f3ec6d7ee3a77cec04f5711782ceb5ad0ad`. Neither child was activated. No
  source clone/export, cache access, build, install, validator/test, credential,
  model, telemetry, provider/network, retrieval, GO, or live command occurred.
- 2026-08-25: Records-only authority correction superseded the flawed one-model
  decision. The candidate returned active under its existing provider-free
  activation with its exact retained handoff; the live child remained blocked/
  inactive pending dual-model cache/ref/assets and harness-guard evidence plus a
  fresh independent PASS/GO. No source/spec/test change, model/cache access,
  build, credential read, telemetry, provider/network, retrieval, GO, or live
  command occurred.
