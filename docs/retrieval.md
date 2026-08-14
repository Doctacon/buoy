# Automatic and explicit retrieval

`buoy retrieve QUERY` automatically chooses the relevant indexed corpora. The
router reads the live Turbopuffer namespace inventory and the validated cards
in `buoy-routing-catalog-v1`, then searches at most three content namespaces.

```bash
export TURBOPUFFER_API_KEY=...

# Inspect the automatic route. This reads routing state but not content.
buoy retrieve "How is approximate vector recall evaluated?" --dry-run

# Run the selected retrieval.
buoy retrieve "How is approximate vector recall evaluated?"
```

`--plan` is an alias for `--dry-run`. Buoy reads credentials only from the
process environment and does not load `.env` automatically. If a local `.env`
is the intended credential source, load it explicitly into the command
subshell:

```bash
(
  set -a
  . ./.env
  set +a
  buoy retrieve "How is approximate vector recall evaluated?"
)
```

The runtime also reads `TURBOPUFFER_REGION` (default
`gcp-us-central1`), `BUOY_EMBEDDING_MODEL`, and
`BUOY_EMBEDDING_PRECISION`. `TURBOPUFFER_NAMESPACE` is ignored.

## Automatic routing

Automatic routing is intentionally bounded. Before it scores the question,
Buoy requires one valid card for every live content namespace. Reserved control
namespaces such as `buoy-routing-catalog-v1` and `buoy-evidence-*` are never
content candidates. Stale cards, missing cards, incompatible cards, and
disabled cards are reported; incomplete or corrupt coverage fails before any
content query.

Selection first looks for complete normalized titles or aliases in the
question:

- one named corpus selects that corpus;
- two or three named corpora select all of them in deterministic order;
- more than three named corpora fails with guidance to use explicit selection;
- otherwise a pinned local semantic router selects one corpus only when the
  top result clears both the confidence and margin thresholds;
- an ambiguous semantic route selects the top three, or every eligible corpus
  when fewer than three exist.

Automatic `--dry-run` requires `TURBOPUFFER_API_KEY` because live inventory and
catalog reads are routing authority. It performs those read-only requests and
one local route embedding, then reports selected cards, confidence, coverage,
and expected fanout. It does not embed the content query, query a content
namespace, or write provider state.

## Explicit override

Supply `--namespace` to bypass namespace listing, catalog reads, and route-model
work. Repeat it to search a known set of two or three namespaces:

```bash
# Local, provider-free preview of one known namespace.
buoy retrieve "How are retries configured?" \
  --namespace github-example-service-v1 \
  --dry-run

# Explicit multi-corpus retrieval.
export TURBOPUFFER_API_KEY=...
buoy retrieve "Compare retry and deployment guidance" \
  --namespace github-example-service-v1 \
  --namespace site-example-docs-v1
```

Explicit namespaces must be unique and may be repeated at most three times. A
single explicit namespace preserves the established text and JSON result
contract. An explicit preview is local, credential-free, and provider-free.

## Search, widening, and reranking

The content query is embedded once. Each selected namespace runs ANN plus
boosted BM25 over title, section path, and content, then performs
within-namespace reciprocal-rank fusion and the source-aware file/page ranking
already used by single-namespace retrieval.

Source-aware defaults remain:

- websites, local documents, and database relations: page mode, no repository
  profile, pool 20, max aggregation;
- repositories: file mode, `repo-code` profile, pool 100,
  `adaptive-sum-3` aggregation.

A confident one-corpus route queries only that corpus and does not load the
cross-corpus reranker. If it is empty or fails, Buoy widens once to the next two
route candidates. A route that starts with two or three corpora queries them
concurrently, with at most three workers.

For a true multi-corpus result, each successful namespace contributes at most
eight hits. Buoy collapses exact citation/section/content duplicates, retains
at most 24 candidates, and gives each candidate a local MiniLM rank. The final
order uses fixed equal-weight reciprocal-rank fusion (`k=60`) of that MiniLM
rank and the candidate's existing namespace-local rank. Raw provider scores
and corpus-route scores are never mixed across namespaces. This keeps strong
local evidence from being erased while still letting the cross-encoder compare
the combined candidate set. The requested `--top-k` is the final global limit.
When that limit has room for every nonempty selected corpus, Buoy also retains
the existing local-rank-one hit from each corpus. If this safety rail replaces
a lower global result, JSON reports the promoted namespace; if `top_k` is too
small to represent every corpus, JSON reports that coverage was impossible.
Reranker load or inference failure fails the multi-corpus request rather than
returning an arbitrary cross-corpus order.

The exact model is `cross-encoder/ms-marco-MiniLM-L-6-v2` at immutable revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`. Loading is CPU-only,
`local_files_only`, safetensors-only, and remote code is disabled. Retrieval
does not download a model or accept an unpinned substitute. The snapshot is
about 88 MB. With the routing model already resident, a measured 24-candidate
run on the development Mac took about 0.58 seconds and added about 151 MiB of
peak working memory using the fixed batch size of eight. It is already present
in the development environment. If that exact snapshot is not
in the Hugging Face cache, the request fails before querying the widened
namespaces and explains which revision must be cached.

Overrides remain explicit:

```bash
buoy retrieve "customer cancellation reason" \
  --namespace customer-conversations \
  --ranking-mode page \
  --ranking-profile none \
  --ranking-pool 20 \
  --ranking-aggregation max
```

`--doc-kind` applies one exact metadata filter. Tags remain output and routing
card metadata, not retrieval-filter authority.

## Results and failures

Every result retains its source URL/path, title, section, content preview,
stable row identity, score diagnostics, and ordered tags. Automatic and
explicit multi-corpus JSON also report selected `namespaces`, routing and
reranking details, per-hit `namespace`, per-namespace summaries, and failures.

One selected namespace failing does not discard successful results. Buoy
redacts and attributes the failed namespace and marks the combined response
`incomplete`. If every attempted namespace fails, the command fails. An empty
namespace is not itself a provider failure; it contributes no candidates, and
the one-corpus automatic path still performs its single widening attempt.

## Catalog inspection and management

Catalog reads and mutations require `TURBOPUFFER_API_KEY` because
`buoy-routing-catalog-v1` is remote authority:

```bash
buoy catalog list
buoy catalog list --all
buoy catalog show site-example-docs-v1

# Preview, then approve the same enablement change.
buoy catalog disable site-example-docs-v1
buoy catalog disable site-example-docs-v1 --approve
buoy catalog enable site-example-docs-v1
buoy catalog enable site-example-docs-v1 --approve
```

`catalog upsert` creates or replaces one complete manual card; use
`buoy catalog upsert --help` for its required source, embedding, and ranking
fields. `upsert`, `enable`, and `disable` are previews unless `--approve` is
present. They modify routing cards only. They never delete, enable, disable, or
otherwise mutate a content namespace.

## Evaluation

The ordinary `buoy evals` command still evaluates one explicitly named corpus:

```bash
buoy evals --namespace site-example-docs-v1 --dry-run
buoy evals --namespace site-example-docs-v1 --live
```

The automatic-routing release gate is a separate governed 50-query basket:
20 named-source questions, 15 descriptor-free/confusable questions, 10
multi-corpus questions, and 5 no-answer questions. Its checked-in labels remain
marked candidate until a human approves them against current indexed content.
Provider-backed scoring is read-only and compares automatic results with an
exhaustive search of all four eligible logical corpora; the disabled duplicate
Dagster namespace is covered by a card but never earns route or retrieval
credit.
