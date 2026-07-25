Status: recorded
Created: 2026-07-24
Updated: 2026-07-24
Relates-To: .10x/tickets/done/2026-07-24-command-center-phase-2a-live-acceptance.md, .10x/reviews/2026-07-24-command-center-phase-2a-live-acceptance.md, .10x/specs/phase-2a-stabilization.md, .10x/specs/phase-2a-plan-job-lifecycle.md, .10x/specs/phase-2a-plan-job-interface.md, .10x/specs/phase-2a-plan-job-api-security.md, .10x/specs/phase-2a-public-source-planning-service.md

# Command Center Phase 2A Live Acceptance

## Environment and boundary

- Branch: `work/command-center-phase-2a-acceptance`.
- Tested base commit: `6910ec7b9c1cebefead105de64135965a27cdb2e` (`Merge branch 'develop'`) plus the bounded repairs described below.
- Host: macOS 26.5.1 (Build 25F80), Apple arm64. No Windows or Linux claim is made.
- Python: CPython 3.13.0 through uv 0.11.7. Node: v24.6.0.
- Browser: Playwright 1.60.0 with real Chromium 148.0.7778.96, headless.
- Primary server address: `127.0.0.1:63963`. `lsof` observed only `TCP 127.0.0.1:63963 (LISTEN)`.
- Server invocation: `uv run buoy serve --host 127.0.0.1 --port 63963 --artifacts-root <resolved-temp>/artifacts --state-root <resolved-temp>/state --no-browser`, with stdout/stderr under `<resolved-temp>/logs`.
- The isolated root used only `<resolved-temp>/{artifacts,state,logs}`. It was not the repository's normal `artifacts/`, `.buoy/`, or `.turbo-search/` tree.
- `TURBOPUFFER_API_KEY`, GitHub token variables, and unrelated ambient provider credentials were removed from acceptance subprocesses. No credential was supplied.
- The browser cache was host-ephemeral. No Playwright dependency, browser profile, screenshot, generated artifact, job record, raw log, source clone, or external content was added to the repository.

## Browser startup and local-only navigation

A fresh Chromium context opened `/`, `/namespaces`, `/plans`, `/plans/new`, `/plan-jobs`, `/search`, and `/graphs` against the packaged production frontend. Dashboard, Namespaces, Plan history, Start plan, Plan jobs, Search, and the graph roadmap all rendered without a raw exception. Hashed JavaScript `assets/index-lDcMEzTj.js`, CSS `assets/index-Amu9gKyT.css`, and `buoy.svg` loaded successfully; no browser response was HTTP 500 or higher.

Before planning, 39 captured requests were same-origin loopback requests for static assets and local APIs. There were zero external browser requests, no remote-refresh API request, no search API request, and plan-job count remained `0 → 0`. Dashboard remote state was `Not checked`. Navigation did not request a CSRF token, start a plan, load visible embedding behavior, require a turbopuffer credential, or expose a raw exception. `localStorage` and `sessionStorage` were empty.

The plan form had no credential, API-key, password, local-file/upload, database, or SQL input. The browser POSTs used `application/json`, a same-origin `Origin`, and the server-issued `X-Buoy-CSRF-Token`; the token was not stored in browser storage. A request with `Host: hostile.example` returned HTTP 400 with safe code `invalid_host`.

## Live website plan and reconnect

Source: `https://example.com/`, with maximum 3 pages and 30 chunks.

- Job: `planjob_7cd3b1f6b4df4991a983f1654f05c060`.
- UI observed `queued`, then durable state `running`, then a hard reload while running. Immediately after reload the timeline showed 3 persisted/live events.
- Terminal result: `succeeded`; 17 unique contiguous events ended in `succeeded`. The job count increased by exactly one, so reload did not restart or duplicate the job. Timeline rendering did not duplicate sequence identities.
- Plan: `plan_d6926d297669fd09`.
- Artifact-relative directory: `command-center/plans/planjob_7cd3b1f6b4df4991a983f1654f05c060/`.
- `plan.json`, `manifest.json`, `chunks.jsonl`, `summary.json`, and `pages/` existed. The three JSON files parsed; plan ID matched the job; `summary.json` contained the originating job ID.
- The job ID occurred in `plan.json` only in managed storage-path fields (`chunks_path`, `manifest_path`, `pages_dir`) and in summary audit/storage metadata; it did not occur in manifest/chunk identity content.
- Artifact inspection found no API key, cookie, authorization header, CSRF token, browser-profile path, or turbopuffer write result.
- The plan review showed source provenance, proposed diff, page/plain-text Markdown preview, chunks, and originating-job linkage. It remained read-only.
- A second live Chromium check planned a loopback page containing the literal text `<script id="fixture-evil">window.fixtureScriptExecuted=true</script>`. The preview displayed the literal text, created zero `script#fixture-evil` nodes, and left `window.fixtureScriptExecuted` false.

