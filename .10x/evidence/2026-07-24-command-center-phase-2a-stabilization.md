Status: recorded
Created: 2026-07-24
Updated: 2026-07-24
Relates-To: .10x/tickets/done/2026-07-24-implement-command-center-phase-2a-stabilization.md, .10x/tickets/done/2026-07-24-command-center-phase-2a-stabilization.md, .10x/specs/phase-2a-stabilization.md

# Command Center Phase 2A Stabilization Validation

## What was observed

### Unsupported-platform fallback

The platform probe raises only `ManagedPlanningUnsupportedError` for absent `O_NOFOLLOW`, absent `O_DIRECTORY`, missing descriptor-relative support, or missing descriptor enumeration. FastAPI probes before constructing `PlanJobService`. Tests observed successful health/dashboard/inventory startup, sanitized capability values (`managed_public_planning_available=false`, reason `platform_unsupported`, durable history false), and identical structured 503 responses for create/list/detail/events. The service factory was never called; managed job/artifact roots remained absent; source/remote/provider/model modules were not newly imported. Separate startup tests proved integrity/tamper, service ownership, and permission failures propagate rather than degrade.

### Durable event bound

The configured limit is 5,000. Boundary tests used a reduced injected limit to generate 6,000 callbacks efficiently while exercising the exact production comparisons. Persisted sequences remained contiguous, exactly one `Additional progress updates are being coalesced while planning continues.` event appeared, post-marker callbacks left record bytes, event bytes, mtime, timestamp, and sequence unchanged, and service notifications occurred only for persisted changes. Success, failure, and interruption retained terminal events; replay after the marker and terminal observer closure passed. A schema-v1 history already over the injected limit remained readable and could append its terminal interruption without rejection or rewriting old events.

### UI, terminology, shutdown, and advisory

Capabilities now gate every managed frontend route. Unsupported tests rendered no form, history request, EventSource, CSRF request, or POST while Dashboard stated that read-only features remain available. Supported website/GitHub submission, job history, SSE reconnect, plan review, explicit remote refresh, and search regressions passed.

README, guide, CLI help, frontend copy, service errors, active Phase 2A specs, and planning knowledge distinguish credential-free HTTP(S) websites from public GitHub repository roots and state that website validation is not a public-routability/SSRF firewall. The guide documents unsupported fallback, capabilities, 5,000-event coalescing, terminal retention, non-cancellable shutdown wait, and the React Router disposition.

A blocking shutdown test observed one warning containing only the safe job ID/state and no source URL, while the pending future remained blocking until executed. `shutdown(wait=True)` and restart interruption semantics were unchanged.

React Router evidence and disposition are in `.10x/evidence/2026-07-24-react-router-advisory-no-action.md`.

## Procedure and results

