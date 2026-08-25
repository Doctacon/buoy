Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/tickets/done/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md, .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-preparation.md, .10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md

# Provider Invocation Receipt Final Recovery Candidate Repair

## Question

Can the two independent candidate NO-GO findings be corrected entirely within
provider-free preparation while preserving the exact reviewed source and wheel?

## Bound candidate

The review and repair were bound to preparation evidence commit
`5e2259d5422a3f3b649c521422a868d770dc7d0d`, tree
`cc80dc4bf49ed3eec63b8d379b30af0e82f23f4d`, and wheel SHA-256
`42a4ba1be691de541c17df1e3d9858e3bf88e7a7b758461f7ccc19b899533f87`.

Provider-free reproof confirmed that the retained VCS-aware source remains
detached and clean at commit `0b27c4eaa2449493125f4040af3cd1f7c926b531`,
tree `9017c4a335938faca80cdded54545df8b79c12f8`. The retained wheel
remains exactly 730602 bytes with the bound SHA-256 above. Source and candidate
bytes were not changed.

## Repair ledger

| Stage | Generic outcome |
| --- | --- |
| evidence-gate correction | replaced shape-only values with exact reviewed commit/tree equality |
| arbitrary-binding rejection | PASS before the execution marker; dedicated live state remained empty |
| construction-only self-check | PASS with exact-evidence binding armed |
| automatic model-boundary inspection | exact retained source exposes a distinct second-model construction path |
| handoff-summary refresh | exact corrected harness identities retained; live eligibility set false |

The first handoff-summary write encountered the expected read-only retention
mode and made no change. Preparation restored owner-write permission only long
enough to refresh the owned summary, then restored its read-only mode. This was
an owned harness/summary correction, not source, candidate, cache, runtime, or
external-state mutation.

## Finding 1: exact evidence gate corrected

Both retained gate layers now compare the supplied values for exact equality
with the reviewed preparation evidence commit and tree above. Neither layer
accepts a merely well-formed 40-hex substitute.

Provider-free negative checks supplied a different valid lowercase 40-hex
commit while keeping the exact tree, then a different valid lowercase 40-hex
tree while keeping the exact commit. Both were rejected before creation of the
one-execution or command-start marker. The dedicated live-state directory
remained empty. The positive executable path was deliberately not run because
matching values would proceed toward the separately blocked live command.

The corrected retained hashes are:

- harness SHA-256:
  `2e249a4b3148398bd7e3e5640d13d6ad35a4baa2c1379b790a69058857514cd8`;
- wrapper SHA-256:
  `2e50db19ee9b7a11bcdc527d9bc95e2a860f13fe0809e1a94af14076d16f7317`;
- combined regular-file bytes: `6472`; and
- content-free handoff-summary SHA-256:
  `29f877d71b0744bb204255d4055095bd26dd19182581390adda2871a6d0371ae`.

The handoff summary binds each harness file by SHA-256, binds the exact reviewed
evidence commit/tree, and records `live_eligible` false. The harness directory,
its two files, and the handoff summary were restored to owner-read-only modes.

## Finding 2: exact candidate has a contract-blocking product defect

Static inspection of the exact retained source, without importing or
constructing any model, confirmed all of the following:

- `src/buoy_search/cross_encoder.py`, SHA-256
  `ed963371948f9c51fdbc7d25df4193613e7b2616f34ba18e7b7b2e01d2ba1674`,
  defines and constructs a model distinct from the only ratified
  `BAAI/bge-small-en-v1.5` model;
- automatic active routing can invoke that distinct model through the routing
  reranker loader;
- automatic multi-corpus retrieval can invoke it for initial fanout or fallback
  reranking; and
- the automatic evidence assessor can invoke it when existing cross-encoder
  scores are absent, while the unchanged automatic command always installs that
  assessor.

These are production paths in the exact reviewed source, not harness-invented
behavior. The authorized live child allows construction of only
`BAAI/bge-small-en-v1.5`. Provider-free preparation cannot inspect provider
results or safely assume that the private case avoids every reachable branch.
A harness override that disables the production loader would no longer preserve
the unchanged ordinary automatic path and can turn the sole one-shot command
into a model error. Authorizing the distinct model or changing product source is
outside this ticket.

Therefore no provider-free harness correction can make the exact source both
(1) preserve unchanged ordinary automatic behavior and (2) guarantee that only
the authorized model is constructed. This is a real defect in the exact product
candidate relative to the ratified live-command contract, not a cache,
environment, build, runtime, validator, or harness-mechanics defect.

## Prohibited access and retained state

This repair performed no credential read, model import/construction/load or
inference, provider-client creation, DNS, TLS, network, catalog/content access,
retrieval, telemetry database/store/API/command operation, existing-cache
access, global package/home access, source-ref mutation, or live-command start.
No raw query, credential, provider value, model content, command output,
receipt, private path, or diagnostic was retained.

The dedicated live-state, temporary, bytecode, and XDG directories are empty.
The exact source, wheel, owned cache, isolated runtime, corrected harness, and
content-free handoff summary remain retained privately. The wheel and source
identities remain exact; only owned harness and handoff-summary bytes changed.

## Conclusion

**CANDIDATE-PREPARATION-DEFECT.** The arbitrary evidence-binding defect is
repaired, but the exact product candidate cannot satisfy the approved one-model
live boundary while preserving the unchanged ordinary automatic command. The
preparation ticket is blocked, no PASS/GO may issue, and the dependent live
child remains ineligible and inactive.

This evidence proves only provider-free static reachability and retained-byte
identities. It proves no live branch was taken and makes no claim about provider
behavior, wire sends, SDK retries, billing, cost, or rate limits.
