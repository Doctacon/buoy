Status: done
Created: 2026-07-20
Updated: 2026-07-20

# Dynamic Content-Vector Dimensions

## Question and bounded conclusion

How could Buoy support a 768- or 3,584-dimensional **content** embedding without changing the independent 384-dimensional namespace-card routing projection, silently mixing incompatible namespaces, migrating existing namespaces by default, or weakening offline/resource controls?

The architecture is feasible only as a new, exact content-embedding contract. The safest candidate-independent shape is isolated new content namespaces, a versioned card/catalog contract, exact plan/apply/query compatibility checks, and no migration or default change. The routing card's semantic `vector` remains a normalized 384-dimensional float32 BGE vector; only content namespace rows and content query vectors vary.

This record does **not** select a model or architecture option, ratify behavior, supersede an active specification/decision, approve a download/load/inference/write, or make C4 executable. It ends with a confirm-or-correct checkpoint.

## Authority and observed current boundary

This shaping uses C2's immutable retained-model snapshot in `.10x/research/.storage/2026-07-19-code-aware-embedding-source-snapshot.json`, its reviewed research/evidence, current source at `72d1344fe344b444dcb6977f18aa461aa8fdb0e0`, and `uv.lock`.

Current source and active records establish:

- `src/buoy_search/chunker.py` uses one `VECTOR_DIMENSIONS = 384`, content schema `[384]f16`, `SentenceTransformer(model_name)` without revision/offline arguments, construct-then-`.half()`, and shared `normalize_embeddings=True`.
- `src/buoy_search/plan_artifacts.py` records model and precision but not immutable revision, dimension, role transforms, pooling, normalization, or contract hash. Its `embedding_text_hash` binds only text plus non-default precision, not model contract.
- `src/buoy_search/apply.py` previews `vector_dimensions=384`, uses the fixed content schema, and creates the content embedder from model/precision only.
- `src/buoy_search/catalog.py` uses `NamespaceCard.vector` as a separate normalized 384-dimensional float32 routing projection. It also sets and validates the card's `vector_dimensions` content-compatibility field from `ROUTING_DIMENSIONS`, which is the current conflation to remove.
- `src/buoy_search/remote_catalog.py` stores card projection `vector` as `[384]f32`; its `vector_dimensions` attribute is a scalar `uint`, but current card parsing requires exactly 384. Valid-but-nonmatching model/precision cards are incompatible/excluded; a non-384 serialized card is currently malformed/fatal before compatibility classification, as are corrupt cards/schema.
- `src/buoy_search/routing.py` embeds the routing query with pinned BGE and validates exactly 384 values. Its eligibility function includes a runtime content-dimension comparison, but current card parsing prevents a dynamic-dimension card from reaching that check. Content retrieval embeds the query once and reuses that vector across selected namespaces.
- Active `.10x/specs/namespace-routing-card-contract.md` requires content `vector_dimensions=384`; `.10x/specs/remote-turbopuffer-routing-catalog.md` fixes the routing vector schema at `[384]f32`; `.10x/specs/default-remote-namespace-routing.md` and `.10x/decisions/production-routing-remote-catalog.md` fix automatic authority at `buoy-routing-catalog-v1`. These active records must be explicitly updated or superseded after ratification; shaping cannot override them.
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

### Required resource checkpoint before any future download or load

A later candidate-specific, separately approved ticket must state:

1. exact immutable repository identity and listed bytes above;
2. the exact bootstrap file manifest/allowlist and forecast transfer/cache bytes (which may differ from all listed repository bytes);
3. cache root, existing-cache treatment, required free-disk bound, and abort behavior;
4. precision and construction strategy, including whether current construct-then-cast is retained or replaced by a locked-library-supported direct-dtype path;
5. supported CPU/CUDA/MPS hardware and software versions;
6. approved maximum construction peak host RSS, steady host RSS, peak/steady device allocation, elapsed load time, and batch size;
7. an observation method and immediate abort if any approved resource bound is reached.

Until a permitted load measures them, construction peak, steady host RAM, and peak/steady device memory remain blockers, not facts. C2's 2/24/48 GiB values are planning estimates only.

## Candidate-independent content contract

If ratified, every content namespace, plan, card, apply, and query must bind the same immutable contract:

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

The plan artifact and card must expose these values directly or expose a canonical contract ID/hash whose complete immutable expansion is reviewable. Model name plus dimension is insufficient. Contract fields must contribute to card revision, plan artifact hash/ID, and stored document embedding identity. Changing model, revision, prefix, pooling, normalization, precision, dimension, or distance metric must force a new namespace under the no-migration default; it must never be treated as an incremental update to old vectors.

