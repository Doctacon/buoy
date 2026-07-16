Status: active
Created: 2026-07-14
Updated: 2026-07-15

# Buoy Package and CLI Identity

## Purpose and scope

Define the code and distribution identity for Buoy through the 0.3 release.

## Behavior

- Project metadata MUST use display name `Buoy`, distribution name `buoy-search`, current release version `0.3.0`, and Apache-2.0 licensing with a root `LICENSE` file.
- Implementation code MUST live under `src/buoy_search`; internal imports, tests, mocks, module commands, bundled data paths, reports, and build configuration MUST use `buoy_search`.
- The primary console script MUST be `buoy = buoy_search.cli:main`; CLI help and version output MUST identify `buoy`.
- Version 0.3 MUST continue to expose `turbo-search` through a dedicated legacy entry point that emits one concise deprecation warning to stderr and then executes identical behavior. JSON stdout MUST remain clean.
- `python -m buoy_search` and `python -m buoy_search.autoresearch` MUST work. `turbo_search` Python imports/module execution are an intentional clean break and MUST be documented in the migration guide.
- User agents, generated runner identifiers, self-referential eval questions, expected source paths, fixture names, and active user-facing error text MUST use the new identity.
- Existing semantic identifiers unrelated to branding—including source namespaces, plan IDs, apply IDs, deterministic remote `ts_*` row IDs, and intermediate `jf_*` chunk IDs—MUST NOT change solely for the rebrand.
- The wheel/sdist MUST contain `buoy_search` and required bundled datasets, and MUST NOT contain the old implementation package.

## Compatibility

- The deprecated `turbo-search` console alias remains supported through 0.3 and is marked for removal in 0.4.
- No Python import shim is provided.
- Existing plan and state compatibility is governed separately by `.10x/specs/buoy-local-compatibility.md`.

## Acceptance scenarios

- A clean install can run `buoy --version`, `buoy --help`, and `python -m buoy_search --help`.
- Running `turbo-search --help` emits a deprecation warning on stderr and otherwise matches `buoy --help`.
- Importing representative modules from `buoy_search` succeeds; importing `turbo_search` is not part of the supported contract.
- Package build inspection finds the new module/data and no old implementation module.

## Explicit exclusions

GitHub repository mutation, PyPI publication, remote namespace changes, live Turbopuffer calls, and float16 inference implementation.
