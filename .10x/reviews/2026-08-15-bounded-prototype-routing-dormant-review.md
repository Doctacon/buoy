Status: pass
Created: 2026-08-15
Updated: 2026-08-15
Ticket: .10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
Specification: .10x/specs/bounded-prototype-routing-activation.md
Decision: .10x/decisions/buoy-activates-certified-bounded-prototype-routing.md

# Bounded Prototype Routing Dormant Review

## Scope and exact reviewed candidate

The independent review compared the settled dormant task-worktree candidate
with its governing ticket, specification, decision, authorization evidence,
public documentation, evaluator and release gates, focused regressions, and
the unchanged `develop` base. It covered governance order, exact collect
authority, packaged canary ground truth, explicit-namespace bypass, collect
legacy selection, active strict loading and fail-closed call order, evidence
compatibility and bounded widening, evaluator receipts, archive inventory,
installed-package behavior, redaction, and phase-independent tests.

The reviewed candidate is on `work/activate-bounded-prototype-routing` against
base commit `94b06ac58c86e96ddd012aae0a4a019dcc548cef` and base tree
`c002897fc3224faae9c8670f785e906884100890`, before its dormant handoff
commit. The governing records were present before production source behavior
was changed, and the packaged authority remained collect-only throughout this
implementation and review checkpoint.

The exact pre-review candidate comprised the following 26 changed or new
paths; this review file is the sole subsequent addition:

```text
.10x/decisions/buoy-activates-certified-bounded-prototype-routing.md
.10x/evidence/2026-08-15-bounded-prototype-routing-activation-authorization.md
.10x/specs/bounded-prototype-routing-activation.md
.10x/tickets/2026-08-15-activate-bounded-prototype-routing.md
.github/workflows/ci.yml
.github/workflows/release-readiness.yml
CHANGELOG.md
README.md
docs/retrieval.md
scripts/evaluate_routing_quality.py
scripts/release_automation.py
src/buoy_search/cli.py
src/buoy_search/data/routing_canaries/rentptr.json
src/buoy_search/data/routing_canaries/salesforce.json
src/buoy_search/data/routing_canaries/whiteboxgeo.json
src/buoy_search/evidence.py
src/buoy_search/multi_corpus_evals.py
src/buoy_search/routing.py
src/buoy_search/routing_quality.py
tests/routing_confidence_fixtures.py
tests/test_automatic_routing.py
tests/test_evidence.py
tests/test_release_automation.py
tests/test_retrieval_evidence.py
tests/test_routing_activation_cli.py
tests/test_routing_quality.py
```

For each path above, the reviewer formed one line as
`<repository-relative-path> <raw-file-sha256>\n`, sorted the paths in bytewise
order, and SHA-256 hashed the resulting UTF-8 manifest. Its digest is
`9588d936b6484701cbb73f3d436c2f4696d60b5d4c15f7fac2481a5881a75c09`.
The production and evaluator source bytes within that manifest are:

- evaluator runner `scripts/evaluate_routing_quality.py`:
  `6f179cb93ef85754e05e86bf8f300f1d430aefa34cccbf3ae7e23feb618402cc`;
- evaluator scorer `src/buoy_search/routing_quality.py`:
  `be8792b94698f8775760988583eb912a187da666a03f6a0ae234b4d26d014079`;
- `src/buoy_search/routing.py`:
  `340f7f804923dad9a9fb0c563507b3cdb807260e7713dbeffe881138921198c5`;
- `src/buoy_search/cli.py`:
  `27fef95c69a82fe733863b193e44bbe9821383a49e02321a1bfda184b1ea9dff`;
  and
- `src/buoy_search/evidence.py`:
  `78b792098ee0c49bedc7c135dffc33f4096f7d92222bc437f5d8438f1e015c7b`.

Any production, evaluator, test, package, workflow, documentation, or
governance change beyond adding this review invalidates this dormant PASS and
requires a fresh review before live collection.

## Authority, routing, and failure-boundary findings

- The installed confidence artifact is still the exact tracked schema-v1
  collect file. It is byte-identical to the base at SHA-256
  `23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed`,
  remains owner-unapproved with null thresholds and a zero-case non-passing
  certification, and cannot activate prototype routing.
- The loader accepts only the exact collect shape or the exact frozen
  schema-v2 active shape. Active state is accepted only from the installed
  package artifact and requires exact scalar and nested object types, all
  frozen bindings and receipts, current scorer/routing/CLI/evidence byte
  hashes, finite exact thresholds, and the certified catalog projection.
  There is no CLI, environment, configuration, public path, strategy, or loose
  threshold override.
- Repeated explicit namespaces resolve before confidence, catalog, routing
  embedder, and routing reranker work. Valid collect mode calls the unchanged
  legacy hybrid selector. Valid active mode calls only the bounded prototype
  selector and cannot silently fall back to legacy routing.
- Active automatic routing validates authority and the complete eligible
  catalog before routing-model use, then validates prototype state again at
  the selector boundary. Content configurations, resources, and queries occur
  only after route selection. Artifact failure, catalog drift, stale prototype
  state, BGE load/inference failure, or MiniLM load/inference failure returns a
  fixed redacted routing error before content construction or query.
