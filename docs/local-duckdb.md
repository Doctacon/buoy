# Local DuckDB edition

## What changed

There is one search backend: DuckDB. The Turbopuffer SDK, credentials, endpoints,
and service dependency are removed. This is not a remote/local toggle.

- Native DuckDB `FLOAT[384]` vectors and `array_cosine_distance` provide **exact**
  nearest-neighbor search, followed by Buoy's existing reciprocal-rank fusion.
- Transactionally maintained token postings provide BM25 over title, section,
  and content, with the existing field boosts. Tokenization differs from the
  former service, so rankings and old benchmark measurements are not equivalent.
- Content, vectors, keyword statistics, namespace metadata, and routing cards
  live in `BUOY_HOME/search.duckdb`.
- No `INSTALL vss`, `INSTALL fts`, extension autoloading, hosted model calls,
  or vector database service is involved. DuckDB external access is disabled.
- Existing routing/catalog Python names containing `remote` remain for source
  compatibility; their client is now local. Old evaluation fixtures mentioning
  Turbopuffer describe a documentation corpus, not a runtime dependency.

Exact scanning avoids the experimental persistence and resident-memory behavior
of DuckDB's HNSW extension. Search cost grows with corpus size. Start with tens
of thousands of chunks, measure on your own data, and split large corpora into
namespaces. No latency or maximum corpus-size guarantee is implied.

## Windows / WSL2 setup

Use **WSL2 Ubuntu on its Linux filesystem**, not native Windows Python. Existing
plan verification, workers, and telemetry rely on POSIX filesystem semantics.
Keep Buoy, its environment, models, and databases under `/home/<user>/...`, not
`/mnt/c`, a network drive, OneDrive, or another synchronized folder.

On a connected Windows machine, install WSL2/Ubuntu and Python tooling using
approved IT procedures. Install Python 3.11–3.13, Git, and `uv` inside Ubuntu.
On a 32 GB host, a reasonable `%UserProfile%\\.wslconfig` starting point is:

```ini
[wsl2]
memory=20GB
processors=4
swap=4GB
```

Apply that configuration with `wsl --shutdown` from PowerShell. It is a suggested
WSL allocation, not a requirement; leave sufficient RAM for Windows.

From this branch in the Linux filesystem:

```bash
uv sync --locked --extra mcp
uv run --no-sync python scripts/prepare_local_models.py --download
```

`uv` uses CPU-only PyTorch wheels on Linux/Windows. Models default to CPU and
float32. The 4 GB GPU remains available to other applications. Inference uses
small BGE embeddings and MiniLM reranking, not a local generative LLM.

Normal usage after setup:

```bash
export BUOY_HOME="$HOME/.buoy-local"  # optional; this is the default
export BUOY_TELEMETRY=off             # optional; telemetry is already opt-in

uv run --no-sync buoy plan ./notes.md --namespace notes
uv run --no-sync buoy apply --dry-run
uv run --no-sync buoy apply --approve
uv run --no-sync buoy retrieve "What is the deployment procedure?" --namespace notes
uv run --no-sync buoy retrieve "What is the deployment procedure?" --json
uv run --no-sync buoy catalog list --all --json
```

If multiple pending plans exist, select one with `apply --plan /path/to/plan.json`.
Stale rows are retained unless you explicitly approve `--delete-stale`.

## Fully disconnected installation

Package installation and initial model acquisition need a connected **staging
machine**, not access from the work laptop. Use a Linux x86-64 staging environment
matching the target's Python minor version and architecture (another WSL2 Ubuntu
installation is suitable). Do not copy a macOS/ARM virtual environment to WSL.
Have Python and WSL available on the target before disconnecting.

On the approved staging machine, from this branch:

```bash
uv sync --locked --extra mcp
uv build --wheel
uv export --locked --no-dev --extra mcp --no-emit-project \
  --format requirements-txt --output-file requirements-local.txt
mkdir -p wheelhouse
uv run --with pip --no-sync python -m pip download --only-binary=:all: \
  --extra-index-url https://download.pytorch.org/whl/cpu \
  --requirement requirements-local.txt --dest wheelhouse
cp dist/buoy_search-*.whl wheelhouse/
uv run --no-sync python scripts/prepare_local_models.py \
  --download --cache-dir ./hf-cache
```

Copy the branch source (including `scripts/`), `wheelhouse/`,
`requirements-local.txt`, and the **whole** `hf-cache/` directory to the target.
Use an archive that preserves symlinks, or dereference them while copying. The
HF cache contains both snapshots and blobs; copying just snapshot symlinks is
not sufficient. The preparation script downloads only the exact required model
files, with no remote Python code.

On the offline target, inside WSL:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links wheelhouse \
  -r requirements-local.txt
.venv/bin/python -m pip install --no-index --find-links wheelhouse \
  wheelhouse/buoy_search-*.whl
