Status: done
Created: 2026-07-29
Updated: 2026-07-29
Parent: .10x/tickets/done/2026-07-29-autonomous-local-semantics-foundation-plan.md
Depends-On: .10x/tickets/done/2026-07-29-research-local-openai-compatible-runtimes.md

# Implement Local Semantic Inference

## Scope

Implement `.10x/specs/local-semantic-inference.md`: provider-independent protocol/model contracts, hardened loopback OpenAI-compatible HTTP adapter, strict bounded structured calls and repair support, model pinning/capability discovery, and `semantics doctor`, with focused provider-free tests and lazy CLI wiring.

## Acceptance criteria

All endpoint and doctor test cases in the governing spec pass; ordinary imports and `semantics --help`/`doctor --help` are connection/model/turbopuffer inert; no local-runtime dependency or weight is added; no hosted adapter/fallback exists.

## Explicit exclusions

Semantic evidence reads, pipeline/storage/build/estimate/verify/inspect implementation, docs beyond directly necessary CLI help, live model calls, and external writes.

## Evidence expectations

Changed files, focused command results, request/response caps/timeouts, security behavior, model contract, and residual compatibility limits.

## Blockers

None after the research dependency.

## Progress and notes

- 2026-07-29: Implemented provider-inert semantic model contracts and bounded JSON-schema validation in `semantics_models.py`.
- 2026-07-29: Implemented the direct stdlib loopback HTTP(S) adapter with exact-host and DNS/connected-peer checks, direct no-proxy/no-cookie/no-credential transport, redirect rejection, explicit timeout, 256 KiB request and 2 MiB response defaults, temperature zero, configured seed, strict runtime-specific schema envelopes, sanitized errors, model availability checks, Ollama digest/quantization/context/version discovery, llama.cpp metadata support, and fail-closed external revision pinning.
- 2026-07-29: Added synthetic-only `buoy semantics doctor`, environment/CLI configuration, pinned model contract/hash, best-effort determinism reporting, sanitized platform/memory information, and truthful zero-evidence/zero-turbopuffer/zero-hosted activity fields.
- 2026-07-29: Added 25 provider-free focused tests covering endpoint policy, poisoned DNS and peer escape, redirects, proxies, headers, byte bounds, timeout, malformed/schema-invalid output, unavailable model, revision/context mismatch, seed/schema reporting, synthetic doctor, sanitized platform/errors, inert help/imports, and stable endpoint-free model identity. Focused semantic tests passed; semantic/evidence/general CLI regression suite passed 73 tests; help/import and `git diff --check` passed. No network, model, evidence, turbopuffer, hosted provider, source write, or external action occurred.
- 2026-07-29: Independent review failed the initial slice on DNS-rebinding pre-send safety, weak Ollama digest/capability claims, incomplete schema-contract validation, missing generic repair, path disclosure, and total-deadline handling. Ticket returned to active for bounded repair.
- 2026-07-29: Repair pins the connection to a previously validated numeric loopback address and verifies the connected peer before HTTP body transmission while preserving Host/TLS SNI; exact lowercase `sha256:<64-hex>` Ollama digests are required for runtime verification. Doctor now confirms structured-output/seed capability only for identified documented Ollama or llama.cpp envelopes and fails generic runtimes closed instead of overclaiming.
- 2026-07-29: Complete schema trees, including omitted optional properties, are validated before instances. Added provider-independent validation-code-only repair with a two-retry hard cap, path-like model-ID rejection, finite timeout validation, and an absolute response deadline across connect/request/read.
- 2026-07-29: Repaired focused suite passed 33 tests; semantic/CLI/evidence regression suite passed 118 tests in 20.916s; `git diff --check` passed. Tests prove pre-send peer rejection transmits no body, pinned numeric connect with Host/SNI preservation, exact digest/capability behavior, nested schema rejection, bounded repair, path privacy, non-finite timeout rejection, and total-deadline failure. No live endpoint, model, evidence, turbopuffer, hosted provider, source write, or external action occurred. Ticket is done pending independent parent review.
- 2026-07-29: A second independent review found active Ollama digest reconciliation, relative model-ID/build-info privacy, and pre-resolution/header deadline gaps. The narrow repair now requires exact agreeing installed/active Ollama digests whenever their model records exist, reports an installed-but-unloaded model without observed runtime context, rejects every slash/backslash model ID, omits llama.cpp build metadata, and establishes the total deadline before DNS with remaining-budget checks before connect, TLS, request, response headers, and every body read. Deterministic regressions prove malformed/conflicting/missing active digests fail, unloaded pinning is truthful, private fragments are absent from full doctor JSON, slow resolution sends/connects nothing, and an over-budget request cannot advance to response headers.
- 2026-07-29: Second-repair focused suite passed 36 tests in 0.270s; semantic/CLI/evidence/general-CLI regression suite passed 121 tests in 21.025s; `git diff --check` passed. No live endpoint, network, model, evidence, turbopuffer, hosted provider, source write, staging, or external action occurred. Ticket remains done pending fresh independent acceptance review.
- 2026-07-29: Final narrow privacy repair validates externally supplied revisions as bounded public tokens before they can enter the model contract and omits path-like/control runtime quantization rather than persisting it. Valid SHA-256 and ordinary revision/quantization tokens remain supported. A regression injects absolute, relative, backslash, and control-containing revision values plus private Ollama quantization and proves sanitized failure or complete omission from the full doctor JSON. The 37-test focused semantic suite and `git diff --check` passed; no live endpoint or external side effect occurred.
- 2026-07-29: Final drive-relative privacy follow-up rejects Windows `C:private...` forms for configured model IDs and externally supplied model revisions before either can be persisted. Focused regressions verify sanitized errors contain no private fragment.
