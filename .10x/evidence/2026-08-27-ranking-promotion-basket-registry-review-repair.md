Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md, .10x/specs/versioned-repository-evaluations-and-promotion-gate.md, .10x/reviews/2026-08-27-evidence-layout-aggregate-review.md

# Ranking promotion basket registry review repair

## Finding repaired

The latest independent aggregate review retained one P1: the promotion artifact self-declared 12 of 13 repository dataset/corpus/benchmark identities. Only Buoy was cross-checked against repository state, so fabricated hashes for the other basket members could pass.

## Implementation

Added the packaged versioned registry:

```text
src/buoy_search/data/repo_ranking_promotion_baskets.json
```

Its schema is exact `{schema_version, baskets}`. Every nonempty basket must have a unique sorted `(basket_id, basket_version)` identity, `baseline_status=recorded`, a canonical `basket_sha256`, and exactly the sorted 13 governed repositories. Every member must be recorded and include repository-relative paths plus exact raw-byte SHA-256 values for:

- its versioned dataset;
- its content-addressed corpus manifest; and
- its recorded baseline benchmark artifact.

The validator resolves every path under the repository root, requires an existing regular non-symlink file, hashes the actual bytes, and parses each as JSON. Recorded benchmark JSON has a strict schema and must repeat the member's repo/dataset/corpus identities, strict retrieval contract/options, and one exact baseline result row. Promotion validation then requires those actual recorded benchmark inputs/results to equal the promotion artifact's baseline inputs/results.

Promotion artifacts schema v2 now contain only a basket `{basket_id, basket_version, basket_sha256}` reference. Self-declared embedded members are rejected by exact keys. The reference must resolve to one registry entry and exact hash. The existing Buoy evaluation registry remains an additional check: the Buoy basket version must be registered, recorded, promotion eligible, non-path-only, and match dataset/corpus/benchmark identities.

The truthful production registry is:

```json
{"baskets": [], "schema_version": 1}
```

No current promotion-eligible basket was fabricated. Current Buoy v2 remains pending/path-membership-only and therefore cannot be registered or used for promotion.

## Mutation and fixture coverage

Passing tests construct a complete temporary repository state with:

- 13 real dataset JSON files;
- 13 real corpus-manifest JSON files;
- 13 real recorded benchmark JSON files;
- an exact recorded Buoy evaluation-version entry;
- a one-entry versioned promotion-basket registry whose hashes reproduce from those files; and
- a promotion artifact referencing only that registered basket identity.

Tests fail on:

- unregistered basket ID/version;
- missing registry member;
- pending basket/member or pending Buoy version;
- path-membership-only Buoy version;
- dataset-byte tampering;
- corpus-manifest-byte tampering;
- recorded-benchmark-byte tampering;
- missing corpus-manifest or benchmark file;
- placeholder content hash;
- basket-hash drift;
- strict recorded benchmark result/input mismatch; and
- the prior authority, policy, unsafe-option, and CI-base mutations.

The production empty registry itself is asserted and validated.

## Validation

### Focused

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_ranking_promotion.py tests/test_ranking_contract.py tests/test_retriever.py
```

Result: `53 passed, 21 subtests passed`.

```sh
PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py \
  --base-ref HEAD --allow-authority-introduction
```

Result: passed with `registered_baskets=0`, preserving truthful pending state.

The ranking contract validator, compileall, C6 validator, and `git diff --check` passed.

### Full

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `1188 passed, 1276 subtests passed`, with 57 existing lxml deprecation warnings.

```sh
PYTHONPATH=.:src PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Result: `Ran 1188 tests`, `OK`; two existing best-effort temporary plan-cleanup warnings and one lxml warning were emitted.

### Package and isolated installation

```sh
uv build --out-dir /tmp/buoy-basket-registry-dist
# Inspect wheel bytes and empty registry.
uv venv --python 3.13 /tmp/buoy-basket-registry-venv
uv pip install --python /tmp/buoy-basket-registry-venv/bin/python /tmp/buoy-basket-registry-dist/*.whl
# Read packaged registry and ranking authority.
```

Result: sdist and 91-entry wheel built. The new registry, ranking authority, and loader were present. Wheel and isolated-install registry bytes parsed as exact schema v1 with zero baskets; active defaults remained unchanged.

### Hygiene and external effects

`git diff --check` passed and `git diff --cached --name-only` returned no files. No real benchmark, dataset/corpus generation, retrieval, model construction/download, provider call, credential access, namespace/catalog mutation, release, publication, or deployment occurred. The complete passing basket exists only inside temporary test directories and uses deterministic JSON fixtures.

## Limits

- Production has no promotion-eligible basket by design; a future real promotion must separately produce, review, and register complete immutable dataset/corpus/benchmark files.
- GitHub-hosted Actions was not run locally.
- Fresh independent review is required before closure.
