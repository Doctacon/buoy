Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Relates-To: .10x/tickets/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md, .10x/tickets/2026-07-19-buoy-v0-4-compatibility-removal-plan.md, .10x/specs/buoy-v0-4-internal-record-artifact-exclusion.md

# Buoy 0.4 Internal Record Artifact Exclusion Evidence

## Controlled baseline observation

The controlled baseline build ran from implementation base `5683eb6c00eb0aefe8e0a2c1047215b78ad718b4` plus exactly the bounded `pyproject.toml` exclusion and focused `tests/test_release_automation.py` assertion. It used macOS arm64, CPython 3.13.0, uv 0.11.7, a dedicated disposable build environment, `SOURCE_DATE_EPOCH=1784506710`, fresh `/tmp/buoy-v040-packaging-control/before`, and this exact frozen build environment:

```text
hatchling==1.31.0
packaging==26.2
pathspec==1.1.1
pluggy==1.6.0
trove-classifiers==2026.6.1.19
```

Command:

```text
SOURCE_DATE_EPOCH=1784506710 PYTHONDONTWRITEBYTECODE=1 uv build --no-build-isolation --python /tmp/buoy-v040-packaging-control/build-env/bin/python --out-dir /tmp/buoy-v040-packaging-control/before --no-create-gitignore
```

Artifacts and baseline SHA-256 digests:

```text
1a5cdb4a303eb0c4f7e42b335138a43f4b1098a8f8b2189ded2d3d9fc8e00d30  /tmp/buoy-v040-packaging-control/before/buoy_search-0.4.0-py3-none-any.whl
bd7d2f80e06e8f6ae2c99a5b81f9ae709d5af5e71c0659cf5333f281e46404b1  /tmp/buoy-v040-packaging-control/before/buoy_search-0.4.0.tar.gz
```

The baseline wheel has 45 members and zero `.10x` members. The baseline sdist has one distribution root, `buoy_search-0.4.0`, and 95 members; after removing that root, it has zero `.10x` members.

### Complete baseline wheel inventory

```text
buoy_search-0.4.0.dist-info/METADATA
buoy_search-0.4.0.dist-info/RECORD
buoy_search-0.4.0.dist-info/WHEEL
buoy_search-0.4.0.dist-info/entry_points.txt
buoy_search-0.4.0.dist-info/licenses/LICENSE
buoy_search/__init__.py
buoy_search/__main__.py
buoy_search/applied_state.py
buoy_search/apply.py
buoy_search/autoresearch.py
buoy_search/catalog.py
buoy_search/catalog_cli.py
buoy_search/catalog_pending.py
buoy_search/chunker.py
buoy_search/cli.py
buoy_search/config.py
buoy_search/crawler.py
buoy_search/data/black_repo_search_seed_evals.json
buoy_search/data/buoy_search_repo_search_seed_evals.json
buoy_search/data/click_repo_search_seed_evals.json
buoy_search/data/django_repo_search_seed_evals.json
buoy_search/data/flask_repo_search_seed_evals.json
buoy_search/data/httpx_repo_search_seed_evals.json
buoy_search/data/mkdocs_repo_search_seed_evals.json
buoy_search/data/pi_site_search_seed_evals.json
buoy_search/data/pydantic_repo_search_seed_evals.json
buoy_search/data/pytest_repo_search_seed_evals.json
buoy_search/data/requests_repo_search_seed_evals.json
buoy_search/data/rich_repo_search_seed_evals.json
buoy_search/data/ruff_repo_search_seed_evals.json
buoy_search/data/ruff_site_search_seed_evals.json
buoy_search/data/scrapling_retrieval_smoke_evals.json
buoy_search/data/sqlmesh_site_search_seed_evals.json
buoy_search/data/turbopuffer_site_search_seed_evals.json
buoy_search/data/typer_repo_search_seed_evals.json
buoy_search/data/typer_site_search_seed_evals.json
buoy_search/evals.py
buoy_search/github_repo.py
buoy_search/namespaces.py
buoy_search/plan_artifacts.py
buoy_search/plan_cleanup.py
buoy_search/plan_diff.py
buoy_search/remote_catalog.py
buoy_search/retriever.py
buoy_search/routing.py
```

### Complete baseline sdist raw inventory

