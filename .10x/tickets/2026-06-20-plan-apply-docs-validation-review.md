Status: done
Created: 2026-06-20
Updated: 2026-06-21
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/tickets/2026-06-20-plan-cli-artifact-workflow.md, .loom/tickets/2026-06-20-apply-cli-incremental-upsert.md, .loom/tickets/2026-06-20-apply-stale-delete-guardrail.md

# Plan/Apply Docs, Validation, and Review

## Scope

Document, validate, and review the polished incremental plan/apply workflow before the parent plan is considered complete.

In scope:

- Update README with plan/apply examples.
- Update relevant docs under `docs/` with safety and credential guidance.
- Update `.pi/skills/turbopuffer-site-rag/` guidance to describe plan/apply and incremental state guardrails without private credential identifiers.
- Add or update tests documenting no-credential/no-live-call behavior.
- Run full unit tests and compile checks.
- Run a small real-network plan smoke against Scrapling docs if network is available and appropriate.
- Record evidence under `.loom/evidence/`.
- Perform an adversarial review under `.loom/reviews/` before closing parent.

Out of scope:

- Live generic apply unless explicitly approved in the current conversation.
- Remote state docs beyond noting it as future work.
- UI/TUI review tooling.

## Acceptance criteria

- README distinguishes `plan`, apply preflight, approved apply, and `--delete-stale`.
- Docs state that plan is local-only and apply is live only with explicit approval.
- Skill guidance does not persist private vault names, item titles, share IDs, tokens, or API keys.
- Tests pass:
  - Python unit test discovery.
  - uv unit test discovery.
  - compile checks for `src` and `tests`.
- Evidence records the validation commands and results.
- Review record explicitly checks:
  - no accidental turbopuffer calls from plan/preflight;
  - stale delete guardrail;
  - state update/failure behavior;
  - no secret-adjacent private identifiers persisted.

## Progress and notes

- 2026-06-20: Ticket opened as Phase 3 hardening/review work.
- 2026-06-21: Updated README, added `docs/generic-site-rag-plan-apply.md`, and updated `.pi/skills/turbopuffer-site-rag/` guidance to clearly distinguish local-only plan, apply preflight, approved apply, and `--delete-stale` stale-row deletion.
- 2026-06-21: Confirmed existing tests document no-credential/no-live-call behavior for plan and apply preflight; no new tests were needed for this docs-only ticket.
- 2026-06-21: Ran full Python and uv unit suites, compile checks, private identifier/secret-adjacent grep checks, and a safe real-network Scrapling docs `turbo-search plan` smoke. Evidence: `.loom/evidence/2026-06-21-plan-apply-docs-validation-review.md`.
- 2026-06-21: Recorded adversarial review with pass verdict. Review: `.loom/reviews/2026-06-21-plan-apply-docs-validation-review.md`.

## Blockers

None.
