Status: active
Created: 2026-07-18
Updated: 2026-08-13
Amended-By: .10x/decisions/buoy-owns-bounded-multi-corpus-retrieval.md

# Direct Commands Execute by Default

## Context

Historically, Buoy made `retrieve` a preview unless `--live` was supplied and
made `apply` a local preflight unless `--approve` was supplied. The user wanted
normal interactive commands to perform their named action while retaining
explicit previews and preventing accidental or non-interactive writes.

Retrieval performs read-only content queries against one explicit namespace or
the bounded automatic/multi-namespace selection restored by the later
multi-corpus decision.
Apply performs durable content and local-ledger writes, so silently making
plain apply mutate would weaken a safety boundary.

## Decision

- `buoy retrieve QUERY` executes live automatic routing and retrieval by
  default; one or more explicit `--namespace ID` values bypass routing.
- `retrieve --dry-run` and compatibility alias `--plan` request preview. The
  obsolete `--live` flag is removed because live execution is already the
  explicit-namespace default.
- Interactive `buoy apply` performs the complete local preflight, displays it,
  and then prompts `Apply this plan? [y/N]` before any model, credential,
  local-ledger, or remote work.
- Only case-insensitive exact `y` or `yes` confirms. Enter, `n`/`no`, any other input, or EOF cancels safely with exit 0 and zero mutation.
- `apply --dry-run` performs explicit preflight without a prompt. `apply --approve` remains the non-interactive/automation confirmation and bypasses the prompt.
- Plain non-interactive apply fails before plan work with exit 2 and directs the caller to `--dry-run` or `--approve`; piped input is not treated as interactive approval.
- `--dry-run` and `--approve` are contradictory.
- Existing stale-row deletion and all other content/apply safety gates remain unchanged.
- Cancellation and preflight remain genuinely mutation-free. Applied state is DuckDB-only under `.10x/decisions/duckdb-only-applied-state-hard-cutover.md`; obsolete JSON state is inert and receives no compatibility handling.

## Alternatives considered

- Keep both activation flags: rejected because it makes the primary commands behave as previews rather than their named actions.
- Make plain apply write immediately: rejected because it would remove explicit confirmation from durable and potentially costly writes.
- Use the prompt itself as the only apply preview: rejected because scripts and operators need an unambiguous, non-interactive zero-write preflight.
- Treat cancellation as an error: rejected because a deliberate safe decline is a successful no-op, not an operational failure.

## Consequences

Normal interactive usage becomes `buoy retrieve QUERY` (or an explicit
`--namespace ID` override) and `buoy apply`. Preview intent becomes explicit. Interactive cancellation reports
`dry_run=false, cancelled=true`; explicit `--dry-run` reports `dry_run=true,
cancelled=false`. Existing scripts that depended on plain retrieve being a
preview must add `--dry-run`; scripts that passed `--live` must remove it;
scripts that depended on plain apply being preflight must add `--dry-run`.
Existing `--approve` scripts remain compatible. Documentation, generated
retrieval commands, CLI help, JSON/text output, validation precedence, and
tests must change atomically with each command's implementation ticket. The
JSON applied-state hard cutover is a separate child outcome and does not remove
unrelated compatibility surfaces.
