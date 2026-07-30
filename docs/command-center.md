# Command Center

Buoy Command Center is an optional, local-first console for one operator. Phase 1 review, inventory, remote-status, and search screens remain read-only. Implemented Phase 2A adds one bounded managed workflow: start a local plan for a credential-free HTTP(S) website or public GitHub repository root, observe durable progress, and open the resulting plan for review. Graph Phase 3A remote evidence snapshots and Phase 3B autonomous local semantic builds are CLI-only; Command Center does not create, verify, inspect, retain, or delete them. Both `buoy-evidence-` and `buoy-semantics-` infrastructure are excluded from source inventory and search. It does not add apply, deletion, catalog, namespace, source-definition, local-file, database-source, credential, or graph authority.

## Architecture

The console has four layers:

1. Framework-independent Python services read saved plan artifacts and local DuckDB applied-state ledgers. Summary inventory treats every directory containing `plan.json` as a traversal boundary, reads only bounded plan metadata, and obtains applied-state counts and metadata through aggregate read-only queries rather than loading complete row ledgers. Separate lazy services own the two explicit turbopuffer operations: remote refresh and search.
2. A durable, single-worker plan-job service validates credential-free HTTP(S) websites and public GitHub repository roots, calls the same planning service as `buoy plan`, persists safe records and events, and writes ordinary plan artifacts.
3. A loopback-only FastAPI application exposes the versioned same-origin `/api/v1` API and serves packaged static files. Uvicorn runs it in-process.
4. A React and TypeScript application consumes only that same-origin API. Its production assets ship in the Python wheel; Node is needed only to develop or rebuild the frontend.

FastAPI and Uvicorn are optional. Importing `buoy_search`, loading the CLI, and running ordinary Buoy commands do not require the `ui` extra or Node. Server startup reads local job and artifact state but does not crawl, clone, resume work, inspect turbopuffer credentials, contact providers, connect to a source database, or load embedding models. If the platform lacks required no-follow, directory-descriptor, or descriptor-relative filesystem primitives, startup logs one sanitized warning and leaves the managed worker absent; read-only review/inventory/applied-state pages plus explicit remote refresh and search remain available. Integrity failures, malformed or tampered records, permissions/durability failures, and service-lock conflicts still fail startup closed.

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

Open **Start plan** to submit a credential-free HTTP(S) website URL or a public GitHub repository-root URL. Optional fields are limited to maximum pages/files, maximum chunks, namespace, and include/exclude paths. GitHub tree/blob URLs, private-repository credentials, local paths and uploads, local documents, and DuckDB, BigQuery, or Snowflake sources are not accepted. Command-line `buoy plan` retains its broader source support.

Managed website planning validates HTTP(S) syntax and accepts no source credentials, but it is not a public-routability or SSRF firewall. The Command Center must remain loopback-only and under the control of the local operator.

Only one managed job may be `queued` or `running` at a time for the configured local service. A second submission is rejected and links to the active job; it is not queued. Job history and append-only progress events are durable. New jobs retain at most 5,000 lifecycle and progress events. At the threshold, one durable event states that additional progress is being coalesced; later intermediate callbacks do not rewrite the record or event log, and the final `succeeded`, `failed`, or `interrupted` event remains reserved. Existing over-limit schema-v1 history remains readable and is never compacted or deleted by this rule. States are `queued`, `running`, `succeeded`, `failed`, and `interrupted`. On startup, a previously queued or running job becomes `interrupted`; no job resumes or retries automatically. There is no cancel, pause, resume, automatic retry, or plan-job retry endpoint. **Start a new plan** always creates a new job identity.

A successful job publishes exactly the same two integrity-verified schema-v2 artifacts as CLI planning: `plan.json` and `delta.duckdb`. It retains no manifest, chunk JSONL, summary sidecar, extracted pages, or source staging. The job ID is audit/storage metadata only and does not change source, namespace, document, chunk, plan, or row identity. The plan appears in the existing read-only plan review screen. Planning does not read turbopuffer credentials, embed content, call turbopuffer, update applied state, or mutate a namespace or catalog.

Command Center never applies a plan. After reviewing a successful managed plan, hand its exact artifact path to the existing CLI:

