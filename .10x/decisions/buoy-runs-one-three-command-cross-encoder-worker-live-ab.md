Status: active
Created: 2026-08-28
Updated: 2026-08-28

# Buoy Runs One Three-Command Cross-Encoder Worker Live A/B

## Context

The scoring-capable schema-v2 local worker is implemented and independently reviewed. Provider-free evidence proves exact score parity at 1, 24, 49, and 108 pairs and isolates 7.46–7.93 seconds of process-cold CrossEncoder import/runtime initialization. It does not establish the end-to-end effect in a real automatic retrieval command where catalog and namespace network latency remain confounders.

A prior embedding-only worker campaign used the automatic query `How is approximate vector recall evaluated?` and exactly three baseline/cold/warm commands. Reusing that query provides procedural and historical continuity, but remote catalog/content state may have changed, so old and new outputs cannot be assumed equal.

Live calls require explicit bounded authority because they read provider catalog/content data, use a credential, incur external cost, and may expose result content transiently to the client harness.

## Decision

Authorize exactly one three-command, automatic, read-only live A/B using this fixed query:

```text
How is approximate vector recall evaluated?
```

Run once each, in this order:

1. `--no-embedding-worker` process-cold in-process baseline;
2. default schema-v2 cold worker; and
3. default schema-v2 warm worker reusing the same resident embedding/cross-encoder models.

No command may be retried, replaced, reordered, or supplemented. A failure or contract mismatch stops all remaining commands. No fourth live command is authorized.

The campaign will retain only redacted counts, booleans, wall timings, bounded worker RSS/reuse/cleanup observations, and SHA-256 identities for complete output, payload, route, and structural shape. Raw stdout/stderr may exist only in private temporary files long enough to parse and reduce them; decoded provider objects must be released and raw files deleted before worker idle waiting. No result text, URL, namespace value, route value, query output, credential, PID, socket path, raw provider response, or raw error is retained.

Telemetry is disabled, model loading is offline/local-only, and source plus both model-cache identities are checked before and after. The campaign performs no provider write, apply/index/catalog mutation, model download, cache repair, install, release, deployment, or publication.

## Alternatives considered

- **Skip live evidence:** rejected because provider-free parity does not show observed end-to-end behavior after both local models became resident.
- **Run more samples:** rejected because network variance would require a materially larger campaign and cost; this campaign is a bounded observation, not a distribution.
- **Use a new query:** rejected because the owner selected continuity with the prior worker A/B.
- **Enable telemetry for stage attribution:** rejected to preserve the prior campaign's privacy/no-store boundary; this campaign measures wall behavior and parity only.
- **Compare only to historical timings:** rejected because current remote and source state differ; the new three commands form their own within-campaign comparison.

## Consequences

The campaign can establish one observed baseline/cold/warm result and whether outputs/routes remain identical under current live conditions. It cannot establish percentiles, an SLA, causal provider-adjusted savings, cold-host behavior, or a release gate. Provider/network variance and command ordering remain confounders.

The authorization is consumed when the first live command starts. Harness debugging and all provider-free gates must finish before that point. No automatic default, release, deployment, or further campaign follows from the result.
