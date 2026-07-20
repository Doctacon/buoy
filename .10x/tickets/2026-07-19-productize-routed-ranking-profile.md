Status: blocked
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/2026-07-19-reproduce-and-generalize-routed-profile-selection.md

# C9: Productize Routed Ranking Profile

## Scope

Shape and implement only the routed-ranking product surface explicitly chosen after C8. This ticket starts blocked. No active product spec is justified before C8 establishes whether evidence supports only oracle/static mapping, an explicit opt-in profile, or a genuinely general held-out selector.

`.10x/specs/repo-ranking-profile-selection.md` intentionally does not exist yet.

## Product checkpoint

Only after C8, ask:

> I recommend a versioned explicit opt-in profile with `repo_code` unchanged; confirm that surface, or explicitly authorize shaping an automatic selector from the held-out C8 result.

Do not offer or ship a static per-repo benchmark map as automatic selection. The checkpoint must also ratify selector/profile inputs, override precedence, deterministic fallback, observability, unknown-profile and failure behavior, multi-namespace compatibility, and whether catalog cards participate.

## Acceptance criteria after ratification

- C8 has terminal evidence and the user explicitly chooses the product surface.
- A focused active `.10x/specs/repo-ranking-profile-selection.md` captures the complete chosen contract before this ticket becomes executable.
- Existing `repo_code` defaults remain unchanged unless separately promoted under the active policy and label-confidence checkpoint.
- Hidden namespace-name lookups and benchmark-repo hard-coding are rejected.
- Tests cover every ratified override, fallback, failure, compatibility, and unchanged-default behavior.
- Live validation, if later approved, uses retrieval-only calls. Any remote catalog-card mutation is separately previewed and approved; it is not bundled with local implementation.

## Stop conditions

- If C8 proves only oracle/static mapping or fails held-out policy, record explicit no action for automatic selection rather than shipping the benchmark lookup table.
- Do not create an active product spec, implement source/tests, name public profiles, or choose CLI/catalog surfaces before the product checkpoint.
- Stop before any live retrieval or catalog mutation without separate exact approval.
- A passing C8 experiment is not promotion authority.

## Evidence expectations

C8 disposition, user ratification, active focused spec, bounded implementation evidence/tests, independent review, retrieval-only approval/evidence if applicable, and separately approved catalog preview/evidence if applicable.

## Blockers

- C8 is incomplete.
- Product surface, selector semantics, fallback, observability, override precedence, and catalog participation are unratified.
- No active product spec exists.

## Explicit exclusions

Static benchmark map as automatic routing; hidden namespace-name routing; unapproved source/tests/spec creation; default promotion; bundled remote catalog mutation; namespace writes/deletes.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/tickets/2026-07-19-reproduce-and-generalize-routed-profile-selection.md`
- `.10x/evidence/2026-07-02-repo-routed-profile-portfolio-validation.md`
- `.10x/decisions/repo-ranking-promotion-policy.md`

## Progress and notes

- 2026-07-19: Opened blocked with no active product spec. No profile name, selector surface, writes, defaults, or promotion was ratified.
