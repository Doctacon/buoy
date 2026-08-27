Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md, .10x/specs/versioned-repository-evaluations-and-promotion-gate.md

# Versioned Buoy repository evaluations implementation

## What was observed

The frozen Buoy v1 dataset is preserved byte-for-byte at `.10x/evidence/.storage/2026-08-27-buoy-repo-eval-v1.json`. Its SHA-256 is `60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792`, exactly matching `HEAD:src/buoy_search/data/buoy_search_repo_search_seed_evals.json`. The historical source-path bundle and contract inventory remain byte-identical with SHA-256 values `1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697` and `e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`.

The active packaged dataset is now `src/buoy_search/data/buoy_search_repo_search_v2.json`. It carries forward all 10 cases and 32 judgments. Exactly nine distinct historical source paths are mapped to their reorganized locations; questions, IDs, coverage areas, grades, reasons, and all other judgment/metadata semantics are validator-proven unchanged. V2 is explicitly `baseline_status=pending` and contains no benchmark artifact or score claim.

The current path-membership manifest contains exactly the 15 unique v2 judgment paths. All exist in the reorganized checkout. After the aggregate-review correction, its raw SHA-256 is `4b7739515d15cd14b9cf9e374e5318c7fa9e7a3bb7e208f25878e6489751068b`. The corrected v2 dataset raw SHA-256 is `691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae`.

The standard-library ranking validator now resolves frozen v1 through the immutable version registry while retaining the historical logical dataset path when reproducing the original 13-dataset bundle hash. Historical paths are checked against the historical source bundle, not `HEAD`. V2 is separately checked against its declared path mapping and current path-membership manifest. The pending-v2 registry and dataset expose only `path_membership_manifest_path`/`sha256`, contain no corpus-manifest or source-snapshot field, and set `promotion_eligible=false`; the path-membership manifest also explicitly sets `promotion_eligible=false`. One mutation test rehashes a modified v2 dataset and proves non-path question drift fails; another proves adding a corpus-identity field to pending v2 fails exact-schema validation.

No retrieval, embedding, model construction/download, provider, namespace, catalog, credential, or live evaluation operation was performed. The only autoresearch execution used the checked-in fixture-mode experiment and completed locally.

## Exact path mapping

- `src/buoy_search/applied_state.py` -> `src/buoy_search/planning/applied_state.py`
- `src/buoy_search/apply.py` -> `src/buoy_search/planning/apply.py`
- `src/buoy_search/chunker.py` -> `src/buoy_search/indexing/chunker.py`
- `src/buoy_search/cli.py` -> `src/buoy_search/cli/main.py`
- `src/buoy_search/crawler.py` -> `src/buoy_search/indexing/crawler.py`
- `src/buoy_search/evals.py` -> `src/buoy_search/evals/core.py`
- `src/buoy_search/github_repo.py` -> `src/buoy_search/indexing/github_repo.py`
- `src/buoy_search/plan_artifacts.py` -> `src/buoy_search/planning/plan_artifacts.py`
- `src/buoy_search/retriever.py` -> `src/buoy_search/retrieval/retriever.py`

## Procedure and results

### Integrity and semantic validator

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py
```

Passed. It reproduced 13 datasets, 90 composite identities, 369 judgments, the frozen v1 dataset/bundle/inventory/source-manifest identities, active dataset version 2, pending baseline state, nine path mappings, v2 dataset hash, and v2 manifest hash.

### Focused tests

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_ranking_contract.py tests/test_evals.py tests/test_autoresearch.py
```

Passed: `35 passed, 22 subtests passed`.

### Fixture-only autoresearch

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run python \
  -m buoy_search.evals.autoresearch \
  --experiment autoresearch/experiments/repo-search-fixture-baseline.json \
  --out <temporary-directory> --json
```

Passed with fixture result status `passed`. The temporary output was removed. No live mode or credentials were used.

### Compilation and full suite

```sh
PYTHONDONTWRITEBYTECODE=1 uv run python -m compileall -q src tests scripts
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:src uv run --with pytest pytest -q
```

Passed: `1169 passed, 57 warnings, 1232 subtests passed` in 87.40 seconds. Warnings were existing lxml `strip_cdata` deprecations.

### Wheel inventory

```sh
uv build --wheel --out-dir /tmp/buoy-eval-wheel
```

Passed. The wheel contains `buoy_search_repo_search_v2.json`, `buoy_search_repo_search_v2_path_membership.json`, and `repo_evaluation_versions.json`; it does not package the historical v1 filename. Historical v1 remains repository evidence under `.10x`, which distributions exclude.

### Final hygiene

`git diff --check` passed. `git diff --cached --name-only` returned no output; no files are staged. Direct hash comparison proved the v1 archive matches the old tracked dataset exactly, and `git diff --quiet` proved the historical source bundle/inventory were not modified.

## Aggregate-review repair validation

The significant review finding in `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md` was repaired under the updated specification. The pending v2 file was renamed from `buoy_search_repo_search_v2_manifest.json` to `buoy_search_repo_search_v2_path_membership.json`. The pending registry and dataset use only `path_membership_manifest_path` and `path_membership_manifest_sha256`, set `promotion_eligible=false`, and contain no `corpus_manifest_*` or `source_snapshot` fields. The path-membership file itself contains no source-snapshot or content identity.

Fresh validation results:

- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` passed and reported active v2 pending, promotion ineligible, dataset SHA-256 `691566d85d1187717cfc06daebeb8bb965d9b337787050fab071afe8fad4d0ae`, and path-membership SHA-256 `4b7739515d15cd14b9cf9e374e5318c7fa9e7a3bb7e208f25878e6489751068b`.
- Focused ranking/eval/autoresearch tests passed: `36 passed, 22 subtests passed`.
- Compilation, `git diff --check`, no-staged-files, and wheel inventory passed. The wheel contains the explicitly named path-membership file and excludes both the old generic v2 manifest filename and historical v1 package filename.
- A full suite attempt reached `1175 passed, 1232 subtests passed` with exactly two failures in `tests/test_ranking_promotion.py`. Both belong to the separate promotion-gate repair: its old fixture directly indexes `active["corpus_manifest_sha256"]`, which the corrected pending interface intentionally removes. The promotion validator/tests must consume the discriminated registry and reject pending versions; this evaluation ticket did not implement that separate validator.

The historical v1 dataset remains SHA-256 `60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792`; the historical source bundle and inventory remain unchanged.

## What this supports

This evidence supports the evaluation-specific acceptance criteria in `.10x/tickets/done/2026-08-27-version-buoy-repository-evaluations.md`: immutable v1 preservation, explicit v2 lineage and path mapping, pending and promotion-ineligible state without a corpus/source claim, current path truth, historical/current validation separation, focused tests, package inclusion, and no external/model operation. A fresh aggregate full-suite pass remains pending the separately owned promotion-validator repair described above.

## Limits and residual risk

- V2 intentionally has no benchmark result and cannot support a ranking-default promotion until a separately authorized same-corpus baseline/candidate artifact is recorded.
- The path-membership manifest binds the active judged path set, not source file bytes or corpus identity. This is intentional for baseline-pending fast CI; a future recorded evaluation version and benchmark artifact must bind its actual content-addressed corpus snapshot.
- The first aggregate review failed; this repair requires fresh independent review. Parent-plan integration was previously run but must be revalidated against the repaired interface. This evidence does not close the ticket or authorize promotion, live evaluation, release, or publication.
