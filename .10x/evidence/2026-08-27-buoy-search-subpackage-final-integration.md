Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md, .10x/tickets/done/2026-08-27-decouple-evidence-from-source-layout-plan.md, .10x/tickets/done/2026-08-27-implement-routing-semantic-compatibility.md, .10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md, .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md

# Buoy Search subpackage final integration

> Aggregate review update: the initial validation narrative below records the pre-review checkpoint. `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md` subsequently failed that checkpoint. The final section records the complete repaired state and supersedes earlier counts/interface wording for acceptance.

## What was observed

The concern-oriented package layout is fully integrated with the three evidence-authority dependencies:

- eight implementation subpackages (`catalog`, `cli`, `evals`, `indexing`, `planning`, `relations`, `retrieval`, and `telemetry`) plus unchanged `data`;
- strict routing semantic compatibility schema v4 without active Python-byte receipts;
- immutable historical Buoy repo-eval v1 plus current v2 with pending baseline; and
- one packaged ranking-default authority with promotion-only validation.

The root package contains only `__init__.py`, `__main__.py`, `_version.py`, `config.py`, `local_paths.py`, `model_progress.py`, `source_url.py`, the eight implementation subpackages, and `data`. Exact per-subpackage file inventory matched `.10x/specs/buoy-search-subpackage-layout.md` plus the separately governed `retrieval/ranking_defaults.py`. Every subpackage initializer is empty; no forwarding export or compatibility shim exists.

No old moved-module import was found in tracked Python under `src`, `tests`, or `scripts`. Remaining old path strings are either deliberately preserved historical v1 evidence or synthetic retrieval-hit values that test path ranking and output behavior rather than Python imports.

## Changed surface

The integration diff consists of:

- moving the 41 flat implementation modules into the specified subpackages and updating source/test/script imports;
- updating package/console entrypoints and recursive package inventory;
- semantic routing schema-v4 source/artifact/tests;
- versioned repo-eval v1/v2 data, pending path-membership interface, validator, fixtures, docs, and tests;
- ranking-default authority, promotion validator, CI wiring, docs, and tests; and
- governing decisions/specs/tickets/evidence and repaired record references.

No compatibility module, new dependency, ranking-default value, routing threshold/model/selection change, evaluation judgment semantic change, benchmark result, provider operation, release, or publication was introduced.

## Validation procedure and results

### Source compilation and local contract validators

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m compileall -q src tests scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/c6_syntax_forecast.py validate
```

At the initial checkpoint these passed with the then-current interfaces. The repaired final checkpoint below replaces the permissive `base-unavailable` behavior with fail-closed PR/push comparison and distinguishes pending path membership from recorded corpus authority.

### Full tests

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q
```

Passed on the Python 3.13 project environment: `1176 passed, 57 warnings, 1232 subtests passed` in 87.05 seconds. Warnings were existing lxml `strip_cdata` deprecations.

CI-equivalent unittest discovery was then run sequentially under locked Python 3.13 and 3.11 environments:

```sh
uv sync --locked --python 3.13
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m unittest discover -s tests -p 'test_*.py' -q
uv sync --locked --python 3.11
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Both passed: `Ran 1176 tests`, `OK`. Python 3.13 took 103.431 seconds; Python 3.11 took 114.979 seconds. Existing best-effort plan-cleanup warnings and lxml deprecation warnings did not fail either run. The project environment was restored with `uv sync --locked --python 3.13`.

### CLI and import audits

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m buoy_search --help
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run buoy --help
```

Both passed and output compared byte-for-byte equal.

Exact import smoke imported all 37 moved implementation module paths. Searches for old flat `from`/`import` paths returned no matches. Explicit checks proved every old flat implementation file absent and all eight package initializers empty.

### Distribution and isolated installation

```sh
rm -rf dist
uv build
```

Passed, producing wheel and sdist. Wheel inventory contained 90 entries; sdist contained 173. Both contained all eight subpackages and required semantic-routing, v2-eval, v2-manifest, eval-version registry, and ranking-default data. The wheel contained no sampled old flat modules (`cli.py`, `retriever.py`, `telemetry.py`, or `catalog.py`).

The wheel was installed into a fresh Python 3.13 environment. Validation:

- imported all 37 moved modules;
- loaded routing schema 4 and exact semantic descriptor;
- reproduced unchanged repository and website ranking defaults;
- proved `python -m buoy_search --help` and installed `buoy --help` output parity; and
- passed installed explicit-namespace retrieval planning, preserving automatic-routing bypass.

The first custom isolated assertion attempted a nonexistent convenience method `RoutingSemanticCompatibility.as_json()` and failed with `AttributeError`. Inspection showed the production dataclass intentionally has no such API; the validation harness was corrected to use standard-library `dataclasses.asdict`, after which the complete isolated validation passed. This was a validation-script mistake, not a product failure or source change.

### Layout, shim, and hygiene audits

