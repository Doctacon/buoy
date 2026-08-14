Status: provisional
Created: 2026-08-14
Updated: 2026-08-14
Ticket: .10x/tickets/2026-08-14-implement-automatic-retrieval-evidence-abstention.md

# Automatic Retrieval Evidence Abstention Evidence

## Candidate

- Branch: `work/automatic-retrieval-abstention`
- Base: merged `origin/develop`
  `9cd80752953e4f48ade343832de8d1e8cfd65f9f`
- Implementation boundary: automatic live retrieval after routing and content
  retrieval. Explicit single- and multi-namespace retrieval remains outside
  the assessor and preserves its existing contract.
- The assessor reuses the immutable
  `cross-encoder/ms-marco-MiniLM-L-6-v2` revision
  `c5ee24cb16019beea0893ab7796b1df96625c6b8`. An automatic single-corpus
  request may load it for evidence scoring without changing local result
  order; an explicit single-corpus request does not.

## Provisional rollout state

- The packaged schema-1 artifact is
  `automatic-retrieval-evidence-v1` revision `collect-unassessed-v1`, with
  `mode=collect`, `threshold=null`, and `owner_approved=false`.
- Collect mode records bounded, content-free observations and reports
  `unassessed` for automatic JSON/evaluator runs. It preserves the existing
  hits and does not treat an unknown score as weak, so it neither triggers
  `weak_top1` widening nor suppresses a result. Ordinary text retrieval skips
  the otherwise-discarded collect inference.
- The packaged loader and calibrated assessor reject all shadow and active
  artifacts. A later reviewed implementation must verify exact runtime and
  certification-report bindings before shadow can be enabled. Active then also
  requires an exact owner-approved artifact and passing locked certification.
- The public active-mode wording is bounded to “No sufficiently relevant
  evidence was found in the indexed corpora.” No mode may claim that an answer
  does not exist.

## Validation state

- A governed read-only diagnostic collector completed all 50 cases from the
  dirty candidate tree. It recorded 50 `unassessed` observations and zero
  assessment failures. Logical call accounting was 50 routing embeddings, 50
  content embeddings, 50 local reranker calls, 99 automatic namespace queries,
  and 200 exhaustive namespace queries.
- The diagnostic report's exact-key privacy audit found no `question`, `query`,
  `passage`, `content`, `vector`, `credential`, `token`, or `api_key` field.
- Existing multi-corpus metrics remained passing in this diagnostic run:
  route Recall@3 `0.982759`, automatic Recall@5 `0.970588`, reranked nDCG@5
  improvement `0.062256`, average fanout `1.98`, maximum fanout `3`, and zero
  incorrect high-confidence singleton routes.
- The five historical no-answer cases had top evidence scores from `-11.2867`
  through `-9.6270`, while answer-bearing categories extended substantially
  above that range. This is encouraging separation, but five negative cases
  are deliberately insufficient to select or activate a threshold.
- The collector correctly marked the report non-release-ready because the
  candidate working tree was dirty. It is a pre-commit diagnostic and is not
  trusted calibration, certification, release, or activation evidence.
- Focused evidence/routing/retrieval/CLI/evaluator/release tests passed
  `186/186` on Python 3.11 and `186/186` on Python 3.13.
- The complete suite passed `671/671` on Python 3.11 and `671/671` on Python
  3.13. The lock check resolved 154 packages; source-release, ranking-contract,
  tokenizer-forecast, and diff checks passed.
- The final diagnostic wheel and source archive passed focused archive and
  metadata validation. A fresh Python 3.13 wheel install passed version/import,
  both help paths, packaged collect-artifact loading, evidence-evaluator import,
  and offline tokenizer smoke. No publication occurred.
- Independent product/governance and code/security/calibration reviews passed
  for the collect-only boundary. Threshold selection, locked certification,
  runtime binding, and owner activation approval remain explicitly deferred.
- No calibrated threshold, shadow candidate, active artifact, or passing
  certification claim exists in this provisional record.
- Public documentation changes are limited to `README.md`,
  `docs/retrieval.md`, `docs/releasing.md`, and `CHANGELOG.md`.

## External effects

The governed diagnostic used the existing process-environment credential for
read-only Turbopuffer inventory, catalog, and content queries. The collector
exposed no provider mutation method and made no catalog/content write,
namespace/card change, content reindex, credential operation, model download,
or release action.
