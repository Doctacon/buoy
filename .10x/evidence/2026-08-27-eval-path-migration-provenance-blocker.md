Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Relates-To: .10x/tickets/cancelled/2026-08-27-migrate-frozen-repo-eval-paths.md, .10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md, .10x/tickets/cancelled/2026-08-27-recertify-routing-receipts-after-subpackage-migration.md, .10x/decisions/superseded/buoy-migrates-frozen-repo-eval-paths-with-subpackage-layout.md

# Eval-path migration stopped on historical source-manifest provenance

## What was observed

Before changing the dataset, execution traced every ranking-contract hash and membership dependency through `scripts/validate_ranking_contract.py`. The validator does not validate the Buoy dataset against the current checkout. It requires every judged `repo_path` to be present in the frozen Buoy `selected_repo_paths` stored in `.10x/evidence/.storage/2026-07-20-repo-ranking-source-path-manifests.json`.

The dataset has 21 affected judgment occurrences across nine distinct moved flat paths. All nine old paths are present in the frozen source-path manifest; none of their new paths is present there; all nine new files exist in the current checkout:

| Frozen path | Current path |
|---|---|
| `src/buoy_search/applied_state.py` | `src/buoy_search/planning/applied_state.py` |
| `src/buoy_search/apply.py` | `src/buoy_search/planning/apply.py` |
| `src/buoy_search/chunker.py` | `src/buoy_search/indexing/chunker.py` |
| `src/buoy_search/cli.py` | `src/buoy_search/cli/main.py` |
| `src/buoy_search/crawler.py` | `src/buoy_search/indexing/crawler.py` |
| `src/buoy_search/evals.py` | `src/buoy_search/evals/core.py` |
| `src/buoy_search/github_repo.py` | `src/buoy_search/indexing/github_repo.py` |
| `src/buoy_search/plan_artifacts.py` | `src/buoy_search/planning/plan_artifacts.py` |
| `src/buoy_search/retriever.py` | `src/buoy_search/retrieval/retriever.py` |

Updating only dataset and autoresearch fixture paths would therefore fail contract validation after the dataset hash was updated: the new judgment paths would not belong to the frozen source-path bundle. Making them members would require rewriting that historical bundle's `selected_repo_paths` and rebinding `source_path_manifest_bundle_sha256`.

That bundle is not merely a derived list of current checkout paths. Its Buoy entry records historical source/corpus provenance:

- `source_commit`: `fcb7abbe1652d2eab4ee23816b6d992d893603ac`
- `selected_corpus_artifact_hash`: `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`
- `original_manifest_sha256`: `a8e82bd81e5303157691494dfb2f8de50955d072c21cef2e150ec31ae261079c`
- `original_plan_sha256`: `f1316f233857c59f6467071b95750638276ac364a6994f3b25a0a3a2c42d3b46`

Changing its path membership while retaining those identities would make the manifest inconsistent with the historical corpus it attests. Regenerating the corpus identities would violate the active decision's explicit prohibition on changing source corpus identity or regenerating candidates.

This is an unexpected governed dependency beyond the authorized dataset paths, matching test/evaluation fixture paths, and mechanically derived hashes. The supervisor selected the mandatory stop: do not rewrite a historical source manifest with inconsistent corpus identity and do not regenerate corpus identity without explicit owner authority.

No dataset, autoresearch fixture, inventory, source-path bundle, or derived hash was changed under this ticket.

## Procedure and command results

### Governing-record review

Read completely:

- `.10x/tickets/cancelled/2026-08-27-migrate-frozen-repo-eval-paths.md`
- `.10x/decisions/superseded/buoy-migrates-frozen-repo-eval-paths-with-subpackage-layout.md`
- `.10x/specs/buoy-search-subpackage-layout.md`
- `.10x/evidence/2026-08-27-routing-receipt-recertification-blocked-by-eval-path-contract.md`
- `.10x/tickets/done/2026-08-27-reorganize-buoy-search-subpackages.md`
- `.10x/tickets/cancelled/2026-08-27-recertify-routing-receipts-after-subpackage-migration.md`

Inspected `scripts/validate_ranking_contract.py`, the dataset, autoresearch fixture, ranking inventory, and source-path bundle before mutation.

### Identity and membership audit

A standard-library Python script loaded the dataset, source-path bundle, and inventory; counted moved judgment paths; tested old/new bundle membership and current path existence; and printed the bound source/corpus identities.

Observed:

```text
dataset_sha256 60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792
source_bundle_sha256 1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697
inventory_bound_source_bundle_sha256 1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697
inventory_buoy_dataset_sha256 60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792
distinct_moved_paths 9
affected_judgments 21
```

For each of the nine mappings, `old_in_bundle=True`, `new_in_bundle=False`, and `new_exists=True`.

### Mutation and test status

No authorized implementation could be completed without first resolving the provenance conflict. Per the ticket's explicit stop condition, focused tests, the full suite, CLI, wheel inventory, and installed-wheel validation were not rerun in this attempt. Their latest pre-existing outcomes and remaining ten case-level path-existence failures are recorded in `.10x/evidence/2026-08-27-routing-receipt-recertification-blocked-by-eval-path-contract.md`.

`git diff --cached --name-only` returned no output. No files are staged.

## What this supports or challenges

This evidence challenges the current ticket's executability. Its requested path migration cannot satisfy the existing ranking validator while both preserving the historical source-manifest paths and keeping source corpus identity unchanged. It supports the decision to stop before creating an internally inconsistent contract artifact.

## Limits and residual risk

- No implementation or new validation success is claimed.
- The complete repository suite retains the previously recorded ten case-level failures caused by old judged paths.
- The structural migration and four approved routing receipt changes remain present but cannot close while this contract conflict remains unresolved.
- Resolving the conflict requires new owner-level product authority defining whether judgments follow current paths independently of frozen corpus provenance, or authorizing a regenerated source corpus/contract.
- No credentials, models, providers, catalogs, namespaces, releases, publications, deployments, or staged changes were involved.
