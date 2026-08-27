Status: open
Created: 2026-08-25
Updated: 2026-08-25
Parent: None
Depends-On: None
Execution: non-executable
Activation: not-applicable
Decision: .10x/decisions/one-time-provider-invocation-receipt-final-recovery-precommand-boundary-correction.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
Authority-Correction: .10x/evidence/2026-08-25-provider-invocation-receipt-model-authority-correction.md
Preflight-Failure: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-live-preflight-failure.md
Shaping-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-activation-review.md
Boundary-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-precommand-boundary-review.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Historical-Candidate-Evidence: commit fa70a8c3e79d2df4d5b643f7bc1cc8af462f51ec, tree 45b2684c7d2f71e7c03a65e2d9bd5e201b923ffa
Historical-Candidate-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-dual-model-candidate-review.md
Historical-Candidate-GO: GO, wheel SHA-256 42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87, stale after deletion
Command-Start-Count: 0
Live-Authority: unconsumed

# Provider Invocation Receipt Final Recovery Plan

## Aggregate outcome

Prepare, completely preflight, retain, and independently approve one exact
immutable provider-free candidate, then use only that candidate for exactly one
ordinary automatic live command and one strict canonical content-free receipt.
This parent is a plan, not an executable ticket, and grants no build, cache,
credential, model, telemetry, provider/network, retrieval, GO, wrapper, or live
command authority.

## Child sequence and dependencies

1. `.10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md`
   is the active regression owner. Required cleanup after a generic provider-
   free pre-wrapper failure deleted its reviewed handoff. It must rebuild the
   exact candidate, repeatedly exercise and correct the complete pre-wrapper
   preflight until it passes without credential-value/model/provider/network/
   telemetry access, retain the candidate through failures and review, and
   receive fresh independent **PASS/GO**.
2. `.10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md`
   remains blocked/inactive. Command-start count is zero and its sole live
   authority is unconsumed. It becomes eligible only after child 1 has a rebuilt
   exact candidate, complete pre-wrapper PASS, and fresh independent GO bound to
   the retained immutable handoff. Eligibility does not activate it.

The children remain strictly sequential. The first invocation of the retained
wrapper for its sole ordinary command is the live start and consumption
boundary. No provider-free assertion may be deferred into child 2.

## Integration points and side-effect boundaries

Both children are governed by the active accounting and lifecycle
specifications and the focused knowledge linked from the active decision. The
reviewed implementation/package authority remains exact source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

Preparation writes only owned private temporary state and may repeat builds,
harness/wrapper corrections, validators, and complete pre-wrapper assertions.
It may inspect both exact model cache roots, refs, and public assets by
provider-free filesystem reads only, without importing or constructing a model.
It may inspect credential-source metadata without its value and telemetry
filesystem state without opening telemetry storage or APIs. Bounded diagnostics
name only content-free assertion categories and generic outcomes. A provider-
free preflight failure retains the candidate and remains correctable preparation.

Live execution begins by invoking the freshly reviewed retained wrapper. That
start consumes the only live authority before any credential value, model
construction, provider/network access, or ordinary-command behavior inside it.
After start there is no wrapper, provider, command, receipt, or second-command
retry. Neither child changes source, tests, specs, package locks, routing data,
repository refs, global tools, existing caches, provider data, or unrelated
state.

