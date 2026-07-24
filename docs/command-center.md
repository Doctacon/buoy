# Command Center

Buoy Command Center is an optional, local-first console for one operator. Phase 1 review, inventory, remote-status, and search screens remain read-only. Implemented Phase 2A adds one bounded managed workflow: start a local plan for a public HTTP(S) website or public GitHub repository, observe durable progress, and open the resulting plan for review. It does not add apply, deletion, catalog, namespace, source-definition, local-file, database-source, credential, or graph authority.

## Architecture

The console has four layers:

1. Framework-independent Python services read saved plan artifacts and local DuckDB applied-state ledgers. Separate lazy services own the two explicit turbopuffer operations: remote refresh and search.
2. A durable, single-worker plan-job service validates public sources, calls the same planning service as `buoy plan`, persists safe records and events, and writes ordinary plan artifacts.
3. A loopback-only FastAPI application exposes the versioned same-origin `/api/v1` API and serves packaged static files. Uvicorn runs it in-process.
4. A React and TypeScript application consumes only that same-origin API. Its production assets ship in the Python wheel; Node is needed only to develop or rebuild the frontend.

FastAPI and Uvicorn are optional. Importing `buoy_search`, loading the CLI, and running ordinary Buoy commands do not require the `ui` extra or Node. Server startup reads local job and artifact state but does not crawl, clone, resume work, inspect turbopuffer credentials, contact providers, connect to a source database, or load embedding models.

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
--artifacts-root PATH             saved-plan and managed-plan root (default artifacts/site-crawls)
--state-root PATH                 applied-state and durable plan-job root
--no-browser                      do not open the default browser
```

When `--state-root` is omitted, Buoy uses its normal `.buoy` root and preserves the existing in-place `.turbo-search` fallback for migrated projects. Paths are resolved from the directory where `buoy serve` is run. Managed artifacts live beneath `<artifacts-root>/command-center/plans/<job-id>/`; durable records and events live beneath `<state-root>/command-center/jobs/`. The server rejects non-loopback hosts; Command Center is not a hosted or LAN service.

## Managed public-source planning

Open **Start plan** to submit a public HTTP(S) website URL or a public GitHub repository-root URL. Optional fields are limited to maximum pages/files, maximum chunks, namespace, and include/exclude paths. GitHub tree/blob URLs, private-repository credentials, local paths and uploads, local documents, and DuckDB, BigQuery, or Snowflake sources are not accepted. Command-line `buoy plan` retains its broader source support.

Only one managed job may be `queued` or `running` at a time for the configured local service. A second submission is rejected and links to the active job; it is not queued. Job history and append-only progress events are durable. States are `queued`, `running`, `succeeded`, `failed`, and `interrupted`. On startup, a previously queued or running job becomes `interrupted`; no job resumes or retries automatically. There is no cancel, pause, resume, automatic retry, or plan-job retry endpoint. **Start a new plan** always creates a new job identity.

A successful job writes the same ordinary, integrity-verified `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and `pages/` artifacts as CLI planning. The job ID is audit/storage metadata only and does not change source, namespace, document, chunk, plan, or row identity. The plan appears in the existing read-only plan review screen. Planning does not read turbopuffer credentials, embed content, call turbopuffer, update applied state, or mutate a namespace or catalog.

Command Center never applies a plan. After reviewing a successful managed plan, hand its exact artifact path to the existing CLI:

```bash
uv run buoy apply --dry-run --plan artifacts/site-crawls/command-center/plans/<job-id>/plan.json
uv run buoy apply --plan artifacts/site-crawls/command-center/plans/<job-id>/plan.json
```

Use the configured artifacts root instead of `artifacts/site-crawls` when overridden. The second command performs the normal preflight and exact interactive confirmation; `--approve` remains the explicit non-interactive CLI option. No browser control performs this handoff or approval.

## Local and remote activity

Ordinary navigation is local-only. Dashboard, namespace, plan, and plan-job history pages inspect saved artifacts, Markdown, chunks, summaries, job events, and local applied state beneath the configured roots. Malformed artifacts are isolated and displayed as item-level errors. The console never repairs or changes them.

Submitting **Start plan** is the only source-acquisition workflow: it may crawl the submitted public website or clone the submitted public GitHub repository. It never reconnects to document or database sources. Opening history, progress, or a completed plan does not reacquire the source. Displayed source activity on saved plans is recorded plan metadata, not a new source query.

Only two controls may perform turbopuffer reads:

- **Refresh remote status** explicitly lists remote namespaces and reads compatible catalog cards. No refresh runs automatically.
- **Search** explicitly performs retrieval. Automatic routing may read the remote catalog and load the local routing model; retrieval may load the local content embedding model and query selected namespaces.

Both responses report whether credentials were required, API calls occurred, and writes occurred. Writes are always false for these Command Center operations. Multi-namespace search remains all-or-nothing if one selected namespace fails.

## Credentials

Local browsing and managed public-source planning require no turbopuffer credentials. Managed planning accepts no source credential, header, cookie, or token. Remote refresh and search use the existing server-process turbopuffer configuration, including `TURBOPUFFER_API_KEY` and the normal optional region setting. Credentials stay in the Python process: the API does not return them, and the frontend does not ask for or store them.

Do not put secrets in plan artifacts, URLs, browser storage, logs, screenshots, or bug reports. Missing remote credentials produce a safe not-configured message; they do not prevent local review or public-source planning.

