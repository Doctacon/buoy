# Indexing sources safely

This is the detailed reference for turning a source into a reviewed, incremental turbopuffer index.

## The safety model

Indexing has three gates:

1. `plan` crawls or converts the source, chunks it, compares it with local state, and writes review artifacts. It does not read credentials, load embeddings, or contact turbopuffer.
2. `apply` verifies the saved artifacts and recomputes the diff. Without `--approve`, it is still local-only.
3. `apply --approve` loads the local embedding model and writes only the reviewed new or changed rows.

Stale rows are retained unless `--delete-stale` is also explicit. Namespace deletion is not part of this workflow.

## Sources

### Websites

```bash
uv run buoy plan https://example.com/
```

Website planning uses Scrapling, stays on the source host, obeys robots.txt, and derives a namespace such as `site-example-com-v1`.

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
uv run buoy apply
```

By default, apply selects the newest plan under `artifacts/site-crawls/`. Use `--plan <path>` when multiple plans exist.

Preflight verifies schema, namespace, manifest/chunk agreement, embedding-text hashes, artifact integrity, and compatibility with local state. Review at least:

- target namespace;
- rows and embeddings to upsert;
- unchanged and stale rows;
- state path;
- whether deletion is requested.

It does not read `TURBOPUFFER_API_KEY` or contact turbopuffer.

## Approved apply

After reviewing the plan and preflight:

```bash
export TURBOPUFFER_API_KEY="..."
uv run buoy apply --approve
```

If credentials live in this repository's `.env`, load them only into the command subshell:

```bash
(
  set -a
  . ./.env
  set +a
  uv run buoy apply --approve
)
```

Approved apply acquires a fail-fast lock for the target namespace and overlaps one local embedding batch with one ordered remote upsert. It never runs concurrent embeddings or concurrent writes, and commits local state only after all remote work succeeds. Interactive runs show confirmed batches/rows on one stderr line; the final summary separates elapsed, embedding, and write time, whose stage totals may exceed wall time because they overlap. Tune the two independent batch controls only after measuring the workload:

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

Pending, preflighted, and failed plans remain available. A successful approved apply removes its exact plan directory after remote work and state commit. A newly written verified plan removes older sibling plans for the same namespace. Copy a plan elsewhere before approval if it must be retained for audit.

A legacy `last-applied.json` is removed when the DuckDB ledger is first used; the ledger starts empty so the next approved apply re-upserts reviewed rows rather than trusting legacy local state.

## Stale rows

Preview stale deletion locally:

```bash
uv run buoy apply --delete-stale
```

Delete only those exact stale row IDs after approval:

```bash
uv run buoy apply --approve --delete-stale
```

This never deletes the namespace.
