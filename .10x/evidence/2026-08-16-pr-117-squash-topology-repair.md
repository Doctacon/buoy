Status: provisional
Created: 2026-08-16
Updated: 2026-08-16
Ticket: .10x/tickets/2026-08-16-bridge-pr-117-squash-topology-once.md
Specification: .10x/specs/one-time-pr-117-squash-topology-repair.md
Governance-Review: .10x/reviews/2026-08-16-pr-117-squash-topology-governance-review.md

# PR #117 Squash-Topology Repair Evidence

## Provisional pre-bridge observation

This record contains prerequisite observations only. It is not evidence that a
bridge commit, pull request, CI run, independent bridge review, integration, or
main promotion exists or passed.

Read-only local ref inspection observed:

- `origin/main` / accidental one-parent PR #117 squash `M`:
  `0db802ec1a895f289c7600b19c80603986839873`;
- `parent(M)`: `059753a0cff756c531ec1b723747c85d22fc542d`;
- `tree(M)`: `1df8c48adc5d578dc274693e9aea2c8cf786a9f0`;
- `origin/develop` / governance task base `D0`:
  `fc867bebb541f06f116502798a08640df375a3dc`;
- `parent(D0)`: `7e55f73bb6df428bddd24aa9db80039ba0809923`;
- `tree(D0)`: `6c57862183918f83cebd419ce81d73d1b293ef9e`;
- exact merge base `B`:
  `b9d996250893974c11b4dc69ecd12fd99bf2e016`;
- `origin/main...origin/develop` divergence: 15 main-only / 2 develop-only
  commits.

Hosted readback on 2026-08-16 established that both `main` and `develop` have
no branch-protection rules. The owner explicitly instructed that those rules
must not be brought back. Accordingly PR use, exact-head CI, independent review,
and merge method are behavioral session gates; this repair neither claims
mechanical enforcement nor authorizes creating or changing protection.

The tree comparison names eleven differing paths. Four are the reviewed
newcomer README plus its evidence/review/done-ticket present on `M`; seven are
the reviewed empty-prototype reader-fix evidence/review/spec/ticket,
`CHANGELOG.md`, source, and tests present on `D0`. That makes an unreviewed
choice of either raw branch tree unsafe.

## Exact content alignment

The governance candidate restores these exact `M` blobs:

- `README.md`: `c4408beb8bc0613401fd0fa66222023e0d496f69`;
- `.10x/evidence/2026-08-16-readme-newcomer-rewrite.md`:
  `180b58b9546f1b9c70c69d2d958df576accac6fe`;
- `.10x/reviews/2026-08-16-readme-newcomer-rewrite-review.md`:
  `e90b980aa0817e5e2a2d786c725f46fc34cc01b3`;
- `.10x/tickets/done/2026-08-16-rewrite-readme-for-newcomers.md`:
  `c15c6932f230e02670bb3fd78882818e04f4b40f`.

The remaining candidate changes are limited to the executable governance and
bridge records plus the active branch-policy truth update and narrow bridge
exception. The policy records the user-retained absence of hosted protection,
requires behavioral exact-head CI/review/merge-method gates, and authorizes no
settings mutation. Root `AGENTS.md` and the active worktree-flow spec receive
the same bounded truth correction. No source, test, dependency, lock, workflow,
release, routing, provider, catalog, or content behavior is edited by this
prerequisite.

Local candidate validation passed under isolated CPython 3.13.0:

- exact twelve-path pre-review modified/untracked allowlist, including the permitted
  modified `AGENTS.md`, `.10x/specs/protected-github-branches.md`, and
  `.10x/specs/pi-worktree-development-flow.md`;
- four imported blob comparisons to exact `M`;
- README `94` lines / `456` words, eight resolving local targets, and four
  parser-valid displayed command shapes;
- source-release validation with active routing receipts intact;
- `uv lock --check` with 154 resolved packages;
- ranking validation for 13 datasets, 369 judgments, and 90 composite
  identities; C6 forecast digest
  `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`;
- in-memory compilation of all 88 Python files and successful version plus
  top-level/`plan`/`apply`/`retrieve` help checks;
- zero diff from `D0` across `src`, `tests`, `scripts`, `pyproject.toml`,
  `uv.lock`, and `.github`;
- `git diff --check` and empty staged diff.

A separate full local suite is unnecessary because source, tests, tooling,
dependencies, lock, and workflow bytes remain exact `D0`. Exact-head hosted PR
CI remains required and is not yet claimed. Independent governance review
passed for commit/push/ordinary-PR handoff; the final thirteen-path allowlist
adds only that review record and these ticket/evidence links.

## Pending evidence

Before this record can become `recorded` completion evidence, it must add the
integrated prerequisite develop identity, freshly bound `D`, exact bridge and
integration commits/parents/trees, zero-content PR and exact-head hosted CI,
independent review, post-integration ancestry/tree checks, unchanged hosted and
external state, closure mapping, and consumed disposition required by the
specification. Missing pending evidence blocks bridge integration or closure.

## External effects so far

Local inspection and content preparation made no ancestry commit, bridge PR,
long-lived-branch merge, direct/force push, protection change, tag, Release,
package publication, provider request/write, catalog migration, content-index
mutation, model inference, or credential read/change.