```text
buoy_search-0.4.0/.github/workflows/ci.yml
buoy_search-0.4.0/.github/workflows/release.yml
buoy_search-0.4.0/.gitignore
buoy_search-0.4.0/.pi/skills/turbopuffer-site-rag/SKILL.md
buoy_search-0.4.0/.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md
buoy_search-0.4.0/AGENTS.md
buoy_search-0.4.0/CHANGELOG.md
buoy_search-0.4.0/CONTRIBUTING.md
buoy_search-0.4.0/LICENSE
buoy_search-0.4.0/PKG-INFO
buoy_search-0.4.0/README.md
buoy_search-0.4.0/SECURITY.md
buoy_search-0.4.0/autoresearch/experiments/repo-search-fixture-baseline.json
buoy_search-0.4.0/autoresearch/experiments/repo-search-live-baseline.json
buoy_search-0.4.0/autoresearch/program.md
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/evaluate.py
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/namespace_cards.json
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/plan.json
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/report.md
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/result.json
buoy_search-0.4.0/docs/catalog.md
buoy_search-0.4.0/docs/evaluation.md
buoy_search-0.4.0/docs/indexing.md
buoy_search-0.4.0/docs/migrating-to-buoy.md
buoy_search-0.4.0/docs/releasing.md
buoy_search-0.4.0/docs/retrieval.md
buoy_search-0.4.0/images/buoy.svg
buoy_search-0.4.0/pyproject.toml
buoy_search-0.4.0/scripts/release_checks.py
buoy_search-0.4.0/src/buoy_search/__init__.py
buoy_search-0.4.0/src/buoy_search/__main__.py
buoy_search-0.4.0/src/buoy_search/applied_state.py
buoy_search-0.4.0/src/buoy_search/apply.py
buoy_search-0.4.0/src/buoy_search/autoresearch.py
buoy_search-0.4.0/src/buoy_search/catalog.py
buoy_search-0.4.0/src/buoy_search/catalog_cli.py
buoy_search-0.4.0/src/buoy_search/catalog_pending.py
buoy_search-0.4.0/src/buoy_search/chunker.py
buoy_search-0.4.0/src/buoy_search/cli.py
buoy_search-0.4.0/src/buoy_search/config.py
buoy_search-0.4.0/src/buoy_search/crawler.py
buoy_search-0.4.0/src/buoy_search/data/black_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/buoy_search_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/click_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/django_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/flask_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/httpx_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/mkdocs_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pi_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pydantic_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pytest_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/requests_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/rich_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/ruff_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/ruff_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/scrapling_retrieval_smoke_evals.json
buoy_search-0.4.0/src/buoy_search/data/sqlmesh_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/turbopuffer_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/typer_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/typer_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/evals.py
buoy_search-0.4.0/src/buoy_search/github_repo.py
buoy_search-0.4.0/src/buoy_search/namespaces.py
buoy_search-0.4.0/src/buoy_search/plan_artifacts.py
buoy_search-0.4.0/src/buoy_search/plan_cleanup.py
buoy_search-0.4.0/src/buoy_search/plan_diff.py
buoy_search-0.4.0/src/buoy_search/remote_catalog.py
buoy_search-0.4.0/src/buoy_search/retriever.py
buoy_search-0.4.0/src/buoy_search/routing.py
buoy_search-0.4.0/tests/test_applied_state.py
buoy_search-0.4.0/tests/test_apply_cli.py
buoy_search-0.4.0/tests/test_automatic_routing.py
buoy_search-0.4.0/tests/test_autoresearch.py
buoy_search-0.4.0/tests/test_catalog.py
buoy_search-0.4.0/tests/test_catalog_cli.py
buoy_search-0.4.0/tests/test_catalog_pending.py
buoy_search-0.4.0/tests/test_chunker.py
buoy_search-0.4.0/tests/test_cli.py
buoy_search-0.4.0/tests/test_config.py
buoy_search-0.4.0/tests/test_crawler.py
buoy_search-0.4.0/tests/test_crawler_exact_host.py
buoy_search-0.4.0/tests/test_cutover_isolation.py
buoy_search-0.4.0/tests/test_environment_alias_removal.py
buoy_search-0.4.0/tests/test_evals.py
buoy_search-0.4.0/tests/test_github_repo.py
buoy_search-0.4.0/tests/test_multi_namespace_retrieval.py
buoy_search-0.4.0/tests/test_namespaces.py
buoy_search-0.4.0/tests/test_plan_artifacts.py
buoy_search-0.4.0/tests/test_plan_cleanup.py
buoy_search-0.4.0/tests/test_plan_diff.py
buoy_search-0.4.0/tests/test_release_automation.py
buoy_search-0.4.0/tests/test_remote_catalog.py
buoy_search-0.4.0/tests/test_retriever.py
buoy_search-0.4.0/tests/test_semantic_routing_representative.py
buoy_search-0.4.0/uv.lock
```

### Complete baseline sdist normalized inventory

```text
.github/workflows/ci.yml
.github/workflows/release.yml
.gitignore
.pi/skills/turbopuffer-site-rag/SKILL.md
.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md
AGENTS.md
CHANGELOG.md
CONTRIBUTING.md
LICENSE
PKG-INFO
README.md
SECURITY.md
autoresearch/experiments/repo-search-fixture-baseline.json
autoresearch/experiments/repo-search-live-baseline.json
autoresearch/program.md
autoresearch/runs/semantic-routing-representative-20260715/evaluate.py
autoresearch/runs/semantic-routing-representative-20260715/namespace_cards.json
autoresearch/runs/semantic-routing-representative-20260715/plan.json
autoresearch/runs/semantic-routing-representative-20260715/report.md
autoresearch/runs/semantic-routing-representative-20260715/result.json
docs/catalog.md
docs/evaluation.md
docs/indexing.md
docs/migrating-to-buoy.md
docs/releasing.md
docs/retrieval.md
images/buoy.svg
pyproject.toml
scripts/release_checks.py
src/buoy_search/__init__.py
src/buoy_search/__main__.py
src/buoy_search/applied_state.py
src/buoy_search/apply.py
src/buoy_search/autoresearch.py
src/buoy_search/catalog.py
src/buoy_search/catalog_cli.py
src/buoy_search/catalog_pending.py
src/buoy_search/chunker.py
src/buoy_search/cli.py
src/buoy_search/config.py
src/buoy_search/crawler.py
src/buoy_search/data/black_repo_search_seed_evals.json
src/buoy_search/data/buoy_search_repo_search_seed_evals.json
src/buoy_search/data/click_repo_search_seed_evals.json
src/buoy_search/data/django_repo_search_seed_evals.json
src/buoy_search/data/flask_repo_search_seed_evals.json
src/buoy_search/data/httpx_repo_search_seed_evals.json
src/buoy_search/data/mkdocs_repo_search_seed_evals.json
src/buoy_search/data/pi_site_search_seed_evals.json
src/buoy_search/data/pydantic_repo_search_seed_evals.json
src/buoy_search/data/pytest_repo_search_seed_evals.json
src/buoy_search/data/requests_repo_search_seed_evals.json
src/buoy_search/data/rich_repo_search_seed_evals.json
src/buoy_search/data/ruff_repo_search_seed_evals.json
src/buoy_search/data/ruff_site_search_seed_evals.json
src/buoy_search/data/scrapling_retrieval_smoke_evals.json
src/buoy_search/data/sqlmesh_site_search_seed_evals.json
src/buoy_search/data/turbopuffer_site_search_seed_evals.json
src/buoy_search/data/typer_repo_search_seed_evals.json
src/buoy_search/data/typer_site_search_seed_evals.json
src/buoy_search/evals.py
src/buoy_search/github_repo.py
src/buoy_search/namespaces.py
src/buoy_search/plan_artifacts.py
src/buoy_search/plan_cleanup.py
src/buoy_search/plan_diff.py
src/buoy_search/remote_catalog.py
src/buoy_search/retriever.py
src/buoy_search/routing.py
tests/test_applied_state.py
tests/test_apply_cli.py
tests/test_automatic_routing.py
tests/test_autoresearch.py
tests/test_catalog.py
tests/test_catalog_cli.py
tests/test_catalog_pending.py
tests/test_chunker.py
tests/test_cli.py
tests/test_config.py
tests/test_crawler.py
tests/test_crawler_exact_host.py
tests/test_cutover_isolation.py
tests/test_environment_alias_removal.py
tests/test_evals.py
tests/test_github_repo.py
tests/test_multi_namespace_retrieval.py
tests/test_namespaces.py
tests/test_plan_artifacts.py
tests/test_plan_cleanup.py
tests/test_plan_diff.py
tests/test_release_automation.py
tests/test_remote_catalog.py
tests/test_retriever.py
tests/test_semantic_routing_representative.py
uv.lock
```

