# Command Center

Buoy Command Center is an optional, local-first operator console for reviewing saved plans, applied state, remote namespace status, and search results. Phase 1 is read-only: it cannot apply a plan, delete a namespace, write a catalog card, reconnect to a source warehouse, or extract a graph.

## Architecture

The console has three layers:

1. Framework-independent Python services read saved plan artifacts and local DuckDB applied-state ledgers. Separate lazy services own the two explicit turbopuffer operations: remote refresh and search.
2. A loopback-only FastAPI application exposes the versioned same-origin `/api/v1` API and serves packaged static files. Uvicorn runs it in-process.
3. A React and TypeScript application consumes only that same-origin API. Its production assets ship in the Python wheel; Node is needed only to develop or rebuild the frontend.

FastAPI and Uvicorn are optional. Importing `buoy_search`, loading the CLI, and running ordinary Buoy commands do not require the `ui` extra or Node. Server startup reads local files but does not inspect turbopuffer credentials, contact providers, connect to a source database, or load embedding models.

## Install and run

From a checkout managed by uv:

```bash
uv sync --extra ui
uv run buoy serve
```

The browser opens at `http://127.0.0.1:8765/` by default. Installed packages use the same command through their chosen environment manager; no Node installation is required.

Options:

```text
--host 127.0.0.1|localhost|::1   loopback bind address (default 127.0.0.1)
--port PORT                       TCP port (default 8765)
--artifacts-root PATH             saved-plan root (default artifacts/site-crawls)
--state-root PATH                 applied-state root
--no-browser                      do not open the default browser
```

When `--state-root` is omitted, Buoy uses its normal `.buoy` root and preserves the existing in-place `.turbo-search` fallback for migrated projects. Paths are resolved from the directory where `buoy serve` is run. The server rejects non-loopback hosts; Phase 1 is not a hosted or LAN service.

## Local and remote activity

Ordinary navigation is local-only. Dashboard, namespace, and plan pages inspect saved `plan.json`, manifest, Markdown, chunk, summary, and local applied-state data beneath the configured roots. Malformed artifacts are isolated and displayed as item-level errors. The console never repairs or changes them.

The UI does not reconnect to website, GitHub, document, DuckDB, BigQuery, or Snowflake sources. A remote-source plan can therefore be reviewed without source credentials or warehouse calls. Displayed source activity is recorded plan metadata, not a new source query.

Only two controls may perform turbopuffer reads:

- **Refresh remote status** explicitly lists remote namespaces and reads compatible catalog cards. No refresh runs automatically.
- **Search** explicitly performs retrieval. Automatic routing may read the remote catalog and load the local routing model; retrieval may load the local content embedding model and query selected namespaces.

Both responses report whether credentials were required, API calls occurred, and writes occurred. Writes are always false in Phase 1. Multi-namespace search remains all-or-nothing if one selected namespace fails.

## Credentials

Local browsing requires no provider or source credentials. Remote refresh and search use the existing server-process turbopuffer configuration, including `TURBOPUFFER_API_KEY` and the normal optional region setting. Credentials stay in the Python process: the API does not return them, and the frontend does not ask for or store them.

Do not put secrets in plan artifacts, URLs, browser storage, logs, screenshots, or bug reports. Missing remote credentials produce a safe not-configured message; they do not prevent local review.

## Screens

- **Dashboard** shows local counts, recent plans, attention items, artifact errors, and the initial remote `Not checked` state.
- **Namespaces** filters combined local inventory by namespace, source kind, local state, refreshed remote classification, and catalog-card status.
- **Namespace detail** shows source provenance, retrieval settings, related plans and diffs, a search entry point, and a clearly labeled future graph area.
- **Plans** presents deterministic plan history, source/activity metadata, counts, and proposed diffs.
- **Plan detail** shows identity, safe provenance, embedding and retrieval contracts, diff, bounded page/Markdown previews, paginated chunks, warnings, and errors.
- **Search** supports explicit namespace selection or automatic routing with bounded ranking inputs, execution-impact disclosure, and citation-rich results.
- **Graphs** explains the future evidence-backed graph flow. It contains no generated, placeholder, or inferred graph data.

Markdown, chunk content, citations, and result text are rendered as escaped plain text rather than executable HTML.

## Security boundary

Command Center is for one local operator. It has no authentication and compensates by accepting only `127.0.0.1`, `localhost`, or `::1`. The server uses same-origin static/API delivery, does not enable permissive CORS, and adds a restrictive content security policy, frame denial, MIME sniffing protection, and a no-referrer policy.

Browser requests address plans by validated plan ID and bounded index or pagination values. They cannot request arbitrary filesystem paths or SQL. Responses redact private absolute paths, warehouse connection details, credentials, and raw provider errors. There are no mutation endpoints or controls.

Do not reverse-proxy the server, expose it through a tunnel, bind it to a network interface, or treat it as a multi-user service.

## Troubleshooting

### Optional dependencies are missing

Run `uv sync --extra ui`. If using an installed distribution, install its `ui` extra with the environment manager that installed Buoy.

### The browser did not open

Open `http://127.0.0.1:8765/` manually or start with `--no-browser`. For `--host ::1`, use `http://[::1]:8765/`.

### The port is already in use

Choose another loopback port, for example `uv run buoy serve --port 8876`.

### Plans or namespaces are absent

Run the server from the project that owns the artifacts and state, or pass the correct `--artifacts-root` and `--state-root`. The artifacts root is searched recursively for `plan.json`; unsafe symlinks, malformed artifacts, and identity mismatches are not silently accepted.

### Remote status remains `Not checked`

That is the expected initial state. Activate **Refresh remote status** to perform the explicit read. A namespace missing from the refreshed result is not automatically a local artifact error.

### Refresh or search reports missing credentials

Set the normal `TURBOPUFFER_API_KEY` in the server process, restart if necessary, and retry the explicit operation. Local pages remain available without it.

### Packaged assets are missing during development

From the repository, run `cd web && npm ci && npm run build`, then restart the server. Released wheels already contain the built assets; Node is not a production prerequisite.

## Phase 1 non-goals

Phase 1 does not provide apply approval, crawling, source reconnection, catalog registration or repair, namespace deletion, other provider writes, authentication, remote hosting, desktop packaging, background refresh, persisted remote snapshots, live updates, graph extraction, graph storage, taxonomy generation, or graph editing.

## Roadmap

These phases describe direction, not behavior available in Phase 1; each requires its own reviewed security, permission, lifecycle, and failure contracts.

- **Phase 2 — managed workflows:** add explicitly authorized operator workflows around selected Buoy lifecycle operations, with confirmation and audit boundaries rather than exposing current CLI mutations directly.
- **Phase 3 — graph backend models:** derive versioned, evidence-linked graph snapshots and taxonomy or ontology models from selected namespaces. Graph facts must remain traceable to source chunks and citations.
- **Phase 4 — graph interface:** add exploration and review of those backend snapshots, including provenance navigation and taxonomy or ontology views. Phase 4 consumes established graph models; it does not invent graph data in the browser.
