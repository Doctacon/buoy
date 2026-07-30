Status: active
Created: 2026-07-19
Updated: 2026-07-19
Amended-By: .10x/specs/focused-buoy-boundary.md

# Buoy 0.4 Environment Alias Removal

## Focused-boundary amendment

The removed branded embedding aliases remain rejected exactly as specified.
Clauses for removed catalog, routing, discovery, evidence, or Command Center
commands no longer create compatibility authority. `TURBOPUFFER_NAMESPACE` is
ignored; retrieval and evals require one explicit CLI namespace.

## Purpose and scope

Remove fallback acceptance of exactly two deprecated branded embedding variables in Buoy 0.4.0:

- `TURBO_SEARCH_EMBEDDING_MODEL` -> `BUOY_EMBEDDING_MODEL`;
- `TURBO_SEARCH_EMBEDDING_PRECISION` -> `BUOY_EMBEDDING_PRECISION`.

No other `TURBO_SEARCH_*` variable is implemented, and this contract grants no authority over `TURBOPUFFER_*` variables.

## Dispatch boundary

After successful argument parsing and before dispatching any actual command handler, the CLI MUST inspect environment-variable presence. Presence includes an empty value.

If either removed variable is present:

- the invocation MUST return exit 2;
- stdout MUST be empty, including when `--json` is present;
- stderr MUST contain exactly one newline-terminated diagnostic and no warning in addition to it;
- no command handler, model loader, credential lookup, local state/artifact operation, or remote client call may begin.

Argument-parser errors occur before this gate and retain existing argparse behavior. Help/version requests terminate within parsing and remain available even when removed variables are present. A parsed invocation with no selected handler, including bare `buoy` or bare `buoy catalog`, retains its existing help behavior rather than being treated as an actual command.

The same boundary applies to `python -m buoy_search.autoresearch`: `--help` remains available, while a successfully parsed experiment invocation rejects removed-variable presence before reading the experiment or choosing/writing its output directory.

## Exact diagnostics

Diagnostics MUST never print either old or new variable value. They MUST use these exact forms:

- model only: `Removed environment variable is not supported in Buoy 0.4.0: TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL`
- precision only: `Removed environment variable is not supported in Buoy 0.4.0: TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION`
- both: `Removed environment variables are not supported in Buoy 0.4.0: TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL; TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION`

When both are present, the model mapping MUST precede the precision mapping regardless of process-environment insertion order. Old-only, old+new-equal, and old+new-different input all reject identically based on which old names are present. CLI model/precision overrides do not bypass the gate.

## Exact command coverage

The gate MUST cover every actual primary CLI command:

- `crawl`, `plan`, `apply`, `namespaces`, `retrieve`, and `evals`;
- `catalog list`, `catalog show`, `catalog upsert`, `catalog enable`, `catalog disable`, `catalog remove`, `catalog migrate-local`, `catalog reconcile`, and `catalog abandon-pending`;
- one successfully parsed `python -m buoy_search.autoresearch` experiment invocation.

Tests MUST cover each command handler with valid minimum arguments while replacing the handler with a sentinel that proves dispatch did not occur. They MUST also cover `buoy --help`, `buoy --version`, every top-level `buoy <command> --help`, every `buoy catalog <command> --help`, bare `buoy`, bare `buoy catalog`, `python -m buoy_search --help`, and `python -m buoy_search.autoresearch --help` with removed variables present. Help/version tests prove availability only and MUST NOT execute command behavior.

## Current configuration behavior retained

With neither old variable present:

- `BUOY_EMBEDDING_MODEL`, `BUOY_EMBEDDING_PRECISION`, defaults, CLI overrides, validation, and precedence remain unchanged;
- `TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, and command-specific `TURBOPUFFER_NAMESPACE` behavior remain unchanged;
- approved apply continues deriving effective embedding model and precision from its verified plan;
- old plans without `embedding_precision` remain interpreted as `float32` under their active contract;
- all parser, output, direct-command, state-root, plan, identifier, catalog, and migration compatibility outside the two named aliases remains unchanged.

Approved apply does not bypass the rejection gate: removed ambient names reject before plan discovery or verification even though the verified plan remains authoritative when no old name is present.

## State, data, and external effects

Rejection MUST occur before crawl/plan output creation, state-root discovery, plan reads, DuckDB reads/writes, model loading, embedding, credential access, remote catalog/content reads or writes, namespace mutation, deletion, or publication. The removal MUST NOT migrate configuration automatically, rewrite plans or ledgers, re-embed content, change deterministic IDs, mutate remote cards/rows/namespaces, or delete local/remote data.

## Acceptance scenarios

- Given only one removed variable, including an empty value, when any actual command is invoked with otherwise valid arguments, then it exits 2 with empty stdout and the exact one-mapping diagnostic before its handler runs.
- Given both removed variables in either environment insertion order, when any actual command is invoked, then it exits 2 and emits the exact model-then-precision diagnostic without either value.
- Given an old name and its new name with equal or different values, when a command is invoked, then the old name's presence rejects rather than selecting, warning, or comparing values.
- Given `--json`, when rejection occurs, then stdout remains empty and the sole diagnostic remains stderr text.
- Given help/version or a parsed no-handler invocation, when removed names are present, then existing help/version behavior remains available.
- Given malformed arguments, when parsing fails, then existing argparse exit/output occurs and the removed-variable gate does not replace it.
- Given no removed names, when commands run, then current `BUOY_*`, plan-derived apply, parser, state/data, and remote behavior is unchanged.

## Acceptance criteria

- Deprecated fallback/warning/conflict selection is removed for exactly the two named old variables, while a minimal presence detector enforces this contract at the pre-dispatch boundary.
- Focused tests cover the complete command/help/version matrix, all old/new combinations, empty values, both insertion orders, exact bytes/streams/exit status, sentinel non-dispatch, and pre-read/pre-write side-effect boundaries.
- Existing current-variable/default/CLI/plan precedence tests and the complete supported Python suite pass.
- User documentation and changelog list both exact substitutions, the exit-2 migration failure, help/version exception, value redaction, and absence of state/data/remote effects.
- Evidence records exact focused/full commands and results, representative stderr bytes, empty stdout under `--json`, sentinel traces, no-side-effect observations, and independent review.

## Explicit exclusions

Console alias removal; changes to current variables/defaults; changes to `TURBOPUFFER_*`; plan-schema changes; state/data migration; remote operations; version/tag/publication work; removal of any unrelated compatibility; correction of stale `.pi/skills/turbopuffer-site-rag/references/scrapling-site-workflow.md` direct-command guidance.