```bash
uv run buoy apply --dry-run --plan artifacts/site-crawls/command-center/plans/<job-id>/plan.json
uv run buoy apply --plan artifacts/site-crawls/command-center/plans/<job-id>/plan.json
```

Use the configured artifacts root instead of `artifacts/site-crawls` when overridden. The second command performs the normal preflight and exact interactive confirmation; `--approve` remains the explicit non-interactive CLI option. No browser control performs this handoff or approval.

## Local and remote activity

Ordinary navigation is local-only. Dashboard, namespace, plan, and plan-job history pages inspect bounded `plan.json` summaries, selected fully verified deltas, job events, and local applied state beneath the configured roots. Every directory containing `plan.json` is an inventory leaf, so summary discovery does not descend into legacy pages, staging/payload directories, or nested plans below that boundary; valid sibling directories remain discoverable. Inventory never opens `delta.duckdb`; it reports payload verification as `not_checked`. Applied-state inventory opens each selected `state.duckdb` read-only and obtains metadata plus active, retained-stale, deleted, and total counts with aggregate queries, without materializing the full applied-row ledger. Selecting one plan fully verifies that delta before showing bounded windows. Schema-v1 plans are silently ignored and never opened. Malformed schema-v2 artifacts are isolated and displayed as item-level errors. The console never repairs or changes them.

Dashboard, namespace, and plan summaries share the unchanged locked, process-local snapshot cache with a 1.0-second lifetime. Successful in-process managed-plan publication invalidates that snapshot immediately; CLI or other-process changes may remain invisible until the next refresh after the lifetime expires. The cache is bounded to summary records and isolated errors, is neither persisted nor shared between processes, and never authorizes apply or artifact access. Direct plan and namespace misses force one refresh.

Dashboard, Plans, and Namespaces carry and render at most a deterministic 20-error sample from that cached snapshot while reporting the complete error count and whether the sample is truncated. The read-only **Artifact errors** diagnostics screen provides all isolated errors through server-filtered 50-item pages, with a maximum requested page size of 100. It matches code, sanitized message, or safe artifact ID before pagination and never verifies a delta, accesses a source, repairs an artifact, or offers a show-all or mutation control.

Plans and local Namespaces are paginated by the server after applying their local search, source-kind, namespace, or local-status filters to that cached snapshot. The browser requests and renders one 50-row page at a time; filter changes return to the first page, and Previous/Next navigation requests only the selected page. Namespace detail receives at most 20 matching plans by default (100 when explicitly requested) and links to the filtered Plans screen when more history exists. Explicitly refreshed remote data does not alter those local filters: matching `local_present=true` entries only enrich local rows, while `local_present=false` entries appear in a separately labeled, independently paginated remote-only section.

Opening a selected plan initially issues one combined review request and performs one fresh complete verification to derive detail plus both bounded payload windows. Changed-chunk or stale-row pagination then issues only that section's focused request; each focused payload request performs its own fresh complete verification before replacing that window. One Plan screen accepts only one focused changed/stale pagination or retry request at a time and disables both sections' focused controls until it finishes. This is a per-screen resource bound, not cancellation, a queue, or a verification cache: other tabs remain independent, an old route's server work may finish, and every accepted payload request still performs complete verification. No verified result, row set, token, or authority is persisted between requests. Complete identity, schema, logical, source, baseline, payload, tamper, and replacement checks remain in force. Verification is linear in the selected delta size and can still take several seconds for a large delta, so no constant-time or universal subsecond claim is made.

Submitting **Start plan** is the only source-acquisition workflow: it may crawl the submitted credential-free HTTP(S) website or clone the submitted public GitHub repository root. It never reconnects to document or database sources. Opening history, progress, or a completed plan does not reacquire the source. Displayed source activity on saved plans is recorded plan metadata, not a new source query.

Only two controls may perform turbopuffer reads:

- **Refresh remote status** explicitly lists remote namespaces and reads compatible catalog cards. No refresh runs automatically. Names beginning `buoy-evidence-` are internal evidence infrastructure: they are excluded from ordinary source rows and automatic routing, while refresh may report only their bounded count.
- **Search** explicitly performs retrieval. Automatic routing may read the remote catalog and load the local routing model; retrieval may load the local content embedding model and query selected namespaces.

