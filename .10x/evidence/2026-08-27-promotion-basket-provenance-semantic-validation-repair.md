Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md, .10x/specs/versioned-repository-evaluations-and-promotion-gate.md, .10x/reviews/2026-08-27-promotion-basket-provenance-review.md

# Promotion basket provenance semantic-validation repair

## Finding repaired

`.10x/reviews/2026-08-27-promotion-basket-provenance-review.md` found that registry member files were hash-verified but dataset/corpus JSON semantics were not. A registry could consistently replace a dataset or corpus with unrelated JSON, update the member and basket hashes, and pass.

## Strict dataset validation

Every registered dataset now has exact schema-v1 keys:

```text
schema_version
dataset_id
dataset_version
repository
cases
```

Dataset ID, positive version, and repository must equal the basket member. Cases must be a nonempty list with unique bounded safe IDs, bounded nonempty questions, and nonempty judgments. Every judgment has exact `repo_path`, `grade`, and `reason` fields. Paths must be unique per case, canonical POSIX repository-relative paths without traversal; grades are non-boolean integers in `[0,3]`; reasons are bounded, stripped, and nonempty. Every judged path must occur in the recorded corpus inventory.

## Strict corpus-manifest validation

Every registered corpus manifest now has exact schema-v1 keys:

```text
schema_version
manifest_id
repository
source_identity
document_inventory_sha256
documents
```

Repository must equal the basket member. Source identity has exact `{kind, revision}` shape, `kind=git-commit`, and a full lowercase 40-hex revision matching the member. Documents must be a nonempty list with exact `path` and `content_sha256` fields. Paths must be sorted, unique, canonical, repository-relative, and traversal-free. Content hashes must be non-placeholder lowercase SHA-256 values. The canonical document inventory hash and positive document count must match both manifest bytes and basket-member fields.

Recorded benchmark schema was extended to repeat and match repository/source identity in addition to its existing dataset/corpus/config/result linkage.

## Consistent-rehash mutation coverage

The passing fixture now creates semantically complete dataset and corpus documents for all 13 repositories. New tests mutate actual files and then consistently update their raw member hash, basket hash, registry bytes, and promotion-artifact basket reference. Validation still rejects:

Dataset mutations:

- empty/unrelated JSON object;
- wrong repository;
- wrong dataset ID;
- wrong dataset version;
- wrong schema version;
- empty cases;
- grade outside `[0,3]`; and
- a valid-looking judgment path absent from the corpus.

Corpus mutations:

- empty/unrelated JSON object;
- wrong repository;
- wrong source revision;
- wrong schema version;
- empty document inventory;
- duplicate document paths;
- traversal path;
- placeholder content hash; and
- inconsistent inventory identities.

These are in addition to prior missing/tampered/unregistered file and promotion-policy mutations.

## Validation

### Focused

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_ranking_promotion.py tests/test_ranking_contract.py tests/test_retriever.py
```

Result: `55 passed, 37 subtests passed`.

The production promotion validator passed with explicit introduction authority and reported `registered_baskets=0`. Ranking-contract, C6, compileall, and diff-hygiene checks passed.

### Full

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `1191 passed, 1292 subtests passed`, with 57 existing lxml warnings.

```sh
PYTHONPATH=.:src PYTHONDONTWRITEBYTECODE=1 \
  uv run python -m unittest discover -s tests -p 'test_*.py' -q
```

Result: `Ran 1191 tests`, `OK`; two existing best-effort temporary plan-cleanup warnings and one lxml warning were emitted.

### Package and isolated installation

```sh
uv build --out-dir /tmp/buoy-provenance-dist
# Inspect wheel registry/authority resources.
uv venv --python 3.13 /tmp/buoy-provenance-venv
uv pip install --python /tmp/buoy-provenance-venv/bin/python /tmp/buoy-provenance-dist/*.whl
# Read packaged empty registry and active ranking authority.
```

Result: sdist and 91-entry wheel built; packaged/installed registry remained exact `{baskets: [], schema_version: 1}` and active defaults remained unchanged.

## External-effect boundary and limits

No real basket, dataset, corpus, benchmark, retrieval, model, provider, credential, namespace, catalog, release, publication, or deployment operation occurred. Semantically complete passing files exist only in temporary test directories.

Production remains truthfully empty and current Buoy v2 remains pending. A future real basket requires separate evidence generation/review. GitHub-hosted Actions was not run locally. Fresh independent review is required before closure.