- `git diff --check` — passed.
- `uv sync --locked` and `uv lock --check` — passed.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — passed; 13 datasets/13 folds/369 judgments, expected Buoy insufficiency unchanged.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — passed; forecast hash `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Final core full suite: `python -m unittest discover -s tests -p 'test_*.py' -q` — 736 passed, 30 skipped (optional UI absent in core environment).
- Final UI-extra focused basket across planning/jobs/local/remote/API/CLI/release automation — 155 passed, no skips.
- `npm ci` — passed.
- `npm test -- --run` — 40 passed.
- `npm run build` — passed; synchronized static JS `assets/index-lDcMEzTj.js` and existing CSS produced.
- `npm ls react-router react-router-dom --all` — `react-router-dom@7.18.1 -> react-router@7.18.1`.
- `npm audit --omit=dev --audit-level=high` — expected exit 1: two high findings on GHSA-qwww-vcr4-c8h2 through the same dependency edge; suggested force fix is a breaking downgrade. Source-backed no-action rationale applies because Buoy has no affected RSC/action path.
- `uv build --out-dir dist` — passed; wheel 68 entries, sdist 155 entries. Wheel contains synchronized static index/JS/CSS; sdist contains frontend sources/lockfile; neither contains `node_modules`.
- Temporary installed-wheel check — supported `/`, capabilities, and hashed static asset returned 200; simulated missing `O_NOFOLLOW` kept `/`, dashboard, capabilities, and structured plan-job 503 available without managed roots.

The first installed-wheel check used unresolved macOS `/var/...` temporary paths and correctly failed the existing no-follow ancestor check because `/var` is a symlink. Re-running with `Path.resolve()` used the real `/private/var/...` path and passed; no source change was made to weaken that safety control.

## Post-review repair validation

Independent review found that unsupported invalid query parameters could reach FastAPI validation before the route-level 503, shutdown inspected a mutable future dictionary before cleanup protection, one import-isolation assertion ran after explicit search imported its allowed remote module, the router guard was non-recursive, and unavailable managed routes lacked an `h1`. The repairs now intercept every unavailable `/api/v1/plan-jobs` path in middleware after Host validation but before route parsing; snapshot futures and close the start gate under the shared start/shutdown lock; degrade only the shutdown log's state to `unknown` if audit lookup fails while still waiting and releasing ownership; capture startup imports before explicit remote/search requests; recursively inspect `web/src`; and render an unavailable page heading.

Focused post-repair validation observed:

- isolated unsupported-platform API test — 1 passed, including invalid `offset`/`limit` uniform 503s, security headers, no factory/root creation, and startup-only import assertions;
- shutdown regressions — 3 passed, including safe log/wait, state-lookup failure cleanup with replacement ownership, and rejection of start after the shutdown snapshot;
- API/jobs/release basket — 102 passed;
- recursive router guard — passed;
- Vitest — 40 passed;
- production frontend build — passed and regenerated synchronized `assets/index-lDcMEzTj.js`.

A rereview then found that a second concurrent `shutdown(wait=True)` caller returned while the first caller still waited for the active worker. The repair separates the start-prohibiting `_closed` gate from a dedicated shutdown-completion event. The first caller snapshots work and owns cleanup; later `wait=True` callers wait for completion, while `wait=False` retains its non-cancelling behavior. A two-caller regression held both shutdown threads until the captured worker completed, then observed both return and a replacement service acquire ownership.

A final rereview found that one artifact-close or unlock exception could skip later cleanup while still signaling completion. The final implementation clears retained artifact descriptor state first, attempts every descriptor close plus owner unlock, owner-handle close, and notification independently, preserves the first cleanup failure, stores it for concurrent waiting callers, and signals completion only after all attempts. Fault injection closed the first descriptor and then raised, yet all remaining descriptors were attempted, notification ran, the owner handle closed, the same failure reached a later `wait=True` caller, and a replacement service acquired ownership. Separate unlock-after-release fault injection likewise closed the owner handle, ran notification, and allowed replacement ownership. All 43 durable-job tests passed; `git diff --check` and the no-staged-files check passed.

The final acceptance review found stale capability state when one FastAPI app experienced an unsupported lifespan and was then started again on a supported platform. The supported lifespan now explicitly restores `managed_public_planning_available=true` and clears the unavailable reason before exposing its constructed service. A same-app regression first observed `platform_unsupported` and plan-job HTTP 503 with no service construction, then started the same app without the missing primitive and observed available capabilities, durable history, successful job listing/creation, and normal service shutdown. The focused lifecycle test and all 30 Command Center API tests passed; `git diff --check`, no-staged-files, default-environment restoration, and `uv lock --check` passed.

## What this supports or challenges

This supports every acceptance criterion in `.10x/specs/phase-2a-stabilization.md` while preserving `PLAN_SCHEMA_VERSION`, `JOB_SCHEMA_VERSION=1`, identities, plan artifact hashes, supported source behavior, explicit remote operations, security checks, and Phase 2A authority.

## Limits

No live crawl, clone, provider/turbopuffer call, model load, source database access, push, PR, merge, publish, or release was performed. The npm audit remains nonzero for the documented mode-inapplicable advisory. Final full core tests and the final focused UI-extra basket passed; a second full 736-test run under UI-extra was unnecessary because all API/UI-extra tests were included in the 155-test basket. Independent closure review passed in `.10x/reviews/2026-07-24-command-center-phase-2a-stabilization-review.md`.
