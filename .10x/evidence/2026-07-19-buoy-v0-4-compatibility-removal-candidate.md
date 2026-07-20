Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/done/2026-07-19-buoy-v0-4-compatibility-removal-plan.md, .10x/tickets/done/2026-07-19-remove-buoy-v0-4-console-alias.md, .10x/tickets/done/2026-07-19-remove-buoy-v0-4-environment-aliases.md, .10x/tickets/done/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md, .10x/specs/buoy-v0-4-console-alias-removal.md, .10x/specs/buoy-v0-4-environment-alias-removal.md, .10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md

# Buoy 0.4 Compatibility Removal Aggregate Candidate

## What was observed

Aggregate implementation commit `68477fdca5a5b5f7b890d059c484739f02fc1dd8` combines the complete reviewed child tips `b6bbfcc` and `a049bbf` on base `31b355a` with two non-fast-forward merges. Both child tips are ancestors of the candidate, preserving their full histories and diffs.

The first merge, for the console child, was conflict-free. The environment-child merge reported two conflicts:

- `CHANGELOG.md`: resolved by retaining both independently specified removal bullets under one `Removed` section.
- `tests/test_cli.py`: resolved by retaining the environment child's exact exit-2 tests while retaining the console child's deletion of the obsolete `legacy_main` import and alias-only test.

Git automatically reconciled the shared migration document, CLI, and release-automation tests without conflict. Candidate-versus-child diffs and full tests confirmed those shared resolutions contain both contracts without adding behavior.

Source/project/lock metadata report `0.4.0`; `[project.scripts]` contains only `buoy = "buoy_search.cli:main"`; runtime source and built CLI contain no `legacy_main`; and the environment presence gate remains exactly the reviewed post-parse/pre-dispatch detector in the primary and autoresearch entry points. Searches found no old fallback variables, warning path, or legacy hook in runtime source. Retained `.turbo-search`, plan/flag/direct-command, migration, `BUOY_*`, and `TURBOPUFFER_*` references remain present, and non-conflicting paths are byte-for-byte identical to their owning reviewed child tips.

## Supported-Python and focused validation

- `UV_PROJECT_ENVIRONMENT=/tmp/buoy-v040-candidate-py311 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q`: passed 422 tests on CPython 3.11.5 in 39.515 seconds.
- `UV_PROJECT_ENVIRONMENT=/tmp/buoy-v040-candidate-py313 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q`: passed 422 tests on CPython 3.13.0 in 38.368 seconds.
- `UV_PROJECT_ENVIRONMENT=/tmp/buoy-v040-candidate-py313 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest tests.test_config tests.test_environment_alias_removal tests.test_cli tests.test_autoresearch tests.test_release_automation -v`: passed 75 focused tests in 4.529 seconds.
- The full/focused runs emitted two pre-existing mocked plan-artifact cleanup advisories and still passed. All test filesystem work was temporary; no user or repository state root was used.

The focused environment suite covered every actual primary/catalog command with sentinel non-dispatch; empty/old-only/old+new equal/different values; both insertion orders; exact singular/plural value-redacted diagnostics; exit 2; empty JSON stdout; help/version/no-handler and parser precedence; and autoresearch rejection before experiment/output access. No live handler, credential, model, state, artifact, plan, DuckDB, network, or remote path began.

## Distribution construction and inspection

From exact aggregate implementation commit `68477fdca5a5b5f7b890d059c484739f02fc1dd8`:

```text
/tmp/buoy-v040-candidate-artifacts-68477fd/buoy_search-0.4.0-py3-none-any.whl
SHA-256 e6f682081f86b897ed61dbffd17c4ad6e4385c9a7de46f8659b99538961997fc

/tmp/buoy-v040-candidate-artifacts-68477fd/buoy_search-0.4.0.tar.gz
SHA-256 6863591298ef822a2f934a16f06ed98f440654b696b3ac7b40b258264332255c
```

`uv build` succeeded, and `scripts/release_checks.py tag --tag v0.4.0` plus `assets --dist` passed. Direct archive inspection observed:

- wheel: 45 files, distribution `buoy-search` version `0.4.0`, 19 `buoy_search/data` files, and zero `.10x` entries;
- wheel `entry_points.txt` exactly `[console_scripts]\nbuoy = buoy_search.cli:main\n`;
- no `turbo_search` package and no `legacy_main` in bundled CLI source;
- sdist: 536 files, 0.4.0 project metadata, no console alias/hook, and the aggregate environment-gate test present;
- subsequent direct inventory of these recorded artifacts found 441 `.10x` entries in the sdist. This blocks the newly ratified both-artifact packaging boundary and makes record-only evidence capable of changing the sdist.

## Clean candidate install

A fresh Python 3.13 environment at `/tmp/buoy-v040-candidate-clean-68477fd/venv` installed the candidate wheel normally. Installed metadata reported version 0.4.0 and exactly `('console_scripts', 'buoy', 'buoy_search.cli:main')`. `buoy --version` printed `buoy 0.4.0`; `buoy --help` and `python -m buoy_search --help` began `usage: buoy [-h] [--version]`; complete launcher-directory inspection found `buoy` and no `turbo-search`; and an explicit absence assertion passed.

