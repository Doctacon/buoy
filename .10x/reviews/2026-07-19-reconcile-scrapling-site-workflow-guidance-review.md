Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: .10x/tickets/done/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md
Verdict: pass

# Scrapling Site Workflow Guidance Reconciliation Review

## Target

PR #51 at reviewed head `dd3cb6f871b6a7b26696bd242151f3ec0eeced0d`, governed by `.10x/tickets/done/2026-07-19-reconcile-scrapling-site-workflow-direct-command-guidance.md`.

## Findings

Independent record-only review compared the changed guidance with the active direct-command decision, default-remote-routing and apply-handoff specifications, current retrieve/evals/apply help and source, focused tests, implementation evidence, and the complete `origin/develop...HEAD` diff.

The ticket criteria map as follows:

1. **Retrieval modes:** the reference now states separately that plain retrieve is live, retrieve `--dry-run`/`--plan` previews, retrieve `--live` is a compatibility no-op, evals list by default, and evals `--live` activates live execution. This agrees with active authority, current parser/help, and focused credential-gate and dry-run/list tests.
2. **Apply namespace authority:** the reference no longer instructs setting `TURBOPUFFER_NAMESPACE` for apply. It identifies plan-time `--namespace` selection, the namespace persisted in the reviewed plan, and apply `--namespace` as an optional equality assertion whose mismatch fails. This agrees with the apply parser, `_run_apply`, `load_verified_apply_plan`, and focused preflight/mismatch tests.
3. **Credential and approval boundaries:** the explicit-namespace retrieve preview and eval-list examples remain credential-free and Turbopuffer-free. The prose still requires explicit approval and `TURBOPUFFER_API_KEY` for live retrieval/evals and approved apply.
4. **Preserved surrounding workflow:** region setup, plan review, interactive confirmation and `--approve` automation, opt-in stale deletion, and secret-handling guidance remain intact.
5. **No behavior change:** the implementation commit changes only the ticket, its evidence, and six prose lines in the two named reference sections. It changes no source, tests, specifications, package/version metadata, state/data, or remote-resource semantics.
6. **Evidence and validation:** all 13 ticket references and both target headings resolve; six focused Python 3.13 tests and current retrieve/evals/apply help comparison passed independently; `git diff --check` passed. PR #51 hosted Python 3.11, Python 3.13, and distribution checks were successful at review time.

No blocker, significant, minor, or nitpick finding was identified.

## Verdict

Pass. The implementation is bounded, the ticket acceptance criteria are satisfied, evidence and hosted CI remain successful, and the ticket may move to done.

## Residual risk

No live Turbopuffer retrieval, eval, or apply was exercised. The review therefore establishes documentation/source/authority coherence and fake-backed or credential-gated behavior, not live-service behavior. This is an explicit evidence limit, not a blocker for the record-only correction.