## Limits at record creation

This record was created only after the baseline build so that staging this single `.10x/**` record could be the complete source-tree delta for the controlled comparison. Aggregate tests, install/upgrade observations, exact candidate inspection, hosted checks, and the final comparison are recorded after they are observed.


## Controlled record-only comparison

Immediately after the baseline, this evidence file was created and staged. The before status was exactly:

```text
 M pyproject.toml
 M tests/test_release_automation.py
```

The comparison status was exactly:

```text
A  .10x/evidence/2026-07-19-exclude-internal-records-from-buoy-v0-4-artifacts.md
 M pyproject.toml
 M tests/test_release_automation.py
```

A programmatic assertion removed the one named evidence-record status line and proved the remaining ordered status exactly equaled the baseline status. No file outside `.10x/**` changed between builds. Staging ensured the newly added record was visible to VCS-aware file selection. The second build used the identical build environment, platform, interpreter, command, fixed epoch, and a fresh `/tmp/buoy-v040-packaging-control/after` output directory.

```text
SOURCE_DATE_EPOCH=1784506710 PYTHONDONTWRITEBYTECODE=1 uv build --no-build-isolation --python /tmp/buoy-v040-packaging-control/build-env/bin/python --out-dir /tmp/buoy-v040-packaging-control/after --no-create-gitignore
```

After SHA-256 digests:

```text
1a5cdb4a303eb0c4f7e42b335138a43f4b1098a8f8b2189ded2d3d9fc8e00d30  /tmp/buoy-v040-packaging-control/after/buoy_search-0.4.0-py3-none-any.whl
bd7d2f80e06e8f6ae2c99a5b81f9ae709d5af5e71c0659cf5333f281e46404b1  /tmp/buoy-v040-packaging-control/after/buoy_search-0.4.0.tar.gz
```

`cmp` returned 0 for each corresponding archive. The wheel bytes are identical, the sdist bytes are identical, and before/after digests match exactly:

- wheel before/after: `1a5cdb4a303eb0c4f7e42b335138a43f4b1098a8f8b2189ded2d3d9fc8e00d30`;
- sdist before/after: `bd7d2f80e06e8f6ae2c99a5b81f9ae709d5af5e71c0659cf5333f281e46404b1`.

Machine comparison also proved the complete before/after wheel, raw sdist, and normalized sdist inventories identical. Both builds had 45 wheel members, 95 sdist members, and zero `.10x` hits after the required sdist root stripping.

### Complete comparison wheel inventory

```text
buoy_search-0.4.0.dist-info/METADATA
buoy_search-0.4.0.dist-info/RECORD
buoy_search-0.4.0.dist-info/WHEEL
buoy_search-0.4.0.dist-info/entry_points.txt
buoy_search-0.4.0.dist-info/licenses/LICENSE
buoy_search/__init__.py
buoy_search/__main__.py
buoy_search/applied_state.py
buoy_search/apply.py
buoy_search/autoresearch.py
buoy_search/catalog.py
buoy_search/catalog_cli.py
buoy_search/catalog_pending.py
buoy_search/chunker.py
buoy_search/cli.py
buoy_search/config.py
buoy_search/crawler.py
buoy_search/data/black_repo_search_seed_evals.json
buoy_search/data/buoy_search_repo_search_seed_evals.json
buoy_search/data/click_repo_search_seed_evals.json
buoy_search/data/django_repo_search_seed_evals.json
buoy_search/data/flask_repo_search_seed_evals.json
buoy_search/data/httpx_repo_search_seed_evals.json
buoy_search/data/mkdocs_repo_search_seed_evals.json
buoy_search/data/pi_site_search_seed_evals.json
buoy_search/data/pydantic_repo_search_seed_evals.json
buoy_search/data/pytest_repo_search_seed_evals.json
buoy_search/data/requests_repo_search_seed_evals.json
buoy_search/data/rich_repo_search_seed_evals.json
buoy_search/data/ruff_repo_search_seed_evals.json
buoy_search/data/ruff_site_search_seed_evals.json
buoy_search/data/scrapling_retrieval_smoke_evals.json
buoy_search/data/sqlmesh_site_search_seed_evals.json
buoy_search/data/turbopuffer_site_search_seed_evals.json
buoy_search/data/typer_repo_search_seed_evals.json
buoy_search/data/typer_site_search_seed_evals.json
buoy_search/evals.py
buoy_search/github_repo.py
buoy_search/namespaces.py
buoy_search/plan_artifacts.py
buoy_search/plan_cleanup.py
buoy_search/plan_diff.py
buoy_search/remote_catalog.py
buoy_search/retriever.py
buoy_search/routing.py
```

