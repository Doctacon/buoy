Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/done/2026-08-27-add-ranking-default-promotion-gate.md, .10x/specs/versioned-repository-evaluations-and-promotion-gate.md, .10x/decisions/buoy-versions-repo-evals-and-gates-only-default-promotion.md

# Ranking-default promotion gate implementation

## What was observed

The packaged authority `src/buoy_search/data/ranking_defaults.json` has SHA-256 `ec33b7921b163cd5451cab3c935600b6f2ce90307d23375d8f67c7713a5a9dfc` and reproduces the pre-change active values exactly:

- repository: candidates 200, file/repo_code/pool 100/adaptive_sum_3;
- website/document/database: candidates 200, page/none/pool 20/max.

`src/buoy_search/retrieval/ranking_defaults.py` strictly loads that package resource with duplicate/unknown-key rejection, positive integer and supported-value validation, and one shared candidates boundary. `retriever.py` derives all established exported default constants and `ranking_defaults_for_namespace` mappings from the loaded authority; it no longer contains independently editable ranking-default literals.

`scripts/validate_ranking_promotion.py` validates the current authority locally and classifies it solely from exact bytes at `git merge-base HEAD <base-ref>`. An absent base authority is the one-time non-promotional introduction; equal bytes are ordinary/implementation-only; changed bytes are promotion. Promotion requires exactly one explicit or auto-discovered artifact matching the proposed authority hash under `.10x/evidence/.storage/ranking-promotions/`.

The offline artifact validator strictly binds exact old/proposed authority objects and raw hashes, the active versioned dataset/corpus identities, non-empty retrieval/model contract revisions, complete 13-repository baseline/candidate score and Precision@5 rows, and configurations containing the corresponding ranking authorities. It recomputes the active distribution-aware policy: no per-repository score or P@5 regression, at least three positive score gains, largest gain share at most 70%, and positive average score delta. Missing/mismatched/regressing artifacts fail. Secret-like keys fail. No benchmark is run by CI.

CI now supplies the pull request base SHA and runs this validator in the existing local contract step. Push builds with no PR base validate authority schema and report `base-unavailable`. Documentation explains the single authority and committed immutable artifact convention.

## Procedure and results

### Focused tests and validators

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q \
  tests/test_ranking_promotion.py tests/test_ranking_contract.py tests/test_retriever.py
```

Result: `43 passed, 13 subtests passed`.

```sh
PYTHONPATH=.:src uv run python scripts/validate_ranking_contract.py
PYTHONPATH=.:src uv run python scripts/validate_ranking_promotion.py
PYTHONPATH=.:src uv run python -m compileall -q src tests scripts
```

Result: ranking contract reproduced 13 datasets, 90 identities, 369 judgments, versioned Buoy v2 pending; promotion validator accepted current authority with `classification=base-unavailable`; compilation passed.

```sh
PYTHONPATH=.:src PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest \
  tests.test_ranking_promotion tests.test_ranking_contract tests.test_retriever -q
PYTHONPATH=.:src PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate
```

Result: 43 tests passed; C6 forecast retained exact valid digest `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243` and its pre-existing tokenizer-readiness false state.

The focused matrix covers exact default parity, strict authority parsing, one-time introduction, unchanged implementation-only work, changed authority classification, missing artifact, exact authority mismatch, policy failure, passing same-corpus fixture, and no-base command behavior.

### Full suite

```sh
PYTHONPATH=.:src uv run --with pytest pytest -q
```

Result: `1176 passed, 1232 subtests passed`, with 57 existing lxml deprecation warnings.

### Distribution and isolated installation

```sh
uv build --out-dir /tmp/buoy-promotion-dist
# Inspect wheel ZIP for ranking_defaults.json and ranking_defaults.py.
uv venv --python 3.13 /tmp/buoy-promotion-venv
uv pip install --python /tmp/buoy-promotion-venv/bin/python /tmp/buoy-promotion-dist/*.whl
# Import authority and assert repository/website runtime mappings.
```

Result: sdist and 90-entry wheel built. Both required authority files were present. Isolated Python 3.13 installation loaded the exact authority and reproduced existing repository and website mappings.

### Hygiene and external effects

```sh
git diff --check
git diff --cached --name-only
```

Result: diff hygiene passed; no staged files. No retrieval, model construction/download, provider, credential, namespace, catalog, benchmark, release, publication, or deployment operation occurred. Package installation downloaded ordinary dependencies but did not instantiate a model or issue provider calls.

## What this supports or challenges

This supports every implementation acceptance criterion for the promotion-gate slice: one authority, exact behavioral parity, mechanical merge-base classification, fast non-promotion checks, fail-closed supplied-artifact validation, passing offline fixture, CI wiring, package inclusion, and installed behavior.

## Limits

- No real ranking promotion artifact was generated or approved; passing artifact coverage is synthetic and offline by design.
- The one-time authority introduction is classified non-promotional because its base has no authority file. Exact old-value parity is established by source review and regression tests rather than a historical authority-file hash.
- GitHub Actions was not hosted-run in this local slice; workflow behavior is covered by merge-base integration tests and exact local commands.
- Independent review and parent-plan integration remain outstanding.
