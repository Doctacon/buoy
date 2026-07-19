Status: open
Created: 2026-07-19
Updated: 2026-07-19
Parent: None
Depends-On: None

# Reconcile Scrapling Site Workflow Command and Apply-Namespace Guidance

## Scope

Perform a record/documentation-only correction to exactly two stale statements in `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`:

1. Under **Retrieval validation**, replace the claim that live retrieval and evals both require `--live`. Plain `buoy retrieve` is live, retrieve `--live` is only a retained compatibility no-op, retrieve `--dry-run`/`--plan` request preview, and evals `--live` still opts into live eval execution.
2. Under **Apply sequence**, remove the instruction to set `TURBOPUFFER_NAMESPACE`. The namespace is selected and recorded by the reviewed plan (including an explicit plan CLI `--namespace` when chosen); apply defaults to that verified plan namespace, and an apply `--namespace` argument only asserts the same value because a mismatch fails. Ambient `TURBOPUFFER_NAMESPACE` is not required to direct the approved apply.

Update only those two stale statements and the minimum surrounding prose needed to keep their examples and safety language coherent. Verify the result against active command/apply authority, current CLI help/source, and focused tests without changing the skill's broader workflow.

## Acceptance criteria

- The retrieval-validation text clearly distinguishes plain-live retrieval, retrieval preview via `--dry-run`/`--plan`, retrieve's compatibility `--live`, and evals' still-operative `--live`.
- The apply sequence no longer instructs setting `TURBOPUFFER_NAMESPACE` and instead identifies the reviewed plan namespace, optional plan CLI selection, and apply's matching CLI assertion as namespace authority.
- The existing explicit-namespace preview examples remain credential-free and Turbopuffer-free; surrounding text remains explicit that live retrieval/evals and approved apply require user approval and `TURBOPUFFER_API_KEY`.
- Existing region guidance, plan review, apply confirmation/automation, stale-deletion guardrails, and secret-handling guidance remain intact except for the two necessary corrections above.
- No direct-command, apply, namespace, environment-variable, 0.4 alias-removal, source, test, package/version, state/data, or remote-resource semantics change.
- Reference checks and a bounded authority/help/test comparison pass; evidence and independent record-only review are recorded.

## Evidence expectations

- A changed-lines diff shows corrections only in the target reference's **Apply sequence** and **Retrieval validation** guidance.
- Retrieval comparison cites `.10x/decisions/direct-commands-execute-by-default.md`, `.10x/specs/default-remote-namespace-routing.md`, `.10x/evidence/2026-07-18-retrieval-live-by-default.md`, current retrieve/evals help in `src/buoy_search/cli.py`, and their focused parser/routing tests.
- Apply-namespace comparison cites `.10x/specs/apply-to-retrieval-handoff.md`, current apply parser and `_run_apply` in `src/buoy_search/cli.py`, `load_verified_apply_plan` in `src/buoy_search/apply.py`, and the matching/mismatched namespace cases in `tests/test_apply_cli.py`.
- Reference/link check output and a no-source/no-test/no-spec/no-state/no-remote attestation are recorded.

## Blockers

None.

## Explicit exclusions

Buoy 0.4 console/environment alias implementation; changing retrieve/evals/apply behavior or flags; changing plan or apply namespace selection/verification; changing any `TURBOPUFFER_*` runtime contract; changing active decisions/specifications; source/tests/package/version/release changes; live apply, retrieval, or evals.

## References

- `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md` (`Apply sequence` and `Retrieval validation`)
- `.10x/decisions/direct-commands-execute-by-default.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/apply-to-retrieval-handoff.md`
- `.10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md`
- `.10x/evidence/2026-07-18-retrieval-live-by-default.md`
- `.10x/tickets/done/2026-07-14-explicit-plan-to-retrieval-handoff.md`
- `.10x/evidence/2026-07-14-apply-to-retrieval-handoff.md`
- `src/buoy_search/cli.py`
- `src/buoy_search/apply.py`
- `tests/test_cli.py`
- `tests/test_apply_cli.py`
- `.10x/research/2026-07-19-v0-4-compatibility-removal-inventory.md`

## Progress and notes

- 2026-07-19: Opened as the separate owner discovered during 0.4 compatibility inventory. It is not a child or implementation prerequisite of the 0.4 removal plan.
- 2026-07-19: Expanded after PR #46 review to own both stale statements already discovered in the same reference: retrieve's live mode and apply's ambient namespace setup. The contradictory apply-guidance exclusion was removed; implementation and specification semantics remain excluded.
