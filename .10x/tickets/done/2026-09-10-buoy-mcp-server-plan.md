Status: done
Created: 2026-09-10
Updated: 2026-09-10
Parent: None
Depends-On: None

# Buoy MCP Server Plan

## Outcome and authority

Ship the owner-approved local stdio MCP interface: `retrieve(query,
namespaces?, top_k=5)`, `catalog_list(search?, include_all=false)`, and
`catalog_show(namespace)`, launched by `buoy mcp` with an optional MCP extra.
This is a parent plan, not an executable ticket.

The owner approved transport and tool categories, then explicitly approved the
concrete signatures, JSON/failure behavior, process-environment credentials,
normal read costs, retained worker/opt-in telemetry, no writes/new logging/
retries/client edits, and provider-free verification on 2026-09-10.

## Governing records

- `.10x/specs/buoy-mcp-stdio-server.md`
- `.10x/specs/buoy-mcp-retrieval-tool.md`
- `.10x/specs/buoy-mcp-catalog-tools.md`
- `.10x/research/2026-09-10-buoy-mcp-adapter-substrate.md`
- `.10x/specs/pi-worktree-development-flow.md`

## Child sequence and coherence

1. `.10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md`: SDK/CLI adapter,
   packaging, protocol/tool tests, and optional-extra CI coverage.
   Verify: fake-backed parity, error/privacy/cancellation tests, and existing
   regression gates. Independently review before moving to installed checks.
2. `.10x/tickets/done/2026-09-10-document-and-verify-buoy-mcp-installation.md`:
   consumer documentation plus base/extra distribution and installed stdio
   validation. Depends on child 1.
   Verify: source/installed discoverability, clean protocol lifecycle, accurate
   setup examples, package optionality, and preserved pre-existing changes.

Use one writer at a time on an isolated `work/*` task worktree based on current
`develop`; parent delegates each child rather than implementing it. Review can
be read-only, but no concurrent writer touches the same checkout. No parallel
implementation is needed for this small shared-module change.

Parent review maps every child criterion to evidence, resolves findings,
checks the three specs against actual tool schemas/results, records reusable
learning if any, and reconciles paths/statuses before closure. No child report
or mocked passthrough alone establishes installed protocol or search parity.

## Scope exclusions and execution gate

No HTTP/SSE/auth service, plan/apply/indexing/catalog mutation, arbitrary
command execution, additional filters/ranking controls, live provider test,
model download, client registration, global install, portable-skill rewrite,
release, tag, push, or merge. Existing routing thresholds and calibration are
not being re-certified or changed.

This preparation turn authors the initial specs/tickets only. Implementation
MUST begin in a subsequent turn. The initial checkout is dirty `main`; do not
implement there. Preserve the portable-skill work described in the research.
Normal isolated dependency installation/build/test artifacts are part of child
execution, not permission to mutate the user's installed Buoy or runtime home.

## Acceptance and evidence expectations

Both children complete with passing independent review; all three tools retain
CLI semantics and cannot dispatch writes; base/extra installation works; real
stdio smoke passes without provider/model work; Python 3.11/3.13 required tests
and lock/distribution gates are supported by recorded output; docs accurately
state local and remote side effects. Handoff records exact worktree/branch/head
and validation limits, without publication or integration claims.

## Blockers

None. Both children meet their approved criteria, both independent reviews
pass, and parent artifact/source/preservation/installed-smoke checks pass.
The scoped SDK compatibility repair is recorded and accepted; no product
behavior was invented. Live calls, client setup, hosted CI, integration and
publication remain explicit exclusions, not unfinished work under this plan.

## Progress and notes (append-only)

- 2026-09-10: Completed read-only source/record/official-SDK inspection. Both
  initial blockers (transport and read/write scope) were answered. The follow-up
  concrete contract checkpoint was explicitly approved. Authored three focused
  active specs and two bounded child tickets. No implementation, tests, builds,
  dependency installation, or provider operations performed.
- 2026-09-10: Read-only preparation checks passed for headers, trailing
  whitespace, and referenced record existence across all seven new records
  plus the amended focused-boundary spec. `git diff --check` passed; the
  source/test/CI/lock diff remained empty. These are record-hygiene checks,
  not evidence that an MCP server exists or works.
- 2026-09-10: At the owner's request, re-read all three MCP specs and this plan
  for a final pre-execution ambiguity check. Transport, exact tools/defaults,
  credential/read-cost boundary, retained worker/telemetry, output/failure
  behavior, and provider-free verification are settled. No additional
  user-decision blocker was found. Client setup, live validation, publication,
  and write operations remain excluded. Technical compatibility is still to
  be verified by the existing children; this check did not authorize or start
  execution.
- 2026-09-10: Owner authorized execution of the complete approved plan while
  away, with escalation for any new behavioral decision. A read-only
  `git ls-remote --heads origin develop` confirmed base
  `db5e8e1597e908c30fff76ec2aba565f1e2fbcbc`. Created branch
  `work/buoy-mcp-server` in
  `/Users/crlough/Code/personal/turbo-search.worktrees/buoy-mcp-server`.
  That worktree owns child execution/progress until parent reconciliation;
  this original-checkout copy remains the discovery pointer. No source edits
  or user-dirty-file transfers occurred during worktree setup.
