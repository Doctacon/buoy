Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-20-remove-buoy-internal-ranking-judgment.md, .10x/specs/repo-search-eval-autoresearch.md, .10x/evidence/2026-07-20-repo-ranking-experiment-contract-freeze.md

# Remove Ratified Internal Buoy Ranking Judgment

## What was observed

Exactly one judgment was removed from `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`, case `evals-composite-metrics`:

- `repo_path`: `.10x/specs/repo-search-eval-autoresearch.md`
- `grade`: `1`
- reason: `Specifies the intended metric contract and config-only autoresearch scope, but is not runtime implementation.`

A semantic comparison against `HEAD` removed that exact object from the prior JSON and then proved deep equality with the checked-in result. All 12 other dataset files were byte-equal to `HEAD`. The Buoy fixture baseline's corresponding no-longer-judged hit was removed so its stated ideal-relevant-hit contract remains accurate; no other fixture hit changed.

The revised contract loads 13 datasets, 90 unique composite identities, and 369 judgments. All 369 remaining judgment paths resolve against the unchanged checked-in source-path bundle. Buoy remains `insufficient`: path validation is complete, but baseline namespace `github-doctacon-buoy-search-v1` remains `pending_approval` and no remote contents or model compatibility were verified. C3 and all dependent comparison work remain blocked. C7/C8 retain their independent threshold gates.

## Regenerated contract-v1 hashes

- Buoy dataset SHA-256: `60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792` (was `605ac5b775a0b9ce2fc6adb78c4de9ee98a597ec9c8b4cd91e0712b2ed6e8eaf`)
- dataset bundle SHA-256: `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`
- inventory canonical payload SHA-256: `97fb02f79e2f9ada09b19eb6e0c91f987ab4e132e906a6814f73af1bc66c50b1`
- inventory whole-file SHA-256: `e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608`
- unchanged source-path bundle SHA-256: `1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697`

| `repo_key` | Cases | Judgments | Dataset SHA-256 | Paths | Baseline status | Sufficiency |
|---|---:|---:|---|---:|---|---|
| `black` | 5 | 18 | `79606bd520ee0b5dac5bc323ea2f0d2891c9929f45bde266ba4e29cd3efcd7ef` | 18/18 | `existing` | sufficient |
| `buoy` | 10 | 32 | `60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792` | 32/32 | `pending_approval` | **insufficient / pending approval** |
| `click` | 10 | 36 | `10f5b7fad2542b9fc30bda307787626f5d3de30060b78f0983aeb7727f377b8b` | 36/36 | `existing` | sufficient |
| `django` | 5 | 21 | `852856a5cba5c00914be43bcd12b62b5a574c740542f167f9b7588cb7d8dd13e` | 21/21 | `existing` | sufficient |
| `flask` | 5 | 21 | `9f2dbb6ca3d131c68ee04d9cea3ac614ebb329a49d7c076de1f30a2c35a5194f` | 21/21 | `existing` | sufficient |
| `httpx` | 5 | 20 | `c9b224b88ca619aced7a027697bd4b761b614b9f8660fdafbd0009a9ac9b6f0d` | 20/20 | `existing` | sufficient |
| `mkdocs` | 5 | 22 | `cd32c7f1e119b8b0fbbb30ceed06b40e3c20d9b4d1de4dd8b6888390429286e5` | 22/22 | `existing` | sufficient |
| `pydantic` | 5 | 18 | `8ecc2c54a7a5e63ff424a67cdf357833dbc933b05147c4f4f5d59d9984fd3255` | 18/18 | `existing` | sufficient |
| `pytest` | 10 | 52 | `9d0640002bde44ba0cc1645b85de03ccd833a7a4f3b6387a3ef6d4a8aad24674` | 52/52 | `existing` | sufficient |
| `requests` | 10 | 30 | `34b83e35b3fbe5c222a7ec75826a1476223597496ea006ddc0025034308a64ca` | 30/30 | `existing` | sufficient |
| `rich` | 5 | 26 | `2f46d8a768cc50741905a31433f4e79d27c4a472a63b4cd2feb7d47fbedbbf2d` | 26/26 | `existing` | sufficient |
| `ruff` | 5 | 20 | `2e4e96a66890a57d363da885fb7a3ada3ef5ed86f96df4094298ccfd44aa8bc1` | 20/20 | `existing` | sufficient |
| `typer` | 10 | 53 | `4aafafbd0a4c4c427b680e53fbce93d5f1f9154b7762f0eb59c1e8a832165947` | 53/53 | `existing` | sufficient |

## Procedure and validation

The inventory was regenerated mechanically from the checked-in dataset bytes: each dataset SHA-256 and judgment count was recomputed, bundle rows were rehashed in inventory order, path membership was re-evaluated, and the canonical payload hash was recomputed with sorted compact JSON excluding `inventory_payload_sha256`. The standard-library validator then independently reproduced the checked-in values:

```text
{"composite_identities": 90, "dataset_bundle_sha256": "5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9", "datasets": 13, "folds": 13, "insufficient_repositories": ["buoy"], "inventory_payload_sha256": "97fb02f79e2f9ada09b19eb6e0c91f987ab4e132e906a6814f73af1bc66c50b1", "inventory_sha256": "e6f97842ec90f0558f51e70f93ea6b8f09f82f63019a27d0738d2b1efb427608", "judgments": 369, "pending_baseline_approval": ["buoy"], "source_path_manifest_bundle_sha256": "1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697"}
```

The semantic comparison reported:

```text
{"after_buoy_sha256": "60008af2950ae8fa27da59c0af737ebf5b4a3e618680bfa113ec75951d338792", "before_buoy_sha256": "605ac5b775a0b9ce2fc6adb78c4de9ee98a597ec9c8b4cd91e0712b2ed6e8eaf", "buoy_semantics_equal_after_exact_removal": true, "other_dataset_files_byte_equal": 12, "removed_exact_judgments": 1}
```

Validation results:

- Python 3.11: validator passed; 5 focused contract tests passed; 446 full tests passed.
- Python 3.13: validator passed; 5 focused contract tests passed; 446 full tests passed.
- CI-equivalent locked syncs passed on both interpreters; wheel and source distribution built successfully.
- PR #60 hosted checks passed: Python 3.11, Python 3.13, and Build distributions.
- `git diff --check` passed.

The first Python 3.11 full-suite attempt correctly exposed that the sample ideal fixture still returned the removed internal path and scored `99.66666666666666` instead of `100.0`. Removing only that stale fixture hit restored the fixture's stated all-relevant-hits behavior; both complete reruns then passed.

## Safety and limits

All validation was local. No namespace, catalog, model, credential, provider, retrieval, or remote state was read or mutated. No model was loaded or downloaded. No retrieval/provider/live namespace query ran. No namespace/catalog/default write or delete occurred.

This evidence proves the checked-in dataset, contract hashes, local path membership, and test outcomes. It does not approve, create, populate, inspect, or verify `github-doctacon-buoy-search-v1`; does not establish Buoy model/corpus compatibility; and does not unblock C3 or dependent work. Independent review is still required before the active ticket can close.
