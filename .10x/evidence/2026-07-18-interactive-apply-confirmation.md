Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Relates-To: .10x/tickets/2026-07-18-add-interactive-apply-confirmation.md, .10x/specs/interactive-apply-confirmation.md

# Interactive Apply Confirmation Implementation Evidence

## What was observed

- Apply mode selection rejects `--dry-run --approve` and plain non-TTY stdin before state-root resolution or plan selection. The diagnostic names `--dry-run` and `--approve`; a piped `yes` is not accepted.
- Explicit `apply --dry-run` remains prompt-free, model-free, credential-free, API-free, and non-mutating. Its JSON reports `approved=false`, `dry_run=true`, `cancelled=false`, `confirmation=not_requested`, `state_updated=false`, and `catalog_updated=false`.
- Plain TTY apply renders complete preflight before the exact stderr prompt `Apply this plan? [y/N] `. Surrounding whitespace and case are normalized, but only exact `y` or `yes` confirms.
- Enter, `no`, arbitrary input, EOF, prompt-read failure, and prompt-output failure exit 0 as safe cancellation. JSON stdout is one parseable object with `dry_run=false`, `cancelled=true`, `confirmation=declined_or_unavailable`, and false API/state/catalog effects; text states `Apply cancelled; nothing was written.`
- Call-order instrumentation observed visible preflight, prompt read, config loading, namespace-lock acquisition, approved revalidation, and model construction in that order. Interactive confirmation enters the unchanged `run_approved_apply` pipeline, whose protective state/lock/pending/content/catalog/cleanup suites remain passing.
- Obsolete `last-applied.json` and `legacy-json/last-applied.json` fixtures remained inode/size/mtime/byte identical through dry-run, cancellation, and confirmed interactive apply. Production source contains no obsolete-JSON recognition.
- Existing prompt-free `--approve`, stale deletion, depth-one batching/timing, lock contention, content/state/catalog ordering, pending recovery, plan retention/cleanup, and partial-success tests remain passing.

## Procedure

From `/Users/crlough/Code/personal/turbo-search.worktrees/add-interactive-apply-confirmation` on `work/add-interactive-apply-confirmation`:

```text
PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_apply_cli tests.test_catalog_pending tests.test_cli -q
# Ran 109 tests in 15.759s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_apply_cli tests.test_catalog_pending tests.test_cli -q
# Ran 109 tests in 15.193s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 413 tests in 21.382s — OK

PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
# Ran 413 tests in 19.343s — OK

DIST=$(mktemp -d /tmp/buoy-interactive-apply-dist.XXXXXX)
uv build --out-dir "$DIST"
uv run --python 3.13 python scripts/release_checks.py assets --dist "$DIST"
# Built and validated buoy_search-0.3.0.tar.gz and buoy_search-0.3.0-py3-none-any.whl.

rg -n 'last-applied\.json|legacy-json' src/buoy_search
# No matches (expected exit 1).

python3 -m compileall -q src tests scripts
# Exit 0.

git diff --check
# Exit 0.

git diff --name-only --cached
# Empty: no staged files at the validation checkpoint.
```

The full suites emit two expected warnings from existing cleanup safety tests that deliberately present plan paths under the state root; the suites still pass.

## What this supports or challenges

This supports the ticket's local behavior, output, ordering, compatibility, inert obsolete-state, and regression-preservation criteria on Python 3.11 and 3.13. It also supports reproducible distribution construction and source cleanliness.

## Limits

- All content/model/API effects were faked; no live Turbopuffer, credential-provider, catalog, namespace, or external data mutation occurred.
- Hosted pull-request check identities will be appended after the branch is pushed and the PR runs.
- Independent review is intentionally not performed by this implementation session; the ticket remains active.
