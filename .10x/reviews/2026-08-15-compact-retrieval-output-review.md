Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-compact-retrieval-output.md
Evidence: .10x/evidence/2026-08-15-compact-retrieval-output.md

# Compact Retrieval Output Review

## Scope

The independent review compared the complete candidate with
`origin/develop` and the compact-output decision, specification, ticket, and
evidence. It covered default compact text, legacy detailed text behind
`--explain`, exact JSON compatibility, detailed plan output, partial and
evidence-state failures, progress suppression, CLI validation order,
packaging, documentation, and the boundary around the stopped pure-global
ranking experiment.

## Finding closed during review

The first candidate checked the `--json --explain` conflict inside retrieval
dispatch, after the shared CLI entry point had already inspected removed
environment variables. That contradicted the required early-failure order.
The final candidate performs the conflict check immediately after argument
parsing. An adversarial regression supplies a removed legacy environment
variable and makes the later environment, configuration, model, catalog, and
provider seams fail if reached; it observes status 2, empty standard output,
and only the concise flag-conflict error.

## Presentation and compatibility findings

- Compact results preserve input hit order and render only count, one-based
  rank, single-line title, the ordered URL/repository-path/path/stable-ID
  citation fallback, optional section, and a whitespace-collapsed excerpt of
  at most 320 characters. Empty fields, singular/plural headers, and
  word-boundary truncation follow the specification.
- Partial-result namespace warnings and `assessment_failed` warnings remain
  prominent and content-free. The existing no-relevant-evidence and
  inconclusive branches run before presentation selection, so `--explain`
  cannot bypass abstention. Positive, observational, shadow, score, model,
  precision, tag, path, and namespace diagnostics are absent only from compact
  text.
- The detailed renderer after the new compact branch is the pre-amendment
  implementation. `--explain` changes only the renderer call; dry-run and plan
  paths deliberately ignore that presentation choice and retain their detailed
  provider-boundary output.
- JSON continues to serialize the original result directly. No result schema,
  ordering field, or presentation field changed. The three-mode regression
  observes identical explicit retrieval inputs and exact original JSON.
- The new progress context restores prior Transformers and Hugging Face Hub
  state, preserves the exact model constructors and inference arguments, and
  suppressed a real pinned cached routing-model load in the installed-wheel
  smoke without changing the model type.

## Retrieval boundary and validation

`retriever.py`, `routing.py`, `evidence.py`, `remote_catalog.py`, and
`config.py` are unchanged from `origin/develop`. The final source still calls
the existing namespace-covered top-k implementation and retains its promotion
diagnostics. The presentation flag is referenced only at the two text-renderer
calls and is never passed into routing, widening, namespace retrieval,
deduplication, MiniLM scoring, fusion, evidence assessment, or provider code.
No evaluation data, threshold, routing card, provider adapter operation, or
namespace state changed, and no provider write was performed.

The reviewer reran the final focused suite successfully on both supported
Python versions (`131/131` each), checked source validation and diff hygiene,
and verified the protected-file diff. The recorded unrestricted full suites
passed `690/690` on Python 3.11 and Python 3.13. The diagnostic wheel and source
archive contain 64 and 130 files and match the recorded SHA-256 values
`0e98acef07d5f6d13732b065be5fda3e379481a2cc692f3fd0b4b26d9b7a0264`
and
`5113cf18d81aba20056fd6f8f9ed37930c02e78dd73f5b19f6a5ff95d4498c72`;
the wheel's changed source files match the final worktree byte-for-byte. Clean
installation, CLI help, detailed-plan, hostile-conflict, and silent cached-model
smokes passed without publication or provider access.

## Verdict

PASS. The candidate implements the bounded compact-output task and restores
the established detailed format through `--explain` while preserving JSON,
plans, failures, result selection, per-corpus coverage promotion, evidence
decisions, and provider behavior. This verdict does not approve the rejected
pure-global ranking policy, change relevance thresholds, authorize provider
mutation, publish a release, merge the task, or claim that retrieval quality
itself improved.
