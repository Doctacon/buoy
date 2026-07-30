Status: recorded
Created: 2026-07-29
Updated: 2026-07-30
Relates-To: .10x/tickets/done/2026-07-29-autonomous-local-semantics-foundation-plan.md, .10x/tickets/done/2026-07-29-complete-semantic-operations-and-validation.md, .10x/specs/local-semantic-inference.md, .10x/specs/autonomous-semantic-builds.md, .10x/specs/semantic-build-operations.md

# Autonomous Local Semantics Foundation

## What was observed

Semantic Phase 3B was implemented on `work/autonomous-local-semantics-foundation` from fetched `origin/main` commit `27cdcc7a5cecf527ce558f898d6ad39fa204a5bd`. The bounded final commit is pending the parent session's independent review and commit step; this record must be updated with that hash when created.

The implementation adds provider-inert `semantics_models.py`, a hardened standard-library `semantics_local_model.py`, deterministic `semantics_pipeline.py`, remote-first `semantics_remote.py`, lazy `semantics_cli.py`, provider-free tests, internal namespace filtering, package metadata, and documentation. No runtime/model/provider client is constructed by ordinary imports or help.

## Local inference and endpoint boundary

Runtime protocol is `openai_chat_completions_local_v1`. The first adapter sends synchronous strict structured Chat Completions to an explicitly configured OpenAI-compatible local server. Endpoint validation accepts only credential-free HTTP(S) URLs hosted at `127.0.0.1`, `localhost`, or `::1`; every DNS result and the connected peer must be loopback. The transport connects to the already validated numeric address to prevent DNS rebinding before prompt transmission. It uses no environment proxy, redirect handler, cookie jar, hosted API key, or retry; rejects every 3xx; bounds requests at 256 KiB and responses at 2 MiB by default; and applies one monotonic total deadline across resolution validation, connect, TLS, request, headers, and body reads.

Model identity records protocol/runtime, model ID, immutable revision, revision verification mode, quantization when safely known, configured context window, seed and confirmed support, exact structured-output envelope, prompt contract, and `determinism=best_effort`. Ollama manifest digests must match `sha256:<64 lowercase hex>` and conflicting tag/running digests fail. Runtimes without an observable digest require an externally asserted revision, which is path/control-character sanitized and truthfully labeled. Endpoint host/port and local paths are excluded from the model/build contract. Doctor uses synthetic text only and reports no evidence transmission or turbopuffer call.

Official interface research is recorded at `.10x/research/2026-07-29-local-openai-compatible-runtimes.md` from Ollama and llama.cpp primary documentation/source accessed 2026-07-29.

## Semantic pipeline and schemas

The explicit stages are active-evidence selection; strict extraction with at most two repair attempts; remote per-row extraction staging/resume; conservative normalization and bounded lexical blocking; independent local same-concept/close-match/related/distinct verification; deterministic union-find canonicalization; mention publication; bounded taxonomy proposal; independent taxonomy verification; structural validation; conditional final namespace publication; evidence re-verification; exact final scans; conditional catalog-last completion; and atomic bounded manifest write.

Controlled concept types are `process`, `capability`, `metric`, `problem`, `technique`, `technology`, `product`, `organization`, `person`, `place`, `event`, and `domain_concept`. Stored predicates are exactly `broader`, `related`, and `close_match`; `narrower` is derived and exact aliases live on concepts. Generic filler is rejected. Medium same-concept judgments do not merge; they retain distinct concepts with a provisional close-match disposition.

Remote exact schemas are exported as `EXTRACTION_SCHEMA_REMOTE`, `CONCEPT_SCHEMA`, `MENTION_SCHEMA`, `TAXONOMY_SCHEMA`, and `CATALOG_SCHEMA`. Extraction staging stores IDs, snapshot/branch/source/chunk/input/model/prompt/normalization hashes, state/count/bounded candidates JSON/retries/output hash—never full content, endpoint, credentials, prompts, raw provider responses, or chain-of-thought. Concepts store canonical/normalized labels, definition, controlled type, aliases, accepted/provisional state, score/breakdown, mention/namespace support, timestamps, and persisted-row hash. Mentions store accepted/provisional concept status, exact active snapshot/branch/source/chunk/page/URL/title/section provenance, bounded surface/excerpt, scores/contracts, and hash. Taxonomy stores endpoints, one allowed predicate, state, score/breakdown, basis (`evidence_supported` or `semantic_induction`), bounded representative mention IDs/rationale, timestamp, and hash.

