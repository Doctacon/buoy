Status: done
Created: 2026-07-20
Updated: 2026-07-20

# Dynamic Content-Vector Dimensions

## Question and bounded conclusion

How could Buoy support a 768- or 3,584-dimensional **content** embedding without changing the independent 384-dimensional namespace-card routing projection, silently mixing incompatible namespaces, migrating existing namespaces by default, or weakening offline/resource controls?

The user ratified Crow-Plus at 768 dimensions as the first candidate, contained in an explicit-namespace-only pilot with no cards, catalog participation, or automatic routing. Every vector plus resource/output compliance must be staged and validated before the first remote content write. Five phases require five independent approvals in this fixed order: specification, bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write. Approval or success of one phase does not authorize, approve, or imply the next.

This selection does not supersede the active 384-dimensional default pipeline or C4's stop. Phase 1 ratification approves no bootstrap/download, load/inference, source/test change, or remote operation. The exact resource thresholds and focused behavior contracts are now active exactly as independently reviewed; each later operation remains separately approval-gated.

## Authority and observed current boundary

This shaping uses C2's immutable retained-model snapshot in `.10x/research/.storage/2026-07-19-code-aware-embedding-source-snapshot.json`, its reviewed research/evidence, current source at `72d1344fe344b444dcb6977f18aa461aa8fdb0e0`, and `uv.lock`.

Current source and active records establish:

- `src/buoy_search/chunker.py` uses one `VECTOR_DIMENSIONS = 384`, content schema `[384]f16`, `SentenceTransformer(model_name)` without revision/offline arguments, construct-then-`.half()`, and shared `normalize_embeddings=True`.
- `src/buoy_search/plan_artifacts.py` records model and precision but not immutable revision, dimension, role transforms, pooling, normalization, or contract hash. Its `embedding_text_hash` binds only text plus non-default precision, not model contract.
- `src/buoy_search/apply.py` previews `vector_dimensions=384`, uses the fixed content schema, and creates the content embedder from model/precision only.
- `src/buoy_search/catalog.py` uses `NamespaceCard.vector` as a separate normalized 384-dimensional float32 routing projection. It also sets and validates the card's `vector_dimensions` content-compatibility field from `ROUTING_DIMENSIONS`, which is the current conflation to remove.
- `src/buoy_search/remote_catalog.py` stores card projection `vector` as `[384]f32`; its `vector_dimensions` attribute is a scalar `uint`, but current card parsing requires exactly 384. Valid-but-nonmatching model/precision cards are incompatible/excluded; a non-384 serialized card is currently malformed/fatal before compatibility classification, as are corrupt cards/schema.
- `src/buoy_search/routing.py` embeds the routing query with pinned BGE and validates exactly 384 values. Its eligibility function includes a runtime content-dimension comparison, but current card parsing prevents a dynamic-dimension card from reaching that check. Content retrieval embeds the query once and reuses that vector across selected namespaces.
- Active `.10x/specs/namespace-routing-card-contract.md` requires content `vector_dimensions=384`; `.10x/specs/remote-turbopuffer-routing-catalog.md` fixes the routing vector schema at `[384]f32`; `.10x/specs/default-remote-namespace-routing.md` and `.10x/decisions/production-routing-remote-catalog.md` fix automatic authority at `buoy-routing-catalog-v1`. The explicit-only pilot leaves these active records unchanged and operates outside cards/catalog/automatic routing.
- `uv.lock` resolves the existing open-source path: `sentence-transformers==5.6.0`, `transformers==5.12.1`, `torch==2.12.1`, and `huggingface-hub==1.20.1`. C2 metadata found both candidates use built-in modules/architectures and no remote code, but runtime compatibility is unverified because no model was loaded.

## Non-negotiable separation

| Concern | Content retrieval vector | Catalog-routing vector |
| --- | --- | --- |
| Purpose | ANN query/upsert in one content namespace | Rank namespace semantic cards before content retrieval |
| Dimension | Exactly the chosen content contract: current 384, candidate 768, or candidate 3,584 | Always 384 under the current pinned routing contract |
| Storage | Content namespace `vector`, currently f16 | `NamespaceCard.vector` / reserved catalog `vector`, f32 |
| Model | Namespace-specific exact content model/revision | `BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` |
| Query transform | Model-specific; Nomic has a query-only prefix | Existing BGE routing prefix `Represent this sentence for searching relevant passages: ` |
| Compatibility | Exact content contract match before model load/query/write | Fixed routing contract validation independent of content dimension |

