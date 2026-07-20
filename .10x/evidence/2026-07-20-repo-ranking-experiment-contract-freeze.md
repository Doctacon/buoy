Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md, .10x/decisions/repo-ranking-promotion-policy.md, .10x/specs/repo-search-eval-autoresearch.md

# Repo Ranking Experiment Contract Freeze

## What was observed

Local, read-only validation loaded exactly the 13 expected checked-in repo-search datasets under the active `buoy_search.evals` schema. The files contain exactly 90 unique composite `repo_key:case_id` identities and 370 judgments. Dataset-local IDs were preserved. The local ID `top-level-request-api` intentionally occurs in both HTTPX and Requests; the distinct composite identities are `httpx:top-level-request-api` and `requests:top-level-request-api`.

Every judgment path was checked against the corresponding pinned local plan manifest. There are no explicit-zero judgments in this basket. Of 370 nonzero judgment paths, 341 resolve and 29 do not. The unresolved paths affect only Buoy (22 paths) and Click (7 paths), so those two repositories are **insufficient** under C1's stop condition. The other 11 repositories are sufficient. No label, local ID, judgment, grade, reason, dataset, source artifact, or namespace was changed.

The machine-readable inventory is `.10x/evidence/.storage/2026-07-20-repo-ranking-experiment-contract-inventory.json` (SHA-256 `fbdb0723f928ca08ac6a9a9dba1878a0e7974bffc77843b9e97be157411c9f97`). It contains all 90 identity triples, every dataset/plan/manifest hash, exact missing paths, repository mappings, and validation status.

The requested worktree-local `context.md` and `plan.md` were absent. The planner artifact named by the decomposition record was inspected at `/Users/crlough/Code/personal/turbo-search/.pi-subagents/artifacts/outputs/ede1dca0-7084-420f-a122-b9568444f19f/parallel-0/1-planner/plan.md`. The source plans/manifests are ignored local artifacts under `/Users/crlough/Code/personal/turbo-search/artifacts/site-crawls/`; they are pinned below by repository-relative path and SHA-256 rather than copied or modified.

## Procedure

Read authority:

