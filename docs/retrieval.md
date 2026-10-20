# Local retrieval

`buoy retrieve QUERY` chooses relevant indexed corpora from the routing catalog
in your local DuckDB database, then searches at most three content namespaces.
No API key or region setting is needed. Set `BUOY_HOME` and `HF_HOME` consistently
with indexing; see [offline setup](local-duckdb.md).

```bash
# Inspect routing without querying content (uses cached routing models).
buoy retrieve "How do we deploy?" --dry-run

# Automatic local search.
buoy retrieve "How do we deploy?"

# Bypass routing and search one explicit namespace.
buoy retrieve "How do we deploy?" --namespace work-docs

# Search up to three namespaces, embedding once and reranking locally.
buoy retrieve "How do we deploy?" --namespace work-docs --namespace work-code
```

## Hybrid search and ranking

Each content namespace combines:

1. DuckDB native exact cosine vector search over 384-dimensional float32 vectors.
2. BM25 keyword scoring over title (boost 2), section path (boost 1.5), and content.
3. Client-side reciprocal-rank fusion, with deterministic tie-breaking.
4. Existing page/file/chunk grouping and optional repository ranking heuristics.

`--top-k` sets the final result limit; `--candidates` controls each retrieval
channel's candidate pool. `--doc-kind` filters both channels before their limit.
Use `buoy retrieve --help` for grouping/ranking overrides. Multi-namespace results
use the pinned local MiniLM cross-encoder and bounded cross-namespace fusion.
No generative LLM is invoked: Buoy returns evidence, not a synthesized answer.

This is **not ANN/HNSW**. The retained internal `ANN` query expression is executed
as exact DuckDB cosine search. No extension installation is necessary. Local
BM25 tokenization and search rankings differ from the previous hosted backend;
old cloud metrics are not performance or quality promises for this branch.

## Output and previews

Compact text shows the best citation and a short passage excerpt. `--explain`
includes namespaces, scores, grouping and evidence diagnostics. `--json` returns
the structured result. `--explain` and `--json` are mutually exclusive.

`--plan` aliases `--dry-run`:

- An **explicit namespace preview** does not read the index or load a model.
- An **automatic preview** reads the local catalog and runs local route selection,
  but does not issue a content search or modify the index.

No command reads `TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, or
`TURBOPUFFER_NAMESPACE`. Those obsolete settings have no effect. The legacy
`--region` option accepts `local` only. The default embedding contract is pinned
BGE-small, float32; keep it unchanged between indexing and retrieval.

JSON `credentials_required` is false. `local_index_operations` describes local
storage work. Historical generic `api_calls_occurred`, request counters, and
provider-invocation telemetry count calls to the local storage interface; they
do not represent HTTP traffic or billable operations.

## Persistent local model worker

On WSL2/POSIX, retrieval can reuse pinned models in a private local worker.
Communication uses a Unix-domain socket, not an external service. The worker
exits after five minutes of inactivity. Cached model weights are required even
when the worker is enabled. Missing models never trigger a download.

```bash
buoy retrieve "How do we deploy?" --namespace work-docs --no-embedding-worker
```

Use `--no-embedding-worker` to force in-process inference, for troubleshooting,
or when experimenting with an explicitly installed GPU runtime. A failed worker
falls back to in-process inference with one bounded warning. Models default to
CPU; the recommended installation does not use your laptop's limited VRAM.

## Automatic routing and evidence

Approved apply registers the namespace's card automatically, including up to
eight representative passages from the reviewed source. The first local apply
creates the reserved schema-v3 catalog. No separate cloud provisioning is needed.

Routing prefers exact normalized titles/aliases. Otherwise it takes a bounded
vector shortlist and compares candidate passages with the pinned local reranker.
An uncalibrated/new catalog uses up to three candidates rather than claiming
certified singleton confidence. Disabled, stale, missing, and incompatible cards
are reported; malformed catalog state fails rather than silently ignoring it.

Automatic evidence assessment retains the existing provisional relevance gate.
Its historical thresholds have **not been recalibrated for DuckDB or your work
corpus**. Inspect results and evaluate representative questions. Explicit namespace
search bypasses automatic routing/abstention when you need raw search behavior.
Empty results are not proof that an answer does not exist. Partial namespace
failures retain successful results with `incomplete=true`; total failure is an
error, not a fabricated empty success.

## Catalog management

```bash
buoy catalog list --all --json
buoy catalog show work-docs --json
buoy catalog disable work-docs           # preview
buoy catalog disable work-docs --approve # commit
buoy catalog enable work-docs --approve
```

`catalog upsert` edits complete manual cards; see its help for required source,
embedding and ranking fields. Mutations preview unless `--approve` is explicit.
Manual titles, summaries, aliases, tags, and enabled state survive later applies.
Disabling a card only affects automatic routing; it does not delete content.

### Reader-first schema and reviewed examples

Fresh local indexes start at schema v3. Existing compatible local catalogs can
still use the revision-bound `migrate-routing-v2`, `migrate-routing-v3`, and
`set-routing-examples` commands. Preview first, inspect their JSON, and supply the
exact requested revision/projection hashes with approval. These commands change
catalog state, not indexed content. The system-owned source passage bank is
updated by approved apply, not generic manual card editing.

A post-content catalog failure is reported as `partial_success`; content and
applied state remain committed. Retain the plan and follow the emitted
`catalog repair-apply --inspect-current` or revision-bound repair command rather
than replaying a baseline-stale apply. See [indexing](indexing.md).

The database and routing cards contain source excerpts. Filesystem access to
BUOY_HOME is content access; protect it accordingly.
