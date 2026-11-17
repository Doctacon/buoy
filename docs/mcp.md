# Buoy over MCP

Buoy exposes retrieval and catalog inspection to local MCP clients over stdio.
This is an optional interface, not an HTTP/SSE service or background MCP daemon.

## Install from a source checkout

MCP is unreleased: the published release in the README quick start does not
include it. Use a source checkout that contains `src/buoy_search/mcp.py`, with
Python 3.11 or newer and `uv`. From that checkout's root:

```bash
uv sync --locked --extra mcp --python 3.13
uv run --locked --extra mcp buoy mcp --help
uv run --locked --extra mcp buoy mcp
```

The last command serves protocol messages on stdout until the client disconnects
or the process is stopped; it is not an interactive search prompt. The optional
extra uses the official Python MCP SDK, currently pinned to `mcp==2.2.0` for its
tested stdio compatibility. A base install still supports ordinary CLI commands
and `buoy mcp --help`; launching without the extra fails with an installation
instruction rather than installing anything automatically.

## Connect a client

An agent-neutral example (configuration locations differ by client):

```json
{"mcpServers":{"buoy":{"command":"buoy","args":["mcp"]}}}
```

The client must resolve the **extra-installed** executable. For the source setup
above, use the absolute path to the checkout's `.venv/bin/buoy` if that directory
is not on the client's PATH. On Windows virtual environments use `Scripts`
instead of `bin`; Windows execution has not been verified here.

Clients, especially desktop applications, may not inherit your shell's PATH or
environment. Arrange for the launched server process to receive
`TURBOPUFFER_API_KEY` and any existing Buoy region configuration through your
client's supported environment mechanism. Do not put credentials in tool
arguments, command-line arguments, or checked-in configuration. The example
stores no credentials and does not assume shell-variable interpolation in JSON.
Buoy does **not** auto-load `.env`. Connecting a client does not add an account or
namespace ACL: tools have the existing credential's provider access, and returned
evidence goes to the invoking client.

## Tools

Exactly three tools are available; there are no resources, prompts, write tools,
or arbitrary command runner. Unknown arguments and wrong types are rejected;
strings containing option or shell syntax remain data.

### `retrieve(query: string, namespaces?: string[] | null, top_k: integer = 5)`

- `query` must contain non-whitespace text; the CLI trims surrounding whitespace.
- Omitted/null `namespaces`, or `[]`, uses existing automatic catalog routing and
  bounded fanout (at most three namespaces), **not** a query of every index.
- One to three explicit namespaces bypass catalog discovery and routing work.
  Names are trimmed, must be nonempty and unique after trimming, and retain input
  order. `buoy-routing-catalog-v1` and `buoy-evidence-*` are reserved targets.
  `TURBOPUFFER_NAMESPACE` is not used for implicit selection.
- `top_k` is the final global result limit: a positive integer, default `5`, with
  no new upper cap. Booleans, numeric strings and fractions are not integers.

The result is the equivalent `buoy retrieve --json` object, not a generated
answer. Preserve source citations, passage content, tags, namespace attribution,
and routing/reranking/evidence diagnostics when using it. Partial failure keeps
successful hits and attributed failures with `incomplete=true`; do not present
these results as complete. Empty successful retrieval remains successful.
Automatic `no_relevant_evidence` and `inconclusive` outcomes retain their evidence
object and empty hits; the latter also retains incomplete/failure information.
They mean no sufficiently relevant evidence was found, **not** that no answer
exists. Explicit selection retains raw-search behavior rather than automatic
abstention. Total failure is an error, never an invented empty success.

### `catalog_list(search?: string | null, include_all: boolean = false)`

Returns the equivalent `buoy catalog list --json` object. By default it lists
enabled cards with live targets, including incompatible live cards the CLI
reports; it is not an eligible-only filter. `include_all=true` maps to `--all`,
including disabled/stale cards without enabling or repairing them.

Omitted/null search means no filter. Empty/whitespace search also retains the
CLI's no-filter behavior. Other strings use canonical substring matching of
namespace, title, summary, aliases, tags, and reviewed routing examples, not
fuzzy or semantic search. Zero matching cards is a successful empty list.
The count, cards, search/all fields, catalog status, missing-card diagnostics,
compatibility and snapshot/read metadata are preserved.

### `catalog_show(namespace: string)`

Returns the equivalent `buoy catalog show --json` object: the card and existing
target/catalog status and snapshot metadata. The namespace must contain
non-whitespace text; otherwise it is an **exact card-ID lookup**, with no trimming
or fuzzy resolution. A missing card is an error.

Both catalog tools inspect the fixed `buoy-routing-catalog-v1`. They omit vectors
and system-owned source-derived routing-passage banks, but retain reviewed
`routing_examples` visible through normal CLI inspection. There is no
`include_vector` argument or content-namespace enumeration tool.

## Results, costs and local effects

Successful CLI JSON objects are returned in MCP structured content and an
equivalent JSON text block, without filtering fields or synthesizing answers.
Invalid input, command failure and malformed/non-object output become sanitized
MCP tool errors (`isError`), not empty results. Diagnostics suggest checking the
schema, installation, server environment, catalog/namespace or local model setup;
raw command stderr, traceback, malformed output and credential values are not
forwarded. The existing content-free worker fallback warning can appear once on
stderr. The adapter invokes one fixed CLI subprocess per accepted call with no
adapter retry; existing CLI/provider retry and fallback policies are unchanged.

Import, help, startup, initialization and tool discovery are provider-free: they
do not load models, start workers or create Buoy runtime assets. **Valid live
calls can incur ordinary billed Turbopuffer reads.** Catalog tools may read
inventory/catalog data; retrieval may read catalog and content data and use
existing locally configured models. The adapter adds no model-download workflow.

Read-only means no index/catalog mutations: no planning/apply, upsert, enable,
disable, repair, schema migration or deletion is exposed. It does **not** mean
cost-free or filesystem-free retrieval. Existing inference workers and opted-in
local retrieval telemetry remain in effect, including their local assets and
idle lifetimes. The adapter adds no durable request/result log, cache, exporter
or telemetry schema. Cancellation/shutdown cleans up the adapter-owned command
child, not shared inference or telemetry workers.

See [retrieval](retrieval.md) for existing retrieval/model setup and
[telemetry](telemetry.md) for the existing local opt-in behavior. Installation and
protocol verification here used isolated, credential-free/offline environments;
no live provider or real-model retrieval was performed.
