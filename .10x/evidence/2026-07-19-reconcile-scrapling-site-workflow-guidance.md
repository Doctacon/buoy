Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/done/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md

# Scrapling Site Workflow Guidance Reconciliation

## What was observed

A bounded comparison found exactly the two stale guidance areas owned by the ticket in `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`:

1. **Retrieval validation:** `.10x/decisions/direct-commands-execute-by-default.md`, `.10x/specs/default-remote-namespace-routing.md`, and `.10x/evidence/2026-07-18-retrieval-live-by-default.md` agree with current retrieve/evals parser and routing code in `src/buoy_search/cli.py`: plain retrieve is live, retrieve `--dry-run`/`--plan` previews, retrieve `--live` is a retained compatibility no-op, and evals `--live` still activates live eval execution. Focused cases in `tests/test_cli.py` cover plain and compatibility-live retrieval, credential-free eval listing, and the live-evals credential gate.
2. **Apply sequence:** `.10x/specs/apply-to-retrieval-handoff.md`, the apply parser and `_run_apply` in `src/buoy_search/cli.py`, and `load_verified_apply_plan` in `src/buoy_search/apply.py` agree that apply defaults to the verified plan namespace. Plan CLI `--namespace` selects the namespace recorded in the reviewed artifact. Apply CLI `--namespace` is an optional equality assertion; `tests/test_apply_cli.py` covers matching preflight and mismatched rejection. Ambient `TURBOPUFFER_NAMESPACE` is not needed to direct apply.

The changed-lines diff is limited to the target reference's existing **Apply sequence** and **Retrieval validation** prose. Existing preview examples, approval/API-key safety, region handling, plan review, confirmation/automation, stale deletion, and secret handling remain present.

## Procedure

No live command was run. No Turbopuffer credential was supplied.

```text
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest tests.test_cli.CliTests.test_help_mentions_current_safe_workflow_commands tests.test_cli.CliTests.test_plain_and_compatibility_live_explicit_retrieval_require_api_key tests.test_cli.CliTests.test_evals_command_dry_run_lists_cases_without_credentials tests.test_cli.CliTests.test_evals_live_with_generic_overrides_is_gated_by_api_key tests.test_apply_cli.ApplyCliTests.test_apply_preflight_verifies_plan_without_credentials_or_live_calls tests.test_apply_cli.ApplyCliTests.test_apply_fails_on_namespace_mismatch -q
# Ran 6 tests in 0.024s — OK (Python 3.13.0)

uv run buoy retrieve --help
# Help identifies plain-live retrieval, compatibility-no-op --live, and --dry-run/--plan preview.

uv run buoy evals --help
# Help identifies --live execution and --dry-run/--list listing.

uv run buoy apply --help
# Help identifies apply --namespace as expected namespace defaulting to the plan value.

# Bounded reference check using test -f for every ticket reference plus heading checks.
# 13 ticket references and both target headings resolve.

git diff --check
# exit 0
```

The first `uv run` created a worktree-local ignored `.venv`; it was removed after validation so no generated environment remained in the worktree.

## What this supports or challenges

This supports the two documentation corrections against active authority, current source/help, and focused tests. Tracked changes contain no files under `src/`, `tests/`, `.10x/specs/`, package/version metadata, or state/data locations. The validation used only help, missing-credential gates, explicit dry-run/list behavior, and fake-backed/temp-directory tests; it made no live retrieval, live eval, approved apply, remote read/write, state/data mutation, namespace mutation, or other remote-resource change.

## Limits

This implementation evidence did not itself constitute independent review; the subsequent independent review is recorded in `.10x/reviews/2026-07-19-reconcile-scrapling-site-workflow-guidance-review.md`. No live Turbopuffer behavior was exercised.
