Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/tickets/2026-08-25-run-provider-invocation-receipt-canary-fix-offline-one-live.md, .10x/decisions/one-time-provider-invocation-receipt-canary-fix-offline-one-live.md

# Provider Invocation Receipt Successor Preparation Failure

## What was observed

Provider-free preparation began only after the separate successor activation
commit `f2bbe83658b2f04abb5ddf25daa84cae679abfed`, tree
`592b51aef984c1a427b0821504662cd5a82d28d1`. That activation bound clean
pre-activation HEAD `7723bd96f00fa72d4c280f4a227f5f767f4ecf52`, tree
`57627acf1bacf378cd0227f8aa5f1919d1f2cd8a`, the exact task branch and
worktree registration, and package-relevant equality with reviewed source
commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`.

One owner-private mode-0700 root outside the repository received one no-ref
archive export of the exact reviewed source. The export contained no Git
metadata. All seven required source/package SHA-256 identities passed, including
`pyproject.toml`, `uv.lock`, the private receipt module, retriever, remote
catalog, CLI, and routing artifact. The frozen lock check passed offline.

Exactly one offline wheel-only build command began once. Build start consumed
the ticket's sole build authority. It exited nonzero before producing a wheel
because the detached export's build environment did not supply version
discovery in the form accepted by the pinned VCS build backend. The sanitized
category is `build_environment_version_discovery_failure` within
`offline_wheel_build_failure`. The build was not retried, corrected, or
substituted. No wheel filename, version, size, or SHA-256 was accepted, and the
prior reviewed wheel digest was not claimed for this failed attempt.

## Stop boundary and cleanup

The failure is terminal under the successor's one-build contract. No archive
member-type classifier was authored or run. No isolated candidate runtime or
package installation began. No provider-free package, routing, receipt, or
harness validator ran after the build failure. No credential source was opened,
read, sourced, copied, or hashed; no credential value was obtained. No model
was imported through the candidate, constructed, loaded, or run. No telemetry
database, store, API, or command was opened or invoked. No DNS, TLS, provider,
network, retrieval preview, explicit retrieval, automatic retrieval, or live
command began.

The build command used the established offline package cache and created a
transient build workspace there. That workspace was absent after command
termination, but using it crossed the stricter no-global-cache-touch preparation
boundary and no complete cache-wide pre/post equality was established. This is
a second terminal preparation failure category,
`global_build_cache_boundary_violation`.

The complete owned preparation root was removed, including source export, build
output, logs, scripts, and partial state, and absence was verified. The
repository remained clean at the activation commit before this bounded failure
record was written. No source, test, specification, lock, routing, dataset,
model-cache, credential-source, telemetry, provider, global Buoy, release,
deployment, publication, push, or repository worktree/ref change was made by
preparation.

## What this supports or challenges

This supports exact activation ordering, exact source export and pre-build
identities, one passing frozen offline lock check, exactly one failed wheel-only
offline build start, fail-closed no-rebuild behavior, no live access, bounded
owned-root cleanup, and truthful disclosure of the global-cache boundary breach.

It challenges every preparation criterion requiring an exact reproduced wheel,
isolated installation, provider-free candidate validation, retained immutable
candidate/runtime/harness, complete preparation evidence, independent GO, or a
live receipt. The ticket is blocked, its preparation activation and build
authority are consumed, and no preparation correction or live execution may
resume under it.

## Limits

No candidate wheel or receipt exists. This evidence does not establish installed
package identity, current model/cache, telemetry-filesystem, or global package-
cache equality, provider behavior, application-boundary invocation counts,
physical sends, SDK retries, billing, cost, or rate-limit effects. It grants no rebuild, alternate export,
substitution, validator rerun, GO, credential/model/provider/network access, or
live command.
