Status: active
Created: 2026-09-10
Updated: 2026-09-10

# Buoy MCP SDK Compatibility

## Current integration boundary

Buoy's local MCP adapter invokes only fixed CLI JSON read commands through the
same interpreter. This preserves the CLI's routing/evidence, worker, and opt-in
telemetry behavior. Do not substitute direct retriever calls without accounting
for the orchestration they would omit.

The optional dependency intentionally pins **mcp==2.2.0**. Two SDK behaviors
required explicit adaptation; neither is permission to fork the protocol or
weaken Buoy's approved inputs/lifecycle:

- SDK stdio uses an AnyIO AsyncFile reader whose blocked read is not cancelled
  by a signal. Command cleanup can succeed while the server interpreter hangs
  with client stdin still open. Abandoning an AnyIO threadpool read is not
  sufficient: non-daemon threads still hold interpreter shutdown. Buoy uses an
  owned duplicated unbuffered input fd and daemon read, retains SDK framing and
  stdout protection, and calls the pinned SDK's `_lowlevel_server` serving seam.
  Do not close/recycle a descriptor under an abandoned read or replace the
  unbuffered fd with a buffered stdin object without finalization tests.
- SDK `FuncMetadata.pre_parse_json` interprets strings such as `"null"` as JSON
  values. Buoy's typed string inputs must retain those literal values. Its
  metadata override disables this convenience parsing; strict raw validation
  also rejects unknown fields and coercions before SDK diagnostics can echo
  caller input.

These are narrow compatibility repairs, not product behavior changes. The
private serving seam/pin was approved by the parent after inspecting the
installed SDK and failing lifecycle evidence. Independent runtime and installed
reviews accepted the final boundary. There is no pending upgrade or alternate
server work under this delivery: retaining the tested pin is the explicit
no-action choice, not an untracked follow-up.

## Verification lessons

Test **actual interpreter exit**, not merely cancellation of a coroutine:
protocol cancellation followed by another request; EOF; SIGINT/SIGTERM with the
client's input pipe open; owned command reaping; shared-process survival; and
absence of non-protocol stdout/finalization stderr. Include split UTF-8/CRLF,
literal JSON-looking strings, fake-backed actual CLI output/operation parity,
and a genuinely installed wheel, not only mocked subprocess output.

An AnyIO-backed MCP Client context must enter and exit in the same async task.
Standard-library unittest async setup and teardown can use different tasks;
keep the client context inside each async test rather than bridging those hooks.

Before changing the SDK pin or removing either adapter, prove the replacement
behavior against the same lifecycle, strict-input, privacy, and installed-wheel
tests. Tests here ran on macOS with CPython 3.11.10/3.13.0, MCP/mcp-types 2.2.0,
AnyIO 4.14.0, and Pydantic 2.13.4; no Windows or hosted-CI execution is implied.

Sources: `src/buoy_search/mcp.py`, `tests/cli/test_mcp.py`,
`tests/core/mcp_installation_smoke.py`,
`.10x/evidence/2026-09-10-buoy-mcp-runtime.md`, and
`.10x/evidence/2026-09-10-buoy-mcp-installation.md`.
