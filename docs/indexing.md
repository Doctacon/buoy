# Indexing sources safely

This is the detailed reference for turning a source into a reviewed, incremental turbopuffer index.

## The safety model

Indexing has three gates:

1. `plan` crawls, converts, or reads the source, chunks it, compares it with local state, and writes review artifacts. BigQuery and Snowflake planning authenticate only to the source warehouse; no planning mode reads turbopuffer credentials, loads embeddings, or contacts turbopuffer.
2. `apply --dry-run` verifies the saved artifacts and recomputes the diff without prompting, credentials, models, or API calls.
3. Plain interactive `apply` displays that complete preflight and prompts `Apply this plan? [y/N]`; only exact `y`/`yes` loads the local embedding model and writes reviewed rows. `apply --approve` bypasses the prompt for automation.

Stale rows are retained unless `--delete-stale` is also explicit. Namespace deletion is not part of this workflow.

## Sources

### Websites

```bash
uv run buoy plan https://example.com/
```

Website planning uses Scrapling, stays on the source host, obeys robots.txt, and derives a namespace such as `site-example-com-v1`. Supply website URLs only as a trusted local operator: exact-host crawl containment is enforced, but private-network SSRF blocking is not part of this local CLI.

### Public GitHub repositories

```bash
uv run buoy plan https://github.com/owner/repository
```

Repository URLs are cloned and indexed from git-tracked files rather than rendered GitHub pages. Generated/vendor directories and local agent/run artifacts are excluded by default. The namespace is repository-specific, such as `github-owner-repository-v1`.

Useful repository controls:

```bash
uv run buoy plan https://github.com/owner/repository \
  --include-path 'src/**' \
  --exclude-path 'dist/**' \
  --repo-max-file-bytes 200000 \
  --repo-search-metadata
```

`--repo-file-cards` adds separate searchable file metadata cards; `--repo-oversize-file-cards` adds cards for oversize files skipped during code chunking.

### Local documents

```bash
uv run buoy plan ./research-notes.pdf
```

One local file is converted with MarkItDown. Supported extensions are `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.xls`, `.csv`, `.html`, `.htm`, `.txt`, `.text`, `.md`, `.markdown`, `.json`, `.jsonl`, `.xml`, `.ipynb`, and `.epub`.

PDF namespaces use `pdf-<filename>-<sha16>-v1`; other files use `file-<ext>-<filename>-<sha16>-v1`. Artifacts retain filename, extension, file hash, and a synthetic `pdf://` or `file://` URL—not the absolute source path.

Directories, archives, OCR, image captioning, audio/video transcription, remote file URLs, plugins, and page/slide/sheet/cell-level citations are not supported.

### Database document relations

DuckDB, BigQuery, and Snowflake all consume the same already-shaped document relation. Buoy does **not** run dlt, dbt, SQLMesh, API extraction, or source-system normalization. Any number of normalized upstream tables may feed the final model, but one Buoy command reads exactly one final table or view. Buoy then owns validation, reviewable Markdown materialization, shared chunking, diffing, planning, and the existing apply path.

Install only the remote adapter you need; ordinary Buoy and DuckDB installs do not include either cloud SDK:

```bash
uv sync --extra bigquery
uv sync --extra snowflake
```

Commands:

```bash
# Backward-compatible implicit DuckDB selection
uv run buoy plan ./knowledge.duckdb \
  --relation analytics.documents \
  --source-id product-docs

# Explicit DuckDB is equivalent
uv run buoy plan ./knowledge.duckdb --database-backend duckdb \
  --relation analytics.documents --source-id product-docs

# BigQuery uses Application Default Credentials
uv run buoy plan --database-backend bigquery \
  --relation source-project.corpus.documents \
  --source-id product-docs \
  --bigquery-project billing-project \
  --bigquery-location US \
  --bigquery-maximum-bytes-billed 1000000000 \
  --source-query-timeout 300

# Snowflake uses a named connector connection
uv run buoy plan --database-backend snowflake \
  --relation ANALYTICS.CORPUS.DOCUMENTS \
  --source-id product-docs \
  --snowflake-connection analytics \
  --source-query-timeout 300
```

`crawl` accepts the same backend, relation, mapping, authentication-location, cost, and timeout controls. DuckDB requires its local filepath. BigQuery and Snowflake reject a local source path. `--table` remains an alias for `--relation`. Every database command requires a strict lowercase slug `--source-id` and one relation.

#### Relation and row contract

One row is one **logical document**, not one final vector row. Required columns are `document_id` and `content`; `title` is optional. Use `--id-column`, `--content-column`, or `--title-column` for different ordinary single identifier names. Buoy does not accept expressions or arbitrary SQL.