No code may derive content dimension from `ROUTING_DIMENSIONS`, infer content semantics from the length of the routing vector, or resize/project either vector to fit the other.

## Candidate compatibility and resource decision matrix

All byte values below are copied from C2's immutable tree snapshot. GB/GiB conversions are arithmetic presentations of those bytes, not new measurements.

| Decision factor | Crow-Plus candidate | Nomic candidate |
| --- | --- | --- |
| Exact identity | `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` | `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52` |
| License/path | Apache-2.0; standard SentenceTransformer modules; no remote code observed | Apache-2.0; standard SentenceTransformer modules; no remote code observed |
| Content dimension | 768 | 3,584 |
| Max input | 1,024 tokens | 32,768 tokens |
| Query/document roles | No prefix / no prefix | Query prefix exactly `Represent this query for searching relevant code: ` / no document prefix |
| Pooling | Single CLS token | Last token, with prompt included |
| Normalization | No Normalize module; Buoy must request and record normalized output | Normalize module present; contract still records normalized output and must prevent double role-prefix application |
| Exact listed weight bytes | `606,681,112` (0.606681112 GB / 0.565015815 GiB) | `28,282,512,976` (28.282512976 GB / 26.340142801 GiB) |
| Exact total listed repository bytes | `611,525,163` (0.611525163 GB / 0.569527189 GiB) | `28,298,426,837` (28.298426837 GB / 26.354963739 GiB) |
| Exact raw f16 bytes per stored vector | `1,536` | `7,168` |
| Relative raw f16 payload vs current 384 | 2x | 9.333x |
| Current construction implication | Float32 construction needs more than 0.565 GiB weight bytes plus unmeasured runtime overhead before any `.half()` | Float32 construction needs more than 26.340 GiB weight bytes plus unmeasured runtime overhead before any `.half()` |
| C2 analytical planning figures, **not measurements or approved bounds** | At least 2 GiB available host RAM; if accelerated, 2 GiB device memory | 48 GiB host planning estimate for current construct-then-cast; 24 GiB accelerator estimate only after separately authorized direct-half/loading plumbing |
| Known implementation delta | Dynamic schema/contract plus pinned local loading; no prefix plumbing | Same, plus query-only role plumbing and likely direct-dtype/loading work before a bounded load is credible |
| Primary tradeoff | Much smaller download/cache/memory and implementation-risk checkpoint; shorter maximum input | Much larger context and retained primary research status, but about 46.3x listed repository bytes and materially higher host/device risk |

For comparison, current raw `[384]f16` vector payload is exactly 768 bytes; `[768]f16` is 1,536 bytes; `[3584]f16` is 7,168 bytes. These are raw element bytes only. Turbopuffer ANN/storage overhead, row encoding, replication, billing, cache filesystem allocation, tokenizer files in active use, activations, allocator fragmentation, batch effects, construction peak, steady host RSS, and steady/peak device memory are **unmeasured**.

### Exact ratified resource checkpoint before any future download or load

Read-only host inspection observed an Apple `Mac14,9` with M2 Pro, 17,179,869,184 bytes unified memory, macOS 26.5.1 (`25F80`), and 34,890,539,008 bytes available disk. `.10x/specs/crow-plus-resource-verification-checkpoint.md` proposes one exact host-specific checkpoint:

