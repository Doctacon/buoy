Status: open
Created: 2026-08-25
Updated: 2026-08-25
Parent: None
Depends-On: None
Execution: non-executable
Activation: not-applicable
Decision: .10x/decisions/one-time-provider-invocation-receipt-final-recovery.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
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
   is the only provider-free preparation owner. It is open/inactive and may
   iterate only after separate activation. It closes only with complete
   sanitized evidence and independent candidate **PASS/GO** against the retained
   immutable candidate/runtime, or reaches a truthful blocked terminal outcome.
2. `.10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md`
   depends on child 1 and begins blocked/inactive. It becomes eligible only when
   child 1 has exact preparation evidence and independent PASS/GO. It receives
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
candidate privately through review. Live execution may read the intended
credential and cached model only after GO and may perform only provider catalog/
content reads reached by the single ordinary automatic command. Telemetry stays
disabled throughout. Neither child changes source, tests, specs, package locks,
routing data, repository refs, global tools, existing caches, provider data, or
unrelated state.

All three prior attempts remain blocked, consumed, and ineligible. They are
historical inputs only and are not children of this plan.

## Aggregate acceptance criteria

- The provider-free child uses exact VCS-aware source, an owned isolated UV
  cache, repeatable preparation, and the exact reviewed wheel identity without
  novel archive classification or prohibited access.
- Independent PASS/GO binds complete sanitized preparation evidence and the
  privately retained immutable candidate/runtime before live eligibility.
- The live child receives only that candidate and exact GO, begins exactly one
  automatic command under the established case/dataset/model and receipt scope,
  and performs no preparation or retry.
- The original command succeeds truthfully; one canonical content-free all-
  success receipt passes catalog <=5/content <=18 and both active specs.
- Exact post-state equality, bounded retention, raw/private cleanup, and
  independent final review pass without wire/SDK-retry/billing claims.
- Ticket statuses, dependencies, evidence, reviews, and predecessor disposition
  remain coherent.

## Evidence expectations

Child 1 records bounded preparation identities, attempts/corrections, exact
candidate/runtime identity, owned-cache and no-prohibited-access proofs,
side-effect equality, retention, privacy, and independent PASS/GO. Child 2
records exact GO/candidate receipt, one command start/terminal outcome, strict
receipt verdict/counts, post-state equality, read-only inventory, cleanup,
retention, privacy, and independent final review. Records contain no private
path or prohibited value.

## Explicit exclusions

Parent execution; concurrent children; reopening predecessors; source/test/spec/
lock/routing change; public receipt activation; telemetry-v2 change; global
install/tool/cache mutation; provider write/management; model download/cache
mutation; release/deployment/publication/push/ref mutation; transport
interception; physical-wire, SDK-retry, billing, cost, or rate-limit claim.

## Blockers

None at the parent-planning level. Child 1 remains inactive pending separate
activation. Child 2 has the blockers recorded in its own ticket.

## Progress and notes

- 2026-08-25: Created records-only at clean shaping baseline HEAD
  `da928dd1ef339e16d525ba6c95f2bf42e90ab667`, tree
  `5eaf0f3ec6d7ee3a77cec04f5711782ceb5ad0ad`. Neither child was activated. No
  source clone/export, cache access, build, install, validator/test, credential,
  model, telemetry, provider/network, retrieval, GO, or live command occurred.
