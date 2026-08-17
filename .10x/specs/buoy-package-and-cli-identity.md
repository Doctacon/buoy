Status: active
Created: 2026-07-21
Updated: 2026-08-17
Amended-By: .10x/specs/user-global-buoy-home-defaults.md

# Buoy Package, Dynamic Version, and CLI Identity

## User-global-default amendment

The later user-global-home specification supersedes only this record's claim
that `.turbo-search` remains an implicit state-root fallback. Explicit legacy
state and plan compatibility remains. The active routing artifact separately
binds the exact raw bytes of `src/buoy_search/cli.py`; this path-default task
does not bypass or silently rewrite that receipt.

## Purpose and scope

Define current code/distribution/CLI identity and tag-derived package version behavior after v0.4. This supersedes `.10x/specs/superseded/buoy-package-and-cli-identity-through-v0-4.md` while preserving its non-version identity and compatibility boundaries.

## Identity

- Product is Buoy; tagline is **Search that stays anchored to the source.**; distribution `buoy-search`; package `buoy_search`; sole console script `buoy = buoy_search.cli:main`; license Apache-2.0 with root `LICENSE`; canonical repository `Doctacon/buoy`; existing visual identity remains.
- Implementation code lives under `src/buoy_search`; internal imports, tests, mocks, module commands, bundled data paths, reports, and build configuration use `buoy_search`.
- `python -m buoy_search` and `python -m buoy_search.autoresearch` work. No `turbo-search` console entry point, `legacy_main`, `turbo_search` import shim, or removed environment aliases return.
- User agents, generated runner identifiers, self-referential eval questions, expected source paths, fixture names, and active user-facing errors use Buoy identity.
- Existing semantic identifiers—including namespaces, plan/apply IDs, deterministic remote `ts_*` row IDs, and intermediate `jf_*` chunk IDs—do not change solely for branding/version automation.
- Existing state/plan compatibility is governed by `.10x/specs/buoy-local-compatibility.md`; `.turbo-search` state-root fallback is not removed. Deprecated environment aliases remain removed under `.10x/specs/buoy-v0-4-environment-alias-removal.md`.
- Migration from old installed commands replaces only the executable name; Buoy does not delete user-created aliases, copied launchers, wrappers, caches, or files outside package-manager ownership.

## Dynamic version behavior

- `[project]` MUST declare `dynamic = ["version"]` and no static version.
- Build requirements MUST pin `hatchling==1.31.0` and `hatch-vcs==0.5.0`.
- Hatch version source MUST be `vcs`; its build hook MUST generate untracked `src/buoy_search/_version.py`; `buoy_search.__version__` imports that generated value.
- Clean locked install/build occurs before source imports that need `_version.py`; the generated file MUST be gitignored and MUST be present in built artifacts.
- Ordinary source/editable installs may expose a valid PEP 440 VCS development version derived from the latest tag and commit.
- Publication is paused under
  `.10x/decisions/release-publication-is-paused.md`. Diagnostic builds retain
  the ordinary tag-derived development version and MUST prove wheel/sdist
  metadata agreement, the generated module, installed metadata, and
  `buoy --version` coherence without selecting a stable target.
- `uv.lock` MUST represent the root project as dynamic editable source without a committed root release version and remain `uv lock --check` stable across commits.

## Artifact and CLI behavior

- Wheel/sdist contain `buoy_search`, generated version module, required datasets/tokenizer, and sole `buoy` entry point; they exclude `.10x/**`, old implementation package/entry points, dedicated legacy hook, and internal release artifacts.
- `buoy --version`, `buoy --help`, `python -m buoy_search --help`, and representative imports work in clean installed wheels.
- Package project URLs use canonical `Doctacon/buoy`.

## Acceptance scenarios

- Clean editable sync after v0.4.0 exposes a PEP 440 development version and passes tests.
- A diagnostic tag-derived development build installs and reports one coherent
  PEP 440 version without publishing it.
- Lock check remains stable after a commit without dependency change.
- Missing generated version during unsupported raw-source import does not justify tracking a stale generated file; supported workflows install/build first.

## Explicit exclusions

Distribution/package/CLI rename; static release-version commits; PyPI; repository/provider/product mutations; removal of separately governed state compatibility.