## Screens

- **Dashboard** shows local counts, recent plans, attention items, artifact errors, and the initial remote `Not checked` state.
- **Start plan** creates only a managed public website or public GitHub plan and states its no-embed/no-turbopuffer/no-namespace-mutation boundary.
- **Plan jobs** shows bounded durable history. **Plan-job detail** shows persisted and live progress, falls back to polling, links successful jobs to review, and offers only a new-plan link after failure/interruption.
- **Namespaces** filters combined local inventory by namespace, source kind, local state, refreshed remote classification, and catalog-card status.
- **Namespace detail** shows source provenance, retrieval settings, related plans and diffs, a search entry point, and a clearly labeled future graph area.
- **Plans** presents deterministic plan history, source/activity metadata, counts, and proposed diffs.
- **Plan detail** shows identity, safe provenance, embedding and retrieval contracts, diff, bounded page/Markdown previews, paginated chunks, warnings, errors, and an originating job link when durable managed metadata establishes one.
- **Search** supports explicit namespace selection or automatic routing with bounded ranking inputs, execution-impact disclosure, and citation-rich results.
- **Graphs** explains the future evidence-backed graph flow. It contains no generated, placeholder, or inferred graph data.

Markdown, chunk content, progress, errors, citations, and result text are rendered as escaped plain text rather than executable HTML. A shared **Retry** button on a read-error card only repeats that idempotent GET; it does not retry, resume, or replay a plan job.

## Security boundary

Command Center is for one local operator. It has no authentication and compensates by accepting only `127.0.0.1`, `localhost`, or `::1`. The server validates the `Host`, uses same-origin static/API delivery, rejects cross-origin plan creation, does not enable permissive CORS, and adds a restrictive content security policy, frame denial, MIME sniffing protection, and a no-referrer policy.

Starting a plan requires JSON within the bounded request size and a server-process CSRF token fetched by the UI and returned in a non-simple header. The token is not persisted, logged, or stored in browser storage. Restarting the server changes the token. These protections complement the loopback bind; they do not make remote exposure safe.

Browser requests address plans and jobs by validated IDs and bounded index or pagination values. They cannot request arbitrary filesystem paths or SQL. Responses redact private absolute paths, warehouse connection details, credentials, and raw provider errors. The only Phase 2A mutation endpoint creates a bounded local plan job; there are no apply, approve, cancel, retry/resume, delete, catalog/source-definition, or namespace mutation endpoints.

Do not reverse-proxy the server, expose it through a tunnel, bind it to a network interface, or treat it as a multi-user service.

## Troubleshooting

### Optional dependencies are missing

Run `uv sync --extra ui`. If using an installed distribution, install its `ui` extra with the environment manager that installed Buoy.

### The browser did not open

Open `http://127.0.0.1:8765/` manually or start with `--no-browser`. For `--host ::1`, use `http://[::1]:8765/`.

### The port is already in use

Choose another loopback port, for example `uv run buoy serve --port 8876`.

### Plans, plan jobs, or namespaces are absent

Run the server from the project that owns the artifacts and state, or pass the correct `--artifacts-root` and `--state-root`. The artifacts root is searched recursively for `plan.json`; unsafe symlinks, malformed artifacts, and identity mismatches are not silently accepted. Plan-job history belongs to the selected state root.

### A prior job is interrupted

This is expected after the server process exits while a job is queued or running. Review its preserved events and safe incomplete artifacts if present, then use **Start a new plan** to create a distinct job. Nothing resumes automatically.

### A new job reports another active job

Only one managed job may be queued or running. Follow the active-job link and wait for it to reach a terminal state. There is no cancellation endpoint.

### Remote status remains `Not checked`

That is the expected initial state. Activate **Refresh remote status** to perform the explicit read. A namespace missing from the refreshed result is not automatically a local artifact error.

### Refresh or search reports missing credentials

Set the normal `TURBOPUFFER_API_KEY` in the server process, restart if necessary, and retry the explicit operation. Local pages and public-source planning remain available without it.

### Packaged assets are missing during development

From the repository, run `cd web && npm ci && npm run build`, then restart the server. Released wheels already contain the built assets; Node is not a production prerequisite.

## Current non-goals

Command Center does not provide plan apply or approval, cancellation, pause/resume, plan-job retry, saved source definitions, local-file/document or database planning, source credentials, private repositories, catalog registration or repair, namespace deletion, other provider writes, authentication, remote hosting, desktop packaging, background remote refresh, persisted remote snapshots, graph extraction, graph storage, taxonomy generation, or graph editing.

## Roadmap

**Phase 2A is implemented:** one local operator can create one active public website or public GitHub plan, observe durable progress, and review ordinary artifacts before an explicit CLI apply handoff.

Broader Phase 2 remains **unratified**. Possible managed apply, deletion, catalog, credential, source-definition, namespace, local-file, database, or other lifecycle workflows are not approved behavior and must not be inferred from Phase 2A; each would require its own ratified security, permission, lifecycle, and failure contract.

- **Phase 3 — graph backend models (direction only):** derive versioned, evidence-linked graph snapshots and taxonomy or ontology models from selected namespaces. Graph facts must remain traceable to source chunks and citations.
- **Phase 4 — graph interface (direction only):** add exploration and review of established backend snapshots, including provenance navigation and taxonomy or ontology views. It must not invent graph data in the browser.
