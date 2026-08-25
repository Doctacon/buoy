Status: active
Created: 2026-08-25
Updated: 2026-08-25
Parent: .10x/tickets/2026-08-25-provider-invocation-receipt-final-recovery-plan.md
Depends-On: .10x/tickets/done/2026-08-24-validate-provider-invocation-receipt-integration.md
Activation: active
Eligibility: eligible-under-existing-provider-free-activation
Decision: .10x/decisions/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md
Authorization: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-authorization.md
Authority-Correction: .10x/evidence/2026-08-25-provider-invocation-receipt-model-authority-correction.md
Shaping-Review: .10x/reviews/2026-08-25-provider-invocation-receipt-final-recovery-activation-review.md
Accounting: .10x/specs/provider-client-invocation-accounting.md
Lifecycle: .10x/specs/provider-client-invocation-receipt.md
Candidate-Readiness: .10x/knowledge/provider-free-candidate-readiness-before-one-shot-authority.md
Package-Inheritance: .10x/knowledge/exact-reproduced-package-digests-inherit-reviewed-safety.md
Implementation-Evidence: .10x/evidence/2026-08-24-provider-invocation-receipt-integration-closure.md
Implementation-Review: .10x/reviews/2026-08-24-provider-invocation-receipt-integration-review.md
Preparation-Evidence: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-preparation.md
Repair-Evidence: .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-repair.md

# Prepare Provider Invocation Receipt Final Recovery Candidate

## Outcome

In owned isolated provider-free state, iteratively produce and validate the exact
reviewed wheel and complete immutable runtime/harness handoff. Retain that exact
candidate privately until an independent reviewer records PASS/GO against the
complete sanitized evidence. Do not consume or approach live authority.

## Scope and activation gate

This is the sole executable preparation child under the parent plan. It is
active under the existing owner-directed provider-free activation recorded in
its progress history. That activation remains bounded to this provider-free
phase and is never credential/model-construction/provider/network/live GO. The
exact retained candidate/runtime/harness remains the only candidate authority;
this correction authorizes only the unresolved provider-free dual-model cache/
ref/assets inspection and harness-guard correction described below.

All three predecessor attempts remain blocked, consumed, and ineligible. Do not
resume, edit, or infer authority from them. Do not change implementation source,
tests, active specifications, package locks, routing data, datasets, repository
refs, global tools, existing caches, credential sources, model caches,
telemetry state, provider state, or unrelated state.

## Exact VCS-aware source

Create an owner-private local VCS-aware clone or checkout and detach it at exact
reviewed source commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
`9017c4a335938faca80cdded54545df8b79c12f8`. The checkout MUST retain the VCS
metadata Hatch-VCS needs to derive the reviewed version. A metadata-free archive,
version override, synthesized tag, ref creation, ref update, source patch, or
alternate commit/tree is forbidden.

Before each build, prove the checkout remains detached/clean at that exact
commit/tree and that the reviewed package, receipt, retriever, catalog, CLI, and
routing identities match the integration evidence. Local clone/checkout
creation MUST NOT change any source repository ref or registered worktree.

## Owned isolated UV cache and write boundary

Create a distinct owner-private UV cache under the owned temporary root. It MAY
be seeded only by a read-only copy from the existing cache. The existing cache
is a source for that copy only: builds and runtimes MUST neither use it directly
nor write, lock, prune, clean, repair, index, or otherwise mutate it. Bind
existing-cache identity before and after preparation and require equality.

Set build/runtime cache and temporary roots so every UV, build-backend, wheel,
installer, bytecode, log, harness, dependency, and runtime write remains inside
owned temporary state. Use offline/no-download controls. Do not fall back to a
user/global cache, package index, tool install, package install, home directory,
or network.

## Repeatable build and provider-free correction

There is no build-count or rebuild limit. Build/rebuild from only the exact
clean VCS-aware checkout as many times as needed to correct owned cache,
environment, build invocation, isolated installation, validator, or harness
mechanics. Corrections may modify only owned temporary cache/runtime/harness
material. Record a bounded sanitized attempt ledger with generic outcome
categories; never record a private path or raw diagnostic.

