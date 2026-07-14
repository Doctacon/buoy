Status: done
Created: 2026-07-13
Updated: 2026-07-14
Parent: None
Depends-On: None

# Rewrite README for Details on Demand

## Scope

Rewrite `README.md` as the showcase landing page governed by `.10x/knowledge/documentation-details-on-demand.md`. Move retained reference material into focused Markdown documents under `docs/`, eliminating duplicate ownership.

## Acceptance criteria

- README is approximately 100 lines or fewer and leads with the product promise and copyable source → plan → preflight → approved apply → retrieve workflow.
- Setup, local-safe versus live behavior, and the three supported source categories are understandable without reading another document.
- README contains no exhaustive extension list, crawl-default matrix, state migration/locking internals, ranking heuristic prose, metric formula, eval schema, or autoresearch internals.
- Detailed material remains discoverable in clearly named focused docs covering indexing/sources/safety, retrieval, and evaluation/autoresearch. Replace the current all-purpose `docs/generic-site-rag-plan-apply.md` if splitting produces clearer ownership; repair all repository references.
- README links are descriptive, relative, and valid. Detailed docs have no broken local links and do not materially duplicate one another.
- Commands shown in README parse against the current CLI without credentials or remote writes; no live command is executed.
- README and docs reflect current artifact cleanup, DuckDB state, progress/timing, and embedding-precision behavior implemented by the repository at execution time.

## Explicit exclusions

- Application behavior changes, new CLI flags, package metadata redesign, website generation, badges, screenshots beyond the existing puffin, marketing claims without evidence, and live Turbopuffer operations.

## References

- `.10x/knowledge/documentation-details-on-demand.md`
- `README.md`
- `docs/indexing.md`
- `docs/retrieval.md`
- `docs/evaluation.md`
- `.pi/skills/turbopuffer-site-rag/SKILL.md`

## Evidence expectations

README line/word count, local-link validation, safe CLI parse/help checks for shown commands, repository search proving moved-detail ownership, full test suite, and independent editorial/technical review.

## Progress and notes

- 2026-07-13: User designated this as a showcase codebase and established “details on demand” as the documentation policy.
- 2026-07-13: Rewrite authorized; assigned to a single documentation worker.
- 2026-07-14: Editorial and technical review found two significant accuracy defects: README safety wording hid remote source fetching, and indexing docs stated per-domain concurrency 1 instead of the implemented default 4. Repair required before closure.
- 2026-07-13: Replaced the 262-line README with a 91-line landing page; split detailed ownership into `docs/indexing.md`, `docs/retrieval.md`, and `docs/evaluation.md`; removed the all-purpose generic doc; corrected the operational workflow reference. Local links resolve, six README command shapes parse without execution, and the full suite passes (206 tests). Evidence: `.10x/evidence/2026-07-13-readme-details-on-demand-rewrite.md`.
- 2026-07-14: Repaired both review findings: README now explicitly distinguishes public-source network fetching from Turbopuffer-local planning, indexing docs now state the source-backed 2 global / 4 per-domain defaults, and equivalent ambiguous plan wording in the operational skill was corrected. README remains 91 lines; links and six command shapes validate; full suite passes (206 tests).
- 2026-07-14: Final independent editorial/technical review passed. Parent revalidated 206 tests, local links, counts, and diff hygiene. Evidence: `.10x/evidence/2026-07-13-readme-details-on-demand-rewrite.md`; review: `.10x/reviews/2026-07-14-readme-details-on-demand-review.md`.

## Blockers

- None.
