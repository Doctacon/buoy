Status: open
Created: 2026-08-24
Updated: 2026-08-24
Parent: None
Depends-On: .10x/tickets/2026-08-24-validate-provider-invocation-receipt-integration.md
Decision: .10x/decisions/one-time-live-provider-invocation-receipt-canary.md
Authorization-Evidence: .10x/evidence/2026-08-24-provider-invocation-probe-and-live-canary-authorization.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Historical-Canary: .10x/evidence/2026-08-24-local-telemetry-v2-canary.md
Historical-Pilot: .10x/evidence/2026-08-24-v0-6-3-installed-telemetry-pilot.md

# Run One-Time Live Provider Invocation Receipt Canary

## Outcome

After the exact fake-only provider-invocation receipt integration passes
independent review, run one automatic live retrieval through the private
in-process receipt harness. Accept and retain only one strict canonical
content-free receipt with catalog attempts at most 5 and content attempts at
most 18, while preserving the original command outcome and leaving telemetry,
model cache, provider write surfaces, global tools, and unrelated state
unchanged.

## Dependency and activation gate

Before activation, the integration dependency MUST be `done` at one exact
commit with complete fake-only evidence and independent PASS review of that
exact commit. The review MUST confirm both active receipt specifications still
match implementation, the private scope remains default-off/non-public, all
source-owned call sites and concurrency/failure paths are covered, exact CLI
receipt recertification is coherent, and no telemetry-v2 or routing semantic
changed.

This ticket is open and inactive. Creation records future one-time authority but
MUST NOT activate the ticket, build a wheel, access the model/cache/credential/
provider/store, or run the canary in this turn.

## Pre-operation candidate and identity gates

In an owner-private temporary root outside the repository:

1. check out/export the exact independently reviewed integration commit without
   changing repository refs or worktrees;
2. build exactly one candidate wheel from that commit using its locked runtime;
3. verify source commit/tree, clean package-relevant diff, wheel digest/member
   safety, metadata/version, sole entry point, dependency lock, private receipt
   source identities, final CLI SHA-256, and exact routing-artifact CLI receipt;
4. install the wheel only into one isolated temporary runtime and prove the
   installed package manifest reproduces the reviewed source identities; and
5. run only provider-free isolated help/import/receipt-validator checks required
   to establish candidate identity before external access.

There MUST be no user/global install, replacement, uninstall, rollback, release,
deployment, publication, push, ref mutation, or invocation of an installed
global Buoy. Any identity or isolated validation failure stops before provider
access. Building/validation is not retried under this ticket; a changed
candidate requires a separately reviewed dependency state and fresh activation.

Bind content-free pre-state immediately before command start:

- repository refs/worktree and exact candidate/runtime/package identities;
- current host/platform/architecture and production automatic device class;
- exact approved dataset SHA-256 and private case extraction success;
- existing intended credential-source presence after inherited credentials are
  removed, without reading it into retained output;
- exact model/cache root set, ratified model ref, and full cache manifest;
- real telemetry root/store/queue/receipt/backup filesystem manifest, bytes,
  modes, link counts, and content digests without opening the database or
  invoking telemetry; and
- process/external-side-effect baseline sufficient to detect an independent
  candidate child, telemetry writer/migration, installer, or harness survivor.

