Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Relates-To: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md, .10x/decisions/repo-ranking-promotion-policy.md, .10x/specs/repo-search-eval-autoresearch.md

# Repo Ranking Experiment Contract Freeze

## What was observed

The repaired contract loads exactly 13 checked-in repo-search datasets, 90 unique composite `repo_key:case_id` identities, and 370 judgments. Dataset bytes and labels are unchanged. The local ID `top-level-request-api` intentionally occurs in both HTTPX and Requests; its composite identities remain distinct.

A checked-in, deterministic source-path bundle now replaces dependence on 347 MB of ignored crawl artifacts: `.10x/evidence/.storage/2026-07-20-repo-ranking-source-path-manifests.json` (1,385,787 bytes; SHA-256 `1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697`). For each repository it stores sorted distinct `repo_path` values plus repository, commit, namespace/status, original plan and manifest hashes, `selected_corpus_artifact_hash`, selected-path count, and selected-row count. The authoritative inventory is `.10x/evidence/.storage/2026-07-20-repo-ranking-experiment-contract-inventory.json` (whole-file SHA-256 `918bdbd152fb6627dfe08d1ea0de0904dc631749165ddb2e798520e192acbd2b`; canonical payload SHA-256 `7c93ae8953e43aac2c2ed98d1ef846458329121453b2662a0d07d93c191c8c13`).

Path validation now resolves 369 of 370 judgments. Click is sufficient after compatibility was established and its source pin was moved to the existing `github-pallets-click-v4-oversize-cards` plan at commit `6ec99f89261b32f8a50848786eca055e1967659f`: all 36 judgments are members of its 144-path/1,215-row selected corpus. The prior v1 manifest was commit `679a7a0e...`, contained 140 paths/1,196 rows, and omitted three distinct judged paths; it was not corpus-compatible and was not retained as Click's contract pin.

Buoy was replanned read-only from public `Doctacon/buoy-search` branch `develop` at commit `fcb7abbe1652d2eab4ee23816b6d992d893603ac`, post-rebrand, with oversize file cards and proposed namespace `github-doctacon-buoy-search-v1`. The local plan selected exactly 64 distinct repository paths and 903 rows. It resolves 32 of 33 judgments; `.10x/specs/repo-search-eval-autoresearch.md` remains absent because checked-in internal records are intentionally excluded from public Buoy artifacts. The proposed 903-row baseline namespace write remains pending a separate explicit approval gate. No namespace was created or written.

The requested worktree-local `context.md` and `plan.md` were absent. The existing C1 ticket and records governed this repair.

## Procedure

Read the C1 ticket, parent, referenced research/specifications/decisions/evidence, all 13 datasets, and the original local plans/manifests. Generated the current Buoy plan with:

```text
PYTHONDONTWRITEBYTECODE=1 uv run buoy plan https://github.com/Doctacon/buoy-search/tree/develop --out-dir /tmp/buoy-c1-current-plan --state-root /tmp/buoy-c1-state --namespace github-doctacon-buoy-search-v1 --repo-oversize-file-cards --json --no-progress
```

This made one public read-only git clone and local temporary plan files. It read no credential, loaded no model, called no retrieval/provider/live namespace service, and made no namespace/catalog write or delete. `scripts/validate_ranking_contract.py` uses only the Python standard library and deterministically verifies the checked-in inventory, source-path bundle, dataset hashes/bundle hash, schemas, 90 identities, 370 judgments, path membership, folds, namespace pattern, and compatibility hashes. CI invokes it directly before the full unittest suite.

## Frozen dataset and source mapping

- dataset bundle SHA-256: `3eb31ab2ac0c4b4a23b4c755668cc4480aecbdfa905893caf822c5a2aefa656e`
- source-path manifest bundle SHA-256: `1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697`

