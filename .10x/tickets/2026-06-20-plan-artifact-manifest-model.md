Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-generic-site-rag-incremental-plan-apply.md
Depends-On: .loom/specs/generic-site-rag-incremental-plan-apply.md, .loom/knowledge/generic-site-rag-plan-apply-vocabulary.md

# Plan Artifact and Manifest Model

## Scope

Define and implement the local artifact model for generic site RAG plans.

In scope:

- Data structures for `plan.json`, `manifest.json`, and `chunks.jsonl`.
- Stable schema versioning.
- Deterministic `plan_id` or content-derived plan identifiers.
- Page records with canonical URL, title, content path, page hash, status, content type, and source metadata.
- Chunk records with row ID candidate, canonical URL, section path, chunk index, chunk hash, embedding text hash, title, content preview or content reference, and source page relationship.
- Artifact hash calculation used by apply to verify reviewed files have not changed.
- Tests for deterministic serialization/hash behavior.

Out of scope:

- Live turbopuffer writes.
- State diffing against previous applies.
- CLI command wiring except small helper hooks if needed.
- Policy/filter design beyond preserving already-supplied crawl/chunk options.

## Implementation notes

The model should be explicit rather than inferred from `summary.json` alone. `summary.json` is for human-readable reporting; `plan.json` and `manifest.json` are part of the apply contract.

The artifact hash should avoid volatile values where possible. Generated Markdown currently includes `crawl_timestamp`; implementation should either exclude volatile frontmatter from the plan hash or move volatile timestamps out of content hashed for apply verification.

Recommended artifacts:

```text
plan.json        # command-level plan, diff summary, hash, state pointers
manifest.json    # complete desired page/chunk manifest
chunks.jsonl     # line-oriented chunk inspection/apply input
summary.json     # existing human/machine summary
pages/*.md       # extracted Markdown pages
```

## Acceptance criteria

- Plan/manifest/chunk artifact schema is represented by typed Python structures or clearly documented dictionaries.
- Serialization is deterministic: repeated generation from the same content/options produces the same artifact hash.
- Artifact hash changes when chunk content, page content, or relevant options change.
- Artifact hash does not change only because of a volatile crawl timestamp.
- `plan.json` includes schema version, plan ID, site ID, base URL, namespace candidate/target, options, state path, artifact hash, and diff placeholder/summary fields.
- `manifest.json` records all desired pages and chunks needed for apply without re-crawling.
- `chunks.jsonl` is generated and inspectable.
- Tests cover deterministic output, changed content, changed options, and volatile timestamp handling.

## Progress and notes

- 2026-06-20: Ticket opened as Phase 1 foundation for incremental plan/apply.
- 2026-06-20: Implemented `src/turbo_search/plan_artifacts.py` with typed local-only models for `plan.json`, `manifest.json`, chunk JSONL rows, deterministic serialization, state path helpers, a first-apply diff placeholder, and artifact hashing that excludes volatile `crawl_timestamp` frontmatter.
- 2026-06-20: Added `tests/test_plan_artifacts.py` covering required fields, deterministic output, timestamp volatility, content changes, option changes, and writing inspectable `plan.json`/`manifest.json`/`chunks.jsonl` artifacts.
- 2026-06-20: Validation passed. Evidence: `.loom/evidence/2026-06-20-plan-artifact-manifest-model-validation.md`.

## Blockers

None.