Iteration stops only when either:

1. the exact wheel and all required provider-free checks pass; or
2. sanitized reproducible evidence establishes a real defect in the exact
   reviewed product candidate rather than a cache, environment, build, runtime,
   validator, or harness issue.

A real product defect blocks this ticket and grants no source change or live
access. A failed non-product iteration does not consume a one-shot build
entitlement because none exists, but it never widens the prohibited-access or
write boundary.

## Exact accepted candidate

Accept only one regular nonsymlink wheel with:

| Identity | Exact value |
| --- | --- |
| Filename | `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl` |
| Version | `0.5.2.dev87+g0b27c4eaa` |
| Size | `730602` bytes |
| Reviewed members | `78` |
| SHA-256 | `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87` |

Once these identities match, reuse the established member inventory, path/link
safety, metadata, entry point, routing/source equality, and source-to-wheel
evidence from the exact integration evidence. MUST NOT author or run a novel
archive member-type classifier. Output-directory validation remains separate
and may accept only the exact wheel plus the already established optional
regular nonsymlink one-byte uv `.gitignore` marker; no sdist, second wheel,
link, directory, or other entry is accepted.

## Provider-free validation

Install only the exact wheel into an isolated runtime under the owned root,
offline and from the owned cache. Provider-free checks MUST prove:

- exact distribution/module version and sole `buoy = buoy_search.entrypoint:main`
  entry point;
- complete installed package manifest and exact reviewed production/routing
  identities;
- production routing loader/validator acceptance of exact schema-v3 authority;
- executable/module help and private receipt import without retrieval;
- strict receipt encode/decode/validation/canonicalization behavior governed by
  both active specs;
- no ambient editable checkout, `PYTHONPATH`, user/global package, or installed
  global Buoy/tool supplied the result; and
- provider-free filesystem inspection binds exact cache roots, refs, and assets
  for both authorized production models, while harness guards enforce their
  exact identities/runtime settings and reject every other model, download, or
  substitution without constructing either model.

The exact dual-model boundary is:

