# Automatic and explicit retrieval

`buoy retrieve QUERY` automatically chooses the relevant indexed corpora. The
router reads the live Turbopuffer namespace inventory and the validated cards
in `buoy-routing-catalog-v1`, then searches at most three content namespaces.

```bash
export TURBOPUFFER_API_KEY=...

# Inspect the automatic route. This reads routing state but not content.
buoy retrieve "How is approximate vector recall evaluated?" --dry-run

# Run the selected retrieval.
buoy retrieve "How is approximate vector recall evaluated?"
```

## Output modes

Every successful live retrieval uses compact, citation-first text by default,
including an explicit single namespace:

```text
Found 1 passage.

1. Retry behavior
   https://docs.example.com/retries · Backoff
   Requests use bounded exponential backoff and stop after the configured...
```

Each hit contains its rank, title, best available citation, optional section,
and a whitespace-collapsed excerpt capped at 320 characters. Citation choice
prefers a URL, then a repository path, source path, or stable row identifier.
Compact text omits namespace and ranking diagnostics, tags, redundant paths,
model and precision details, scores, and positive evidence diagnostics.

Use `--explain` to render the same result in the established detailed text
format. It includes the namespace, ordered tags, paths, embedding precision,
model, fusion/reranking, scores, and evidence diagnostics that apply. `--json`
retains the existing structured contract. `--explain` and `--json` are mutually
exclusive; combining them fails before configuration, credentials, model
loading, or provider calls. Dry-run and plan output remain detailed.

Output mode is presentation only. It does not change routing, widening,
retrieval, deduplication, ranking, deterministic tie-breaking, per-corpus
coverage promotion, result limits, evidence assessment, or provider calls.
Partial-failure warnings still identify failed namespaces. The existing
`assessment_failed` warning also remains visible in compact text, while
`supported`, `unassessed`, and shadow `would_*` evidence diagnostics are hidden.
No-relevant-evidence and inconclusive messages are unchanged. Buoy returns
passages and citations; it does not synthesize an answer.

`--plan` is an alias for `--dry-run`. Buoy reads credentials only from the
process environment and does not load `.env` automatically. If a local `.env`
is the intended credential source, load it explicitly into the command
subshell:

```bash
(
  set -a
  . ./.env
  set +a
  buoy retrieve "How is approximate vector recall evaluated?"
)
```

The runtime also reads `TURBOPUFFER_REGION` (default
`gcp-us-central1`), `BUOY_EMBEDDING_MODEL`, and
`BUOY_EMBEDDING_PRECISION`. `TURBOPUFFER_NAMESPACE` is ignored.

## Automatic routing

Automatic routing is intentionally bounded. Before it scores the question,
Buoy requires one valid card for every live content namespace. Reserved control
namespaces such as `buoy-routing-catalog-v1` and `buoy-evidence-*` are never
content candidates. Stale cards, missing cards, incompatible cards, and
disabled cards are reported; incomplete or corrupt coverage fails before any
content query.

Selection first looks for complete normalized titles or aliases in the
question:

- one named corpus selects that corpus;
- two or three named corpora select all of them in deterministic order;
- more than three named corpora fails with guidance to use explicit selection;
- otherwise a pinned local semantic router selects one corpus only when the
  top result clears both the confidence and margin thresholds;
- an ambiguous semantic route selects the top three, or every eligible corpus
  when fewer than three exist.

Automatic `--dry-run` requires `TURBOPUFFER_API_KEY` because live inventory and
catalog reads are routing authority. It performs those read-only requests and
one local route embedding, then reports selected cards, confidence, coverage,
and expected fanout. It does not embed the content query, query a content
namespace, or write provider state.

### Growing the routing catalog

Adding a corpus does not require adding it to the fixed end-to-end retrieval
answer key. Each new enabled corpus instead gets a small reviewed route-canary
pack: a named query, two descriptor-free capability queries, one query that is
easy to confuse with a neighboring corpus, and one contrast query that should
route elsewhere. The complete route-only suite is replayed against the current
eligible catalog so a new card cannot silently steal an existing route.