IDs and content are converted to text. IDs must be globally non-null, nonblank, and unique after conversion. Null or blank content is skipped and counted; a relation with no nonblank content fails. Without an explicit title mapping, Buoy auto-detects `title`; missing, null, or blank titles fall back to the text ID. Rows are selected deterministically by converted ID. Because a cloud relation may change between schema/validation and acquisition statements, BigQuery and Snowflake acquisition filters require both a valid ID and nonblank content, and Buoy defensively revalidates the bounded selected rows before writing Markdown. `--max-pages` caps documents returned to Buoy and `--max-chunks` caps generated chunks; a long logical document may become multiple chunks and vector rows.

A Gong-style upstream transformation can join any number of normalized tables before Buoy reads the one final relation. DuckDB can use `STRING_AGG` and `CHR(10)`:

```sql
CREATE OR REPLACE VIEW corpus.gong_call_documents AS
SELECT
    CAST(c.call_id AS VARCHAR) AS document_id,
    c.title,
    STRING_AGG(
        CONCAT('[', s.start_time_label, '] ', s.speaker_name, ': ', s.transcript_text),
        CHR(10) ORDER BY s.start_seconds
    ) AS content
FROM normalized.gong_calls c
JOIN normalized.gong_transcript_segments s ON c.call_id = s.call_id
GROUP BY c.call_id, c.title;
```

BigQuery expresses the ordered aggregation separately:

```sql
CREATE OR REPLACE VIEW `source-project.corpus.gong_call_documents` AS
SELECT
    CAST(c.call_id AS STRING) AS document_id,
    c.title,
    STRING_AGG(
        CONCAT('[', s.start_time_label, '] ', s.speaker_name, ': ', s.transcript_text),
        '\n' ORDER BY s.start_seconds
    ) AS content
FROM `source-project.normalized.gong_calls` AS c
JOIN `source-project.normalized.gong_transcript_segments` AS s USING (call_id)
GROUP BY c.call_id, c.title;
```

Snowflake uses `LISTAGG ... WITHIN GROUP`:

```sql
CREATE OR REPLACE VIEW CORPUS.GONG_CALL_DOCUMENTS AS
SELECT
    CAST(c.call_id AS VARCHAR) AS document_id,
    c.title,
    LISTAGG(
        CONCAT('[', s.start_time_label, '] ', s.speaker_name, ': ', s.transcript_text),
        CHR(10)
    ) WITHIN GROUP (ORDER BY s.start_seconds) AS content
FROM NORMALIZED.GONG_CALLS AS c
JOIN NORMALIZED.GONG_TRANSCRIPT_SEGMENTS AS s ON c.call_id = s.call_id
GROUP BY c.call_id, c.title;
```

#### Backend safety, authentication, and cost

DuckDB supports one to three ordinary relation components. It opens one read-only connection with external access, extension autoinstall/autoload, and community extensions disabled. Self-contained tables and views over in-database relations work; persisted views that read external files/databases or need extensions do not. Materialize those upstream first.

BigQuery requires `project.dataset.table_or_view`, supports project IDs containing hyphens, inspects tables or views with the official client, and uses its normal Application Default Credentials path. Buoy accepts no credential JSON, tokens, or keys. Buoy combines global counts, one duplicate diagnostic, and bounded ordered documents into one generated read-only source query. It first dry-runs that exact query **without** the provider-side bytes cap, reports the aggregate `bigquery_estimated_bytes_processed`, and compares that estimate with `--bigquery-maximum-bytes-billed`. An over-cap estimate fails with Buoy's estimate-and-cap diagnostic before the actual query is submitted; after preflight passes, the actual job still receives the provider-side maximum-bytes safeguard. Available executed-job diagnostics include total bytes, cache hit, and job ID. `--max-pages` limits returned documents, **not necessarily BigQuery bytes scanned**.

Snowflake requires `database.schema.table_or_view` using the v1 ordinary-identifier subset `[A-Za-z_][A-Za-z0-9_]*`. Lowercase input is canonicalized to Snowflake's normal uppercase resolution behavior; `$` names and quoted case-sensitive identifiers are v1 non-goals. Authentication comes only from `snowflake.connector.connect(connection_name=...)`, so the named profile owns account, user, role, warehouse, password/key/OAuth/SSO settings. Buoy applies a source-specific query tag, deterministically truncating oversized source IDs with a SHA-256 suffix to stay within Snowflake's supported tag length, applies `--source-query-timeout`, fetches bounded batches, and closes/rolls back the read-only connection reliably.