### Complete comparison sdist raw inventory

```text
buoy_search-0.4.0/.github/workflows/ci.yml
buoy_search-0.4.0/.github/workflows/release.yml
buoy_search-0.4.0/.gitignore
buoy_search-0.4.0/.pi/skills/turbopuffer-site-rag/SKILL.md
buoy_search-0.4.0/.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md
buoy_search-0.4.0/AGENTS.md
buoy_search-0.4.0/CHANGELOG.md
buoy_search-0.4.0/CONTRIBUTING.md
buoy_search-0.4.0/LICENSE
buoy_search-0.4.0/PKG-INFO
buoy_search-0.4.0/README.md
buoy_search-0.4.0/SECURITY.md
buoy_search-0.4.0/autoresearch/experiments/repo-search-fixture-baseline.json
buoy_search-0.4.0/autoresearch/experiments/repo-search-live-baseline.json
buoy_search-0.4.0/autoresearch/program.md
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/evaluate.py
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/namespace_cards.json
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/plan.json
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/report.md
buoy_search-0.4.0/autoresearch/runs/semantic-routing-representative-20260715/result.json
buoy_search-0.4.0/docs/catalog.md
buoy_search-0.4.0/docs/evaluation.md
buoy_search-0.4.0/docs/indexing.md
buoy_search-0.4.0/docs/migrating-to-buoy.md
buoy_search-0.4.0/docs/releasing.md
buoy_search-0.4.0/docs/retrieval.md
buoy_search-0.4.0/images/buoy.svg
buoy_search-0.4.0/pyproject.toml
buoy_search-0.4.0/scripts/release_checks.py
buoy_search-0.4.0/src/buoy_search/__init__.py
buoy_search-0.4.0/src/buoy_search/__main__.py
buoy_search-0.4.0/src/buoy_search/applied_state.py
buoy_search-0.4.0/src/buoy_search/apply.py
buoy_search-0.4.0/src/buoy_search/autoresearch.py
buoy_search-0.4.0/src/buoy_search/catalog.py
buoy_search-0.4.0/src/buoy_search/catalog_cli.py
buoy_search-0.4.0/src/buoy_search/catalog_pending.py
buoy_search-0.4.0/src/buoy_search/chunker.py
buoy_search-0.4.0/src/buoy_search/cli.py
buoy_search-0.4.0/src/buoy_search/config.py
buoy_search-0.4.0/src/buoy_search/crawler.py
buoy_search-0.4.0/src/buoy_search/data/black_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/buoy_search_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/click_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/django_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/flask_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/httpx_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/mkdocs_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pi_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pydantic_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/pytest_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/requests_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/rich_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/ruff_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/ruff_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/scrapling_retrieval_smoke_evals.json
buoy_search-0.4.0/src/buoy_search/data/sqlmesh_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/turbopuffer_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/typer_repo_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/data/typer_site_search_seed_evals.json
buoy_search-0.4.0/src/buoy_search/evals.py
buoy_search-0.4.0/src/buoy_search/github_repo.py
buoy_search-0.4.0/src/buoy_search/namespaces.py
buoy_search-0.4.0/src/buoy_search/plan_artifacts.py
buoy_search-0.4.0/src/buoy_search/plan_cleanup.py
buoy_search-0.4.0/src/buoy_search/plan_diff.py
buoy_search-0.4.0/src/buoy_search/remote_catalog.py
buoy_search-0.4.0/src/buoy_search/retriever.py
buoy_search-0.4.0/src/buoy_search/routing.py
buoy_search-0.4.0/tests/test_applied_state.py
buoy_search-0.4.0/tests/test_apply_cli.py
buoy_search-0.4.0/tests/test_automatic_routing.py
buoy_search-0.4.0/tests/test_autoresearch.py
buoy_search-0.4.0/tests/test_catalog.py
buoy_search-0.4.0/tests/test_catalog_cli.py
buoy_search-0.4.0/tests/test_catalog_pending.py
buoy_search-0.4.0/tests/test_chunker.py
buoy_search-0.4.0/tests/test_cli.py
buoy_search-0.4.0/tests/test_config.py
buoy_search-0.4.0/tests/test_crawler.py
buoy_search-0.4.0/tests/test_crawler_exact_host.py
buoy_search-0.4.0/tests/test_cutover_isolation.py
buoy_search-0.4.0/tests/test_environment_alias_removal.py
buoy_search-0.4.0/tests/test_evals.py
buoy_search-0.4.0/tests/test_github_repo.py
buoy_search-0.4.0/tests/test_multi_namespace_retrieval.py
buoy_search-0.4.0/tests/test_namespaces.py
buoy_search-0.4.0/tests/test_plan_artifacts.py
buoy_search-0.4.0/tests/test_plan_cleanup.py
buoy_search-0.4.0/tests/test_plan_diff.py
buoy_search-0.4.0/tests/test_release_automation.py
buoy_search-0.4.0/tests/test_remote_catalog.py
buoy_search-0.4.0/tests/test_retriever.py
buoy_search-0.4.0/tests/test_semantic_routing_representative.py
buoy_search-0.4.0/uv.lock
```

