Status: active
Created: 2026-08-27
Updated: 2026-08-27

# Provider-Free Local Diagnostics Separate Debugging from Measurement

## Context

Two provider-free local attribution attempts applied one-shot/no-retry and immediate raw-failure deletion before their temporary harnesses were proven against the real target. Ordinary harness defects then became terminal and undiagnosable. One false-positive credential check was recoverable only through retained agent context; a later import-profile warm-up failed opaquely even though an ordinary exact-production import subsequently succeeded immediately.

No provider, credential, network, telemetry, model mutation, external service, release, deployment, or irreversible operation was involved. Applying live-operation irreversibility controls to this local diagnostic work reduced safety by destroying the information needed to diagnose harmless harness failures.

## Decision

For provider-free, credential-free, offline local diagnostics with no external or durable product side effect:

1. Harness debugging and measurement acceptance are separate phases.
2. The debugging phase MAY be repeated until the exact target command succeeds reliably.
3. Raw diagnostic output MAY exist temporarily long enough to diagnose failure. Before durable retention, private paths, environment values, credentials, process identifiers, host/user identities, and unrelated content MUST be removed; raw material MUST then be deleted.
4. Measurement counts, warm-ups, no-retry rules, and acceptance gates begin only after the exact target command and parser have passed debugging.
5. Security controls MUST be proportional to the target. Do not add a sandbox or minimal environment that changes native/import behavior unless that control is itself the subject or a named risk.
6. Provider credentials remain removed, telemetry disabled, offline controls enabled, and source/cache/store state checked where relevant.
7. Ordinary diagnostic observations MUST be labeled as diagnostics, not distributions, targets, benchmarks, or optimization authority.

This decision does not relax no-retry or cleanup rules for provider calls, credentials, external services, data mutation, release/deployment, global installation, irreversible operations, or ratified benchmark campaigns after measurement acceptance begins.

## Alternatives considered

- Keep one-shot harnesses for all diagnostics: rejected because repeated opaque harness failures blocked harmless local investigation.
- Remove all controls: rejected because credential, network, privacy, and state boundaries remain useful even for local diagnostics.
- Treat ordinary diagnostics as benchmark evidence: rejected because one-off debug observations do not establish repeatability or acceptance thresholds.

## Consequences

Future local attribution work can diagnose its own tooling before consuming measurement authority. Historical failed attempts remain immutable evidence, but they no longer block ordinary provider-free diagnosis or require successor campaigns merely to correct a temporary harness. Live and irreversible operation controls remain unchanged.