The unreleased scalable-routing foundation also understands an additive
`routing_examples` card field containing at most eight reviewed questions the
corpus can answer. These examples are separate from aliases and tags and never
trigger exact-name routing. A candidate router takes an exact in-memory vector
shortlist of at most twelve cards from the already-read catalog, then compares
their base text and examples with the pinned local MiniLM model. It still
queries at most three content namespaces and adds no provider query per card.

This candidate is intentionally inactive until its canaries are approved and
its confidence thresholds pass a locked calibration/certification run. The
live catalog remains schema v1 and the current cosine router remains production
authority. A later reader-first migration may add examples only after the new
reader is deployed; ordinary apply cannot invent capability examples from a
URL or source name and preserves reviewed manual examples.

## Explicit override

Supply `--namespace` to bypass namespace listing, catalog reads, and route-model
work. Repeat it to search a known set of two or three namespaces:

```bash
# Local, provider-free preview of one known namespace.
buoy retrieve "How are retries configured?" \
  --namespace github-example-service-v1 \
  --dry-run

# Explicit multi-corpus retrieval.
export TURBOPUFFER_API_KEY=...
buoy retrieve "Compare retry and deployment guidance" \
  --namespace github-example-service-v1 \
  --namespace site-example-docs-v1
```

Explicit namespaces must be unique and may be repeated at most three times. A
single explicit namespace preserves its established retrieval, ranking, and
JSON result contract; its default live text uses the same compact renderer as
every other live retrieval. An explicit preview is local, credential-free, and
provider-free.

## Search, widening, and reranking

The content query is embedded once. Each selected namespace runs ANN plus
boosted BM25 over title, section path, and content, then performs
within-namespace reciprocal-rank fusion and the source-aware file/page ranking
already used by single-namespace retrieval.

Source-aware defaults remain:

- websites, local documents, and database relations: page mode, no repository
  profile, pool 20, max aggregation;
- repositories: file mode, `repo-code` profile, pool 100,
  `adaptive-sum-3` aggregation.

A confident one-corpus route initially queries only that corpus. If it is
empty, fails, or returns a best evidence score below the provisional cutoff,
Buoy widens once to the next two route candidates. An explicit
single-namespace request does not cross this automatic evidence boundary and
retains its established raw-search behavior. A route that starts with two or
three corpora queries them concurrently, with at most three workers.

For a true multi-corpus result, each successful namespace contributes at most
eight hits. Buoy collapses exact citation/section/content duplicates, retains
at most 24 candidates, and gives each candidate a local MiniLM rank. The final
order uses fixed equal-weight reciprocal-rank fusion (`k=60`) of that MiniLM
rank and the candidate's existing namespace-local rank. Raw provider scores
and corpus-route scores are never mixed across namespaces. This keeps strong
local evidence from being erased while still letting the cross-encoder compare
the combined candidate set. The requested `--top-k` is the final global limit.
When that limit has room for every nonempty selected corpus, Buoy also retains
the existing local-rank-one hit from each corpus. If this safety rail replaces
a lower global result, JSON reports the promoted namespace; if `top_k` is too
small to represent every corpus, JSON reports that coverage was impossible.
Reranker load or inference failure fails the multi-corpus request rather than
returning an arbitrary cross-corpus order.

The exact model is `cross-encoder/ms-marco-MiniLM-L-6-v2` at immutable revision
`c5ee24cb16019beea0893ab7796b1df96625c6b8`. Loading is CPU-only,
`local_files_only`, safetensors-only, and remote code is disabled. Retrieval
does not download a model or accept an unpinned substitute. The snapshot is
about 88 MB. With the routing model already resident, a measured 24-candidate
run on the development Mac took about 0.58 seconds and added about 151 MiB of
peak working memory using the fixed batch size of eight. It is already present
in the development environment. If that exact snapshot is not
in the Hugging Face cache, an ambiguous multi-corpus request fails before its
content queries. A high-confidence single-corpus route queries that corpus
first; if evidence assessment then needs the missing model, the request fails
with a generic assessment error before widening or presenting results.

