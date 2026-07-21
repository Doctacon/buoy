Status: done
Created: 2026-07-20
Updated: 2026-07-21
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: None

# Shape Prose Token-Budget Compatibility

## Outcome

Resolved the shaping decision for exactly 366 incompatible unchanged prose plan rows in the preserved C6 checkpoint by activating user-ratified Option A no action. Repository prose remains byte-for-byte unchanged across ordinary no-arm, `current-default`, `fixed-80-python-breadcrumbs`, and `python-ast`; all 366 occurrences remain fail-closed and C6 remains blocked. No implementation ticket is needed or authorized.

## Known boundary

The preserved tokenizer checkpoint contains 366 incompatible prose plan rows: 183 unique `(repository,row_id)` identities across 57 paths, duplicated across the two treatment arms because their prose path is unchanged. The rows comprise 9 pytest rows per treatment arm and 174 Ruff rows per treatment arm. They are disjoint from the 20,926 incompatible source plan rows and remain an independent fail-closed C6 stop.

The active source-only specification `.10x/specs/deterministic-treatment-token-budget-subdivision.md` MUST NOT process these rows. Physical-source-line subdivision, inherited treatment breadcrumbs/ownership, and `SourceRange` reconstruction do not define prose behavior.

## Scope after separate shaping authorization

- Inspect the active generic Markdown/prose renderer and exact incompatible prose entries without mutating preserved artifacts.
- Present user-legible options for exact tokenizer-compatible prose behavior, including coverage/citations, overlap or no-overlap, structure preservation, identity/order, individually unsplittable content, and fail-closed handling.
- Map every semantic to active-record-backed, source-observed, user-ratified, or blocked provenance.
- Draft a focused prose specification only after execution-critical behavior is explicitly ratified; do not fold prose rules into the active source contract.
- Preserve C6’s separate complete-regeneration, independent-review, and exact namespace-write approval gates.

## Acceptance criteria

- All 366 preserved prose plan rows and their exact class/repository/path counts remain accounted for without treating duplication across arms as distinct prose semantics.
- A confirm-or-correct checkpoint settles exact rendered-payload accounting, deterministic boundaries, coverage/citations, structure/overlap behavior, identity/order, unsplittable content, failure scope, treatment/control parity, and isolation.
- Options and tradeoffs distinguish preserving current generic prose behavior from any new tokenizer-compatible behavior; no source-range semantics are silently reused.
- Required source/test, full-plan regeneration, artifact identity/count, review, and separate write-approval consequences remain downstream-only.
- C6 remains blocked because selected Option A intentionally retains all 366 exact incompatibilities; no regenerated readiness claim or write checkpoint exists.

## Blockers

None for this completed shaping outcome. Independent review passed PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74`, and the user explicitly ratified exact Option A. Options B, C, and D remain rejected non-authority. This resolution intentionally does not unblock C6 and creates no implementation ticket, source/test change, regeneration, readiness claim, live authority, or write approval.

## Explicit exclusions

Source subdivision implementation; prose source/tests before a separately reviewed active prose spec and executable ticket; mutation/regeneration of the preserved C6 forecast, compact authority, tokenizer report, or validator; model construction/inference/download; credentials/provider access; namespace/catalog/applied-state/default operations; retrieval; deletes; evaluation; promotion; write approval.

## Evidence expectations

Satisfied by exact provenance-classified decomposition, renderer/source citations, options/tradeoffs, the user-legible checkpoint, preserved-artifact attestation, independent PASS, ratification evidence, and explicit no-implementation/no-regeneration/no-live-operation evidence.

## References

- `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md`
- `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md`
- `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md`
- `.10x/specs/deterministic-treatment-token-budget-subdivision.md`
- `.10x/evidence/2026-07-20-deterministic-token-budget-subdivision-shaping.md`
- `.10x/evidence/2026-07-20-prose-token-budget-compatibility-shaping.md`
- `.10x/specs/deterministic-repository-prose-token-budget-compatibility.md`
- `.10x/evidence/.storage/2026-07-20-c6-python-syntax-tokenizer-preflight.json.gz`
- `.10x/tickets/2026-07-20-implement-deterministic-token-budget-source-subdivision.md`

## Progress and notes

- 2026-07-20: Opened blocked when the user ratified only the reviewed source-only subdivision contract. The exact 366 incompatible prose plan rows remain unchanged and fail closed. No prose semantics, specification, implementation/test, artifact regeneration, model/live operation, or write was authorized or performed.
- 2026-07-20: Executed the separately authorized shaping-only inspection. Accounted for all 366 treatment occurrences as 183 unique parents across 57 paths, proved the same parents are identical in current-default, classified approximate-count/overlap/full-payload causes, and recorded no-action plus exact-cap options and locally projected deltas. Added an inactive focused draft with the exact confirm-or-correct checkpoint. No semantics were selected; this ticket remains blocked pending independent review and explicit ratification. No source/test/artifact/validator, model inference/provider operation, C6 status, namespace, or write changed.
- 2026-07-20: Repaired the draft after reviewer feedback without selecting or activating behavior. Added top-level Option A recommendation and separate shared-pipeline C shaping recommendation; expanded exact tokenizer files/class/version/offline and production-render mismatch rules; hardened content/context/metadata/overlap/citation, duplicate-ordinal/ID/index, scalar-terminal, repository/arm failure, authority, and downstream gates; corrected optional-Section wording; and explicitly blocked B2 pending lossless normalized-parent character-offset and separator definitions. Preserved all counts and historical artifacts. Ticket and C6 remained blocked; no implementation, test, regeneration, model/live operation, or write occurred.
- 2026-07-21: Independent review passed PR #78 pre-ratification head `02adbd1cd9fc33dd7f5d52e6c9ef33770f155f74`, and the user ratified exact Option A. Activated only byte-for-byte no-action parity across ordinary/current-default/fixed/AST, retained the exact 366 occurrences / 183 parents / 57 paths as fail-closed incompatibilities, and kept B/C/D as rejected non-authority. Closed shaping with no implementation ticket; no source/test, plan/artifact/count/identity, regeneration, tokenizer/model, live operation, namespace, write approval, or C6 status changed.

## Acceptance mapping

- Exact 366/183/57 accounting: `.10x/evidence/2026-07-20-prose-token-budget-compatibility-shaping.md` and the active specification preserve the exact counts and inventory.
- Ratified behavior: `.10x/evidence/2026-07-21-prose-token-budget-option-a-ratification.md` records exact Option A; `.10x/reviews/2026-07-21-prose-token-budget-compatibility-contract-review.md` records independent PASS.
- Isolation and safety: the branch diff is record-only; preserved C6 artifacts retain their recorded hashes, and no implementation ticket was opened.
- C6 disposition: `.10x/tickets/2026-07-19-evaluate-python-syntax-chunking.md` remains blocked on the unchanged fail-closed prose incompatibilities and other existing gates.

## Retrospective

The smallest complete resolution was a durable no-action contract, not an implementation slice. Making rejected alternatives visibly non-authoritative prevents detailed exploratory mechanics from being mistaken for executable semantics. No additional reusable procedure or follow-up owner is needed unless a future user explicitly supersedes Option A.