The current `embedding_text_hash` must eventually bind the complete document-side contract, not merely text/precision, so a contract change cannot reuse stale rows.

## Card/catalog architecture options

| Option | Shape | Advantages | Costs/failure implications | Status |
| --- | --- | --- | --- | --- |
| A. Evolve `buoy-routing-catalog-v1` in place | Add self-contained content-contract fields and reinterpret `vector_dimensions` as content-only while keeping card `vector` at `[384]f32` | One catalog authority | Current exact schema/field readers reject missing/extra fields; existing cards require coordinated backfill/migration and old clients fail. Conflicts with no-migration default. | Unratified; stop unless migration and cutover are explicitly approved |
| B. Parallel versioned experimental catalog | Keep v1/default 384 behavior untouched; place only new dynamic experiment cards in a new versioned catalog contract with explicit content fields and fixed 384 routing vectors | Strong isolation, no existing card/content migration, reversible experiment boundary | Automatic routing needs an explicit experimental catalog/profile; cross-version routing is not automatic; a later production convergence decision remains | **Provisional safety recommendation**, not selected or active |
| C. Explicit namespace pilot without automatic catalog registration | New content namespaces only; operator supplies one exact content contract and bypasses automatic routing | Smallest initial control-plane change; leaves v1 untouched | Cannot honestly provide card-visible contract or automatic-routing compatibility by itself; explicit multi-namespace verification and preview semantics remain unresolved | Valid deferment/pilot containment option, not full dynamic-routing architecture |
| D. Stop/defer | Keep all production and experiments at 384; retain candidates as research only | Zero migration/resource/product risk | Code-aware candidate pilot remains blocked | Always available |

A future card v2 should make names unambiguous (for example, content fields prefixed `content_` and routing fields prefixed `routing_`) or provide an equally explicit nested canonical representation. Exact serialization remains a ratification question; this record does not create that schema.

## Namespace, plan, apply, and routing behavior matrix

| Surface | Proposed compatibility rule | Required failure behavior |
| --- | --- | --- |
| New content namespace | Physical metadata vector type must equal the plan's exact `[D]f16` content schema and cosine distance contract. Namespace identity is dedicated to one contract for its lifetime. | Wrong/existing dimension, model-contract reuse, or unknown metadata: fail before embedding or write; never resize, delete, or overwrite. |
| Existing 384 namespace | Remains under current model/schema/card/default. No re-embedding, schema mutation, card migration, or default change. | Any dynamic plan targeting it fails as incompatible. |
| Plan/card | Both carry the same canonical content contract/hash. Card routing projection remains exact 384 BGE. | Missing/unknown/malformed contract is fatal. A valid card for another selected content contract is incompatible/excluded, not coerced. |
| Apply preview | Reports model@revision, content dimension/schema, role transforms, pooling, normalization, listed/cache bytes, cache readiness, resource unknowns, exact new namespace, rows/writes, and zero-delete/default/catalog-v1 change. It remains credential/model/API-free. | Any unknown exact namespace/rows/cache/resource/write bound stops before approval request. |
| Approved apply | After explicit approval, require exact local cache and offline environment, validate locked dependency/no-remote-code path, validate advertised model dimension before remote work where possible, read remote metadata/card strongly, then validate every produced vector length/finite values before its write batch. | Missing cache, attempted network, dependency mismatch, resource bound, output mismatch, remote schema/card mismatch, or namespace existence conflict stops with zero content writes at the earliest observable point. No fallback model/revision. |
| Explicit retrieval | One query may target only namespaces with the exact same content contract. Query transform is selected from that contract. | Mixed model/revision/dimension/prefix/pooling/normalization/precision groups fail before model load/content query. No per-namespace silent re-embedding. |
| Automatic routing | Routing query and card vectors remain 384. Before relevance, choose one explicit content-contract group; only cards with that exact group are eligible. Embed the content query once with that group's query role, then query selected namespaces. | Default v1 continues excluding dynamic cards. Multiple/unselected contract groups, zero eligible cards, malformed cards, output dimension mismatch, or selected metadata mismatch fail closed; never fan out across groups or fall back to namespace IDs/all live namespaces. |
| Card registration/recovery | Pending/base/revision hashes bind the complete content contract. Manual semantics/enabled state may be preserved only when content and routing contracts remain exact. | Content-contract drift is a system-field conflict: no safe rebase and no content replay. |