### Complete comparison sdist normalized inventory

```text
.github/workflows/ci.yml
.github/workflows/release.yml
.gitignore
.pi/skills/turbopuffer-site-rag/SKILL.md
.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md
AGENTS.md
CHANGELOG.md
CONTRIBUTING.md
LICENSE
PKG-INFO
README.md
SECURITY.md
autoresearch/experiments/repo-search-fixture-baseline.json
autoresearch/experiments/repo-search-live-baseline.json
autoresearch/program.md
autoresearch/runs/semantic-routing-representative-20260715/evaluate.py
autoresearch/runs/semantic-routing-representative-20260715/namespace_cards.json
autoresearch/runs/semantic-routing-representative-20260715/plan.json
autoresearch/runs/semantic-routing-representative-20260715/report.md
autoresearch/runs/semantic-routing-representative-20260715/result.json
docs/catalog.md
docs/evaluation.md
docs/indexing.md
docs/migrating-to-buoy.md
docs/releasing.md
docs/retrieval.md
images/buoy.svg
pyproject.toml
scripts/release_checks.py
src/buoy_search/__init__.py
src/buoy_search/__main__.py
src/buoy_search/applied_state.py
src/buoy_search/apply.py
src/buoy_search/autoresearch.py
src/buoy_search/catalog.py
src/buoy_search/catalog_cli.py
src/buoy_search/catalog_pending.py
src/buoy_search/chunker.py
src/buoy_search/cli.py
src/buoy_search/config.py
src/buoy_search/crawler.py
src/buoy_search/data/black_repo_search_seed_evals.json
src/buoy_search/data/buoy_search_repo_search_seed_evals.json
src/buoy_search/data/click_repo_search_seed_evals.json
src/buoy_search/data/django_repo_search_seed_evals.json
src/buoy_search/data/flask_repo_search_seed_evals.json
src/buoy_search/data/httpx_repo_search_seed_evals.json
src/buoy_search/data/mkdocs_repo_search_seed_evals.json
src/buoy_search/data/pi_site_search_seed_evals.json
src/buoy_search/data/pydantic_repo_search_seed_evals.json
src/buoy_search/data/pytest_repo_search_seed_evals.json
src/buoy_search/data/requests_repo_search_seed_evals.json
src/buoy_search/data/rich_repo_search_seed_evals.json
src/buoy_search/data/ruff_repo_search_seed_evals.json
src/buoy_search/data/ruff_site_search_seed_evals.json
src/buoy_search/data/scrapling_retrieval_smoke_evals.json
src/buoy_search/data/sqlmesh_site_search_seed_evals.json
src/buoy_search/data/turbopuffer_site_search_seed_evals.json
src/buoy_search/data/typer_repo_search_seed_evals.json
src/buoy_search/data/typer_site_search_seed_evals.json
src/buoy_search/evals.py
src/buoy_search/github_repo.py
src/buoy_search/namespaces.py
src/buoy_search/plan_artifacts.py
src/buoy_search/plan_cleanup.py
src/buoy_search/plan_diff.py
src/buoy_search/remote_catalog.py
src/buoy_search/retriever.py
src/buoy_search/routing.py
tests/test_applied_state.py
tests/test_apply_cli.py
tests/test_automatic_routing.py
tests/test_autoresearch.py
tests/test_catalog.py
tests/test_catalog_cli.py
tests/test_catalog_pending.py
tests/test_chunker.py
tests/test_cli.py
tests/test_config.py
tests/test_crawler.py
tests/test_crawler_exact_host.py
tests/test_cutover_isolation.py
tests/test_environment_alias_removal.py
tests/test_evals.py
tests/test_github_repo.py
tests/test_multi_namespace_retrieval.py
tests/test_namespaces.py
tests/test_plan_artifacts.py
tests/test_plan_cleanup.py
tests/test_plan_diff.py
tests/test_release_automation.py
tests/test_remote_catalog.py
tests/test_retriever.py
tests/test_semantic_routing_representative.py
uv.lock
```

## Implementation and scope inspection

The only build configuration change is:

```diff
+[tool.hatch.build]
+exclude = ["/.10x/**"]
```

The leading slash anchors the one exclusion to repository root; the only pattern covers `.10x` descendants. The focused assertion reads `pyproject.toml` and requires the exclusion list to equal exactly `["/.10x/**"]`.

Before ticket-record progress updates, changed paths were exactly this new evidence record, `pyproject.toml`, and `tests/test_release_automation.py`. Diff assertions from starting head `5683eb6` proved no change under `src/`, `src/buoy_search/data/`, `README.md`, `CHANGELOG.md`, or `docs/`, and no test change outside `tests/test_release_automation.py`. Repository `.10x/**` remains present; this record itself demonstrates that the directory remains writable and preserved.

## Test and exact gate validation