- `BAAI/bge-small-en-v1.5` at revision
  `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, with unchanged
  production automatic-device behavior; and
- `cross-encoder/ms-marco-MiniLM-L-6-v2` at revision
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU-only, local-files-only,
  safetensors-only, remote code disabled, max-length 512, and batch 8.

Both MUST remain offline/no-download. No other model or substitution is allowed.
Inspection reads model cache files only to establish exact public model assets;
it MUST NOT import a model library, construct, load, or run either model, or
read unrelated credential-bearing cache content.

Validators and harnesses may be corrected and rerun against the same exact
source/candidate. After exact candidate acceptance, corrections MUST NOT mutate
or substitute wheel bytes. Every rerun rebinds the exact candidate digest.

Throughout preparation MUST NOT:

- read, source, copy, print, hash for retention, or expose a credential value;
- import a model library or construct, load, or run either authorized model or
  any other model;
- perform DNS, TLS, provider, catalog, content, or any other network access;
- open or invoke telemetry database, store, API, status, migration, flush,
  writer, queue, receipt, backup, export, or purge behavior;
- run preview, explicit, automatic, or other retrieval;
- install, replace, uninstall, or invoke a user/global Buoy or tool;
- mutate a source or task repository ref/worktree, existing UV cache, model
  cache, credential source, telemetry filesystem, home/global state, or
  unrelated state; or
- change source, tests, specifications, lock files, routing artifacts, datasets,
  or accepted candidate bytes.

## Immutable handoff and independent PASS/GO

After all checks pass, retain the complete accepted VCS-aware source, wheel,
owned cache needed by the runtime, isolated runtime/dependencies, installed
package, and live harness privately and immutably. Delete correction diagnostics
and other unnecessary raw material before review. Sanitized evidence MUST bind
the complete retained candidate/runtime/harness by exact content-free identities
without a private path.

An independent reviewer MUST inspect the exact evidence commit/tree, this
ticket/decision, active specs and knowledge, source/candidate/runtime identities,
all sanitized iterations and final checks, cache isolation/equality, prohibited-
access proof, side-effect inventory, retained handoff, privacy, and current
repository state. The reviewer performs no build, correction, credential/model/
telemetry/provider/network operation.

The reviewer MUST record explicit **PASS/GO** tied to the exact evidence
commit/tree, candidate SHA-256, and retained runtime/harness identity. A general
PASS without GO, qualified/stale review, drift, deletion, unresolved finding,
NO-GO, or a real product defect leaves the live child blocked.

This ticket may close `done` only after that exact independent PASS/GO and while
the complete handoff remains retained and unchanged. A failed/defective
preparation remains open or blocked truthfully and cannot close as success.

## Acceptance criteria

- The recorded separate provider-free activation remains the only activation;
  this ticket is active and no credential/model-construction/provider/network/
  live authority is implied.
- Exact reviewed VCS-aware commit/tree is clean and provides Hatch-VCS version
  authority without ref mutation or override.
- Builds/runtimes use only an owned UV cache seeded by read-only copy; all writes
  stay in owned temporary state and existing cache equality holds.
- Iterative builds/rebuilds and provider-free harness corrections continue until
  exact PASS or a real product defect, with no build-count limit.
- Exact filename/version/730602-byte/78-member/SHA-256 wheel is produced; prior
  reviewed package safety is inherited and no novel archive classifier runs.
- Exact isolated package, routing, installation, help/import, and strict receipt
  checks pass without retrieval or prohibited access.
- Exact filesystem-only cache/ref/assets inspection and harness guards pass for
  both pinned production models without importing or constructing either, and
  reject every other model, download, or substitution.
- No credential value, model construction/load, provider/DNS/TLS/network,
  telemetry DB/store/API/command, global install/tool, ref, source/test/spec, or
  external-state mutation occurs.
- The complete candidate/runtime/harness is retained privately and immutably;
  sanitized evidence contains no private path or prohibited value.
- Independent exact-candidate PASS/GO is recorded before truthful closure or
  live eligibility.

## Evidence expectations

Record activation and clean repository identities; exact VCS-aware source and
reviewed hashes; owned-cache seed source identity/equality and write-boundary
proof; bounded build/correction counts and generic outcomes; exact wheel and
output inventory; inherited package-review reference; installed/runtime/routing/
receipt results; no-prohibited-access and process/side-effect inventory; raw
correction cleanup; retained immutable handoff identities; changed-path/status/
privacy checks; and fresh independent PASS/GO or NO-GO. No evidence contains a
private path, credential, query, namespace, content/result, raw output/error,
model or provider identifier beyond the two ratified public model identities, or
receipt bytes.

## Explicit exclusions

Live command or GO issuance by the executor; predecessor resumption; metadata-
free source; version override; tag/ref mutation; one-build/no-rebuild limit;
novel archive classifier; source/test/spec/lock/routing/data change; credential
value; model import/construction/load/inference; provider/network/retrieval;
telemetry storage/API/commands; global install/tool/cache mutation; model-cache
mutation; any model beyond the two exact production identities; model download
or substitution; release/deployment/publication/push; private path in records;
wire/SDK-retry/
billing/cost/rate-limit claim.

## Dependencies

The fake-only implementation is done and independently passed at exact source
commit/tree above. Its evidence/review and both active specifications govern
this ticket. All known prior preparation failures are resolved by the expressly
ratified VCS-aware source, owned cache, repeatable build, inherited exact-digest
package safety, and split candidate/live gates; they remain historical and do
not become authority.

## Blockers

None. The active authority-correction decision resolves the flawed one-model
governing boundary without changing the exact product candidate or ordinary
automatic behavior. The exact retained source, wheel, runtime, and evidence-gate
repair remain valid. This active child must still complete provider-free exact
cache/ref/assets inspection and harness guards for both authorized models,
without constructing either, then obtain a fresh independent PASS/GO. Until
then the dependent live child remains blocked and inactive.

## Progress and notes

- 2026-08-25: Created open/inactive at clean records-only shaping baseline HEAD
  `da928dd1ef339e16d525ba6c95f2bf42e90ab667`, tree
  `5eaf0f3ec6d7ee3a77cec04f5711782ceb5ad0ad`. No clone, cache access, build,
  install, validator/test, credential, model, telemetry, provider/network,
  retrieval, GO, or live operation occurred.
- 2026-08-25: Explicit owner-directed activation marks only this candidate child
  active for provider-free preparation. The pre-activation repository was clean
  at exact HEAD `68ee19ffcca3bc9178a5c7335f6d8747f925728d`, tree
  `54dcb5e9a1b00f7b38e5635da59acc3c5044c58f`, branch ref
  `refs/heads/work/provider-invocation-receipts-execution`, in its registered
  task worktree. The complete 67-worktree porcelain inventory SHA-256 was
  `a9e7c5049c79917a2092fffa4e50e9e7e8ca2e00d7de8b2938695822017c2ac5`.
  This separate activation authorizes provider-free preparation only. It did not
  clone source, access or seed a cache, build or install a wheel, run a validator
  or harness, read credentials, construct a model, open telemetry, access
  provider/network, issue PASS/GO, or start a live command.
- 2026-08-25: Provider-free preparation passed. A VCS-aware clone remained
  detached/clean at exact source commit
  `0b27c4eaa2449493125f4040af3cd1f7c926b531`, tree
  `9017c4a335938faca80cdded54545df8b79c12f8`. Three offline wheel-build
  attempts corrected only owned cache material and produced exact wheel
  `buoy_search-0.5.2.dev87+g0b27c4eaa-py3-none-any.whl`, 730602 bytes, 78
  inherited reviewed members, SHA-256
  `42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.
  Isolated installation, exact installed/package/routing identities,
  executable/module help, strict receipt validation, and the established 91
  fake-only tests passed. Existing UV cache content/type equality passed without
  claiming atime equality; model and telemetry filesystem equality,
  credential-source presence-only, exact case/dataset, offline float32 automatic-
  device source posture, process guards, raw-diagnostic deletion, and guarded
  one-command harness construction passed without credential/model/provider/
  network/telemetry/retrieval access. The complete owner-private immutable
  handoff remains retained. Sanitized evidence is at
  `.10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-preparation.md`.
  This ticket remained active pending independent exact-candidate PASS/GO. The
  live child remained blocked/inactive and was not moved or edited.