Both responses report whether credentials were required, API calls occurred, and writes occurred. Writes are always false for these Command Center operations. Multi-namespace search remains all-or-nothing if one selected namespace fails.

## Credentials

Local browsing and managed credential-free website/public-GitHub planning require no turbopuffer credentials. Managed planning accepts no source credential, header, cookie, or token. Remote refresh and search use the existing server-process turbopuffer configuration, including `TURBOPUFFER_API_KEY` and the normal optional region setting. Credentials stay in the Python process: the API does not return them, and the frontend does not ask for or store them.

Do not put secrets in plan artifacts, URLs, browser storage, logs, screenshots, or bug reports. Missing remote credentials produce a safe not-configured message; they do not prevent local review or public-source planning.

## Screens

- **Dashboard** shows local counts, recent plans, attention items, artifact errors, and the initial remote `Not checked` state.
- **Start plan** creates only a managed credential-free HTTP(S) website or public GitHub repository-root plan and states its no-embed/no-turbopuffer/no-namespace-mutation boundary.
- **Plan jobs** shows bounded durable history. **Plan-job detail** shows persisted and live progress, falls back to polling, links successful jobs to review, and offers only a new-plan link after failure/interruption.
- **Namespaces** filters one server-paginated local page by namespace, source kind, and local state; explicit refreshed remote data enriches matching local rows and places only remote entries without a local snapshot in a separate independently paginated section.
- **Namespace detail** shows source provenance, retrieval settings, related plans and diffs, a search entry point, and a clearly labeled future graph area.
- **Plans** presents one server-filtered and server-paginated deterministic plan-history page with source/activity metadata, counts, proposed diffs, and at most a 20-item artifact-error sample linked to diagnostics.
- **Artifact errors** provides read-only, searchable, server-paginated access to every isolated local artifact error by code, sanitized message, and safe artifact ID. It requests and renders only the current 50-item page and has no show-all, repair, or deletion action.
- **Plan detail** derives its initial detail and both bounded payload windows from one fresh complete verification; later changed/stale pagination verifies afresh through only the focused section endpoint, with at most one focused request accepted by that screen at a time. It shows identity, applied-state baseline, safe provenance, embedding and retrieval contracts, diff, paginated changed/new/reactivated chunks, paginated stale identities, an explicit unchanged-content omission notice, warnings, errors, and an originating job link when durable managed metadata establishes one.
- **Search** supports explicit namespace selection or automatic routing with bounded ranking inputs, execution-impact disclosure, and citation-rich results.
- **Graphs** explains the evidence-backed roadmap. Phase 3A snapshots and Phase 3B concepts/mentions/lightweight taxonomy exist only through the CLI; the screen contains no snapshot or semantic-build creation, generated graph, visualization, editing, approval, arbitrary assertions, or complete ontology.

Changed chunk content, progress, errors, citations, and result text are rendered as escaped plain text rather than executable HTML. A shared **Retry** button on a read-error card only repeats that idempotent GET; it does not retry, resume, or replay a plan job.

## Security boundary

Command Center is for one local operator. It has no authentication and compensates by accepting only `127.0.0.1`, `localhost`, or `::1`. The server validates the `Host`, uses same-origin static/API delivery, rejects cross-origin plan creation, does not enable permissive CORS, and adds a restrictive content security policy, frame denial, MIME sniffing protection, and a no-referrer policy.

Starting an available plan requires JSON within the bounded request size and a server-process CSRF token fetched by the UI and returned in a non-simple header. When capabilities report `managed_public_planning_available: false` with reason `platform_unsupported`, managed routes render an unavailable explanation and make no job-history, CSRF, or creation request; `durable_plan_job_history_available` is also false. The token is not persisted, logged, or stored in browser storage. Restarting the server changes the token. These protections complement the loopback bind; they do not make remote exposure safe.

