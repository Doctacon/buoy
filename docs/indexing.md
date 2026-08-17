# Indexing sources safely

This is the detailed reference for turning a source into a reviewed, incremental turbopuffer index.

## The safety model

Indexing has three gates:

1. `plan` crawls, converts, or reads the source, chunks it, compares it with local state, and writes review artifacts. BigQuery and Snowflake planning authenticate only to the source warehouse; no planning mode reads turbopuffer credentials, loads embeddings, or contacts turbopuffer.
2. `apply --dry-run` verifies the saved artifacts and recomputes the diff without prompting, credentials, models, or API calls.
3. Plain interactive `apply` displays that complete preflight and prompts `Apply this plan? [y/N]`; only exact `y`/`yes` loads the local embedding model, writes reviewed rows, commits local state, and then registers the namespace's routing card. `apply --approve` bypasses the prompt for automation.

Stale rows are retained unless `--delete-stale` is also explicit. Namespace deletion is not part of this workflow.

## Default local storage

Buoy resolves its implicit local paths from the operating-system user's home,
not from the current working directory:

| Data | Implicit location |
| --- | --- |
| Applied state | `~/.buoy/state/<source-id>/<namespace>/state.duckdb` |
| Crawl and plan artifacts | `~/.buoy/artifacts/site-crawls/` |
| `apply` plan discovery | The same artifact root, only when it contains exactly one supported pending plan |

Source-specific directories beneath the artifact root remain deterministic.
`crawl` retains its normal crawl leaf, while every default plan leaf ends in
`-plan` (including database-relation plans) so the two outputs cannot collide.
A successful schema-v3 `plan` retains exactly `plan.json` and `delta.duckdb`
in its plan directory.

The existing `--state-root`, `--out-dir`, and `--plan` options remain explicit
overrides. They do not redirect one another, so a plan written to a custom
`--out-dir` must later be selected with `--plan`. For example, a supported plan
and DuckDB ledger already kept in a project can still be selected explicitly:

```bash
uv run buoy apply \
  --plan /path/to/project/artifacts/site-crawls/example-plan/plan.json \
  --state-root /path/to/project/.buoy \
  --dry-run
```

Omitting those options does not inspect a noncanonical current-directory
`.buoy`, legacy `.turbo-search`, or `artifacts/site-crawls`. Buoy does not
implicitly copy, move, merge, backfill, or delete any existing files. If
continuity with an old ledger matters, use its explicit `--state-root` for both
planning and apply; otherwise the user-global ledger begins with normal
first-apply semantics. Explicitly selected state and plans retain normal state
writes and verified success-only plan cleanup.

This layout governs Buoy-owned applied state and crawl/plan artifacts only.
Package and model caches owned by `uv`, Hugging Face, or Sentence Transformers
keep their normal cache locations.

Compatibility note: several option descriptions in `buoy ... --help` still
name the former current-directory defaults. Automatic routing binds the exact
CLI module bytes as an active safety receipt, so this path-only change does not
silently rewrite that receipt. The runtime defaults and explicit behavior in
this section are current; updating those embedded help strings requires a
separate routing recertification.

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

Repository acquisition opens only git-tracked regular files from the cloned
checkout. Symbolic and other link entries, submodules, and special filesystem
entries are skipped even when they match an explicit `--include-path`. Path
filters choose among eligible regular files; they never override this boundary.

Reads are size-bounded. Files above `--repo-max-file-bytes` do not enter normal
content chunking, and optional oversize file cards read only a bounded prefix
for metadata. Buoy does not follow an in-repository entry to read another path.

Useful repository controls:

```bash
uv run buoy plan https://github.com/owner/repository \
  --include-path 'src/**' \
  --exclude-path 'dist/**' \
  --repo-max-file-bytes 200000 \
  --repo-search-metadata
```

`--repo-file-cards` adds separate searchable file metadata cards; `--repo-oversize-file-cards` adds cards for oversize files skipped during code chunking.

After upgrading, a new plan may report stale rows that an earlier version
derived through a link entry. Stale rows remain retained by default. Review the
dry-run preflight and use `--delete-stale` only when an approved apply should
explicitly delete those exact stale IDs.

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

Every new database delta row and turbopuffer content row retains the fixed provenance fields `database_backend`, `database_source_id`, `database_relation`, and `database_document_id`. New DuckDB rows also retain legacy `duckdb_*` provenance for compatibility.

