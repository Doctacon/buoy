# Index sources locally

This branch stores search content, vectors, and routing cards in DuckDB. Start
with [WSL2/offline setup](local-duckdb.md); models must already be cached.

## Plan, review, apply

```bash
buoy plan ./notes.pdf --namespace work-notes
buoy apply --dry-run
buoy apply --approve
buoy retrieve "What do the notes say?"
```

1. `plan` reads/converts a source, chunks it, compares it with applied state, and
   saves integrity-checked review artifacts. It does not load an embedding model
   or write the search index.
2. `apply --dry-run` verifies artifacts and recomputes the diff without model
   loading or index writes.
3. Interactive `apply` asks `Apply this plan? [y/N]`. Only `y`/`yes` proceeds;
   `--approve` is the explicit automation equivalent.
4. Approved apply embeds locally, writes reviewed changes to DuckDB, commits the
   incremental baseline, then registers the namespace's routing card locally.

Stale rows remain searchable until explicitly deleted with `--delete-stale`.
No command in this workflow deletes a namespace. Multiple pending plans require
`apply --plan /absolute/path/to/plan.json`; Buoy does not guess which one you meant.

## Local storage

All defaults share `BUOY_HOME` (default `~/.buoy-local`):

| Data | Location relative to BUOY_HOME |
| --- | --- |
| Content, vectors, keyword postings and routing catalog | `search.duckdb` |
| Per-source/namespace applied state | `state/<source-id>/<namespace>/state.duckdb` |
| Crawl/plan artifacts | `artifacts/site-crawls/` |
| Model-worker socket/state | Private worker directory |
| Optional telemetry | `telemetry/` |

A successful plan retains exactly `plan.json` and `delta.duckdb`. The plan binds
source identity, chunk counts, embedding contract, routing passages, and the exact
applied-state baseline. Never edit the files to bypass verification.

`--out-dir`, `--plan`, and `--state-root` remain explicit overrides. They do not
redirect the search database. Prefer setting BUOY_HOME to keep all parts together.
**Do not reuse a cloud-era state root**: it would claim content has already been
written to a different backend. See [migration](migrating-to-buoy.md).

## Local documents

```bash
buoy plan ./research-notes.md --namespace research
buoy plan ./quarterly-report.pdf --namespace reports
```

Supported single-file extensions: `.pdf`, `.docx`, `.pptx`, `.xlsx`, `.xls`, `.csv`,
`.html`, `.htm`, `.txt`, `.text`, `.md`, `.markdown`, `.json`, `.jsonl`, `.xml`,
`.ipynb`, `.epub`. MarkItDown converts locally with plugins disabled. There is no
OCR, image captioning, transcription, or remote conversion service.

Single-file default identities include the filename and file hash. For stable
incremental document collections, use stable IDs in a DuckDB relation or the
folder helper below. Citations use synthetic document URIs, not uploaded files.

## Local folders / code checkouts

```bash
python scripts/import_local_directory.py ./checkout ./source-docs.duckdb
buoy plan ./source-docs.duckdb --relation documents --source-id work-code
buoy apply --approve
```

The output database must be outside the input folder. The helper skips symlinks,
hidden/generated folders, common secret files, oversized and non-UTF-8/binary
files. It preserves relative paths as document IDs. Use `--include`, `--exclude`,
`--max-files`, and `--max-file-bytes` to restrict input; review its summary.

Rerun with `--replace` after changes, then plan/apply using the same source ID.
This path uses ordinary document chunking, not the optional GitHub syntax/file
card experiments. It never contacts GitHub or executes repository code.

## Prepared DuckDB document relations

```bash
buoy plan ./knowledge.duckdb --relation analytics.documents --source-id product-docs
# Explicit backend is equivalent:
buoy plan ./knowledge.duckdb --database-backend duckdb \
  --relation analytics.documents --source-id product-docs
```

One row represents one logical document. Required columns are `document_id` and
`content`; `title` is optional. Use `--id-column`, `--content-column`, or
`--title-column` to map different ordinary column names. IDs must be non-null,
nonblank, and unique after text conversion. Empty content is skipped. Rows are
read deterministically; `--max-pages` caps documents and `--max-chunks` caps chunks.

