Status: active
Created: 2026-07-18
Updated: 2026-08-13
Amended-By: .10x/specs/automatic-multi-corpus-retrieval.md

# Interactive Apply Confirmation

## Bounded-retrieval amendment

This specification remains active for local preflight, interactive consent,
automation approval, and content/local-state mutation gates. The focused
boundary's removal of all catalog behavior is superseded only as authorized by
`.10x/specs/automatic-multi-corpus-retrieval.md`: a successfully confirmed
apply may register its routing card after content and local-state success, and
the separate catalog commands retain their own preview/`--approve` boundary.
Apply preflight, cancellation, and declined confirmation still perform no
catalog write.

## Purpose and scope

Make normal interactive `buoy apply` perform its named operation without removing explicit confirmation from durable writes. This specification owns apply mode selection, preflight/prompt behavior, cancellation, non-interactive behavior, output, and compatibility. Existing plan verification, locking, pending recovery, content sequencing, stale deletion, catalog registration, and failure contracts remain governed by their focused specifications.

## Modes and precedence

1. `--dry-run` and `--approve` together MUST fail with exit 2 before plan selection, model construction, credentials, state mutation, or remote calls.
2. `buoy apply --dry-run` MUST perform the established complete local preflight and exit 0 without prompting, model loading, credential lookup, pending/state mutation, or API calls.
3. `buoy apply --approve` MUST retain the established approved path and bypass interactive prompting. This is the supported automation/non-interactive write mode.
4. Plain `buoy apply` with an interactive stdin MUST perform complete local preflight, display the plan, and then prompt exactly `Apply this plan? [y/N] ` before any approved-only work.
5. Plain `buoy apply` with non-interactive stdin MUST fail with exit 2 before plan selection and direct the caller to `--dry-run` for preflight or `--approve` for confirmed execution. Piped text MUST NOT count as interactive approval.

Existing argument/schema/plan validation precedences within preflight and approved execution remain unchanged after mode selection.

## Interactive confirmation

- Prompting MUST use the actual stdin TTY boundary; no environment variable or config may auto-confirm.
- Case-insensitive exact input `y` or `yes`, after surrounding whitespace is stripped, confirms.
- Empty input, `n`, `no`, any other input, or EOF cancels without reprompting.
- The prompt MUST occur only after successful complete preflight and before model construction, credential lookup, namespace lock acquisition for approved work, pending creation, local-ledger mutation, or remote calls.
- Preflight MUST use a non-mutating DuckDB applied-state inspection path. Obsolete JSON applied-state files are inert under `.10x/decisions/duckdb-only-applied-state-hard-cutover.md` and MUST NOT affect this path.
- Confirmation MUST enter the same approved implementation as `--approve` and MUST revalidate all approved invariants rather than trusting stale preflight results.
- Existing `--delete-stale` intent remains part of the displayed plan and is executed only after confirmation. Confirmation never implies stale deletion when `--delete-stale` was absent.

## Cancellation

Cancellation is a successful no-op:

- exit 0;
- no model, credentials, pending artifact, local state, Turbopuffer call, content mutation, catalog mutation, or plan cleanup;
- text states that apply was cancelled and nothing was written;
- JSON stdout remains one valid object with existing preflight fields plus `approved=false`, `dry_run=false`, `cancelled=true`, `confirmation="declined_or_unavailable"`, `turbopuffer_api_calls=false`, `state_updated=false`, and `catalog_updated=false`;
- prompt and human diagnostics go to stderr so JSON stdout remains clean.

`--dry-run` is not cancellation: it reports `approved=false`, `dry_run=true`, `cancelled=false`, and does not prompt. Interactive cancellation deliberately reports `dry_run=false` because the user requested execution and then declined confirmation.

## Interactive output

For text mode, the complete preflight summary MUST be visible before the prompt. After confirmation, normal approved progress/final summary follows. For `--json`, a concise secret-free preflight summary and prompt may be written to stderr, while stdout emits exactly one final JSON document after confirmation or cancellation.

A prompt I/O failure is treated like safe cancellation, exits 0, and reports no writes. An approved-path failure after `y`/`yes` retains the existing nonzero and recovery contracts.

## Compatibility and documentation

- `--approve` remains supported and retains meaning.
- Scripts that used plain apply as preflight must migrate to `apply --dry-run`.
- Generated instructions, README/docs/help/changelog, and tests MUST present plain interactive apply as the normal flow, `--dry-run` as explicit preflight, and `--approve` as automation/non-interactive confirmation.
- Catalog mutation commands retain their own explicit `--approve` contracts; this change applies only to top-level `buoy apply`.

## Acceptance scenarios

- Interactive plain apply + `y` and `yes` executes the exact approved path.
- Interactive plain apply + Enter/no/arbitrary input/EOF exits 0 with zero side effects.
- Prompt occurs after visible successful preflight and before every approved-only constructor/read/write.
- Obsolete-JSON fixtures prove its presence and contents do not affect preflight, cancellation, or confirmed apply and remain byte-for-byte unchanged.
- Preflight failure never prompts.
- Non-TTY plain apply fails before plan/API work and names both supported flags.
- `--dry-run` succeeds non-interactively with complete preflight and no prompt/side effects.
- `--approve` succeeds non-interactively without prompt.
- `--dry-run --approve` fails at the mode gate.
- Text and JSON output remain truthful and JSON stdout stays parseable.
- `--delete-stale` behavior is unchanged and never activated by confirmation alone.

## Explicit exclusions

Interactive confirmation for catalog commands; automatic approval from configuration/environment; piping `yes`; changed stale deletion policy; changed apply sequencing/recovery; changed batching/model/precision defaults; remote plan storage; shared local ledger.