- bootstrap the complete immutable 611,525,163-byte Crow-Plus tree into one absent dedicated cache root, with a 611,525,163-byte transfer ceiling, 805,306,368-byte allocated-cache ceiling, and 5-GiB start/4-GiB post-bootstrap disk floors;
- measure only on that exact M2 Pro/MPS host and locked dependencies, constructing float32 then casting to float16, with exactly two sequential batch-1 calls: the 51-byte UTF-8 query `Where does Buoy validate content vector dimensions?` with no final newline (SHA-256 `4f51d3b93aea75b1f2f58ae55eda6a74b112bb2d1e236549569d64132379d8cc`), then the 129-byte UTF-8 LF-terminated code/document fixed in the checkpoint (SHA-256 `a89366d7ffbd3e7816a58e297ebc2605d24dd4c98ae0f92627fc0c6cf2981260`); pinned tokenizer IDs/counts are recorded after bootstrap and both literals must fit within 1,024 tokens without truncation;
- require a separate `[1,768]`, all-finite, L2 norm `[0.999, 1.001]` output from each call; a combined batch/output is prohibited;
- start with at least 8 GiB available memory; hard-abort at 4 GiB child RSS, 2 GiB MPS current allocation, 3 GiB MPS driver allocation, 120 seconds load, or 300 seconds total;
- sample external RSS/time and in-process MPS counters at most every 100 ms and fail on a sample gap over 200 ms; qualification additionally requires 3 GiB RSS, 1.5 GiB MPS-current, 2.25 GiB MPS-driver, 90-second load, and 225-second total ceilings.

These exact values are ratified as the phase 1 contract, not as authority for an operation. They resolve the prior circularity: phase 2 bootstrap/download requires its own approval; phase 2 does not authorize phase 3 bounded measurement load; passing phase 3 does not authorize phase 4 implementation/source changes; and phase 4 does not authorize phase 5 indexing/write. Until a permitted measurement, construction peak, steady host RAM, and peak/steady device memory remain unknown blockers, not facts. C2's 2/24/48 GiB values remain analytical planning estimates only.

## Candidate-independent content contract

For the ratified explicit-only pilot, every content namespace, plan, staged artifact, write approval, and query must bind the same immutable contract:

- model repository ID and immutable revision;
- output dimensions;
- inference precision and stored vector scalar type;
- exact query prefix and exact document prefix, including empty strings;
- pooling semantics;
- normalization boolean and where normalization occurs;
- distance metric;
- maximum input and the chunk/query truncation policy;
- no-remote-code requirement;
- canonical contract hash/version.

The plan and staged artifact must expose these values directly or expose a canonical contract ID/hash whose complete immutable expansion is reviewable. Model name plus dimension is insufficient. Contract fields must contribute to the plan artifact hash/ID, staged-artifact/vector hashes, and stored document embedding identity. Changing model, revision, prefix, pooling, normalization, precision, dimension, or distance metric must force a new namespace under the no-migration default; it must never be treated as an incremental update to old vectors.

The current `embedding_text_hash` must eventually bind the complete document-side contract, not merely text/precision, so a contract change cannot reuse stale rows.

## Ratified control-plane containment

The first pilot is explicit-namespace-only. It creates no card, uses no existing or new catalog, performs no catalog registration/reconciliation, and cannot participate in automatic or multi-namespace routing. The operator supplies one exact new namespace and Crow-Plus content contract. Existing `buoy-routing-catalog-v1`, its 384-dimensional routing projection, authority, cards, and defaults remain untouched.

The previous in-place-v1 and parallel-v2 options are rejected for this pilot. A future card/catalog architecture would require new shaping and ratification; this work does not draft it.

## Namespace, plan, apply, and routing behavior matrix

