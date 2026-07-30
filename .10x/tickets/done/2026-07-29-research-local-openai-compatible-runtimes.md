Status: done
Created: 2026-07-29
Updated: 2026-07-29
Parent: .10x/tickets/done/2026-07-29-autonomous-local-semantics-foundation-plan.md
Depends-On: None

# Research Local OpenAI-Compatible Runtimes

## Scope

Verify current official Ollama and llama.cpp OpenAI-compatible Chat Completions, model metadata/revision, structured output/JSON schema, seed, runtime metadata, and redirect/protocol behavior relevant to Buoy's external local-server adapter. Record primary-source findings and limits without changing implementation.

## Acceptance criteria

A dated research record cites current official primary sources, distinguishes portable OpenAI-compatible behavior from runtime-specific optional probes, identifies what can/cannot prove immutable model pinning and deterministic output, and recommends the smallest provider-independent adapter contract consistent with active specs.

## Evidence expectations

URLs, access date, precise endpoints/fields, contradictions/unknowns, and implementation implications.

## Explicit exclusions

No code edits, runtime installation, model download, model call, evidence read, turbopuffer call, or hosted inference call.

## Blockers

None.

## Progress and notes

- 2026-07-29: Read `.10x/specs/local-semantic-inference.md` and completed official-primary-source research in `.10x/research/2026-07-29-local-openai-compatible-runtimes.md`. Verified the portable `/v1/chat/completions` and `/v1/models` subset; documented runtime-specific strict-output envelopes, seed limits, metadata probes, HTTP/status behavior, and mandatory redirect rejection. Established that Ollama's native manifest SHA-256 digest can pin the resolved local model, while llama.cpp's documented HTTP surface cannot prove model bytes and requires an externally supplied/verified revision. No runtime/provider/model/turbopuffer/evidence call, installation, download, or source edit occurred.
- 2026-07-29: Acceptance criteria met. Ticket marked done at its existing path; mechanical movement to `.10x/tickets/done/` and reference repair are reserved to the parent session because this worker has no rename/delete capability.