export HF_HOME="$PWD/hf-cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
.venv/bin/buoy --help
.venv/bin/buoy plan ./notes.md --namespace notes
.venv/bin/buoy apply --approve
.venv/bin/buoy retrieve "deployment procedure" --namespace notes
```

Use `.venv/bin/buoy` directly or `uv run --offline --no-sync buoy ...` for normal
offline operation. Ordinary `uv run` may check/sync packages; that is installer
behavior, not search traffic. Buoy model constructors themselves enforce offline
mode even if inherited Hugging Face flags say otherwise. Missing weights produce
a setup error instead of an attempted download.

The exact required models are:

| Purpose | Model | Revision |
| --- | --- | --- |
| Content + routing embeddings | `BAAI/bge-small-en-v1.5` | `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` |
| Routing + result reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `c5ee24cb16019beea0893ab7796b1df96625c6b8` |

No automatic weight substitution or model download is permitted. Keep the pinned
embedding model unchanged between apply and retrieval.

## Import local folders and repositories

The helper materializes UTF-8 text/code files into a source DuckDB table. It does
not contact GitHub, run git hooks, execute source code, or load models:

```bash
.venv/bin/python scripts/import_local_directory.py ./checkout ./source-docs.duckdb
.venv/bin/buoy plan ./source-docs.duckdb --relation documents --source-id work-code
.venv/bin/buoy apply --approve
```

Put the output database outside the input folder. Symlinks, hidden/generated
folders, common secret files, binary files, and oversized files are skipped.
Review the summary and source relation before applying. Exclusions are a safety
convenience, not a guarantee that arbitrary source folders contain no secrets.

After changing files, rerun the helper with `--replace`, then plan/apply with the
same source ID. Relative paths are stable document IDs. `--max-file-bytes`,
`--max-files`, `--include`, and `--exclude` bound the import. This uses the shared
document chunker; specialized GitHub syntax/file-card experiments do not apply.

Individual PDF/Office/Markdown files and existing DuckDB document relations also
work without this helper. No OCR, image captioning, or remote file conversion is
performed. Explicit online acquisition is available only if you set
`BUOY_ALLOW_NETWORK=1` for that invocation on an approved connected machine.
Never set it on the restricted laptop. This application guard is not an OS
firewall; enforce your organization's network policy at the OS/network level.

## Resource settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `BUOY_HOME` | `~/.buoy-local` | Index, plans, incremental state, workers, telemetry |
| `HF_HOME` | Hugging Face default | Location of transferred model cache |
| `BUOY_DEVICE` | `cpu` | Local inference device |
| `BUOY_MODEL_THREADS` | `4` | PyTorch CPU threads |
| `BUOY_DB_MEMORY_LIMIT` | `4GB` | DuckDB buffer-manager limit per connection |
| `BUOY_DB_THREADS` | `4` | DuckDB query threads |
| `BUOY_ALLOW_NETWORK` | unset | Only `1` enables explicit remote source acquisition |

DuckDB's memory limit is **not** a process RSS cap. Python, model tensors,
intermediate data, and ingestion artifacts need additional RAM. Keep apply's
embedding batch at its default 32; reduce `--embedding-batch-size` if necessary.
The write batch defaults to 64. Plan verification currently materializes the
reviewed delta in Python; batching does not make the whole apply constant-memory.
Start with `buoy plan ... --max-chunks 20000`, review any truncation diagnostics,
and measure a representative corpus before increasing limits. Disk use includes
original sources, plans, content, postings, vectors, and model/package caches.

The local index serializes database access with a cross-process file lock and
opens/closes connections per operation. This supports CLI/MCP use without a
server and avoids DuckDB multi-process writer conflicts. It does not offer
cloud-scale concurrent throughput. Do not open a second external DuckDB writer
against the search file while Buoy is running.

Approved applies additionally hold a namespace-wide lock across all sources and
state-root overrides. Each write batch and its postings update are transactional,
but **the whole apply is not one atomic corpus swap**: concurrent readers may see
completed batches before later batches or stale deletion finish. A failed apply
can leave partial writes; retry the same approved plan (and deletion choice) to
complete it. The baseline check permits only that plan's idempotent partial work.

GPU use is optional: install an appropriate CUDA-enabled PyTorch build explicitly,
then select `BUOY_DEVICE=cuda`. The default locked CPU installation is the
recommended configuration for this laptop. Do not assume 4 GB VRAM can accommodate
large batches. CPU float16 is rejected; leave precision at float32.

## Backups and migration

Stop active apply/retrieve/MCP processes and allow workers to exit before backing
up. Copy the **whole BUOY_HOME**, not only `search.duckdb`: applied-state databases
are the incremental baseline, and pending plans bind that baseline. If you use
an external `--state-root`, include it in the same stopped-process backup too.
Model caches can be copied separately. Before applying, Buoy checks source-owned row IDs and
embedding hashes against the reviewed state baseline. Missing unchanged rows,
untracked rows, or changed hashes fail closed before inference or index writes;
deleting only `search.duckdb` cannot silently produce a successful no-op apply.
Restore a complete backup, or rebuild in a new empty BUOY_HOME and plan/apply again.

The database also records the embedding model revision, vector representation,
lexical tokenizer and BM25 contract. An incompatible contract requires a fresh
index rather than silently reusing old vectors or postings.

Earlier `~/.buoy` data and remote indexes are not imported, deleted, or modified.
The local edition intentionally uses `~/.buoy-local`. **Do not point
`--state-root` at a cloud-era ledger**: it describes another index and the local
baseline check will refuse to skip missing rows. Re-index original documents, copied repositories, or source relations.
Keep the same BUOY_HOME in the CLI and MCP environment.

## Verification and limitations

```bash
uv sync --locked --extra mcp
uv run --no-sync pytest -q
```

Storage tests use real temporary DuckDB databases. End-to-end tests use
lightweight deterministic embeddings so they can run with network disabled and
without model weights. After transferring the model cache, run the real-model
check as well:

```bash
python scripts/smoke_local_install.py
```

It uses a temporary BUOY_HOME, exercises plan/apply and explicit/automatic search
with the pinned CPU models, and forbids Python INET socket connections. It does
not alter your existing index or start a persistent embedding worker.

Old ranking/calibration artifacts were measured against another backend/corpus.
They are not evidence of DuckDB quality or performance. Automatic routing still
works, but evaluate your work corpus before depending on ranking thresholds.
Native Windows Python is not a supported target; Windows through WSL2 is.