- 2026-08-25: Independent review returned NO-GO. Provider-free repair replaced
  shape-only harness evidence values with exact equality to reviewed preparation
  evidence commit `5e2259d5422a3f3b649c521422a868d770dc7d0d`, tree
  `cc80dc4bf49ed3eec63b8d379b30af0e82f23f4d`; arbitrary lowercase 40-hex
  substitutes were rejected before execution state, and construction-only
  self-check passed. Static inspection of the exact unchanged source then
  confirmed reachable production construction of a distinct second model in
  automatic routing, multi-corpus reranking/fallback, and evidence assessment.
  Because the live child authorizes only `BAAI/bge-small-en-v1.5`, preparation
  cannot guarantee the one-model boundary without changing source, authority,
  or ordinary automatic behavior. This is a real exact-candidate defect, not a
  harness-mechanics issue. Supplemental sanitized evidence is at
  `.10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-repair.md`.
  The ticket is blocked; no PASS/GO issued; no credential, model, telemetry,
  provider/network, retrieval, global package/home, or live operation occurred.
- 2026-08-25: Records-only authority correction established that the NO-GO was
  correct against the then-governing flawed one-model ticket, while superseding
  its product-defect classification. Active specs, decisions, and exact source
  require both pinned production models for unchanged ordinary automatic
  behavior. The ticket returned to `Status: active` under its existing repeatable
  provider-free activation. The exact candidate remains retained; fresh dual-
  model cache/ref/assets and harness-guard evidence plus independent PASS/GO are
  still required. No immutable evidence was edited. No source/spec/test change,
  model/cache access, build, credential read, telemetry, provider/network,
  retrieval, GO, or live command occurred.
