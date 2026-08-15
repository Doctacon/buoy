Status: active
Created: 2026-08-15
Updated: 2026-08-15
Amends: .10x/decisions/direct-commands-execute-by-default.md

# Buoy Defaults Live Retrieval to Compact Citations

## Context

The current live text renderer exposes operator diagnostics for every hit:
namespace attribution, paths, tags, embedding precision, fusion and reranking
details, model identity, score dictionaries, and a long content preview. Those
details are useful when diagnosing retrieval, but they obscure the passages and
citations that are the ordinary human-facing result. JSON already provides the
complete machine-readable contract.

This decision is about presentation only. The existing router, widening rules,
namespace-local retrieval, deduplication, cross-namespace ranking, deterministic
tie-breaking, per-corpus coverage promotion, result limits, partial-failure
semantics, evidence assessment, and provider calls remain authoritative.

## Decision

Successful live `buoy retrieve` text defaults to a compact, citation-first list
of passages. Each item contains only its rank, title, best available citation,
optional section, and a whitespace-collapsed excerpt of at most 320 characters.
Prominent partial-failure warnings and the existing no-relevant-evidence and
inconclusive messages remain visible. The existing `assessment_failed` warning
also remains prominent because results are being preserved after an assessment
problem. Positive `supported`, observational `unassessed`, and shadow
`would_*` statuses remain available as diagnostics but are omitted from compact
text.

`--explain` selects the current detailed live text for the exact same retrieval
result. It is a rendering choice, not a retrieval option. `--json` remains the
stable complete machine contract, and dry-run/plan output remains detailed.
`--json` and `--explain` are mutually exclusive and fail before credentials,
models, or provider operations are reached.

## Consequences

Ordinary compact text may omit namespace attribution, tags, redundant paths,
embedding precision, model and fusion details, positive evidence status, and
scores. Those values remain in JSON and, where they are part of the current
detailed text contract, in `--explain`; plan/dry-run diagnostics remain intact.
Omission from compact text does not remove metadata from a hit or alter the
serialized JSON object.

Buoy still returns retrieved passages rather than synthesizing an answer. This
decision does not add `ask`, content-only, verbose, summarization, generation,
or citation-rewriting behavior. It also does not authorize a ranking or
evaluation change from the stopped pure-global-ranking work.
