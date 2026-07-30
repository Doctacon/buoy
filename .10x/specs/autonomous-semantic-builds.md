Status: active
Created: 2026-07-29
Updated: 2026-07-29

# Autonomous Semantic Builds

## Purpose and scope

Phase 3B transforms one completed immutable Phase 3A evidence snapshot into one immutable remote semantic build containing reusable concepts, exact evidence mentions, and a lightweight taxonomy. Publication is autonomous: high-confidence objects are accepted, medium-confidence objects provisional, and low-confidence candidates rejected or retained only in bounded diagnostics. This is not a complete ontology and does not extract factual assertions.

## Inputs and eligibility

The build MUST read the completed evidence catalog row, evidence ledger, and immutable evidence branches only. It MUST process selected ledger rows with `status=active`; `retained_stale` and `deleted` remain historical membership and are ineligible. Content retrieval MUST be strong, bounded, exact-ID where safe or deterministic ordered streaming otherwise, request only required attributes, never request/persist vectors, and never materialize a whole namespace or corpus in memory/local storage.

Every published mention MUST bind `evidence_snapshot_id`, branch, source namespace/row ID, and matching chunk hash for an active ledger row.

## Semantic kernel

Every concept has exactly one controlled type: `process`, `capability`, `metric`, `problem`, `technique`, `technology`, `product`, `organization`, `person`, `place`, `event`, or `domain_concept`. Models cannot invent types. Concepts are reusable domain ideas, not every noun, filler, complete claims, generic words without domain meaning, or hierarchy-only inventions.

Stored taxonomy predicates are exactly `broader` (child to parent), `related` (canonical symmetric pair), and `close_match` (canonical symmetric pair). `narrower` is derived and never stored. Exact aliases live on canonical concepts. Arbitrary predicates and factual assertions are prohibited.

## Pipeline

1. Stream selected active evidence rows one at a time. A strict extraction prompt returns at most 12 bounded candidates with surface form, canonical proposal, controlled type, concise definition, exact supporting excerpt, and confidence. Exact substring/surface/type/length/finite-confidence validation is deterministic; unknown fields fail. Duplicate row candidates are removed deterministically.
2. Invalid output receives at most two bounded repair attempts using only the same bounded row and invalid structured output. A full or sampled build cannot complete while a selected row remains unaccounted for.
3. Persist one bounded extraction record per selected row in deterministic `buoy-semantics-extractions-<short-id>`, including zero-candidate rows, hashes/contracts/state/candidates/retries/output hash but no full content, prompt, response, endpoint, path, secret, or chain-of-thought. Exact valid records are resumable; conflicts fail closed; `--resume` is required for incomplete matching internals.
4. Deterministically normalize Unicode/case/whitespace/conservative punctuation and create lexical blocks. Use the evidence snapshot's compatible local embedding contract when available, or an explicit documented deterministic lexical-only fallback; never silently change/download an embedding model. Candidate generation is bounded and not all-pairs.
5. A separate local verifier classifies bounded pairs as `same_concept`, `close_match`, `related`, or `distinct`. Accepted same-concept decisions feed deterministic union-find; incompatible senses/types remain distinct unless a separately validated canonicalization safely resolves them.
6. Generate and validate canonical label, definition, one controlled type, aliases, and deterministic cluster-based concept ID. Every published concept has at least one valid mention; aliases are unique and cannot silently belong to two accepted concepts.
7. Publish deterministic accepted/provisional mention rows with bounded exact excerpts and provenance; never full content.
8. Propose only bounded `broader`, `related`, or `close_match` candidates, then verify each through a separate taxonomy prompt returning supported/unsupported/alternative/confidence/bounded rationale.
9. Programmatically reject self/duplicate edges, canonicalize symmetric pairs, enforce accepted endpoint/status rules, at most three accepted parents, depth at most 12, and acyclic accepted `broader`. Structural diagnostics record prevented cycles.
10. Write final concepts, mentions, and taxonomy remote namespaces, then write one `state=complete` row to `buoy-semantics-catalog-v1` last. Only then atomically write bounded local `artifacts/semantic-builds/<build-id>/build.json` (maximum 256 KiB).

## Confidence policy

Defaults are accepted `0.85` and provisional `0.65`, with `0 <= provisional < accepted <= 1`; overrides are build identity. A deterministic versioned policy score MUST combine applicable schema validity, exact substring validation, extraction confidence, supporting mention and namespace counts, lexical consistency, local similarity, independent merge/taxonomy verifier judgment, type consistency, and structural validity. Raw model confidence MUST NOT dominate or alone create accepted status. Score components and a compact bounded breakdown MUST persist; rationale is bounded to 280 characters and never chain-of-thought.

## Identity, coverage, limits, and concurrency

Build identity is `semantics_<first-16-hex>` over semantic schema, evidence snapshot, full/sampled coverage and sampling contract, pinned local model contract excluding endpoint, seed, prompt versions, embedding contract, concept/type/taxonomy/confidence versions, thresholds, and relevant hard limits. Creation time, endpoint, paths, request IDs, and timing are excluded. Final content also has a separate semantic logical hash; best-effort local inference is not claimed bit-identical.

Default full coverage processes all active rows and never silently truncates. Experimental `--sample-size/--sample-seed` uses deterministic stratified namespace-aware stable-hash sampling and records sampled coverage/counts/algorithm. Full builds fail before completion when limits would be exceeded. Defaults: 500 rows, 4,000,000 evidence UTF-8 bytes, 2,000 model calls, 21,600 wall seconds, 10,000 candidates, 5,000 concepts, 20,000 taxonomy rows, 268,435,456 derived bytes, and model concurrency exactly 1.

A local lock under the semantic output root prevents same-host duplicate build execution. Incomplete deterministic internals are reported and retained; no automatic deletion or cross-host takeover/lease claim exists.

## Remote and local contracts

Final namespaces are deterministic `buoy-semantics-concepts-<short>`, `...-mentions-<short>`, and `...-taxonomy-<short>` plus extraction staging and fixed catalog. All `buoy-semantics-` and `buoy-evidence-` IDs are internal and excluded from ordinary routing and Command Center source inventory.

Concept rows include identity/build/snapshot, canonical+normalized label, definition/type/aliases, status/policy/breakdown, mention/namespace counts/source namespaces, timestamp, and semantic hash. Mention rows include build/snapshot/concept/status, complete active evidence provenance, bounded label/excerpt, extraction/policy scores, and model/prompt contracts. Taxonomy rows include endpoints/predicate/status/policy/breakdown/basis (`evidence_supported` or `semantic_induction`), representative mention IDs, bounded rationale, timestamp, and semantic hash. Exact schemas are authoritative; vectors are optional and not required.

The catalog records complete provenance/contracts/thresholds/namespaces/counts/activity/bytes/tokens/quality sample/logical+manifest hashes. Completion is catalog-last. Local persistence is only the bounded manifest and normal lock/operational state—not candidates, corpus, graph, model output, or model weights.

## Acceptance criteria

Provider-free fake-model/fake-turbopuffer tests cover extraction validation/repair/failure, active-only evidence, deterministic resume/conflict behavior, canonicalization and ambiguous senses, confidence status rules, taxonomy grammar/verification/acyclicity/depth/parents, exact remote schemas and filtering, budgets/sampling/build identity, bounded manifest, immutable catalog-last lifecycle, and a 500-row/several-thousand-candidate structural run proving streamed evidence, one model call at a time, batched writes, exact hashes/counts, bounded local bytes, and observational RSS.