- `.10x/tickets/2026-07-19-freeze-repo-ranking-experiment-contract.md`
- `.10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md`
- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`
- `.10x/decisions/namespace-ranking-defaults.md`
- `.10x/specs/repo-search-eval-autoresearch.md`
- `.10x/evidence/2026-06-28-expanded-repo-ranking-basket-validation.md`
- the planner artifact named above
- all 13 datasets, paired source plans, and paired source manifests

Validation was performed with Python standard-library JSON and SHA-256 handling plus the active `buoy_search.evals.load_eval_cases` loader. `PYTHONDONTWRITEBYTECODE=1` prevented bytecode writes. No credential name was read, no model was imported or loaded, and no live command or provider client was invoked.

## Frozen dataset and source mapping

The bundle hashes are SHA-256 over ordered UTF-8 rows of `relative_path + NUL + file_sha256 + LF`, in the repository order shown below:

- dataset bundle: `3eb31ab2ac0c4b4a23b4c755668cc4480aecbdfa905893caf822c5a2aefa656e`
- plan bundle: `d3298eb850499a6e55e5fb1b7869bbc8ca4a83d52d1b6fa9bf6a9347ee18187a`
- manifest bundle: `1bc90a7beaea69f4c380ab381e583766d32961d2c78aded08145b79778a2409e`

| `repo_key` | Repository | Cases | Judgments | Dataset SHA-256 | Baseline namespace | Source commit | Plan SHA-256 | Manifest SHA-256 | Paths | Status |
|---|---|---:|---:|---|---|---|---|---|---:|---|
| `black` | `psf/black` | 5 | 18 | `79606bd520ee0b5dac5bc323ea2f0d2891c9929f45bde266ba4e29cd3efcd7ef` | `github-psf-black-v1` | `c4c9a93111309459a3f0e1e268160f7ef2159077` | `5a4ffd21545b08f3d6fc99a3d2504d53c953143abdb78899aa3a9037c3efe66c` | `20bc565b7877bdc8825a19e4e258377967ff43cd6ee0990261cc6c364df062ab` | 18/18 | sufficient |
| `buoy` | `Doctacon/turbo-search` | 10 | 33 | `605ac5b775a0b9ce2fc6adb78c4de9ee98a597ec9c8b4cd91e0712b2ed6e8eaf` | `github-doctacon-turbo-search-v2-clean` | `fd7f20cdc14f8d7769bf5305e2dd67eae415a8d2` | `1669f4c3d5471e8f7bf879218c50ecaa6e621744398908169329c373e4cce918` | `6a6e67b0b0ef1ea62ee52dfcfe8aa4b825603895b17d01efe70d04606f40b434` | 11/33 | **insufficient** |
| `click` | `pallets/click` | 10 | 36 | `10f5b7fad2542b9fc30bda307787626f5d3de30060b78f0983aeb7727f377b8b` | `github-pallets-click-v1` | `679a7a0eccbdded7a6e85680bdaaf08003765e01` | `c93e028b8a8a3bb301cd33ec45faea695b8c357c70ff528dc20ce85aeddb9af5` | `e15e52d93139abcddc52f3630b2401696a735d57809dcd5e0e8bf22dcd866c63` | 29/36 | **insufficient** |
| `django` | `django/django` | 5 | 21 | `852856a5cba5c00914be43bcd12b62b5a574c740542f167f9b7588cb7d8dd13e` | `github-django-django-v1` | `54495840a6a8b09ec40c793495e6541a3c0d3d5b` | `4433078fbfae6325fe699f2c08bd52f5845a72154c158a023bec2ad66cd4b510` | `ef2375de0180ae30468f31cc16861b89c4e2f252721139ed7d94670b58cbf001` | 21/21 | sufficient |
| `flask` | `pallets/flask` | 5 | 21 | `9f2dbb6ca3d131c68ee04d9cea3ac614ebb329a49d7c076de1f30a2c35a5194f` | `github-pallets-flask-v1` | `36e4a824f340fdee7ed50937ba8e7f6bc7d17f81` | `f1cf012100a676b070ea9d1d6f0885dcadb95dfba5b76a5c0a0e5e50b4a3df0a` | `7c896549caf74ee301746f03e966c1b9b71693c36404799b553a3b8b73a47042` | 21/21 | sufficient |
| `httpx` | `encode/httpx` | 5 | 20 | `c9b224b88ca619aced7a027697bd4b761b614b9f8660fdafbd0009a9ac9b6f0d` | `github-encode-httpx-v1` | `b5addb64f0161ff6bfe94c124ef76f6a1fba5254` | `a2de5c6266cc90b9493593f1131b4c95bb50069671c7e48a681ee086be472cfd` | `ec99afbf68d1032b065c5c31fa75268496206383c98610d7c1a540fd9c824578` | 20/20 | sufficient |
| `mkdocs` | `mkdocs/mkdocs` | 5 | 22 | `cd32c7f1e119b8b0fbbb30ceed06b40e3c20d9b4d1de4dd8b6888390429286e5` | `github-mkdocs-mkdocs-v1` | `2862536793b3c67d9d83c33e0dd6d50a791928f8` | `9f066a983ea4f4bffdd726dce0d84aebc751f4fdd38aed34119cd65d4cb59651` | `c8b81a99b3b75f774a2115ad521742af854132b96a62e21a323725c45ff06afc` | 22/22 | sufficient |
| `pydantic` | `pydantic/pydantic` | 5 | 18 | `8ecc2c54a7a5e63ff424a67cdf357833dbc933b05147c4f4f5d59d9984fd3255` | `github-pydantic-pydantic-v1` | `080c741ecf4e113b9c7487de16ffbba5182f03bf` | `8c95c9d79e7863f62e53141d71bcecf9b7595114695861d5f8c3bb2a724cac1b` | `1f046e1a5d53e6634e07bbcdf7f8d8b1c8a00b940f97b8ccfbbe22fdf9f43c2e` | 18/18 | sufficient |
| `pytest` | `pytest-dev/pytest` | 10 | 52 | `9d0640002bde44ba0cc1645b85de03ccd833a7a4f3b6387a3ef6d4a8aad24674` | `github-pytest-dev-pytest-v1` | `1aa747de62dd9e9f395513c25298ba604f1724d0` | `50db24227eca82011ecf4dd3f08785c84ed4360fe10aaaaf3e967397da8b615e` | `7b7dd0310e30b393aaba245c5dbcb0796d1d4ec620892443ba4d5a1469eeab34` | 52/52 | sufficient |
| `requests` | `psf/requests` | 10 | 30 | `34b83e35b3fbe5c222a7ec75826a1476223597496ea006ddc0025034308a64ca` | `github-psf-requests-v1` | `4ed3d1b3204caa6806a36125a39589044a02e807` | `6a104745e689b18ed20de8d97deec0eb905136bd50899fcf230a2ed2c7a57d54` | `856b00be507ea051f8cf457b51adb3164b9d22aea93ba164aa74cfe75015aecd` | 30/30 | sufficient |
| `rich` | `Textualize/rich` | 5 | 26 | `2f46d8a768cc50741905a31433f4e79d27c4a472a63b4cd2feb7d47fbedbbf2d` | `github-textualize-rich-v1` | `9d8f9a372cc5916fd4781fec207ced7ddac2f08f` | `0b0a4f139ff2421dadc5310dc96a0894b1403c46b1c7e82a133c3156f58297d8` | `a26d4dddc2b8b13dae149277dfca7d5c6d386ac7ab3a2c99e2380eb7c02128a5` | 26/26 | sufficient |
| `ruff` | `astral-sh/ruff` | 5 | 20 | `2e4e96a66890a57d363da885fb7a3ada3ef5ed86f96df4094298ccfd44aa8bc1` | `github-astral-sh-ruff-v1` | `e6856de97d72225196444b7d969b8fe084140503` | `4c11ca923b89f71c85d0c45851676d291fff53eefcf4f77c5f65e041b06455dd` | `f980d0e64617ee05ca7d6653b8683583f42ac1e72d890025f536608d960485d0` | 20/20 | sufficient |
| `typer` | `fastapi/typer` | 10 | 53 | `4aafafbd0a4c4c427b680e53fbce93d5f1f9154b7762f0eb59c1e8a832165947` | `github-fastapi-typer-v1` | `b210c0e2376d99344f79f11fab3ad34cf890cc20` | `8ef2d1c89a6f7ee452c054d2c7a27ec028bd0bf8aad71a3fd9265121b94a996d` | `bdea1a2c64ec928cacd4dbfbc7a00e56acdeefb1a0690632624c7b258d2fa83d` | 53/53 | sufficient |

The dataset's `metadata.commit_sha` and `metadata.namespace`, where present, match the pinned manifest/plan. Buoy, Click, and Requests omit one or both values in dataset metadata; their mapping above is pinned from the ranking evidence and exact source plan/manifest instead.

### Exact insufficient paths

Buoy's dataset now names `src/buoy_search/*` paths, while its pinned ranking source manifest at commit `fd7f20c...` contains the pre-rename `src/turbo_search/*` corpus. The unresolved checked-in paths are:

- `buoy:github-url-routing`: `src/buoy_search/crawler.py`, `src/buoy_search/github_repo.py`
- `buoy:github-local-acquisition`: `src/buoy_search/github_repo.py`, `src/buoy_search/crawler.py`
- `buoy:repo-file-selection-corpus`: `src/buoy_search/github_repo.py`, `src/buoy_search/chunker.py`
- `buoy:plan-command-local-only`: `src/buoy_search/cli.py`, `src/buoy_search/plan_artifacts.py`
- `buoy:apply-preflight-approved-safety`: `src/buoy_search/apply.py`, `src/buoy_search/cli.py`, `src/buoy_search/applied_state.py`
- `buoy:plan-artifacts-github-metadata`: `src/buoy_search/plan_artifacts.py`, `src/buoy_search/github_repo.py`
- `buoy:chunking-code-and-markdown`: `src/buoy_search/chunker.py`, `src/buoy_search/github_repo.py`
- `buoy:retrieval-hybrid-command`: `src/buoy_search/retriever.py`, `src/buoy_search/cli.py`
- `buoy:evals-composite-metrics`: `src/buoy_search/evals.py`, `.10x/specs/repo-search-eval-autoresearch.md`
- `buoy:evals-cli-safety`: `src/buoy_search/cli.py`, `src/buoy_search/evals.py`, `src/buoy_search/retriever.py`

Click's pinned default manifest omits these judged paths (including oversized or otherwise unselected files); they were not reinterpreted:

- `click:command-group-decorators`: `src/click/core.py`
- `click:command-context-invocation`: `src/click/core.py`
- `click:option-argument-parser`: `src/click/core.py`, `tests/test_options.py`
- `click:terminal-ui-prompts-progress-style`: `tests/test_termui.py`
- `click:exceptions-usage-errors`: `tests/test_options.py`
- `click:help-formatting-output`: `src/click/core.py`

The inventory JSON is the authoritative exact machine-readable list. C1 does not repair these labels. Until source-compatible manifests are separately supplied without changing labels, the 13-repo basket, three-repo pilot (which includes Buoy), C3 capture, and every dependent comparison remain blocked.

## Immutable comparison contract

### Identity and label rules

- `repo_key` is the exact lowercase key in the table.
- `case_id` is the unchanged dataset-local `cases[].id`.
- `composite_case_id` is the literal concatenation `repo_key + ":" + case_id` and is the only case join/cache identity.
- Consumers MUST NOT assume dataset-local `case_id` is globally unique or rename it.
- Dataset bytes and SHA-256 are immutable inputs. Any byte change creates a new contract version and invalidates existing caches.
- Labels are assistant-drafted calibration inputs, not human-approved ground truth. No label-quality claim is made.

### Namespace, corpus, and model compatibility

The baseline namespace and source commit are exact per-repository values in the table. A baseline row is compatible only when all of these fields match: `repo_key`, repository, source commit, source plan SHA-256, source manifest SHA-256, selected corpus artifact hash, namespace, embedding model identity/revision, dimensions, precision, normalization, query/document transform, distance metric, and retrieval options.

The observed plans record model `BAAI/bge-small-en-v1.5` but no immutable model revision. Current source establishes 384 dimensions, `float32`, normalized SentenceTransformer embeddings, document text as title + section + content, raw query text, and cosine distance. `model_revision` therefore MUST remain explicit and nullable for the historical source artifacts; it MUST NOT be invented. An index-changing candidate MUST instead create its paired current-default baseline from the same pinned model revision, source commit, corpus-selection options, and chunk artifact as the candidate. Missing compatibility fields stop that comparison.

The frozen experiment namespace pattern is:

```text
github-{owner_slug}-{repo_slug}-exp-{experiment_slug}-{contract_sha256_12}-v{positive_integer}
```

`owner_slug` and `repo_slug` derive mechanically from the frozen repository mapping using lowercase ASCII and hyphens; `contract_sha256_12` is the first 12 lowercase hex characters of the committed inventory SHA-256. A concrete namespace still requires its child ticket and explicit approval; C1 creates none.

### Baseline and references

- The comparison baseline for scoring-only experiments is the current promoted retrieval default: `candidates=200`, `ranking_mode=file`, `ranking_profile=repo_code`, `ranking_pool=100`, `ranking_aggregation=adaptive_sum_3`, using the repository's frozen namespace/corpus.
- Every index-changing candidate MUST be paired with the current promoted default on the same source commit and selected corpus. A historical namespace on a different commit/corpus is not a paired baseline.
- The routed portfolio `repo_search_score=80.316` and `Precision@5=0.517` is a secondary historical reference only. It is neither a universal baseline nor selector/default authority.

### Frozen folds

Leave-one-repository-out folds are frozen in this order:

```text
fold-01 black
fold-02 buoy
fold-03 click
fold-04 django
fold-05 flask
fold-06 httpx
fold-07 mkdocs
fold-08 pydantic
fold-09 pytest
fold-10 requests
fold-11 rich
fold-12 ruff
fold-13 typer
```

For each fold, the named repository is the entire held-out evaluation group and the other 12 repositories are the only training/selection groups. No query, judgment, candidate, derived feature, aggregate, profile choice, or weight from the held-out repository may enter training, feature scaling, hyperparameter selection, early stopping, or model/profile choice for that fold. Fold assignment is by `repo_key`, never case ID. Insufficient repositories are not silently dropped to form an 11-repo substitute; folds remain frozen but non-executable until all 13 repositories are sufficient.

The fixed three-repo pilot set is `buoy`, `pytest`, and `ruff`. Pilot outcomes MUST NOT be used to tune a candidate after looking at their labels; a changed candidate is a new preregistered experiment.

### Metrics

Per `.10x/specs/repo-search-eval-autoresearch.md`, compute per-case metrics and then the arithmetic mean per repository:

```text
repo_search_score = 100 * (
  0.55 * NDCG@10
+ 0.20 * Recall@10
+ 0.15 * MRR@10
+ 0.10 * Precision@5
)
```

NDCG uses gain `2^grade - 1`. Relevant judgments for recall/MRR/precision have grade greater than zero. Primary comparison metrics are repository-level `repo_search_score` and Precision@5. NDCG@10, Recall@10, MRR@10, every per-case metric, and candidate-minus-baseline per-case deltas MUST remain reported diagnostics. All-repo averages give each repository equal weight, not each case equal weight.

### Escalation and promotion gates

The fixed three-repo pilot gate decides only whether to request a separately approved full-basket experiment:

1. no pilot repository score regression;
2. no pilot repository Precision@5 regression;
3. positive three-repo average score delta; and
4. at least two of the three repositories have positive score deltas.

It is not promotion policy or authority. A full-basket general-default candidate uses the active `.10x/decisions/repo-ranking-promotion-policy.md` unchanged:

1. no repository score regression;
2. no repository Precision@5 regression;
3. positive score delta on at least 3 repositories;
4. largest single-repository positive contribution at most 70% of total positive gain; and
5. improved equal-weight all-repository average score.

Passing either gate authorizes no default, catalog, namespace, or product mutation.

C1 does not define or infer C7's material-weight/sign/order thresholds or C8's oracle-gap measure/threshold. Schema may carry later preregistered values, but both children remain blocked until their distinct values are explicitly user-ratified.

## Frozen raw-candidate and cache schema

The immutable artifact envelope MUST include:

```text
schema_version
contract_id
contract_inventory_sha256
dataset_bundle_sha256
source_plan_bundle_sha256
source_manifest_bundle_sha256
created_at_utc
capture_tool_commit
request_accounting
credential_redaction_attestation
cases[]
artifact_sha256
```

Each `cases[]` entry MUST include:

```text
repo_key
case_id
composite_case_id
question
dataset_path
dataset_sha256
repository
source_commit
source_plan_sha256
source_manifest_sha256
selected_corpus_artifact_hash
namespace
model_compatibility
retrieval_options
ann_candidates[]
bm25_candidates[]
fused_candidates[]
default_ranked_hits[]
```

`model_compatibility` MUST include model ID, immutable revision or explicit null, vector dimensions, precision, normalization flag, query transform/prefix, document transform/prefix, pooling, and distance metric. `retrieval_options` MUST include top-k, candidates, ANN/BM25 enablement, ANN/BM25 field/weight configuration, RRF constant and implementation mode, final ranking mode/profile/pool/aggregation, filters, and every provider option that can affect candidate selection or order.

Every candidate entry MUST include:

```text
namespace
hit_id
namespace_qualified_hit_id
repo_path
path
url
title
content
section_path
chunk_index
doc_kind
tags
source_metadata
ann_rank
ann_score
bm25_rank
bm25_score
fused_rank
fused_score
score_info
```

Ranks/scores not applicable to one list are explicit nulls. `namespace_qualified_hit_id` is the literal `namespace + ":" + hit_id`; a missing hit ID is a capture failure, not permission to join on path. Candidate lists preserve provider order and also record deterministic fused/default ranks. Credentials, tokens, authorization headers, provider request objects, and unrelated provider metadata MUST NOT appear.

The cache key is SHA-256 over RFC 8259-compatible canonical JSON (UTF-8, object keys sorted lexicographically, no insignificant whitespace, arrays order-preserving, finite JSON numbers only) containing:

```text
contract_inventory_sha256
repo_key
case_id
composite_case_id
dataset_sha256
source_commit
source_manifest_sha256
namespace
model_compatibility
retrieval_options
```

Cache lookup and every C7/C8 join MUST use `composite_case_id`; local `case_id` alone is forbidden. The artifact hash uses the same canonical encoding over the complete envelope with `artifact_sha256` omitted, then stores the lowercase SHA-256 hex digest in `artifact_sha256`. Re-serialization MUST reproduce the digest.

## Determinism, tolerances, accounting, and stop conditions

- Dataset, plan, manifest, contract, feature, fold, and artifact hashes require exact byte equality.
- Repeated offline replay from one frozen cache requires exact namespace-qualified hit order, exact integer ranks/counts, and absolute floating-point metric/score difference at most `1e-12`.
- Capture-to-current-default replay requires exact top-10 namespace-qualified hit order per case and absolute per-case/aggregate metric difference at most `1e-9`. Failure blocks C7/C8; it does not justify recapture per child.
- Ties use the current deterministic boundaries: fused order by descending RRF score, then best source rank, then hit ID; final grouped order by descending ranking score, then best fused rank, then normalized group key. Any provider order needed before these boundaries is preserved explicitly.
- Missing, duplicate, non-finite, or ambiguous ranks/scores; namespace/source/model incompatibility; duplicate composite identities; or any held-out leakage is a hard stop.
- A repository with any unreproduced judgment path is marked `insufficient` as a whole, retained in inventory, excluded explicitly from computation, and never replaced by rewritten or reinterpreted labels. A reduced basket is not evidence for the 13-repo gates.
- Request accounting separates logical cases, ANN subqueries, BM25 subqueries, physical provider requests, retries, successes, failures, and any provider-reported billable units. For 90 cases, one complete raw pass is exactly 90 logical cases, 90 ANN subqueries, and 90 BM25 subqueries. Physical requests may be fewer only when documented multi-query batching contains both subqueries; retries are additional and must be reported. No second pass is implicit.
- C1 read no credentials. Future artifacts MUST record only credential variable names checked/removed and a redaction attestation, never values. Provider headers, endpoints containing secrets, internal request bodies, and billing/account identifiers are excluded.

## Validation output

```text
active schema load: 13 files; per-file counts 5/10 as expected; total 90
composite identities: 90 total, 90 unique
cross-repo duplicate local IDs: top-level-request-api -> httpx, requests (allowed)
judgments: 370 total; 0 explicit zero
manifest path checks: 341 resolved; 29 unresolved
repository status: 11 sufficient; buoy and click insufficient
models loaded/downloaded: 0
credentials read: 0
live/provider queries: 0
remote/local namespace writes or deletes: 0
labels/datasets modified: 0
```

## What this supports or challenges

Supports:

- The 13 files and 90 composite identities are now hash-pinned without changing dataset-local identity or label bytes.
- Eleven repositories have complete local source-manifest path reproduction.
- Folds, metrics, paired baseline semantics, pilot escalation, promotion policy, raw artifact/cache identity, hashing, tolerance, redaction, and request accounting are explicit for later children.

Challenges:

- Buoy's current renamed labels do not reproduce against the historical ranking manifest.
- Click's manifest does not contain seven judged paths.
- The source plans/manifests are ignored local artifacts, not checked-in files; their hashes and expected relative paths are durable, but a cold environment must restore exact matching artifacts before use.
- Historical plans do not record an immutable embedding-model revision, so index-changing experiments need a freshly paired baseline with a fully pinned model contract.
- C7/C8 thresholds remain deliberately unresolved and user-gated.

## Limits

This evidence proves local file/schema/hash/path observations and freezes a contract. It does not prove label quality, retrieval quality, model suitability, namespace existence/current contents, provider compatibility, promotion eligibility, or absence of defects. No C3+ work was performed. Independent review is still required; the C1 ticket remains active pending that review.
