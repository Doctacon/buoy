# Single-namespace retrieval

Buoy searches exactly one explicitly named Turbopuffer namespace.

```bash
# Local preview: no credentials, model load, or provider call.
buoy retrieve "How are retries configured?" \
  --namespace github-example-service-v1 \
  --dry-run

# Live retrieval.
export TURBOPUFFER_API_KEY=...
buoy retrieve "How are retries configured?" \
  --namespace github-example-service-v1
```

`--plan` is an alias for `--dry-run`. The old no-op `--live`, automatic routing,
repeatable namespace, and route-limit options are not supported.

The runtime reads:

- `TURBOPUFFER_API_KEY` only for live work;
- `TURBOPUFFER_REGION`, defaulting to `gcp-us-central1`;
- `BUOY_EMBEDDING_MODEL`;
- `BUOY_EMBEDDING_PRECISION`.

`TURBOPUFFER_NAMESPACE` is ignored. Use singular `--namespace` so the target is
visible in commands, logs, and review.

## Search and ranking

Each query uses ANN over the configured embedding and boosted BM25 over title,
section path, and content, then reciprocal-rank fusion. Final grouping/ranking
uses source-aware defaults:

- websites, local documents, and database relations: page mode, no repository
  profile, pool 20, max aggregation;
- repositories: file mode, `repo-code` profile, pool 100,
  `adaptive-sum-3` aggregation.

Approved apply prints exact retrieval commands containing the source-derived
ranking flags. Preserve those flags when a source uses a custom namespace that
does not reveal its source kind.

Overrides are explicit:

```bash
buoy retrieve "customer cancellation reason" \
  --namespace customer-conversations \
  --ranking-mode page \
  --ranking-profile none \
  --ranking-pool 20 \
  --ranking-aggregation max
```

`--doc-kind` applies one exact metadata filter. Tags remain output metadata,
not routing or filtering authority.

## Results

Every result retains its source URL/path, title, section, content preview,
stable row identity, score diagnostics, and ordered tags. Buoy does not attach
a per-hit namespace because the one namespace is already the result-set
identity.

Cross-namespace selection, routing, and fusion are Kite responsibilities.

## Evaluation

Evaluation also requires an explicit namespace:

```bash
buoy evals --namespace site-example-docs-v1 --dry-run
buoy evals --namespace site-example-docs-v1 --live
```

Dry-run lists the cases without credentials. `--live` is meaningful for
`evals`: it executes the listed cases against the selected namespace.
