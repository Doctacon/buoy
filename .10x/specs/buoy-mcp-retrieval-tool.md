Status: active
Created: 2026-09-10
Updated: 2026-09-10

# Buoy MCP Retrieval Tool

## Purpose and provenance

Expose the existing `buoy retrieve --json` behavior, not a new search engine or
answer generator. The owner explicitly approved this signature and default on
2026-09-10 after selecting local stdio/read-only MCP:

```text
retrieve(query: string, namespaces?: string[] | null, top_k: integer = 5)
```

Transport, packaging, privacy, diagnostics, and subprocess lifecycle are owned
by `.10x/specs/buoy-mcp-stdio-server.md`.

## Inputs and delegation

- `query` MUST be a string with non-whitespace content. Retain the CLI's
  leading/trailing whitespace normalization.
- Omitted/null `namespaces`, or an empty list, means automatic routing, matching
  the CLI's zero-explicit-namespace path. It does not mean query every index.
- One through three explicit namespaces MUST be trimmed, nonempty, and unique
  after trimming. Reject more than three and reject `buoy-routing-catalog-v1`
  and any `buoy-evidence-*` content target. Preserve explicit input order.
- `top_k` MUST be a positive integer, not a boolean, string, or fractional
  value. Its default is the owner-approved existing CLI value `5`; no new
  upper cap is introduced. It is the existing final global result limit.
- Use `retrieve --json --top-k=<value>` with repeated bound namespace options
  and the query as positional data. The caller cannot supply CLI fragments,
  credentials, model names, ranking controls, file paths, or arbitrary options.
- Unknown tool arguments and invalid values MUST fail validation rather than
  enabling a hidden flag or live operation.

## Retained search contract

The adapter MUST preserve the equivalent CLI JSON object and operation
sequence. In particular:

1. Automatic retrieval uses the existing catalog/router and bounded fanout.
   Explicit namespaces bypass catalog discovery and routing work.
   `TURBOPUFFER_NAMESPACE` remains ignored.
2. Ranking, citation/source identity, passage content, tags, per-namespace
   summaries, routing/reranking diagnostics, deduplication, widening, and
   evidence assessment are not reimplemented or weakened by the adapter.
3. Empty successful results remain successful. Automatic `no_relevant_evidence`
   and `inconclusive` outcomes retain their existing evidence object, hits,
   failures, and incomplete status. They do not claim an answer does not exist.
4. A partially failed retrieval preserves successful hits and attributed
   failures. Total failure is an MCP tool error, never a fabricated empty hit
   list. Explicit raw-search behavior remains distinct from automatic
   evidence-abstention behavior.
5. Return evidence, not a synthesized answer. Tool documentation MUST tell the
   consuming agent to retain source citations and respect incomplete/abstained
   results.

Underlying semantic authority remains the current amended
`.10x/specs/automatic-multi-corpus-retrieval.md`,
`.10x/specs/automatic-retrieval-evidence-abstention.md`, and
`.10x/specs/default-retrieve-embedding-worker.md`. This adapter authorizes no
threshold, routing-certification, worker, or telemetry change. If implementation
finds material source/spec drift, block that slice rather than redefining it in
a wrapper test.

## Side effects and acceptance

Each valid live call may make ordinary billed Turbopuffer reads under the
operator's existing environment credentials, use the existing local inference
worker, and produce existing opt-in local telemetry. The MCP adapter adds no
remote writes or durable query/result log. Launch and discovery are inert.

Provider-free tests MUST cover:

- automatic, explicit-single, and explicit-multi argument mapping;
- null/empty selection and default/explicit positive top-k;
- blank/wrong-type inputs, duplicate/reserved/excess namespaces, unknown
  arguments, and option/shell-like strings treated only as data;
- exact structured/text JSON parity for normal hits, no hits, partial failure,
  no-relevant-evidence, and inconclusive outcomes;
- nonzero exit/malformed response as sanitized errors and no adapter retry.

Use existing fake CLI/provider seams to establish parity with actual CLI
rendering as well as adapter mapping. Mocked payload passthrough alone does not
prove the retained search contract. New live evaluations, ranking promotion,
preview tools, doc-kind/ranking overrides, ingestion, and namespace mutation
are excluded.
