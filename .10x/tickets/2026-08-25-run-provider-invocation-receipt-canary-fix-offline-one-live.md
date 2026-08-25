Status: blocked
Created: 2026-08-25
Updated: 2026-08-25
Parent: None
Depends-On: .10x/tickets/done/2026-08-24-validate-provider-invocation-receipt-integration.md
Activation: consumed
Eligibility: ineligible
Preparation-Failure: .10x/evidence/2026-08-25-provider-invocation-receipt-successor-preparation-failure.md
Decision: .10x/decisions/one-time-provider-invocation-receipt-canary-fix-offline-one-live.md
Authorization-Evidence: .10x/evidence/2026-08-25-provider-invocation-receipt-renewed-canary-authorization.md
Knowledge: .10x/knowledge/exact-reproduced-package-digests-inherit-reviewed-safety.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Implementation-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Implementation-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md
Consumed-Predecessor: .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md
Consumed-Recovery: .10x/tickets/2026-08-24-recover-one-time-live-provider-invocation-receipt-canary.md
Superseded-Stop: .10x/decisions/superseded/provider-invocation-receipt-live-canary-attempts-are-permanently-stopped.md

# Run Provider Invocation Receipt Canary: Fix Offline, One Live

## Outcome

From the exact reviewed source, reproduce one exact wheel with one offline build,
correct and complete provider-free preparation against those immutable bytes,
obtain independent GO, then run exactly one ordinary automatic live command in
the private receipt scope. PASS only with a successful original command and one
strict canonical content-free receipt whose catalog count is at most 5, content
count is at most 18, and every represented operation and attempt is successful.

## Cold-start authority and scope

This ticket is the only executable successor created by
`.10x/decisions/one-time-provider-invocation-receipt-canary-fix-offline-one-live.md`.
The two predecessor tickets remain blocked, consumed, and ineligible; do not
resume or edit their execution history. Their failures are historical inputs,
not execution authority.

This ticket is open and inactive. Creation does not authorize source export,
build, installation, operational inspection, credential access, model
construction, telemetry behavior, provider/network access, or canary execution.
A separate activation record MUST bind this exact ticket/decision graph and the
then-current clean repository HEAD/tree/ref/worktree state before preparation.
Activation permits the provider-free preparation phase only. Independent GO is
a later, separate gate for credential-value/model/provider/network/live access.

No implementation source, test, specification, package lock, routing artifact,
production data, global tool, repository ref, provider state, telemetry store,
model cache, credential source, or unrelated state may be changed under this
ticket.

## Exact immutable source and package authority

