Status: pass
Created: 2026-08-14
Updated: 2026-08-14
Ticket: .10x/tickets/2026-08-14-implement-automatic-retrieval-evidence-abstention.md
Evidence: .10x/evidence/2026-08-14-automatic-retrieval-evidence-abstention.md

# Automatic Retrieval Evidence Abstention Review

## Scope

The completed independent adversarial review covered the historical
collect-only evidence observation and dormant decision seam, packaged
calibration authority, pinned cross-encoder
identity, exact-final-hit scoring and score reuse, weak-singleton widening,
failure and no-answer semantics, public JSON/text redaction, offline threshold
selection and certification metrics, collector normalization and label joining,
explicit-retrieval compatibility, packaging, documentation, and governing
records.

On 2026-08-14, the owner subsequently authorized a provisional active `-8.0`
cutoff in revision `owner-approved-provisional-minus-8-v1` despite the disclosed
five-no-answer sample limitation. That activation changes user-visible behavior
and was outside the original PASS. The final independent review covered the
active text/JSON path, strict artifact, failure semantics, explicit bypass,
tests, packaging, and documentation.

## Findings closed during review

- The first implementation allowed shadow and active artifacts without proving
  their recorded retrieval, dataset, evaluator, source-mix, and certification
  bindings against runtime state. The historical collect-only phase rejected
  non-collect artifacts. The owner-authorized delta now admits only the exact
  packaged active revision and does not claim locked statistical certification.
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
- Documentation and governance now state the actual active boundary, known
  false-support risk, no-override rule, and provisional evidence limits
  consistently.

## Historical collect-only boundary and compatibility

The prior PASS was for collect-only instrumentation, not evidence suppression.
The packaged artifact had `mode=collect`, `threshold=null`, and
`owner_approved=false`. Automatic live JSON and the governed evaluator could
score up to five exact final hits and report `unassessed`; they preserved the
existing hit list and ranking. Ordinary automatic text output skipped the
otherwise-discarded collect-only inference. Automatic preview performed no
content retrieval and could not claim an evidence decision.

Explicit single- and multi-namespace retrieval remains outside the evidence
assessor. It does not load the evidence calibration or scorer, does not add an
`evidence` field, and retains its established ranking, result, failure, and JSON
contracts. The three-namespace maximum and provider read-only evaluation
boundary are unchanged.

## Historical activation blockers and owner exception

The original review approved no threshold or active suppression and required a
larger reviewed basket and locked certification. Those facts remain historical
and the stringent gates have not been shown to pass. The owner later made a
narrow, informed exception: activate packaged revision
`owner-approved-provisional-minus-8-v1` at `-8.0`, with no CLI, environment, or
runtime threshold override. Changing the cutoff requires a new reviewed
packaged revision. The starting point uses the observed category gap between
five `no_answer` top scores (`-11.2867` through `-9.6270`) and 45
`answer_expected` scores beginning at `-5.8328`. This gap does not show that
the accepted passages are relevant.

The evidence audit found a known false support:
`d11-vector-recall-debug` returned unrelated Dagster, Oscilar, and Thistle
passages for a Turbopuffer exact-versus-ANN recall question and scored `-5.8328`,
which `-8.0` accepts. `m10` also returned none of its three judged overview
pages at `-3.178`. The incomplete judged-URL/group signal is TP30, FP15, FN0,
TN5, meaning 15 of 45 accepted cases missed that signal. Some may be useful
unjudged alternates, so this is not a complete passage-level confusion matrix;
it is nevertheless a material false-support warning.

Final review verified that automatic text and JSON apply the same rule; explicit
namespace retrieval bypasses it; weak top-one results widen only once; complete
weak searches produce `no_relevant_evidence`; partial weak searches produce
`inconclusive`; and all-failed retrieval still errors. The raw score remains
documented as a non-probability, and the 50-case diagnostic is not represented
as locked certification.

## Validation and evidence limits

- Full suites passed `677/677` on both Python 3.11 and Python 3.13. The final
  reviewer-focused suite passed `43/43`, and the evaluator-fix regression suite
  passed `56/56`.
- Dependency-lock, source, ranking, C6, diff-hygiene, distribution, and clean-
  wheel validation passed. The wheel SHA-256 is
  `6d662bd0eea974e79ecf741ad57985eb9c10e0d52676355754fabeda427c1661`;
  the source-archive SHA-256 is
  `992874d71a6b8b5f294211cc2b96d4e7a8682b82f7f82827de15d1133aff4ab5`.
- The clean wheel reported the active `-8.0` revision and passed package-data,
  tokenizer, help, and import smoke.
- Read-only live wheel smoke verified: transit no-answer returned
  `no_relevant_evidence`, zero hits, and `incomplete=false`; the Turbopuffer
  query returned `supported` with one hit; explicit
  `site-turbopuffer-com-v1` returned one hit without evidence/routing; and plain
  text used the careful no-evidence wording after searching three namespaces.
  No provider write occurred.
- The 50-case run remains diagnostic only. The owner supplied the separate
  authority for the provisional threshold; neither the run nor this code PASS
  supplies locked calibration, certification, or an error-rate claim.

## Verdict

The owner-authorized active delta is an independent code, security/redaction,
compatibility, evaluator, packaging, documentation, and governance PASS. It
implements the bounded provisional behavior and explicit bypass without
provider writes. This verdict does not claim locked statistical certification,
erase the known `d11` false support or heuristic caveats, authorize a release or
merge, or establish that `-8.0` is a stable long-term cutoff.