- `UV_PROJECT_ENVIRONMENT=/tmp/buoy-v040-packaging-py311 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q`: passed 422 tests in 52.468 seconds on CPython 3.11.5.
- `UV_PROJECT_ENVIRONMENT=/tmp/buoy-v040-packaging-py313 PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q`: passed 422 tests in 51.163 seconds on CPython 3.13.0.
- `PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python -m unittest tests.test_config tests.test_environment_alias_removal tests.test_cli tests.test_autoresearch tests.test_release_automation -v`: passed all 75 focused tests in 39.015 seconds, including the complete exact environment presence/value/order/stream/exit matrix, every real-handler non-dispatch sentinel, autoresearch pre-read/pre-output rejection, parser/help/version precedence, current-variable retention, focused packaging assertion, and release checks.
- `uv lock --check`, `git diff --check`, `scripts/release_checks.py tag --tag v0.4.0`, and `scripts/release_checks.py assets --dist /tmp/buoy-v040-packaging-control/after` passed.

The full suites emitted the same two mocked temporary plan-artifact cleanup advisories documented by the prior aggregate evidence and passed. Test state roots and environments were disposable `/tmp` or framework temporary directories. No live service was invoked.

The normally installed wheel also rejected a valid `crawl --base-url https://example.com --json` invocation with the removed model name present. It returned 2, emitted zero stdout bytes, emitted exactly this one newline-terminated stderr line, and left a fresh temporary HOME empty:

```text
Removed environment variable is not supported in Buoy 0.4.0: TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL
```

## Clean candidate-wheel installation

A fresh CPython 3.13 environment at `/tmp/buoy-v040-packaging-clean/venv` normally installed the comparison wheel. Installed metadata reported version 0.4.0 and exactly `('console_scripts', 'buoy', 'buoy_search.cli:main')`. The complete launcher-directory inventory contained `buoy` and no `turbo-search`; explicit existence/absence assertions passed. `buoy --version` printed `buoy 0.4.0`; `buoy --help` and `python -m buoy_search --help` began `usage: buoy [-h] [--version]`.

```text
version=0.4.0
entry_points=[('console_scripts', 'buoy', 'buoy_search.cli:main')]
launcher-directory:
/tmp/buoy-v040-packaging-clean/venv/bin/activate
/tmp/buoy-v040-packaging-clean/venv/bin/activate.bat
/tmp/buoy-v040-packaging-clean/venv/bin/activate.csh
/tmp/buoy-v040-packaging-clean/venv/bin/activate.fish
/tmp/buoy-v040-packaging-clean/venv/bin/activate.nu
/tmp/buoy-v040-packaging-clean/venv/bin/activate.ps1
/tmp/buoy-v040-packaging-clean/venv/bin/activate_this.py
/tmp/buoy-v040-packaging-clean/venv/bin/buoy
/tmp/buoy-v040-packaging-clean/venv/bin/cffi-gen-src
/tmp/buoy-v040-packaging-clean/venv/bin/curl-cffi
/tmp/buoy-v040-packaging-clean/venv/bin/deactivate.bat
/tmp/buoy-v040-packaging-clean/venv/bin/distro
/tmp/buoy-v040-packaging-clean/venv/bin/dotenv
/tmp/buoy-v040-packaging-clean/venv/bin/dumppdf.py
/tmp/buoy-v040-packaging-clean/venv/bin/f2py
/tmp/buoy-v040-packaging-clean/venv/bin/hf
/tmp/buoy-v040-packaging-clean/venv/bin/httpx
/tmp/buoy-v040-packaging-clean/venv/bin/huggingface-cli
/tmp/buoy-v040-packaging-clean/venv/bin/idna
/tmp/buoy-v040-packaging-clean/venv/bin/isympy
/tmp/buoy-v040-packaging-clean/venv/bin/magika
/tmp/buoy-v040-packaging-clean/venv/bin/mammoth
/tmp/buoy-v040-packaging-clean/venv/bin/markdown-it
/tmp/buoy-v040-packaging-clean/venv/bin/markdownify
/tmp/buoy-v040-packaging-clean/venv/bin/markitdown
/tmp/buoy-v040-packaging-clean/venv/bin/normalizer
/tmp/buoy-v040-packaging-clean/venv/bin/numpy-config
/tmp/buoy-v040-packaging-clean/venv/bin/onnxruntime_test
/tmp/buoy-v040-packaging-clean/venv/bin/patchright
/tmp/buoy-v040-packaging-clean/venv/bin/pdf2txt.py
/tmp/buoy-v040-packaging-clean/venv/bin/pdfplumber
/tmp/buoy-v040-packaging-clean/venv/bin/playwright
/tmp/buoy-v040-packaging-clean/venv/bin/pybase64
/tmp/buoy-v040-packaging-clean/venv/bin/pydoc.bat
/tmp/buoy-v040-packaging-clean/venv/bin/pygmentize
/tmp/buoy-v040-packaging-clean/venv/bin/pypdfium2
/tmp/buoy-v040-packaging-clean/venv/bin/python
/tmp/buoy-v040-packaging-clean/venv/bin/python3
/tmp/buoy-v040-packaging-clean/venv/bin/python3.13
/tmp/buoy-v040-packaging-clean/venv/bin/runxlrd.py
/tmp/buoy-v040-packaging-clean/venv/bin/scrapling
/tmp/buoy-v040-packaging-clean/venv/bin/tiny-agents
/tmp/buoy-v040-packaging-clean/venv/bin/torchfrtrace
/tmp/buoy-v040-packaging-clean/venv/bin/torchrun
/tmp/buoy-v040-packaging-clean/venv/bin/tqdm
/tmp/buoy-v040-packaging-clean/venv/bin/transformers
/tmp/buoy-v040-packaging-clean/venv/bin/typer
/tmp/buoy-v040-packaging-clean/venv/bin/update-tld-names
/tmp/buoy-v040-packaging-clean/venv/bin/vba_extract.py
buoy 0.4.0
usage: buoy [-h] [--version]
usage: buoy [-h] [--version]
```