| Surface | Proposed compatibility rule | Required failure behavior |
| --- | --- | --- |
| New content namespace | Physical metadata vector type must equal the plan's exact `[D]f16` content schema and cosine distance contract. Namespace identity is dedicated to one contract for its lifetime. | Wrong/existing dimension, model-contract reuse, or unknown metadata: fail before embedding or write; never resize, delete, or overwrite. |
| Existing 384 namespace | Remains under current model/schema/card/default. No re-embedding, schema mutation, card migration, or default change. | Any dynamic plan targeting it fails as incompatible. |
| Plan | Carries the complete canonical Crow-Plus content contract/hash and exact explicit new namespace. | Missing/unknown/malformed contract, namespace, rows, or write forecast is fatal. |
| Apply preview | Reports model@revision, content dimension/schema, role transforms, pooling, normalization, listed/cache bytes, cache readiness, resource unknowns, exact new namespace, rows/writes, and zero-delete/default/card/catalog change. It remains credential/model/API-free. | Any unknown exact namespace/rows/cache/resource/write bound stops before approval request. |
| Experimental staging | Uses an already-approved cached model to encode every approved row locally, records all vectors/resource observations/output checks in one hash-bound artifact, and creates no remote client. | Any missing/duplicate/non-finite/wrong-dimension/out-of-norm vector, resource violation, or identity drift invalidates the whole artifact with zero remote content writes. |
| Experimental write | After a separate indexing/write approval, revalidates the complete staged artifact and exact remote target, then serially writes its ordered batches without embedding overlap. | Missing approval, artifact drift, remote schema/namespace conflict, or unexpected affected IDs stops later writes; no delete/card/catalog/default mutation. |
| Explicit retrieval | One query targets one exact namespace with the exact Crow-Plus content contract. | Missing namespace, mixed contract, or output mismatch fails before content query; no card/catalog lookup or fallback. |
| Cards/catalog/automatic routing | Excluded from the pilot; active v1 behavior remains untouched. | Any attempt to register, reconcile, route, or fall back through a catalog is fatal. |

### Depth-one apply conflict resolution

The active `.10x/specs/depth-one-approved-apply-pipeline.md` remains the ordinary default and is not weakened or superseded. The pilot requires a separate governed experimental stage-then-write path: all vectors are encoded, persisted, hash-bound, and resource/output validated before credential lookup or the first remote content write. Its later approved write phase performs no embedding overlap. Selection requires the exact experimental plan/contract plus per-run write approval; ordinary plans continue on the current depth-one pipeline.

## Isolation and migration policy options

The default proposed policy is **new namespace, no migration**:

- every 768/3,584 experiment uses exact, newly approved namespace IDs;
- existing 384 namespaces, cards, defaults, state, and rows remain untouched;
- no stale-row deletes or namespace deletes;
- no dimension change in place and no mixed-model rows;
- no automatic default change or candidate promotion;
- a paired 384 baseline, if later approved, also uses a new namespace when experiment comparability requires it;
- exact namespace names/row counts/writes/storage require plan evidence and separate approval.

Migration is unnecessary for a bounded experiment. A later production decision might choose parallel generations, explicit re-index into new namespaces followed by separately approved cutover, or no adoption. It must never mutate an existing vector schema or claim that copying/reinterpreting old vectors changes their dimension/model semantics.

## Revision-pinned offline bootstrap/load contract

Bootstrap and runtime are separate phases.

### Bootstrap (future network-enabled operation; separately approved)

- Use locked `huggingface-hub` snapshot semantics with exact `repo_id`, immutable `revision`, explicit `cache_dir`, and public/no-credential mode (`token=False` or locked equivalent).
- Forecast and approve bytes/free disk first; store a manifest of returned commit snapshot, allowed files, exact observed file sizes, and cache root. Abort on revision/path/file/size drift or insufficient disk.
- Do not install or update dependencies as part of model bootstrap. Do not use mutable branches/tags, remote code, or a default global-cache fallback.
- Bootstrap success authorizes only cache population, not model construction or inference.

### Runtime after bootstrap

