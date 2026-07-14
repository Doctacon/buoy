Status: recorded
Created: 2026-07-13
Updated: 2026-07-14
Relates-To: .10x/tickets/2026-07-13-readme-details-on-demand-rewrite.md, .10x/knowledge/documentation-details-on-demand.md

# README Details-on-Demand Rewrite Validation

## What was observed

- `README.md` is now a 91-line, 400-word showcase landing page centered on source → local plan → local preflight → approved apply → retrieval.
- Setup, safety boundaries, and website/GitHub/local-document source choices are visible without opening reference docs.
- Exhaustive crawl defaults, source limits, DuckDB migration/locking, artifact retention, ranking heuristics, eval metrics/schema, and autoresearch mechanics moved out of README.
- Focused canonical user docs now exist at `docs/indexing.md`, `docs/retrieval.md`, and `docs/evaluation.md`.
- The former all-purpose `docs/generic-site-rag-plan-apply.md` was removed. No live README, user-doc, or skill link targets it; historical `.10x` records retain the old path as provenance.
- The operational Scrapling workflow reference was corrected to match the actual sitemap-first default and no longer lists completed disposable-namespace SDK validation as a current gap.
- No unimplemented float16 precision behavior is documented; current apply progress/timing and independent write/embedding batch controls are documented.
- After independent review, README now states that planning may fetch public remote sources while remaining local-only with respect to Turbopuffer credentials, embeddings, and calls. The focused indexing reference now matches the implemented crawl concurrency defaults: 2 global and 4 per domain. Equivalent ambiguous plan wording in the operational skill was corrected.

## Procedure

1. Read the current README, all user docs, CLI help/parser, operational skill/reference, and active precision spec.
2. Rewrote README and split retained detail by user question.
3. Validated relative Markdown links across README and all `docs/*.md` files.
4. Parsed six README command shapes through `build_parser()` without dispatching them, including the live-shaped examples.
5. Executed only safe CLI help commands; no plan crawl, apply, retrieval, eval, credentials, or remote operation ran.
6. Searched active user/skill documentation for removed-doc references and README for out-of-scope detailed terms; only historical `.10x` provenance mentions the old path.
7. Ran the complete test suite and whitespace/index checks.
8. Repaired the two independent-review findings, searched rewritten docs and operational skill references for equivalent stale wording/defaults, then repeated link, parser, help, count, full-suite, whitespace, and index validation.

## Results

```text
wc -l -w README.md
91 400 README.md

Markdown link validation
validated 4 markdown files; local links resolve

README command parser validation
parsed 6 README command shapes without executing them

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 206 tests in 6.274s
OK

git diff --check
OK

git diff --cached --quiet
no staged files
```

The suite emitted one existing temporary plan-cleanup warning and still passed.

## What this supports or challenges

Supports the requested progressive-disclosure landing page, focused doc ownership, command accuracy, link integrity, and no application behavior change. It also resolves both review findings: source-network access is explicit without weakening the Turbopuffer safety boundary, and documented crawl concurrency matches source constants.

## Limits

External web links were not network-checked. Live-shaped commands were parser-validated only and deliberately not executed. The repair still requires independent re-review before closure.