Export exact reviewed source commit
`0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, into one mode-0700 owner-private
temporary root outside the repository. Use an archive/detached export that does
not create or mutate repository refs or worktrees. The exported source MUST
reproduce these reviewed/current SHA-256 identities before the build:

| Path | SHA-256 |
| --- | --- |
| `pyproject.toml` | `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22` |
| `uv.lock` | `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254` |
| `src/buoy_search/_provider_invocation_receipt.py` | `73361cde0ad7fad2906d01c10a7044f1a7ff34d28425e987f4265e7f60404349` |
| `src/buoy_search/retriever.py` | `89aeb5db61a1997f127db2ebe651beb9f184d4358e0e0cd3d98921713c9b613d` |
| `src/buoy_search/remote_catalog.py` | `3d859a21c257f7edaf113593aa486defdc78d1c89d45367811d0ac9ce991399d` |
| `src/buoy_search/cli.py` | `c6b575e160c5379b8a7214b3434a06d47864f0414e1478f44bcddeff313609ce` |
| `src/buoy_search/data/automatic_routing_confidence_calibration.json` | `79c780a5c3ffebfe5569d463663c30d681cf224aec3ddfb1e03202641b97ed1e` |

Run the established frozen lock check offline before build. Then run exactly one
wheel-only offline build using the reviewed locked package tooling. Build-command
start consumes the one build authority. The build MUST NOT produce an sdist.
Build failure or any source/wheel identity mismatch is terminal preparation
failure: stop, clean owned artifacts, record bounded sanitized evidence, and do
not rebuild.

Require exactly one regular nonsymlink wheel with all exact identities below:

| Identity | Exact value |
| --- | --- |
| Filename | `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl` |
| Version | `0.5.2.dev87+g0b27c4eaa` |
| Bytes | `730602` |
| Established members | `78` |
| SHA-256 | `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87` |

Enumerate output-directory entries separately from wheel identity. The only
optional additional entry is uv's regular nonsymlink `.gitignore` marker with
exactly one byte, `*`; absence is accepted. Reject any other file, directory,
link, second wheel, sdist, or hidden entry.

Once filename, version, size, source, and SHA-256 match, the bytes are the exact
wheel already reviewed in
`.10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md`.
Reuse its established 78-member inventory, member/path/link safety, package
metadata, sole entry point, routing/source identities, and source-to-wheel
equality cryptographically. DO NOT author or run another archive member-type
classifier. Do not reinterpret a harness-only classifier disagreement as a
candidate defect after exact digest identity is established.

## Provider-free correction and validation phase

Keep the exact source export and wheel immutable. Provider-free validators,
isolated installation, dependency setup, and harness checks MAY be corrected
and rerun against only that same source/wheel until either all preparation gates
pass or evidence establishes a real candidate defect. A correction may change
only owned temporary harness/runtime material outside the repository. It MUST
NOT:

- rebuild the wheel or mutate/substitute candidate/source bytes;
- author or run an archive member-type classifier;
- read, source, copy, print, hash for retention, or expose a credential value;
- construct, import through the candidate, or run the model;
- access provider, DNS, TLS, network, catalog, content, or remote telemetry;
- open a telemetry database/store/API or invoke telemetry status, migration,
  flush, writer, queue, receipt, backup, export, or purge behavior;
- install, replace, uninstall, or invoke a user/global Buoy or tool;
- touch model caches, credential source, repository refs/worktrees, global
  package caches, user home state, or unrelated/global state; or
- run preview, explicit retrieval, automatic retrieval, or any other command
  operation that can reach provider/model behavior.

Provider-free checks MUST establish exact isolated installed distribution/module
version, entry point, package manifest, reviewed production-source hashes,
routing artifact/production loader authority, executable and module help,
private receipt import, and strict receipt encode/decode/validator behavior.
Ambient editable source or `PYTHONPATH` MUST NOT satisfy installed-package
checks. Every rerun must bind the same immutable wheel digest.

While correcting the harness, retain only bounded nonsensitive diagnostics
needed to distinguish harness/environment failure from a real candidate defect.
Diagnostics MUST use generic categories/counts, contain no private value or path,
and stay only in the owned temporary root. Delete them and verify absence before
requesting GO or crossing any credential-value/model/provider/network boundary.
If a real candidate defect is established, stop without live access or rebuild,
clean owned artifacts, and retain only bounded sanitized failure evidence.

## Complete provider-free preparation ledger

Before independent GO, bind all of the following with content-free exact
identities and equality checks:

1. then-current repository HEAD/tree/ref/worktree list and clean status, plus no
   package-relevant drift from the reviewed source;
2. exact exported source commit/tree/hashes, one-build count, wheel/output-marker
   identities, isolated runtime/dependencies/installed package, and every
   provider-free validator/harness correction and final result;
3. a bounded process baseline proving no candidate child, installer, telemetry
   writer/migration/flush, or harness survivor outside the owned preparation;
4. exact current model/cache root set, file types/targets/content manifest,
   established 159-entry manifest SHA-256
   `c395f5807452ede94efade87f5be77c0492911e6ac5936a85ce9aaf72ac4263f`,
   cached model `BAAI/bge-small-en-v1.5` revision
   `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, complete assets, float32
   configuration, unchanged production automatic-device source behavior, and
   enforced offline/local-only/no-download controls, without model construction;
5. exact current real telemetry root/store/queue/receipt/backup filesystem
   manifest, bytes/digests, modes, types, links, and targets by filesystem
   inspection only, with telemetry disabled and no database/store/API open;
6. intended credential-source presence as the expected regular nonsymlink file
   after inherited provider credentials are removed, without opening or reading
   the source or value;
7. dataset `automatic-multi-corpus-retrieval-v1` at exact SHA-256
   `29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b`
   and private successful extraction of exact case
   `m01-dagster-turbopuffer-quality`, retaining no query, namespace, card,
   content, result, or private path; and
8. source/runtime guards proving the ordinary automatic path is read-only at the
   provider, telemetry stays disabled, catalog/content receipt gates are 5/18,
   and no write/management/global/ref path is reachable from the harness.

