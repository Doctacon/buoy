Status: done
Created: 2026-08-19
Updated: 2026-08-19
Decision: .10x/decisions/one-time-integrated-local-telemetry-writer-tool-replacement.md
Evidence: .10x/evidence/2026-08-19-integrated-local-telemetry-writer-tool-replacement.md
Authority-Review: .10x/reviews/2026-08-19-integrated-local-telemetry-writer-install-authority-review.md
Review: .10x/reviews/2026-08-19-integrated-local-telemetry-writer-installation-review.md

# Install the Integrated Local Telemetry Writer Once

## Outcome

Replace only the user-global `buoy-search` uv tool with a reviewed offline
artifact built from exact integrated telemetry result `D0`, verify it without
touching the real application home or executing retrieval, and retain at most
one fail-closed rollback to the reviewed prior package/runtime state with new,
truthful rollback-bundle provenance.

## Fixed implementation identities

- PR #134 base:
  `3787e0eabd2720732fb5c68ca168f926342ae454`;
- PR #134 final head:
  `fe40aadf88e6fbe8ad702225a111d2f787291689`;
- PR #134 head and integration tree:
  `51c756d8bed8f7eee397fa5381feeb3146255180`;
- successful PR exact-head CI run `32305182775`:
  - Python 3.11 job `96236296365`;
  - Python 3.13 job `96236296821`;
  - Build distributions job `96236848069`;
- squash integration:
  `D0 = e9c906ca99caa7b85d6e31e65e10221161013686`;
- `parent(D0) = 3787e0eabd2720732fb5c68ca168f926342ae454`;
- `tree(D0) = 51c756d8bed8f7eee397fa5381feeb3146255180`.

## Phase 1: integrate this authority normally

1. Start the isolated records branch at exact `D0` and change only the
   decision, this active ticket, provisional evidence, and independent
   authority review named above.
2. Validate links, statuses, exact four-path scope, diff hygiene, source
   policy, lock integrity, and zero executable/source/test/spec/dependency/
   workflow change.
3. Open one ordinary same-repository pull request to exact `develop@D0`.
   Require the exact head, successful `CI / Python 3.11`,
   `CI / Python 3.13`, and `CI / Build distributions`, empty blocking
   discussion, mergeability, and independent authority review.
4. A dedicated integration session may squash only. Fetch and bind its actual
   result `A`; require `parent(A) == D0`, `tree(A)` equal to the reviewed
   records-head tree, and `origin/develop == A`. Do not delete the task branch.
5. Installation must not begin until every Phase-1 fact passes fresh readback.

## Phase 2: bind the exact install and rollback bundles

1. Use a clean detached worktree at exact `D0`, not `A`, so authority-record
   history cannot alter the candidate version or artifact bytes.
2. Validate exact source, frozen contracts, lock, compilation, deterministic
   builds, distribution inventory, the sole
   `buoy = buoy_search.entrypoint:main` console mapping, and all governed
   telemetry modules. Clean-install the exact wheel into a temporary
   environment and run only the ticket's isolated provider-free lifecycle.
3. Record the existing global baseline before mutation: executable and link
   target, uv compatibility, tool environment, Python runtime, dynamic version,
   package-manager provenance, distribution set, entry point, installed-source
   identity, and other-tool/executable inventory. Keep the local snapshot
   owner-private outside the repository. Do not inspect any real `~/.buoy`
   path.
4. Prepare one owner-only candidate bundle containing exactly one exact-`D0`
   wheel plus one regular, exact, checksum-validated dependency wheel per pin.
   Validate ZIP integrity, package metadata, pin agreement, absence of
   symlinks and extras, offline installability, and a complete manifest.
5. Prepare and independently validate one owner-only rollback bundle bound to
   the exact observed package/runtime, CLI, entry-point, and dependency state.
   It must be sufficient for one offline package/runtime restoration without
   consulting mutable package indexes. Its rehearsal provenance must truthfully
   identify the reviewed rollback bundle rather than duplicate the original
   installation provenance.
6. Obtain independent `INSTALL-GO` on the exact source/tree, baseline,
   candidate and rollback artifacts, constraints, manifests, isolated smokes,
   executable target, other-tool inventory, owner-private command text, opaque
   LF-terminated command-file digests and digests of the same command-text
   bytes with the sole terminal LF removed, and conditional rollback trigger. Any
   unresolved placeholder or drift is `INSTALL-NO-GO`.

## Phase 3: one forward invocation and bounded verification

1. Re-read every Phase-1 and Phase-2 identity immediately before mutation.
2. Invoke the owner-private reviewed forward command exactly once. Its start
   consumes forward authority. Do not retry it.
3. From an unrelated working directory with a newly created temporary `HOME`,
   verify exact installed wheel/source identities, entry point, package-manager
   provenance,
   runtime, dependency set, version, top-level and module help, telemetry help,
   read-only telemetry status, and empty bounded telemetry flush. Require the
   isolated home to contain only the explicitly reviewed temporary telemetry
   effects, if any. Never access the real application home.