Namespaces are `buoy-semantics-extractions-<short>`, `buoy-semantics-concepts-<short>`, `buoy-semantics-mentions-<short>`, `buoy-semantics-taxonomy-<short>`, and fixed `buoy-semantics-catalog-v1`. All `buoy-evidence-` and `buoy-semantics-` IDs are excluded from retrieval, routing cards, discovery, local/remote Command Center inventory, and explicit search. Semantic code contains no source-namespace or evidence-branch write path.

## Confidence and publication policy

Policy version is `semantic-confidence-v1`. Applicable signals use a normalized weighted mean:

- strict schema validity: 0.10;
- exact substring: 0.15;
- extraction confidence: 0.15;
- mention support: 0.10;
- namespace support: 0.05;
- lexical consistency: 0.10;
- local similarity: 0.10;
- independent verifier judgment: 0.10;
- type consistency: 0.075;
- structural validity: 0.075.

All values must be finite in `[0,1]`; the breakdown is sorted and persisted. When extraction confidence applies, schema/exact-substring/type/structural signals must equal 1 or the result is capped below provisional. Without verifier judgment at least provisional, the score is capped immediately below accepted. Alias union requires the verifier itself to reach the accepted threshold. Taxonomy verifier confidence directly gates accepted/provisional/rejected publication. Defaults are accepted `0.85` and provisional `0.65`; overrides must satisfy `0 <= provisional < accepted <= 1` and are build identity.

Accepted taxonomy is canonical, duplicate/self-edge free, accepted-endpoint only, acyclic, at most three parents per concept, and depth at most 12. Verification independently rechecks endpoint/status/cycle/parent/depth rules.

## Build identity, resume, verification, and inspection

Build identity `semantics_<first-16-hex>` hashes semantic schema; evidence snapshot; full/sampled coverage and deterministic namespace-proportional SHA-256 sampling contract; pinned model contract; evidence embedding contract; extraction/merge/taxonomy prompt versions; normalization/blocking/concept/confidence/taxonomy versions; thresholds; and every hard limit. It excludes creation time, endpoint, local path, request ID, and wall timing. A separate semantic logical hash binds canonical persisted concept/mention/taxonomy rows.

One same-host portalocker lock prevents concurrent execution of an identical build ID. Its retained zero-byte file is normal bounded operational state, not semantic data. One conditional staging row exists per selected evidence row, including zero-candidate rows. Resume requires `--resume`; it scans staging IDs, exact-fetches selected rows, checks bounded canonical bytes plus all input/chunk/content/model/prompt/output/candidate hashes and exact excerpts, reuses only exact rows, and processes only missing rows. Final rows use conditional first-write semantics. Incomplete internals receive no completed catalog row, are reported by deterministic namespace ID, and are not deleted. After all inference, a synthetic-only doctor re-probe must exactly match the pinned build model contract before final remote evidence/semantic validation and catalog publication.

`semantics verify` loads no model and performs no write. It validates catalog/build identity, evidence snapshot, exact schemas, every persisted row hash and logical hash, counts/statuses, concept/mention/active-evidence provenance, taxonomy endpoints/basis/status/acyclicity/parents/depth, model contract hashes, and a supplied/present manifest. `semantics inspect` performs remote reads only, supports summary/concepts/mentions/taxonomy plus accepted/provisional filters, caps output at 100 rows, and exposes bounded excerpts and safe score/rationale/provenance fields without full content.

## 500-row structural result

The deterministic in-process fake-provider/fake-model structural test processed 500 active evidence rows and 3,000 raw candidates. It published 2,900 concepts, 3,000 active-evidence mentions, and four taxonomy rows covering accepted `broader`, `related`, and `close_match` plus a provisional relation. It observed one accepted alias merge, 1,326 sequential accounted local-model calls (1,321 fake-client calls including the final synthetic pin probe plus five injected proposer/verifier calls) with maximum concurrency one, exactly 6,405 remote semantic rows (500 extraction + 2,900 concept + 3,000 mention + 4 taxonomy + 1 catalog), approximately 7,449,020 canonical JSON request bytes including schemas and catalog completion, 19 bounded remote write calls, 32,600 evidence UTF-8 bytes, 10,867 approximate input tokens by the conservative bytes/3 method, 7,424,226 derived bytes, 7,638 persistent local manifest bytes plus a zero-byte lock file, 97,583,104 maximum RSS reported by the process, and 0.835900 seconds measured fake wall time (0.833794 seconds reported in the build result). Semantic logical hash was `d5ca6f33ffc1137cf2d7fa951d0710ffd015cdfb56139acb226b874f6934806e`.

The in-process RSS includes fake remote state and the Python test process; it is observational, not a provider-backed client-only measurement and has no brittle latency threshold. Content was requested one row at a time and never persisted locally. The approximate remote-byte number is canonical JSON request bytes generated by Buoy, including explicit schemas and the catalog completion request; it is not turbopuffer billing or physical storage. Remote writes were batched and catalog completion was last.

