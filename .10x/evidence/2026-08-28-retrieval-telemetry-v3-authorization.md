Status: recorded
Created: 2026-08-28
Updated: 2026-08-28
Relates-To: .10x/research/2026-08-28-retrieval-telemetry-current-state-and-gaps.md

# Retrieval Telemetry V3 Authorization

## What was observed

After receiving the current-state audit, the repository owner explicitly authorized implementation of retrieval telemetry updates and ratified these exact choices:

- supersede the canary-only limitation for provider invocation accounting;
- introduce observation/storage schema v3 with both inference-worker visibility and content-free Buoy SDK call-attempt accounting;
- preserve the strict privacy boundary: no query text/hash, namespace/corpus/result/provider identifiers, content, paths, credentials, responses, raw errors, or ambient trace context;
- keep telemetry opt-in through `BUOY_TELEMETRY=local`; and
- permit at most 20 bounded Turbopuffer calls after provider-free validation passes, after which new approval is required.

The authorization permits read-only retrieval/catalog use for validation. It does not authorize provider writes, catalog mutation, telemetry network export, model downloads, cache mutation, default-on telemetry, release/publication, or collection of prohibited data.

## Procedure

The assistant presented four explicit decisions: feature scope, privacy, enablement, and live-validation budget. The owner selected worker plus SDK v3, strict privacy, opt-in enablement, and supplied the custom upper bound of 20 bounded calls.

## What this supports

This observation ratifies the semantic choices needed to create focused v3 specifications, a superseding decision, and bounded implementation tickets. It authorizes implementation only after the specification/ticket gate and provider-free validation before live calls.

## Limits

- Twenty is an authorization ceiling, not a target or requirement.
- Physical HTTP sends, SDK-internal retries, provider billing, and rate-limit units remain outside the accepted `provider_client_invocation` meaning.
- Exact live cases and a lower execution budget must be fixed by the validation owner before any live call runs.
- 2026-08-29 closure note: provider-free evidence proved implementation acceptance, so no live call ran and none of the ceiling was consumed. The phrase “20 bounded calls” remained ambiguous between CLI executions and `provider_client_invocation` units; a future live campaign must ratify that unit rather than inherit an interpretation.
