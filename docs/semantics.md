# Autonomous local semantics

Semantic Phase 3B turns one completed [remote evidence snapshot](evidence-snapshots.md) into one immutable set of reusable **concepts**, exact **evidence mentions**, and a lightweight **taxonomy**. It is not a complete ontology and does not extract factual assertions.

```text
completed evidence catalog + active ledger membership + immutable branches
  -> local model extraction, alias/sense resolution, taxonomy verification
  -> remote concepts + mentions + taxonomy + completed semantic catalog row
  -> one bounded local build.json + zero/small same-host lock state
```

## Privacy and local runtime contract

All inference uses an explicitly configured external local OpenAI-compatible Chat Completions server. Buoy accepts only credential-free HTTP(S) endpoints whose host and every resolved/connected address are loopback (`127.0.0.1`, `localhost`, or `::1`). It connects directly to a validated numeric loopback address, ignores environment proxies, sends no API key or cookies, follows no redirects, bounds request/response bytes, applies an explicit total deadline, and never falls back to a hosted provider. Prompt and response bodies are not logged.

The adapter works with compatible local runtimes such as Ollama and llama.cpp. It uses `temperature=0`, an explicit seed when the runtime confirms support, and strict runtime-compatible JSON schema output. `determinism` is still `best_effort`: local hardware, runtime builds, batching, caches, and backend behavior can change output. An immutable model revision is mandatory. Ollama's observed manifest SHA-256 digest can verify the pin; runtimes without a digest require an externally supplied revision and record that limitation. Build re-probes the synthetic-only model contract after inference and fails on any pin or contract drift before final remote validation and catalog publication. Model ID, revision, quantization when known, context length, seed/structured-output capabilities, runtime protocol/version, and prompt contract are provenance. Endpoint host/port is deliberately excluded from build identity.

Buoy packages and downloads no model weights. The external runtime owns model storage. Ordinary imports/help, verification, and inspection load no local model.

## Commands

Check the local model using synthetic text only:

```bash
uv run buoy semantics doctor \
  --model-endpoint http://127.0.0.1:11434/v1 \
  --model-id <local-model> \
  --model-revision <immutable-revision> \
  --model-context-window 8192
```

Doctor reads no evidence and makes no turbopuffer call. It reports the model contract, strict-output and seed support, observed latency, sanitized platform/memory/runtime metadata, and that no evidence was transmitted.

Estimate before building:

```bash
uv run buoy semantics estimate \
  --snapshot-id evidence_<id> \
  --model-endpoint http://127.0.0.1:11434/v1 \
  --model-id <local-model> \
  --model-revision <immutable-revision> \
  --model-context-window 8192
```

Estimate verifies the completed snapshot, reads active counts and at most 20 deterministically sampled active rows, performs bounded local extraction calls, and reports approximate UTF-8/token/model-call/time/object ranges plus limit pass/fail. Tokens use a conservative UTF-8-byte heuristic unless a trustworthy tokenizer exists. Estimate writes no remote namespace and no local artifact.

Build the complete active snapshot by default:

```bash
uv run buoy semantics build \
  --snapshot-id evidence_<id> \
  --model-endpoint http://127.0.0.1:11434/v1 \
  --model-id <local-model> \
  --model-revision <immutable-revision> \
  --model-context-window 8192
```

A failed extraction leaves deterministic remote staging. Continue only with the identical contract and explicit `--resume`; exact valid rows are reused and missing rows are processed. Conflicting input, chunk, model, prompt, candidate, or output hashes fail closed. Incomplete internal namespaces are retained and reported, never automatically deleted.

Experimental sampling is explicit:

```bash
uv run buoy semantics build ... --sample-size 25 --sample-seed 7
```

Sampling is stable-hash, deterministic, and stratified across source namespaces where possible. Its catalog and manifest say `sampled`; it is never presented as full coverage.

Verify and inspect without a model:

```bash
uv run buoy semantics verify --build-id semantics_<id>
uv run buoy semantics inspect --build-id semantics_<id> --kind concepts --status accepted --limit 25
uv run buoy semantics inspect --build-id semantics_<id> --kind mentions --limit 25
uv run buoy semantics inspect --build-id semantics_<id> --kind taxonomy --status provisional --limit 25
uv run buoy semantics inspect --build-id semantics_<id> --kind summary
```

