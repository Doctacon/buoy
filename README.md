<p align="center">
  <img src="images/buoy.png" alt="Buoy">
</p>

# Buoy — local DuckDB edition

*Search that stays anchored to the source, on your own machine.*

This branch replaces Turbopuffer completely with a **local DuckDB database**.
Documents, vectors, keyword indexes, routing cards, and retrieval stay on disk.
No account, API key, vector server, GPU, or downloadable DuckDB extension is
required. Models run locally and **never download during indexing or search**.

Preserved: reviewed plan/apply, incremental updates, hybrid vector/BM25 search,
namespace routing, local reranking, anchored citations, JSON output, and MCP.

## Quick start

Recommended target: **Ubuntu in Windows WSL2**, Python 3.11–3.13, `uv`, and Git.
CPU defaults suit a 32 GB RAM / 4 GB VRAM laptop; the GPU is not needed.
Install this branch directly as a normal tool inside WSL:

```bash
uv tool install --torch-backend cpu "buoy-search[mcp] @ git+https://github.com/Doctacon/buoy.git@local-duckdb"
buoy setup --download-models
```

That's the setup. Package installation and the explicit one-time model download
use the internet; normal indexing and search do not. No manual virtual environment,
model paths, API keys, or running database service are needed. A supplied wheel
can be installed with the same `uv tool install --torch-backend cpu` command,
using its path instead of the Git requirement. From a checkout, use `.[mcp]`.
On macOS, omit `--torch-backend cpu`.

```bash
buoy plan ./research-notes.pdf --namespace work-notes
buoy apply --dry-run
buoy apply --approve
buoy retrieve "What do the notes say?"
```

The default home is `~/.buoy-local/`, **separate from earlier Buoy installations**.
Set `BUOY_HOME` to move the index and its state together. Do not reuse a
cloud-era applied-state ledger: re-plan and re-index your original sources.

For bulk text/code folders, see the [folder import helper](docs/local-duckdb.md#import-local-folders-and-repositories).
The separate [air-gapped installation procedure](docs/local-duckdb.md#fully-disconnected-installation)
is needed **only if the target cannot download packages/models during setup**.

Website, GitHub, BigQuery, and Snowflake acquisition is disabled by default.
It can be explicitly enabled on a connected staging machine with
`BUOY_ALLOW_NETWORK=1`; it is not necessary for local use.

## Setup and reference

- **[WSL2 and fully offline installation](docs/local-duckdb.md)** — model transfer,
  CPU wheels, hardware limits, backups, migration, and troubleshooting
- [Index sources](docs/indexing.md)
- [Retrieve with automatic routing](docs/retrieval.md)
- [Connect an MCP client](docs/mcp.md)
- [Local telemetry](docs/telemetry.md)
- [Evaluation](docs/evaluation.md)

Vector search uses DuckDB's built-in exact cosine distance, not experimental
persistent HNSW. It favors reliable offline persistence over large-corpus speed.
Earlier cloud benchmark scores do not describe this backend.

[Apache License 2.0](LICENSE).