The live case remains `m01-dagster-turbopuffer-quality` from dataset
`automatic-multi-corpus-retrieval-v1` at SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`.
Only exact pinned BGE and MiniLM production models/settings are allowed.
Telemetry remains disabled; provider activity remains current strong catalog
reads and selected content reads only; receipt limits remain catalog at most 5
and content at most 18.

All three prior consumed attempts remain blocked, consumed, and ineligible.
They are historical inputs only and are not children of this plan.

## Aggregate acceptance criteria

- The provider-free child uses exact VCS-aware source, an owned isolated UV
  cache, repeatable preparation, and the exact reviewed wheel identity without
  novel archive classification or prohibited access.
- The exact dual-model cache/ref/assets readiness and guard rules pass without
  model import or construction; no other model, download, or substitution is
  possible.
- Every assertion before credential-value access, model construction,
  provider/network access, wrapper invocation, and command start runs as
  repeatable provider-free preparation. Complete pre-wrapper preflight passes in
  one bound run with only bounded content-free assertion categories retained.
- The rebuilt complete candidate/runtime/harness/wrapper remains retained after
  provider-free failures and through fresh independent PASS/GO.
- Fresh independent PASS/GO binds the new sanitized evidence commit/tree and the
  exact privately retained immutable handoff before live eligibility.
- The existing live child receives only that handoff and GO, performs no
  preparation/reproof, and starts exactly one wrapper/ordinary command under the
  established case/dataset/two-model scope.
- Wrapper/ordinary-command start consumes authority; there is no preview,
  explicit command, provider/command/receipt retry, or second command.
- The original command succeeds truthfully; one canonical content-free all-
  success receipt passes catalog `<=5`, content `<=18`, and both active specs.
- Exact post-state equality, provider read-only reconciliation, bounded
  retention, raw/private cleanup, and independent final review pass without
  wire/SDK-retry/billing claims.
- Ticket statuses, dependencies, evidence, reviews, predecessor disposition,
  command-start count zero before live, and singular authority remain coherent.

## Evidence expectations

Child 1 records bounded build/correction/preflight attempt counts and generic
content-free categories; exact source/wheel/runtime/handoff identities; owned-
cache and no-prohibited-access proofs; exact filesystem-only model-cache,
telemetry-filesystem, credential-source-metadata, global/process/current-state,
case/dataset, and wrapper assertions; final complete pre-wrapper PASS;
retention; privacy; and fresh independent PASS/GO. Child 2 records exact fresh
GO/handoff receipt, one wrapper/command start and terminal outcome, strict
receipt verdict/counts, post-state equality, read-only inventory, cleanup,
retention, privacy, and independent final review. Records contain no private
path or prohibited value.

## Explicit exclusions

Parent execution; concurrent children; reopening consumed predecessors; a new
live child or widened command count; source/test/spec/lock/routing change;
credential-value access during preparation; model import/construction during
preparation; provider/network/retrieval or telemetry operation during
preparation; public receipt activation; global install/tool/cache mutation;
provider write/management; any model beyond the two exact production models;
model download/cache mutation/substitution; release/deployment/publication/push/
ref mutation; physical-wire, SDK-retry, billing, cost, or rate-limit claim.

## Blockers

The parent is blocked on active child 1 rebuilding and retaining the deleted
exact candidate, passing the complete repeatable pre-wrapper preflight, and
receiving fresh independent PASS/GO. Child 2 remains blocked/inactive until
those gates pass. No new owner authority or live ticket is required; command-
start count remains zero and the originally authorized single live command
remains unconsumed.

## Progress and notes

- 2026-08-25: Created records-only at clean shaping baseline HEAD
  `da928dd1ef339e16d525ba6c95f2bf42e90ab667`, tree
  `5eaf0f3ec6d7ee3a77cec04f5711782ceb5ad0ad`. Neither child was activated. No
  source clone/export, cache access, build, install, validator/test, credential,
  model, telemetry, provider/network, retrieval, GO, or live command occurred.
- 2026-08-25: Records-only model-authority correction restored the exact BGE and
  MiniLM boundary. Later provider-free evidence and independent review issued
  **PASS/GO** for candidate evidence commit
  `fa70a8c3e79d2df4d5b643f7bc1cc8af462f51ec`, tree
  `45b2684c7d2f71e7c03a65e2d9bd5e201b923ffa`, and exact wheel SHA-256
  `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
- 2026-08-25: A separately activated runner failed generic `preflight` before
  wrapper invocation. The command-start ledger was absent; no credential value,
  model import/construction, telemetry operation, provider/network/retrieval,
  command, or receipt occurred. Fail-closed cleanup deleted the retained
  candidate and raw/private state. The failure evidence remains truthful.
- 2026-08-25: Owner-directed records-only boundary correction began at clean
  HEAD `11c877312d60d7676f9ebfb779b59eb09eb35758`, tree
  `bdf48fa5bc84a7bdc3ae2baabfcb7cb23d9b2e00`, and classified all pre-wrapper
  checks as repeatable provider-free preparation. The historical GO
  is stale only because its handoff was deleted. The candidate ticket moved
  canonically from `done` to active as the rebuild/preflight regression owner;
  the existing live ticket returned to blocked/inactive with command-start count
  zero and authority unconsumed. No new live command or count was created. This
  correction did not build, access any cache/model/credential/provider/network/
  telemetry behavior, issue GO, or run live.
