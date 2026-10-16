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
After checking out this branch:

```bash
uv sync --locked --extra mcp

# ONE-TIME ONLINE SETUP, on an approved connected machine only:
uv run --no-sync python scripts/prepare_local_models.py --download

# All commands below work offline once dependencies and models are installed:
uv run --no-sync buoy plan ./research-notes.pdf --namespace work-notes
uv run --no-sync buoy apply --dry-run
uv run --no-sync buoy apply --approve
uv run --no-sync buoy retrieve "What do the notes say?"
```

The default home is `~/.buoy-local/`, **separate from earlier Buoy installations**.
Set `BUOY_HOME` to move the index and its state together. Do not reuse a
cloud-era applied-state ledger: re-plan and re-index your original sources.

For a folder of documents or source code:

```bash
uv run --no-sync python scripts/import_local_directory.py ./docs ./knowledge.duckdb
uv run --no-sync buoy plan ./knowledge.duckdb --relation documents --source-id work-docs
uv run --no-sync buoy apply --approve
```

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
