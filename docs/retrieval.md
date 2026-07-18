# Retrieve and rank results

Without CLI `--namespace`, retrieval uses authenticated automatic remote routing by default. Buoy lists live Turbopuffer namespaces, reads the fixed remote catalog `buoy-routing-catalog-v1`, intersects valid cards with live content namespaces, and routes only across eligible cards. `TURBOPUFFER_NAMESPACE` is ignored for retrieval.

Repeatable CLI `--namespace` is the sole bypass: it skips namespace discovery, remote catalog reads, and routing-model work. An explicit namespace preview remains credential-free and local. Live content search additionally requires `--live` and `TURBOPUFFER_API_KEY`.

## Discover namespace IDs

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy namespaces
uv run buoy namespaces docs
```

Use `--region` to override `TURBOPUFFER_REGION`, and `--json` for structured output. Discovery is read-only and filters identifiers only; it does not inspect namespace contents.

## Automatic remote routing

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy retrieve "How is this feature implemented?"
uv run buoy retrieve "How is this feature implemented?" --route-top-k 2
uv run buoy retrieve "How is this feature implemented?" --route-top-k 2 --live
```

The first two commands are read-only remote previews and make no content-namespace queries. `--auto-route` remains accepted as a compatibility no-op: automatic routing is already the default when no CLI namespace is supplied. It is contradictory with `--namespace`. `--route-top-k` works directly in automatic mode (default 3, maximum 10).

Automatic preview requires credentials and makes read-only namespace-list and remote-catalog calls. Output identifies the catalog namespace and snapshot revision, live/card/eligible/missing/stale/incompatible counts, selected card scores, and each retrieval plan. Cards provide their own region/model/precision and ranking contracts; invalid schema, unstable reads, missing permissions, or zero eligible cards fail closed. Namespace IDs never become fallback descriptions.

The router combines normalized exact title/alias/tag phrase matching with cosine similarity over persisted card vectors using equal-weight reciprocal-rank fusion. It loads the exact cached pinned routing model only after a valid eligible remote card exists. It never repairs remote state, downloads a model, falls back to all visible namespaces, or uses `TURBOPUFFER_NAMESPACE`.

## Explicit namespace preview and live retrieval

```bash
# Local, credential-free plan: no namespace listing, catalog call, or model load.
uv run buoy retrieve "How does this feature work?" --namespace site-example-com-v1

# Explicit live query; repeat --namespace as needed.
export TURBOPUFFER_API_KEY="..."
uv run buoy retrieve \
  "How does this feature work?" \
  --namespace site-product-docs-v1 \
  --namespace github-owner-product-v1 \
  --live --top-k 5
```

Explicit namespaces retain their supplied order. Buoy embeds once, queries each selected namespace sequentially with the same explicitly resolved region/model/precision, and merges namespace-local rankings with equal-weight reciprocal-rank fusion. If any selected namespace fails, no partial result set is printed. Every result identifies its source namespace.

Runtime configuration uses `TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, `BUOY_EMBEDDING_MODEL`, and `BUOY_EMBEDDING_PRECISION`. `TURBOPUFFER_NAMESPACE` is intentionally ignored; use repeatable `--namespace` for an explicit bypass. Precision defaults to `float32`; use `float16` only on CUDA or Apple MPS.

## Hybrid retrieval and ranking

Each live namespace query produces an ANN subquery over the normalized local BGE query vector and a BM25 full-text subquery, then fuses them with reciprocal-rank fusion. `--candidates` controls each subquery pool and `--top-k` controls final results. `--doc-kind` filters result categories.

Website and document cards normally use page grouping with `none` profile, pool 20, and `max` aggregation. Repository cards normally use file grouping with `repo-code` profile, pool 100, and `adaptive-sum-3`. Automatic routing uses each card's recorded values; explicit ranking flags override the corresponding field across selected cards. Compare changes with a fixed eval dataset; see [Evaluate search quality](evaluation.md).