| `repo_key` | Repository | Cases | Judgments | Dataset SHA-256 | Baseline namespace | Source commit | Plan SHA-256 | Manifest SHA-256 | Paths | Rows | Status |
|---|---|---:|---:|---|---|---|---|---|---:|---:|---|
| `black` | `psf/black` | 5 | 18 | `79606bd520ee0b5dac5bc323ea2f0d2891c9929f45bde266ba4e29cd3efcd7ef` | `github-psf-black-v1` | `c4c9a93111309459a3f0e1e268160f7ef2159077` | `5a4ffd21545b08f3d6fc99a3d2504d53c953143abdb78899aa3a9037c3efe66c` | `20bc565b7877bdc8825a19e4e258377967ff43cd6ee0990261cc6c364df062ab` | 18/18 | 2238 | sufficient |
| `buoy` | `Doctacon/buoy-search` | 10 | 33 | `605ac5b775a0b9ce2fc6adb78c4de9ee98a597ec9c8b4cd91e0712b2ed6e8eaf` | `github-doctacon-buoy-search-v1` | `fcb7abbe1652d2eab4ee23816b6d992d893603ac` | `f1316f233857c59f6467071b95750638276ac364a6994f3b25a0a3a2c42d3b46` | `a8e82bd81e5303157691494dfb2f8de50955d072c21cef2e150ec31ae261079c` | 32/33 | 903 | **insufficient / pending approval** |
| `click` | `pallets/click` | 10 | 36 | `10f5b7fad2542b9fc30bda307787626f5d3de30060b78f0983aeb7727f377b8b` | `github-pallets-click-v4-oversize-cards` | `6ec99f89261b32f8a50848786eca055e1967659f` | `e7daa6e9115c1da02cceee841eefd8008719ccbc46347bea3fc5689de1c0ba61` | `9b24e0ee247a3bc475e47fe4a576c4f5927b638a64da2740b948524c7d2008de` | 36/36 | 1215 | sufficient |
| `django` | `django/django` | 5 | 21 | `852856a5cba5c00914be43bcd12b62b5a574c740542f167f9b7588cb7d8dd13e` | `github-django-django-v1` | `54495840a6a8b09ec40c793495e6541a3c0d3d5b` | `4433078fbfae6325fe699f2c08bd52f5845a72154c158a023bec2ad66cd4b510` | `ef2375de0180ae30468f31cc16861b89c4e2f252721139ed7d94670b58cbf001` | 21/21 | 36447 | sufficient |
| `flask` | `pallets/flask` | 5 | 21 | `9f2dbb6ca3d131c68ee04d9cea3ac614ebb329a49d7c076de1f30a2c35a5194f` | `github-pallets-flask-v1` | `36e4a824f340fdee7ed50937ba8e7f6bc7d17f81` | `f1cf012100a676b070ea9d1d6f0885dcadb95dfba5b76a5c0a0e5e50b4a3df0a` | `7c896549caf74ee301746f03e966c1b9b71693c36404799b553a3b8b73a47042` | 21/21 | 1341 | sufficient |
| `httpx` | `encode/httpx` | 5 | 20 | `c9b224b88ca619aced7a027697bd4b761b614b9f8660fdafbd0009a9ac9b6f0d` | `github-encode-httpx-v1` | `b5addb64f0161ff6bfe94c124ef76f6a1fba5254` | `a2de5c6266cc90b9493593f1131b4c95bb50069671c7e48a681ee086be472cfd` | `ec99afbf68d1032b065c5c31fa75268496206383c98610d7c1a540fd9c824578` | 20/20 | 963 | sufficient |
| `mkdocs` | `mkdocs/mkdocs` | 5 | 22 | `cd32c7f1e119b8b0fbbb30ceed06b40e3c20d9b4d1de4dd8b6888390429286e5` | `github-mkdocs-mkdocs-v1` | `2862536793b3c67d9d83c33e0dd6d50a791928f8` | `9f066a983ea4f4bffdd726dce0d84aebc751f4fdd38aed34119cd65d4cb59651` | `c8b81a99b3b75f774a2115ad521742af854132b96a62e21a323725c45ff06afc` | 22/22 | 1930 | sufficient |
| `pydantic` | `pydantic/pydantic` | 5 | 18 | `8ecc2c54a7a5e63ff424a67cdf357833dbc933b05147c4f4f5d59d9984fd3255` | `github-pydantic-pydantic-v1` | `080c741ecf4e113b9c7487de16ffbba5182f03bf` | `8c95c9d79e7863f62e53141d71bcecf9b7595114695861d5f8c3bb2a724cac1b` | `1f046e1a5d53e6634e07bbcdf7f8d8b1c8a00b940f97b8ccfbbe22fdf9f43c2e` | 18/18 | 7377 | sufficient |
| `pytest` | `pytest-dev/pytest` | 10 | 52 | `9d0640002bde44ba0cc1645b85de03ccd833a7a4f3b6387a3ef6d4a8aad24674` | `github-pytest-dev-pytest-v1` | `1aa747de62dd9e9f395513c25298ba604f1724d0` | `50db24227eca82011ecf4dd3f08785c84ed4360fe10aaaaf3e967397da8b615e` | `7b7dd0310e30b393aaba245c5dbcb0796d1d4ec620892443ba4d5a1469eeab34` | 52/52 | 3493 | sufficient |
| `requests` | `psf/requests` | 10 | 30 | `34b83e35b3fbe5c222a7ec75826a1476223597496ea006ddc0025034308a64ca` | `github-psf-requests-v1` | `4ed3d1b3204caa6806a36125a39589044a02e807` | `6a104745e689b18ed20de8d97deec0eb905136bd50899fcf230a2ed2c7a57d54` | `856b00be507ea051f8cf457b51adb3164b9d22aea93ba164aa74cfe75015aecd` | 30/30 | 729 | sufficient |
| `rich` | `Textualize/rich` | 5 | 26 | `2f46d8a768cc50741905a31433f4e79d27c4a472a63b4cd2feb7d47fbedbbf2d` | `github-textualize-rich-v1` | `9d8f9a372cc5916fd4781fec207ced7ddac2f08f` | `0b0a4f139ff2421dadc5310dc96a0894b1403c46b1c7e82a133c3156f58297d8` | `a26d4dddc2b8b13dae149277dfca7d5c6d386ac7ab3a2c99e2380eb7c02128a5` | 26/26 | 4221 | sufficient |
| `ruff` | `astral-sh/ruff` | 5 | 20 | `2e4e96a66890a57d363da885fb7a3ada3ef5ed86f96df4094298ccfd44aa8bc1` | `github-astral-sh-ruff-v1` | `e6856de97d72225196444b7d969b8fe084140503` | `4c11ca923b89f71c85d0c45851676d291fff53eefcf4f77c5f65e041b06455dd` | `f980d0e64617ee05ca7d6653b8683583f42ac1e72d890025f536608d960485d0` | 20/20 | 56407 | sufficient |
| `typer` | `fastapi/typer` | 10 | 53 | `4aafafbd0a4c4c427b680e53fbce93d5f1f9154b7762f0eb59c1e8a832165947` | `github-fastapi-typer-v1` | `b210c0e2376d99344f79f11fab3ad34cf890cc20` | `8ef2d1c89a6f7ee452c054d2c7a27ec028bd0bf8aad71a3fd9265121b94a996d` | `bdea1a2c64ec928cacd4dbfbc7a00e56acdeefb1a0690632624c7b258d2fa83d` | 53/53 | 2512 | sufficient |

