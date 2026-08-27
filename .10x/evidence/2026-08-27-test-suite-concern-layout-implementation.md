Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-reorganize-test-suite-by-concern.md, .10x/specs/buoy-test-suite-layout.md, .10x/decisions/buoy-advances-repo-eval-for-test-layout.md

# Test suite concern-layout implementation

## What was observed

All 62 Python modules formerly directly under `tests/` were moved as whole files into the exact eleven concern packages governed by `.10x/specs/buoy-test-suite-layout.md`. The only Python file now directly under `tests/` is an empty `__init__.py`; all eleven concern initializers are also empty. `tests/fixtures/retrieve_command_timing_probe.py` remained in place.

Cross-test imports were updated to their new fully qualified package paths. Relocation-dependent repository-root lookups were advanced one parent level, and the telemetry subprocess probe now resolves the unchanged shared `tests/fixtures/` path. No flat forwarding module or compatibility shim was created.

Execution discovered that five moved test paths were judgments in immutable current repo-eval v2. Work stopped before any eval mutation. After explicit owner authority in `.10x/decisions/buoy-advances-repo-eval-for-test-layout.md`, implementation preserved the exact v2 bytes and created baseline-pending, promotion-ineligible v3 with exactly these mappings:

```text
tests/test_cli.py         -> tests/cli/test_cli.py
tests/test_crawler.py     -> tests/indexing/test_crawler.py
tests/test_evals.py       -> tests/evals/test_evals.py
tests/test_github_repo.py -> tests/indexing/test_github_repo.py
tests/test_retriever.py   -> tests/retrieval/test_retriever.py
```

V3 carries every v2 case, question, grade, reason, and non-path semantic unchanged. It uses a new path-membership-only manifest and makes no corpus, benchmark, or promotion claim. Active fixture/autoresearch/docs pointers use v3; the production promotion basket registry remains empty.

## Structural and semantic procedure

The move used filesystem renames, not file recreation or splitting. Subsequent edits inside moved test modules were limited to:

- cross-test import qualification;
- relocation-dependent `Path(__file__)` repository/fixture references;
- active v3 dataset path references; and
- mechanically derived v3 registry/hash/count assertions in the existing ranking-contract tests.

No test method/class was renamed, no test was added or removed, and no ordinary assertion or fixture behavior was changed. Pytest collection reproduced exactly 1,191 tests before execution. Full pytest and both standard-library discovery runs reproduced the same 1,191-test baseline; pytest also reproduced exactly 1,292 subtests. The unchanged counts and scripted rename/edit inventory support the folders-only semantic boundary.

Exact layout audit output:

```text
{'moved_modules': 62, 'concern_packages': 11, 'root_python': ['__init__.py'],
 'empty_initializers': 12, 'layout': 'exact'}
```

Searches found no flat `tests.test_*`/`tests.routing_confidence_fixtures` imports, no root test/support/benchmark modules, and no compatibility shims.

## Immutable evaluation identities

```text
v2 dataset SHA-256:
691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae

v2 path-membership SHA-256:
4b7739515d15cd14b9cf9e374e5318c7fa9e7a3bb7e208f25878e6489751068b

v3 dataset SHA-256:
d3e1b63a5e2c70c586dfeb588991c16173d06e749bb520a802e79149594fc184

v3 path-membership SHA-256:
896fa063e78ab734cdb7b8efa04267a3f673c11eb01bb294bc7967ffb6b9ef10
```

The ranking validator independently reproduced v1, immutable v2, active v3, exactly five mappings, `baseline_status=pending`, and `promotion_eligible=false`.

## Validation results

### Collection and full pytest

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest --collect-only -q
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q
```

Collection: `1191 tests collected`.

Full suite: `1191 passed, 57 warnings, 1292 subtests passed in 93.52s`. Warnings were the existing lxml `strip_cdata` deprecations under the moved crawler exact-host module.

### Python 3.11 and 3.13 standard-library discovery

For each runtime:

```sh
uv sync --locked --python <3.11|3.13>
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src \
  uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Python 3.11: `Ran 1191 tests in 119.603s`, `OK`.

Python 3.13: `Ran 1191 tests in 109.238s`, `OK`.

The project environment was left restored to locked Python 3.13. Existing best-effort plan cleanup and lxml warnings remained non-failing.

### Validators and workflow coverage

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
BUOY_RANKING_AUTHORITY_INTRODUCTION=true \
BUOY_RANKING_EVENT_NAME=pull_request \
BUOY_RANKING_PR_BASE_REF=$(git rev-parse HEAD) \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m compileall -q src tests scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m unittest tests.core.test_ci_workflow -q
```

All passed. Promotion validation retained zero registered baskets. C6 retained exact valid digest `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`. Workflow coverage passed three tests from its new package path.

### Distribution and isolated install

```sh
uv build --out-dir /tmp/buoy-test-layout-dist
```

Build passed with a 93-entry wheel and 189-entry sdist. Both contained immutable v2, active v3, both path-membership manifests, and the version registry.

A fresh Python 3.13 environment installed the wheel. Isolated validation loaded active version 3, proved v2 remained packaged, and passed `python -m buoy_search --help`.

### Hygiene

`git diff --check` passed. `git diff --cached --name-only` returned no output; no files are staged.

## What this supports

This supports the ticket's structural mapping, no-shim, discovery/count, cross-import, immutable-v2/v3-successor, validator, package, and no-external-effect acceptance criteria. It provides implementation evidence for independent review; it does not itself satisfy the review gate.

## Parent-observed closure validation

After independent review, the parent directly inspected the complete test tree and empty initializers, confirmed that only `tests/__init__.py` remains at the root, and reran:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q
```

The validator reproduced immutable v2 and active pending/promotion-ineligible v3 with exactly five mappings. The full suite passed with `1191 passed, 57 warnings, 1292 subtests passed`. `git diff --check` passed and no files were staged.

## Limits and residual risk

- Independent review remains required before ticket closure.
- GitHub-hosted Actions was not run. Exact workflow tests and dual-runtime CI commands passed locally; hosted execution naturally occurs on a future PR.
- No benchmark, retrieval, model, provider, credential, namespace, catalog, release, publication, or deployment operation occurred. Isolated package installation fetched ordinary declared dependencies only.
