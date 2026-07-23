Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Command Center Packaging, Documentation, and CI

## Purpose and scope

Ship the optional local command center without imposing web runtime dependencies or Node on ordinary Buoy users.

## Behavior

- Add a `ui` Python optional dependency containing sensibly bounded FastAPI and Uvicorn versions.
- Commit/build frontend assets into the Python package so wheel and sdist users can run without Node.
- Wheel MUST contain `index.html` and hashed assets; sdist MUST contain the intended frontend source/build inputs.
- Ordinary package imports MUST not require FastAPI, Uvicorn, or Node.
- README MUST document `uv sync --extra ui` and `uv run buoy serve`, loopback-only/read-only behavior, local inspection, explicit remote refresh, search, no mutation, and no graph extraction.
- `docs/command-center.md` MUST document architecture, installation/options, local versus remote activity, credentials, screens, roots, security, troubleshooting, non-goals, and Phase 2 managed workflows, Phase 3 graph backend models, and Phase 4 graph interface roadmap.
- CI MUST retain Python checks and add pinned current Node LTS frontend install/test/build plus Python UI-extra command-center tests and package asset verification.

## Acceptance criteria

1. `npm ci`, `npm test -- --run`, and `npm run build` pass.
2. Python UI tests and the full existing suite pass without live credentials/network/models/browser/server.
3. `uv build` succeeds; wheel and sdist contents satisfy the packaging contract.
4. Required ranking and syntax validation scripts and `git diff --check` pass.
5. Normal locked environment is restored when required.

## Exclusions

No release, publish, push, PR, managed hosting, runtime Node server, desktop installer, or live provider/source validation.
