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

Choose `github_repo`, `website`, or `document` for `--source-kind`. Repeat `--alias` and `--tag` as needed. Add `--disabled` to create a disabled card; updating an existing card otherwise preserves its enabled state. Apply-generated document cards retain the verified canonical `file://<source-id>` or `pdf://<source-id>` URI. The opaque identifier is never treated as a human filename; PDF titles come only from verified `pdf_filename` metadata.

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

## Repair an interrupted apply registration

Approved apply precomputes a local pending card before remote writes. If remote work and applied-state commit succeed but pending confirmation or catalog commit fails, apply prints an exact local repair command:

```bash
uv run buoy catalog reconcile --pending <state-root>/catalog-pending/<plan-id>.json --catalog <catalog-path>
```

Reconcile validates the artifact hash, trusted path, exact catalog and applied-state bindings, then commits locally under namespace-before-catalog lock order. It reads no credentials, contacts no remote service, and is idempotent when the exact card is already present. An interrupted confirmation is recoverable only when the bound ledger proves a new matching apply identity.

An unconfirmed artifact without that applied-state proof means remote state is indeterminate and blocks apply reruns. Preview local abandonment first, then approve only after accepting that a later apply may repeat idempotent upserts:

```bash
uv run buoy catalog abandon-pending --pending <pending-path> --catalog <catalog-path>
uv run buoy catalog abandon-pending --pending <pending-path> --catalog <catalog-path> --approve
```

Abandonment never changes remote data or applied state and refuses artifacts whose bound ledger proves success.

The catalog is routing metadata, not proof that a remote namespace exists, a remote catalog, an authorization system, or a replacement for explicit namespace selection. Current retrieval continues to require `--namespace` or an explicitly set `TURBOPUFFER_NAMESPACE` environment value.
