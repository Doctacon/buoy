Status: active
Created: 2026-06-20
Updated: 2026-06-20

# Turbopuffer Site RAG Skill

## Summary

The project now has a reusable Pi skill at `.pi/skills/turbopuffer-site-rag/SKILL.md`.

Use it when future sessions need to:

- answer questions from the existing Jellyfish turbopuffer namespace;
- remember the Jellyfish namespace details and retrieval guardrails;
- plan or dry-run generic website crawling with Scrapling;
- decide whether and how to create/write a new turbopuffer namespace for a crawled site;
- enforce cost/security guardrails around live turbopuffer writes.

## Included references

- `.pi/skills/turbopuffer-site-rag/references/jellyfish-namespace.md`
- `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md`

## Dry-run crawl implementation

- First-class CLI: `uv run turbo-search crawl --base-url <url> --json`
- Reference helper: `.pi/skills/turbopuffer-site-rag/scripts/scrapling_dry_crawl.py`

The CLI is local-only. It crawls with Scrapling, writes a generated Markdown corpus under `artifacts/`, chunks it with the existing `turbo_search.indexer` pipeline, and prints a JSON summary with:

- `dry_run: true`
- `credentials_required: false`
- `turbopuffer_api_calls: false`

## Guardrails

The skill explicitly forbids persisting secrets and forbids namespace creation, namespace deletion/replacement, live writes, or live evals without explicit user approval in the current conversation.
