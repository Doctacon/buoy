Status: active
Created: 2026-08-16
Updated: 2026-08-16
Decision: .10x/decisions/one-time-pr-117-squash-topology-repair.md

# One-Time PR #117 Squash-Topology Repair

## Purpose and scope

Define the only permitted repair for the accidental one-parent PR #117 squash
while preserving both the reviewed newcomer README and the reviewed routing
reader fix. This specification authorizes no recurring branch synchronization.

## Exact observed identities

- `M = 0db802ec1a895f289c7600b19c80603986839873`, exact observed `origin/main`
  and one-parent PR #117 squash;
- `D0 = fc867bebb541f06f116502798a08640df375a3dc`, exact task base and observed
  `origin/develop`;
- `B = b9d996250893974c11b4dc69ecd12fd99bf2e016`, exact `merge-base(M,D0)`.

`D` means the future exact `origin/develop` only after the ordinary governance
and content-alignment task is squash-integrated. The bridge executor must fetch
and record `D`; it must not infer or predeclare that commit.

## Phase 1: governance and content alignment

The ordinary branch `work/govern-pr-117-squash-topology-repair` begins at exact
`D0` and may restore only these exact `M` blobs:

- `README.md` (`c4408beb8bc0613401fd0fa66222023e0d496f69`);
- README evidence (`180b58b9546f1b9c70c69d2d958df576accac6fe`);
- README review (`e90b980aa0817e5e2a2d786c725f46fc34cc01b3`);
- README done ticket (`c15c6932f230e02670bb3fd78882818e04f4b40f`).

It may also add the exact decision, this specification, the two executable
tickets, provisional evidence, eventual governance review, and only the bounded
current-posture corrections in `.10x/specs/protected-github-branches.md`,
`.10x/specs/pi-worktree-development-flow.md`, and root `AGENTS.md`, including
the exact PR #117 exception. Every other preexisting path must remain
byte-identical to `D0`. This phase uses the normal behavioral task flow and
squash integration into `develop`. Hosted branch protection is intentionally
absent under the user's retained choice; this specification does not claim
mechanical enforcement or authorize changing that state.

### Exact content resolution

For the current main/develop tree difference, `M` is authoritative only for the
four pinned README blobs. `D0` is authoritative for every other preexisting
path, including all seven reader-fix paths. New paths are limited to the owned
governance records. No merge driver, three-way textual resolution, opportunistic
main import, or deletion is permitted. In Phase 2, freshly bound `D` is
authoritative for the entire tree; the bridge contributes ancestry and no
content. These rules are the complete conflict resolution.

## Phase 2: content-neutral ancestry bridge

Only `.10x/tickets/2026-08-16-bridge-pr-117-squash-topology-once.md` may execute
this phase, after Phase 1 is integrated.

1. Fetch without mutating long-lived branches. Require `origin/main == M`; bind
   exact current `origin/develop` as `D`; record both commits and trees.
2. Prove `D` contains the four exact blobs above, the integrated governance
   exception, and the reviewed reader fix. Prove neither branch already
   contains the other in the intended repaired direction.
3. From exact `D` in an isolated `work/bridge-pr-117-squash-topology-once`
   worktree, create one true merge commit `C` with ordered parents `[D, M]` and
   `tree(C) == tree(D)`. No file may be edited or staged.
4. Push only that work branch and open one pull request targeting `develop`.
   The PR must report zero changed files, additions, and deletions.
5. Require the exact-head hosted `Python 3.11`, `Python 3.13`, and
   `Build distributions` checks to pass. Obtain independent read-only review
   of refs, ordered parents, tree identity, zero diff, check identities, the
   intentionally absent protection state, and non-mutation boundaries. These
   are future behavioral execution prerequisites, not facts established by
   Phase 1 or mechanically enforced hosted gates.
6. A dedicated integration session must merge the bridge PR using a merge
   commit, never squash/rebase. Bind resulting `I`; require ordered parents
   `[D, C]`, `tree(I) == tree(D)`, and both `M` and `C` ancestors of `I`.
7. Verify `main` remains `M`, final `develop` has the intended tree, the
   intentionally absent protection state is unchanged, and no release/provider
   state changed. Record exact evidence and independent review, close the bridge
   ticket, and mark this exception consumed through an ordinary closure task.

## Review and evidence contract

The governance candidate requires an independent governance review at
`.10x/reviews/2026-08-16-pr-117-squash-topology-governance-review.md` before
Phase 1 integration. The exact future bridge head and integration require a
separate independent review at
`.10x/reviews/2026-08-16-pr-117-squash-topology-repair-review.md`. Provisional
evidence must not claim either review or bridge completion before it occurs.

Final evidence must include exact refs, ordered parents, tree IDs, merge base,
divergence, imported blob IDs, zero-diff assertions, PR/check/run identities,
integration method and SHA, unchanged absent-protection/main/release/provider
state, and the command-level ancestry/tree proofs. Any mismatch stops
execution.

## Acceptance criteria

- Phase 1 is an ordinary, passing, independently reviewed squash integration.
- Phase 2 starts only from freshly bound exact long-lived refs after Phase 1.
- `C` and `I` have the exact ordered parents and develop-identical trees above.
- The bridge PR has no content delta and all exact-head behavioral CI checks
  pass.
- Independent review passes before bridge integration.
- Final `develop` contains exact `M` ancestry without changing its pre-bridge
  tree; no other task receives merge-commit authority.
- No direct/force push, rebase, squash of the bridge, protection change, main
  merge, publication, provider operation, or content mutation occurs.
- Closure marks the exception consumed and non-repeatable.

## External effects and exclusions

Phase 1 permits only its bounded branch push. Phase 2, when all prerequisites
hold, permits only one bridge-branch push, one bridge PR, and its
merge-commit integration to `develop`. Neither phase authorizes changing
branch protection, merging `main`, tagging or publishing, running a provider
operation, migrating the catalog, mutating indexed content, reading secrets,
or retrying after a bound identity/tree mismatch.
