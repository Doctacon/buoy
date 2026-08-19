Status: superseded
Created: 2026-08-19
Updated: 2026-08-19

# One-Time Integrated Local-Telemetry-Writer Tool Replacement

## 2026-08-19 disposition

The records-only authority integrated through PR #135 as exact
`A = 4be90faea973f2ec63a22fe8c61145688e11429e`, with sole parent
`D0 = e9c906ca99caa7b85d6e31e65e10221161013686` and reviewed tree
`84514232229a1af491ae424d241e9322c466c6e7`. The sole reviewed forward
replacement invocation then began, consuming forward authority, and exited
zero. Independent post-install verification passed the exact candidate
package, runtime, entry point, dependency, package-content, and isolated-home
acceptance gates.

The rollback predicate was false, so rollback was neither authorized nor
invoked. Unused rollback authority expired at task closure. This decision is
retained as historical context only and grants no retry, rollback, uninstall,
second replacement, recurring procedure, publication, provider operation, or
other excluded action.

## Context

The repository owner explicitly directed the agent to integrate the approved
private local telemetry writer and install it. The implementation passed its
repaired exact-head checks and ordinary squash integration through PR #134 as:

- integration result
  `D0 = e9c906ca99caa7b85d6e31e65e10221161013686`;
- `parent(D0) = 3787e0eabd2720732fb5c68ca168f926342ae454`;
- `tree(D0) = 51c756d8bed8f7eee397fa5381feeb3146255180`;
- reviewed PR head
  `fe40aadf88e6fbe8ad702225a111d2f787291689`, with the same exact tree;
- successful exact-head CI run `32305182775`, with Python 3.11 job
  `96236296365`, Python 3.13 job `96236296821`, and Build distributions job
  `96236848069`.

The former one-time user-global-home main-promotion and tool-replacement
decision is superseded and consumed. It is historical evidence only and
cannot authorize this replacement, a rollback, or any other action. This new
decision records the owner's later instruction without reopening `main`,
release, publication, provider, retrieval, or real-home authority.

## Decision

Authorize one records-only authority branch and ordinary squash pull request
into exact `develop@D0`. Only after that authority pull request passes all
three exact-head CI jobs, independent review, empty blocking discussion,
mergeability, and exact-tree readback may a dedicated installation session
replace the user-global `buoy-search` uv tool with a build cryptographically
bound to exact `D0`.

Before replacement, a clean detached exact-`D0` worktree must pass source,
lock, compilation, build, distribution-content, installed-entry-point, and
isolated-home lifecycle validation. A pre-install review must bind all of the
following without unresolved placeholders or drift:

- current executable, uv-tool environment, Python runtime, version,
  distribution set, installed-source identity, and owner-private provenance
  snapshot;
- exact `D0`, its tree, build inputs, dynamic version, deterministic candidate
  wheel, source distribution, dependency constraints, and every artifact
  digest used by the command;
- one owner-only prevalidated offline candidate wheelhouse and one exact
  prevalidated rollback bundle for the existing package/runtime state;
- the owner-private other-tool and executable inventories needed to prove
  replacement scope;
- isolated-home clean-install and lifecycle results; and
- the opaque LF-terminated command-file digests and digests of the same
  command-text bytes with the sole terminal LF removed for the owner-private
  forward and conditional rollback commands.

Authorize exactly one reviewed forward replacement invocation for
`buoy-search`, using only the reviewed exact-`D0` wheel and dependency bundle
bound by those opaque command digests. Beginning that invocation consumes
forward authority. A nonzero or uncertain result grants no forward retry,
uninstall, fallback, dependency substitution, or second candidate invocation.

Authorize at most one conditional rollback invocation to the reviewed
package/runtime rollback target, and only after the forward invocation exits
zero, fresh readback proves the global tool is the exact reviewed candidate,
and a required immediate identity, dependency, entry-point, version/help, or
isolated-home lifecycle check deterministically fails. An independent rollback
audit must also prove the exact rollback bundle is unchanged and no telemetry
writer or uv replacement process is active. A nonzero, interrupted, uncertain,
or ambiguous forward result stops without rollback. Rollback is not authorized
for a warning, preference change, unrelated failure, or intact pre-install
package/runtime state. It may use only the independently validated rollback
wheel and dependency bundle named by the pre-install review. Beginning
rollback consumes rollback authority; there is no retry, second rollback, or
renewed forward authority regardless of result.

Rollback means exact restoration of the reviewed wheel bytes, Buoy version,
Python runtime, CLI/source bytes, `cli:main` entry point, 103 dependency pins,
104-distribution normalized set, and absence of the OpenTelemetry trio. It
does not mean byte-identical restoration of the entire pre-install environment.
The owner-private pre-install provenance snapshot remains evidence of the
original installation. A rollback installed from the reviewed bundle must
instead record truthful new bundle provenance and match the separately
reviewed rollback semantics.

Post-install or post-rollback verification must use an unrelated working
directory and a newly created isolated temporary `HOME`. Rollback verification
must require the package/runtime target and reviewed new provenance above, not
the original provenance bytes. Verification must not inspect,
create, traverse, stat, resolve, migrate, copy, or mutate the real
`~/.buoy` path. It may run only provider-free identity,
dependency, `--version`, help, module-help, telemetry-help, read-only telemetry
status, and empty bounded telemetry-flush checks against the isolated home.

## Fail-closed and consumption boundary

Any branch, commit, tree, path scope, CI, discussion, review, baseline,
artifact, digest, dependency, executable target, command, isolated-home,
installed identity, or other-tool drift stops execution. No exact identity may
be silently rebound and no install method may be substituted. The authority
pull request does not itself consume installation authority. Forward authority
is consumed when its sole invocation begins; conditional rollback authority is
consumed only if its sole invocation begins. Both expire at task closure and
are never reusable.

## External effects and exclusions

Permitted effects are limited to this records-only task branch and ordinary
pull request, one squash integration into `develop`, read-only repository and
global-tool inspection outside the real application home, bounded owner-only
temporary build/cache/wheelhouse/isolated-home files, bounded public package
index and package-file reads needed to prepare the reviewed offline bundles,
exactly one forward `buoy-search` uv-tool replacement, at most one qualifying
rollback, verification, and one later records-only closure task and ordinary
pull request.

No `main` change, release-readiness action, tag, GitHub Release, package
publication, deployment, provider request/write, retrieval, plan, apply,
namespace/catalog/indexed-content mutation, model inference, credential
access/change, telemetry export, listener, remote backend, real `~/.buoy`
access, migration, other-tool mutation, direct or force push to a long-lived
branch, branch deletion, or protection/ruleset change is authorized.
Publication remains paused.

The complete preflight report, literal command text, local provenance, and
machine inventory snapshots remain owner-private outside the repository. A
post-integration `INSTALL-GO` must freshly verify them against the opaque
repository bindings before any invocation.
