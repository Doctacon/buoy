Status: active
Created: 2026-09-10
Updated: 2026-09-10

# Buoy MCP Stdio Server

## Purpose and authority

Expose Buoy's existing retrieval and catalog reads to a local MCP client. On
2026-09-10 the owner selected local stdio and search/catalog reads, then
explicitly approved the concrete three-tool contract, launch command, optional
SDK dependency, credential/read-cost boundary, retained worker/telemetry,
sanitized failures, and provider-free verification described below.

This is an additive interface to `.10x/specs/focused-buoy-boundary.md`, not a
restoration of the Command Center, HTTP API, jobs, or Kite orchestration.
Tool behavior is owned separately by:

- `.10x/specs/buoy-mcp-retrieval-tool.md`
- `.10x/specs/buoy-mcp-catalog-tools.md`

## Launch and packaging

1. `buoy mcp` MUST serve MCP over stdio until the client disconnects or the
   process is stopped. There MUST be no HTTP/SSE listener, port, remote auth
   service, automatic reconnection, or background MCP daemon.
2. Use the official MIT-licensed Python `mcp` SDK, with the optional package
   extra named `mcp`. The inspected stable substrate is `mcp>=2.2,<3`; resolve
   and lock the exact compatible release during implementation. Do not add the
   SDK's CLI extra, a Node runtime, or a second MCP framework.
3. Base Buoy installation and existing commands MUST remain usable without the
   optional extra. `buoy --help` MUST advertise `mcp`. `buoy mcp --help` MUST
   work without credentials or the SDK. Missing SDK at actual launch MUST
   produce an actionable, value-free installation diagnostic and nonzero exit,
   not a traceback or an automatic install.
4. Startup, import, help, MCP initialization, and tool discovery MUST NOT read
   provider state, load models, start workers, or create Buoy runtime assets.
5. Server identity is Buoy with the installed Buoy package version. Exactly
   `retrieve`, `catalog_list`, and `catalog_show` are callable tools. No
   resources, prompts, general command runner, or hidden write tool is added.

## Execution boundary

The adapter MUST delegate to fixed read-only CLI commands in a subprocess
using the same Python interpreter and installed Buoy package. This preserves
current routing, evidence, worker, provider accounting, and opt-in telemetry
without copying the CLI orchestration into another implementation.

- Use an argument vector, never a shell. Only code-owned `retrieve`, `catalog
  list`, and `catalog show` argv prefixes are allowed. Values beginning with
  `-`, quotes, newlines, or shell metacharacters remain data, never options or
  executable syntax. Use option/value binding and positional `--` boundaries.
- The command child MUST NOT inherit the MCP stdin/stdout descriptors. It gets
  no interactive input; stdout/stderr are captured separately. MCP stdout
  MUST contain protocol messages only, including startup and shutdown.
- Tool calls inherit the process environment; credentials are not tool
  arguments, argv values, configuration files, logs, or results. `.env` is not
  auto-loaded. The server adds no account/namespace ACL and grants no access
  beyond the existing credential's provider access.
- There is one CLI invocation per accepted tool call. The adapter MUST NOT
  retry a failed invocation, repeat provider operations, or invent recovery.
  Existing CLI/provider retry and worker-fallback policies are unchanged.
- Protocol cancellation or server shutdown MUST clean up the adapter-owned
  command child. It MUST NOT kill a shared Buoy inference/telemetry worker or
  change those existing workers' idle lifetimes. Do not add an independent
  product timeout or worker pool in this slice.

## Results, diagnostics, and privacy

Successful CLI JSON objects MUST be returned as MCP structured content and a
JSON text content block representing the same object. No field filtering,
answer generation, ranking changes, or omission of partial/evidence outcomes
is permitted. The CLI remains the producer of these objects.

Invalid input, nonzero command exit, process failure, and malformed/non-object
JSON MUST be errors, never empty successful retrievals. Tool execution errors
MUST use MCP `isError` with sanitized actionable text. Protocol-level errors
remain the SDK's responsibility. Do not forward raw stderr, traceback,
exception chains, environment values, or malformed stdout to clients/logs.
Missing credentials may name `TURBOPUFFER_API_KEY`, never its value.

The established content-free worker fallback warning MUST remain visible once
on stderr when emitted by a command. Only that known safe diagnostic may be
forwarded verbatim; this is not authority to forward arbitrary command stderr.
The exact existing warning is recorded in the substrate research.

The adapter MUST add no request/result log, durable cache, exporter, telemetry
schema, provider write, or model-download workflow. Existing retrieve worker
and opt-in local telemetry behavior is retained, not described as filesystem-
free. Read-only tool annotations MUST describe the absence of index/catalog
mutations without claiming provider-free execution or absence of local worker
and opt-in telemetry effects.

## Consumer documentation

A focused `docs/mcp.md` and one concise README link MUST explain optional-extra
installation, `buoy mcp`, the three tools, and an agent-neutral launch example:

```json
{"mcpServers":{"buoy":{"command":"buoy","args":["mcp"]}}}
```

Explain that clients differ in configuration location/environment inheritance;
the operator must supply the environment to the launched server, using an
absolute executable path if needed. Do not embed a real credential or promise
shell-variable interpolation in JSON. Do not edit any client configuration.
Document source-checkout installation until an MCP-bearing release actually
exists; do not advertise the existing v0.6.5 release as containing this feature.
The release-pinned portable skill remains outside this change.

## Acceptance and exclusions

- A real SDK stdio client can initialize, discover exactly the three tools,
  receive a provider-free validation error, and disconnect cleanly.
- Tests prove fixed argv, value containment, cancellation cleanup, pure
  protocol stdout, result parity, and secret/raw-error non-disclosure.
- Optional-extra tests run in normal Python 3.11/3.13 CI rather than silently
  skipping all MCP coverage. Base-package and extra-installed smoke checks
  both remain covered; existing protective tests are retained.
- Distribution inspection and isolated installation prove the advertised
  entrypoint and optional dependency, with temporary HOME/cache/runtime paths.
- Verification uses fake providers/models and credential-free protocol checks.
  No live Turbopuffer call, model download, global install, client registration,
  release, tag, push, or merge is authorized by this contract.
