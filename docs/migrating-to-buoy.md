# Migrating to the local DuckDB branch

This branch has no Turbopuffer client or cloud index connection. It does not
retrieve, copy, delete, or modify your old remote indexes.

1. Install this branch and prepare/copy the pinned models using
   [the offline setup guide](local-duckdb.md).
2. Use the new default `~/.buoy-local`, or set `BUOY_HOME` to a new empty directory.
3. Re-plan original local documents, copied code folders, or prepared DuckDB
   relations, then review and apply them to build the local index.
4. Use the same BUOY_HOME/HF_HOME in terminal and MCP environments.

**Do not reuse an old `--state-root` or copy only the old applied-state ledger.**
The ledger records rows written to the old backend; reusing it would incorrectly
skip content that is absent in local DuckDB. Old pending plans also bind that
baseline and should be replaced by fresh plans.

```bash
export BUOY_HOME="$HOME/.buoy-local"
buoy plan ./notes.md --namespace notes
buoy apply --dry-run
buoy apply --approve
buoy retrieve "deployment procedure" --namespace notes
```

The first approved apply initializes the local routing catalog automatically.
There is no separate cloud catalog provisioning step. Preserve any manually
curated titles/aliases/tags by reviewing and recreating the appropriate local
cards after indexing.

`TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, and `TURBOPUFFER_NAMESPACE` are unused.
Remove them from Buoy launch configurations. The old `--region` flag accepts only
`local`. Deprecated `TURBO_SEARCH_*` embedding aliases remain rejected rather than
silently overriding current configuration.

CLI workflows, namespace IDs, citations, grouping, and routing largely remain.
Provider-specific output `turbopuffer_api_calls` is replaced by
`local_index_operations`; credentials-required flags are false. Historical generic
API/request counters now describe local interface operations, not network traffic
or billing. Tokenization/vector precision/backend changes mean old metric results
cannot certify this branch. Evaluate representative questions from your own data.

Windows support is through **WSL2**, not native Windows Python. Keep runtime files
on the WSL Linux filesystem. See [setup, resource limits and backups](local-duckdb.md).
