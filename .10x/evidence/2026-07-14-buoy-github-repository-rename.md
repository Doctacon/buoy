Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-buoy-github-repository-rename.md, .10x/decisions/buoy-product-identity-and-compatibility.md

# Buoy GitHub Repository Rename

## Raw evidence

Sanitized structured before/after observations are retained at `.10x/evidence/.storage/2026-07-14-buoy-github-repository-rename.json`. No token, credential, or secret value is stored.

## What was observed

Read-only preflight confirmed:

- GitHub authentication was active for account `Doctacon` with repository scope; no token value was printed or retained.
- The exact source was the public repository `Doctacon/turbo-search`, default branch `main`.
- `Doctacon/buoy-search` did not resolve before mutation, supporting target availability.
- The code-level integration dependency was already done with pass evidence/review.

The exact authorized command shape completed successfully:

```text
gh repo rename -R Doctacon/turbo-search buoy-search --yes
```

Afterward:

- `gh repo view Doctacon/buoy-search` reported canonical `Doctacon/buoy-search` at `https://github.com/Doctacon/buoy-search`.
- The new HTTPS endpoint returned 200.
- The old HTTPS endpoint returned 301 with `Location: https://github.com/Doctacon/buoy-search`.
- `gh repo view Doctacon/turbo-search` resolved to the new canonical repository.
- Local `origin` fetch and push URLs both became `git@github.com:Doctacon/buoy-search.git`; `git ls-remote --symref origin HEAD` resolved `main` successfully.
- Repository description was updated from stale pre-brand copy to `Plan, index, and search public knowledge sources with anchored citations.`
- `pyproject.toml` now records canonical Repository and Issues project URLs. A fresh wheel build exposed both as `Project-URL` metadata.

The one current-surface old GitHub URL in `autoresearch/experiments/repo-search-live-baseline.json` was intentionally preserved: it identifies the original source of an existing pre-rebrand applied namespace, not the current canonical repository link.

## Procedure

1. Inspected the active ticket, identity decision, and done integration evidence.
2. Ran sanitized auth status and exact source/target repository preflight.
3. Executed the one authorized rename.
4. Verified canonical repository identity, new endpoint, old redirect, and default branch.
5. Updated both local origin URLs.
6. Added canonical package project URLs and updated the external repository description.
7. Built wheel/sdist in a temporary directory and verified canonical `Project-URL` metadata.
8. Ran `git diff --check`, `uv lock --check`, and current-link scans.

## What this supports or challenges

Supports every external rename acceptance criterion without package publication, release creation, branch/tag/issue mutation, organization transfer, or Turbopuffer calls.

## Limits

- The working tree contains extensive inherited rebrand changes and eleven inherited staged documentation paths. This task preserved the index and changed only the external repository/remote, `pyproject.toml` canonical URLs, ticket/evidence records, and repository description.
- GitHub redirect behavior was observed immediately after rename; GitHub controls its future redirect lifecycle.
- No push was performed; `git ls-remote` verified read access and canonical remote resolution without changing branches.
- Independent review is still required before ticket closure.
