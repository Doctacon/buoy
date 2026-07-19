Status: done
Created: 2026-07-18
Updated: 2026-07-18
Parent: .10x/tickets/2026-07-18-direct-command-defaults-plan.md
Depends-On: None

# Make Retrieval Live by Default

## Scope

Implement `.10x/specs/default-remote-namespace-routing.md` and the retrieval portion of `.10x/decisions/direct-commands-execute-by-default.md`:

- plain automatic and explicit retrieval execute live;
- `--dry-run` and `--plan` request preview;
- `--live` remains accepted as a compatibility no-op and conflicts with preview flags;
- preserve automatic routing, explicit namespace bypass, credential boundaries, all-or-nothing results, and output truthfulness;
- reverse generated apply handoff commands so live is plain and preview appends `--dry-run`;
- update retrieval/help/README/changelog/migration documentation affected by the default.

## Acceptance criteria

- Parser and validation matrices cover plain/`--live`/`--dry-run`/`--plan`, automatic/explicit namespaces, contradictory flags, whitespace, missing credentials, and existing `--auto-route` compatibility.
- Plain automatic route performs the established catalog read/route/content query; plain explicit route skips catalog/router and queries content.
- Preview behavior remains exact: automatic preview uses read-only list/catalog calls; explicit preview is credential/API/model-free.
- Plain and compatibility `--live` outputs are byte-equivalent after normalizing invocation-only fields; preview remains truthful.
- Any selected namespace failure emits no partial content result; no fallback or changed route ranking occurs.
- Generated `retrieval_commands.live` omits `--live`; `.preview` appends `--dry-run`, with shell quoting preserved.
- No catalog/apply write behavior changes.
- Focused/full Python 3.11/3.13 tests, distributions, evidence, independent review, and hosted checks pass.

## Evidence expectations

Exact fake call traces for automatic/explicit live and preview modes; parser/help snapshots; generated command tokenization; all-or-nothing failures; full/hosted check identities; no-write attestation.

## Blockers

None.

## Explicit exclusions

Apply prompt/mode implementation; catalog command defaults; routing algorithm/card changes; concurrent namespace queries; confidence thresholds; telemetry; release.

## References

- `.10x/tickets/2026-07-18-direct-command-defaults-plan.md`
- `.10x/decisions/direct-commands-execute-by-default.md`
- `.10x/specs/default-remote-namespace-routing.md`
- `.10x/specs/apply-to-retrieval-handoff.md`

## Progress and notes

- 2026-07-18: Implemented plain live automatic and explicit retrieval, retained `--live` as a conflicting-with-preview compatibility no-op, and preserved `--dry-run`/`--plan` preview boundaries and validation precedence.
- 2026-07-18: Reversed generated apply handoff commands so `live` is plain and `preview` appends `--dry-run`; updated retrieval help, README, changelog, retrieval guide, and migration guidance without changing apply confirmation or applied-state behavior.
- 2026-07-18: Focused fake-backed suites passed on Python 3.11 and 3.13 (107 tests each); full suites passed on both (405 tests each); wheel/sdist build and asset verification passed. Evidence: `.10x/evidence/2026-07-18-retrieval-live-by-default.md`.
- 2026-07-18: Initial hosted pull-request checks passed on Python 3.11, Python 3.13, and distribution build (PR #34, Actions run `29673894066`); identities are recorded in `.10x/evidence/2026-07-18-retrieval-live-by-default.md`.
- 2026-07-18: Implementation session left the ticket active pending independent review.
- 2026-07-18: Corrected the PR #34 review blocker: routed automatic preview now reports command-level credentials and read-only Turbopuffer API calls truthfully at the top level while explicit preview remains credential/API-free and live behavior is unchanged. Focused suites passed on Python 3.11 and 3.13 (26 tests each); full suites passed on both (405 tests each). Evidence: `.10x/evidence/2026-07-18-retrieval-live-by-default.md`.
- 2026-07-18: Final independent re-review passed at commit `31aeeee27758e4aed9d16d73e7886b62235840b3`; hosted Python 3.11/3.13 and distribution checks passed. Review: `.10x/reviews/2026-07-18-retrieval-live-by-default-review.md`.

## Closure mapping

- Parser/mode/compatibility matrix: focused tests and evidence call traces in `.10x/evidence/2026-07-18-retrieval-live-by-default.md`.
- Automatic and explicit live/preview boundaries: focused automatic and multi-namespace suites on Python 3.11/3.13 plus independent review.
- Output equivalence, truthfulness, and all-or-nothing behavior: regression assertions reviewed at final commit, including the corrected command-level automatic-preview fields.
- Generated handoff command shape/quoting: apply CLI tokenization tests and reviewed `shlex.join` implementation.
- No apply/catalog write behavior change: bounded diff inspection and independent review.
- Full validation: 405 tests on Python 3.11 and 3.13, wheel/sdist build, release asset checks, and hosted PR checks.

## Retrospective

The useful durable lesson is that nested output truth does not guarantee command-level truth when serializers compose objects. Existing tests asserted only nested routing facts, allowing contradictory top-level safety fields to pass. The final regression now checks both levels; this lesson is specific to the corrected implementation and does not require a separate reusable procedure.
