Status: active
Created: 2026-07-15
Updated: 2026-07-15

# Representative Semantic Namespace Routing Experiment

## Purpose and scope

Determine whether small, reviewable namespace cards can route existing public-repository questions back to their originating Buoy namespace better than literal aliases alone.

This is one descriptive, read-only experiment. It MUST produce representative source-attribution evidence without adding a production taxonomy, catalog, router, CLI, API, persistence layer, or graph. Its code and artifacts MUST remain under an explicitly experimental boundary.

## Provenance

### User-ratified direction

On 2026-07-15 the user accepted the smaller path recommended by `.10x/reviews/2026-07-15-holistic-semantic-routing-workstream-review.md`: one representative experiment, reuse rather than parallel infrastructure, no production architecture before evidence, and no graph unless simpler routing leaves a measured gap.

### Source-backed inputs

The experiment MUST load these tracked source datasets and mappings directly:

| Repository key | Home namespace | Tracked dataset | Cases |
|---|---|---|---:|
| `black` | `github-psf-black-v1` | `src/buoy_search/data/black_repo_search_seed_evals.json` | 5 |
| `buoy` | `github-doctacon-buoy-search-v1` | `src/buoy_search/data/buoy_search_repo_search_seed_evals.json` | 10 |
| `click` | `github-pallets-click-v1` | `src/buoy_search/data/click_repo_search_seed_evals.json` | 10 |
| `django` | `github-django-django-v1` | `src/buoy_search/data/django_repo_search_seed_evals.json` | 5 |
| `flask` | `github-pallets-flask-v1` | `src/buoy_search/data/flask_repo_search_seed_evals.json` | 5 |
| `httpx` | `github-encode-httpx-v1` | `src/buoy_search/data/httpx_repo_search_seed_evals.json` | 5 |
| `mkdocs` | `github-mkdocs-mkdocs-v1` | `src/buoy_search/data/mkdocs_repo_search_seed_evals.json` | 5 |
| `pydantic` | `github-pydantic-pydantic-v1` | `src/buoy_search/data/pydantic_repo_search_seed_evals.json` | 5 |
| `pytest` | `github-pytest-dev-pytest-v1` | `src/buoy_search/data/pytest_repo_search_seed_evals.json` | 10 |
| `requests` | `github-psf-requests-v1` | `src/buoy_search/data/requests_repo_search_seed_evals.json` | 10 |
| `rich` | `github-textualize-rich-v1` | `src/buoy_search/data/rich_repo_search_seed_evals.json` | 5 |
| `ruff` | `github-astral-sh-ruff-v1` | `src/buoy_search/data/ruff_repo_search_seed_evals.json` | 5 |
| `typer` | `github-fastapi-typer-v1` | `src/buoy_search/data/typer_repo_search_seed_evals.json` | 10 |

Together these tracked files contain 90 source-backed, assistant-drafted project questions. The table's mapping mechanically establishes each question's **home namespace**. The experiment MUST use only case ID, question text, repository key, and home namespace; it MUST ignore file-level relevance judgments.

The questions and judgments are not human-approved product ground truth, as recorded in `.10x/evidence/2026-06-28-cross-corpus-seed-eval-datasets.md` and each dataset's metadata. Independent review MUST inspect the source-attribution use and identify materially ambiguous questions; the report MUST preserve this provenance and limitation.

