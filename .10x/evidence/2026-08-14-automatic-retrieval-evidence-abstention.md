Status: recorded
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

- The first packaged schema-1 artifact was
  `automatic-retrieval-evidence-v1` revision `collect-unassessed-v1`, with
  `mode=collect`, `threshold=null`, and `owner_approved=false`. That historical
  phase gathered the observations below without changing results.
- On 2026-08-14, the owner explicitly approved replacing that collect-only
  behavior with `automatic-retrieval-evidence-v1` revision
  `owner-approved-provisional-minus-8-v1`, `mode=active`,
  `owner_approved=true`, and a provisional `-8.0` threshold. The
  owner was told before approval that the supporting diagnostic contained only
  five no-answer questions.
- Automatic text and JSON retrieval apply the same top-score rule. A weak
  high-confidence singleton widens once. A final weak result returns no hits as
  `no_relevant_evidence` when every search completed, or `inconclusive` with
  attributed failures when any selected namespace failed. Explicit namespace
  retrieval bypasses this gate.
- `-8.0` is a raw score for the exact pinned model and feature contract, not a
  probability or a locked certification result. There is no CLI, environment,
  or runtime override. Monitoring evidence can change the cutoff only through
  a new reviewed packaged revision.
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
- The five historical `no_answer`-category cases had top model scores from
  `-11.2867` through `-9.6270`, while all 45 `answer_expected`-category cases
  scored `-5.8328` or higher. This separates dataset question categories, not
  useful from irrelevant returned passages. Five negative-category cases are
  insufficient to establish future error rates or locked certification. The
  owner knowingly accepted that limitation when approving `-8.0` as a
  provisional active cutoff.
- `d11-vector-recall-debug` is a known false support: it asked about exact
  versus ANN recall in Turbopuffer, but automatic retrieval returned unrelated
  Dagster, Oscilar, and Thistle passages and the `-5.8328` top score is accepted
  by the provisional cutoff. `m10` scored `-3.178` but returned none of its
  three judged overview pages; useful unjudged alternates remain possible.
- The strongest available but incomplete judged-URL/group signal at `-8.0` is
  TP30, FP15, FN0, TN5. Thus 15 of 45 accepted cases, or 33%, missed that signal.
  Some of those 15 may be useful unjudged alternatives, so this is a monitoring
  warning rather than a complete passage-relevance confusion matrix.
- The collector correctly marked the report non-release-ready because the
  candidate working tree was dirty. It is a pre-commit diagnostic and is not
  trusted calibration, certification, release, or activation evidence.
- Focused evidence/routing/retrieval/CLI/evaluator/release tests passed
  `186/186` on Python 3.11 and `186/186` on Python 3.13.
- The complete suite passed `671/671` on Python 3.11 and `671/671` on Python
  3.13. The lock check resolved 154 packages; source-release, ranking-contract,
  tokenizer-forecast, and diff checks passed.
- The historical diagnostic wheel and source archive passed focused archive and
  metadata validation. A fresh Python 3.13 wheel install loaded the then-current
  collect artifact and passed version/import, both help paths,
  evidence-evaluator import, and offline tokenizer smoke. That historical smoke
  did not validate revision `owner-approved-provisional-minus-8-v1`; separate
  active-delta validation is recorded below. No publication occurred.
- No claim is made that a locked calibration/certification report, source-kind
  sufficiency gate, or statistically established error rate exists. Broader
  monitoring remains required even after the active implementation passes its
  code and compatibility checks.
- Public documentation changes are limited to `README.md`,
  `docs/retrieval.md`, `docs/migrating-to-buoy.md`, `docs/releasing.md`, and
  `CHANGELOG.md`.

## Active-delta final validation

- The complete suite passed `677/677` on Python 3.11 and `677/677` on Python
  3.13. The final reviewer-focused suite passed `43/43`, and the evaluator-fix
  regression suite passed `56/56`.
- The locked dependency check, source-release validation, ranking-contract
  validator, C6 tokenizer forecast, and final diff check passed.
- The diagnostic wheel and source archive passed distribution validation. Their
  SHA-256 digests are:
  - wheel:
    `6d662bd0eea974e79ecf741ad57985eb9c10e0d52676355754fabeda427c1661`;
  - source archive:
    `992874d71a6b8b5f294211cc2b96d4e7a8682b82f7f82827de15d1133aff4ab5`.
- A clean installed wheel reported calibration revision
  `owner-approved-provisional-minus-8-v1`, `mode=active`, and threshold `-8.0`.
  Packaged data, tokenizer, help, and module/import smoke passed.
- Read-only live smoke from that installed wheel produced:
  - the transit no-answer query: `no_relevant_evidence`, zero hits, and
    `incomplete=false`;
  - the Turbopuffer query: `supported` with one hit;
  - explicit `site-turbopuffer-com-v1`: one hit with no automatic evidence or
    routing object; and
  - plain automatic text: the bounded no-evidence wording after searching three
    namespaces.
- The live smoke performed catalog, inventory, and content reads only. It made
  no provider write, catalog/card mutation, content mutation, namespace change,
  reindex, model download, release, or publication.
- Independent final review passed the active implementation, compatibility,
  failure semantics, packaging, and records. This PASS does not erase the known
  `d11-vector-recall-debug` false support, the `m10` judged-page miss, the
  TP30/FP15/FN0/TN5 incomplete heuristic, or the absence of locked statistical
  certification.

## External effects

The governed diagnostic used the existing process-environment credential for
read-only Turbopuffer inventory, catalog, and content queries. The collector
exposed no provider mutation method and made no catalog/content write,
namespace/card change, content reindex, credential operation, model download,
or release action.
