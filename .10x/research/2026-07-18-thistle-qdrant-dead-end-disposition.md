Status: done
Created: 2026-07-18
Updated: 2026-07-18

# Thistle/Qdrant Dead-End Disposition

## Question

What unique work exists in dirty worktree `/Users/crlough/Code/personal/turbo-search.worktrees/thistle-site-test`, what remains relevant to current Buoy/Turbopuffer, and what may be retired before deleting that worktree?

## Sources and methods

Read-only inspection used dirty-worktree HEAD `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62`, branch `thistle-site-test`, and current `develop` at `980e536`. No source/worktree file was edited, staged, cleaned, reset, deleted, executed, or contacted over the network. Qdrant was not started.

- Captured `git status --porcelain=v1 --untracked-files=all`, SHA-256 of the exact status, and SHA-256/size for every changed/untracked file.
- Enumerated `develop..HEAD`, endpoint divergence, and every path in each unique commit.
- Inspected all 17 tracked dirty diffs and all untracked top-level records; raw evidence artifacts were indexed by path/hash rather than replayed.
- Compared current crawler, MarkItDown, plan/row, DuckDB diff, Turbopuffer row schema, retrieval/citation, catalog, and stale-deletion contracts.
- Rechecked ignored-state directories only by status/size.
- Applied the user's final disposition: retire exact-chunk deduplication, preserve its old records/evidence only as historical non-authority, port no dedup behavior, and salvage the exact-host crawler boundary. Other findings retained owners only where current source plus prior ratification prove an unresolved current gap.

Complete mechanical inventories:

- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-path-inventory.tsv` — all 108 dirty paths (17 tracked modified, 91 untracked), classification, owner, bytes, hash.
- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/unique-commit-path-inventory.tsv` — all 288 path entries across both unique commits.
- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/unique-commits.txt`.
- `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-status-before.txt` and `dirty-content-manifest-before.txt`.

## Inventory

### Unique commits

`develop...thistle-site-test` was `48` develop-only commits and `2` dirty-branch-only commits:

1. `b48f13c6286af65781e82327eea4deffd471c8a7` — `fix(sources): normalize markitdown output`.
2. `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62` — `feat: cut over search backend to qdrant`.

The second commit is a 288-path composite. Classification counts are: 135 Qdrant/Tantivy dead-end paths; 52 historical record-graph edits/relocations; 26 mixed provider-cutover source paths; 20 historical branch-only records; 10 historical Turbopuffer namespace-delete paths with no current product request; 7 historical compact-plan paths with no measured current need; 6 superseded SQLite-state paths; 6 superseded generated-cleanup paths; 5 Apache-license paths already present/evolved; 4 missing sitemap-resource-limit paths; 3 provider docs/skills; 3 historical local-quality-gate paths; 3 historical CLI-refactor paths; and 3 other composite paths. The TSV is the authoritative exhaustive path list; this prose does not abbreviate it into authority.

### Dirty tracked changes

The 17 modified tracked files contain 1,246 insertions and 59 deletions:

- mixed exact-host plus dedup implementation/tests: `src/turbo_search/crawler.py`, `tests/test_crawler.py`;
- dedup/alias/state/apply/retrieval implementation/tests bound to Qdrant schema v2 and SQLite: `src/turbo_search/{applied_state,apply,chunker,cli,plan_artifacts,plan_diff,retriever}.py`, `tests/test_{applied_state,apply_cli,cli,plan_artifacts,retriever}.py`;
- Qdrant-era docs/skill edits describing dedup: `.pi/skills/qdrant-site-rag/SKILL.md`, `.pi/skills/qdrant-site-rag/references/scrapling-site-workflow.md`, `docs/generic-site-rag-plan-apply.md`.

No tracked dirty file is safe to copy mechanically into current `src/buoy_search`.

### Untracked changes

The 91 untracked files classify as:

- 13 exact-host evidence/review/ticket files;
- 5 exact-dedup spec/evidence/review/ticket files;
- 14 first Thistle safety-stop files;
- 44 Thistle Qdrant retry files;
- 12 Mercury Qdrant smoke files;
- 3 local lock/SQLite state files.

The exact path/hash inventory is durable in the TSV. Full OAuth-shaped URLs were not copied from ignored artifacts.

### Ignored state

Read-only status/size inspection found:

- `.venv/` — about 1.3 GiB;
- `artifacts/` — about 79 MiB;
- `.turbo-search-mercury-smoke/` — about 26 MiB;
- `.pi-subagents/` — about 5.7 MiB;
- `.pytest_cache/` — about 52 KiB;
- `.ruff_cache/` — about 48 KiB;
- ignored Qdrant retry log — 11,320 bytes.

These are generated/cache/local-state surfaces, not current authority. External Docker volumes/collections are outside the worktree and outside the deletion manifest.

## Findings

### Critical — current final responses and redirects are not exact-host enforced

Current `src/buoy_search/crawler.py:1292-1379` uses `LinkExtractor(allow_domains=...)`, accepts `response.url`, and calls `response.follow()` with automatic redirect behavior; it does not explicitly validate the final response hostname or each redirect target before request. Sitemap/robots acquisition at `src/buoy_search/crawler.py:782-790` uses default `urlopen` redirect handling. The current helper at lines 856-861 filters candidate URLs but is not a final-response/redirect boundary.

The historical local two-server evidence reported zero unauthorized destination requests after explicit exact-host redirect handling, with independent pass review. Because it tested superseded source, it is evidence of the contract/approach, not evidence that current Buoy is safe.

Current owners:

- `.10x/specs/website-exact-host-crawl-boundary.md` (active, record-backed);
- `.10x/tickets/2026-07-18-enforce-website-exact-host-crawl-boundary.md` (bounded executable repair).

### Significant — sitemap/robots reads and gzip expansion are currently unbounded

`src/buoy_search/crawler.py:782-790` performs `response.read()` with no byte ceiling. Lines 805-814 incrementally read gzip chunks into an unbounded bytearray and treat malformed gzip as the original body, allowing empty parsing/fallback rather than the old fail-closed behavior. Historical commit `d7a37d7` contained user-ratified 512 KiB robots, 10 MiB transfer, and 50 MiB decompressed ceilings that did not reach current develop.

Current owners:

- `.10x/specs/sitemap-resource-limits.md` (active preserved contract);
- `.10x/tickets/2026-07-18-bound-sitemap-resource-usage.md`.

### No action — exact-chunk deduplication is retired

The Qdrant-era implementation grouped exact chunk content, selected a deterministic URL primary, stored aliases, added a SQLite record hash, emitted aliases in retrieval, and forced explicit stale deletion when duplicate rows would remain. Current Turbopuffer rows, DuckDB state, and retrieval citations differ materially, and the user explicitly chose not to activate or port this behavior.

The old spec, implementation, tests, evidence, and review remain discoverable only through the exhaustive path/hash inventories. They have no current behavioral authority. The prior draft current spec was discarded rather than laundering candidate alias, row-identity, diff, or stale-deletion semantics into an active contract. The durable no-action owner is `.10x/tickets/cancelled/2026-07-18-reconcile-website-exact-chunk-deduplication.md`.

### Significant — unique MarkItDown safety normalization is absent

Unique commit `b48f13c` removed Unicode `Cc` controls except `\n`, `\r`, and `\t` before local documents were written/chunked. Current `src/buoy_search/crawler.py:1633-1657,1892-1907` returns converter text and applies only `.strip()`. Embedded NUL/control characters can therefore enter generated pages/chunks again.

Owner: `.10x/tickets/2026-07-18-restore-markitdown-control-character-normalization.md`.

### Informational — compact artifacts and namespace deletion need no current owner

Historical Qdrant schema-v2 evidence measured compact/streaming artifact gains, but no current measurement or active requirement proves a Buoy defect. The active namespace-card contract requires schema version 1. The draft compact-plan reconciliation ticket was discarded; a future measured problem requires fresh shaping.

Historical Turbopuffer namespace-deletion guardrails predate the current remote catalog lifecycle. Current source has no deletion command and no current product request requires one. The draft reconciliation ticket was discarded rather than inventing catalog-card deletion semantics. A future deletion request must explicitly ratify its remote catalog, pending recovery, DuckDB state, failure, and concurrency effects.

### Informational — provider and superseded storage/tooling work

Qdrant/Tantivy runtime, BM25/RRF experiments, compose/config/dependency changes, Qdrant skills/docs, Qdrant lifecycle tests, SQLite state, and Qdrant collection smoke execution are historical only. Apache licensing is already present on develop. Old guarded generated cleanup targeted retired SQLite/history/checkout lifecycle. The old local pytest/Ruff choice is superseded as authority by current hosted CI and current project commands. The old CLI source-argument refactor no longer matches the differentiated current crawl/plan interface. These are indexed, not activated.

## Historical record provenance map

| Dirty/branch records | Current durable disposition |
|---|---|
| Untracked exact-host done ticket, evidence, raw validation, pass review | Findings indexed here; current active exact-host spec and open repair ticket own behavior. Old review verdict applies only to old source. |
| Untracked exact-dedup active spec, done ticket, evidence, pass review | Indexed by exact path/hash as historical non-authority; current port cancelled/no-action. No current dedup spec remains. |
| Untracked first-Thistle evidence and concerns review | Safety facts summarized here; exact-host has a current repair owner and dedup is historical/no-action. |
| Untracked Mercury smoke ticket/evidence/raw results | Historical observation summarized here; ticket preserved as cancelled at `.10x/tickets/cancelled/2026-07-11-smoke-test-mercury-site.md`. |
| Untracked Thistle retry ticket/raw results | Provider run indexed here; ticket preserved as cancelled at `.10x/tickets/cancelled/2026-07-11-test-thistle-site-qdrant-rag.md`. |
| `b48f13c` normalization records/source/tests | Exact behavior summarized in a current open restoration ticket; old records remain non-authoritative provenance. |
| `d7a37d7` Qdrant/Tantivy records/source/evidence | Per-path classification TSV; no current authority. Named product-neutral gaps have current owners. |
| Historical namespace deletion, sitemap limits, compact artifacts | Current active sitemap spec/ticket; namespace deletion and compact artifacts indexed as no-action absent a current requirement/measurement. |

## Current-versus-branch behavior matrix

| Surface | Dirty branch | Current develop | Disposition |
|---|---|---|---|
| Final-response/redirect host safety | Explicit exact-host manual redirect guards and counts | Candidate URL filtering only; automatic redirects/final response unchecked | Active spec + open repair |
| Sitemap resource bounds | Bounded/fail-closed on committed branch | Unbounded response/gzip accumulation | Active spec + open repair |
| Exact chunk dedup | Website exact hashes, deterministic primary, aliases | No ingestion dedup; only page-level retrieval collapse | Retired; historical non-authority only |
| Alias citations | Qdrant native list, JSON and compact text | One URL only | No action; do not port |
| Alias-only diff | SQLite `record_hash` | DuckDB equality uses embedding hash only | No action; do not port |
| MarkItDown controls | `Cc` normalization in `b48f13c` | Absent | Open repair |
| Applied state | SQLite/provider-era | Active DuckDB hard cutover | Retire old state work |
| Backend | Local Qdrant + Tantivy exploration | Turbopuffer | Retire provider work |
| Namespace deletion | Guarded Turbopuffer delete before catalog era | Absent; remote catalog now authoritative | Historical only; no current request |
| Compact plans | Qdrant schema v2 streaming | Current schema v1/current catalog pin | Historical only; no measured current need |

## Uncommitted draft disposition

Every draft left by the timed-out worker was inspected:

| Draft | Disposition |
|---|---|
| Five files under `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/` | Keep. Exhaustive mechanical inventories and before-state hashes. Owner classifications corrected to the final no-action decisions. |
| `.10x/research/2026-07-18-thistle-qdrant-dead-end-disposition.md` | Keep as done research; corrected to final user ratification. |
| `.10x/specs/website-exact-host-crawl-boundary.md` | Keep active; historical ratification and current source gap support it. |
| `.10x/tickets/2026-07-18-enforce-website-exact-host-crawl-boundary.md` | Keep open; bounded current-architecture repair. |
| `.10x/specs/sitemap-resource-limits.md` and `.10x/tickets/2026-07-18-bound-sitemap-resource-usage.md` | Keep active/open; exact limits were previously user-ratified and current source is unbounded. |
| `.10x/tickets/2026-07-18-restore-markitdown-control-character-normalization.md` | Keep open; unique commit plus its ticket/evidence/review prove user authorization and current source lacks the fix. |
| Prior draft `specs/website-exact-chunk-deduplication.md` | Discard. Candidate current semantics are unratified and the user selected retirement. |
| Prior draft `tickets/2026-07-18-reconcile-website-exact-chunk-deduplication.md` | Replace with cancelled/no-action record under `tickets/cancelled/`. |
| Prior draft `tickets/2026-07-18-reconcile-compact-plan-artifacts.md` | Discard. Historical gains do not prove a current requirement or defect. |
| Prior draft `tickets/2026-07-18-reconcile-turbopuffer-namespace-deletion.md` | Discard. Feature absence is not a current defect/request; lifecycle semantics are unratified. |
| Two historical Qdrant smoke tickets under `.10x/tickets/cancelled/` | Keep cancelled after preservation; neither grants current execution authority. |

## Deletion disposition and manifest

After this record-only PR is merged, every valuable product-neutral finding and historical observation has a current durable owner or explicit indexed no-action rationale. No dirty source implementation should be copied. Dedup semantics are preserved only as historical path/hash provenance and the current port is explicitly cancelled.

At that point the exact safe deletion candidate is:

1. linked worktree registration and entire filesystem checkout `/Users/crlough/Code/personal/turbo-search.worktrees/thistle-site-test` (about 1.4 GiB), including the 17 modified tracked paths, 91 untracked paths, and ignored/cache/generated directories enumerated above;
2. local branch `thistle-site-test` only after the worktree is removed and the record-only PR is merged, because both unique commits are fully dispositioned by the inventories/current owners.

Deletion remains forbidden before merge/integration of this preservation PR. The manifest does **not** include Docker volumes/collections, remote Turbopuffer namespaces, any other branch/worktree, or external state. It grants no deletion command execution in this ticket.

## Limits

- No live behavior was rerun; old test/review claims remain scoped to old source.
- The untracked raw evidence payloads are indexed by path/hash and summarized, not copied wholesale; their Qdrant provider details are intentionally non-authoritative.
- Current line references are observations at `develop` commit `980e536` and must be refreshed by implementation tickets after integration.
- No claim is made that retired dedup behavior is desirable or compatible with current Buoy; preservation records are historical provenance only.
