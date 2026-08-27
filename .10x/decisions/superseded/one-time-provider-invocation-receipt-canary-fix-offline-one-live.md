Status: superseded
Created: 2026-08-25
Updated: 2026-08-25
Superseded-By: .10x/decisions/one-time-provider-invocation-receipt-final-recovery.md
Supersedes: .10x/decisions/superseded/provider-invocation-receipt-live-canary-attempts-are-permanently-stopped.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-renewed-canary-authorization.md
Ticket: .10x/tickets/2026-08-25-run-provider-invocation-receipt-canary-fix-offline-one-live.md
Knowledge: .10x/knowledge/exact-reproduced-package-digests-inherit-reviewed-safety.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Implementation-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Implementation-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md

# One-Time Provider Invocation Receipt Canary: Fix Offline, One Live

## Context

The provider-invocation receipt implementation remains exact at independently
reviewed source commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. At shaping baseline HEAD
`49de54138a1607e3b8fef1acfb779ecd541419f2`, tree
`97a64af52bc9edac104f27818c2bf22cf43f5544`, the current package and production
source bytes are identical to that reviewed source. The reviewed integration
evidence records a wheel with exact filename, version, size, 78-member
inventory, member/path/link safety, package metadata, source equality, and
SHA-256 identity.

The original canary and its recovery each consumed one preparation activation
and one build, then stopped before a live command. The recovery reproduced the
exact reviewed wheel digest but failed a newly introduced archive member-type
assertion before installation or live access. Both predecessor tickets remain
truthfully blocked, consumed, and ineligible. They are not reopened and grant no
new authority.

The owner has now explicitly superseded the permanent stop, selected **Fix
offline, one live**, and ratified the prior content-free live bounds. This new
decision creates one separate successor rather than revising either consumed
attempt.

## Decision

Authorize only
`.10x/tickets/2026-08-25-run-provider-invocation-receipt-canary-fix-offline-one-live.md`
as the successor execution owner. It starts `Status: open`, `Activation:
inactive`; this records-only decision does not activate preparation or live
execution.

### Exact source, build, and immutable wheel

Preparation MUST export exact reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, without changing repository refs.
It MUST run exactly one offline wheel build. Build-command start consumes the
single build authority. Build failure or any candidate identity mismatch blocks
the ticket with no rebuild.

The one output wheel MUST be exactly:

