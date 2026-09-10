Status: done
Created: 2026-09-10
Updated: 2026-09-10
Parent: .10x/tickets/done/2026-09-10-buoy-mcp-server-plan.md
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

Blockers: None. All seven runtime criteria are supported by the runtime and
final installed evidence, independent review, and parent acceptance mapping.
The SDK compatibility issue was repaired within the approved behavioral
contract, without changing retrieval semantics or weakening shutdown checks.

## Progress and notes (append-only)

- 2026-09-10: Opened from the explicitly approved contract. Source seams, SDK
  v2.2.0 availability, original dirty work, and planned checks are documented.
  No implementation or verification has run.
- 2026-09-10: Owner authorized execution. Assigned to the single writer in
  `/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server`
  on `work/buoy-mcp-server`, based on live-confirmed develop `db5e8e1`.
  Follow that worktree's copy for active execution progress; the original
  checkout remains untouched except this workstream's `.10x` records.
- 2026-09-10: Runtime implemented in the assigned worktree: optional official SDK,
  lazy launch/help, exactly three strict typed read tools, fixed CLI subprocess
  mapping, sanitized diagnostics, safe warning preservation, and cancellation /
  EOF / SIGTERM / SIGINT child cleanup. No retrieval/catalog/worker semantics or
  consumer docs changed.
- 2026-09-10: SDK compatibility blocker found and resolved with live supervisor
  approval: SDK 2.2.0's default stdio thread blocks signal shutdown; AnyIO's
  non-daemon pool also blocks interpreter finalization even when abandoned.
  Approved exact consumer pin `mcp==2.2.0`, one underlying SDK serving seam,
  and cancellable owned unbuffered input while retaining SDK framing/stdout
  protection. The pin/workaround removal condition and failing evidence are in
  `.10x/evidence/2026-09-10-buoy-mcp-runtime.md`. No spec was rewritten.
- 2026-09-10: Both full credential-free/offline suites passed 1339 tests on
  CPython 3.11.10 and 3.13.0. Final narrow SDK literal-JSON-search preservation
  change passed all 12 MCP tests on both. Lock, ranking-contract, explicit-base
  promotion, C6, base-without-extra smoke, build/metadata inspection, original
  preservation hashes, and diff hygiene passed. Raw failure/repair history and
  reviewer source diff are under `.10x/evidence/.storage/buoy-mcp-runtime/`.
  All runtime checks are fake-backed/credential-free; no model downloads or
  live provider operations. Ticket stays active for parent independent review
  and dependent consumer/installed-wheel acceptance. Blockers: none remaining
  in runtime implementation; independent review not yet performed.
- 2026-09-10: Recovered final runtime handoff after the orchestration WebSocket
  connection failed following clean implementation commit
  `dba28f01076f81bdad01ea46edf934abc7d15597`. Reconfirmed saved full/focused test
  logs and authoritative versions; no broad checks rerun and no source, test,
  packaging, CI, or governing spec changed. Normalized only the evidence record's
  required 10x headers and retained its observed facts. Recovery diff hygiene
  checked; final structured attestation restored for parent independent review.
  Ticket remains active; consumer docs and clean installed-wheel acceptance
  remain with the dependent phase.
- 2026-09-10: Parent closure: independent runtime and installation reviews pass
  with no required findings. Final product commit `89cecb2` retains runtime
  implementation `dba28f0`; final 1,342-test suites pass on both required Python
  versions. Parent independently verified artifact/source bytes, original-file
  preservation, and all four installed base/extra smoke combinations. Every
  criterion maps to `.10x/evidence/2026-09-10-buoy-mcp-parent-acceptance.md`;
  `.10x/reviews/2026-09-10-buoy-mcp-runtime-review.md` records the runtime review.
  Retrospective preserved SDK/input/async-lifecycle constraints in
  `.10x/knowledge/buoy-mcp-sdk-compatibility.md` and installed-identity learning
  in the existing reproducible-installed-wheel knowledge record. No material
  spec drift or remaining in-scope blocker. Closed for the implemented local
  work branch; no hosted CI, integration, live account validation, or release
  is claimed or authorized by closure.
