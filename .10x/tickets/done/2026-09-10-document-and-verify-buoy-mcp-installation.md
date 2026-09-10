Status: done
Created: 2026-09-10
Updated: 2026-09-10
Parent: .10x/tickets/done/2026-09-10-buoy-mcp-server-plan.md
Depends-On: .10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md

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
- `.10x/tickets/done/2026-09-10-implement-buoy-mcp-server.md` and its evidence/review
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

Blockers: None. The runtime dependency and all eight installation criteria
are satisfied by recorded evidence and independent review. No runtime repair
or behavioral change was needed in this dependent slice.

## Progress and notes (append-only)

- 2026-09-10: Opened the bounded documentation/installed-verification follow-on
  in the initial spec-first preparation turn. No documentation implementation,
  build, installation, tests, or live operations performed.
- 2026-09-10: Runtime independent review passed; dependent execution begun on
  `work/buoy-mcp-server` at `f9ddf19`. Added source-only installation guidance,
  agent-neutral configuration and tested-tool documentation, exactly one README
  link, source-named schema/docs checks and clean installed-wheel stdio smoke.
  Existing base tokenizer/data smoke remains intact; installed-extra CI coverage
  is additive. No runtime/spec/package/skill behavior changed. Final committed
  build, isolated base/extra installs and required offline gates follow.
- 2026-09-10: Committed implementation as `89cecb2ed0bf5279b0bbedb5cc42cd342d2885a0`.
  Clean wheel/sdist version `0.5.2.dev131+g89cecb2ed` built and inspected; the same
  wheel passed four isolated base/extra installs across Python 3.11.10/3.13.0.
  Real SDK client and guarded raw stdio initialize/discovery/invalid errors,
  EOF/SIGINT/SIGTERM passed without provider/model/runtime assets. Both final
  full suites passed 1342 tests, with lock/ranking/promotion/C6 and unchanged
  base tokenizer/data smoke passing. All nine original preservation entries
  still match, including the old ticket's absence. Evidence and byte-for-byte
  artifacts are recorded in `.10x/evidence/2026-09-10-buoy-mcp-installation.md`
  and its `.storage/buoy-mcp-installation/` directory. No runtime owner repair
  was needed. Ticket remains active for parent independent review/closure;
  no live provider/model validation, hosted CI, Windows or release is claimed.
- 2026-09-10: Parent closure: the independent installation review passed with no
  findings and is preserved at
  `.10x/reviews/2026-09-10-buoy-mcp-installation-review.md`. Parent re-read all
  eight criteria, checked current product bytes still equal tested `89cecb2`,
  rehashed both retained artifacts and original-file preservation entries, and
  independently reran all four installed base/extra combinations successfully.
  The complete acceptance map and literal temporary-root cleanup observations
  are `.10x/evidence/2026-09-10-buoy-mcp-parent-acceptance.md`.
  Retrospective updated the existing installed-wheel identity knowledge rather
  than leaving stale editable-version learning only in logs. Specs, docs,
  schemas, evidence, and review agree; no in-scope blocker remains. Closed for
  the local work branch only, without integration/publication/client-install
  authority or a live-provider/Windows/hosted-CI claim.