Browser requests address plans and jobs by validated IDs and bounded pagination values. They cannot request arbitrary filesystem paths or SQL. Responses redact private absolute paths, warehouse connection details, credentials, and raw provider errors. The only Phase 2A mutation endpoint creates a bounded local plan job; there are no apply, approve, cancel, retry/resume, delete, catalog/source-definition, or namespace mutation endpoints.

Do not reverse-proxy the server, expose it through a tunnel, bind it to a network interface, or treat it as a multi-user service.

## React Router advisory disposition

The installed `react-router-dom@7.18.1` resolves `react-router@7.18.1`, which is numerically within GHSA-qwww-vcr4-c8h2. The official advisory affects only unstable React Server Components request handling where a rejected cross-origin document POST can still reach a route action. Buoy is a Vite declarative SPA initialized with `BrowserRouter`; it has no React Router framework mode, server actions, React Server Components, RSC plugin, or unstable RSC API entrypoint, so the vulnerable path is unreachable and no breaking dependency migration is made solely to silence `npm audit`. Repository validation guards this routing mode. Reevaluate before adopting framework mode, React Server Components, server actions, unstable RSC APIs, or if the official advisory scope changes.

## Troubleshooting

### Optional dependencies are missing

Run `uv sync --extra ui`. If using an installed distribution, install its `ui` extra with the environment manager that installed Buoy.

### The browser did not open

Open `http://127.0.0.1:8765/` manually or start with `--no-browser`. For `--host ::1`, use `http://[::1]:8765/`.

### The port is already in use

Choose another loopback port, for example `uv run buoy serve --port 8876`.

### Plans, plan jobs, or namespaces are absent

Run the server from the project that owns the artifacts and state, or pass the correct `--artifacts-root` and `--state-root`. The artifacts root is searched recursively for bounded schema-v2 `plan.json` summaries with regular-file `delta.duckdb` siblings, but discovery never descends below a directory once it contains `plan.json`. Legacy schema-v1 plans are inert and omitted. Unsafe symlinks, malformed schema-v2 artifacts, and summary identity mismatches are not silently accepted. Summary results are cached for up to 1.0 second per server process, so wait for that interval after an external CLI change or request the new plan/namespace directly to force one refresh. Plan-job history belongs to the selected state root.

### Server shutdown waits for an active job

Phase 2A does not support cancellation. Gracefully stopping the server while its in-process job is active logs the safe job ID/state and waits for that job to finish. Forced or genuinely interrupted process termination is handled by the restart rule below.

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

Command Center does not provide plan apply or approval, cancellation, pause/resume, plan-job retry, saved source definitions, local-file/document or database planning, source credentials, private repositories, catalog registration or repair, namespace deletion, other provider writes, authentication, remote hosting, desktop packaging, background remote refresh, evidence snapshot or semantic-build creation/verification/inspection/retention/deletion, graph extraction, graph storage, taxonomy generation, or graph editing.

## Roadmap

**Phase 2A is implemented:** one local operator can create one active credential-free HTTP(S) website or public GitHub repository-root plan, observe durable progress, and review ordinary artifacts before an explicit CLI apply handoff.

Broader Phase 2 remains **unratified**. Possible managed apply, deletion, catalog, credential, source-definition, namespace, local-file, database, or other lifecycle workflows are not approved behavior and must not be inferred from Phase 2A; each would require its own ratified security, permission, lifecycle, and failure contract.

- **Phase 3A — remote evidence snapshots: implemented.** Explicit CLI commands create/reuse branch-backed point-in-time evidence, a compact active/retained/deleted remote ledger, one completed remote catalog row, and only bounded local `snapshot.json`; see [Remote evidence snapshots](evidence-snapshots.md).
- **Phase 3B — autonomous local concepts, mentions, and taxonomy: implemented.** CLI-only local inference publishes accepted/provisional remote semantic objects and retains bounded local `build.json` plus only normal zero/small same-host lock state; see [Autonomous local semantics](semantics.md).
- **Phase 3C — evidence-backed typed assertions: future.**
- **Phase 4 — graph review and visualization: future.**
- **Phase 5 — incremental semantic maintenance: future.**

Phase 3B is a lightweight taxonomy, not a complete ontology. Command Center has no semantic or graph UI.