The preparation evidence MUST be bounded and sanitized. Keep the exact accepted
candidate/runtime owner-private and immutable while review is pending.

## Independent GO gate

An independent reviewer MUST inspect the exact sanitized preparation evidence
commit/tree, this ticket and decision, both active receipt specifications,
reviewed package evidence, immutable wheel/source/runtime identities, provider-
free correction history, current repo/process/cache/model/telemetry-filesystem/
credential-source-presence/case/dataset bindings, privacy, and no-unrelated-
mutation state.

The reviewer MUST record explicit **GO** or **NO-GO** tied to the evidence
commit/tree and exact candidate SHA-256. The reviewer does not rebuild, rerun
preparation, inspect credential values, construct the model, open telemetry, or
access provider/network. A general PASS without explicit GO, a qualified/stale
GO, candidate/evidence drift, unresolved finding, deleted candidate, or NO-GO
forbids live access. NO-GO cleans owned artifacts and ends this ticket without a
live command or rebuild.

Before exact GO, do not read the credential value, construct/load the model,
access provider/network, or start any live command.

## Exact one-command live harness after GO

After exact GO and only while the candidate/evidence/current-state identities
remain unchanged, the owner-private harness MUST:

1. reprove the immutable wheel/runtime/package digest and current cache/model/
   telemetry-filesystem identities without rebuilding or mutating state;
2. remove inherited provider credentials and all telemetry enablement;
3. load the intended credential value only inside the private child environment,
   never in argv, stdout/stderr, retained diagnostics, or records;
4. privately load the exact approved case/dataset above;
5. enter the underscore-prefixed private in-process provider invocation receipt
   scope;
6. run exactly one ordinary **automatic** live command operation through the
   isolated candidate against the current remote catalog and selected current
   content namespaces;
7. preserve the exact original return/exception/exit outcome outside the scope;
   and
8. after terminal scope exit, obtain the same immutable receipt bytes once for
   strict validation.

Command start consumes the sole live authority regardless of outcome. There is
no preview, explicit command, alternate case, alternate candidate, substitution,
second command, receipt-only rerun, provider retry, command retry, or rebuild.
Any command/receipt/process/privacy/side-effect/cleanup failure stops without
retry.

Telemetry MUST remain disabled. Network is limited to provider endpoints reached
by the unchanged ordinary automatic read path. Provider activity is read-only:
only current strong remote-catalog reads and selected content retrieval reads
are allowed. No provider/catalog/card/namespace/content create, update, upsert,
delete, repair, migration, management, or other write path is allowed. No model
download, cache mutation, telemetry export/store access, global install, release,
deployment, publication, push, or ref mutation is allowed.

## Original outcome and receipt acceptance

Preserve the original command outcome truthfully and separately from receipt
acceptance. Receipt validation MUST NOT replace, wrap, suppress, relabel, or
rewrite it. A command error, interruption, nonterminal/uncertain process, or
non-success outcome fails the canary and stops without retry.

PASS requires one known successful original outcome and terminal canonical
receipt bytes that satisfy both active specifications and all of these gates:

- strict canonical compact sorted-key UTF-8 JSON, at most 65,536 bytes, with
  duplicate/unknown/missing keys and noncanonical bytes rejected;
- byte-identical decode, strict validate, and re-encode round trip;
- `receipt_schema_version` exactly integer `1` and `unit` exactly
  `provider_client_invocation`;
- automatic catalog begun, valid source-order grammar, and
  `catalog.invocation_count <= 5`;
- valid content route/attempt grammar and `content.invocation_count <= 18`;
- every represented catalog/content operation and attempt has outcome
  `success`; no `error` or `interrupted` outcome is accepted;
- exact count/sum/order/type/integer-not-boolean/privacy rules; and
- no query, argv, namespace/card/catalog/provider/account identifier, content,
  result, credential, path, payload, URL, billing, raw error/stack, timing,
  process/thread/trace identifier, or ambient context in bytes or diagnostics.

Missing, incomplete, null, observer-failed, malformed, noncanonical,
over-budget, error, interrupted, privacy-unsafe, or otherwise rejected receipt
fails without inference or retry. Source maxima, command result, output,
telemetry, or provider behavior cannot substitute for receipt bytes.

