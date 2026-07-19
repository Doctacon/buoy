Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Target: .10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md
Verdict: pass

# Remove Legacy JSON Applied State Review

## Target

PR #36 at reviewed implementation head `67f47630993db1db6384b9f97354e37afd70628b`, governed by `.10x/tickets/done/2026-07-18-remove-legacy-json-applied-state.md`.

## Findings

Independent review confirmed:

- production applied-state paths, load, and save use only per-namespace DuckDB and lock paths;
- no production JSON discovery, parsing, migration, archive, deletion, or warning path remains;
- obsolete direct/archive JSON fixtures preserve device, inode, size, modification time, and bytes across plan, preflight, successful apply, and failed content apply;
- valid populated DuckDB remains authoritative; missing/valid-empty state remains first apply; schema/identity errors remain fail closed;
- `.turbo-search` state-root fallback remains intact and distinct from removed JSON applied-state compatibility;
- namespace lock, content writes, DuckDB commit, pending confirmation, and remote catalog sequencing are unchanged;
- docs and the project skill describe DuckDB-only authority and inert obsolete files;
- focused/full Python 3.11/3.13 suites and hosted build/test checks pass.

The parent additionally recorded temporary corrupt and permission-denied DuckDB probes, both of which raised `AppliedStateError`. No reviewer blocker remains.

## Verdict

Pass.

## Residual risk

Remote content/catalog interactions remain fake-backed; no live Turbopuffer operation was needed for this local state-format cutover. The permission-denied probe is platform-observed evidence rather than a committed regression, while schema and identity fail-closed behavior remains committed and protective.
