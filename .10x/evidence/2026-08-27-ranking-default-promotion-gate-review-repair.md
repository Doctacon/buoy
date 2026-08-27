Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md, .10x/specs/versioned-repository-evaluations-and-promotion-gate.md, .10x/reviews/2026-08-27-evidence-layout-aggregate-review.md

# Ranking-default promotion gate review repair

## What was changed

The significant promotion-gate findings in `.10x/reviews/2026-08-27-evidence-layout-aggregate-review.md` were repaired under the amended specification.

### Recorded content-addressed basket only

Promotion artifact schema v2 now requires one exact, sorted 13-repository `evaluation_basket`. The basket and every member must have `baseline_status=recorded`. Every member binds a versioned dataset identity/hash, non-placeholder content-addressed corpus-manifest hash, and recorded baseline benchmark hash. The canonical basket payload is rehashed and must equal `basket_sha256`.

The Buoy basket member must match a registered version in `repo_evaluation_versions.json`. That registered version must be recorded, `promotion_eligible=true`, have no path-membership-manifest identity, and match dataset, corpus, and benchmark hashes. The repository's current v2 remains pending/path-only and therefore cannot authorize promotion. No corpus or benchmark was generated.

Each repository's recorded baseline benchmark link is independently recomputed from its dataset/corpus identity, exact baseline result, retrieval contract, and strict retrieval options. Baseline and candidate aggregate benchmark payloads are also content-addressed and rehashed.

### Exact experiment isolation

Baseline and candidate configurations contain exactly:

- their respective ranking-default authority;
- the same basket hash;
- the same strict retrieval contract; and
- the same strict retrieval options.

After removing only `ranking_defaults`, the complete configurations must be exactly equal. Candidate gains therefore cannot be attributed to a changed model/revision, retrieval option, dataset, corpus, basket, or contract.

### Closed safe input schema

Retrieval options accept exactly `top_k`, `candidates`, `use_ann`, and `use_bm25`, with bounded integer/boolean validation and at least one retrieval arm enabled. Retrieval/model contract fields are exact and bounded safe identifiers. URL schemes, bearer values, API-key/authorization/credential/password/secret markers, token assignments, and `sk-` credential-like values are rejected. No free-form options, headers, URLs, nested objects, or arbitrary strings are accepted.

### Fail-closed CI comparison

The validator no longer accepts `base-unavailable`. Pull requests compare exact authority bytes at their Git merge base. Pushes compare against the event's exact previous SHA rather than a merge base. Missing PR bases, missing/all-zero push SHAs, and unknown/no-event local invocation fail closed.

The one-time authority introduction requires explicit mode and exact current raw-byte SHA-256 `ec33b7921b163cd5451cab3c935600b6f2ce90307d23375d8f67c7713a5a9dfc`, proving equality with the reviewed pre-file defaults. CI now provides event name, PR base, push previous SHA, and explicit introduction authority. Once a comparison base contains the authority file, introduction mode cannot bypass normal unchanged/promotion classification.

## Tests and mutation coverage

`tests/test_ranking_promotion.py` now covers:

- exact authority introduction hash and unchanged runtime defaults;
- explicit-introduction requirement and changed-introduction rejection;
- PR merge-base and push previous-SHA classification;
- missing event/base, missing PR base, missing/all-zero push SHA rejection;
- missing promotion artifact;
- passing recorded content-addressed 13-repository basket;
- pending and path-membership-only Buoy version rejection;
- incomplete basket and placeholder corpus identity rejection;
- unequal retrieval options and model revision rejection;
- unknown/free-form options, wrong types, out-of-range values, and unsafe URL/credential-like values;
- basket hash, aggregate benchmark hash, and per-repository recorded benchmark linkage mutation;
- authority hash mismatch and distribution-policy failure.

## Validation

### Focused tests

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_ranking_promotion.py tests/test_ranking_contract.py tests/test_retriever.py
```

Result: `51 passed, 21 subtests passed`.

```sh
PYTHONPATH=.:src uv run python -m unittest \
  tests.test_ranking_promotion tests.test_ranking_contract tests.test_retriever -q
```

Result: `Ran 51 tests`, `OK`.

### Contract, CI-mode, compilation, and hygiene

Commands exercised the ranking contract validator; explicit local introduction; simulated pull-request merge-base mode; simulated push previous-SHA mode; the C6 validator; and compileall. All passed. A no-event/no-base invocation exited 1 with:

```text
ranking promotion validation failed: ranking comparison event/base is missing; use --base-ref for local validation
```

`git diff --check` passed and `git diff --cached --name-only` returned no files.

### Full suite

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `1184 passed, 1240 subtests passed`, with 57 existing lxml deprecation warnings.

The exact CI test style also passed:

```sh
PYTHONPATH=.:src PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Result: `Ran 1184 tests`, `OK`; two existing best-effort temporary plan-cleanup warnings and one lxml deprecation warning were emitted.

### Package and isolated install

```sh
uv build --out-dir /tmp/buoy-promotion-repair-dist
# Inspect wheel inventory.
uv venv --python 3.13 /tmp/buoy-promotion-repair-venv
uv pip install --python /tmp/buoy-promotion-repair-venv/bin/python /tmp/buoy-promotion-repair-dist/*.whl
# Load packaged authority and assert current repository/website defaults.
```

Result: sdist and 90-entry wheel built; `ranking_defaults.json` and `retrieval/ranking_defaults.py` were present; isolated Python 3.13 loaded the authority and reproduced current defaults.

## External-effect boundary

No real benchmark artifact, corpus, score, model, retrieval, provider, credential, namespace, catalog, release, publication, or deployment operation occurred. The passing recorded-basket test is a deterministic synthetic offline fixture. Package installation resolved dependencies but did not construct/load a model or contact a product provider.

## Limits and residual risk

- No real recorded 13-repository basket exists in this task; current v2 correctly remains pending and promotion-ineligible.
- GitHub-hosted Actions was not run locally. PR/push environment behavior is covered by deterministic resolution/classification tests and direct simulated commands.
- The review's removed-flat-module distribution-smoke finding belongs to final subpackage integration and is not repaired by this promotion-gate slice, as permitted by the follow-up scope.
- Fresh independent review is required before ticket closure.