- Root and exact subpackage inventories passed.
- Old import searches passed with zero matches.
- Old flat file/shim existence checks passed with zero files.
- `git diff --check` passed.
- `git diff --cached --name-only` returned no output; no files are staged.

## What this supports

This evidence supports the package-layout acceptance criteria and aggregate integration behavior across routing semantic compatibility, versioned evals, and promotion gating. Tests, package builds, isolated imports, CLI behavior, package data, and shim/import audits are green without widening product behavior.

## Aggregate review repair and final validation

The failing aggregate review identified stale hosted clean-wheel imports plus six promotion/evaluation authority defects and stale routing test terminology. The promotion/evaluation repair is recorded in `.10x/evidence/2026-08-27-ranking-default-promotion-gate-review-repair.md`; the final integration repair completed the remaining hosted-workflow boundary.

### Hosted workflow repair

`.github/workflows/ci.yml` now imports `buoy_search.indexing.treatment_token_budget` and `buoy_search.evals.routing_quality`. `tests/test_ci_workflow.py` statically rejects every removed flat module in workflow Python imports, extracts and compiles each workflow Python heredoc, and dynamically imports every referenced `buoy_search` module. The exact clean-wheel heredoc was also extracted from the workflow and executed under the isolated wheel installation; tokenizer, three packaged canary hashes, 65-case suite digest, and schema-v4 calibration assertions all passed.

### Repaired evaluation and promotion interfaces

Final ranking validation reproduced 13 datasets, 90 composite identities, 369 judgments, immutable v1 identities, active v2 SHA-256 `691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae`, pending path-membership SHA-256 `4b7739515d15cd14b9cf9e374e5318c7fa9e7a3bb7e208f25878e6489751068b`, nine mappings, and `promotion_eligible=false`.

Promotion validation now requires a recorded content-addressed 13-repository basket, rejects pending/path-only Buoy versions, binds every dataset/corpus/recorded benchmark, requires exact baseline/candidate non-authority equality, accepts only bounded safe retrieval/model fields, and fails closed without PR merge-base or push previous-SHA authority. Simulated pull-request merge-base and push exact-previous-SHA introduction both passed against `HEAD`; a no-event/no-base invocation failed with the required error.

### Exact Python 3.11 and 3.13 CI validation

For each locked runtime, the following exact sequence passed:

```sh
uv sync --locked --python <3.11|3.13>
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
BUOY_RANKING_AUTHORITY_INTRODUCTION=true \
BUOY_RANKING_EVENT_NAME=pull_request \
BUOY_RANKING_PR_BASE_REF=$(git rev-parse HEAD) \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/c6_syntax_forecast.py validate
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Python 3.11: `Ran 1186 tests in 108.749s`, `OK`. Python 3.13: `Ran 1186 tests in 114.827s`, `OK`. Existing best-effort temporary plan cleanup and lxml deprecation warnings remained non-failing.

Focused repaired coverage passed: `53 passed, 57 subtests passed` across workflow, promotion, ranking-contract, and retriever tests.

### Final source, distribution, and isolated validation

- `compileall`, source/module CLI help parity, all 38 new-module imports, exact root/subpackage inventory, empty initializer/no-shim checks, old-import searches, and old-flat-file absence passed.
- `uv build` produced a 90-entry wheel and 174-entry sdist with all eight subpackages, semantic routing artifact, v2 dataset, v2 path-membership file, evaluation registry, and ranking-default authority; sampled removed flat modules were absent.
- Fresh Python 3.13 wheel installation passed CLI/module parity, all 38 imports, semantic schema/descriptor equality, ranking-default parity, the exact hosted workflow Python smoke, and explicit-namespace bypass.
- `git diff --check` passed and `git diff --cached --name-only` remained empty.

## Parent-observed closure validation

After the final independent PASS review and ticket reconciliation, the parent directly reran:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
BUOY_RANKING_AUTHORITY_INTRODUCTION=true \
BUOY_RANKING_EVENT_NAME=pull_request \
BUOY_RANKING_PR_BASE_REF=$(git rev-parse HEAD) \
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q
```

The ranking contract reproduced 13 datasets, 90 identities, 369 judgments, exact historical/current hashes, pending and promotion-ineligible Buoy v2, and nine path mappings. Promotion validation classified the authority introduction against the exact base and reported zero registered production baskets. The complete suite passed with `1191 passed, 57 warnings, 1292 subtests passed`. `git diff --check` passed and no files were staged.

## Limits and residual risk

- The prior aggregate review verdict remains `fail` historically; a fresh independent reviewer must assess this repair before closure. All tickets remain active and none was marked done.
- GitHub-hosted Actions was not run; both event modes, fail-closed missing-base behavior, exact workflow heredoc, and CI commands were exercised locally.
- V2 repo-eval intentionally remains `baseline_status=pending`, uses only path-membership authority, is `promotion_eligible=false`, and cannot authorize ranking promotion.
- No real promotion basket/benchmark, live retrieval, product model construction, provider/credential access, namespace/catalog mutation, release, publication, or deployment occurred. Isolated wheel installation fetched ordinary declared dependencies only.