Overrides remain explicit:

```bash
buoy retrieve "customer cancellation reason" \
  --namespace customer-conversations \
  --ranking-mode page \
  --ranking-profile none \
  --ranking-pool 20 \
  --ranking-aggregation max
```

`--doc-kind` applies one exact metadata filter. Tags remain output and routing
card metadata, not retrieval-filter authority.

## Automatic evidence assessment

Automatic routing answers which indexed corpus is the closest fit; it cannot
by itself show that the returned rows are useful evidence. For live automatic
text and JSON retrieval, Buoy therefore scores the first up to five hits from
the exact final ranking, never beyond the requested `top_k`, with the same
immutable MiniLM revision used for cross-corpus reranking. Multi-corpus
retrieval reuses its existing scores. Automatic single-corpus retrieval may
load the model for this bounded check but keeps its original result order.
Explicit `--namespace` retrieval is unchanged and bypasses this check.

The current rule is deliberately simple: if the best final score is below
`-8.0`, the result is weak. The number is a raw cross-encoder score, not a
percentage, probability, or universal measure that can be compared with other
models. It applies only to the pinned model and retrieval contract documented
here.

The project owner explicitly approved `-8.0` on 2026-08-14 as a provisional
packaged starting point. The calibration revision is
`owner-approved-provisional-minus-8-v1`. There is no CLI, environment-variable,
or runtime threshold override. In the observed 50-question run, the
five questions categorized as `no_answer` scored from `-11.2867` through
`-9.6270`, while all 45 questions categorized as `answer_expected` scored
`-5.8328` or higher. This separates question categories, not relevant from
irrelevant returned evidence.

There is already a known false support above the cutoff:
`d11-vector-recall-debug` asked about exact versus ANN recall in Turbopuffer but
automatic retrieval returned unrelated Dagster, Oscilar, and Thistle passages
with a top score of `-5.8328`. The `m10` case also scored `-3.178` without
returning any of its three judged overview pages, although unjudged alternates
could still be useful. Against the incomplete judged-URL/group signal, `-8.0`
produced TP30, FP15, FN0, and TN5: 15 of 45 accepted cases, or 33%, missed that
signal. That is not a complete relevance judgment, but it makes the residual
false-support risk explicit. Evaluation must monitor accepted-passage quality,
and the cutoff may change only through a new reviewed packaged revision as
broader passage-level judgments are collected.

A weak high-confidence one-corpus result widens once to the next two routed
candidates with reason `weak_top1`. After that final attempt:

- a score at or above `-8.0` returns the normal ranked hits as `supported`;
- a score below `-8.0` with every namespace search complete returns no hits as
  `no_relevant_evidence`; and
- a score below `-8.0` with any namespace failure returns no hits as
  `inconclusive`, preserves the attributed failures, and marks the response
  incomplete.

If every namespace fails, retrieval still fails normally. The complete weak
text result says “No sufficiently relevant evidence was found in the indexed
corpora.” An inconclusive result says that namespace failures prevented a
complete assessment. Neither outcome claims that an answer does not exist.
Automatic preview does not query content, so it reports the planned threshold
but cannot make an evidence decision.

## Results and failures

The underlying result retains its source URL/path, title, section, content
preview, stable row identity, score diagnostics, and ordered tags. Compact text
shows only the citation-first subset described above; `--explain` exposes the
detailed text representation. Automatic and explicit multi-corpus JSON retain
selected `namespaces`, routing and reranking details, per-hit `namespace`,
per-namespace summaries, and failures. Automatic live JSON additionally
retains the governed `evidence` mode, status, model and calibration identities,
the `-8.0` threshold, bounded score features, and whether weak evidence
triggered widening. It does not include extra raw content in evidence
diagnostics.

