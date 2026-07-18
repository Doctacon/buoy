# Manage the remote namespace catalog

Buoy stores routing cards in the fixed Turbopuffer control-plane namespace `buoy-routing-catalog-v1` in the resolved region. Catalog commands use `TURBOPUFFER_API_KEY`; `--region` overrides `TURBOPUFFER_REGION`. Keys used for list/show need namespace-list and reserved-catalog query permission. Mutations additionally need reserved-catalog write permission. Catalog operations never query, write, or delete target content rows or namespaces.

There is no active local catalog path. `--catalog` and `BUOY_CATALOG_PATH` are not supported or read.

## Inspect remote cards

```bash
uv run buoy catalog list
uv run buoy catalog list "example docs" --all
uv run buoy catalog show site-example-com-v1
uv run buoy catalog show site-example-com-v1 --include-vector --json
```

List reports control-plane, content-live, card, stale, missing, disabled, incompatible, and eligible counts. Missing live namespaces are classified but are not synthesized as cards. Read failures, schema drift, unstable pagination, and missing permissions fail closed. Vectors are redacted unless explicitly included in JSON.

## Create or update a manual card

A manual card requires complete source and retrieval settings; Buoy never infers settings from a namespace ID.

```bash
uv run buoy catalog upsert site-example-com-v1 \
  --source-kind website \
  --source-uri https://example.com/docs \
  --site-id site-example-com \
  --title "Example documentation" \
  --summary "Product and API documentation for Example." \
  --alias "Example docs" --tag docs \
  --region gcp-us-central1 \
  --embedding-model BAAI/bge-small-en-v1.5 \
  --embedding-precision float32 \
  --plan-schema-version 1 \
  --ranking-mode page --ranking-profile none \
  --ranking-pool 20 --ranking-aggregation max
```

Repeat `--alias` and `--tag` as needed. Add `--disabled` to create a disabled card. Upsert uses the exact cached pinned routing model and conditionally writes the remote card; it does not download or substitute a model.

## Enable, disable, or remove

```bash
uv run buoy catalog disable site-example-com-v1
uv run buoy catalog enable site-example-com-v1
uv run buoy catalog remove site-example-com-v1
uv run buoy catalog remove site-example-com-v1 --approve
```

Enable and disable are idempotent. Remove is preview-only without approval. Approved remove verifies the exact remote revision and leaves the target content namespace, rows, and local applied state untouched.

## Migrate a legacy local catalog

```bash
# Authenticated preview: validates source and compares remote state; zero writes
uv run buoy catalog migrate-local --source /absolute/path/catalog.json

# Create only the validated missing remote schema/cards
uv run buoy catalog migrate-local --source /absolute/path/catalog.json --approve
```

`migrate-local` accepts one regular, non-symlink schema-v1 file. Preview lists namespaces and reads remote catalog state, classifying absent, empty, partial, exact, conflicting, or extra state. Approved migration uses conditional writes and two-pass verification. It never changes or deletes the source file. A legacy local catalog is deleted only later by the cutover operator after the reviewed remote cutover and post-integration verification succeed; the command itself never deletes it.

## Recover an interrupted approved apply

Approved apply writes a local integrity-bound pending artifact before content writes, then conditionally commits the remote card. If completion is interrupted, use the exact command printed by apply:

```bash
uv run buoy catalog reconcile --pending <state-root>/catalog-pending/<plan-id>.json
uv run buoy catalog reconcile --pending <pending-path> --rebase --approve
uv run buoy catalog reconcile --pending <pending-path> \
  --accept-remote --approve --expected-remote-revision <revision>
```

Ordinary reconcile retries the original idempotent commit. Approved rebase preserves only safe concurrent manual/enabled changes. `--accept-remote` performs no remote write and requires two stable reads of the operator-supplied revision. Reconcile never replays content; unsafe revision or lineage changes remain conflicts.

Only genuinely unconfirmed, non-promotable pending state may be abandoned:

```bash
uv run buoy catalog abandon-pending --pending <pending-path>
uv run buoy catalog abandon-pending --pending <pending-path> --approve
```

The first command previews removal. Approved abandonment removes only the revalidated pending artifact and performs no remote mutation; confirmed or ledger-promotable state must be reconciled instead.