Buoy does not perform upstream ETL, joins, API extraction, or model your source
systems. Prepare a table or view first. Source DuckDB files open read-only with
external access and extension loading disabled. Views over internal tables work;
views depending on external files or remote databases must be materialized first.
The source relation database is distinct from Buoy's search database.

## Optional connected source acquisition

Network acquisition is disabled by default. Only on an approved connected machine:

```bash
BUOY_ALLOW_NETWORK=1 buoy plan https://example.com/
BUOY_ALLOW_NETWORK=1 buoy plan https://github.com/owner/repository \
  --include-path 'src/**' --exclude-path 'dist/**'
```

Web crawling stays on the exact host and obeys robots.txt. Website URLs must be
trusted operator inputs; the crawler is not a private-network SSRF firewall.
GitHub acquisition indexes git-tracked regular files, skipping symlinks, submodules,
generated/vendor paths, and oversized files. Existing repository chunking and
file-card flags remain available via `plan --help`. No remote vector storage is
used even during an approved connected source import.

The optional `bigquery` and `snowflake` extras retain read-only warehouse source
adapters. Install only on a connected staging machine if needed:

```bash
uv sync --extra bigquery
BUOY_ALLOW_NETWORK=1 buoy plan --database-backend bigquery \
  --relation project.dataset.documents --source-id product-docs \
  --bigquery-project billing-project --bigquery-location US \
  --bigquery-maximum-bytes-billed 1000000000

uv sync --extra snowflake
BUOY_ALLOW_NETWORK=1 buoy plan --database-backend snowflake \
  --relation ANALYTICS.CORPUS.DOCUMENTS --source-id product-docs \
  --snowflake-connection analytics --source-query-timeout 300
```

Cloud source authentication is unchanged: BigQuery uses Application Default
Credentials; Snowflake uses a named connector connection. Credentials are not
plan content. Once saved, apply consumes verified artifacts only and does not
reconnect to the source. Do not enable these adapters on the restricted laptop.

## Incremental updates, failures, and safety

Approved apply rechecks the exact baseline under a namespace lock. Embedding one
batch can overlap the previous batch's write, but model inference and writes are
individually serial. DuckDB storage operations use transactions and a database
file lock across threads/processes. Default batches are 32 embeddings / 64 writes;
reduce `--embedding-batch-size` on a constrained machine.

The plan's precision governs apply. Float32 is the CPU default. Float16 requires
an explicitly selected CUDA/MPS device and does not silently run on CPU. Keep the
same model and precision when retrieving; changing embedding contracts requires
reindexing, not just changing an environment variable.

Rows and exact-ID deletes are deterministic. Applied state is committed only
after successful content work. A failed batch can leave earlier batches written
but not advance state; the verified unchanged plan is safe to inspect/retry.
Content, applied state and routing cards are **not one cross-database transaction**.

The first approved local apply creates the schema-v3 routing catalog. Later apply
preserves manual card descriptions, aliases, tags, reviewed examples, and enabled
state while refreshing lineage and source-derived passages. No generative model
creates routing questions.

If catalog registration fails after content/state commit, the command reports
`partial_success`, retains the plan, and supplies a bounded repair command.
Follow its `catalog repair-apply --inspect-current`/revision instructions. Do not
replay an ordinary apply whose baseline has already advanced. Successful apply
cleans its plan only after card verification; cleanup errors warn without
claiming the content write failed. There is no background reconciliation daemon.

A new verified plan may clean older verified sibling plans for the same namespace.
Copy review artifacts separately before approval if your audit policy requires
long-term retention. Back up the entire BUOY_HOME while idle, not the search file
alone. Never replace/delete just `search.duckdb` while retaining its incremental
baseline; rebuild in a fresh BUOY_HOME instead.

```bash
buoy apply --dry-run --delete-stale
buoy apply --approve --delete-stale
```

Only the reviewed exact stale row IDs are removed. Catalog disable/enable affects
routing, not content; see [retrieval and catalog operations](retrieval.md).
