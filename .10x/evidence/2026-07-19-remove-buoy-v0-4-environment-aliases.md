Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/done/2026-07-19-remove-buoy-v0-4-environment-aliases.md, .10x/specs/buoy-v0-4-environment-alias-removal.md

# Buoy 0.4 Environment Alias Removal Implementation Evidence

## What was observed

The task branch implements the ratified pre-dispatch presence gate for exactly `TURBO_SEARCH_EMBEDDING_MODEL` and `TURBO_SEARCH_EMBEDDING_PRECISION`. The old fallback, warning, equal-value acceptance, and conflict-selection logic is absent from runtime configuration. Current `BUOY_*` and `TURBOPUFFER_*` configuration paths are unchanged.

Local tests observed:

- every real primary and catalog command, including apply interactive/dry-run/approved and catalog preview/approved cases, rejected model-only, precision-only, and both-present environments with exit 2 before its patched handler sentinel ran;
- the value/empty/equal/different/insertion-order matrix produced exact singular/plural diagnostics, deterministic model-then-precision ordering, zero stdout under `--json`, and one newline on stderr without observed values;
- primary and autoresearch help, primary version, all top-level/catalog-subcommand help, bare `buoy`, bare `buoy catalog`, and `python -m` help remained available;
- malformed primary and autoresearch arguments retained argparse output instead of the removed-variable diagnostic;
- autoresearch rejection occurred before patched experiment loading/running and did not create its requested output directory;
- direct config tests observed that removed names never became the effective model or precision, while current variables/defaults and vendor region/namespace behavior remained unchanged.

No test invoked a real command handler after rejection. Therefore no handler-owned credential lookup, state-root discovery, artifact or plan access, DuckDB access, model load, remote client construction, or local/remote mutation began. Validation used no live Turbopuffer credentials or endpoint and performed no state/data migration, publication, tag, release, or remote operation.

## Procedure and results

1. `uv run python -m unittest tests.test_config tests.test_environment_alias_removal tests.test_cli tests.test_autoresearch tests.test_release_automation`
   - Passed: 75 tests on CPython 3.13.0.
2. `uv run python -m unittest tests.test_environment_alias_removal -v`
   - Passed: 7 focused test methods covering the command/help/version/matrix/no-dispatch contract.
3. `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q`
   - Passed: 422 tests.
4. `uv sync --locked --python 3.11 && PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q`
   - Passed: locked sync and 422 tests on CPython 3.11.5.
5. `git diff --check`
   - Passed with no whitespace errors.
6. First temporary distribution-inspection script after a successful `uv build` failed because it incorrectly counted uv's output-directory `.gitignore` as a distribution artifact. This did not indicate a product/build failure and wrote only below `/tmp`.
7. Corrected temporary distribution check: `uv build --out-dir "$dist_dir"` followed by Python `zipfile`/`tarfile` inspection filtering `*.whl` and `*.tar.gz`.
   - Passed: wheel and sdist built below `/tmp/buoy-env-alias-dist.awcMiN`; the wheel contained the changed runtime modules and the sdist contained `tests/test_environment_alias_removal.py`.
8. `PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_config tests.test_environment_alias_removal tests.test_cli tests.test_autoresearch tests.test_release_automation -q`
   - Passed: 75 focused tests after final diff inspection.
9. Repository searches for the two removed names and legacy fallback identifiers across `src`, `tests`, `docs`, `CHANGELOG.md`, and active specs.
   - Observed removed names only in the presence detector, diagnostics/tests, migration/changelog text, and governing historical/current spec statements; no fallback variables or deprecation-warning implementation remained.
10. Pull request [#48](https://github.com/Doctacon/buoy-search/pull/48) at implementation commit `96ff96e563a0e5b57207446534040fe881e5e2cb` ran hosted workflow `29708193056`.
   - Python 3.11 job `88248483359`: passed in 52 seconds.
   - Python 3.13 job `88248483358`: passed in 56 seconds.
   - Build distributions job `88248542411`: passed in 11 seconds.

The two pre-existing advisory cleanup warnings printed by full/focused tests concern mocked plan cleanup behavior and did not fail either suite.

## Changed paths observed before record/progress updates

- `.10x/specs/buoy-local-compatibility.md`
- `.10x/specs/embedding-inference-precision.md`
- `CHANGELOG.md`
- `docs/migrating-to-buoy.md`
- `src/buoy_search/autoresearch.py`
- `src/buoy_search/cli.py`
- `src/buoy_search/config.py`
- `tests/test_cli.py`
- `tests/test_config.py`
- `tests/test_environment_alias_removal.py`
- `tests/test_release_automation.py`

## What this supports

This supports the child ticket's local implementation, exact stream/exit behavior, parser/dispatch ordering, exhaustive real-command sentinel coverage, configuration cleanup, focused docs/spec coherence, supported-Python suites, and local distribution construction. It also supports the claim that rejection itself began no command, experiment, credential, state, data, artifact, DuckDB, model, or remote operation.

## Limits

- Independent source review, aggregate review, and integration with the console-alias sibling remain pending; passing hosted checks do not satisfy those review gates.
- Candidate 0.4.0 version metadata is intentionally absent from this child diff. The parent plan assigns package/module/lock candidate metadata to the console-alias sibling and requires aggregate reconciliation before integration. The locally built standalone child artifacts therefore still report the base version `0.3.0`; they establish build integrity, not final candidate-version acceptance.
- No live remote behavior was exercised. Non-rejection behavior is supported by the unchanged-handler boundary plus passing existing tests, not by live Turbopuffer calls.
- Temporary build outputs are outside the repository and are not release candidates; nothing was published, tagged, or released.
