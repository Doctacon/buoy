# Indexing sources safely

This is the detailed reference for turning a source into a reviewed, incremental turbopuffer index.

## The safety model

Indexing has three gates:

1. `plan` crawls or converts the source, chunks it, compares it with local state, and writes review artifacts. It does not read credentials, load embeddings, or contact turbopuffer.
2. `apply --dry-run` verifies the saved artifacts and recomputes the diff without prompting, credentials, models, or API calls.
3. Plain interactive `apply` displays that complete preflight and prompts `Apply this plan? [y/N]`; only exact `y`/`yes` loads the local embedding model and writes reviewed rows. `apply --approve` bypasses the prompt for automation.

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
