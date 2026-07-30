Status: recorded
Created: 2026-07-30
Updated: 2026-07-30
Relates-To: .10x/tickets/2026-07-30-autonomous-local-semantics-live-acceptance.md, .10x/specs/local-semantic-inference.md, .10x/specs/autonomous-semantic-builds.md, .10x/specs/semantic-build-operations.md

# Autonomous Local Semantics Live Acceptance

## What was observed

The live acceptance ran from Buoy commit `4ec8186ef3245abbc56072c343f5d6c0140b8712` on `work/autonomous-local-semantics-live-acceptance`. The foundation branch had already been pushed for backup. The acceptance branch remained unmerged and unpushed during delegated execution.

Hardware was macOS 26.5.1 on arm64 Apple M2 Pro with 16 GiB physical memory. The safe system probe reported 36% memory free and approximately 3.05 GB free/inactive/speculative/purgeable memory at the probe; encrypted swap was already 7.96 GiB used before inference. Free disk before model download was approximately 26.8 GiB and approximately 25.0 GiB afterward, retaining more than 15 GiB. Buoy used Python 3.13.0.

Ollama 0.11.10 was already installed and listening only on `127.0.0.1:11434` before this task. llama.cpp build 9360 was also installed but was not used. The only preexisting cached Ollama model was an embedding model, so one instruction model was downloaded: `qwen2.5:3b-instruct-q4_K_M`, GGUF 3.1B Q4_K_M, 1,929,912,432 bytes. Its runtime-observed immutable revision was `sha256:357c53fb659c5076de1d65ccb0b397446227b71a42be9d1603d46168015c9e4b`. The configured and observed runtime context was 4,096 tokens. Ollama reported approximately 2.9 GB loaded model size on Apple GPU. The Ollama process group changed from approximately 13,984 KiB resident before inference to approximately 95,936 KiB after doctor; GPU/model allocation is not represented by that RSS number. The preexisting server was not stopped; the downloaded model was unloaded after the blocked acceptance attempt.

Before local inference, OpenAI, Anthropic, Cohere, Voyage, Gemini/Google, Mistral, Together, Groq, Hugging Face, and upper/lowercase HTTP proxy variables were confirmed absent. The semantic commands explicitly removed those variables from their execution environment. Buoy's direct transport continued to inherit no proxy configuration, prohibit redirects, and use the validated numeric loopback peer. No hosted-provider key or hosted fallback was available to the semantic pipeline.

## Live doctor and repaired defects

The first real doctor exposed two implementation defects against the documented local-runtime contract:

1. `http.client` can mark a declared-Content-Length response complete and close the underlying socket after the final body read. Buoy attempted another socket timeout update before recognizing completion and converted `EBADF` into `transport_failure`. The repair checks `HTTPResponse.isclosed()` before the next deadline/read iteration. A deterministic regression reproduces a response that closes its socket immediately after the declared body.
2. Ollama 0.11.10 reports installed and active SHA-256 model digests as 64 lowercase hexadecimal characters, while Buoy accepted only the equivalent `sha256:<hex>` form. The repair accepts either exact format and canonicalizes to `sha256:<hex>` before pin comparison; malformed and conflicting digests still fail closed. A regression verifies raw runtime digest canonicalization against a prefixed configured pin.

After both repairs, actual `buoy semantics doctor` passed against `http://127.0.0.1:11434/v1`. Final observed command wall time was 3.824 seconds and the structured local call latency was 3.043808 seconds. Doctor reported runtime digest verification, Q4_K_M quantization, context 4,096, seed support, strict structured-output support, evidence rows read 0, turbopuffer calls false, hosted model calls false, and hosted cost 0. The troubleshooting path used only bounded synthetic prompts; no evidence was transmitted or logged.

Classification: both findings were **implementation defects**, repaired narrowly with regressions. Ollama itself was compatible after repair. The 3.1B model passed the synthetic protocol check, but its semantic capability was not evaluated because no evidence entered inference.

## Namespace and evidence gate

Exactly one valid local applied-state candidate existed, referred to only as the selected test namespace. It was non-internal and had valid applied state with 3,301 active and 84 retained-stale rows (3,385 total). It was the only candidate, so no namespace below 1,000 rows was available.

A bounded read confirmed no evidence catalog namespace and therefore no compatible completed snapshot to reuse. The required read-only evidence estimate then ran with maximum 1,000 rows and maximum 1 GiB remote logical bytes. It observed 3,385 ledger rows, approximately 3,385 remote rows, and 7,920,763 approximate logical bytes. The byte limit passed, but the exact row limit failed. The estimate made six accounted remote read queries, wrote zero remote rows, made zero branch calls, wrote no manifest, and reported source namespace writes false.

Per the explicit instruction to proceed only when this strict estimate passed, no evidence snapshot was created. No snapshot ID exists. No source namespace, evidence branch, evidence ledger, or evidence catalog write occurred. This is an **environment limitation**: the only applied-state candidate exceeded the user-authorized evidence row cap. Subsetting Phase 3A snapshot membership or increasing the cap would change the authorized contract and was not attempted.

Consequently, semantic estimate, semantic build, semantic verify, private inspect bundle, and local-model semantic-quality audit were not run. No semantic build ID exists, no semantic internal namespaces were created, local semantic persistent bytes are zero, semantic internal write calls/rows/bytes are zero, and accepted/provisional/rejected/taxonomy quality counts are unavailable. No private evidence content, semantic label, mention, excerpt, prompt, response, source title, raw provider response, credential, or private path is contained in this record.

## Validation

After the two source repairs:

- `git diff --check` passed.
- `uv sync --locked --extra semantics` and `uv lock --check` passed before live work; the environment was restored with locked sync/check afterward.
- Focused semantic suite passed 83 tests in 1.284 seconds.
- Ranking contract validator passed with its existing fixture hashes.
- C6 syntax forecast validator passed with checkpoint `c3a1560e611114760909c110a118a3ce1a60f0527de08c769a85a20b263f4e0f`.
- Full unittest discovery passed 937 tests in 107.756 seconds with 39 skipped.
- Wheel and sdist built successfully; inventory remained 77 wheel entries and 179 sdist entries and contained the repaired source/regression test.
- `dist` was removed and final diff/lock checks passed.

## Side-effect accounting and limits

Hosted inference calls and cost were zero. Hosted embeddings were not invoked. Source writes, evidence-branch writes, apply, deletion, garbage collection, graph visualization, merge, pull request, publish, and release did not occur. Turbopuffer activity was read-only metadata/estimate activity; internal evidence and semantic writes were zero. No local database, model weight, runtime file, raw log, private manifest, provider response, or semantic content was added to Git.

The local model download remains cached as authorized. The preexisting Ollama server remains running because the task did not start it; the selected model was unloaded to release inference memory.

## What this supports and limits

This supports real loopback compatibility of the repaired transport/digest boundary with Ollama 0.11.10 and the selected pinned quantized model, plus fail-closed enforcement of the strict evidence row budget. It does not support claims about extraction quality, model-call throughput on evidence, concepts/mentions/taxonomy, remote semantic publication, verification, or useful semantics. Semantic-quality review remains required before merge, and the bounded live acceptance remains blocked until a suitable <=1,000-row applied namespace/snapshot exists or the user explicitly authorizes a larger evidence snapshot cap.
