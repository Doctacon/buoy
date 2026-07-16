# Retrieve and rank results

Retrieval is a safe dry run by default. Choose namespaces explicitly with `--namespace`/`TURBOPUFFER_NAMESPACE`, or opt into the canonical local catalog with `--auto-route`; Buoy never falls back to a demo namespace or silently searches every remote namespace. Live search additionally requires `--live` and `TURBOPUFFER_API_KEY`.

## Discover namespace IDs

List every namespace ID visible to the configured account and region:

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy namespaces
```

Filter IDs case-insensitively before choosing a retrieval target:

```bash
uv run buoy namespaces dagster
```

Use `--region` to override `TURBOPUFFER_REGION`, and `--json` for structured output. Discovery is read-only and searches namespace identifiers only; it does not embed text or inspect namespace contents.

## Preview a query

```bash
uv run buoy retrieve \
  "How does this feature work?" \
  --namespace site-example-com-v1
```

The preview shows the namespace, embedding model, generated ANN/BM25 subqueries, candidate count, fusion strategy, and final ranking settings. It does not load the model or contact turbopuffer.

## Run live retrieval

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy retrieve \
  "How does this feature work?" \
  --live \
  --namespace site-example-com-v1 \
  --top-k 5
```

Runtime defaults can come from the environment:

```text
TURBOPUFFER_REGION
TURBOPUFFER_NAMESPACE
BUOY_EMBEDDING_MODEL
BUOY_EMBEDDING_PRECISION
```

Use `--region`, `--namespace`, `--embedding-model`, or `--embedding-precision` for one command. Precision defaults to `float32`; set `float16` only on CUDA or Apple MPS. Query embedding should use the model and precision recorded by the namespace's indexing plan because Buoy cannot infer that remote configuration.

Live results include the source title, URL, section, content, score information, document kind, tags, and repository path when available. Use those source URLs and titles as citations rather than presenting retrieved text without provenance.

## Search multiple namespaces

Discover IDs, then repeat `--namespace` to select an explicit set:

```bash
uv run buoy namespaces docs
uv run buoy retrieve \
  "How does this feature work?" \
  --namespace site-product-docs-v1 \
  --namespace github-owner-product-v1 \
  --live \
  --top-k 5
```

CLI namespace selections replace `TURBOPUFFER_NAMESPACE` and retain their supplied order. Buoy normalizes and embeds the query once, queries each namespace sequentially with the same region/model/precision, then merges the namespace-local rankings using equal-weight reciprocal-rank fusion. `--top-k` limits the final merged list, and every result identifies its source namespace.

If any selected namespace fails, the command fails without printing a partial result set. Explicit retrieval does not load or validate the local catalog. This first version does not automatically search every visible namespace, infer per-namespace model settings, or mix different model/precision settings in one command.

## Route from the local catalog

Automatic routing is explicit and local-first:

```bash
# Preview the default top-three route locally.
uv run buoy retrieve "How is this feature implemented?" --auto-route

# Query at most two selected namespaces after the local route succeeds.
export TURBOPUFFER_API_KEY="..."
uv run buoy retrieve "How is this feature implemented?" \
  --auto-route --route-top-k 2 --live
```

The router fully validates the canonical local catalog, excludes disabled cards and cards incompatible with the resolved region/model/precision, then combines exact normalized title/alias/tag phrase matches with cosine similarity over persisted card vectors using equal-weight RRF. It uses the pinned `BAAI/bge-small-en-v1.5` routing model revision with local files only; retrieval never repairs cards, re-embeds them, downloads a model, discovers remote namespaces, or substitutes lexical-only routing.

A routed dry preview loads that pinned local model but reads no Turbopuffer credential, constructs no SDK client, makes no remote call, and mutates no catalog/state. Output includes the catalog revision, eligibility counts, ordered selected cards, route ranks/scores, and each namespace's retrieval plan without card vectors. A missing model or no enabled compatible card fails closed with an explicit manual-retrieval/catalog-repair path.

Catalog path precedence is `--catalog PATH`, then non-empty `BUOY_CATALOG_PATH`, then the catalog under Buoy's resolved state root. `--catalog` and `--route-top-k` require `--auto-route`; `--auto-route` is mutually exclusive with CLI `--namespace`. If `TURBOPUFFER_NAMESPACE` is set, `--auto-route` replaces it and warns on stderr so JSON stdout remains valid.

Each routed card supplies its own ranking mode/profile/pool/aggregation. Any explicitly supplied `--ranking-mode`, `--ranking-profile`, `--ranking-pool`, or `--ranking-aggregation` overrides only that field across selected cards. `--candidates` and `--doc-kind` apply to every selected namespace; `--top-k` limits the final namespace-qualified cross-namespace RRF result. Routed output keeps an explicit multi-namespace shape even when one card is selected, and any selected namespace failure emits no partial result payload.

## Hybrid retrieval

Each query produces:

1. an ANN subquery over the normalized local BGE vector;
2. a BM25 full-text subquery;
3. reciprocal-rank fusion (server-side when supported, otherwise client-side);
4. namespace-aware grouping and final ranking.

Use `--candidates` to change each subquery's candidate pool and `--top-k` to change returned results. `--doc-kind` filters categories such as `blog`, `library`, `platform`, or `integrations`.

## Namespace-aware ranking

### Websites and documents

`site-*`, `pdf-*`, and `file-*` namespaces default to:

```text
--ranking-mode page
--ranking-profile none
--ranking-pool 20
--ranking-aggregation max
```

Chunks from the same page/document are grouped and the strongest chunk represents the source. This keeps one heavily chunked page from occupying the result list.

### GitHub repositories

Repository namespaces default to:

```text
--ranking-mode file
--ranking-profile repo-code
--ranking-pool 100
--ranking-aggregation adaptive-sum-3
```

Results are grouped by `repo_path`. The best chunk provides the base score and close supporting chunks add a small capped bonus. The `repo-code` profile gently demotes process artifacts, generated run memory, general docs, Markdown, and eval fixtures; lightly boosts tests; applies conservative exact path/symbol matches; and may add one strong documentation or test companion to the top five without replacing the top implementation result.

## Ranking controls

Use strict best-chunk grouping:

```bash
uv run buoy retrieve "query" \
  --namespace github-owner-repository-v1 \
  --ranking-aggregation max
```

Fully reward up to three matching chunks per file/page:

```bash
uv run buoy retrieve "query" \
  --namespace github-owner-repository-v1 \
  --ranking-aggregation capped-sum-3
```

Inspect raw fused chunk order:

```bash
uv run buoy retrieve "query" \
  --namespace github-owner-repository-v1 \
  --ranking-mode chunk \
  --ranking-profile none
```

Ranking changes are easiest to compare with a fixed eval dataset; see [Evaluate search quality](evaluation.md).
