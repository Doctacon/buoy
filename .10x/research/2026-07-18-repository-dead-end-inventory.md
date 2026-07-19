Status: done
Created: 2026-07-18
Updated: 2026-07-18

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

Twenty terminal ticket files remain at `.10x/tickets/` rather than their terminal directories: 19 `done` and one `cancelled`. This is mechanical placement/reference debt.

Several tickets appear status-stale and require closure review rather than automatic closure:

- `.10x/tickets/2026-07-13-float16-embedding-inference.md` and `.10x/tickets/2026-07-14-single-pass-plan-and-stage-timing.md` describe implemented behavior present in commit `aa6110d` and have evidence; both remain `active` only for independent review/closure coherence.
- `.10x/tickets/2026-06-28-cross-corpus-validation-basket.md`, `.10x/tickets/2026-06-28-repo-oversize-source-indexing.md`, `.10x/tickets/2026-06-28-website-capped-aggregation-default-review.md`, and `.10x/tickets/2026-06-28-repo-searchable-path-symbol-metadata.md` contain completed experiments and no-promotion conclusions but remain open/active.
- `.10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md` records a long sequence of completed/promoted/rejected hypotheses and reached named targets but remains active.
- `.10x/tickets/2026-07-14-conditional-website-replanning.md` is a legitimate failed measurement gate and may warrant cancellation/no-action closure rather than indefinite blocked status.

`.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md` is not dead: it owns current source/documentation drift requiring a product decision. `.10x/tickets/2026-07-14-update-node24-github-actions.md` is also live maintenance, not dead-end cleanup.

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
4. Record placement and stale statuses need mechanical normalization plus closure review, not blanket deletion.
5. Compatibility removal belongs to a focused 0.4 shaping decision, not opportunistic cleanup.
6. Ignored artifacts require provenance-aware review and remain excluded.
