Status: active
Created: 2026-07-20
Updated: 2026-07-20

# Crow-Plus Explicit-Namespace Pilot

## Active status and ratified direction

The user ratified Crow-Plus at 768 dimensions as the first dynamic content-vector candidate; an explicit-namespace-only pilot with no namespace cards, catalog participation, or automatic routing; complete local staging and validation of every vector before the first remote content write; and five independent approvals in order for specification, bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write. No phase approval or success implies the next.

The user separately ratified the exact resource-verification checkpoint in `.10x/specs/crow-plus-resource-verification-checkpoint.md` and activated both focused specifications as phase 1 only after independent review passed. Phase 1 authorizes these behavior records only. It does not authorize implementation, evaluation, model bootstrap/download/load/inference, or remote work. Each later phase remains blocked until separately approved.

## Purpose and scope

Define an isolated first pilot for `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` using 768-dimensional normalized content vectors in exact new namespaces. The pilot evaluates content retrieval only. Existing 384-dimensional namespaces, cards, catalog authority, automatic routing, defaults, and ordinary apply behavior remain unchanged.

## Exact content contract

The pilot MUST bind all of these values in plans, staged artifacts, namespace identity, queries, and evidence:

- repository/revision: `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af`;
- license and runtime path: Apache-2.0, locked SentenceTransformer/Transformers/Torch path, remote code prohibited;
- output: one 768-dimensional vector;
- query prefix: empty string;
- document prefix: empty string;
- pooling: CLS token;
- normalization: Buoy requests normalized output; every staged vector is verified as normalized;
- maximum input: 1,024 tokens under an exact truncation policy that must be present in the approved plan;
- stored scalar/schema/distance: `[768]f16` with cosine distance;
- canonical contract hash over every field above plus inference precision and loading strategy.

A model/revision/dimension/prefix/pooling/normalization/precision/distance change MUST produce a different contract hash and a different new namespace. No conversion, projection, truncation, padding, or reuse of old vectors is permitted.

The bounded measurement MUST use only the exact literal query and code/document inputs defined and hashed in `.10x/specs/crow-plus-resource-verification-checkpoint.md`. It MUST encode them sequentially as two separate batch-1 calls and receive two separate `[1,768]` outputs. Token IDs are recorded only after the pinned tokenizer is bootstrapped; neither input may be changed or truncated.

## Explicit namespace only

- Every pilot query and write MUST name one exact, separately approved new content namespace.
- No pilot operation may generate, register, update, reconcile, enable, disable, read for routing, or write a namespace card.
- No pilot operation may read or write `buoy-routing-catalog-v1`, create another catalog, alter catalog authority, or participate in automatic routing.
- Retrieval MUST use the explicit namespace and exact Crow-Plus content contract. Multi-namespace retrieval and automatic namespace selection are excluded.
- Existing 384-dimensional namespaces, rows, cards, defaults, and applied state MUST NOT be mutated, migrated, re-embedded, deleted, or used as a dynamic target.

## Separate staged experimental path

The pilot MUST use a dedicated experimental stage-then-write path, selected only by an exact experimental plan/contract and the separately approved indexing/write operation. It MUST NOT reuse the active depth-one encode/write pipeline for its remote phase and MUST NOT change that pipeline's default or fallback behavior.

This is a governed experimental exception to `.10x/specs/depth-one-approved-apply-pipeline.md`, not a weakening or supersession of it:

1. acquire the namespace-scoped safety boundary;
2. load only the already-bootstrapped immutable model under the approved bounded-resource contract;
3. encode **all** approved rows without any remote client, credential lookup, content read, or content write;
4. persist one local staged artifact binding plan ID/hash, exact namespace, content-contract hash, source/chunk identities, row IDs, every vector, vector hashes, counts, precision, resource observations, and output-validation results;
5. validate the complete artifact before credentials or a remote client exist;
6. stop and unload; measurement/staging success grants no write authority;
7. only after a separate indexing/write approval, revalidate the immutable staged artifact and exact remote target, then perform ordered serial content upserts without embedding overlap.

