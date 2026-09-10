Status: open
Created: 2026-09-10
Updated: 2026-09-10
Parent: .10x/tickets/2026-09-10-buoy-mcp-server-plan.md
Depends-On: .10x/tickets/2026-09-10-implement-buoy-mcp-server.md

# Document and Verify Buoy MCP Installation

## Scope and dependencies

Complete the consumer-facing installation/documentation and distribution
verification for the implemented read-only stdio adapter. Execute after the
runtime child has reviewable passing evidence, on the same isolated work branch
with one writer. Do not implement on the original dirty main checkout.

Read completely:

- `.10x/specs/buoy-mcp-stdio-server.md`
- `.10x/specs/buoy-mcp-retrieval-tool.md`
- `.10x/specs/buoy-mcp-catalog-tools.md`
- `.10x/research/2026-09-10-buoy-mcp-adapter-substrate.md`
- `.10x/tickets/2026-09-10-implement-buoy-mcp-server.md` and its evidence/review
- `.10x/specs/pi-worktree-development-flow.md`

## Write boundary

New `docs/mcp.md`, one README Learn more link, narrowly required package/smoke
tests under the existing concern layout, and a bounded CI installed-extra
smoke step if needed. This ticket also owns its evidence/review and progress
records. Preserve all pre-existing README/pyproject/skill edits and do not
rewrite the release-pinned skill to advertise unreleased MCP behavior.

An exposed runtime defect remains owned by the runtime child. Report/block or
return that child for repair rather than silently widening this ticket.

## Acceptance criteria

1. Documentation shows a verified source-checkout optional-extra installation
   and `buoy mcp` command; until an MCP-bearing release exists, it does not
   claim that v0.6.5 or another published tag already includes MCP.
2. An agent-neutral configuration example names `buoy` with args `["mcp"]`
   without storing credentials. Explain executable path and environment
   inheritance differences between clients. No user's client files are edited.
3. All tool signatures/defaults, automatic versus explicit routing, no-write
   boundary, structured cited evidence/partial/abstained outputs, sanitized
   errors, and omitted vector/passage-bank fields match tested source schemas.
4. Docs state that initialization/discovery are provider-free, valid calls can
   incur Turbopuffer reads, credentials come from process environment, `.env`
   is not auto-loaded, and existing worker/local opt-in telemetry effects
   remain. They do not call live retrieval filesystem-free or cost-free.
5. Build wheel/sdist into an isolated output location. Inspect the optional
   extra and included adapter; preserve existing internal-artifact exclusions.
   Smoke-install the same wheel both without and with the MCP extra in
   disposable environments, without replacing the user's installed tool.
6. Base install still supports normal CLI/help and a clear missing-extra
   error. Extra install supports a real SDK stdio initialize/tools-list,
   invalid-input or missing-credential error, and clean shutdown. No network
   provider/model work or persistent user HOME assets occur during smoke.
7. Existing and new required Python 3.11/3.13 tests, dependency-lock checks,
   applicable ranking/C6 gates, and `git diff --check` pass. Inspect commands
   before running them; constrain HOME, caches, artifacts, and optional test
   dependencies to the task/disposable execution boundary. Never download a
   model merely to make this ticket green; report an actual blocked gate.
8. Independent review maps the installed behavior and docs to the specs.
   Evidence records exact artifact digests, interpreter and MCP versions,
   commands/results, negative privacy/provider observations, and cleanup.
   Handoff identifies branch/head/diff and preserves original dirty work.

## Exclusions and blockers

No live account smoke, model download, indexing/catalog mutation, global
installation, client registration, released skill update, release/tag/push,
merge, HTTP service, or unrelated documentation cleanup. Dependency package
fetches for isolated installs are permitted execution mechanics, not authority
for provider data access or model acquisition.

Blockers: None beyond the declared runtime-child dependency. Work is not ready
for execution until that dependency has passing reviewable evidence. If an
installed behavior contradicts a spec, preserve the finding and return it to
its existing owner rather than narrowing acceptance after the fact.

## Progress and notes (append-only)

- 2026-09-10: Opened the bounded documentation/installed-verification follow-on
  in the initial spec-first preparation turn. No documentation implementation,
  build, installation, tests, or live operations performed.