## Live public GitHub plan

Source: `https://github.com/octocat/Hello-World`, repository root, maximum 20 files and 100 chunks. No token, SSH URL, tree/blob URL, or private-repository path was used.

- Resolved HEAD observed separately through credential-free `git ls-remote`: `7fd1a60b01f91b314f59955a4e4d4e80d8edf11d`.
- Job: `planjob_6bfc93aad8e74f6e8cfd5b2bc1a4cd90`, classified `github_repo`.
- Terminal result: `succeeded`; plan `plan_aa8e22b89df82ae7` under `command-center/plans/planjob_6bfc93aad8e74f6e8cfd5b2bc1a4cd90/`.
- The repaired live timeline contained `clone`, `processing`, and `chunk`, then artifact/diff/write/success stages. Repository provenance and chunk previews rendered on the read-only plan review page.

## CLI verification of the UI-produced plan

Command: `uv run buoy apply --dry-run --plan <resolved-temp>/artifacts/command-center/plans/planjob_7cd3b1f6b4df4991a983f1654f05c060/plan.json --state-root <resolved-temp>/state`.

Result: exit 0. Output identified `Website RAG apply preflight (no credentials, embeddings, or turbopuffer API calls)`, verified plan `plan_d6926d297669fd09`, calculated the first-apply diff (`to_upsert=1`, `stale=0`), and said live execution still requires rerunning without dry-run or explicit approval. The exact `plan.json` SHA-256 and bytes were unchanged afterward. No source reacquisition progress, website request, GitHub clone, model load, turbopuffer call, state write, or remote write was observed.

## One-active conflict

A deterministic HTTP fixture bound only to `127.0.0.1`, served linked pages with delayed responses, and was submitted through Chromium as a credential-free loopback fixture.

- Active job: `planjob_1c6dd81b626849dfa4c99ebd5399d796`.
- While it was `running`, a second tab submitted a valid request. The UI showed `Another plan job is already active.` and linked `View active plan job` to the active ID.
- Total job count was unchanged by the conflict; no second queued job appeared.
- The first job continued and `succeeded`. The fixture received 9 bounded requests and was then stopped.

## Graceful shutdown

A fresh delayed loopback fixture started job `planjob_839c5b21b0764fe9a228431635f5312f`. After its durable state became `running`, the server received SIGTERM.

- The process remained alive after 0.5 seconds and until the worker completed; the job was not cancelled.
- Exactly one line was emitted: `WARNING: Waiting for active plan job planjob_839c5b21b0764fe9a228431635f5312f (running) during shutdown; cancellation is not supported in Phase 2A.`
- The line contained the safe job ID/state, no source URL, no absolute artifact/root path, no credential, and no exception text.
- After restart on the same roots and port, the job remained readable as `succeeded`, not `interrupted`. The replacement process acquired service ownership normally.

## Abrupt interruption and restart

A separate delayed fixture started `planjob_8fd9b58067fb44b3a53b38a52541d56b`. The durable pre-kill state was `running` at event sequence 3. The Buoy process group received SIGKILL while the fixture remained alive until process exit was confirmed.

- Restart with the same roots converted the job to `interrupted` with safe error `job_interrupted: Planning was interrupted by a local service restart.`
- The job had no plan ID, preserved its three prior safe events plus one interruption event, did not resume, and did not change sequence after an additional wait.
- The browser offered only `Start a new plan`; no cancel, retry, replay, or resume action appeared.
- New job `planjob_2978f7c6f41b4879bca9f7593e8ea771` was then submitted and `succeeded`, proving ownership release/reacquisition and normal subsequent operation.

## Product authority and security inspection

Across every navigation route, successful plan reviews, job history/detail, conflict, and interrupted-job detail, browser controls exposed none of: plan apply/approval; stale or namespace deletion; catalog enable/disable; source-definition or credential storage; filesystem browsing or upload; DuckDB/BigQuery/Snowflake planning; job cancel/resume/retry/replay; taxonomy/ontology generation; or concept-graph creation. The Graphs page remained a labeled roadmap stating no graph data exists and contained no fabricated graph data.

There was no Apply, Approve, Delete stale, Delete namespace, Cancel job, Resume job, Retry plan job, or replay control. Ordinary search and explicit remote refresh controls were present but never activated, as allowed. Ordinary browser navigation stayed same-origin. Source content was text-rendered, not executed. No arbitrary filesystem or SQL input existed.

Across the run, no automatic remote refresh, search request, embedding activity, turbopuffer activity, catalog/namespace mutation, or apply occurred. This observation is bounded to the captured browser/server/CLI behavior and credential-free environment; it is not an external network packet capture.

