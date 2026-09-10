Status: done
Created: 2026-09-10
Updated: 2026-09-10

# Buoy MCP Adapter Substrate

## Question and method

Can a small local MCP adapter reuse current Buoy behavior without rebuilding
routing, adding a remote service, or exposing writes? Read-only repository
inspection and official SDK/PyPI documentation were performed on 2026-09-10.
No dependency installation, build, test, Buoy command, credential access,
provider operation, worktree creation, or client configuration change occurred.

## Repository findings

- Broad searches of `.10x` (including terminal/superseded tickets), source,
  tests, docs, and packaging found no MCP implementation or existing MCP owner.
- `pyproject.toml` defines Python >=3.11, the `buoy` console entrypoint, and
  optional warehouse extras, but no MCP dependency. Source is Python; adding
  an independent TypeScript server would duplicate packaging unnecessarily.
- `src/buoy_search/cli/entrypoint.py` is lightweight and already diverts
  telemetry before importing the provider-facing CLI. `__main__.py` invokes
  that entrypoint. It is a suitable lazy dispatch seam for `buoy mcp`.
- `src/buoy_search/cli/main.py::_run_retrieve` owns automatic/explicit routing,
  command telemetry, worker policy/fallback, evidence handling, and rendering.
  Calling the lower-level retriever alone would miss those behaviors.
  `--json` returns the result object's `to_dict()`; default top-k is 5.
- `src/buoy_search/cli/catalog.py::_run_list/_run_show` already produce JSON.
  List accepts optional canonical substring search and `--all`; show has an
  optional vector flag which the approved adapter must not expose.
  Both call `card_to_dict(..., include_routing_passages=False)`; normal output
  hides vectors but may retain reviewed `routing_examples`.
- Some CLI error paths print exception-derived strings. Capturing a command's
  stderr is not proof it is safe to forward. MCP failures need bounded,
  value-free messages rather than arbitrary stderr passthrough.
- The source's exact safe worker fallback warning is:
  `Warning: local embedding worker failed; using in-process embedding for this command.`
  Preserve this content-free warning once, not arbitrary surrounding stderr.
- `.github/workflows/ci.yml` runs standard-library unittest discovery on Python
  3.11/3.13 after base `uv sync --locked`, then builds and smoke-installs a base
  wheel. MCP extras must be exercised explicitly without losing base coverage.

Current source checkout: `main` at `2d33598`, behind the locally recorded
`origin/main` by one commit; local `develop`/`origin/develop` at `db5e8e1`.
Only this main worktree exists. Local develop-to-main source, tests, packaging,
lock, and CI had no differences; README/releasing-doc differences do exist.
These are local observations, not a freshness claim about GitHub.

Existing dirty work belongs to the portable-skill workstream: README release
v0.6.5/skill link, `pyproject.toml` skill-artifact exclusion, `skills/`, and
corresponding `.10x` terminal/evidence/spec/review changes. Do not stage, revert,
copy wholesale, or claim ownership of that work. Its owner is
`.10x/tickets/done/2026-09-05-ship-portable-buoy-agent-skill.md`.

## External sources and findings

Official sources inspected on 2026-09-10:

- https://github.com/modelcontextprotocol/python-sdk — `main/README.md` and
  `main/pyproject.toml` via raw GitHub content; MIT, Python >=3.10, stable v2.
- https://pypi.org/pypi/mcp/json — metadata reported `2.2.0`, non-yanked,
  Python >=3.10, and `mcp-types==2.2.0` among runtime requirements.
- https://py.sdk.modelcontextprotocol.io/get-started/
- https://py.sdk.modelcontextprotocol.io/get-started/first-steps/
- https://py.sdk.modelcontextprotocol.io/run/
- https://py.sdk.modelcontextprotocol.io/servers/tools/

The current server API is `from mcp.server import MCPServer`, decorated typed
tools, and `run(transport="stdio")`. It supports structured and text results,
input schemas/validation, and in-memory `Client(server)` testing. Stdio is the
default; no HTTP service is needed. The docs explicitly warn that pre-serving
or buffered stdout can corrupt the wire even with the SDK's own redirection.

The initially consulted `v1.x` README describes a maintenance line, not the
current API; do not implement against remembered FastMCP-v1 examples. Old
`docs/server.md`, `docs/testing.md`, and singular `/server/` web routes did not
resolve; current documentation uses the URLs above. These were documentation
lookup dead ends, not project defects.

## Conclusion and limits

Use the official optional SDK with fixed, shell-free subprocess calls to the
existing CLI JSON surface. This spends process-launch overhead to preserve
existing command isolation, inference reuse, telemetry, and search semantics.
Do not add a parallel service layer, arbitrary CLI tool, or managed service.
A future extraction needs a named requirement; no throughput/SLA claim was
measured here. Dependency resolution and cancellation/stdio behavior still
require the planned implementation tests, not trust in SDK descriptions.

SDK/doc findings are technical evidence only. Product ratification is the
owner's subsequent explicit approval of the concrete v1 contract, recorded in
`.10x/specs/buoy-mcp-stdio-server.md`,
`.10x/specs/buoy-mcp-retrieval-tool.md`, and
`.10x/specs/buoy-mcp-catalog-tools.md`. Implementation/verification is owned by
`.10x/tickets/2026-09-10-buoy-mcp-server-plan.md`; none is claimed complete.