V1 excludes arbitrary user SQL, Buoy-configured joins, multiple input relations per command, API/dlt/dbt/SQLMesh orchestration, source-specific Gong/Chorus behavior, arbitrary metadata JSON, dynamic turbopuffer schemas, CDC, watermarks, incremental warehouse predicates, BigQuery Storage API, Snowflake pandas/Arrow ingestion, other databases, credential CLI arguments, custom transcript/speaker chunking, and taxonomy/ontology features.

## Plan artifacts

A successful schema-v3 plan directory contains exactly:

```text
plan.json
delta.duckdb
```

Without `--out-dir`, that directory is created beneath
`~/.buoy/artifacts/site-crawls/`, regardless of the shell's current working
directory.

`plan.json` is bounded metadata: source and namespace identity, options, diff
counts, the applied-state baseline hash, routing-passage counts, delta counts,
and artifact identity. `delta.duckdb` contains exact
changed/new/reactivated rows, stale identities, and at most eight representative
routing passages selected deterministically from the complete desired corpus.
Those passages are real source excerpts with provenance, not LLM-generated
questions. The rest of unchanged content and all source staging are not
retained. Older plan schemas remain inert: current discovery ignores them,
explicit apply rejects them, and Buoy does not automatically delete them.

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

By default, apply searches `~/.buoy/artifacts/site-crawls/` and proceeds only
when exactly one supported pending plan exists there. Zero or multiple plans
fail without choosing one; use `--plan <path>` to select the intended plan.
Implicit discovery never searches the current directory. Plain apply requires
an interactive stdin; scripts must choose `--dry-run` or `--approve`, and
piped input cannot confirm.

Preflight fully verifies the schema-v3 metadata and delta, row identities,
embedding-text hashes, routing-passage text and provenance, artifact integrity,
and exact applied-state baseline. If applied state changed after planning,
apply fails with replanning guidance before credentials, models, provider
calls, or writes. Its text identifies the selected plan path and source,
artifact hash, namespace and region, verified embedding model and precision,
first-apply state, routing-passage count, upsert/embedding/unchanged/stale
counts, and an explicit `retain N` or `delete N` stale-row intent.

Use `--region REGION` to override `TURBOPUFFER_REGION` and bind that region into
the retrieval handoff and approved apply receipt.

Preflight does not read `TURBOPUFFER_API_KEY`, load an embedding model, list
namespaces, or contact Turbopuffer. It prints shell-safe preview and live
retrieval commands labeled for use after a successful apply; the approved
apply repeats them as the next step. Replace the quoted `<query>` placeholder
while preserving the namespace, region, model, precision, and ranking flags.

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

Approved apply acquires a fail-fast lock for the target namespace before
credential lookup or remote work, reverifies the plan and exact baseline under
that lock, overlaps one local content-embedding batch with one ordered remote
upsert, performs only explicitly requested exact-ID stale deletion, and commits
local applied state only after content work succeeds. It then attempts to
create or refresh exactly that namespace's card in
`buoy-routing-catalog-v1`. It does not alter any other content namespace.

The card records source, embedding, ranking, lineage, and a pinned routing
projection. When a manual card already exists, approved apply preserves its
title, summary, aliases, tags, semantic vector, and enabled/disabled state
while refreshing system lineage and compatibility fields. Preflight describes
the intended post-commit registration without listing namespaces, reading the
remote catalog, loading the route model, or making a provider request.

