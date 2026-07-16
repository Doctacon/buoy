# Manage the local namespace catalog

Buoy keeps namespace routing metadata in a canonical local catalog. Catalog commands are local-only: they do not read `TURBOPUFFER_API_KEY`, contact Turbopuffer, delete remote namespaces, or change applied-state ledgers.

The default catalog is `.buoy/catalog.json`. Existing projects that have only `.turbo-search` continue to use `.turbo-search/catalog.json` with a warning. If both state roots exist, choose a catalog explicitly. Path precedence is:

1. `--catalog PATH`;
2. `BUOY_CATALOG_PATH`;
3. the catalog under the resolved state root.

## Register a namespace manually

A manual card requires complete source and retrieval settings; Buoy does not infer remote settings from the namespace ID.

```bash
uv run buoy catalog upsert site-example-com-v1 \
  --source-kind website \
  --source-uri https://example.com/docs \
  --site-id site-example-com \
  --title "Example documentation" \
  --summary "Product and API documentation for Example." \
  --alias "Example docs" \
  --tag docs \
  --region gcp-us-central1 \
  --embedding-model BAAI/bge-small-en-v1.5 \
  --embedding-precision float32 \
  --plan-schema-version 1 \
  --ranking-mode page \
  --ranking-profile none \
  --ranking-pool 20 \
  --ranking-aggregation max
```

Choose `github_repo`, `website`, or `document` for `--source-kind`. Repeat `--alias` and `--tag` as needed. Add `--disabled` to create a disabled card; updating an existing card otherwise preserves its enabled state.

Upsert builds and persists a 384-dimensional normalized routing vector with the exact cached `BAAI/bge-small-en-v1.5` revision. Model downloads and substitutions are disabled. If that revision is not already available locally, the command fails without changing the catalog and explains how to cache it explicitly.

## Inspect cards

```bash
# Enabled cards only
uv run buoy catalog list

# Include disabled cards and search normalized card text
uv run buoy catalog list "example docs" --all

# Show one card; vectors remain hidden
uv run buoy catalog show site-example-com-v1

# Include the vector only in explicit JSON output
uv run buoy catalog show site-example-com-v1 --include-vector --json
```

List and show do not load the routing model. JSON output keeps stdout machine-readable; state-root warnings and errors go to stderr.

## Enable, disable, or remove

```bash
uv run buoy catalog disable site-example-com-v1
uv run buoy catalog enable site-example-com-v1

# Preview only; exits successfully without mutation
uv run buoy catalog remove site-example-com-v1

# Remove only the local card
uv run buoy catalog remove site-example-com-v1 --approve
```

Enable and disable are idempotent and preserve card semantics and vectors. Remove requires `--approve` to mutate and never deletes Turbopuffer data or applied state.

The catalog is routing metadata, not proof that a remote namespace exists, a remote catalog, an authorization system, or a replacement for explicit namespace selection. Current retrieval continues to require `--namespace` or an explicitly set `TURBOPUFFER_NAMESPACE` environment value.