The ordinary active pipeline continues to overlap preparation of N+1 with write N. It remains the current default for ordinary approved apply and is untouched by this pilot. The experimental path intentionally performs zero remote content writes until every vector is staged and validated.

## Complete-stage gate before first remote content write

Before the first remote content write, the staged artifact MUST prove:

- exact approved plan/artifact/namespace/content-contract identities;
- exact approved row count, row IDs, write count, storage forecast, and zero deletes;
- one and only one vector per approved row;
- every vector has exactly 768 finite numeric values;
- every vector has L2 norm in the ratified compliance interval;
- deterministic vector hashes and an artifact hash cover all vectors and identities;
- observed construction/load/staging host, device, elapsed-time, and batch values stayed within the ratified resource checkpoint;
- the model was loaded from the exact dedicated cache with offline/network-failing/telemetry-disabled controls and no remote code;
- no card, catalog, default, existing namespace, stale row, or applied state is in the mutation set.

Any missing, duplicate, non-finite, wrong-dimension, out-of-norm, hash-mismatched, resource-noncompliant, or identity-drifted result invalidates the whole staged artifact. Partial-vector success MUST NOT permit a write.

## Approval boundaries

Five phases require five independent, non-transitive approvals in this fixed order. Approval or success of one phase authorizes only that phase and does not authorize, approve, or imply the next:

1. **Specification approval** may activate the behavior contracts only; it authorizes no executable ticket or operation.
2. **Bootstrap/download approval** authorizes only the exact immutable files, bytes, dedicated cache root, and disk bounds in the approved checkpoint. It authorizes no model construction, inference, source/test change, or remote operation.
3. **Bounded measurement load approval** authorizes only the exact cached model load and two literal-input inference observations stated in the checkpoint. It authorizes no implementation/source change, staging, indexing, or remote operation.
4. **Implementation/source changes approval** authorizes only the bounded implementation, test changes, and local plan/staging evidence named in its later executable ticket. It authorizes no remote client operation, namespace creation, indexing, or write.
5. **Indexing/write approval** may be requested only after implementation, tests, review, and exact local plan/staging evidence exist. It must name exact namespaces, rows, writes, storage, staged-artifact hash, and zero deletes.

A failed phase stops progression. A successful phase merely makes the next approval request eligible; it never grants that approval.

## Failure and recovery

- Missing cache, network attempt, remote-code request, dependency drift, resource-bound contact, output mismatch, stage/hash mismatch, namespace existence/schema conflict, or approval mismatch MUST fail closed.
- A stage failure performs zero remote operations and produces no write-eligible artifact.
- A write failure may leave only the successfully upserted prefix remotely. It MUST stop later writes, perform no delete/catalog/default mutation, and record exact affected IDs. Resumption or replay requires a new exact approval against the immutable staged artifact and strong remote verification; it is not automatic.
- Local staging data MUST NOT be treated as applied state or retrieval authority.

## Acceptance scenarios

### Complete staging before write

Given an approved plan with N rows, when one vector fails dimension or norm validation, then no credential is read, no remote client is created, and zero rows are written.

### Depth-one isolation

Given the ordinary depth-one pipeline remains active, when a Crow-Plus experimental plan runs, then all N vectors are staged and validated before write 1; when an ordinary plan runs, its existing depth-one behavior is unchanged.

### Explicit-only retrieval

Given a valid Crow-Plus pilot namespace, when retrieval is requested without its exact namespace and content contract, then it fails rather than consulting a card/catalog or automatically routing.

## Explicit exclusions

Cards; any catalog; automatic or multi-namespace routing; production/default promotion; existing namespace changes; migration; deletes; concurrent writes; encode/write overlap; retries; automatic resume; dependency or lockfile changes; Nomic; and any operation before its separate approval.
