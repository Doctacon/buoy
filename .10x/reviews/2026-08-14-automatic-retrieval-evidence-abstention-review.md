Status: pass
Created: 2026-08-14
Updated: 2026-08-14
Ticket: .10x/tickets/2026-08-14-implement-automatic-retrieval-evidence-abstention.md
Evidence: .10x/evidence/2026-08-14-automatic-retrieval-evidence-abstention.md

# Automatic Retrieval Evidence Abstention Review

## Scope

Independent adversarial review covered the automatic-only evidence observation
and dormant decision seam, packaged calibration authority, pinned cross-encoder
identity, exact-final-hit scoring and score reuse, weak-singleton widening,
failure and no-answer semantics, public JSON/text redaction, offline threshold
selection and certification metrics, collector normalization and label joining,
explicit-retrieval compatibility, packaging, documentation, and governing
records.

## Findings closed during review

- The first implementation allowed shadow and active artifacts without proving
  their recorded retrieval, dataset, evaluator, source-mix, and certification
  bindings against runtime state. The bounded release now pauses both modes:
  the packaged loader and calibrated runtime assessor reject every non-collect
  artifact pending a separately reviewed binding implementation.
- Free-form injected assessors could place content-bearing values in public
  diagnostics. Their decisions may still exercise the internal orchestration
  seam in tests, but their free-form diagnostics are replaced with a fixed,
  content-free marker; calibrated diagnostics contain only governed identifiers,
  enums, booleans, and finite numeric observations.
- Collected scores were initially disconnected from separately reviewed
  question-level judgments, and the first join accepted incomplete or
  substitute evidence contracts. The final join requires exact question IDs,
  the packaged collect calibration/model/revision/feature contract, strict
  normalized observations, attributed route failures, and returned-hit
  identities before producing calibration inputs.
- The collector/evaluation boundary now rejects contradictory score/count/gap
  fields, unknown or content-bearing evidence fields, failures outside the
  attempted route, all-failed cases represented as successful observations,
  hits from failed or unattempted namespaces, and candidate counts inconsistent
  with the redacted returned-hit projection.
- Offline threshold selection is deterministic and question-level: it requires
  nonempty useful and non-useful denominators, maximizes retained useful-evidence
  coverage subject to the exact false-evidence-risk bound, uses the documented
  conservative tie-break, and evaluates a disjoint certification split without
  retuning it. Undefined rates remain null rather than being presented as
  passing.
- Documentation and governance now state the actual boundary consistently:
  scoring in this change gathers calibration evidence; preventing irrelevant
  presentation is a later active-mode benefit.

## Collect-only boundary and compatibility

This PASS is for collect-only instrumentation, not evidence suppression. The
packaged artifact has `mode=collect`, `threshold=null`, and
`owner_approved=false`. Automatic live JSON and the governed evaluator may
score up to five exact final hits and report `unassessed`; they preserve the
existing hit list and ranking. Ordinary automatic text output skips the
otherwise-discarded collect-only inference. Automatic preview performs no
content retrieval and cannot claim an evidence decision.

Explicit single- and multi-namespace retrieval remains outside the evidence
assessor. It does not load the evidence calibration or scorer, does not add an
`evidence` field, and retains its established ranking, result, failure, and JSON
contracts. The three-namespace maximum and provider read-only evaluation
boundary are unchanged.

## Remaining activation blockers

No threshold, shadow rollout, or active suppression is approved by this review.
Activation still requires a materially larger owner-reviewed answerable and
no-answer basket covering every active source kind; frozen question-level
calibration and certification splits; a finite selected threshold; a locked
certification report with sufficient denominators and passing false-evidence,
retained-recall, no-answer, source-kind, fanout, and existing multi-corpus
gates; and exact runtime verification of the retrieval, dataset, evaluator,
source-mix, model, feature, and certification-report bindings.

A later independently reviewed code change must explicitly enable shadow.
Active then additionally requires owner approval of the exact passing artifact
and must wire the governed decision into ordinary automatic text retrieval as
well as JSON. Until those conditions are met, non-collect artifacts must remain
rejected and no weak-evidence widening or hit suppression may occur.

## Validation and evidence limits

- Focused suites passed `186/186` on Python 3.11 and `186/186` on Python 3.13.
- Full suites passed `671/671` on Python 3.11 and `671/671` on Python 3.13.
- Dependency-lock, source, ranking, C6, diff-hygiene, distribution, and
  clean-wheel smoke validation passed.
- The read-only 50-case run is diagnostic only. It made no provider mutation
  and supplies no release, threshold, calibration, certification, shadow, or
  active authority.

## Verdict

The collect-only implementation is a code, security/redaction, compatibility,
calibration-machinery, evaluation, packaging, documentation, and governance
PASS. The reviewed change safely records bounded evidence scores without
changing what users receive. This review authorizes no threshold, suppression,
provider write, label self-approval, release, merge, or other external action.
