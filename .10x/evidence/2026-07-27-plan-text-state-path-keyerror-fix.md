Status: recorded
Created: 2026-07-27
Updated: 2026-07-27
Relates-To: .10x/tickets/done/2026-07-27-fix-plan-text-output-state-path-keyerror.md, .10x/specs/compact-delta-plan-artifacts.md

# Plan Text `state_path` KeyError Fix Evidence

## What was observed

The direct text-mode `buoy plan` path raised `KeyError: 'state_path'` after successfully writing a schema-v2 `plan.json` and `delta.duckdb`. The focused regression reproduced the failure through `main(["plan", ...])` with a real locally generated schema-v2 summary and no `--json` flag.

Removing only the planning text renderer's `state_path` line makes that command return zero while retaining its valid `plan_path` output. The regression also verifies the written plan has `schema_version == 2`, omits `state_path`, and the text output does not claim a state path. The separate apply text renderer remains unchanged, and existing apply preflight coverage still proves `state_path` is emitted there.

## Procedure and exact results

### Failing before the implementation change

- `uv run python -m unittest tests.test_cli.CliTests.test_plan_command_text_output_succeeds_without_schema_v2_state_path`
  - Result: failed as expected before the fix.
  - Exact summary: `Ran 1 test in 9.523s`, `FAILED (errors=1)`.
  - Failure: `src/buoy_search/cli.py:1906` raised `KeyError: 'state_path'` from `print_plan_text(result.summary)`.

An initial attempt to use `uv run pytest -q tests/test_cli.py::CliTests::test_plan_command_text_output_succeeds_without_schema_v2_state_path` could not start because this checkout's installed environment has no `pytest` executable. Validation therefore used the repository's existing standard-library `unittest` suite.

### Passing after the implementation change

- `uv run python -m unittest tests.test_cli.CliTests.test_plan_command_text_output_succeeds_without_schema_v2_state_path tests.test_cli.CliTests.test_plan_command_writes_artifacts_and_first_apply_diff_without_credentials tests.test_apply_cli.ApplyCliTests.test_apply_preflight_verifies_plan_without_credentials_or_live_calls tests.test_apply_cli.ApplyCliTests.test_interactive_preflight_prompt_and_approved_revalidation_order`
  - Result: passed.
  - Exact summary: `Ran 4 tests in 1.112s`, `OK`.
  - One existing cleanup-safety fixture emitted its expected warning about refusing to remove a plan artifact directory under the state root.
- `uv run python -m unittest -k plan_command tests.test_cli`
  - Result: passed.
  - Exact summary: `Ran 12 tests in 11.313s`, `OK`.
  - Two existing cleanup-safety fixtures emitted expected warnings about directories under the state root.
- `uv run python -m unittest -k apply_preflight tests.test_apply_cli`
  - Result: passed.
  - Exact summary: `Ran 5 tests in 1.165s`, `OK`.
- `git diff --check`
  - Result: passed with no output.

### Parent-observed closure confirmation

After independent review, the parent reran the relevant groups in the clean task worktree:

- `uv run python -m unittest -k plan_command tests.test_cli` — `Ran 12 tests in 5.343s`, `OK`; two existing cleanup-safety warnings were emitted.
- `uv run python -m unittest -k apply_preflight tests.test_apply_cli` — `Ran 5 tests in 1.293s`, `OK`.
- `git diff --check` — passed with no output.

## What this supports

This evidence supports that schema-v2 direct plan text output no longer reads the intentionally absent `state_path`, still reports `plan_path`, and exits successfully. It also supports that focused plan JSON behavior and apply preflight behavior—including apply text `state_path` output—remain passing.

## Limits

Validation was focused on plan-command and apply-preflight CLI coverage; the full repository suite was not run. No live source provider, embedding model, Turbopuffer credential/call/write, approved apply, remote catalog mutation, push, PR, merge, publish, or release occurred.
