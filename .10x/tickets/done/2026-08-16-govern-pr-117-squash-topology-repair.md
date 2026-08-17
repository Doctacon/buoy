Status: done
Created: 2026-08-16
Updated: 2026-08-16
Decision: .10x/decisions/one-time-pr-117-squash-topology-repair.md
Specification: .10x/specs/one-time-pr-117-squash-topology-repair.md
Evidence: .10x/evidence/2026-08-16-pr-117-squash-topology-repair.md
Review: .10x/reviews/2026-08-16-pr-117-squash-topology-governance-review.md

# Govern PR #117 Squash-Topology Repair

## Outcome

Establish the exact, non-repeatable governance prerequisite for repairing the
accidental squash topology created by PR #117, and align the four already
reviewed newcomer-README paths from current `main` into `develop` before any
ancestry operation. Prepare, but do not execute, the separately owned
content-neutral ancestry bridge.

## Bound identities

- task base / observed `origin/develop` (`D0`):
  `fc867bebb541f06f116502798a08640df375a3dc`
- accidental PR #117 squash / observed `origin/main` (`M`):
  `0db802ec1a895f289c7600b19c80603986839873`
- merge base (`B`): `b9d996250893974c11b4dc69ecd12fd99bf2e016`
- governance branch: `work/govern-pr-117-squash-topology-repair`

Any remote-ref drift before handoff invalidates these observations and requires
a fresh read-only audit. The later bridge ticket binds a new exact develop head
only after this ordinary task is reviewed and squash-integrated.

## Scope

- Copy exactly these four paths byte-for-byte from `M`, and no other main-only
  content:
  - `README.md`
  - `.10x/evidence/2026-08-16-readme-newcomer-rewrite.md`
  - `.10x/reviews/2026-08-16-readme-newcomer-rewrite-review.md`
  - `.10x/tickets/done/2026-08-16-rewrite-readme-for-newcomers.md`
- Record the accepted one-time repair decision and active exact repair
  specification.
- At Phase 1 execution time, truthfully update the active branch/CI
  specification to the observed absence of hosted protection and behavioral
  PR/CI/review/merge-method gates, then allow only the then-future bridge owned by
  `.10x/tickets/done/2026-08-16-bridge-pr-117-squash-topology-once.md` to use
  merge-commit integration into `develop`.
- Apply the same bounded truth correction to root `AGENTS.md` and
  `.10x/specs/pi-worktree-development-flow.md`: absent protection grants no
  authority, settings must not change, and integration/release sessions enforce
  the behavioral PR, exact-head CI, review, and merge-method stop gates.
- Open that executable bridge ticket and provisional evidence record without
  creating a bridge commit, branch, pull request, or integration commit.
- Validate exact README-path identity, links and examples, source-release
  policy, the unchanged source/test surface, lock coherence, and diff hygiene
  with the exact commands pinned below.
- Commit and push this ordinary task branch for independent review. Its future
  `work/* -> develop` pull request remains an ordinary squash integration.

## Intended aligned-content invariant

The governance candidate retains every `D0` path byte-for-byte except the four
listed README paths, the governance records explicitly owned here, and the
bounded current-posture corrections in the active branch spec, worktree-flow
spec, and root instructions. Each of the four README paths equals its exact
`M` blob. No source, test, dependency, workflow, release, routing, provider, or
catalog behavior changes. After an ordinary squash integration, the later
bridge must preserve the resulting develop tree exactly while adding only
ancestry.

## Acceptance

- The four copied paths compare byte-for-byte equal to `M` and are the only
  restored main-only paths.
- The new decision/specification bind `M`, `D0`, `B`, user authority, exact
  ordered-parent/tree requirements, stop-on-drift behavior, and consumed
  non-repeatability.
- At the Phase 1 acceptance checkpoint, active branch-flow policy still
  required squash for every ordinary task and permitted merge-commit
  integration only for the exact then-future bridge. It truthfully recorded
  absent hosted protection and treated exact-head CI/review as behavioral gates
  without authorizing a settings change.
- At that checkpoint, the bridge ticket was executable, active, and content-
  neutral; it established actual independent review and exact-head hosted CI as
  future execution prerequisites without claiming either had occurred.
- At that checkpoint, provisional evidence recorded only verified pre-bridge
  facts and could not be mistaken for bridge completion.
- Required validation and `git diff --check` pass; the commit contains only the
  bounded paths above.

## Validation commands

- Compare `git hash-object` for each imported path to `git rev-parse
  0db802ec1a895f289c7600b19c80603986839873:<path>` and require exact blobs
  `c4408beb`, `180b58b9`, `e90b980a`, and `c15c6932` as expanded in the
  specification.
- Run `wc -l -w README.md` and require `94 456 README.md`.
- Run a local-only Markdown target audit and require all eight README targets
  to resolve, plus a parser-only audit of the four displayed `plan`, apply
  preview, approved apply, and explicit retrieval command shapes.
- Run
  `PYTHONDONTWRITEBYTECODE=1 uv run --locked --python 3.13 python scripts/release_automation.py validate-source`.
- Run `uv lock --check`, `git diff --check`, and a candidate-scope allowlist
  over modified/tracked plus untracked paths. The allowlist includes the exact
  modified preexisting `AGENTS.md`,
  `.10x/specs/protected-github-branches.md`, and
  `.10x/specs/pi-worktree-development-flow.md`.