The source-path bundle is the clean-checkout authority for path membership. The original plan/manifest hashes and deterministic selected-corpus artifact hashes retain provenance without checking in page/chunk content. `source_artifact_hash` is no longer an inventory field; the exact field is `selected_corpus_artifact_hash`.

### Exact remaining blocker

Only `buoy:evals-composite-metrics` -> `.10x/specs/repo-search-eval-autoresearch.md` is absent from the selected public corpus. C1 does not edit or reinterpret that label. Buoy also has no approved same-source remote baseline: the exact proposal is namespace `github-doctacon-buoy-search-v1`, source commit `fcb7abbe1652d2eab4ee23816b6d992d893603ac`, selected corpus artifact `b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`, and 903 rows. Any write requires a separate explicit approval; this repair grants none. Until both Buoy conditions are resolved, C3 and dependent comparisons remain blocked.

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
source_path_manifest_bundle_sha256
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
$ PYTHONDONTWRITEBYTECODE=1 python3 scripts/validate_ranking_contract.py
{"composite_identities": 90, "dataset_bundle_sha256": "3eb31ab2ac0c4b4a23b4c755668cc4480aecbdfa905893caf822c5a2aefa656e", "datasets": 13, "folds": 13, "insufficient_repositories": ["buoy"], "inventory_payload_sha256": "7c93ae8953e43aac2c2ed98d1ef846458329121453b2662a0d07d93c191c8c13", "inventory_sha256": "918bdbd152fb6627dfe08d1ea0de0904dc631749165ddb2e798520e192acbd2b", "judgments": 370, "pending_baseline_approval": ["buoy"], "source_path_manifest_bundle_sha256": "1af85ca5e1f282e18c4eaa3c634b3da9b0ffb30de09389c799bd34fe3513c697"}

