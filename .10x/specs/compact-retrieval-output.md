Status: active
Created: 2026-08-15
Updated: 2026-08-15
Decision: .10x/decisions/buoy-defaults-live-retrieval-to-compact-citations.md
Amends: .10x/specs/retrieval-tag-output.md
Amends: .10x/specs/embedding-inference-precision.md

# Compact Retrieval Output

## Scope

This contract changes only the presentation of live `buoy retrieve` text. It
applies to automatic retrieval and to explicit retrieval with one, two, or
three namespaces. It does not change the result object that reaches the
renderer.

The hit order, hit count, default and requested `top_k`, routing, widening,
namespace-local retrieval, deduplication, MiniLM use, cross-namespace fusion,
deterministic ties, per-corpus coverage promotion, partial-failure handling,
evidence assessment, abstention, and provider-call sequence MUST remain exactly
as governed before this amendment. Rendering mode MUST NOT be passed into or
consulted by those operations.

## Default compact live text

A successful live text result with `N` hits MUST begin with `Found N passage.`
when `N` is one and `Found N passages.` otherwise. Each rendered hit MUST then
contain, in order:

1. its one-based rank and title on one line;
2. its best available citation, followed by ` · ` and the section when a
   section is present; and
3. a content excerpt when nonempty.

The title is collapsed to one line; an empty title renders as `Untitled`. The
citation is the first nonempty single-line value in this exact order: `url`,
`repo_path`, `path`, stable hit ID. If all are empty, it renders as
`Unknown source`. A path therefore remains visible when it is the best
available citation, but a path MUST NOT be repeated when a URL is available.
The optional section is the hit's existing section path collapsed to one line.

The excerpt MUST trim leading/trailing whitespace and replace every run of
whitespace with one ASCII space. If the result is at most 320 characters it is
rendered unchanged. Otherwise the renderer MUST reserve three characters for a
literal `...`, trim the candidate prefix, avoid splitting the last word when a
prior ASCII-space boundary exists, and append the ellipsis. The final excerpt,
including ellipsis, MUST never exceed 320 characters. An empty excerpt omits
the excerpt line.

Compact text MUST omit ordinary per-hit or positive-status diagnostics,
including corpus/namespace, tags, a redundant path, embedding model and
precision, model revision, fusion/reranking configuration, `supported`,
`unassessed`, and shadow `would_*` evidence diagnostics, and score dictionaries.
This omission is not data deletion: JSON and the in-memory result remain
unchanged.

Raw third-party model weight-loading progress bars MUST NOT leak into normal or
explained retrieval output. Suppressing those bars MUST NOT change which model
is loaded, its configuration, failure behavior, or timing/accounting data.

## Failures, empty results, and evidence states

A partial result MUST retain a prominent redacted warning before its hits. When
failed namespace IDs are available, the warning identifies them in the
existing attributed order; otherwise it says that some corpora could not be
searched. This warning is the deliberate exception to compact text's ordinary
namespace omission. It MUST NOT print credentials, raw provider responses, or
unredacted exceptions.

An evidence status of `assessment_failed` MUST retain the existing prominent
warning that assessment failed and results were preserved because abstention is
not active. Compact text MUST NOT hide this safety-relevant degraded state.
Conversely, `supported`, `unassessed`, and shadow `would_*` statuses are
diagnostic-only in compact text and remain visible through JSON and
`--explain`.

The established `no_relevant_evidence` and `inconclusive` text, searched-corpus
context, attributed failure details, exit behavior, and empty hit set remain
unchanged. `--explain` MUST NOT override an abstention or turn an inconclusive
result into passages. An ordinary complete result with zero hits renders
`Found 0 passages.` under the existing empty-result semantics.

## Explained, JSON, and plan modes

`--explain` MUST reproduce the pre-amendment detailed live text from the same
result: retrieval/fusion header, applicable reranker and evidence diagnostics,
effective embedding precision, and the existing per-hit namespace, URL,
section, path, ordered tags, score metadata, and detailed content preview.
Fields that were already conditional remain conditional. `--explain` changes
presentation only and MUST cause no additional embedding, inference, catalog,
content-namespace, or provider call.

`--json` MUST remain structurally unchanged, including hit ordering and all
existing result, routing, reranking, evidence, failure, tag, precision, score,
and namespace fields. No presentation-mode field is added. `--json` and
`--explain` are mutually exclusive. Their conflict MUST return usage status 2
with empty standard output and a concise error before query validation,
configuration/environment resolution, credential access, model construction,
catalog reads, content queries, or any provider call.

`--dry-run` and its `--plan` alias remain detailed and keep their current
provider-boundary statements, selected namespaces, routing information,
embedding model and precision, limits, ranking configuration, and evidence
plan. Supplying `--explain` with a plan MUST NOT turn the plan into compact live
text or cause live work. Plans contain no hits, so they have no per-hit tag
lines.

## Compatibility and exclusions

- Stored tags remain ordered hit metadata and remain mandatory in JSON. A
  nonempty tag list remains visible in `--explain`; compact text may omit it.
- Effective embedding precision remains visible in JSON, dry-run/plan, and
  `--explain`; compact live text may omit it.
- Existing ranking and coverage diagnostics remain in JSON and `--explain`.
  In particular, this amendment neither disables nor changes the current
  per-corpus coverage-promotion policy.
- No answer synthesis, summary generation, LLM call, `buoy ask`,
  `--content-only`, `--verbose`, interactive pager, color protocol, or new
  output format is included.
- No routing card, content row, namespace, schema, embedding, credential,
  provider, threshold, evaluation basket, or release-state change is included.

## Acceptance

- Compact text is exercised for explicit single-namespace, explicit
  multi-namespace, and automatic results, including one and many hits.
- Citation fallback, optional section, empty title/content, whitespace
  collapse, word-boundary truncation, and the exact 320-character bound are
  deterministic.
- Partial, assessment-failed, empty, no-relevant-evidence, and inconclusive
  output preserve their existing safety semantics and redaction; positive,
  observational, and shadow evidence diagnostics remain hidden in compact
  text.
- `--explain` exposes the current detailed fields without changing the result;
  exact JSON compatibility is proved independently.
- The flag conflict fails before credentials, models, or providers, and plan
  mode remains detailed and non-live.
- Tests prove identical hit identities/order, evidence state, failures, and
  provider/model call accounting across compact, explained, and JSON
  presentation of the same retrieval result.
