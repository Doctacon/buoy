Status: accepted
Created: 2026-08-17
Updated: 2026-08-17
Amends: .10x/decisions/duckdb-only-applied-state-hard-cutover.md

# Buoy Defaults Local Assets to One User Home

## Context

Buoy is installed as one user-global `uv` tool, but its implicit local paths
are relative to the process working directory. Running the same executable
from separate repositories therefore creates independent `.buoy` state roots
and `artifacts/site-crawls` trees. It also makes argument-free `buoy apply`
discover a different plan set depending on where the shell happens to be.

The repository owner wants new Buoy-owned local assets to have one predictable
machine location and explicitly does not want any existing project-local state
or artifacts migrated, copied, merged, backfilled, deleted, or otherwise
reconciled.

## Decision

When the user omits path overrides, Buoy uses the absolute user home
`~/.buoy` as its application home:

```text
~/.buoy/
  state/<source-id>/<namespace>/state.duckdb
  artifacts/site-crawls/<source-derived-plan-or-crawl-directory>/
```

The established `--state-root`, `--out-dir`, and `--plan` flags remain the
only path overrides and retain their existing semantics. An explicit relative
path remains relative to the invocation directory because the user selected
it deliberately.

Implicit resolution never scans, selects, copies, moves, merges, deletes, or
rewrites noncanonical working-directory `.buoy`, `.turbo-search`, or
`artifacts/site-crawls` trees. Those existing assets remain byte-inert unless
the operator selects them through an explicit flag. Explicit selection retains
the normal state-write and verified plan cleanup/supersession lifecycle; it is
not an implicit migration or backfill.

If the process working directory is the user's home, its `.buoy` spelling is
the canonical application home itself rather than a distinct project-local
root. This machine had no such path at the initial inventory boundary, so the
forward-only change adopts no pre-existing home-root asset here.

Default crawl and plan leaf naming remains source-derived and deterministic.
Crawl leaves retain their established names; plan leaves end in `-plan` for
every source kind, including database relations, so a crawl and a plan cannot
collide in the shared machine-global tree.
Argument-free apply discovers supported plans only beneath the user-global
artifact root. If more than one pending supported plan exists, apply fails
closed and requires `--plan` rather than silently choosing one machine-global
candidate.

The canonical global plan tree is a narrowly managed exception to the prior
whole-state-root cleanup guard. Existing exact-plan verification, inode
binding, no-follow deletion, namespace matching, and success-only lifecycle
rules remain mandatory. Cleanup may delete only fully verified plan
directories strictly below the canonical global artifact root; it continues
to reject `~/.buoy/state/**`, the application-home root itself, every other
application-home subtree, explicit noncanonical plans under a state root,
malformed artifacts, and replaced or symlink targets.

Package-manager files and shared dependency/model caches remain owned by `uv`
and Hugging Face in their standard user-global locations. Credentials remain
environment-only. Remote namespaces, rows, schemas, plan identities, row IDs,
and routing behavior do not change solely because local defaults move.

## Consequences

Commands launched from different directories share the same future
incremental ledger, namespace lock, pending-plan set, and default crawl output.
The first plan under the new global home has first-apply semantics when that
global ledger does not exist; ignored project ledgers are not consulted to
infer prior rows or stale deletions. Operators intentionally using multiple
remote accounts or regions must continue to provide separate explicit state
and artifact roots; remote-target identity is not added to the DuckDB schema
by this task.

Existing project-local assets remain exactly where they are unless the user
later opts into one explicitly. Installing a later tool build does not touch
them implicitly, and the implementation contains no automatic migration,
import, archive, garbage collection, or deletion path for them. An explicitly
selected old plan may still be consumed by the established success-only plan
cleanup, and an explicitly selected state root receives the requested normal
state writes.

## Authorization boundary

On 2026-08-17 the repository owner explicitly directed implementation on a
new branch from `develop`, requested forward-only behavior, and reserved
integration for later personal review. This authorizes bounded local source,
test, documentation, records, validation, branch, commit, push, and ordinary
pull-request handoff work. It does not authorize mutation of existing local
assets, provider/catalog/content operations, credential access, tool
installation, integration into `develop` or `main`, release publication,
tagging, or GitHub Release/protection changes.
