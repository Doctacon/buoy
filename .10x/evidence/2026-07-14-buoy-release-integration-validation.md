Status: recorded
Created: 2026-07-14
Updated: 2026-07-14
Relates-To: .10x/tickets/done/2026-07-14-buoy-release-integration-validation.md, .10x/specs/buoy-release-validation.md, .10x/tickets/done/2026-07-14-buoy-rebrand-plan.md

# Buoy 0.2 Release Integration Validation

## Raw evidence

Sanitized structured output, including complete wheel/sdist/installed-file inventories, is retained at `.10x/evidence/.storage/2026-07-14-buoy-release-integration-validation.json`. It contains no credentials.

## What was observed

### Built artifacts and isolated install

A new temporary build produced `buoy_search-0.2.0.tar.gz` and `buoy_search-0.2.0-py3-none-any.whl`. Inspection confirmed:

- distribution/version/license: `buoy-search` / `0.2.0` / `Apache-2.0`;
- console scripts: `buoy = buoy_search.cli:main` and `turbo-search = buoy_search.cli:legacy_main`;
- root license in sdist and wheel license metadata;
- 34 `buoy_search` wheel entries and all 19 bundled JSON datasets;
- the self-search dataset is present;
- neither artifact contains a `turbo_search` implementation package.

The wheel was installed with dependencies into a fresh temporary virtual environment. `buoy --version`, `python -m buoy_search --version`, and legacy `turbo-search --version` all returned `buoy 0.2.0`; primary/module stderr was empty. Primary, module, and legacy help stdout were byte-identical and began `usage: buoy`; only legacy execution emitted the exact one-line 0.3 removal warning. Legacy dry-run retrieval produced parseable clean JSON stdout with the warning only on stderr. Installed package resources exposed all 19 datasets, and `turbo_search` had no import spec.

### Local compatibility

All compatibility scenarios ran in temporary directories using the isolated wheel and no credentials:

- A local-document plan with neither root selected `.buoy/state/...`, reported no API calls, and did not create a state root.
- A schema-supported plan recording `.turbo-search` preflighted against an existing DuckDB ledger through implicit legacy fallback. It loaded one matching `ts_*` row, reported `first_apply=false`, zero upserts, and no API calls. The complete legacy-root path/hash snapshot was unchanged and `.buoy` was not created.
- With both implicit roots present, `apply` exited 2 before plan discovery, named both roots, required `--state-root`, and left both marker snapshots unchanged.
- With both roots present, an explicit `--state-root chosen-state` bypassed implicit resolution and preflighted a matching plan. Neither implicit root changed and the absent explicit root was not created.
- Legacy environment-only retrieval selected the legacy model with one stderr warning and no API calls. Conflicting new/old model variables exited 2 with empty stdout rather than guessing.

The committed pre-rebrand golden regression also preserved artifact hash `aa7faed6db9f353d87a959cc575a408e3278963610eacec1ef7f2aca0f71f7c8`, remote row ID `ts_2fd4695f91b79df01d0f8b1d47587127`, and namespace `site-example-com-v1`.

No test copied, moved, merged, deleted, embedded, or remotely mutated state or namespaces.

### Evals, assets, docs, and identity

Fixture autoresearch passed 10/10 cases with `repo_search_score=100.0` and no API calls. A self-search eval dry run loaded all ten cases, made no API calls, and every judged repository path existed.

Validation found:

- README: 94 lines / 424 words;
- five Markdown files checked with no broken local link;
- valid dependency-free SVG with the required palette and no forbidden script/image/font/gradient content;
- no puffin asset and no old implementation package;
- no unexpected old-primary identity reference in source, tests, user docs, skills, package metadata, or active records. Remaining references were classified as bounded compatibility, preserved semantic namespaces, external rename source identity, or dated historical progress.

Integration inspection found two stale test-only constant names—`TURBO_SEARCH_REPO_EVAL_DATASET` and `EXPECTED_TURBO_SEARCH_COVERAGE_AREAS`—despite their values already targeting Buoy. They were renamed to Buoy equivalents without changing behavior. The active-reference scan now finds no stale test constant.

## Commands and results

```text
uv build --out-dir <temporary>
PASS: wheel and sdist built

uv venv <temporary> && uv pip install --python <temporary>/bin/python <wheel>
PASS: isolated install with 104 dependencies

<isolated>/bin/buoy --version / --help
<isolated>/bin/python -m buoy_search --version / --help
<isolated>/bin/turbo-search --version / --help
PASS: primary/module/legacy identity and bounded warning contract

<isolated>/bin/turbo-search retrieve "How does this work?" --dry-run --json
PASS: parseable JSON stdout; one warning on stderr; no API calls

Temporary plan/preflight/state-root/environment compatibility harness
PASS: new, legacy, dual, explicit, DuckDB load, old-root plan, no-copy snapshots

PYTHONDONTWRITEBYTECODE=1 uv run python -m buoy_search.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out <temporary> --json
PASS: score 100.0; 10/10; no API calls

PYTHONDONTWRITEBYTECODE=1 uv run buoy evals --dry-run \
  --dataset src/buoy_search/data/buoy_search_repo_search_seed_evals.json \
  --namespace github-doctacon-buoy-search-v1 --json
PASS: 10 cases; all not-run by design; no API calls

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest \
  tests.test_evals tests.test_autoresearch tests.test_cli tests.test_apply_cli \
  tests.test_applied_state tests.test_config -q
Ran 120 tests; OK

PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -p 'test_*.py' -q
Ran 226 tests; OK

uv lock --check
uv run python -m compileall -q src/buoy_search
git diff --check
PASS
```

Both test runs emitted the existing non-fatal temporary plan-cleanup warning and completed successfully.

## Preservation of inherited work

Eleven documentation/record paths were staged before this worker began. Their exact staged path list remained unchanged; this worker did not stage, unstage, reset, or overwrite the index. The repository therefore is not globally free of staged files, but this integration ticket added no staged paths.

## What this supports or challenges

Supports every code-level release-validation criterion before external GitHub mutation. Child tickets, parent sequence, and the downstream GitHub ticket are coherent: the first three children are done, this integration ticket is active pending review, and the external rename still depends on it. Float16 remains blocked until this ticket closes.

## Limits

- Independent adversarial review remains required before closure.
- External web links were not network-checked.
- GitHub was not renamed, PyPI was not published, and no Turbopuffer operation ran.
- The live autoresearch baseline intentionally preserves the old applied namespace and still requires a separate source-path compatibility decision before any future live run.
