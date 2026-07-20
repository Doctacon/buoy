Status: recorded
Created: 2026-07-19
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-19-return-retrieval-tags.md, .10x/specs/retrieval-tag-output.md, .10x/specs/explicit-multi-namespace-retrieval.md

# Return Retrieval Tags Implementation

## What was observed

The bounded implementation adds stored chunk tags to retrieval requests and `SearchHit`, always serializes live hit `tags` as a JSON list, conditionally prints ordered tags in text, preserves representative-hit tags through grouping, and retries older schemas only for missing `tags` and/or `repo_path`.

Changed implementation and documentation surfaces:

- `src/buoy_search/retriever.py`
- `src/buoy_search/cli.py`
- `docs/retrieval.md`

Focused tests were added or updated in:

- `tests/test_retriever.py`
- `tests/test_multi_namespace_retrieval.py`
- `tests/test_cli.py`

The implementation did not add a tag filter, query filter, ranking signal, ranking/default change, namespace mutation, or live operation.

## Procedure

All commands ran from the `work/return-retrieval-tags` worktree. `PYTHONDONTWRITEBYTECODE=1` prevented Python bytecode artifacts. No live Turbopuffer query or write was run.

### Focused Python 3.11

```text
$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_retriever tests.test_multi_namespace_retrieval tests.test_cli -q
Ran 74 tests in 12.895s
OK
```

### Focused Python 3.13

```text
$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_retriever tests.test_multi_namespace_retrieval tests.test_cli -q
Ran 74 tests in 13.223s
OK
```

### Full Python 3.11

```text
$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 431 tests in 23.714s
OK
```

### Full Python 3.13

```text
$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 431 tests in 22.701s
OK
```

The suites emitted two pre-existing advisory warnings per run from tests that intentionally simulate inability to remove temporary plan artifact directories. They did not fail validation.

### Packaging and diff hygiene

```text
$ uv build --python 3.13 --out-dir /tmp/buoy-return-retrieval-tags-dist
Successfully built /tmp/buoy-return-retrieval-tags-dist/buoy_search-0.4.0.tar.gz
Successfully built /tmp/buoy-return-retrieval-tags-dist/buoy_search-0.4.0-py3-none-any.whl

$ git diff --check
(exit 0; no output)
```

The repository CI defines the full unittest command for Python 3.11 and 3.13 plus the Python 3.13 distribution build. It defines no separate formatter, linter, or type-check command.

## Contract-specific observations

- Initial ANN and BM25 subqueries request both `repo_path` and `tags` with identical attribute lists.
- Fake-backed fallback tests observed these `(repo_path included, tags included)` attempt sequences:
  - tags absent: `(true, true) -> (true, false)`;
  - repo path absent: `(true, true) -> (false, true)`;
  - tags then repo path absent: `(true, true) -> (true, false) -> (false, false)`;
  - repo path then tags absent: `(true, true) -> (false, true) -> (false, false)`.
- Unrelated missing-`content` provider failure is attempted once and propagated; malformed tag rows are propagated after one request.
- Present, empty, and absent row tags serialize respectively as the stored ordered list, `[]`, and `[]`.
- File/page grouping keeps the first-ranked representative chunk's ordered tags.
- Single-namespace, explicit multi-namespace, and routed multi-namespace JSON checks preserve tags; multi-namespace hits retain namespace attribution.
- Single- and multi-namespace text checks print one `Tags: library, guide` line for the non-empty hit and omit it for the empty hit.
- Existing multi-namespace provider-failure tests continue to prove that a later namespace failure raises and CLI stdout remains empty, so no partial payload is emitted.
- Documentation states the JSON, conditional text, metadata-only/no-filter, grouping, namespace consistency, and older-schema behavior.

## PR #57 review-blocker remediation

Independent review found that the original message-wide substring matching could associate `tags` or `repo_path` with unrelated parts of a provider error, including a near-name or the requested-attribute list, rather than the missing-schema diagnostic itself.

The bounded repair at code/test commit `8aa2ced` parses only the known quoted `attribute "<name>" not found in schema` diagnostic, requires exactly one such diagnostic, and retries only when its exact captured name is a still-requested `tags` or `repo_path`. The retry removes only that attribute. A near-name such as `repo_tags`, an unrelated or ambiguous diagnostic, and a repeated diagnostic for an already-removed attribute propagate through the existing user-friendly error path. The latter membership check also preserves finite retry termination.

Focused regressions now prove:

- `attribute "repo_tags" not found in schema` propagates after one provider attempt and does not remove `tags`;
- a provider message may list the full requested attribute list, including both `tags` and `repo_path`, while identifying only one exact missing attribute;
- requested-list context preserves the other optional attribute until a subsequent diagnostic identifies it, in both sequences: `(true, true) -> (true, false) -> (false, false)` and `(true, true) -> (false, true) -> (false, false)`.

After rebasing onto current `origin/develop` at `0ce5f37`, the following non-live validation passed:

```text
$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest tests.test_retriever tests.test_multi_namespace_retrieval tests.test_cli -q
Ran 75 tests in 12.345s
OK

$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 441 tests in 12.646s
OK

$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest tests.test_retriever tests.test_multi_namespace_retrieval tests.test_cli -q
Ran 75 tests in 12.956s
OK

$ PYTHONDONTWRITEBYTECODE=1 uv run --python 3.13 python -m unittest discover -s tests -p 'test_*.py' -q
Ran 441 tests in 12.311s
OK

$ uv build --python 3.13 --out-dir /tmp/buoy-return-retrieval-tags-review-dist
Successfully built buoy_search-0.4.0.tar.gz
Successfully built buoy_search-0.4.0-py3-none-any.whl

$ git diff --check
(exit 0; no output)
```

The test suites emitted only the same pre-existing advisory plan-artifact cleanup warnings described above. No live Turbopuffer read or write was run.

Hosted PR #57 CI run `29720376822` then passed at head `5c5202e3fb1cc25dda6c01b24b770fb43f63e499`: Python 3.11 in 45 seconds, Python 3.13 in 42 seconds, and distribution build in 11 seconds.

## What this supports or challenges

This supports every implementation and deterministic validation criterion in `.10x/tickets/done/2026-07-19-return-retrieval-tags.md`, including the PR #57 fallback-association blocker. Evidence does not itself close a ticket; the later independent pass and closure mapping are recorded in `.10x/reviews/2026-07-20-return-retrieval-tags-review.md` and the done ticket.

## Handoff

Current `origin/develop` had no divergence before commit. Implementation commit `bd06042` was pushed on `work/return-retrieval-tags`, and PR #57 (`https://github.com/Doctacon/buoy-search/pull/57`) was opened against `develop` for the required independent review.

## Limits

- Validation was entirely fake-backed/non-live. It proves request construction, fallback branching, conversion, serialization, rendering, and failure atomicity without contacting Turbopuffer.
- No remote schema migration or backfill was performed or required.
- The initial independent review blocker, its local remediation, and post-repair hosted CI are represented here. Independent final review subsequently passed in `.10x/reviews/2026-07-20-return-retrieval-tags-review.md`.
