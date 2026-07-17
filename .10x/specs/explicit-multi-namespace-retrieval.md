Status: active
Created: 2026-07-14
Updated: 2026-07-16

# Explicit Multi-Namespace Retrieval

## Purpose and scope

Remove the silent demo-namespace retrieval fallback and allow an operator to search one or more explicitly selected namespaces with one query.

## Namespace selection

- `buoy retrieve` MUST accept repeatable `--namespace ID` arguments as the sole manual namespace-selection override.
- One or more CLI namespaces MUST bypass default catalog routing and retain their supplied order.
- `TURBOPUFFER_NAMESPACE` MUST NOT supply a retrieval namespace; retrieve must not read or warn about it.
- When no CLI namespace is supplied, selection is governed by `.10x/specs/default-production-namespace-routing.md` rather than this explicit mode.
- Explicit namespaces combined with automatic-only `--auto-route`, `--route-top-k`, or retrieve `--catalog` options MUST fail before credential, model, catalog, or Turbopuffer work.
- The hard-coded demo namespace MUST NOT be used by live or dry-run retrieval.

## Query execution

- All selected namespaces MUST use the one region, embedding model, and embedding precision supplied by CLI/environment/default model settings. Buoy does not maintain or infer per-namespace model metadata in this version.
- The query MUST be normalized and embedded once. The same query vector MUST be reused for every selected namespace.
- Namespaces MUST be queried in explicit CLI order.
- Existing within-namespace hybrid retrieval, schema fallback, and final ranking behavior MUST remain unchanged.
- If any namespace fails, the entire command MUST fail and identify that namespace. It MUST NOT print a partial result set.

## Cross-namespace merge

- A single-namespace invocation MUST retain the existing result behavior and JSON contract.
- A multi-namespace invocation MUST merge each namespace's final ranked list using deterministic reciprocal-rank fusion rather than comparing raw namespace-local scores.
- Each namespace MUST have equal fusion weight. The RRF constant MUST reuse Buoy's established client-side RRF constant.
- Cross-namespace identity MUST include namespace plus row identity; equivalent URLs in different namespaces are not silently collapsed.
- Ties MUST resolve deterministically by namespace selection order and source rank.
- `--top-k` is the global returned-hit limit. Existing `--candidates` and ranking controls apply independently inside each namespace before cross-namespace fusion.
- Every merged hit MUST expose its source namespace. Text output MUST show it with the citation; JSON MUST include an ordered `namespaces` list and per-hit namespace.

## Output compatibility

- Existing single-namespace text and JSON fields MUST remain compatible.
- Multi-namespace output MUST use an explicit multi-namespace result shape rather than placing a misleading first namespace in the existing singular `namespace` field.
- Schema changes for the new multi-namespace invocation are additive to individual hit data and documented.

## Acceptance scenarios

### Missing selection

Given no CLI namespace, when dry-run or live retrieval starts, then default catalog routing selects namespaces and never uses a demo or environment namespace.

### One namespace

Given one explicit namespace, retrieval performs one query embedding, one namespace query flow, and returns the existing result contract.

### Multiple namespaces

Given two explicit namespaces, retrieval embeds once, queries both in order, and returns global top-k RRF results with deterministic namespace attribution.

### Failure

Given the first namespace succeeds and the second fails, the command returns an error naming the second namespace and emits no result payload.

## Explicit exclusions

Remote all-namespace fan-out, namespace patterns/groups, concurrent namespace queries, partial-success output, namespace mutation, and multi-namespace eval execution. Default catalog routing and its per-namespace model metadata are governed separately.