## Digest-verified released-0.3.0 same-environment upgrade

Network download was limited to the immutable released wheel at `https://github.com/Doctacon/buoy-search/releases/download/v0.3.0/buoy_search-0.3.0-py3-none-any.whl`. Before installation, SHA-256 was verified equal to `048dba11df692a7efcd7ab7269fc2eec82f6b53e57573a3de113bbd051750bab`.

A fresh CPython 3.13 environment at `/tmp/buoy-v040-packaging-upgrade/venv` normally installed that wheel. Before upgrade, metadata reported 0.3.0 with both package-owned entry points and complete launcher inspection found both `buoy` and `turbo-search`; both help paths passed. The same environment was normally upgraded with:

```text
uv pip install --python /tmp/buoy-v040-packaging-upgrade/venv/bin/python --upgrade /tmp/buoy-v040-packaging-control/after/buoy_search-0.4.0-py3-none-any.whl
```

After upgrade, metadata reported 0.4.0 with only the `buoy` entry point. Complete launcher inspection and an explicit absence assertion found no `turbo-search`; `buoy --version`, `buoy --help`, and `python -m buoy_search --help` passed.

### Complete pre-upgrade observation

```text
before-upgrade:
version=0.3.0
entry_points=[('console_scripts', 'buoy', 'buoy_search.cli:main'), ('console_scripts', 'turbo-search', 'buoy_search.cli:legacy_main')]
launcher-directory-before:
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.csh
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.fish
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.nu
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.ps1
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate_this.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/buoy
/tmp/buoy-v040-packaging-upgrade/venv/bin/cffi-gen-src
/tmp/buoy-v040-packaging-upgrade/venv/bin/curl-cffi
/tmp/buoy-v040-packaging-upgrade/venv/bin/deactivate.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/distro
/tmp/buoy-v040-packaging-upgrade/venv/bin/dotenv
/tmp/buoy-v040-packaging-upgrade/venv/bin/dumppdf.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/f2py
/tmp/buoy-v040-packaging-upgrade/venv/bin/hf
/tmp/buoy-v040-packaging-upgrade/venv/bin/httpx
/tmp/buoy-v040-packaging-upgrade/venv/bin/huggingface-cli
/tmp/buoy-v040-packaging-upgrade/venv/bin/idna
/tmp/buoy-v040-packaging-upgrade/venv/bin/isympy
/tmp/buoy-v040-packaging-upgrade/venv/bin/magika
/tmp/buoy-v040-packaging-upgrade/venv/bin/mammoth
/tmp/buoy-v040-packaging-upgrade/venv/bin/markdown-it
/tmp/buoy-v040-packaging-upgrade/venv/bin/markdownify
/tmp/buoy-v040-packaging-upgrade/venv/bin/markitdown
/tmp/buoy-v040-packaging-upgrade/venv/bin/normalizer
/tmp/buoy-v040-packaging-upgrade/venv/bin/numpy-config
/tmp/buoy-v040-packaging-upgrade/venv/bin/onnxruntime_test
/tmp/buoy-v040-packaging-upgrade/venv/bin/patchright
/tmp/buoy-v040-packaging-upgrade/venv/bin/pdf2txt.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/pdfplumber
/tmp/buoy-v040-packaging-upgrade/venv/bin/playwright
/tmp/buoy-v040-packaging-upgrade/venv/bin/pybase64
/tmp/buoy-v040-packaging-upgrade/venv/bin/pydoc.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/pygmentize
/tmp/buoy-v040-packaging-upgrade/venv/bin/pypdfium2
/tmp/buoy-v040-packaging-upgrade/venv/bin/python
/tmp/buoy-v040-packaging-upgrade/venv/bin/python3
/tmp/buoy-v040-packaging-upgrade/venv/bin/python3.13
/tmp/buoy-v040-packaging-upgrade/venv/bin/runxlrd.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/scrapling
/tmp/buoy-v040-packaging-upgrade/venv/bin/tiny-agents
/tmp/buoy-v040-packaging-upgrade/venv/bin/torchfrtrace
/tmp/buoy-v040-packaging-upgrade/venv/bin/torchrun
/tmp/buoy-v040-packaging-upgrade/venv/bin/tqdm
/tmp/buoy-v040-packaging-upgrade/venv/bin/transformers
/tmp/buoy-v040-packaging-upgrade/venv/bin/turbo-search
/tmp/buoy-v040-packaging-upgrade/venv/bin/typer
/tmp/buoy-v040-packaging-upgrade/venv/bin/update-tld-names
/tmp/buoy-v040-packaging-upgrade/venv/bin/vba_extract.py
usage: buoy [-h] [--version]
Warning: `turbo-search` is deprecated; use `buoy` instead. It will be removed in 0.4.
usage: buoy [-h] [--version]
```

### Complete post-upgrade observation

