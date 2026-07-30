Status: superseded
Created: 2026-07-21
Updated: 2026-07-21

# Buoy Dynamic Release Validation

## Purpose and scope

Define code/artifact validation shared by labeled PR readiness and automatic main-push publication after v0.4. Supersedes `.10x/specs/superseded/buoy-v0-4-release-validation.md` for future candidates.

## Required validation

For an explicitly derived target stable version:

- Validate dynamic Hatch VCS configuration, pinned build dependencies, lock stability, canonical repository, and generated version-file contract.
- Build wheel and sdist once from clean output using exact target override and deterministic environment.
- Assert wheel/sdist filenames, core metadata, generated `buoy_search.__version__`, installed metadata, and `buoy --version` equal target.
- Inspect sole `buoy` entry point, package/data/tokenizer inventory, and absence of `.10x/**`, `turbo-search`, `legacy_main`, old implementation package, and release-plan internals.
- Clean-install wheel and run `buoy --version`, `buoy --help`, `python -m buoy_search --help`, representative imports, and exact tokenizer smoke.
- Run complete locked Python 3.11/3.13 tests/docs plus ranking/C6 validators and diff/link/policy checks.
- Validate target tag/Release absence during readiness and exact authoritative state during main publication.
- Perform no provider/model/live retrieval/apply/eval, namespace, PyPI, user-state, or product mutation.

## Evidence boundary

Passing readiness authorizes only protected PR merge. Passing main validation authorizes only the exact immutable state-machine action in `.10x/specs/main-push-automatic-github-release.md`. A passed build/test does not authorize partial release repair or provider operations.
