Status: active
Created: 2026-09-10
Updated: 2026-09-10

# Buoy MCP Catalog Read Tools

## Purpose and authority

Expose existing remote catalog inspection without any catalog management
capability. On 2026-09-10 the owner explicitly approved these signatures:

```text
catalog_list(search?: string | null, include_all: boolean = false)
catalog_show(namespace: string)
```

Transport, packaging, subprocess lifecycle, errors, and privacy are governed by
`.10x/specs/buoy-mcp-stdio-server.md`. The catalog remains the existing fixed
`buoy-routing-catalog-v1`; this is not arbitrary namespace/document enumeration
or a new metadata store.

## List behavior

`catalog_list` MUST delegate to `buoy catalog list --json`, mapping
`include_all=true` to `--all` and a supplied `search` to positional data.

- Default listing returns enabled cards with live targets, using the current
  CLI filtering and order. It MUST NOT silently change this into eligible-only
  filtering or hide incompatible live cards the CLI reports.
- `include_all=true` includes disabled/stale cards according to the CLI's
  existing `--all` behavior. It does not enable cards, repair them, or query
  their content namespaces.
- Omitted/null search means no search argument. Empty/whitespace search retains
  the existing CLI no-filter behavior. Other strings use the CLI's existing
  canonical substring matching of namespace, title, summary, aliases, tags,
  and reviewed routing examples. Do not add fuzzy/semantic search.
- Return the existing JSON object, including count, cards, search/all fields,
  catalog status, missing-card diagnostics, snapshot/read metadata, and any
  existing compatibility information. A zero-card match is a successful empty
  list, not an error.

## Show behavior

`catalog_show` MUST delegate to `buoy catalog show --json` with exactly the
provided namespace string as positional data. Require non-whitespace content;
otherwise preserve the CLI's exact card-ID lookup rather than inventing fuzzy
resolution or normalization. A missing card is an MCP tool error.

Return the current CLI JSON object, including the card, target/catalog status,
and catalog/snapshot metadata. There is no `include_vector` argument and the
adapter MUST NOT pass `--include-vector`. Both tools retain the normal CLI
exclusion of vectors and system-owned source-derived routing-passage banks.
Reviewed `routing_examples`, already visible through normal CLI inspection,
remain visible; they are not the withheld source-derived passage bank.

## Access and side effects

Both operations use existing environment credentials and may make billed
remote inventory/catalog reads. They inherit the established configured region
and compatibility checks. The adapter adds no ACL, credential storage, cache,
background refresh, content query, embedding work, telemetry workflow, or
provider write. It exposes none of upsert, enable/disable, repair-apply,
schema migration, set-routing-examples, deletion, or an arbitrary CLI runner.
Unknown arguments and wrong types MUST be rejected; values containing option
syntax must remain data, not change the command.

The catalog reader/CLI remain implementation authority at
`src/buoy_search/cli/catalog.py`, `src/buoy_search/catalog/local.py`, and
`src/buoy_search/catalog/remote.py`, under the current amended catalog contract
in `.10x/specs/automatic-multi-corpus-retrieval.md`.

## Acceptance

Provider-free tests MUST prove default and all-card list parity; normalized
search matching and empty results; exact show success/missing-card failure;
absence of vectors and source-passage banks; retained reviewed examples;
strict boolean/string inputs; option-like strings contained as data; and no
reachable mutation command or write method. Compare actual fake-backed CLI
JSON with tool results, not only hand-authored response fixtures. Nonzero exit,
process failure, and invalid JSON must follow the shared sanitized-error
contract. Startup/discovery must not enumerate the account.