- filename `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`;
- version `0.5.2.dev87+g0b27c4eaa`;
- 730602 bytes;
- the established 78-member inventory; and
- SHA-256
  `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.

The output directory MAY also contain only uv's established regular,
nonsymlink `.gitignore` marker with exact one-byte content `*`. Absence of that
marker is accepted. No other output entry is accepted.

Once exact wheel identity matches, the executor MUST treat the wheel as the
same immutable bytes reviewed in the integration evidence and cryptographically
reuse its member inventory, path containment, link safety, package metadata,
entry point, and source-to-wheel evidence. The executor MUST NOT author or run
another archive member-type classifier.

### Provider-free correction boundary and preparation GO

Provider-free validators, isolated installation, and the provider-free harness
MAY be corrected and rerun against only that same immutable source export and
wheel until they pass or establish a real candidate defect. Corrections MUST NOT
rebuild, mutate, or substitute candidate bytes; read credential values;
construct or load the model; access provider/network; open telemetry database,
store, or API behavior; invoke telemetry commands; or touch user/global package,
tool, cache, repository-ref, or other global state.

Only bounded nonsensitive diagnostics MAY exist while correcting the harness.
They MUST contain no private values or paths and MUST be deleted before any
credential-value, model, provider, or network access. A real candidate defect
blocks without live access.

Complete provider-free preparation MUST bind exact current repository HEAD/ref/
worktree status, source/tree and candidate/runtime/package identities, bounded
process baseline, model cache roots/ref/assets/full manifest, exact model
identity and configuration without model construction, telemetry filesystem
identity by filesystem inspection only, intended credential-source presence
without opening it, and the approved case/dataset identities. It MUST bind the
approved case `m01-dagster-turbopuffer-quality` from dataset
`automatic-multi-corpus-retrieval-v1` at SHA-256
`29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`, and
cached model `BAAI/bge-small-en-v1.5` at revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, with unchanged production
automatic-device behavior and offline/no-download controls.

An independent reviewer MUST record explicit **GO** against complete sanitized
provider-free preparation evidence, the exact evidence commit/tree, and the
still-identical candidate wheel. No credential value may be read, model
constructed, provider/network accessed, or live command started before that GO.
Silence, partial/qualified/stale review, candidate drift, or NO-GO stops live
execution.

### Exactly one automatic live command

After exact GO, the isolated candidate MAY load the intended credential value
privately, construct the exact cached model under offline controls, and run
exactly one ordinary automatic command through the private in-process receipt
scope using the exact approved case/dataset above. Telemetry MUST remain
disabled. Provider activity MUST be read-only and limited to current strong
catalog reads and selected content reads. Catalog attempts MUST be at most 5 and
content attempts at most 18.

There is no preview, explicit command, substitution, alternate case/candidate,
receipt-only rerun, provider retry, or second command. Command start consumes
the sole live authority. Any command, process, receipt, privacy, side-effect, or
cleanup failure stops without retry.

The harness MUST preserve the original command return/exception/exit outcome
truthfully and separately. PASS requires a known successful original outcome
and one terminal receipt that strictly validates under both active
specifications, is canonical byte-identical compact UTF-8 JSON, remains
content-free, has catalog invocation count at most 5 and content invocation
count at most 18, and contains only successful begun operations and attempts.
Missing, incomplete, observer-failed, malformed, noncanonical, over-budget,
error, or interrupted receipt fails without inference or retry.

After the terminal outcome, all private source, wheel, build, install, runtime,
harness, raw output, diagnostic, process, manifest-with-path, temporary receipt,
credential, query, namespace/catalog/content/result, and other raw artifacts
MUST be deleted and absence verified. On PASS only the exact canonical sanitized
receipt plus bounded content-free evidence may remain. On failure no receipt or
partial ledger may remain. Exact model-cache and telemetry-filesystem identities
MUST be reproved unchanged, provider effects reconciled as read-only, and no
unrelated/global/ref state may change.

Independent final correctness, privacy, side-effect, receipt, and cleanup review
MUST pass before the successor ticket closes truthfully. No result may be used
to infer physical wire sends, SDK-internal retries, billing, cost, or rate-limit
behavior.

## Supersession and predecessor disposition

The former permanent-stop decision is canonical historical authority at
`.10x/decisions/superseded/provider-invocation-receipt-live-canary-attempts-are-permanently-stopped.md`.
Its former active path is retained only as a relative compatibility link for
immutable historical references. The link resolves to `Status: superseded` and
grants no authority.

Both consumed predecessor tickets MUST remain `Status: blocked`, `Activation:
consumed`, and `Eligibility: ineligible`. Neither can resume, rebuild, validate,
seek GO, execute live, or close as successful. Their immutable failure evidence
remains truthful. Only the new ticket receives the newly ratified one-build and
one-live-command authority.

## Alternatives considered

### Preserve the permanent stop

Rejected by the current explicit owner supersession.

### Reopen either consumed predecessor

Rejected. Reopening would erase attempt consumption and blur immutable failure
history. A separate successor keeps authority and evidence unambiguous.

### Add or rerun an archive member-type classifier

Rejected. Exact digest reproduction identifies the already reviewed wheel
bytes, so reviewed package-safety evidence applies cryptographically. A novel
stricter classifier is an unreviewed harness premise, not stronger candidate
identity.

### Rebuild after a build or digest failure

Rejected. One offline build is the ratified preparation bound. Failure or
mismatch blocks with no rebuild.

### Run more than one live command or retry a failed command/receipt

Rejected. The owner ratified exactly one automatic live command and no live
retry. Command start consumes authority regardless of outcome.

## Consequences

This decision permits provider-free harness correction without spending or
broadening live authority, but keeps candidate bytes immutable and the build
one-shot. A complete provider-free PASS still cannot cross credential/model/
provider/network boundaries without independent GO. One later automatic command
can produce one canonical content-free application-boundary receipt; every
failure remains forward-only. The receipt can prove only governed Buoy SDK call
attempts for that exact operation, not physical sends, SDK retries, billing,
cost, or rate limits.