Catalog registration occurs after content and local state are durable. If it
fails, the command exits with explicit `partial_success`: indexed content and
local applied state remain committed and are not rolled back, while the summary
includes a reviewed catalog repair command. The exact remote catalog schema v3
is a one-time reader-first prerequisite: provision a missing catalog or migrate
an existing v1/v2 catalog separately before applying schema-v3 plans. Ordinary
apply, including a first apply, never creates or migrates the catalog schema.
If the catalog is absent or not exact v3, apply performs no schema or card
write, reports post-content partial success, and retains the exact plan for the
emitted `catalog repair-apply --inspect-current` command. Do not use ordinary
`apply` to replay that baseline-stale plan. Complete the prerequisite or resolve
the catalog read failure, then run the emitted inspection. It reacquires the
namespace lock, revalidates the retained plan against the committed plan/apply
IDs, strongly reads exact-v3 catalog state, and prints a follow-up bound to
either observed card absence or its exact revision. Inspection loads no model,
writes nothing, and retains the plan. Review and run that bound command to
repair. Only after successful card verification may it clean the plan; cleanup
failure warns and retains the artifact without changing registration success.
When apply already observed exact-v3 card state before a later failure, its
original partial-success output may contain the bound repair command directly.
Buoy has no automatic background retry or pending reconciliation daemon.

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
~/.buoy/state/<source-id>/<namespace>/state.duckdb
```

It stores current row identity/status plus compact apply summaries, not full
snapshots. Existing project-local `.buoy` or `.turbo-search` state remains
untouched and can be used with an explicit `--state-root`; it is no longer an
implicit fallback. See [Migrating to focused Buoy](migrating-to-buoy.md).
Replanning the same source against the selected state root reports new/changed
rows to upsert, unchanged rows to skip, and previously applied rows now stale.

A same-namespace approved apply fails fast if another apply holds its lock. Different namespaces have independent ledgers and may apply concurrently. State is local to this machine; it is not a shared service.

Preflighted and failed plans remain available. Apply removes its exact plan
directory only after content, local state, and routing-card registration all
succeed. A post-content catalog partial retains that plan as the bounded
authority for the emitted repair command, even though its applied-state
baseline is no longer valid for ordinary `apply`. A newly written verified
plan removes older fully verified sibling plans for the same namespace. Copy a
plan elsewhere before approval if it must be retained for long-term audit.

Remote upserts and exact-ID deletes are deterministic. If remote content work
succeeds but the local state commit fails, retain the unchanged baseline-bound
plan and investigate before repeating it. Buoy has no catalog-pending or
automatic catalog-reconcile phase.

Successful JSON output includes `receipt_schema_version=1`, source identity,
namespace/region, plan/apply IDs, artifact hash, embedding and ranking
contracts, counts, retrieval commands, and verified catalog-registration
status. That is the supported Kite handoff.

DuckDB is the only applied-state authority. Obsolete JSON applied-state files are ignored and left unchanged; when no `state.duckdb` exists, apply uses normal first-apply behavior.

## Routing catalog operations

The remote routing catalog is `buoy-routing-catalog-v1`. Its cards let
`buoy retrieve QUERY` select among live content namespaces. Catalog commands
require `TURBOPUFFER_API_KEY`; Buoy never loads it from `.env` automatically.

```bash
# Read-only inventory and one-card inspection.
buoy catalog list
buoy catalog list --all
buoy catalog show site-example-com-v1

# Mutations preview by default.
buoy catalog disable site-example-com-v1
buoy catalog enable site-example-com-v1

# Commit only after reviewing the preview.
buoy catalog disable site-example-com-v1 --approve
buoy catalog enable site-example-com-v1 --approve
```

`catalog upsert` requires a complete manual source, embedding, and ranking
contract; see `buoy catalog upsert --help`. It also previews unless
`--approve` is supplied. These commands change routing cards only. They never
write, delete, enable, disable, or otherwise mutate the target content
namespace. Disabled cards remain catalog coverage but are not eligible for
automatic routes; stale cards are reported and never deleted automatically.
The system-owned routing-passage bank cannot be set, cleared, or replaced by
generic `catalog upsert`; an existing bank is preserved. Only approved apply,
retained-plan repair, or a separately governed migration/backfill may change
those passages.

Schema migrations and reviewed-example maintenance use narrower revision-bound
operators. Deploy the compatible v1/v2 reader first, preview
`buoy catalog migrate-routing-v2 --json`, and approve only with that preview's
exact snapshot and projection hashes. Deploy the v3-capable reader before
previewing and approving `buoy catalog migrate-routing-v3 --json`. Provisioning
a missing catalog is likewise a separately reviewed reader-first operation;
ordinary apply never substitutes for either prerequisite. Then preview
`buoy catalog set-routing-examples NAMESPACE --routing-example QUESTION --json`
and approve only with its exact card revision. See
[`retrieval.md`](retrieval.md#reader-first-schema-and-reviewed-examples) for the
full review sequence and safety accounting. These catalog-only operations do
not write indexed content or activate candidate routing, and normal future
applies preserve the reviewed questions.

Schema-v3 routing cards contain bounded, verbatim-derived source excerpts in
their routing-passage fields. Buoy redacts those passages and their vectors from
normal catalog and routing output, but a principal authorized to query raw
provider rows in the catalog namespace can read the excerpts. Treat catalog
credentials and raw-row read access as source-content access, not as
metadata-only access.

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
