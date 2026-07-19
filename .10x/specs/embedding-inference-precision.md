Status: active
Created: 2026-07-13
Updated: 2026-07-19

# Embedding Inference Precision

## Purpose and scope

Add an explicit, opt-in float16 inference profile for the existing `BAAI/bge-small-en-v1.5` Sentence Transformers path while preserving float32 compatibility. Precision applies to both corpus and query embedding and is observable in plan/live outputs.

## Behavior

- Supported precision values MUST be `float32` and `float16`.
- `float32` MUST remain the default for all existing commands, environments, plans, and namespaces.
- `plan --embedding-precision <value>` MUST record the selected value in `plan.json`, include it in artifact integrity, and expose it in plan output. Planning remains local-only and MUST NOT load the model.
- `apply` MUST derive precision from the verified plan; it MUST NOT silently override the plan from ambient environment configuration.
- Plans created before this field existed MUST remain valid and MUST be interpreted as `float32` without changing their existing artifact hash.
- A precision change for an existing namespace MUST make affected rows eligible for re-embedding/upsert rather than appear unchanged. The implementation MUST preserve existing deterministic row IDs.
- Live `retrieve`, live evals, and autoresearch/eval runtime configuration MUST accept `--embedding-precision` and `BUOY_EMBEDDING_PRECISION`. Their default remains `float32`. Through Buoy 0.3, `TURBO_SEARCH_EMBEDDING_PRECISION` follows the deprecated environment fallback/conflict rules in `.10x/specs/buoy-local-compatibility.md`; starting in 0.4.0, actual commands reject its presence under `.10x/specs/buoy-v0-4-environment-alias-removal.md`.
- Retrieval/eval dry-run and result summaries MUST expose the configured precision so an operator can verify it matches the namespace's plan. The CLI cannot infer remote namespace precision and MUST document that explicit responsibility.
- `float16` MUST use the existing local PyTorch Sentence Transformer model in half precision on an accelerator. If the selected runtime device does not support the approved float16 path, the command MUST fail before encoding with a user-friendly message; it MUST NOT silently fall back to float32.
- Embedding vectors returned to Turbopuffer and query construction MUST retain the existing list-of-floats interface, dimensions, normalization, schema, and model identity.

## Compatibility and integrity

- Existing schema-version-1 plan artifacts without `embedding_precision` MUST continue to verify as float32.
- New plans MUST bind precision into artifact integrity.
- Approved apply summaries and throughput timing MUST report effective precision.
- Existing float32 state MUST not be silently relabeled as float16.
- Changing precision MUST NOT change crawl, chunk, row-ID, namespace, deletion, locking, state-commit, write ordering, retry, or model-selection behavior.

## Verification

- Unit tests MUST cover defaults, CLI/environment overrides, old-plan compatibility, artifact tamper detection, precision-driven re-upsert, apply deriving precision from plan, query embedding precision, and unsupported-device failure.
- A local no-write parity benchmark MUST compare normalized float32 and float16 embeddings over representative real chunks. Acceptance requires minimum cosine similarity at least 0.999 and exact top-10 cosine-neighbor identity for a documented query sample, plus measured throughput.
- Existing retrieval tests and the full suite MUST pass.

## Dependencies

Implementation depends on `.10x/tickets/done/2026-07-14-buoy-release-integration-validation.md` and MUST target the `buoy_search` package and `buoy` CLI after that rebrand integrates.

## Explicit exclusions

- Making float16 the default.
- Live Turbopuffer writes or live retrieval/eval execution.
- A new benchmark namespace.
- ONNX, CoreML, MLX, OpenVINO, quantization, model replacement, chunk-size changes, concurrency, or retries.