Remote `plan` and `crawl` require source credentials and make source warehouse API calls. They never read turbopuffer credentials, load embeddings, or call/write turbopuffer. Only `plan` and `crawl` connect to any database. After a plan is saved, `apply --dry-run` and approved `apply` consume integrity-verified artifacts only: source file removal, credential removal, profile changes, or relation changes cannot alter the reviewed plan.

#### Stable identity and fixed provenance

For source ID `product-docs` the identities differ only by backend:

| Backend | Base URI | Source/state ID | Default namespace | Document URI |
| --- | --- | --- | --- | --- |
| DuckDB | `duckdb://product-docs` | `duckdb-product-docs` | `duckdb-product-docs-v1` | `duckdb://product-docs/<encoded-id>` |
| BigQuery | `bigquery://product-docs` | `bigquery-product-docs` | `bigquery-product-docs-v1` | `bigquery://product-docs/<encoded-id>` |
| Snowflake | `snowflake://product-docs` | `snowflake-product-docs` | `snowflake-product-docs-v1` | `snowflake://product-docs/<encoded-id>` |

Credentials, credential paths, DuckDB paths, BigQuery billing project/location/job ID, Snowflake connection name/account/user/role/warehouse, physical row order, row counts, and relation contents never affect logical identity or serialize as source configuration. Stable document IDs determine percent-encoded URIs and hash-derived page filenames.

Every new database page, manifest record, chunk, and turbopuffer content row retains the fixed provenance fields `database_backend`, `database_source_id`, `database_relation`, and `database_document_id`. New DuckDB pages also retain legacy `duckdb_*` provenance for compatibility; existing saved DuckDB plans without generic fields remain supported.

V1 excludes arbitrary user SQL, Buoy-configured joins, multiple input relations per command, API/dlt/dbt/SQLMesh orchestration, source-specific Gong/Chorus behavior, arbitrary metadata JSON, dynamic turbopuffer schemas, CDC, watermarks, incremental warehouse predicates, BigQuery Storage API, Snowflake pandas/Arrow ingestion, other databases, credential CLI arguments, custom transcript/speaker chunking, and taxonomy/ontology features.

## Plan artifacts

A plan directory contains:

```text
plan.json
summary.json
manifest.json
chunks.jsonl
pages/*.md
```

Use `summary.json` for counts and samples; `plan.json` for source, namespace, options, diff, and artifact identity; `manifest.json` and `chunks.jsonl` for exact desired rows; and `pages/` for extracted Markdown.

Interactive `plan` and `crawl` commands show one-line stderr progress. `--json`, non-TTY stderr, and `--no-progress` suppress it.

## Shape a website crawl

Defaults favor a useful but conservative first plan:

| Setting | Default |
| --- | --- |
| Discovery | sitemap, then link fallback if empty |
| Website cap | 3,000 pages / 120,000 chunks |
| Concurrency | 2 global / 4 per domain |
| Download delay | 0.25 seconds |
| Docs versions | warn before crawling repeated version families |
| Languages | unprefixed and English when locale families are detected |
| URL variants | strip trailing slash |

Common controls:

```bash
# Keep only docs and remove noisy pages
uv run buoy plan https://example.com/ \
  --include-path '/docs/**' \
  --exclude-path '/blog/**'

# Explicitly select current docs or retain all languages
uv run buoy plan https://example.com/ --docs-version-policy latest
uv run buoy plan https://example.com/ --language-policy all

# Ignore sitemaps, or combine sitemap and link discovery exhaustively
uv run buoy plan https://example.com/ --crawl-strategy link
uv run buoy plan https://example.com/ --crawl-strategy hybrid
```

`--docs-version-policy` also supports `stable-latest`, `latest-nightly`, and `all`. `--keep-trailing-slash` preserves URL variants when required. `--css-selector` can scope extraction to a site's main content wrapper.

See `uv run buoy plan --help` for current caps and all crawl controls.

## Review the preflight

```bash
uv run buoy apply --dry-run
```

By default, apply selects the newest plan under `artifacts/site-crawls/`. Use `--plan <path>` when multiple plans exist. Plain apply requires an interactive stdin; scripts must choose `--dry-run` or `--approve`, and piped input cannot confirm.

Preflight verifies schema, namespace, manifest/chunk agreement, embedding-text hashes, artifact integrity, and compatibility with local state. Because it does not contact Turbopuffer, remote catalog state and the resulting registration action remain unknown until approved. Its text identifies the automatically selected plan path and source, artifact hash, namespace and region, verified embedding model and precision, first-apply state, upsert/embedding/unchanged/stale counts, and an explicit `retain N` or `delete N` stale-row intent.