- 2026-09-10: Committed only MCP-owned preparation records and original-worktree
  preservation hashes as task commit `6c9b6d8`. Dispatched the sequential
  implementation/review/fix then documentation/install/review workflow through
  pi-subagents. Canonical runtime workflow ID:
  `0aa4ba70-e2f0-4eaa-b29a-a698ece4d229`; mission ID:
  `93525524-681e-4ded-9441-0e2f57d52091`; observed state: active.
  Runtime artifacts are owned by pi-subagents; this plan indexes them.
  Native completion/attention notifications are the revisit trigger. Parent
  acceptance, evidence inspection, retrospective, record synchronization, and
  closure remain pending; no implementation success is claimed at dispatch.
- 2026-09-10: Runtime child reported signal-shutdown hangs with client stdin
  held open. Parent inspected installed MCP 2.2.0 `server/stdio.py`,
  `MCPServer.run_stdio_async`, AnyIO `AsyncFile.readline`, and the recorded
  SIGTERM/SIGINT test timeouts. Authorized a bounded compatibility repair:
  cancellable input passed to official SDK stdio framing, with the single
  `_lowlevel_server` serving seam if no public equivalent exists. Require
  consumer pin `mcp==2.2.0` if that private seam is used, exact lifecycle/stdout
  regression evidence, and no platform restriction or behavioral change.
  Supervisor request `1d171edc-4c56-4093-a8d3-d583a69ca80f` was answered;
  runtime ticket remains the owner and repair verification is pending.
- 2026-09-10: Investigated a long-bash attention notice without interrupting
  the worker. Parent directly read task-worktree raw logs
  `.10x/evidence/.storage/buoy-mcp-runtime/full-313-final.log` and
  `full-311-final.log`: each reports 1,339 tests, OK (113.612s and 141.531s).
  `mcp-third.log` reports all 12 MCP tests OK, including cancellation, EOF,
  SIGTERM, and SIGINT child cleanup. No task-related test process was visible
  in the bounded process check. Requested the runtime evidence/handoff rather
  than redundant broad reruns. These observations support progress, not final
  acceptance; exact-head evidence, independent review, and installed checks
  remain the execution tickets' responsibility.
- 2026-09-10: Original workflow ended with a worker WebSocket error after the
  clean scoped runtime commit `dba28f0` was saved. Parent inspected that commit,
  `.10x/evidence/2026-09-10-buoy-mcp-runtime.md`, and terminal workflow receipt;
  the receipt explicitly marks the runtime child resumable. No implementation
  was lost, but its final structured acceptance handoff was not received.
  Started one recovery continuation, workflow
  `6fcdfacb-b899-4e07-ba15-43d170274dee`, under the same mission. It resumes the
  original child only for evidence-header normalization and final attestation,
  then executes the already-planned independent review/fixes and installation
  phase. Original workflow remains a failed historical run, not a success.
  Recovery uses structured acceptance-report mode with checked writer evidence;
  no review, verification, or behavioral gate is waived.
- 2026-09-10: Recovery completed the runtime handoff. The first independent
  runtime review passed with no required correction; parent read and captured
  it as `.10x/reviews/2026-09-10-buoy-mcp-runtime-review.md`. Its limits explicitly
  reserve final exact-artifact installation and final-tree suite evidence for
  the dependent phase. Investigated the installation child's 240-second bash
  notice: an active isolated Python 3.13 full-suite process was visible within
  its sequential validation script, following the Python 3.11 checks. No
  confirmed hang or new behavioral blocker was established; do not interrupt
  merely because the multi-check batch exceeds the attention threshold.
- 2026-09-10: Successor workflow completed all four recovery/execution/review
  stages. Installation product commit `89cecb2` and evidence commit `9efef60`
  are retained on `work/buoy-mcp-server`. Both reviews pass with no findings.
  Parent reviewed material test assertions and current source/docs/specs,
  directly read both final 1,342-test logs, independently rehashed the tested
  wheel/sdist and original-file manifest, and reran base/extra installed smoke
  on CPython 3.11.10/3.13.0. All four runs passed. Current product bytes remain
  identical to tested commit `89cecb2`; live develop still resolves to `db5e8e1`.
- 2026-09-10: Completed retrospective and closure mapping in
  `.10x/evidence/2026-09-10-buoy-mcp-parent-acceptance.md`. Captured the SDK
  compatibility/strict-string/async-lifecycle lessons in
  `.10x/knowledge/buoy-mcp-sdk-compatibility.md` and refreshed existing
  installed-wheel identity knowledge. Removed only the three evidenced owned
  temporary roots after inspection/reruns, with literal absence checks; kept
  source worktree, archives, logs, and original user work. Both child tickets
  and this parent are done; terminal paths/references are reconciled. Final
  handoff is local only: no main/develop merge, push, release, global install,
  client registration, or live-provider operation. The original-checkout
  `.10x` copies will mirror the completed records for discovery; the canonical
  implemented source and commits remain in the task worktree/branch.