The 5/18 values are post-operation application-boundary receipt acceptance
gates. Do not use them as preemptive transport budgets or infer physical wire
sends, SDK-internal retries, provider billing, cost, or rate-limit effects.

## Post-state, retention, cleanup, review, and closure

After any terminal outcome, rebind and compare exact repository/ref/worktree,
process, model/cache, telemetry-filesystem, credential-source, candidate, and
unrelated-state identities. Prove no model/cache or telemetry mutation, no
surviving owned process, provider reads only, no write/management path, and no
global/release/ref/unrelated operation.

On PASS, retain only:

- one exact canonical validated sanitized receipt;
- bounded content-free source/tree/wheel/runtime/model/cache/telemetry identity;
- generic original command and receipt outcomes;
- exact sanitized family counts/outcomes;
- bounded process/read-only/no-unrelated-effect, privacy, cleanup, and review
  evidence; and
- this governing record graph.

On failure retain no receipt or partial ledger. After bounded evidence is safe,
delete and verify absence of every private source export, wheel, build/install
output, isolated runtime, harness/script, temporary receipt, validator
diagnostic, raw stdout/stderr/error/stack/log, process sample, path-bearing
manifest, query/argv/namespace/card/catalog/content/result value, credential
material, private path, and analysis artifact. Cleanup may touch only owned
temporary artifacts.

Obtain independent final correctness/privacy/side-effect/receipt/cleanup review
of the exact execution evidence commit. Close this ticket only if every
criterion is mapped to evidence and the review passes. Otherwise leave it
blocked or open with the truthful terminal outcome; never close a failed or
missing receipt as PASS.

## Acceptance criteria

- This ticket remains inactive until separately activated against exact clean
  current repository/ref state; consumed predecessors stay blocked/ineligible.
- Exact reviewed source commit/tree and listed source/package hashes reproduce.
- Exactly one offline wheel-only build runs; build failure or identity mismatch
  blocks with no rebuild.
- The wheel has the exact filename/version/730602-byte/78-member/SHA-256
  identity; output contains only it and the accepted optional one-byte uv
  marker.
- Exact digest identity cryptographically reuses the prior reviewed member/path/
  link/package evidence; no archive member-type classifier is authored or run.
- Provider-free validators/install/harness may be corrected and rerun only
  against the same immutable wheel/source, without candidate mutation,
  credential-value/model/provider/network/telemetry/global access, until PASS or
  a real candidate defect.
- Only bounded nonsensitive correction diagnostics exist and are deleted before
  GO/live access.
- Complete exact current repository/ref/process/cache/model/telemetry-filesystem/
  credential-source-presence/case/dataset identities and provider-read-only/
  telemetry-off guards are bound in sanitized preparation evidence.
- Explicit independent GO binds the complete evidence commit/tree and exact
  candidate before credential-value, model, provider, network, or live access.
- After GO, exactly one ordinary automatic live command starts in the private
  scope with the exact approved case/dataset, telemetry off, provider reads only,
  catalog <=5, content <=18, and no preview/explicit/substitution/retry.
- Command start consumes live authority; original outcome remains truthful; any
  command or receipt failure stops without retry.
- PASS has one successful original outcome and one terminal strict canonical
  content-free receipt with every represented operation/attempt successful.
- Cache/telemetry/repository/global state is unchanged; cleanup leaves only the
  canonical sanitized PASS receipt plus bounded evidence, or no receipt on
  failure.
- Independent final review passes before truthful closure, and no wire-send,
  SDK-retry, billing, cost, or rate-limit inference is made.

## Evidence expectations

Record exact activation and current clean HEAD/tree/ref/worktree state; source
export and source hashes; frozen offline lock result; build command-start count
exactly one; exact wheel filename/version/size/digest and inherited 78-member
safety evidence; output marker identity; immutable runtime/install/package
identities; bounded provider-free validator/harness correction ledger and final
verdict; proof no archive classifier ran; current process/cache/model/telemetry-
filesystem/credential-source-presence/case/dataset identities; diagnostic
cleanup; exact independent GO or NO-GO; and changed-path/status/privacy state.

If GO occurs, additionally record the exact GO commit/tree and wheel digest;
exactly one automatic command start and terminal state without argv/PID/time;
generic truthful original outcome; exact canonical receipt bytes and strict
validator verdict; catalog/content counts and success-only outcomes; cache and
telemetry-filesystem pre/post equality; provider-read/no-write and no-unrelated-
effect inventory; raw/private cleanup absence; final repository diff/status;
and independent final review. State explicitly that receipt counts are Buoy
application-boundary attempts and prove no physical sends, SDK retries, billing,
cost, or rate limits.