path membership: 369 resolved; 1 unresolved
repository status: 12 path-complete; buoy insufficient and baseline approval pending
models loaded/downloaded: 0
credentials read: 0
retrieval/provider/live namespace queries: 0
namespace/catalog writes or deletes: 0
labels/datasets modified: 0
```

Closure-only verification after adding review/status/reference records preserved the exact validator output above on both Python 3.11 and 3.13. `tests.test_ranking_contract` passed 4/4 on each interpreter; full locked unittest discovery passed 445/445 on each interpreter; and `uv build` produced the wheel and source distribution successfully. The finalization changed no source, test, dataset, inventory, manifest, or hash artifact.

## What this supports or challenges

Supports:

- A clean checkout can validate all dataset and path-membership claims without the ignored 347 MB crawl artifacts.
- Click's v4 source commit and selected corpus are compatible with every existing Click judgment; no label was edited.
- Buoy's post-rebrand selected corpus, exact 64-path/903-row counts, proposed namespace, and pending-write gate are explicit.
- Folds, metrics, paired baseline semantics, pilot escalation, promotion policy, raw artifact/cache identity, hashing, tolerance, redaction, and request accounting remain explicit.

Challenges:

- Buoy's selected public corpus intentionally excludes the one judged internal `.10x` path, so Buoy and the full basket remain insufficient.
- `github-doctacon-buoy-search-v1` has not been approved, created, or populated; same-source remote baseline compatibility is not established.
- Historical plans do not record an immutable embedding-model revision, so index-changing experiments need a freshly paired baseline with a fully pinned model contract.
- C7/C8 thresholds remain deliberately unresolved and user-gated.

## Limits

This evidence proves checked-in schema/hash/path observations and a read-only public-source Buoy plan. It does not prove label quality, retrieval quality, model suitability, namespace existence/current contents, provider compatibility, promotion eligibility, or absence of defects. No C3+ work, live retrieval, namespace write, merge, or approval occurred. Independent review passed at PR #59 head `2d11a2e` in `.10x/reviews/2026-07-20-repo-ranking-experiment-contract-freeze-review.md`; C1 is done with Buoy's insufficiency frozen explicitly, while C3+ remains blocked.

The user's subsequent ratification to remove only the grade-1 internal Buoy `.10x` judgment is owned by `.10x/tickets/2026-07-20-remove-buoy-internal-ranking-judgment.md`. It did not alter this evidence, the dataset, the recorded 370-judgment count, or any hash during C1 closure, and it does not establish Buoy baseline sufficiency.