Preflight MUST prove exact cached model `BAAI/bge-small-en-v1.5` revision
`5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, complete local assets, float32,
production automatic-device behavior, enforced offline/no-download mode, and
unchanged source expectation. It MUST NOT clear/repair/touch caches or force a
device.

## Exact one-command harness

The private harness MUST:

1. remove inherited provider credentials and all telemetry enablement;
2. load the existing intended credential source only inside the private child
   environment, never into argv/stdout/stderr/records;
3. privately load the exact approved automatic case
   `m01-dagster-turbopuffer-quality` from
   `automatic-multi-corpus-retrieval-v1` at SHA-256
   `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`;
4. enter the underscore-prefixed private in-process receipt scope;
5. run the isolated candidate's ordinary automatic live command operation once
   against the current remote catalog and selected current content namespaces;
6. preserve its exact original return/exception/exit outcome outside the scope;
   and
7. after scope exit and terminal command state, request receipt bytes once and
   hand the same immutable bytes to strict validation.

The harness MUST NOT expose a CLI/environment/public activation, automatically
write a receipt, enable telemetry, or invoke apply/catalog-management/write
code. Exactly one automatic command may begin. There is no preview, explicit
retrieval, second command, substitution, rerun, receipt-only rerun, or provider
retry. Command start consumes the sole live authority.

## Provider and network boundary

Network access is restricted to DNS/TLS/provider endpoints and calls reached by
the unchanged automatic read path after the exact gates pass. The allowed
application operations are current strong remote-catalog reads and selected
content retrieval reads only. Provider/catalog/card/namespace/content create,
update, upsert, delete, repair, migration, management, or other mutation MUST be
denied by source/diff inspection and runtime guard where mechanically possible.
No remote telemetry export or model/network download is allowed.

The harness does not intercept transport, inspect packets, retain endpoints, or
claim wire-send identity. SDK-internal retries and physical sends remain
unknown. Existing provider credential use may have unobserved provider-side
billing/rate-limit effects; the receipt does not measure or authorize a claim
about them.

## Exact receipt validation and acceptance

Validation occurs only after the original operation is terminal. It MUST use
the reviewed strict decoder/validator against the immutable in-process bytes
and independently verify:

- non-null bytes, valid UTF-8, length at most 65,536, canonical compact sorted-key
  JSON, no duplicate/unknown/missing keys, and byte-identical decode/validate/
  re-encode round trip;
- top-level exact keys and values, including integer schema version 1 and unit
  `provider_client_invocation`;
- exact catalog/content keys, types, integer-not-boolean rules, enums, counts,
  sums, operation/attempt ordering, content attempt grammar, catalog source-
  order reachability, outcome consistency, and active-spec maxima;
- catalog was begun for automatic retrieval and its `invocation_count` is at
  most 5;
- content `invocation_count` is at most 18;
- every begun catalog/content operation and attempt has only accepted successful
  terminal structure: any `error` or `interrupted` outcome fails; and
- receipt bytes and all validator diagnostics contain none of the prohibited
  privacy sentinels, with invalid reasons fixed and value-non-echoing.

The catalog/content 5/18 values are post-operation receipt acceptance gates,
not pre-operation kill switches or evidence of physical transport sends,
billing, cost, SDK retries, or rate-limit consumption. They cannot be inferred
when the receipt is missing. Missing, incomplete, observer-failed, invalid,
noncanonical, over-budget, error, or interrupted receipt fails the canary with
no retry. Source maxima, command success, logical telemetry spans, output shape,
or provider behavior MUST NOT substitute for receipt evidence.

Receipt validation is observational. It MUST preserve and report the original
command outcome truthfully and separately. Receipt failure MUST NOT replace,
wrap, suppress, change, or retroactively label the original command outcome.
An original command error/interruption fails the canary even if finalization
produces otherwise parseable bytes.

## Telemetry, cache, and unrelated-state invariants

Telemetry remains disabled throughout. Do not invoke telemetry status, migrate,
flush, writer, store/database read, queue, export, or purge operations. The
real telemetry root and every pre-bound store/queue/receipt/backup artifact MUST
be byte/manifest-identical after command termination and after cleanup; any
change fails the canary.

The model cache root/ref/full manifest MUST be byte/type/target-identical before
and after candidate preparation, command termination, and cleanup. Any model or
cache mutation, new download artifact, ref drift, or device-forcing state fails.
OS/model caches MUST NOT be cleared or repaired.

Repository source/tests/records outside this ticket's evidence/progress/review,
refs, worktrees, global tools, releases, deployments, provider write state,
credential source, non-Buoy processes, and unrelated filesystem state MUST be
unchanged. Any unexpected mutation stops cleanup from widening beyond owned
temporary artifacts and is escalated without retry.

## Process and external side-effect inventory

The execution evidence MUST reconcile:

- one isolated source/wheel/runtime/harness root created and later deleted;
- one automatic command child begun once and terminal, with no surviving
  descendants;
- no independent telemetry writer/migration or global installer process;
- expected provider read boundary only, with no write/management path;
- model inference/cache-read and automatic device selection only, no download or
  cache mutation;
- credential source read inside the child only, no value output/persistence or
  mutation;
- no telemetry/store/database open or write;
- no package/global install, release, deployment, ref, hosted, or unrelated
  mutation; and
- one accepted canonical receipt plus bounded evidence retained only on PASS;
  no raw or partial receipt retained on failure.

## Failure, no-retry, and cleanup

- A pre-command failure stops and cleans owned temporary artifacts without
  consuming live authority; activation ends and no alternate candidate may run.
- Command start consumes live authority. Nonzero/raised/interrupted/uncertain
  outcome, process loss, side-effect violation, missing/invalid/rejected receipt,
  privacy failure, or cleanup uncertainty fails and stops with no retry.
- Preserve the original exception/exit/return truth. Observer/validator/harness
  failure never changes it and never authorizes another command.
- On interruption, terminate only the owned candidate process tree best effort,
  preserve generic truthful outcome, and clean owned temporary artifacts.
  Uncertain termination is failure and escalation, not retry authority.
- Delete query, argv, namespace/card/catalog/content/result values, credential
  material, paths, raw stdout/stderr, errors/stacks, private receipt copies,
  scripts/harness, source tree, wheel, isolated runtime, raw logs, process
  samples, path-bearing manifests, and analysis artifacts after sanitized
  evidence is written. Verify absence.
- Never print, persist, hash for retention, or place the credential value in a
  process argument. Private-literal scanning may hold values only in memory and
  MUST emit only pass/fail and bounded counts.

## Retention and privacy

On PASS, retain indefinitely only:

- the exact canonical validated receipt bytes in a bounded evidence storage
  artifact and/or verbatim canonical content-free representation;
- exact candidate commit/tree/wheel/runtime/package/receipt-source identities;
- content-free host/model/revision/precision/device/cache/store identities;
- generic original command outcome and canary acceptance outcome;
- bounded process/external-effect, privacy, cleanup, and review evidence; and
- this ticket/decision/specification graph.

Do not retain query or hash, argv, executable/cache/store/credential paths,
environment values, namespace/card/catalog/provider/account identity, content,
result, URL, request/response/billing payload, credential/token/key/header, raw
output/error/status/message/traceback/stack, timestamp/duration, trace/span/
thread/process ID, ambient context, host/user name, or hardware serial. The
canonical receipt itself MUST meet the stricter active lifecycle privacy
contract. On failure, do not retain receipt bytes or partial ledger.

## Acceptance criteria

- Exact reviewed fake-only integration dependency and independent PASS review
  are bound before activation.
- One isolated exact candidate wheel/runtime passes identity and provider-free
  gates without global install/release/deployment/ref mutation.
- Exactly one automatic live command begins through the private in-process
  receipt scope, using the existing intended credential source, current remote
  catalog, approved private case, exact cached model revision, float32,
  production auto-device, offline/no-download operation, and telemetry disabled.
- Original command outcome is preserved truthfully and separately from receipt
  acceptance; no retry or substitution occurs.
- One terminal canonical receipt passes every strict specification rule, has
  catalog invocation count <=5 and content invocation count <=18, and contains
  no error/interrupted outcome or prohibited value.
- Missing/invalid/over-budget/error/interrupted receipt fails without inference
  or retry; evidence makes no wire/billing/cost/rate-limit claim.
- Provider activity is read-only; cache and real telemetry-store identities are
  exact pre/post; no unrelated mutation occurs.
- Only canonical accepted receipt plus bounded content-free evidence remains;
  every query/argv/namespace/content/result/credential/path/raw/harness/runtime
  artifact is deleted and absence verified.
- Independent correctness/privacy/side-effect review passes the exact execution
  evidence commit before closure. Review explicitly checks the canonical bytes,
  5/18 post-operation semantics, original outcome preservation, identities,
  cleanup, and no-unrelated-mutation inventory.

## Evidence expectations

Record exact activation, candidate source/tree/wheel/installed-package/runtime
identities; governing independent integration review; generic preflight ledger;
model/cache and telemetry-store pre/post equality; one command start/terminal
ledger without argv/PID/timestamps; original outcome; canonical receipt bytes
and strict-validator verdict; exact family counts/outcomes; privacy scan;
provider-read/no-write and external-effect inventory; cleanup absence; changed
paths/diff/status; and independent review. State explicitly that receipt counts
are application-boundary attempts and do not prove transport sends, billing,
or rate-limit use.

## Explicit exclusions

More than one command; preview/explicit/substituted/retried retrieval; receipt-
only rerun; public/CLI/env receipt activation; automatic receipt persistence;
telemetry-v2 field/span/envelope/store/retention change; telemetry command,
store/database open, migration, flush, writer, purge, or real-store mutation;
provider/catalog/card/namespace/content write/repair/management; model download,
cache mutation/clearing/repair, forced device; credential print/persistence/
mutation; global install/uninstall/rollback; release, deployment, publication,
push, ref/hosted mutation; transport interception or wire/billing/cost/rate-limit
claim; unrelated cleanup or source widening.

## Blockers

- `.10x/tickets/2026-08-24-validate-provider-invocation-receipt-integration.md`
  and its three predecessors are open/inactive. The final integrated fake-only
  commit does not exist and has not passed independent implementation review.
- This canary ticket has not been explicitly activated.

No semantic or operational-contract blocker remains. Satisfying the dependency
does not automatically activate this ticket.

## Progress and notes

- 2026-08-24: Created after exact owner ratification as a separate one-time
  downstream canary. Ticket remains open/inactive and depends on reviewed final
  fake-only integration. No source/test edit, activation, build, wheel, model,
  cache, credential, provider, network, telemetry, store, database, global-tool,
  release, deployment, or canary operation occurred in this records-only turn.