The installed wheel also returned 2 for a representative removed-model invocation, wrote zero stdout bytes, and wrote exactly one newline-terminated value-redacted mapping diagnostic to stderr.

## Digest-verified same-environment 0.3.0 upgrade

Validation downloaded only:

`https://github.com/Doctacon/buoy-search/releases/download/v0.3.0/buoy_search-0.3.0-py3-none-any.whl`

`shasum -a 256` returned and matched required digest `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab` before installation. A fresh Python 3.13 environment at `/tmp/buoy-v040-candidate-upgrade-68477fd/venv` then installed that released wheel. Before upgrade, installed metadata reported 0.3.0 with `buoy` and `turbo-search` entry points; both package-owned launchers existed and both help paths succeeded.

Without recreating the environment, `uv pip install --python /tmp/buoy-v040-candidate-upgrade-68477fd/venv/bin/python --upgrade /tmp/buoy-v040-candidate-artifacts-68477fd/buoy_search-0.4.0-py3-none-any.whl` upgraded normally. Afterward, metadata reported 0.4.0 with only the `buoy` entry point, `buoy --version` and help succeeded, complete launcher inspection found no `turbo-search`, and explicit old-launcher absence passed. This supports package-owned launcher deletion only, not arbitrary user-owned aliases, copies, wrappers, or caches.

## Diff, history, reference, and status checks

- `uv lock --check`, `git diff --check`, release tag/assets checks, and metadata coherence assertions passed.
- `git merge-base --is-ancestor b6bbfcc HEAD` and the equivalent `a049bbf` assertion passed.
- Non-conflicting console-child and environment-child path comparisons were identical to their reviewed tips.
- Combined diff from `31b355a` contains 23 paths, exactly the union of the reviewed child changes plus the conflict reconciliation described above.
- Runtime searches found no `legacy_model`, `legacy_precision`, `legacy_main`, old removal warning, or deprecated fallback implementation.
- Migration/reference searches retained both exact substitutions, console executable-only guidance, current variables, vendor variables, and unrelated compatibility references.
- One optional installed-wheel gate attempt used `--no-deps` and failed at import with `ModuleNotFoundError: duckdb`; this was a validation-harness mistake, not a product failure. The same assertion then passed in the normally installed clean candidate environment.

## Hosted candidate checks

Aggregate PR [#49](https://github.com/Doctacon/buoy-search/pull/49) targets `develop` without merging. Workflow `29708550897` on pushed evidence head `6d4a24c27c215cc40ddcb9e8d4d66211ed2d445d` passed Python 3.11 job `88249318152` in 47 seconds, Python 3.13 job `88249318150` in 1 minute 3 seconds, and distribution job `88249388732` in 9 seconds. A subsequent record-only commit documents these observations; its exact-head hosted status remains observable on PR #49.

## Side-effect attestation

No package was published; no tag or GitHub Release was created; no registry write, live Turbopuffer call, namespace operation, remote data read/write, user-state discovery, state/data migration, local data deletion, or user-owned launcher operation occurred. Build, install, upgrade, test, and artifact outputs were confined to disposable `/tmp` locations. Network reads were limited to dependency resolution/downloads and the immutable GitHub 0.3.0 artifact. Authorized Git branch push and pull-request creation were the only remote writes and did not merge either child or aggregate PR.

## What this supports

This supports aggregate source, history, version, console removal, exact environment gate, retained compatibility, focused/full test, clean-install, released-wheel same-environment upgrade, migration-guidance, and bounded-side-effect acceptance at implementation commit `68477fdca5a5b5f7b890d059c484739f02fc1dd8`.

It does not support final aggregate artifact acceptance under `.10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md`: the recorded sdist contains 441 `.10x` entries, no controlled record-only byte/digest stability proof exists, and aggregate install/upgrade validation must be rerun after the exclusion is implemented.

## Limits and residual risk

- Local build/install/upgrade validation ran on macOS/Python 3.13; complete source suites separately passed on Python 3.11 and 3.13.
- Normal 0.3.0-to-0.4.0 upgrade reconciled the candidate's reviewed `scrapling==0.4.9` pin and related transitive versions; neither child changed that dependency contract.
- No live remote behavior was exercised; gate safety is supported by sentinel/non-dispatch tests and existing non-live suites.
- Hosted aggregate checks passed for the pre-exclusion candidate, but do not resolve the `.10x/**` artifact blocker.
- `.10x/tickets/done/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md` must implement the exact exclusion, prove both-artifact controlled determinism across a record-only delta, rerun aggregate install/upgrade validation, and pass independent review plus exact-head hosted checks.
- Independent final aggregate review remains pending. Parent and all children remain active and must not close while the packaging child is incomplete.

## Subsequent packaging disposition

The packaging-blocker statements above describe the pre-exclusion candidate at implementation commit `68477fdca5a5b5f7b890d059c484739f02fc1dd8`; they do not describe the current candidate. Exact reviewed head `9e7ec237d31d9fb4ef79209df1d45fcc2b0dd6cf` implements and validates the exclusion. Superseding evidence is `.10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md`, and current review disposition is `.10x/reviews/2026-07-19-buoy-v0-4-compatibility-removal-final-aggregate-review.md`. Parent and all three children remain active/open pending final bounded re-review, not pending implementation of the exclusion.
