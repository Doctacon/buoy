Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Local Semantic Inference

## Purpose and scope

Define the provider-independent, local-only inference boundary used by Phase 3B semantic builds. This surface includes endpoint validation, pinned model identity, strict structured Chat Completions, bounded repair, determinism reporting, and `buoy semantics doctor`. It excludes hosted adapters, model downloads or weights, hosted embeddings, arbitrary remote URLs, and evidence access during doctor.

## Behavior

- Buoy MUST communicate with an explicitly configured OpenAI-compatible Chat Completions endpoint over HTTP(S), but only when the URL host is exactly `127.0.0.1`, `localhost`, or `::1` and DNS resolution plus every connection target remains loopback.
- URL credentials, non-HTTP(S) schemes, redirects, proxies, cookies, hosted-provider keys, unbounded bodies, implicit retries, and hosted fallback are prohibited.
- Requests MUST use explicit connect/read timeouts, bounded request/response bytes, `temperature=0`, a configured seed when supported, and strict JSON/schema output when supported. Prompt/response bodies and evidence excerpts MUST NOT enter logs or exception text.
- The model contract MUST record runtime protocol, model ID, immutable revision/digest, quantization when known, configured context window, seed capability, structured-output capability/mode, prompt-contract version, and `determinism=best_effort` unless the runtime proves stronger behavior. Endpoint host/port is not build identity.
- A build MUST NOT publish with an unpinned revision. Runtime metadata may satisfy the pin; otherwise `--model-revision` is required. Revision mismatch fails closed.
- Ordinary imports and every `--help` path MUST be provider/model inert. Buoy packages no model weights and triggers no model download.
- `semantics doctor` MUST use only synthetic text, make no turbopuffer/evidence call, test one strict structured response, report sanitized process/platform/memory/runtime/model metadata when safely available, report latency/capabilities/context/model contract, and truthfully state zero evidence transmission, zero hosted calls/cost, and zero turbopuffer calls/writes.

## Acceptance criteria

Provider-free tests cover loopback IPv4/hostname/IPv6, non-loopback/LAN/public/DNS/credential/scheme/redirect rejection, proxy disabling, request/response bounds, timeout, malformed JSON, unavailable model, revision mismatch, strict-output and seed capability reporting, synthetic-only doctor behavior, platform/path sanitization, no secret/evidence logging, and inert imports/help.

## Constraints and exclusions

No local-runtime library is required. Standard-library HTTP is preferred unless a lightweight optional `semantics` extra is justified. No OpenAI, Anthropic, hosted model, remote endpoint escape hatch, model-weight management, directory scanning, or bit-for-bit reproducibility claim is permitted.
