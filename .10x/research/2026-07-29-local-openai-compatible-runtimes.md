Status: done
Created: 2026-07-29
Updated: 2026-07-29

# Local OpenAI-Compatible Runtimes

## Question

What current, officially documented Ollama and llama.cpp behavior can Buoy safely rely on for a local OpenAI-compatible Chat Completions adapter, and what runtime-specific probes are needed for structured output, seeds, immutable model identity, context/runtime metadata, and HTTP behavior?

## Sources and methods

Accessed 2026-07-29. Research was documentation/source-only: no runtime was installed, no endpoint was contacted, and no model/provider call was made. Only current official project documentation and source were treated as authority.

### Ollama

- [OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [List models (`GET /api/tags`)](https://docs.ollama.com/api/tags)
- [Show model details (`POST /api/show`)](https://docs.ollama.com/api-reference/show-model-details)
- [Running models (`GET /api/ps`)](https://docs.ollama.com/api/ps)
- [Version (`GET /api/version`)](https://docs.ollama.com/api-reference/get-version)
- [Errors](https://docs.ollama.com/api/errors)
- [OpenAI translation source](https://github.com/ollama/ollama/blob/main/openai/openai.go)
- [Manifest digest source](https://github.com/ollama/ollama/blob/main/manifest/manifest.go)
- [Model loading/source](https://github.com/ollama/ollama/blob/main/server/images.go)

### llama.cpp

- [`llama-server` README and endpoint reference](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [Registered routes](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server.cpp)
- [HTTP/status behavior](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-http.cpp)
- [Error mapping and OpenAI request parsing](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/server-common.cpp)

## Findings

### 1. Small portable OpenAI-compatible surface

Both runtimes currently expose synchronous and streaming `POST /v1/chat/completions` plus `GET /v1/models`. The common request subset Buoy needs is `model`, `messages`, `stream`, `temperature`, and a bounded token limit (`max_tokens`); `seed` and `response_format` must remain negotiated capabilities rather than assumed merely because the endpoint is OpenAI-shaped. Ollama calls its compatibility partial; llama.cpp explicitly says it makes no strong compatibility claim.

Provider-independent request behavior should therefore be: `stream=false`, `temperature=0`, an explicit output-token bound, the configured model ID, messages, and only capability-confirmed `seed`/`response_format`. Buoy must parse the ordinary OpenAI response envelope, independently parse and validate `choices[0].message.content` as JSON, and fail closed on malformed or schema-invalid content.

### 2. Ollama Chat Completions, seed, and structured output

Ollama documents `/v1/chat/completions` support for JSON mode, “reproducible outputs,” `response_format`, and `seed`. Current source maps `seed` to Ollama's sampler option. It maps `response_format={"type":"json_object"}` to JSON mode and the standard nested form `{"type":"json_schema","json_schema":{"schema": ...}}` to the supplied schema. The structured-output guide says schemas constrain generation and recommends temperature `0` for more deterministic completions.

This proves parameter support, not bit-for-bit repeatability. Ollama's OpenAI response source emits the constant `system_fingerprint: "fp_ollama"`; it does not identify runtime version, backend configuration, or model revision and MUST NOT be used as a pin or determinism proof. Record `seed_supported=true` only after runtime identification/capability confirmation and still report `determinism=best_effort`.

### 3. llama.cpp Chat Completions, seed, and structured output

`llama-server` documents synchronous/streaming `/v1/chat/completions`, schema-constrained JSON, and support for completion-specific sampler options. `seed` is documented as the RNG seed (`-1` means random). Its current Chat Completions documentation accepts `response_format` JSON mode as `{"type":"json_object"}` and documents schema-constrained variants with a sibling `schema`, including `{"type":"json_schema","schema": ...}`; this is not the same envelope Ollama's current source documents for the standard nested `json_schema.schema` form.

A configured seed still does not establish bit-for-bit determinism. The same official server reference warns that `cache_prompt=true` (the documented default for the native completion path) can produce nondeterministic results because logits are not guaranteed bit-for-bit identical across differing batch sizes. Hardware/backend/build, batching, parallelism, prompt caching, speculative decoding, and model bytes remain relevant. Report only `best_effort`.

Implementation implication: structured mode needs a provider/runtime-specific encoder selected by a non-evidence synthetic capability probe; never silently downgrade from schema mode to unconstrained text. Validate returned JSON and schema locally in every case.

### 4. Ollama model identity and immutable revision

OpenAI-compatible `GET /v1/models` and `GET /v1/models/{model}` expose only OpenAI-shaped `id`, `created`, and `owned_by`; they do not expose Ollama's digest, quantization, or context metadata. They cannot pin a model.

Ollama-native `GET /api/tags` returns `name`/`model`, `digest`, `modified_at`, size, format/family/parameter size, and `quantization_level`. Current Ollama source sets a loaded model's digest from `Manifest.Digest()`, and the manifest source computes that digest with SHA-256 over manifest bytes; the manifest in turn contains config/layer digests. Thus the native digest is a content-addressed immutable revision for the resolved local manifest bytes. A mutable tag/name is not a revision. Buoy can accept the exact native digest as `model_revision`, must compare it before each build/doctor inference, and must fail on mismatch. If the native probe is unavailable, an explicit `--model-revision` remains required, but a caller-supplied string alone cannot prove the server is serving matching bytes; that limitation must be reported.

`POST /api/show` returns configured `parameters` (for example `num_ctx`), capabilities, `modified_at`, details including quantization, and raw `model_info` including architecture-specific training context keys. It does not replace the digest from `/api/tags` or `/api/ps`.

### 5. llama.cpp model identity cannot be proven by its HTTP metadata

`GET /v1/models` returns the loaded model ID (model path by default or configured `--alias`) and a `meta` object with `n_ctx_train`, parameter count, and size. It documents no model digest/revision. Aliases and paths are mutable labels; file size, parameter count, timestamps, and `build_info` are not hashes of model bytes. `GET /props` exposes `model_path` and server `build_info`, but no model digest.

Therefore llama.cpp's documented HTTP surface cannot prove immutable model pinning. Buoy MUST require an explicit revision for llama.cpp (preferably a provisioning-time SHA-256 of the complete GGUF/shard set) and truthfully record that server-side byte equality is unverified unless a separately trusted launcher/sidecar supplies and verifies that digest. Quantization is also not a stable documented `/v1/models` field; filename inference is insufficient, so record configured/external quantization or `unknown`.

### 6. Context and runtime metadata are runtime-specific optional probes

For Ollama, `GET /api/ps` returns loaded-model digest, details/quantization, and the active `context_length`; this is the strongest runtime context observation. `POST /api/show` exposes configured parameters and model training metadata, while `GET /api/version` returns runtime version. These endpoints are Ollama-specific.

For llama.cpp, `GET /props` returns actual default generation settings including `n_ctx`, total slots, model path, chat-template capabilities, modalities, and `build_info`. `GET /v1/models.meta.n_ctx_train` is the model's training context, not necessarily the configured runtime context. `/props.model_path` is sensitive filesystem data and doctor output must omit or sanitize it. The Chat Completions response also includes non-portable `timings` and standard `usage`; timings are diagnostic, not model identity.

The adapter contract should distinguish `configured_context_window` (required build contract) from `training_context_window` and `observed_runtime_context_window`. A mismatch between configured and safely observed runtime context must fail closed where it can affect the build.

### 7. Relevant HTTP behavior and redirects

Ollama documents JSON error bodies and status codes 400, 404, 429, 500, and 502. Mid-stream Ollama errors arrive in NDJSON without changing an already-started status, another reason for Buoy to use `stream=false`. llama.cpp documents `/health` and `/v1/health`: 503 with a JSON `unavailable_error` while loading and 200 when ready. Its source maps invalid request/auth/not-found/permission/not-supported/unavailable/context errors to 400/401/404/403/501/503/400 JSON errors, emits JSON 404 for unknown routes, and registers both `/v1/chat/completions` and `/v1/models` directly.

Neither project's official API contract promises or requires redirects for these endpoints, nor establishes a safe redirect target. Redirect handling is therefore not portable runtime behavior. Buoy must disable automatic redirects and reject every 3xx response without following it, preserving the active specification's loopback target invariant. It should also use `stream=false`, require JSON content within configured byte bounds, set explicit connect/read timeouts, make no implicit retries, and treat readiness/unavailable responses as explicit failures rather than retry signals.

## Smallest recommended adapter contract

1. **Portable required configuration:** loopback-validated base URL, model ID, immutable revision string, configured context window, prompt-contract version, output bound, and timeouts/body bounds.
2. **Portable request:** `POST /v1/chat/completions` with `model`, `messages`, `stream=false`, `temperature=0`, explicit max tokens, plus `seed` and strict `response_format` only when capability-confirmed.
3. **Portable response checks:** bounded JSON envelope; exactly one usable assistant content value; local JSON parse and schema validation; sanitized errors; no retries, redirects, cookies, proxies, or credentials.
4. **Optional read-only probes:** OpenAI `GET /v1/models` for availability only; Ollama `/api/version`, `/api/tags`, `/api/show`, `/api/ps`; llama.cpp `/health`, `/props`. Absence of an optional probe must not cause fallback to an unsafe claim.
5. **Identity:** accept Ollama's native manifest SHA-256 digest as the runtime pin. For llama.cpp, require externally supplied revision and disclose that HTTP cannot verify model bytes. Never treat model ID/path/alias, timestamps, size, metadata, or `system_fingerprint` as an immutable revision.
6. **Capability reporting:** `structured_output_mode` records the exact envelope used; `seed_supported` records confirmed support; determinism remains `best_effort`.

## Contradictions and unknowns

- The two runtimes document different JSON-schema envelopes. A generic “OpenAI-compatible” flag cannot select the correct strict-output request.
- Ollama documentation says “reproducible outputs,” but official material does not promise bit-for-bit determinism; its constant `fp_ollama` supplies no change signal.
- llama.cpp documents seed control but also documents a prompt-cache nondeterminism mechanism.
- No official llama.cpp HTTP field proves model-file digest, immutable revision, or quantization.
- Neither runtime documents a redirect contract. All redirects must remain prohibited.
- Official documents do not provide a stable, portable capability-discovery schema. The doctor must make its one permitted synthetic strict-output request to verify actual configured behavior, while builds fail closed on unconfirmed required capabilities.

## Conclusions

The active specification is feasible with a deliberately small OpenAI Chat Completions core plus narrowly identified optional probes. Ollama can supply an HTTP-observed immutable manifest digest and active context metadata through native endpoints. llama.cpp cannot prove model bytes through its documented HTTP API, so its revision must be supplied and verified outside the generic adapter or reported as externally asserted. Seeds and grammar/schema constraints improve repeatability and shape, but neither runtime justifies a stronger claim than `determinism=best_effort`.

## Limits

This investigation did not install either runtime, inspect a live response, download a model, or execute a capability probe. Current source on moving default branches can change; implementation should pin supported minimum runtime versions or preserve capability-probe failure as a closed error.
