Status: done
Created: 2026-06-20
Updated: 2026-06-21
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/tickets/2026-06-20-apply-cli-incremental-upsert.md, .loom/specs/generic-site-rag-incremental-plan-apply.md

# Generic Site Retrieval Smoke Evals

## Scope

Add a lightweight retrieval validation path for generic site namespaces after plan/apply exists.

In scope:

- Allow retrieval/eval commands to target a generic namespace/site rather than only the Jellyfish default.
- Support a small per-site eval file with questions and expected URL/topic hints.
- Keep dry-run/list mode credential-free and turbopuffer-free.
- Keep live evals explicitly gated by `--live` and environment credentials.
- Provide a Scrapling docs example eval set suitable for validating a future approved apply.

Out of scope:

- Running live evals without explicit user approval.
- Building a full benchmark suite.
- Proprietary rerankers or embedding services.
- Reworking the core hybrid retrieval algorithm unless generic usage exposes a concrete issue.

## Acceptance criteria

- Retrieval can be configured with a generic namespace and region without code changes.
- Eval list/dry-run mode works without credentials.
- A small Scrapling docs eval file exists with expected URL/topic hints.
- Live mode remains explicitly gated and does not print secrets.
- Tests cover CLI configuration and dry-run behavior.
- Documentation explains how to validate an applied site namespace after live apply approval.

## Progress and notes

- 2026-06-20: Ticket opened as Phase 3 product validation. It may be executed after apply exists.
- 2026-06-21: Added non-secret runtime override flags (`--namespace`, `--region`, `--embedding-model`) to `retrieve` and `evals`, while preserving environment defaults.
- 2026-06-21: Added `src/turbo_search/data/scrapling_retrieval_smoke_evals.json` with four Scrapling docs smoke eval cases and expected URL/topic hints.
- 2026-06-21: Added tests for generic retrieve dry-run overrides, generic eval dry-run overrides using the Scrapling dataset, Scrapling dataset loading, and live-mode API-key gates.
- 2026-06-21: Updated README, `docs/generic-site-rag-plan-apply.md`, and the site RAG skill reference with generic retrieval/eval validation examples and safety notes.
- 2026-06-21: Validation passed. Evidence: `.loom/evidence/2026-06-21-generic-site-retrieval-smoke-evals-validation.md`.

## Blockers

None.

## Residual risks

- Live retrieval quality against a generic applied namespace remains unverified because no live generic namespace query was approved or run for this ticket.
- The Scrapling eval dataset is intentionally a small smoke set, not a comprehensive benchmark.
