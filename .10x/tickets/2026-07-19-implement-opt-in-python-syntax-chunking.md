Status: blocked
Created: 2026-07-19
Updated: 2026-07-19
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/2026-07-19-freeze-repo-ranking-experiment-contract.md

# C5: Implement Opt-In Python Syntax Chunking

## Scope

Own a local-only, experiment-only Python syntax chunking implementation after an active focused specification defines exact behavior. Preserve fixed 80-line chunking as the default and preserve existing `--repo-search-metadata` output/behavior.

Existing records support evaluating syntax-aware chunks and lightweight Python breadcrumbs without Tree-sitter. They do not fully settle the exact AST boundary ownership, ancestor breadcrumbs, long-symbol subdivision, line coverage/citation rules, fallback behavior, or experiment arm names. This ticket is therefore not executable yet, and no active syntax experiment spec is created by the decomposition.

## Required syntax-contract checkpoint

Before implementation, recommend the smallest standard-library Python experiment and ask the user to confirm or correct:

- exact comparison arms, including whether fixed/no-breadcrumb, fixed/breadcrumb-only, and Python-AST/ancestor-breadcrumb arms are required;
- which AST nodes own decorators, module statements, nested definitions, and interstitial comments/blank lines;
- maximum long-symbol window and overlap behavior;
- complete, ordered, nonduplicated source-line coverage and citation-line semantics;
- deterministic syntax-error and non-Python fallback;
- whether path-token/global symbol preambles are excluded to isolate breadcrumbs from the completed metadata experiment.

Only the ratified answers may be captured in `.10x/specs/repo-python-syntax-chunking-experiment.md` and used to activate this ticket.

## Acceptance criteria after ratification

- An active focused syntax experiment spec exists and this ticket contains no unresolved behavior.
- Implementation is explicit opt-in, local-plan-capable, standard-library-only unless a later decision says otherwise, and unchanged by default.
- Existing metadata mode remains compatible and is not silently combined with isolated breadcrumb arms.
- Tests cover every ratified boundary/fallback/coverage scenario and prove complete source-order coverage with no unintended omission or duplication.
- Local paired plans record commit, selected files, chunks/rows, multipliers, and zero remote calls/writes.
- No namespace, catalog, applied state, dataset, label, or default changes occur.

## Stop conditions

- Do not implement or create an active spec while the exact syntax behavior remains unratified.
- Stop if deterministic complete source coverage and citation-line preservation cannot be specified and tested.
- Do not add Tree-sitter or multilingual parser dependencies without a later explicit need and decision.
- Do not live-apply from this child.

## Evidence expectations

Ratification provenance, active focused spec, focused/full local tests, paired local plan/preflight summaries, diff review, and no-live-call proof.

## Blockers

- C1 is incomplete.
- Exact syntax experiment behavior is not fully record-backed or user-ratified.
- `.10x/specs/repo-python-syntax-chunking-experiment.md` intentionally does not exist yet.

## Explicit exclusions

Live retrieval or writes; namespace/catalog/default mutation; Tree-sitter; multilingual product support; repeating the completed global metadata experiment; public product promotion.

## References

- `.10x/research/2026-07-19-repo-search-heavy-ranking-experiment-decomposition.md`
- `.10x/research/2026-06-28-repo-search-precision-state-of-art.md`
- `.10x/research/2026-06-28-expanded-validation-ranking-hypotheses.md`
- `.10x/tickets/done/2026-06-28-repo-searchable-path-symbol-metadata.md`

## Progress and notes

- 2026-07-19: Opened blocked. Inspection found the hypothesis record-backed but the exact behavior insufficient for an active spec; no spec, source, tests, plans, or live operations were created.
