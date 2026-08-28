Status: recorded
Created: 2026-08-27
Updated: 2026-08-27
Target: .10x/tickets/cancelled/2026-08-27-profile-sentence-transformers-import-tree.md
Verdict: concerns

# Sentence Transformers Import Profile Failure Review

## Target

The import-only attribution campaign that stopped after its discarded warm-up child exited nonzero.

Independent review run: `892de357-5e19-403b-bf62-93c0e09c9187`.

## Findings

### Significant — experiment acceptance is unsatisfied

Zero retained observations means the six-process sequence, five valid profiles, exclusive-time accounting, and family attribution criteria are unsatisfied. There is no evidence for choosing a narrow import change over persistent-process lifecycle work. The ticket MUST remain blocked.

### Minor — deleted failure artifacts bound independent review

Privacy/no-partial-result rules deleted the harness, parser output, partial profile, elapsed/RSS data, and raw failure detail. Parser enforcement, sandbox behavior, state equality, and cleanup are therefore bounded attestations rather than independently reproducible artifacts. The records disclose this correctly.

### Minor — target statement differs from production seam

`import sentence_transformers` executes the package initializer but is not contractually identical to production's `from sentence_transformers import SentenceTransformer`, which additionally resolves the exported symbol and may trigger from-list behavior. Any separately authorized successor should execute the exact production statement without instantiation.

## Verdict

Concerns. Pass the truthful fail-closed/no-result disposition; fail experiment acceptance and block closure.

## Residual risk

The exact nonzero cause is unrecoverable by design. It would be unsafe to blame a dependency, sandbox rule, native loader, or environment key. A successor should preserve controls, use the exact production import statement, and retain only an allowlisted content-free failure category if the target child fails again.