Verify streams the remote catalog, exact schemas, concepts, mentions, taxonomy, and active evidence membership; recomputes row/logical hashes and build identity; validates mention/concept/evidence references, status rules, taxonomy endpoints and accepted acyclicity, counts, and an available/supplied manifest. It never writes or loads a model. Inspect is remote-read-only, limited to 100 rows, and returns bounded excerpts/provenance/score breakdowns—not full evidence.

## Concepts, mentions, and taxonomy

Controlled concept types are `process`, `capability`, `metric`, `problem`, `technique`, `technology`, `product`, `organization`, `person`, `place`, `event`, and fallback `domain_concept`. Generic filler, complete claims, and arbitrary nouns are rejected by default.

Every published concept has one or more mention rows. A mention stores exact bounded surface/excerpt plus snapshot, branch, source namespace/row, chunk/page hashes, canonical URL, title/section, model and prompt provenance. Full evidence content and vectors are not copied.

Stored taxonomy predicates are only:

- `broader`, from child to parent; `narrower` is derived and not duplicated;
- `related`, one canonical ordered symmetric pair;
- `close_match`, one canonical ordered symmetric pair for distinct similar concepts.

Exact aliases are stored on the canonical concept. There are no arbitrary `causes`, `depends_on`, `owned_by`, or other ontology predicates.

## Autonomous confidence policy

Defaults are accepted at `0.85` and provisional at `0.65`; overrides must satisfy `0 <= provisional < accepted <= 1` and become build identity. Low-scoring candidates are rejected from final namespaces. There is no item-by-item approval gate.

Policy `semantic-confidence-v1` combines applicable strict schema and exact-substring validation, extraction score, mention/namespace support, lexical consistency, local similarity, independent merge/taxonomy verifier judgment, controlled-type consistency, and structural validity. Raw model confidence cannot by itself publish an accepted object. Rows retain a compact score breakdown and at most 280 characters of rationale, never chain-of-thought.

Alias merging requires accepted-threshold independent same-concept verification. Medium-confidence matches stay separate and may become provisional `close_match`. Every taxonomy proposal receives a separate local verification prompt. Programmatic validation rejects self/duplicate edges, enforces canonical symmetric ordering, at most three accepted parents, maximum accepted depth 12, and an acyclic accepted `broader` graph.

## Coverage, budgets, and storage

Fail-closed defaults (never silent truncation):

- 500 active evidence rows;
- 4,000,000 evidence UTF-8 bytes;
- 2,000 model calls;
- 21,600 wall seconds;
- 10,000 candidates;
- 5,000 concepts;
- 20,000 taxonomy relations;
- 268,435,456 derived UTF-8 bytes;
- model concurrency exactly 1.

Semantic data lives in turbopuffer internal namespaces:

- `buoy-semantics-extractions-<build-short-id>`;
- `buoy-semantics-concepts-<build-short-id>`;
- `buoy-semantics-mentions-<build-short-id>`;
- `buoy-semantics-taxonomy-<build-short-id>`;
- fixed `buoy-semantics-catalog-v1`, whose completed row is written last.

Both `buoy-evidence-` and `buoy-semantics-` are excluded from ordinary retrieval, routing cards, namespace discovery, and Command Center source inventory. Semantic commands never write source namespaces or evidence branches.

The only persistent local semantic data artifact is `artifacts/semantic-builds/<build-id>/build.json`, atomically written after remote completion and capped at 256 KiB. Buoy may also retain a zero/small lock file as normal bounded same-host operational state; it contains no corpus or semantic objects. It contains IDs, contracts, coverage, counts, hashes, activity, and quality summary—not evidence content, candidates, mentions, graph data, prompts, raw responses, endpoint credentials, paths, or model weights.

Build identity hashes snapshot/coverage/sampling, pinned model and prompt contracts, embedding contract, type/taxonomy/confidence versions, thresholds, and safety limits. Creation time, endpoint, paths, provider request IDs, and timing are excluded. The separate semantic logical hash binds completed rows. Contract-identical best-effort inference is not claimed to regenerate bit-identical output.

## Current limits and roadmap

- **Phase 3A — remote evidence snapshots: implemented**
- **Phase 3B — autonomous local concepts, mentions, and taxonomy: implemented**
- **Phase 3C — evidence-backed typed assertions: future**
- **Phase 4 — graph review and visualization: future**
- **Phase 5 — incremental semantic maintenance: future**

There is no hosted model support, arbitrary ontology/assertion extraction, graph database, graph visualization, Command Center semantic-build workflow, manual curation, automatic scheduling, incremental update, deletion, retention, or garbage collection in this phase.