## Explicit exclusions

Reopening/resuming either predecessor; more than one build; rebuild after any
failure; alternate source/wheel/case/dataset; candidate byte mutation or
substitution; any archive member-type classifier; implementation source/test/
spec/lock/routing change; provider-free credential-value read, model
construction, provider/network access, telemetry DB/store/API/command, or global
state; live access before exact GO; more than one live command; preview, explicit
retrieval, receipt-only rerun, command/provider retry; public/CLI/env receipt
activation; automatic receipt persistence; telemetry-v2/schema/retention change;
provider write/repair/management; model download/cache mutation/repair/forced
device; credential output/persistence/mutation; global install/replacement;
release/deployment/publication/push/ref mutation; transport interception;
wire/SDK-retry/billing/cost/rate-limit claim; unrelated cleanup.

## Dependencies

The fake-only implementation dependency is done and independently passed at
source commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`, with evidence and review linked in
the headers. Both active receipt specifications and the active successor
decision govern execution. No implementation dependency remains unresolved.

## Blockers

- Preparation is terminally blocked after the separately activated one-build
  authority was consumed by a nonzero offline wheel-only build.
- No candidate wheel, retained runtime/harness, preparation PASS, or independent
  GO exists. Credential/model/provider/network/live access remains forbidden.
- This ticket is ineligible to rebuild, re-export, substitute, resume validation,
  seek GO, or execute the live command.

## Progress and notes

- 2026-08-25: Created from exact current owner authorization as the sole new
  executable successor. Status is open and activation is inactive. The two
  consumed predecessors remain blocked/ineligible. Current shaping baseline is
  clean HEAD `49de54138a1607e3b8fef1acfb779ecd541419f2`, tree
  `97a64af52bc9edac104f27818c2bf22cf43f5544`; current package/source bytes are
  identical to the reviewed source authority. This records-only turn did not
  export source, build/install a wheel, run validators/tests/model/credential/
  provider/network/telemetry/global operations, activate this ticket, seek GO,
  or execute a canary.
- 2026-08-25: Explicit owner-directed activation marks only this successor
  active for provider-free preparation. The pre-activation repository was clean
  at exact HEAD `7723bd96f00fa72d4c280f4a227f5f767f4ecf52`, tree
  `57627acf1bacf378cd0227f8aa5f1919d1f2cd8a`, branch ref
  `refs/heads/work/provider-invocation-receipts-execution`, registered worktree
  `/private/tmp/buoy-provider-invocation-receipts-execution`. The complete
  67-worktree porcelain inventory SHA-256 was
  `dec7f4ab5581e82aece682cbe95ce99325a0aa47cb354dd418cee72b6f3bf74b`.
  Exact package-relevant paths were byte-identical to reviewed source commit
  `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
  `9017c4a335938faca80cdded54545df8b79c12f8`. Both consumed predecessors remain
  blocked, consumed, and ineligible. This separate activation commit authorizes
  provider-free preparation only; it did not export source, build/install a
  wheel, run a validator or harness, read credentials, construct a model, open
  telemetry, access provider/network, seek GO, or start a live command.
- 2026-08-25: Provider-free preparation exported exact reviewed source through a
  no-ref archive, passed all seven required source/package hashes, and passed the
  frozen offline lock check. Exactly one wheel-only offline build began once and
  exited nonzero with sanitized category
  `build_environment_version_discovery_failure`; no rebuild, corrected command,
  substitution, wheel acceptance, installation, candidate validator, or live
  operation followed. The build also used the established offline package cache,
  creating a transient build workspace that was absent afterward; this crossed
  the stricter no-global-cache-touch boundary, and complete cache-wide equality
  was not established. The complete owner-private root was deleted and absence
  verified. No credential value, model construction, telemetry store/API,
  provider/network, retrieval, or live command occurred. Failure evidence is at
  `.10x/evidence/2026-08-25-provider-invocation-receipt-successor-preparation-failure.md`.
  This ticket is blocked; activation and build authority are consumed, live
  authority is unconsumed but ineligible, and no rebuild, retry, GO, or live
  access may resume.
