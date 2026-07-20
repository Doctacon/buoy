Status: done
Created: 2026-07-18
Updated: 2026-07-20

# Repository Dead-End Inventory

## Question

After the remote-catalog cutover and Buoy 0.3 release, which repository/worktree/code/record surfaces are demonstrably dead, which contain salvageable work, and which are intentional compatibility rather than cleanup candidates?

## Sources and methods

- Inspected `git status --short --branch`, `git worktree list --porcelain`, local branches, and GitHub PR state with `gh pr list --state all`.
- Measured root/worktree ignored disk usage with `du -sh`.
- Searched source, tests, docs, skills, changelog, and active `.10x/` records for legacy/deprecated/migration/local-catalog/Qdrant/Tantivy markers.
- Parsed `src/buoy_search/catalog.py` with Python AST, identified symbols imported by other production modules, followed intra-module name dependencies, and separated production-reachable card/schema logic from an unreachable local-persistence cluster.
- Inspected active/open ticket progress and terminal statuses.
- Inspected the dirty `thistle-site-test` worktree, its Qdrant tickets, stop review, unique evidence/spec records, source diff, and current `develop` crawl behavior.

No source, remote namespace, branch, ignored artifact, or dirty worktree was deleted during the investigation. The separately authorized merged-worktree cleanup is recorded in `.10x/evidence/2026-07-18-merged-worktree-cleanup.md`.

## Findings

### Clean merged worktrees

Twenty-eight clean linked worktrees mapped exactly to merged GitHub PR heads. They consumed most of the 16 GB `turbo-search.worktrees` directory. The dirty `work/shape-direct-command-defaults` and `thistle-site-test` worktrees had no merged PR and were excluded.

The 28 clean merged worktrees were removed after authorization. Worktree disk fell from 16 GB to 2.6 GB. No branch was deleted.

### Dirty Thistle/Qdrant dead end

`thistle-site-test` is a 1.4 GB dirty worktree on commit `d7a37d7` (`feat: cut over search backend to qdrant`). It contains 17 modified source/test/docs/skill files, 1,246 added/changed lines in the unstaged tracked diff, ignored state, and untracked evidence/spec/ticket records. Its active smoke tickets target Qdrant, the superseded `turbo_search` package, and old state paths.

The branch is not safe to delete wholesale. Product-neutral work exists only there and is absent from `develop`, including exact-host redirect safety records and an exact-chunk-deduplication contract/implementation with citation-alias semantics. Current `develop` still relies on crawler domain scheduling and does not visibly enforce the branch's final-response exact-host check. The deduplication behavior cannot be copied mechanically because current Turbopuffer row/citation contracts differ from the Qdrant-era branch.

Conclusion: preserve evidence and separately assess each product-neutral change; cancel/retire Qdrant-specific execution only after salvage/disposition is durable. Do not delete this worktree before that ticket closes.

### Unreachable local-catalog persistence cluster

The remote catalog cutover left a production-unreachable cluster in `src/buoy_search/catalog.py`:

- `document_to_dict`
- `empty_catalog`
- `resolve_catalog_path`
- `load_catalog`
- `catalog_lock`
- `_atomic_write`
- `save_catalog`
- `commit_system_card`
- `mutate_catalog`

No other production module imports these symbols, and no production-reachable definition in `catalog.py` depends on them. Tests still exercise portions of the cluster. Card models, schema parsing/validation, generated semantics, routing projection, `parse_catalog`, and remote-card helpers remain production-reachable and are not dead. `catalog migrate-local` also remains an active compatibility command and still requires validated local catalog parsing, but not local catalog persistence.

Conclusion: remove only the unreachable cluster and its obsolete persistence tests; preserve parsing/card-generation/migration-command behavior.

### JSON applied-state compatibility

`last-applied.json` discovery, parsing, migration, archive, and deletion are an intentional removal target already owned by `.10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md`. This inventory does not duplicate that owner.

### Record graph debris

At inventory time, twenty terminal ticket files remained at `.10x/tickets/` rather than their terminal directories: 19 `done` and one `cancelled`. This was mechanical placement/reference debt. Terminal placement was normalized by `.10x/tickets/done/2026-07-18-normalize-terminal-ticket-placement.md`.

The inventory also identified tickets requiring closure review rather than automatic closure. That review completed at `.10x/tickets/done/2026-07-18-review-stale-ticket-statuses.md` with aggregate review `.10x/reviews/2026-07-19-stale-ticket-status-closure-review.md`:

- `.10x/tickets/done/2026-07-13-float16-embedding-inference.md` and `.10x/tickets/done/2026-07-14-single-pass-plan-and-stage-timing.md` closed after evidence, current material tests/source, and spec-drift review supported every criterion.
- `.10x/tickets/done/2026-06-28-cross-corpus-validation-basket.md`, `.10x/tickets/done/2026-06-28-website-capped-aggregation-default-review.md`, and `.10x/tickets/done/2026-06-28-repo-searchable-path-symbol-metadata.md` closed as completed bounded experiments.
- `.10x/tickets/cancelled/2026-06-28-repo-oversize-source-indexing.md` was cancelled with no action because global promotion was rejected and `done` criteria were incomplete.
- `.10x/tickets/cancelled/2026-07-14-conditional-website-replanning.md` was cancelled with no action after the independently reviewed authoritative-validator gate failed.
- `.10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md` remains active with exact missing terminal support for named heavy hypotheses and routed-selector/profile work.

`.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md` is not dead: it owns current source/documentation drift requiring a product decision. `.10x/tickets/done/2026-07-14-update-node24-github-actions.md` was also live maintenance at inventory time, not dead-end cleanup.

### Intentional compatibility, not current dead code

Active records intentionally retain these surfaces:

- `turbo-search` console alias through 0.3;
- `TURBO_SEARCH_*` configuration aliases through 0.3;
- `.turbo-search` state-root fallback;
- `--auto-route` compatibility no-op;
- old-plan compatibility;
- `catalog migrate-local`.

They require an explicit 0.4 contract before removal. This inventory does not treat them as presently dead.

### Ignored local footprint

At inspection time the main worktree contained roughly 4.5 GB under ignored `artifacts/`, 1.2 GB under `.venv/`, 105 MB under `.pi-subagents/`, and 2 MB under `.buoy/`. These are not automatically dead: artifacts and local state may support active evidence or operations. No deletion is authorized by this inventory.

## Conclusions

1. The clean merged worktrees were the largest certain cleanup and are now removed.
2. The Thistle/Qdrant worktree is a dead provider direction containing salvageable product-neutral work; triage precedes deletion.
3. The local-catalog persistence cluster is bounded, source-proven dead code suitable for removal after the direct-command plan integrates.
4. Record placement and stale-status review completed through evidence-backed terminal dispositions while preserving the unsupported heavy-ranking scope under its active owner.
5. Compatibility removal belongs to a focused 0.4 shaping decision, not opportunistic cleanup.
6. Ignored artifacts require provenance-aware review and remain excluded.