Before importing Hub/Transformers/SentenceTransformer in a fresh process, set at least:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
HF_HUB_DISABLE_TELEMETRY=1
DO_NOT_TRACK=1
HF_HUB_DISABLE_UPDATE_CHECK=1
```

Construct with exact model ID, revision, explicit cache root, `local_files_only=True`, and remote code disabled. The locked Hub source treats offline mode as HTTP-failing and exposes telemetry/update-check controls; these environment values must be set before import because package constants are initialized at import time.

A future test must deny/patch network access and prove: cached exact revision loads through the approved path; missing cache fails clearly; no alternate revision/download/credential is attempted; telemetry/update checks are disabled. Runtime compatibility still requires a separately approved load because C2 performed metadata inspection only.

## Model-specific role semantics

| Candidate | Content query input | Content document input | Pooling | Output normalization |
| --- | --- | --- | --- | --- |
| Crow-Plus | Raw query; no prefix | Existing document embedding text; no prefix | CLS token | Explicit normalized output required from Buoy because the repository has no Normalize module |
| Nomic | Exact prefix `Represent this query for searching relevant code: ` followed by raw query | Existing document embedding text with no prefix | Last token; prompt included | Repository Normalize module; card/plan still declare `normalized=true` and implementation must avoid double-prefixing |

The separate routing query always keeps its existing BGE routing prefix. A content query must receive exactly one model-specific query transform after content-contract selection. Document hashing must bind the document transform even when the prefix is empty.

## Implementation and dependency implications (not authorization)

A future ratified implementation would at minimum touch the following contracts, with tests before any live operation:

- content schema construction and vector validation in `chunker.py`/`plan_artifacts.py`;
- revision/local-cache/offline/role-aware model construction and encoding;
- plan schema/version, artifact hash, and embedding identity;
- apply preview, experimental complete-vector staging, staged-artifact hashing, resource/output compliance, approved serial write ordering, and remote metadata verification;
- an explicit experimental selector that cannot enter card/catalog/automatic-routing code and cannot change the ordinary depth-one default;
- exact explicit-namespace query compatibility;
- focused wrong-dimension, mixed-contract, missing-cache, network-denial, prefix, pooling/normalization, resource abort, complete-stage-before-write, default-pipeline isolation, and zero-write failure tests.

No new dependency is currently justified: immutable metadata indicates the locked open-source SentenceTransformer/Transformers/Torch/Hub path contains both architectures and required offline controls. This is not runtime proof. Stop rather than changing dependencies if a permitted compatibility check shows either candidate needs remote code, a lock update, unsupported dtype/device plumbing, or network access; any dependency/lock change requires separate research, approval, and ticket scope.

## Stop conditions before implementation or evaluation

The pilot specifications are active, but stop with no executable operation beyond the separately approved phase if any of the following remains unresolved:

1. phase 2 bootstrap/download approval and exact immutable manifest evidence;
2. phase 3 bounded-measurement-load approval and passing measured resource/output evidence;
3. phase 4 implementation/source-changes approval and a bounded executable implementation ticket;
4. phase 5 indexing/write approval naming exact new namespaces, rows, writes, storage, and staged-artifact identity;
5. locked dependency compatibility/no-remote-code/offline-network behavior fails;
6. any proposal changes existing namespaces/cards/catalog/defaults, invokes automatic routing, or requires migration.

The five approvals are independent and non-transitive in that order. No phase approval or success implies the next.

C4 remains blocked because its exact 384-dimensional candidate condition was not met. This selected dynamic pilot uses a separate contract and MUST NOT widen or execute C4.

## Phase 1 resolution

The user ratified the candidate, explicit-only containment, complete staging-before-write rule, five independent phase boundaries, and exact resource checkpoint in `.10x/specs/crow-plus-resource-verification-checkpoint.md`: dedicated empty cache; immutable 611,525,163-byte tree; 611,525,163-byte transfer and 768-MiB cache ceilings; 5-GiB/4-GiB disk floors; observed M2 Pro/MPS host; float32 construction then float16 inference; two sequential batch-1 calls using the exact 51-byte query (`4f51d3b9…d8cc`) then exact 129-byte LF-terminated code/document (`a89366d7…1260`), with separate `[1,768]` finite normalized outputs; 120-second load/300-second total hard deadlines; 4-GiB RSS/2-GiB MPS-current/3-GiB MPS-driver hard ceilings; 100-ms monitoring; tighter 75%-of-bound qualification values; and immediate abort.

Both focused specifications are active exactly as independently reviewed. Phase 1 activates records only. Phases 2–5—bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write—each require their own later approval, and no phase implies the next. The blocked phase 2 owner is `.10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md`.

## Safety and limits

No model/dependency was downloaded or installed; no model was loaded; no inference ran; no credentials were read; no Buoy runtime, Hugging Face model, or Turbopuffer service was called or written; no namespace/card/catalog/default was read from or written to a live service; and no source, tests, dependencies, configuration, or lockfile changed. The only external mutation was the task-required Git push and record-only pull request.

Model-card quality claims were not reproduced. Runtime/package compatibility and all construction/steady host/device measurements remain unverified. Exact listed repository bytes do not equal an exact future transfer, allocated cache footprint, runtime RSS, device allocation, or provider storage/billing bound.