### Why automatic routing must group before relevance

The 384-dimensional routing projection can compare cards from different content models, but downstream retrieval cannot safely share one content query vector across 384-, 768-, and 3,584-dimensional namespaces. Buoy currently embeds the content query once. Therefore an explicit content contract must be selected before route eligibility; routing first and discovering mixed dimensions afterward is unsafe.

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
- apply preview, approved preflight ordering, remote metadata verification, vector-length checks, and pending recovery fields;
- card serialization/hash/parser and likely a versioned remote catalog schema/authority;
- automatic eligibility grouping and explicit multi-namespace compatibility;
- CLI/config selection semantics and output;
- focused wrong-dimension, mixed-contract, missing-cache, network-denial, prefix, pooling/normalization, old-client/card-version, and zero-write failure tests.

No new dependency is currently justified: immutable metadata indicates the locked open-source SentenceTransformer/Transformers/Torch/Hub path contains both architectures and required offline controls. This is not runtime proof. Stop rather than changing dependencies if a permitted compatibility check shows either candidate needs remote code, a lock update, unsupported dtype/device plumbing, or network access; any dependency/lock change requires separate research, approval, and ticket scope.

## Stop conditions before implementation or evaluation

Stop with no active spec/ticket/download/load/write if any of the following remains unresolved:

1. candidate or defer choice;
2. v1 migration vs parallel v2 vs explicit-only control-plane option;
3. exact self-contained card/plan serialization and public selection surface;
4. exact immutable content contract, including prefixes/pooling/normalization/truncation/distance;
5. exact new namespaces, rows, writes, storage, cache manifest, and resource limits;
6. construct/load precision strategy and supported hardware;
7. measured construction peak, steady host RAM, and peak/steady device memory are required but not approved/available;
8. locked dependency compatibility/no-remote-code/offline-network behavior fails;
9. any proposal changes existing namespaces/cards/defaults or requires migration without explicit supersession/approval;
10. active v1 specs/decision have not been updated or superseded for the chosen bounded behavior;
11. independent review of this shaping output has not passed.

C4 remains blocked because its exact 384-dimensional candidate condition was not met. Dynamic behavior must receive its own focused active specifications and bounded executable tickets after ratification; this record does not widen C4.

## User-legible confirm-or-correct checkpoint

No model or behavior is selected yet. Please confirm or correct these independent choices:

1. **Candidate:** (A) Crow-Plus at 768 for the smaller first experiment, (B) Nomic at 3,584 only after accepting its much larger resource/loading checkpoint, or (C) defer dynamic dimensions. Decision unlocked: exact model contract and resource/bootstrap forecast.
2. **Isolation/control plane:** (A) parallel versioned experimental cards/catalog with v1/defaults untouched (**provisional safety recommendation**), (B) explicit-namespace-only pilot with automatic dynamic routing deferred, or (C) approve shaping a coordinated v1 card migration. Decision unlocked: focused card/routing specifications.
3. **Namespace policy:** confirm new namespaces only, no migration or mutation of existing 384 namespaces/cards/defaults, no deletes, and exact-contract rejection rather than conversion. Decision unlocked: plan/apply safety contract.
4. **Offline/resource gate:** confirm bootstrap and model load are separately approved phases; runtime is pinned-cache-only/network-failing/telemetry-disabled; unmeasured construction/steady host/device RAM blocks load approval until exact abort bounds and observation method are stated. Decision unlocked: bounded verification ticket, but not a download or load by this confirmation alone.

After those answers, the next Outer Loop action is to draft focused **inactive until ratified** behavior contracts for the selected content model/loading surface, versioned card/routing compatibility, and isolated plan/apply lifecycle. No executable implementation/evaluation ticket should exist until those specifications are active and exact resource/write approvals are separately available.

## Safety and limits

No model/dependency was downloaded or installed; no model was loaded; no inference ran; no credentials were read; no Buoy runtime, Hugging Face model, or Turbopuffer service was called or written; no namespace/card/catalog/default was read from or written to a live service; and no source, tests, dependencies, configuration, or lockfile changed. The only external mutation was the task-required Git push and record-only pull request.

Model-card quality claims were not reproduced. Runtime/package compatibility and all construction/steady host/device measurements remain unverified. Exact listed repository bytes do not equal an exact future transfer, allocated cache footprint, runtime RSS, device allocation, or provider storage/billing bound.