## Basket-registry integration checkpoint

The recorded basket-registry repair in `.10x/evidence/2026-08-27-ranking-promotion-basket-registry-review-repair.md` is now integrated into the aggregate package, CI, and hosted clean-wheel boundary.

Production packages `src/buoy_search/data/repo_ranking_promotion_baskets.json` with exact value:

```json
{"baskets": [], "schema_version": 1}
```

This truthfully asserts that no current 13-repository promotion basket or benchmark exists. `scripts/validate_ranking_promotion.py` validates the registry on every invocation and reported `registered_baskets=0` for pull-request merge-base and push previous-SHA simulations. Any future promotion artifact must reference a registry entry whose 13 datasets, corpus manifests, and recorded benchmarks resolve to actual hashed repository files; current pending Buoy v2 remains ineligible.

Hosted clean-wheel Python now reads the packaged registry through `importlib.resources` and requires the exact zero-basket schema. `tests/test_ci_workflow.py` adds source-package resource coverage while continuing to compile/import workflow heredocs and reject removed flat imports. The exact workflow heredoc passed under the isolated wheel.

### Final exact validation after registry integration

For both locked Python 3.11 and 3.13, compilation, ranking-contract validation, promotion validation, C6 validation, and full unittest discovery passed. Each promotion result included:

```json
{"promotion_basket_registry": {"path": "src/buoy_search/data/repo_ranking_promotion_baskets.json", "registered_baskets": 0}}
```

- Python 3.11: `Ran 1189 tests in 112.135s`, `OK`.
- Python 3.13: `Ran 1189 tests in 106.260s`, `OK`.
- Focused workflow/promotion/ranking/retriever coverage: `56 passed, 57 subtests passed`.
- PR merge-base and push exact-previous-SHA introduction checks passed; missing comparison context failed closed.
- CLI parity, all 38 imports, exact layout, old-import/flat-file/no-shim audits passed.
- Wheel: 91 entries; sdist: 175 entries. Both contained and parsed the exact zero-basket registry.
- Fresh Python 3.13 installation passed all 38 imports, semantic routing/default parity, exact hosted workflow smoke including registry assertion, CLI parity, and explicit-namespace bypass.
- `git diff --check` passed; no files are staged.

No external benchmark, retrieval, product-model, provider, credential, namespace/catalog, release, publication, or deployment operation occurred. Fresh independent review remains required; no ticket is marked done.

## Registered dataset/corpus semantic-validation checkpoint

The strict provenance repair recorded in `.10x/evidence/2026-08-27-promotion-basket-provenance-semantic-validation-repair.md` is integrated into the aggregate package and CI validation.

For any future nonempty basket, raw hashes alone are no longer sufficient. The promotion registry validator now requires:

- exact dataset schema/ID/version/repository identity, nonempty unique cases, bounded questions, strict judgments, canonical paths, grades in `[0,3]`, and judgment membership in the corpus inventory;
- exact corpus schema/repository/full Git-commit source identity, nonempty sorted unique document inventory, canonical paths, non-placeholder content hashes, and matching canonical inventory hash/count on the basket member; and
- recorded benchmark repository/source/dataset/corpus identities and strict input/result linkage.

Mutation tests replace dataset/corpus files with semantically invalid content, consistently regenerate raw file hashes, member identities, basket hash, registry bytes, and artifact reference, and still fail. Covered mutations include unrelated JSON, identity/schema drift, empty data, invalid grade, absent judgment path, source revision drift, duplicate/traversal document paths, placeholder content hashes, and inventory mismatch.

Production remains exact `{"baskets": [], "schema_version": 1}` in source, wheel, sdist, and isolated installation; no current basket or benchmark is claimed. Source CI promotion validation continued to report `registered_baskets=0` for PR and push simulations, and hosted clean-wheel Python asserted the packaged empty registry.

### Final exact validation after semantic integration

- Python 3.11: compileall plus ranking, promotion, and C6 validators passed; `Ran 1191 tests in 108.154s`, `OK`.
- Python 3.13: the same exact sequence passed; `Ran 1191 tests in 104.324s`, `OK`.
- Focused workflow/promotion/ranking/retriever coverage: `58 passed, 73 subtests passed`.
- PR merge-base and push exact-previous-SHA comparisons passed; missing context failed closed.
- CLI parity, all 38 imports, exact layout, old-import/flat-file/no-shim audits passed.
- Wheel: 91 entries; sdist: 175 entries. Both contained the truthful empty registry.
- Fresh Python 3.13 install passed all 38 imports, semantic routing/default parity, exact workflow/registry smoke, CLI parity, and explicit-namespace bypass.
- `git diff --check` passed and no files are staged.

No external basket/dataset/corpus/benchmark generation, retrieval, product-model, provider, credential, namespace/catalog, release, publication, or deployment operation occurred. Fresh independent review remains required; no ticket is marked done.
