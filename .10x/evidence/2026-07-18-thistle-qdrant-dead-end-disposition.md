Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/2026-07-18-triage-thistle-qdrant-dead-end.md, .10x/tickets/cancelled/2026-07-18-reconcile-website-exact-chunk-deduplication.md

# Thistle/Qdrant Dead-End Triage Evidence

## What was observed

Read-only inspection of `/Users/crlough/Code/personal/turbo-search.worktrees/thistle-site-test` established:

- branch `thistle-site-test` remained at exact HEAD `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62`;
- its exact porcelain status SHA-256 remained `68975bb89991897480f93ddc57be727d2728f674ef39952f9af49a3b0f35878f`;
- the ordered SHA-256 list for all 108 dirty paths remained byte-identical to `.10x/evidence/.storage/2026-07-18-thistle-qdrant-dead-end/dirty-content-manifest-before.txt`, whose payload SHA-256 is `dac0e1a74a6d0b516c8c443d40ecf5b6c33fecf0995e1f83366a999ac9e14b8b`;
- there are 17 tracked modified paths and 91 untracked paths;
- branch divergence is 48 commits on current `develop` only and two commits on `thistle-site-test` only: `b48f13c6286af65781e82327eea4deffd471c8a7` and `d7a37d79de7011d9b4c0a0180f8bcea6265a7f62`.

No file in that worktree was edited, staged, cleaned, reset, run, or deleted. No Qdrant process, live crawl, model, provider, or remote service was invoked.

## Procedure

1. Captured `git status --porcelain=v1 --untracked-files=all`, `git rev-parse HEAD`, worktree registration, branch divergence, unique commits, and unique-commit path lists.
2. Computed SHA-256 and byte size for every tracked-modified and untracked path, then compared the final ordered hash list with the preserved before-state manifest.
3. Inspected all dirty record/source/test diffs and unique-commit records, and compared relevant behavior with current `src/buoy_search` source and active contracts.
4. Classified all 108 dirty paths and all 288 unique-commit path entries in the storage TSV files.
5. Reconciled every record draft left by the prior worker against final user direction.
6. Ran reference/status/header, inventory-count, whitespace, secret-pattern, and diff-scope checks in the record-only task worktree.

## Supported findings

- **Critical:** `src/buoy_search/crawler.py` filters candidate URLs but does not explicitly enforce the exact hostname on final page responses or each automatic redirect target. The current owner is `.10x/tickets/2026-07-18-enforce-website-exact-host-crawl-boundary.md` under active `.10x/specs/website-exact-host-crawl-boundary.md`.
- **Significant:** `src/buoy_search/crawler.py` performs unbounded robots/sitemap reads and gzip expansion. Historical active limits and user ratification plus the current source gap support `.10x/specs/sitemap-resource-limits.md` and `.10x/tickets/2026-07-18-bound-sitemap-resource-usage.md`.
- **Significant:** current local MarkItDown ingestion strips whitespace but does not remove embedded Unicode `Cc` controls. Unique commit `b48f13c`, its done ticket/evidence/review, and current source support `.10x/tickets/2026-07-18-restore-markitdown-control-character-normalization.md`.
- **No action:** exact-chunk dedup, alias citations, alias-only diff state, and dedup-specific stale deletion are retired by explicit user direction. The only current owner is the cancelled historical-provenance record `.10x/tickets/cancelled/2026-07-18-reconcile-website-exact-chunk-deduplication.md`.
- **No action:** historical compact-plan gains and namespace-deletion behavior do not prove current defects or requests. Their draft tickets were discarded; the path inventories retain their historical provenance.

## Precise deletion manifest

The following become deletion-safe only after the record-only preservation PR is merged into `develop`:

1. the linked worktree registration for `/Users/crlough/Code/personal/turbo-search.worktrees/thistle-site-test`;
2. the entire checkout directory `/Users/crlough/Code/personal/turbo-search.worktrees/thistle-site-test`, including every one of the 108 dirty paths enumerated in `dirty-path-inventory.tsv` and all ignored/cache/generated state beneath that checkout;
3. local branch `thistle-site-test`, only after item 1 is removed and the preservation PR is merged.

This manifest explicitly excludes Docker volumes/collections, remote Turbopuffer state, any other worktree/branch, and any path outside that checkout. It authorizes no deletion in the triage ticket.

## What this supports

The inventory, final disposition, Qdrant ticket cancellations, current repair owners, and deletion manifest satisfy the triage ticket's record-only acceptance criteria once independently reviewed and integrated.

## Limits and residual risk

- Historical test/evidence/review claims apply only to historical source; no current implementation behavior was rerun.
- Ignored/cache directory contents were classified as generated/local state by path and size, not exhaustively content-reviewed.
- Deletion remains blocked on independent review and merge of the preservation PR.
- External Docker/Qdrant and remote provider state remain deliberately uninspected and outside this manifest.
