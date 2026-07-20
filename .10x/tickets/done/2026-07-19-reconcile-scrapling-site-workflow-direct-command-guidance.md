Status: done
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
- 2026-07-19: Activated for record-only execution on `work/reconcile-scrapling-guidance`; the requested `context.md` and `plan.md` paths were absent, so the executable ticket and all of its referenced authority/source/tests were used as the execution contract.
- 2026-07-19: Corrected only the target reference's Apply sequence and Retrieval validation prose. The apply guidance now keeps the reviewed plan namespace authoritative and treats apply `--namespace` as a matching assertion; retrieval guidance now distinguishes plain-live retrieve, retrieve preview, retrieve's compatibility `--live`, and evals' operative `--live`.
- 2026-07-19: Bounded reference checks resolved all 13 ticket references and both target headings. Six focused Python 3.13 tests covering current help, retrieve/evals mode gates, credential-free preview/list behavior, apply preflight, and namespace mismatch passed. CLI help comparison and `git diff --check` passed; no live command or credential was used.
- 2026-07-19: Recorded comparison and side-effect limits in `.10x/evidence/2026-07-19-reconcile-scrapling-site-workflow-guidance.md`. Ticket remains active pending required independent record-only review.
- 2026-07-19: Independent review passed PR #51 at `dd3cb6f871b6a7b26696bd242151f3ec0eeced0d`. Hosted Python 3.11, Python 3.13, and distribution checks remained successful. Review: `.10x/reviews/2026-07-19-reconcile-scrapling-site-workflow-guidance-review.md`.

## Closure mapping

- Retrieval mode guidance: the changed reference distinguishes plain-live retrieve, `--dry-run`/`--plan` preview, compatibility `--live`, and evals' operative `--live`; active decision/specification, current help/source, and focused tests agree.
- Apply namespace guidance: the reference removes ambient namespace setup, identifies plan-time `--namespace` selection and the recorded plan namespace, and describes apply `--namespace` as a matching assertion; current parser, verified-plan loading, and matching/mismatch tests agree.
- Safety and surrounding workflow: bounded diff review confirms credential-free explicit preview/list examples and preserves approval, API-key, region, review, confirmation, stale-deletion, and secret-handling guidance.
- Exclusions: the reviewed implementation commit changes only this ticket, its evidence, and the two target prose areas; it contains no source, tests, specifications, package/version, state/data, or remote-resource behavior change.
- Validation and review: six focused Python 3.13 tests, current retrieve/evals/apply help, 13 ticket references, two target headings, diff checks, independent review, and hosted PR checks passed.
- Residual limit: no live Turbopuffer retrieval, eval, or apply was exercised; acceptance is supported by active authority, current source/help, fake-backed and credential-gate tests, and hosted CI rather than live-service validation.

## Retrospective

When operational guidance combines commands with different activation defaults, grouping them under one sentence can silently overgeneralize a safety flag. The durable correction is to state each command's live/preview boundary separately and to identify persisted reviewed artifacts—not ambient configuration—as authority where plan verification owns runtime identity. Existing active decisions, specifications, help text, and focused tests provided sufficient authority; no new reusable procedure is needed.