- Run `git diff --exit-code
  fc867bebb541f06f116502798a08640df375a3dc -- src tests scripts
  pyproject.toml uv.lock .github` to prove source, tests, tooling, dependencies,
  lock, and workflows remain exact develop bytes. A separate full local suite
  is not required for this content/governance-only candidate; exact-head hosted
  PR CI remains mandatory before integration.

## Owned paths

- `README.md`
- `.10x/evidence/2026-08-16-readme-newcomer-rewrite.md`
- `.10x/reviews/2026-08-16-readme-newcomer-rewrite-review.md`
- `.10x/tickets/done/2026-08-16-rewrite-readme-for-newcomers.md`
- `.10x/decisions/one-time-pr-117-squash-topology-repair.md`
- `.10x/specs/one-time-pr-117-squash-topology-repair.md`
- `.10x/specs/protected-github-branches.md` (current hosted posture,
  behavioral gates, and the exact bridge exception only)
- `.10x/specs/pi-worktree-development-flow.md` (the same bounded hosted-posture
  and behavioral-gate truth correction)
- `AGENTS.md` (the corresponding concise session instruction)
- `.10x/tickets/done/2026-08-16-govern-pr-117-squash-topology-repair.md`
- `.10x/tickets/done/2026-08-16-bridge-pr-117-squash-topology-once.md`
- `.10x/evidence/2026-08-16-pr-117-squash-topology-repair.md`
- `.10x/reviews/2026-08-16-pr-117-squash-topology-governance-review.md`
  when the independent governance review is recorded
- `.10x/reviews/2026-08-16-pr-117-squash-topology-repair-review.md` only as the
  then-future bridge review contract; this task did not predeclare its verdict

## Closure mapping

- Ordinary PR #119 used exact reviewed head
  `fcccda7adb35178902a894ae2a7ba2000702e857`. Hosted CI run
  `31992210742` completed successfully: Python 3.11 job `95277638964`, Python
  3.13 job `95277638907`, and Build distributions job `95277896981` all
  passed.
- Squash integration produced exact develop commit
  `034e01c3bb8bfa5726f57bdd5c17c74b7d55dc9f`, with sole parent
  `fc867bebb541f06f116502798a08640df375a3dc` and tree
  `660581caadb070b4ca24f8474f1696bb476c52ec`.
- The four newcomer-README blobs remain exact `M`: `README.md`
  `c4408beb8bc0613401fd0fa66222023e0d496f69`, evidence
  `180b58b9546f1b9c70c69d2d958df576accac6fe`, review
  `e90b980aa0817e5e2a2d786c725f46fc34cc01b3`, and done ticket
  `c15c6932f230e02670bb3fd78882818e04f4b40f`. The seven reader-fix blobs
  remain exact pre-integration develop as enumerated in the shared evidence.
  At Phase 1 integration, the accepted decision, then-active repair
  specification, passing governance review, behavioral branch-flow exception,
  then-active bridge ticket, and provisional evidence were present.
- Phase 1 changed no source, test, dependency, lock, workflow, release,
  routing, provider, catalog, indexed content, credential, or protection
  state. At that checkpoint, Phase 2 remained separately gated and unexecuted.

## External effects

The user's request to preserve the newcomer README and deliver the completed
routing work through `develop` and then `main` authorizes this bounded local
governance/content alignment, validation, commit, and branch push. It does not
authorize an ancestry merge, pull-request merge, direct/force push, branch
protection change, main merge, tag, GitHub Release, package publication,
provider request/write, credential change, or routing-catalog migration.

## Explicit exclusions

Creating or integrating the bridge; opening or merging any pull request;
changing the four copied README paths beyond exact restoration; importing any
other main-only path; source/test/dependency/workflow edits; protection bypass;
release/publication/provider/catalog/content mutations; repeating the consumed
v0.4 exception.

## Progress

- 2026-08-16: Created this executable ticket first on the exact isolated task
  branch at `D0`. No other file edit, ancestry operation, provider call, or
  external mutation had occurred.
- 2026-08-16: The exact twelve-path pre-review candidate allowlist passed. All four imported
  blobs match `M`; README remains 94 lines / 456 words with eight resolving
  local targets and four parser-valid command shapes. Source validation, the
  154-package lock check, ranking contract, C6 forecast, 88-file in-memory
  compilation, five safe CLI help/version checks, unchanged
  source/test/tool/workflow comparison, and diff hygiene passed under isolated
  Python 3.13. At that pre-review checkpoint, hosted CI and independent
  governance review remained future handoff gates and were not claimed.
- 2026-08-16: Independent governance review passed for commit, branch push, and
  ordinary pull-request handoff. The final thirteen-path allowlist adds only the
  review record and its links; at that review checkpoint hosted CI, integration,
  and bridge execution remained unclaimed future gates.
- 2026-08-16: PR #119 passed all three hosted jobs and was squash-integrated as
  exact develop `034e01c3bb8bfa5726f57bdd5c17c74b7d55dc9f`. This recorded and
  closed Phase 1 only; at that checkpoint the ancestry bridge remained active
  and unexecuted.