## Validation procedure and results

Observed from the task worktree:

- `uv sync --locked --extra semantics` — pass; 157 packages resolved and 106 checked. The `semantics` extra is intentionally empty because the external runtime uses the standard library; it adds no model/runtime dependency.
- `uv lock --check` — pass; 157 packages resolved.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/validate_ranking_contract.py` — pass; 13 datasets, 369 judgments, bundle SHA-256 `5a79f58aaca87a2d4f7cbec68fdcfbbcbf041131821587f8aba74a86daca99d9`.
- `PYTHONDONTWRITEBYTECODE=1 uv run python scripts/c6_syntax_forecast.py validate` — pass; forecast `d5199276c19ae89779287eaa90824ce1e1cc684a3f060899f02f65d976016243`.
- Focused semantic/evidence/catalog/release suite — final repair pass: 180 tests in 18.483s. An immediately prior run found only README's 102-line release-policy limit; README was reduced to 100 lines and the exact suite passed.
- Full `unittest discover` — final parent-observed pass: 935 tests in 112.241s, 39 skipped. Earlier implementation checkpoints passed 921, 929, and 934 tests as coverage expanded.
- `git diff --check` — pass.
- `uv build --out-dir dist` — pass; wheel and sdist built.
- Package inventory — 77 wheel entries and 179 sdist entries. Wheel contains all five semantic modules; sdist contains those modules, `docs/semantics.md`, and all five semantic tests. Neither contains model weights, `build.json`, `snapshot.json`, DuckDB files, or `node_modules`.
- Provider-inert help — `semantics --help`, `doctor --help`, and `verify --help` passed with connection/model/hosted imports guarded. `verify` imports no local model runtime.
- Installed-wheel provider-free fake semantic build — pass in a temporary isolated uv virtual environment using `SemanticRemoteTests.test_exact_remote_schemas_and_catalog_is_written_last`; 104 cached ordinary dependencies installed, one fake build test passed, and the environment was deleted.
- Frontend source was unchanged; `npm ci/test/build` was intentionally not run and packaged frontend assets were not rebuilt.

- Final cleanup/restoration `rm -rf dist web/node_modules; uv sync --locked; uv lock --check` — pass; 157 packages resolved, 106 checked, distribution and node_modules artifacts absent. Final `git diff --check` passed and README remained at the 100-line release-policy limit.
- 2026-07-30 independent-review repair validation — 270 focused semantic/evidence/catalog/namespace/Command Center/release tests passed in 22.490s; full discovery passed 934 tests in 111.564s with 39 skips; `git diff --check` passed. Five new regressions cover exact completed-catalog identity reuse, build-time representative-mention rejection, verify-time unknown/unrelated representative rejection, and doctor-inclusive estimate accounting at a one-call limit. The 500-row structural implementation and measurements were unchanged; no live call ran.

## Activity and prohibited side effects

No live smoke ran. Ambient model/provider credentials were not used. No hosted model call, hosted embedding call, OpenAI/Anthropic adapter, source crawl, source namespace write, evidence-branch write, real apply, graph database, graph visualization, Command Center semantic UI, model download, push, merge, pull request, publish, or release occurred. Model-provider budget remained $0. All semantic and turbopuffer behavior under test used deterministic fakes.

## Limits

- Live Ollama/llama.cpp and turbopuffer permission, billing, latency, runtime-specific metadata, and strict-output behavior remain unobserved because the opt-in smoke was not configured or authorized.
- Best-effort local inference is provenance-bound but not promised bit-identical across environments.
- Model revision equality for runtimes without a served digest is externally asserted, not proven by the generic HTTP surface.
- Semantic catalog integrity detects incoherent changes but is not a cryptographic defense against a privileged actor coherently rewriting all authoritative remote data.
- Incomplete deterministic internals are retained; deletion/GC and cross-host lease recovery are future work.
- Phase 3B has no arbitrary assertions, complete ontology, graph UI, manual curation, scheduling, incremental maintenance, or lifecycle deletion.

## Parent closure observation

On 2026-07-30 the parent independently repeated the requested validation boundary: 186 focused tests passed; 935 full tests passed with 39 skips; locked semantic sync and lock checks, ranking/C6 validators, wheel/sdist build and 77/179-entry inventory, provider-inert imports/help, installed-wheel fake build, environment restoration, and final diff checks all passed. The independent review at `.10x/reviews/2026-07-30-autonomous-local-semantics-foundation-review.md` has verdict `pass`. The implementation commit hash is recorded in the follow-up record-only closure update; that closure-only commit does not change implementation behavior.
