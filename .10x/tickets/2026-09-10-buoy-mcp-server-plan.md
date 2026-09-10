Status: active
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

1. `.10x/tickets/2026-09-10-implement-buoy-mcp-server.md`: SDK/CLI adapter,
   packaging, protocol/tool tests, and optional-extra CI coverage.
   Verify: fake-backed parity, error/privacy/cancellation tests, and existing
   regression gates. Independently review before moving to installed checks.
2. `.10x/tickets/2026-09-10-document-and-verify-buoy-mcp-installation.md`:
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

None in the ratified product contract. Worktree creation, SDK resolution, and
verification remain execution steps, not evidence of completion. If the current
integration base materially differs or a required SDK behavior fails, block the
owning child rather than invent a new behavior.

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