Use `--region REGION` to override `TURBOPUFFER_REGION` and bind that region into the registered retrieval contract. The remote catalog namespace is fixed as `buoy-routing-catalog-v1`; local catalog path options and `BUOY_CATALOG_PATH` are not supported.

Preflight does not read `TURBOPUFFER_API_KEY`, load an embedding model, mutate the catalog, or contact turbopuffer. It also prints shell-safe preview and live retrieval commands labeled for use after a successful apply; the approved apply repeats them as the next step. Replace the quoted `<query>` placeholder with the question to search while preserving the recorded namespace, region, model, and precision.

## Confirmed apply

After reviewing the plan and preflight, run the normal interactive flow:

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy apply
```

The complete preflight is displayed again before the exact `[y/N]` prompt. Enter, no, arbitrary input, EOF, or prompt failure cancels successfully without writes and retains the plan. For separately authorized non-interactive automation, use `uv run buoy apply --approve`; it never prompts.

If credentials live in this repository's `.env`, load them only into the command subshell:

```bash
(
  set -a
  . ./.env
  set +a
  uv run buoy apply
)
```

Approved apply acquires a fail-fast lock for the target namespace before catalog-card embedding, pending-state creation, credential lookup, or remote work, and retains it through applied-state and catalog commit. It validates and persists a secret-free pending card before remote writes, overlaps one local content-embedding batch with one ordered remote upsert, and commits applied state only after all remote work succeeds. Successful apply then conditionally commits one remote catalog card; manual semantic fields and disabled state are preserved.

It never runs concurrent embeddings or concurrent writes. Interactive runs show confirmed batches/rows on one stderr line; the final summary separates elapsed, embedding, and write time, whose stage totals may exceed wall time because they overlap. Tune the two independent batch controls only after measuring the workload:

```bash
uv run buoy apply --approve \
  --batch-size 128 \
  --embedding-batch-size 32
```

`--batch-size` controls Turbopuffer write batches; `--embedding-batch-size` controls local Sentence Transformers computation. Defaults are 64 and 32 respectively.

Embedding inference defaults to `float32`. Opt into accelerator-only half precision when creating a plan:

```bash
uv run buoy plan https://example.com/ --embedding-precision float16
```

The reviewed plan governs apply precision; ambient retrieval settings cannot override it. Float16 requires CUDA or Apple MPS and fails rather than silently falling back. Changing precision re-embeds affected rows while preserving their row IDs.

## Incremental state and artifact lifetime

Each `(source, namespace)` has an embedded DuckDB ledger:

```text
.buoy/state/<source-id>/<namespace>/state.duckdb
```

It stores current row identity/status plus compact apply summaries, not full snapshots. Existing `.turbo-search` state remains usable without being moved; see [Migrating from turbo-search](migrating-to-buoy.md). Replanning the same source reports new/changed rows to upsert, unchanged rows to skip, and previously applied rows now stale.

A same-namespace approved apply fails fast if another apply holds its lock. Different namespaces have independent ledgers and may apply concurrently. State is local to this machine; it is not a shared service.

Pending, preflighted, and failed plans remain available. Catalog registration pending files live under `<state-root>/catalog-pending/`. Any pending file blocks automatic apply reruns so Buoy cannot unknowingly repeat remote writes after a crash. A successful approved apply removes its pending file and exact plan directory after remote work, state commit, and catalog commit. A newly written verified plan removes older sibling plans for the same namespace. Copy a plan elsewhere before approval if it must be retained for audit.

If remote work and applied state succeed but pending confirmation, remote catalog commit, or pending cleanup fails, apply exits 2 with `remote_apply_succeeded=true`, a retained recoverable pending path, and an exact `buoy catalog reconcile` command. Output reports the phase truthfully: a cleanup-only failure keeps `catalog_updated=true`, includes catalog/card revisions, and sets `pending_cleanup=false`; earlier local failures report `catalog_updated=false`. Do not rerun apply; run the repair command instead. Reconcile can recover an interrupted confirmation only when the exact bound applied-state ledger proves a new matching success. Otherwise an unconfirmed pending file represents indeterminate remote state and can be removed only with the separately reviewed `buoy catalog abandon-pending ... --approve` flow described in the catalog guide.

DuckDB is the only applied-state authority. Obsolete JSON applied-state files are ignored and left unchanged; when no `state.duckdb` exists, apply uses normal first-apply behavior.

## Stale rows

Preview stale deletion locally:

```bash
uv run buoy apply --dry-run --delete-stale
```

Delete only those exact stale row IDs after approval:

```bash
uv run buoy apply --approve --delete-stale
```

This never deletes the namespace.