The local Hugging Face cache was inspected on 2026-07-15 and contains open-source model `BAAI/bge-small-en-v1.5` at immutable revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`. The experiment MUST load exactly that revision in offline/local-only mode and MUST fail clearly rather than access the network, use a credential, or substitute another model.

## Experimental boundary

All experiment-specific implementation, card configuration, plan, result, and report artifacts MUST live under:

`autoresearch/runs/semantic-routing-representative-20260715/`

The implementation MUST replace the broad `autoresearch/runs/` ignore rule with an equivalent contents rule plus a narrow exception that tracks this one experiment directory and its files. Existing unrelated run contents MUST remain ignored unless already tracked.

Focused tests MAY live under `tests/`, but production package behavior under `src/buoy_search/` MUST NOT change. The experiment MAY import existing constants or side-effect-free helpers; it MUST NOT create a reusable taxonomy/catalog framework merely to run this benchmark.

The run MUST install fail-fast process guards before model construction or evaluation:

- socket connection attempts MUST raise;
- known Turbopuffer, Hugging Face token, and hosted-model credential variables MUST be absent from the child execution environment;
- Hugging Face implicit token use and telemetry MUST be disabled;
- file creation, write-mode opens, replacement, rename, and deletion MUST be rejected outside the experiment directory and one process-owned temporary directory;
- the existing model cache MUST be read-only under that path policy.

The temporary directory MUST be created specifically for the run, recorded in the plan as ephemeral, and removed after execution. It MUST NOT contain final evidence.

The run MUST NOT:

- contact Turbopuffer or any hosted API;
- read credentials;
- download a model;
- write outside the experiment directory and the one process-owned temporary directory;
- modify production state, local applied state, model caches, or remote state;
- add a production command or public API.

## Namespace cards

The experiment MUST define exactly one card for each of the 13 input repository keys. Each card MUST contain:

- `repo_key` matching the input key;
- the exact input `namespace`;
- a human-readable `title`;
- a short, project-level `summary`;
- zero or more `aliases`;
- zero or more broad `tags`;
- `public: true`;
- an explicit compatible embedding contract for `BAAI/bge-small-en-v1.5`.

Card summaries, aliases, and tags MUST describe the public project, not individual benchmark questions, expected files, or cached hits. A reviewer MUST be able to detect query-specific leakage from the checked-in card file.

Cards MUST be ordered by `repo_key` in the canonical configuration. Loaders MUST reject duplicate repository keys, duplicate namespaces, missing input cards, extra cards, non-public cards, and incompatible embedding contracts before scoring.

## Question labels and limits

For every input question, the containing repository's namespace is the required home namespace. Other namespaces are unlabeled, not known negatives. Consequently:

- the experiment MUST measure whether the home namespace is retrieved and at what rank;
- it MUST NOT report route precision or claim that alternative namespaces are irrelevant;
- it MUST NOT claim answer quality, cross-namespace retrieval quality, ACL correctness, production latency, or production readiness.

This benchmark measures source attribution over existing public project questions. It is stronger than a synthetic plumbing fixture but remains a proxy for production routing relevance.

## Normalization

Lexical comparison MUST be deterministic:

1. apply Unicode NFKC;
2. apply `casefold()`;
3. replace each maximal non-alphanumeric run with one ASCII space;
4. collapse whitespace;
5. trim.

A phrase matches only a contiguous complete normalized token sequence. Arbitrary substring matching is forbidden.

## Routing strategies

The experiment MUST compare four strategies over the same eligible card set.

### Oracle

The oracle ranks the labeled home namespace first. It is a reference ceiling, not a deployable method.

### Lexical aliases

The lexical strategy matches normalized card titles, aliases, and tags against the normalized question. For each card it MUST build a deduplicated set of non-empty normalized descriptors across those fields. Each descriptor contributes at most once when it appears one or more times as a complete token phrase; repeated question occurrences do not increase either score. `total matched-token count` is the sum of token lengths of the distinct matched descriptors.

It MUST rank matched cards by:

1. descending number of distinct matched descriptors;
2. descending total matched-token count;
3. ascending `repo_key` as the deterministic tie-breaker.

Unmatched cards MUST remain unranked. The lexical strategy is deliberately experiment-local and MUST NOT become a controlled-taxonomy subsystem.

### Semantic cards

The semantic strategy MUST:

- build card text from title, summary, aliases, and tags in one documented deterministic format;
- embed cards as passages and questions as queries with `BAAI/bge-small-en-v1.5` revision `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`;
- pass `local_files_only=True` and the exact revision to model construction;
- set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, `HF_DATASETS_OFFLINE=1`, `HF_HUB_DISABLE_IMPLICIT_TOKEN=1`, and `HF_HUB_DISABLE_TELEMETRY=1` before importing/model construction;
- remove `HF_TOKEN`, `HUGGING_FACE_HUB_TOKEN`, `TURBOPUFFER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `COHERE_API_KEY` from the child run environment;
- use normalized float32 embeddings and cosine similarity;
- rank descending by cosine similarity, then ascending `repo_key` for exact ties;
- compute and record a deterministic SHA-256 manifest over resolved regular files in the pinned local model snapshot.

Model-load or path-guard failure MUST stop the run with an actionable error. The implementation MUST NOT download a model, mutate the cache, or silently use lexical scores as semantic scores.

