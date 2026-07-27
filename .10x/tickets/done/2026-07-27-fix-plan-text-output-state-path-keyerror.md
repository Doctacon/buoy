Status: done
Created: 2026-07-27
Updated: 2026-07-27
Parent: None
Depends-On: None

# Fix Plan Text Output `state_path` KeyError

## Scope

Repair the direct `buoy plan` text-output path so a successful schema-v2 compact-delta plan exits successfully after printing its summary. `print_plan_text` currently reads `payload['state_path']`, but the schema-v2 planning summary intentionally excludes absolute state paths under `.10x/specs/compact-delta-plan-artifacts.md`.

Keep JSON output, apply preflight output, compact artifact contents, state-path derivation, and planning behavior unchanged except where required by the governing contract.

## Acceptance criteria

- A successful text-mode `buoy plan` summary does not access a missing `state_path` field and exits zero.
- Text output remains accurate under the schema-v2 no-absolute-state-path contract.
- A focused regression test invokes the direct text-mode plan path with a schema-v2 summary lacking `state_path` and proves successful completion.
- Existing plan JSON and apply preflight tests continue to pass.

## Evidence expectations

Record the focused failing-before/passing-after regression and relevant CLI/apply test results. No live Turbopuffer calls or writes are required.

## Progress and notes

- 2026-07-27: Diagnosed from a real successful website plan of `https://johnstallone.me/`. Planning completed, fully verified, and retained `plan.json` plus `delta.duckdb`; the subsequent display call crashed at `src/buoy_search/cli.py:1906` because `state_path` is absent by design from the schema-v2 planning summary. Existing tests assert that plan artifacts omit `state_path`, while apply preflight separately retains state-path output. The generated artifact was inspected as 1.8 KiB `plan.json` plus 26 MiB `delta.duckdb`, with matching plan ID and 21,202 upserts.
- 2026-07-27: Added a direct text-mode `main(["plan", ...])` regression that writes schema-v2 artifacts, confirms `plan.json` omits `state_path`, and requires successful text completion without a `state_path` line. Before the implementation change, the focused unittest reproduced `KeyError: 'state_path'` at `src/buoy_search/cli.py:1906` (`Ran 1 test in 9.523s`, `FAILED (errors=1)`).
- 2026-07-27: Removed only the direct planning text renderer's invalid `state_path` access; apply text/preflight output remains unchanged. The focused plan-text/plan-JSON/apply-preflight basket passed 4 tests in 1.112s; all `plan_command` CLI tests passed 12 tests in 11.313s; all `apply_preflight` tests passed 5 tests in 1.165s; `git diff --check` passed. Evidence is recorded at `.10x/evidence/2026-07-27-plan-text-state-path-keyerror-fix.md`.
- 2026-07-27: Independent fresh-context review passed with no blocker or required fix at `.10x/reviews/2026-07-27-plan-text-state-path-keyerror-fix-review.md`. The parent then reran 12 plan-command tests and 5 apply-preflight tests successfully and confirmed `git diff --check`. Every acceptance criterion maps to the recorded failing-before/passing-after evidence. The governing schema-v2 specification remains coherent, apply preflight behavior is unchanged, and the ticket is closed.
- 2026-07-27: Retrospective found no reusable operational procedure, domain convention, unfinished work, or instruction gap requiring another durable record. The narrowly missed renderer/summary contract is permanently guarded by the new direct CLI regression.

## Blockers

None.

## Exclusions

Crawl performance tuning, exact-host policy changes, artifact schema changes, live apply, and unrelated CLI formatting.

## References

- `.10x/specs/compact-delta-plan-artifacts.md`
- `.10x/tickets/done/2026-07-24-implement-compact-delta-planning.md`
- `src/buoy_search/cli.py`
