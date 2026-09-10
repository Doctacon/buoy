Status: active
Created: 2026-09-10
Updated: 2026-09-10
Parent: .10x/tickets/2026-09-10-buoy-mcp-server-plan.md
Depends-On: None

# Implement Buoy MCP Server

## Scope and cold-start context

Implement the three approved read-only MCP tools and stdio launch surface as a
thin adapter over existing CLI JSON. All read tools share the same protocol,
fixed subprocess boundary, and error/privacy handling, so this is one bounded
runtime outcome. No direct implementation on the current dirty `main` checkout.

Read completely before execution:

- `.10x/specs/buoy-mcp-stdio-server.md`
- `.10x/specs/buoy-mcp-retrieval-tool.md`
- `.10x/specs/buoy-mcp-catalog-tools.md`
- `.10x/research/2026-09-10-buoy-mcp-adapter-substrate.md`
- `.10x/specs/focused-buoy-boundary.md`
- `.10x/specs/pi-worktree-development-flow.md`

Follow referenced active semantic authority as needed before changing any
related behavior; none of routing, ranking, evidence, worker, or telemetry
implementation is in the write scope. Compare equivalent current CLI output,
not old docs or historical implementation-only contracts.

## Write boundary and design

Expected bounded paths:

- new `src/buoy_search/mcp.py` (or an equally small single module);
- `src/buoy_search/cli/entrypoint.py` for lazy dispatch;
- `src/buoy_search/cli/main.py` for top-level MCP help registration only;
- `pyproject.toml` optional extra and `uv.lock` exact dependency resolution;
- new `tests/cli/test_mcp.py`, plus narrowly affected parser/package tests;
- `.github/workflows/ci.yml` to exercise the extra in existing test jobs;
- this ticket and dedicated `.10x/evidence` / `.10x/reviews` records.

Do not copy the large retrieve orchestration into a new service. Use the same
interpreter's `-m buoy_search` with code-owned read commands, captured pipes,
no shell, and no interactive stdin. Tool names/arguments are the approved spec
signatures, not a general argv interface. Prefer the existing unittest/async
facilities; a new test framework is unnecessary. Declare optional runtime
dependencies actually imported by the adapter, without adding SDK CLI extras.

Base help and command dispatch must not require MCP. Tests must demonstrate
SDK validation/error behavior rather than assume type annotations alone reject
booleans, unknown arguments, or credential-bearing diagnostics. Preserve the
existing safe worker fallback warning without raw stderr passthrough.

## Assumption and side-effect provenance

| Item | Authority / boundary |
| --- | --- |
| Local stdio and three read tools | Owner's explicit 2026-09-10 checkpoints; focused MCP specs |
| API access and recipients | Existing process credential; returned data goes to the invoking MCP client, with no new ACL |
| Provider work / billing | Ordinary catalog/content reads may cost money; owner explicitly approved this runtime boundary |
| Remote state transitions / deletion | None; no mutation command or arbitrary dispatch exposed |
| Local lifecycle / retention | Existing inference worker and opted-in local telemetry only; no new durable query/result storage |
| Credentials | Process environment only; no `.env` loading, CLI-secret arguments, logs, or output |
| Retry / failure | No adapter retry; sanitized MCP errors; retained CLI partial/abstention and safe fallback behavior |
| Notifications / operations | MCP responses and safe stderr only; local launching user owns the process; no remote deployment |
| Execution verification | Owner-approved fakes/credential-free checks only; no live provider authorization |
| SDK implementation | Official MIT Python v2 API/Python compatibility inspected in substrate research |

## Acceptance criteria and checks

1. `buoy mcp`, help without extras, missing-extra diagnostics, optional SDK
   packaging, and exactly-three-tool discovery satisfy the transport spec.
2. Query/namespace/top-k and list/search/all/show schemas map to the exact
   allowed commands; invalid inputs and option-like data cannot invoke writes.
3. Fake-backed equivalent CLI and MCP results agree for automatic/single/multi
   retrieval, empty/partial/abstained/inconclusive outcomes, catalog filters,
   default/all lists, visible examples, hidden vectors/passages, and missing
   cards. Captured output alone is not the entire parity test.
4. A real SDK stdio handshake/discovery and invalid-input round trip passes
   with pure protocol stdout and no provider/model/runtime-asset side effects.
5. Command failures, malformed output, secret-bearing stderr/exception sentinels,
   safe worker warnings, cancellation/shutdown, and no adapter retries are
   covered. Adapter children terminate; shared worker lifecycle is not altered.
6. New MCP coverage runs in Python 3.11/3.13 CI with the extra installed.
   Existing unittest discovery, ranking-contract/promotion/C6 checks, lock
   validation, and diff hygiene retain their assertions and pass as applicable.
7. Independent review records no unresolved significant finding, and raw
   verification facts are recorded with exact command, interpreter/SDK version,
   source diff/head, results, and limits. Do not claim installed-wheel acceptance
   until the dependent child supplies it.

## Exclusions, dependencies, and blockers

All parent/spec exclusions apply. Consumer docs and final clean installed-wheel
validation belong to the dependent child; keep runtime results reviewable for
that handoff. No package release/version change, source reorganization, user
runtime modification, or repair of unrelated existing work.

Blockers: None in the approved contract. Revalidate the current task base before
editing; open a blocker for source/spec or SDK incompatibility that would change
scope/acceptance. Implementation begins only in a subsequent turn after this
initial ticket/spec authoring turn.

## Progress and notes (append-only)

- 2026-09-10: Opened from the explicitly approved contract. Source seams, SDK
  v2.2.0 availability, original dirty work, and planned checks are documented.
  No implementation or verification has run.
- 2026-09-10: Owner authorized execution. Assigned to the single writer in
  `/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server`
  on `work/buoy-mcp-server`, based on live-confirmed develop `db5e8e1`.
  Follow that worktree's copy for active execution progress; the original
  checkout remains untouched except this workstream's `.10x` records.