One selected namespace failing does not discard successful results. Buoy
redacts and attributes the failed namespace and marks the combined response
`incomplete`. If every attempted namespace fails, the command fails. An empty
namespace is not itself a provider failure; it contributes no candidates, and
the one-corpus automatic path still performs its single widening attempt.

## Catalog inspection and management

Catalog reads and mutations require `TURBOPUFFER_API_KEY` because
`buoy-routing-catalog-v1` is remote authority:

```bash
buoy catalog list
buoy catalog list --all
buoy catalog show site-example-docs-v1

# Preview, then approve the same enablement change.
buoy catalog disable site-example-docs-v1
buoy catalog disable site-example-docs-v1 --approve
buoy catalog enable site-example-docs-v1
buoy catalog enable site-example-docs-v1 --approve
```

`catalog upsert` creates or replaces one complete manual card; use
`buoy catalog upsert --help` for its required source, embedding, and ranking
fields. The unreleased reader accepts repeatable `--routing-example` values
for a complete manual-card preview. Prefer the narrower reviewed-example
operator below when only that field is changing. `upsert`, `enable`, and
`disable` are previews unless `--approve` is present. They modify routing cards
only. They never delete, enable, disable, or otherwise mutate a content
namespace.

### Reader-first schema and reviewed examples

Deploy the exact v1/v2-compatible reader everywhere before changing the shared
catalog schema. The reader deployment itself is inert. Then capture a fresh
read-only migration preview:

```bash
buoy catalog migrate-routing-v2 --json
```

Review its normalized schema fingerprint, exact four nonfilterable additions,
complete namespace/card-revision bindings, vector-inclusive projection hash,
old-reader warning, and zero performed writes. Approval must use both exact
values emitted by that same preview:

```bash
buoy catalog migrate-routing-v2 \
  --expected-snapshot-revision REPLACE_WITH_PREVIEW_SHA256 \
  --expected-projection-sha256 REPLACE_WITH_PREVIEW_SHA256 \
  --approve --json
```

The approved migration issues one schema-only request. It sends no rows and
then requires an unchanged, complete schema-v2 strong read. Drift or incomplete
verification is a failure requiring a new preview; Buoy never attempts schema
rollback.

After schema v2 is verified, preview one card's reviewed questions. Repeat
`--routing-example` for one through eight exact questions:

```bash
buoy catalog set-routing-examples site-example-docs-v1 \
  --routing-example "How do I configure bounded retries?" \
  --routing-example "Where is request timeout behavior defined?" --json
```

Review the normalized questions, current and intended revisions, both prototype
hashes, and the one-card/one-write budget. Approval is conditional on the exact
current revision from that preview:

```bash
buoy catalog set-routing-examples site-example-docs-v1 \
  --routing-example "How do I configure bounded retries?" \
  --routing-example "Where is request timeout behavior defined?" \
  --expected-card-revision REPLACE_WITH_PREVIEW_SHA256 --approve --json
```

This operation preserves every base and non-prototype card field and must affect
exactly the target's deterministic row ID. Repeating an already-stored canonical
set is a zero-model, zero-write success. Later ordinary applies preserve reviewed
examples on both manual and generated cards. Neither command reads or writes a
content namespace, changes enablement, or activates prototype routing; production
automatic retrieval continues to use the legacy base-vector route until a
separate activation release passes.

## Evaluation

The ordinary `buoy evals` command still evaluates one explicitly named corpus:

```bash
buoy evals --namespace site-example-docs-v1 --dry-run
buoy evals --namespace site-example-docs-v1 --live
```

The automatic-routing release gate is a separate governed 50-query basket:
20 named-source questions, 15 descriptor-free/confusable questions, 10
multi-corpus questions, and 5 no-answer questions. Its checked-in labels remain
marked candidate until a human approves them against current indexed content.
Provider-backed scoring is read-only and compares automatic results with an
exhaustive search of all four eligible logical corpora; the disabled duplicate
Dagster namespace is covered by a card but never earns route or retrieval
credit.