```text
after-upgrade:
version=0.4.0
entry_points=[('console_scripts', 'buoy', 'buoy_search.cli:main')]
launcher-directory-after:
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.csh
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.fish
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.nu
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate.ps1
/tmp/buoy-v040-packaging-upgrade/venv/bin/activate_this.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/buoy
/tmp/buoy-v040-packaging-upgrade/venv/bin/cffi-gen-src
/tmp/buoy-v040-packaging-upgrade/venv/bin/curl-cffi
/tmp/buoy-v040-packaging-upgrade/venv/bin/deactivate.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/distro
/tmp/buoy-v040-packaging-upgrade/venv/bin/dotenv
/tmp/buoy-v040-packaging-upgrade/venv/bin/dumppdf.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/f2py
/tmp/buoy-v040-packaging-upgrade/venv/bin/hf
/tmp/buoy-v040-packaging-upgrade/venv/bin/httpx
/tmp/buoy-v040-packaging-upgrade/venv/bin/huggingface-cli
/tmp/buoy-v040-packaging-upgrade/venv/bin/idna
/tmp/buoy-v040-packaging-upgrade/venv/bin/isympy
/tmp/buoy-v040-packaging-upgrade/venv/bin/magika
/tmp/buoy-v040-packaging-upgrade/venv/bin/mammoth
/tmp/buoy-v040-packaging-upgrade/venv/bin/markdown-it
/tmp/buoy-v040-packaging-upgrade/venv/bin/markdownify
/tmp/buoy-v040-packaging-upgrade/venv/bin/markitdown
/tmp/buoy-v040-packaging-upgrade/venv/bin/normalizer
/tmp/buoy-v040-packaging-upgrade/venv/bin/numpy-config
/tmp/buoy-v040-packaging-upgrade/venv/bin/onnxruntime_test
/tmp/buoy-v040-packaging-upgrade/venv/bin/patchright
/tmp/buoy-v040-packaging-upgrade/venv/bin/pdf2txt.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/pdfplumber
/tmp/buoy-v040-packaging-upgrade/venv/bin/playwright
/tmp/buoy-v040-packaging-upgrade/venv/bin/pybase64
/tmp/buoy-v040-packaging-upgrade/venv/bin/pydoc.bat
/tmp/buoy-v040-packaging-upgrade/venv/bin/pygmentize
/tmp/buoy-v040-packaging-upgrade/venv/bin/pypdfium2
/tmp/buoy-v040-packaging-upgrade/venv/bin/python
/tmp/buoy-v040-packaging-upgrade/venv/bin/python3
/tmp/buoy-v040-packaging-upgrade/venv/bin/python3.13
/tmp/buoy-v040-packaging-upgrade/venv/bin/runxlrd.py
/tmp/buoy-v040-packaging-upgrade/venv/bin/scrapling
/tmp/buoy-v040-packaging-upgrade/venv/bin/tiny-agents
/tmp/buoy-v040-packaging-upgrade/venv/bin/torchfrtrace
/tmp/buoy-v040-packaging-upgrade/venv/bin/torchrun
/tmp/buoy-v040-packaging-upgrade/venv/bin/tqdm
/tmp/buoy-v040-packaging-upgrade/venv/bin/transformers
/tmp/buoy-v040-packaging-upgrade/venv/bin/typer
/tmp/buoy-v040-packaging-upgrade/venv/bin/update-tld-names
/tmp/buoy-v040-packaging-upgrade/venv/bin/vba_extract.py
buoy 0.4.0
usage: buoy [-h] [--version]
usage: buoy [-h] [--version]
```

This proves package-manager removal of its own obsolete launcher only. It makes no claim about arbitrary user-owned aliases, wrappers, copies, or caches.

## Failed harness attempts

Two non-product validation harness assertions were corrected without source changes: one initially compared correct `git status` members in the wrong lexical order, and one initially supplied `crawl` a positional URL even though its existing parser requires `--base-url`. The corrected source-delta assertion and valid installed invocation passed. Neither attempt invoked a handler, changed repository behavior, or contacted a product service.

## Side-effect attestation and limits

No package publication, registry write, tag, GitHub Release, release publication, live Turbopuffer call, namespace operation, remote product-data read/write, user-state discovery, state/data migration, re-embedding, local user-data deletion, or user-owned launcher operation occurred. All builds, environments, tests, installs, and upgrade state were disposable and confined to `/tmp` or test-managed temporary directories. Network reads were dependency resolution/downloads and the immutable GitHub 0.3.0 wheel. Authorized Git branch/PR/check delivery is the only permitted remote write.

Local build/install/upgrade validation used macOS arm64 and CPython 3.13.0; complete source tests separately passed CPython 3.11.5 and 3.13.0, and exact-head hosted Linux checks remain required. Independent bounded packaging and final aggregate review remain required. All parent/child tickets stay active pending those reviews.

## Final candidate rebuild and inspection

After recording all local evidence and parent/child progress, the candidate was rebuilt into fresh `/tmp/buoy-v040-packaging-control/final` with the identical controlled build environment, command, and `SOURCE_DATE_EPOCH=1784506710`. SHA-256 remained `1a5cdb4a303eb0c4f7e42b335138a43f4b1098a8f8b2189ded2d3d9fc8e00d30` for the wheel and `bd7d2f80e06e8f6ae2c99a5b81f9ae709d5af5e71c0659cf5333f281e46404b1` for the sdist; both final archives were `cmp`-identical to the comparison archives.

Direct final inspection found 45 wheel members and 95 normalized sdist members with zero `.10x` hits. Wheel metadata was `buoy-search==0.4.0`; `entry_points.txt` was exactly `[console_scripts]\nbuoy = buoy_search.cli:main\n`; all 19 bundled-data members remained; `legacy_main` and a `turbo_search` package were absent. The sdist's single root was `buoy_search-0.4.0`. `git diff --check`, `uv lock --check`, exact build-config diff inspection, and protected-surface assertions passed after progress updates. The complete changed-file set before commit is this evidence record, the packaging/parent/console/environment ticket progress records, `pyproject.toml`, and `tests/test_release_automation.py`; the index was empty.