- Exact title/alias routing remains authoritative. Descriptor-free routing
  uses one local top-twelve shortlist and one bounded MiniLM batch. A singleton
  requires inclusive passage-score and two-corpus margin floors; a one-card
  catalog cannot manufacture a margin. Initial and fallback selections remain
  unique and capped at three.
- Routine output contains only permitted ranks, scores, margins, hashes, and
  active authority identifiers. It contains no canary question, routing
  example, prototype passage, vector, credential, provider payload, or raw
  model exception.

## Ground truth, evaluator, and downstream compatibility

The source, wheel, and source-distribution gates require exactly these three
packaged current canary files and raw SHA-256 identities:

- RentPTR:
  `5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5`;
- Salesforce:
  `32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d`;
  and
- WhiteboxGeo:
  `5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916`.

Together with the unchanged approved legacy basket, they load exactly 65
cases and reconstruct suite
`0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5`.
No disabled synthetic pack is present in the source or archive inventory, and
ordinary retrieval never reads the packaged canary questions.

The route-only evaluator emits the collect artifact, runner, scorer,
routing-module, CLI-module, and evidence-module hashes. Its activation verdict
recomputes calibration thresholds and split receipts, certification IDs and
complete verdict digest, runner/scorer receipts, suite/catalog bindings, clean
source identity, and zero content/per-card/write/download accounting. The
active loader independently checks the packaged scorer/routing/CLI/evidence
bytes before returning authority.

Both prototype selection reasons are accepted by evidence normalization. A
CLI-level live fake proves active route context, all three bounded candidates,
initial fanout one, and weak-evidence result wiring. A real
`MultiNamespaceRetriever` regression proves that a weak prototype singleton
widens exactly once to the next two candidates and reuses one reranker.

The separate provider-backed 50-case end-to-end retrieval evaluator remains a
fixed four-corpus basket. Modernizing it for arbitrary active catalogs is a
separately governed read-only validation enhancement, not a condition of this
dormant route-only checkpoint. Later evidence must remain precise: route
selection may be live-certified by the required 65-case collector; active
downstream answer quality is locally regression-tested here and is not yet a
provider-backed certification claim.

## Validation

Parent closure recorded these exact frozen-tree results:

- the focused activation boundary passed `152/152` under locked Python 3.11
  and `152/152` under Python 3.13;
- full repository discovery passed `805/805` under Python 3.11 and `805/805`
  under Python 3.13;
- source-release validation, the frozen ranking-contract validator, the C6
  forecast validator's expected readiness-false checkpoint, Python
  compilation, and `git diff --check` passed; and
- no provider-backed test or model download was run.

The independent reviewer additionally observed:

- `167/167` focused routing-quality, automatic-routing, activation CLI,
  evidence, multi-corpus-evidence, release-automation, evaluator-runner, and
  real-retriever tests passing under Python 3.13;
- `72/72` routing-quality and automatic-routing tests passing with the module
  default replaced by a synthetic valid installed active artifact, proving
  that the test boundary does not depend on the current packaged collect
  phase; and
- source-release validation, exact 65-case suite reconstruction, the collect
  artifact/base equality check, and `git diff --check` passing independently.

A fresh diagnostic build from these exact uncommitted source bytes produced a
69-file wheel at SHA-256
`700093391034046f4874b89c65a3f0be195877f41c7161faf47ba3f667dcb981`
and a 140-file source distribution at SHA-256
`dd0b21a25ce58d66526e9b9cbc79fcc12b0455941d9037999fc73033ea12b85f`.
Real wheel/source-distribution validation passed. The wheel's scorer, routing,
CLI, and evidence bytes exactly matched the current source hashes recorded
above. An isolated locked-dependency wheel installation reproduced exactly the
three canary members and hashes, the 65-case suite and digest, and loaded the
default authority as `mode=collect`, `owner_approved=false`, and
`certification_passed=false`. Nothing was published.

Because version metadata necessarily identifies base `g94b06ac58` while this
candidate is uncommitted, those archives are diagnostic rather than the final
dormant-commit distribution receipt. A fresh build and validation from the
clean dormant commit remain mandatory before any final distribution or
activation claim.

## External effects

The implementation, parent validation, and independent review made no
Turbopuffer or other provider call, acquired no provider credential, performed
no catalog/schema/card/content query or mutation, and made no model download.
No namespace, card, example, content row, credential, tag, release, or package
state changed. The diagnostic archives and isolated environment remained
local and unpublished. The independent reviewer changed only this review
record and did not commit, push, merge, deploy, tag, or publish.

## Verdict and next gate

PASS for the exact dormant implementation described above. No P1 or P2
finding remains. This review authorizes only creating a clean dormant commit
containing the exact reviewed candidate and this review, followed by the
governed read-only 65-case route collection from that exact commit.

It does not authorize writing the schema-v2 active artifact, provider
mutation, catalog repair, activation, integration, merge, deployment, tag,
release, or publication. The dormant collector must reproduce every frozen
suite, catalog, threshold, split, verdict, source, module, and zero-side-effect
receipt exactly. Any mismatch or dirty source stops the sequence. Only a
separate independent audit of that clean report may permit the later
artifact-only activation checkpoint.