### Hybrid route RRF

The hybrid strategy MUST fuse the lexical and semantic namespace ranks with equal-weight reciprocal-rank fusion:

`score(namespace) = sum(1 / (60 + rank))`

Only strategies that ranked a namespace contribute. Hybrid ties MUST resolve by ascending `repo_key`.

The `60` constant MUST be imported from or checked against Buoy's existing `RRF_K`; a second configurable RRF default is forbidden.

`cross_namespace_rrf` MUST NOT run in this route-only experiment because the tracked datasets do not contain the same question executed against every candidate namespace. Faking absent per-namespace hits would produce invalid downstream evidence. A later separately authorized read-only retrieval experiment may use the existing helper once comparable cross-namespace hit lists exist.

## Measurements

For each non-oracle strategy, the result MUST record for every question:

- repository key and case ID;
- question text;
- expected home namespace;
- ordered routed namespaces with raw strategy scores and ranks;
- home-namespace rank or `null` when unranked.

The report MUST include aggregate and per-repository:

- mean reciprocal rank of the home namespace;
- home-namespace recall at 1, 3, and 5;
- unranked question count;
- the count of evaluated questions.

The report MUST include the oracle reference, but MUST NOT use oracle values to obscure the measured strategies. Route fan-out is fixed at five for reporting; no threshold or promotion gate is ratified by this specification.

## One-shot artifacts

The run directory MUST contain:

- a reviewed namespace-card configuration;
- one bounded evaluation script;
- `plan.json` describing immutable inputs, model, strategies, limits, and no-network/no-write controls;
- `result.json` containing machine-readable per-question and aggregate measurements;
- `report.md` summarizing results, failures, limitations, and comparison among strategies.

Artifacts MUST be deterministic apart from explicitly recorded environment/runtime duration fields. Re-running with the same committed inputs and model MUST preserve rankings and metrics.

The script MUST refuse to overwrite an existing final `result.json` unless an explicit experiment-local replacement flag is supplied. Replacement MUST remain inside the run directory and be visible in version control.

## Tests

Focused tests MUST prove:

- card/input bijection and fail-closed validation;
- canonical normalization and complete-phrase lexical matching;
- deterministic lexical tie-breaking;
- semantic tie-breaking with injected vectors, without constructing the real model;
- hybrid RRF semantics and consistency with `RRF_K`;
- metric calculations including unranked homes;
- final-output overwrite refusal;
- default execution sets the exact offline/local-only model controls and revision;
- fail-fast socket, credential-environment, and path-based write guards reject network, implicit-token, model-cache mutation, and writes outside the allowlist;
- the narrow `.gitignore` exception tracks only this experiment's run artifacts.

The final run MUST also pass the repository's full test suite and `git diff --check`.

## Acceptance scenarios

### Representative input

**Given** the 13 tracked public-repository datasets and one independently reviewable card per repository
**When** the experiment validates its inputs
**Then** all 90 questions and exactly 13 unique public namespace cards are accepted, with no query-specific card fields.

### Literal attribution

**Given** a question containing a complete title or alias phrase
**When** lexical routing runs
**Then** matching cards are ranked deterministically and substrings do not produce matches.

### Semantic attribution

**Given** the locally cached required model
**When** semantic routing runs with offline controls
**Then** all cards and questions are embedded without network access and ranked by cosine similarity.

### Hybrid comparison

**Given** lexical and semantic namespace rankings
**When** hybrid routing runs
**Then** it applies equal-weight RRF with `RRF_K = 60` and deterministic tie-breaking.

### Honest evidence boundary

**Given** that alternative relevant namespaces and same-query cross-namespace hits are not labeled
**When** the report is rendered
**Then** it reports home-source attribution metrics and limitations without claiming precision, downstream answer quality, or production readiness.

## Explicit exclusions

- production taxonomy or namespace catalog models;
- production registration, synchronization, persistence, CLI, API, or automatic retrieval routing;
- live Turbopuffer reads or writes;
- model downloads or hosted embedding APIs;
- private namespace or production ACL policy evaluation;
- tag output/filter/boost behavior;
- same-query cross-namespace retrieval fusion;
- query decomposition, concepts, relationship extraction, ontology, or graph storage;
- promotion thresholds or a production architecture decision.