4. Verify the global executable target and all non-Buoy tool/executable
   inventory invariants remain unchanged.
5. On complete acceptance, stop without rollback. Only after a zero-exit
   forward invocation installs the exact candidate and a required immediate
   acceptance check deterministically fails may an independent audit confirm
   the decision's exact rollback predicate, unchanged rollback bundle, and no
   active telemetry writer or replacement process. Only then may the exact
   reviewed rollback command run once. A nonzero, interrupted, uncertain, or
   ambiguous forward outcome, or an intact baseline, means stop without
   rollback.
6. If rollback runs, verify the exact reviewed wheel, version, Python runtime,
   CLI/source bytes, `cli:main` entry point, dependency pins/distribution set,
   absent OpenTelemetry trio, and reviewed new rollback provenance with an
   isolated temporary `HOME`. Do not require the original provenance bytes to
   remain identical. Record the result and stop. Never retry forward or
   rollback.

## Phase 4: durable closure

Create a later records-only task from the then-current `develop` to record the
authority PR result, exact preflight and install facts, invocation count and
exit, post-install or rollback verification, and all zero-effect boundaries.
Mark the decision superseded/consumed, move this ticket to `tickets/done`, set
evidence recorded, time-scope this authority review, and add an independent
final execution review. Integrate that closure only through the ordinary
reviewed task-PR squash flow. Closure grants no retry or recurring procedure.

## Validation and stop gates

- exact four-path allowlist and no tracked modification outside these records;
- correct cross-links, statuses, stale-path scan, and `git diff --check`;
- source validator, offline lock check, and proof the records diff changes no
  executable, package, test, spec, dependency, lock, or workflow surface;
- fresh exact PR, CI, tree, parent, and `develop` identities before install;
- deterministic candidate artifact and complete offline bundle validation;
- independently reviewed pre-install baseline, forward command, rollback
  command, and trigger;
- exactly one forward invocation and zero or one qualifying rollback;
- provider-free isolated-home verification and unchanged other-tool inventory;
- stop on any uncertainty, mismatch, missing artifact, unexpected network
  need during invocation, or real-home access risk.

## External-effects boundary

Only the effects enumerated by the governing decision are permitted. In
particular, this ticket authorizes no `main`, release, publication, provider,
retrieval, plan/apply, model, credential, namespace/catalog/content,
real-application-home, other-tool, protection/ruleset, direct-push,
force-push, or branch-deletion effect.

## Progress

- 2026-08-19: The owner explicitly approved integration and installation.
  PR #134 passed the repaired three-job exact-head CI run and squash-integrated
  as exact `D0`; no installation occurred during implementation or integration.
- 2026-08-19: Created the isolated records-only authority branch at exact
  `D0`. Pre-install bundle preparation and global baseline observation remain
  non-mutating gates; the single forward replacement is not authorized until
  this four-record authority integrates and a separate exact-bundle
  `INSTALL-GO` is issued.
- 2026-08-19: Exact owner-private preflight report SHA-256
  `28600901d7dfbf9cdbd493ec1f8f4559049c12d938a0f2932f86957c2cfc7603`
  records PASS for deterministic exact-`D0` artifacts, candidate and rollback
  wheelhouses, two candidate telemetry lifecycles, rollback rehearsal, fresh
  global baseline, and opaque command bindings. The full report, literal
  commands, local provenance, and inventory snapshots remain owner-private
  outside the repository. Preflight did not mutate the global tool or issue
  the required independent post-commit `INSTALL-GO`.
- 2026-08-19: Same-repository PR #135 at exact head
  `124642b2041f6fdb43d22469798bbe08bf5dca08` passed exact-head CI run
  `32312273623`: Python 3.11 job `96257514149`, Python 3.13 job
  `96257514006`, and Build distributions job `96257962019`. Ordinary squash
  integration produced exact
  `A = 4be90faea973f2ec63a22fe8c61145688e11429e`, whose sole parent is `D0`
  and whose tree is `84514232229a1af491ae424d241e9322c466c6e7`, exactly the reviewed PR-head
  tree.
- 2026-08-19: The independently approved forward replacement was invoked
  exactly once and exited zero. It installed
  `buoy-search 0.5.2.dev36+ge9c906ca9` on Python `3.13` with sole
  `buoy_search.entrypoint:main` entry point and the exact 107 compatible
  distributions. Independent post-install verification passed, the rollback
  predicate was false, and no rollback ran.

## Closure mapping

- Exact authority PR/CI/integration facts, the single invocation and installed
  result, post-install acceptance, and zero-effect boundaries are recorded in
  `.10x/evidence/2026-08-19-integrated-local-telemetry-writer-tool-replacement.md`.
- Independent final execution verification and the final PASS are recorded in
  `.10x/reviews/2026-08-19-integrated-local-telemetry-writer-installation-review.md`.
- Every acceptance criterion passed. The governing decision is superseded,
  forward authority is consumed, and unused rollback authority expired at
  closure. No closed-task record authorizes another installation action.

## Blockers

None.