## Defects and repairs

### `product_defect`: GitHub acquisition progress absent

Initial live GitHub acceptance succeeded but durable stages were only queued/validation/artifact/diff/write/succeeded, violating the active lifecycle/interface contract and the live acceptance requirement for repository acquisition or processing progress. The smallest repair emits fixed, sanitized `clone`, `processing`, and `chunk` callbacks around existing GitHub acquisition, corpus materialization, and chunking. The offline managed-GitHub regression asserts all three durable stages. A repeat live Chromium run observed all three.

### `product_defect`: graceful shutdown warning absent in real Uvicorn lifecycle

The service unit test logged correctly, but live SIGTERM with an open SSE connection caused Uvicorn to wait for the connection until the worker completed before entering application lifespan shutdown. The real process waited safely but never emitted the required active-job warning. The repair adds a default-server signal hook that asks the service to announce an active non-cancellable worker, deduplicates the service warning when lifespan shutdown later runs, and routes that job logger to one bounded stderr handler for the server lifetime. Regression tests cover signal announcement, one warning, existing safe content, and ordinary service shutdown. Repeat live SIGTERM observed exactly one safe line and preserved non-cancellable completion.

Independent review then found the initial boolean deduplication was service-lifetime sticky after a rejected `shutdown(wait=False)`: after active job A completed, later active job B could enter a real waiting shutdown without its own warning. The post-review repair scopes deduplication to the active job ID. A deterministic regression issued `shutdown(wait=False)` for A, confirmed a repeated announcement did not duplicate A, completed A, started B, observed `shutdown(wait=True)` remain blocked, completed B, and observed exactly one warning for each job.

Other harness corrections were `expected_behavior`, not product defects: rendered CSS uppercasing required case-normalized state parsing; Playwright's complete header view was required to observe the custom CSRF header; and the managed job ID's occurrence in storage-path fields is expected operational identity rather than content identity. No `source_instability`, `documentation_mismatch`, or unresolved `acceptance_environment_failure` remained. The preferred website and GitHub sources were available.

## Commands and exact outcomes

- `git fetch origin main`; branch/worktree checks — passed; base `6910ec7` from latest `origin/main`.
- `uv run buoy serve --help`, `uv run buoy plan --help`, `uv run buoy apply --help` — passed; actual syntax used.
- `git diff --check`; `uv lock --check`; `uv sync --locked --extra ui` — passed.
- Initial focused backend basket (planning/jobs/local/remote/API/CLI) — 122 tests passed.
- `npm ci` — passed, 214 packages installed; the two known high React Router advisory findings remained the existing mode-inapplicable scanner result.
- Initial/final `npm test -- --run` — 40/40 tests passed.
- Initial/final `npm run build` — passed; 42 modules transformed, packaged JS/CSS names unchanged, and no static-asset diff remained.
- Focused defect regressions — GitHub managed-progress test passed; three final targeted signal/shutdown/GitHub tests passed.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — passed: 13 datasets, 13 folds, 369 judgments; expected Buoy insufficiency unchanged.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — passed; hash `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Final `PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q` — 737 tests passed.
- Final UI-extra focused basket including release automation — 156 tests passed.
- `uv build --out-dir dist` — passed; wheel and sdist built successfully.
- `uv sync --locked`; `uv lock --check`; final `git diff --check` — passed.
- Real-browser acceptance harness — passed all startup, website, GitHub, reload, review, conflict, graceful, abrupt-restart, dry-run, authority, and security checks; 147 browser requests captured and zero HTTP 500+ responses.
- Targeted malicious-literal browser check — passed: literal visible, zero injected script nodes, execution flag false.
- Post-review targeted shutdown-deduplication regression — 1 test passed.
- Post-review `tests.test_command_center_jobs tests.test_command_center_api` with the UI extra — 75 tests passed, no skips; default dependencies were restored afterward and `uv lock --check` passed.
- Post-review `git diff --check` — passed.
- Independent rereview — passed with no remaining finding; recorded at `.10x/reviews/2026-07-24-command-center-phase-2a-live-acceptance.md`.

## Cleanup, limits, and supported claim

All Buoy processes, fixture servers, browser contexts, temporary clones/artifacts/jobs/state/logs, and temporary roots were stopped or removed. No acceptance listener remained. Browser downloads stayed in the host Playwright cache and no dependency file changed.

This is one native macOS/Chromium acceptance run against the named public sources. It does not claim Firefox, WebKit, Windows, or Linux coverage and is not an invasive security assessment or packet capture. No push, merge, pull request, publish, release, approved/interactive apply, turbopuffer write, remote status refresh, live search, managed database plan, or external mutation occurred.
