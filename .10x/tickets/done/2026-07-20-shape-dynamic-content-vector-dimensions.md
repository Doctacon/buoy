Status: done
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md

# Shape Dynamic Content-Vector Dimensions

## Outcome

Produced and independently reviewed a user-legible architecture and product checkpoint for how Buoy may support non-384-dimensional **content** embeddings. The user ratified phase 1 exactly as reviewed: Crow-Plus at 768 dimensions, explicit namespace only, complete local staging before the first remote content write, the exact resource-verification checkpoint, and five independent approval phases. Both focused specifications are active. No executable operation was authorized or performed.

## Approval provenance

On 2026-07-20, after C2 established that no credible native 384-dimensional candidate fits the current boundary, the user explicitly approved opening separate shaping for dynamic content-vector dimensions. The approved shaping surface covers the retained 768- and 3,584-dimensional candidates, namespace schema/card/routing compatibility, isolation or migration, resource bounds, offline revision-pinned loading, and Nomic's query-only prefix.

The user then ratified Crow-Plus at 768 dimensions; explicit namespace only with no cards, catalogs, or automatic routing; every vector plus resource/output compliance staged and validated before the first remote content write; and five independent phase approvals in this fixed order: specification, bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write. Approval or success of one phase does not authorize, approve, or imply the next. No bootstrap/download, load, inference, implementation, source/test change, or external operation was approved.

After independent review passed repaired PR #61 head `9445030a5438de7f6c4308bfb8645ce0e4bf2bc5`, the user explicitly ratified the exact phase 1 checkpoint and directed activation of both reviewed specifications without changing their Crow/resource/staging contracts. This phase 1 ratification authorized active records only. Phase 2 bootstrap/download was separately approval-gated; it later completed and closed at `.10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md`. Phase 3 remains separately blocked at `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md`.

## Scope

- Compare the decision implications of:
  - `nomic-ai/nomic-embed-code@11114029805cee545ef111d5144b623787462a52` at 3,584 dimensions.
  - `Shuu12121/CodeSearch-ModernBERT-Crow-Plus@96ff525a7aa3bf8bfa90d77337c2b24bd45229af` at 768 dimensions.
- Shape how a content namespace declares and validates its embedding dimension and model contract without conflating content vectors with the independent 384-dimensional catalog-routing vector.
- Identify required namespace-card, remote-card, plan, apply-preview, compatibility, and automatic-routing contract changes and their failure behavior.
- Shape isolation and migration choices for existing 384-dimensional namespaces, including whether new-dimension experiments require separate namespaces, how incompatible namespaces are rejected, and whether any migration is necessary or should be avoided.
- Establish the resource checkpoint needed before any future download or load: exact pinned bytes, disk cache, construction and steady-state host RAM, device memory, precision/loading strategy, supported hardware, and abort bounds.
- Shape a revision-pinned offline-loading contract using explicit cache/bootstrap steps, `local_files_only`/offline enforcement, telemetry disablement, and locked-dependency compatibility verification.
- Shape query/document role handling. Nomic queries require `Represent this query for searching relevant code: ` while documents do not; Crow-Plus uses no prefix. Pooling and normalization semantics must remain model-specific and card-visible.
- Produce explicit options, tradeoffs, unresolved semantic decisions, and a confirm-or-correct checkpoint suitable for later ratification.

## Acceptance criteria

- The 768- and 3,584-dimensional candidates have a side-by-side compatibility and resource decision matrix grounded in C2's immutable evidence.
- The proposed contract clearly separates content-vector dimensions from catalog-routing dimensions and covers namespace schema, cards, plans, compatibility checks, and routing behavior.
- Existing 384-dimensional namespaces/defaults have an explicit isolation or migration strategy; no silent cross-dimension query, mixed-model namespace, or default change is permitted.
- Resource bounds distinguish download/disk, model construction peak, steady host RAM, device memory, and precision/loading assumptions. Unmeasured values remain labeled estimates or blockers.
- Offline loading is revision-pinned, cache-explicit, network-failing after bootstrap, telemetry-disabled, and compatible with the locked open-source dependency path without remote code.
- Query/document prefixes, pooling, and normalization are explicit for each candidate, including Nomic's query-only prefix.
- Before phase 1 ratification, the output recorded the candidate/containment/staging choices and five independent ordered approval phases in two draft focused specifications. After independent review and explicit phase 1 ratification, those exact specifications became active; no executable implementation/evaluation ticket was created.
- The proposed measurement fixes one exact UTF-8 query and one exact UTF-8 code/document input, including newline/encoding/hash identity, and requires sequential batch-1 calls with separate `[1,768]` outputs; pinned tokenizer IDs may be recorded after bootstrap.
- The shaping work records that no model/dependency download or install, model load, inference, credential access, live service call, source/test/lockfile change, or namespace/card/catalog/default write occurred.

## Blockers

None for this completed shaping outcome. Phase 2 is separately complete at `.10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md`; phase 3 is blocked pending separate approval at `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md`, and phases 4–5 remain approval-gated by the active specifications without executable owners.

## Explicit exclusions

Executable phase 2–5 operation or implementation tickets; model promotion; source, tests, configuration, dependencies, or lockfile changes; model/dependency downloads or installs; model loading or inference; credentials or live service calls; namespace, card, catalog, or default mutation; C4 execution or unblocking; migration execution; public CLI/API behavior.

## Evidence expectations

C2's immutable model evidence, inspected current source and locked open-source package contracts, a compatibility/resource/options matrix, explicit unknowns and decision questions, and a no-download/no-load/no-source/no-remote-write statement.

## References

- `.10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md`
- `.10x/research/2026-07-19-code-aware-embedding-candidate.md`
- `.10x/evidence/2026-07-19-code-aware-embedding-feasibility-research.md`
- `.10x/reviews/2026-07-20-code-aware-embedding-candidate-review.md`
- `.10x/research/2026-07-20-dynamic-content-vector-dimensions.md`
- `.10x/evidence/2026-07-20-dynamic-content-vector-dimension-shaping.md`
- `.10x/specs/crow-plus-explicit-namespace-pilot.md`
- `.10x/specs/crow-plus-resource-verification-checkpoint.md`
- `.10x/specs/depth-one-approved-apply-pipeline.md`
- `.10x/tickets/2026-07-19-evaluate-code-aware-embedding-pilot.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/apply.py`
- `src/buoy_search/catalog.py`
- `src/buoy_search/remote_catalog.py`
- `src/buoy_search/config.py`
- `src/buoy_search/plan_artifacts.py`

## Progress and notes

- 2026-07-20: Opened from the user's explicit approval to shape dynamic content-vector dimensions after C2's reviewed stop. No active behavior spec, candidate approval, download/install, model load, inference, source/test/lockfile change, namespace/card/catalog/default write, credential access, or live Buoy operation was authorized or performed.
- 2026-07-20: Completed initial record-only shaping at `.10x/research/2026-07-20-dynamic-content-vector-dimensions.md` with immutable 768/3,584 candidate bytes, explicit unmeasured RAM/device categories, strict 384 routing separation, versioned-card options, new-namespace/no-migration isolation, plan/apply/retrieval/automatic-routing failure contracts, pinned offline bootstrap/runtime controls, model-specific role semantics, implementation implications, stop conditions, and a confirm-or-correct checkpoint. Evidence: `.10x/evidence/2026-07-20-dynamic-content-vector-dimension-shaping.md`. Ticket remained active pending required independent review; no executable implementation/evaluation ticket was created.
- 2026-07-20: Applied the user's ratified choices: Crow-Plus 768 first; explicit namespace only with no card/catalog/automatic routing; complete vector/resource/output staging before write 1; and five independent approvals in order for specification, bootstrap/download, bounded measurement load, implementation/source changes, and indexing/write, with no phase implying the next. Drafted `.10x/specs/crow-plus-explicit-namespace-pilot.md` and `.10x/specs/crow-plus-resource-verification-checkpoint.md`. The experimental path stages every vector before a separately approved serial write and leaves the active depth-one default untouched. Read-only host inspection informed one exact conservative proposed checkpoint; thresholds remain draft and unratified, both specs remain draft, and no executable implementation/evaluation ticket or operation was authorized.
- 2026-07-20: Repaired PR #61 final review blockers record-only: the phase contract is explicitly five ordered, independent approvals; the proposed measurement now binds a 51-byte no-final-newline UTF-8 query and 129-byte LF-terminated UTF-8 code/document by SHA-256, runs them sequentially at batch 1, and requires separate `[1,768]` outputs. Token IDs remain deferred until pinned tokenizer bootstrap. No executable ticket, bootstrap/download, model load/inference, source/test change, credential access, or live operation was authorized or performed.
- 2026-07-20: Independent review passed repaired PR #61 head `9445030`; `.10x/reviews/2026-07-20-dynamic-content-vector-dimensions-shaping-review.md` records no phase 1 blocker and confirms the exact containment/resource/staging contract.
- 2026-07-20: The user explicitly ratified phase 1 exactly as reviewed. Activated both focused specifications without changing their exact Crow/resource/staging values, opened only the blocked phase 2 bootstrap/download owner, and closed this shaping ticket. No phase 2–5 operation was authorized or performed.

## Closure mapping

- **Candidate matrix and authority:** `.10x/research/2026-07-20-dynamic-content-vector-dimensions.md` maps Crow-Plus 768 and Nomic 3,584 to C2's immutable revisions, bytes, role/pooling/normalization contracts, compatibility implications, and explicitly unmeasured runtime resources.
- **Content/routing separation and isolation:** The research and active `.10x/specs/crow-plus-explicit-namespace-pilot.md` preserve the independent 384-dimensional routing projection and all existing 384-dimensional content namespaces/defaults. The pilot is exact explicit-namespace-only with no migration, cards, catalog, or automatic routing.
- **Resource/offline contract:** Active `.10x/specs/crow-plus-resource-verification-checkpoint.md` fixes the immutable 611,525,163-byte revision tree, cache/disk bounds, host/device/precision path, offline/telemetry/no-remote-code controls, fixed inputs, output checks, monitoring, qualification, and abort behavior. Unmeasured runtime values remain blockers rather than facts.
- **Complete staging and phase gates:** The active pilot spec requires every vector and resource/output observation to be staged and validated before credentials or remote content write 1, while preserving the ordinary depth-one default. Both specs require five ordered independent approvals with no transitive authority.
- **Exact workload identity:** The resource spec binds the 51-byte query and 129-byte LF-terminated code/document by exact text and SHA-256, sequential batch-1 calls, separate `[1,768]` outputs, and post-bootstrap tokenizer-ID observation without input changes or truncation.
- **Safety and scope:** `.10x/evidence/2026-07-20-dynamic-content-vector-dimension-shaping.md` and `.10x/evidence/2026-07-20-crow-plus-phase-1-specification-ratification.md` record that no download/install, model load/inference, credentials, live service, source/test/lockfile change, or namespace/card/catalog/default operation occurred.
- **Review and ratification:** `.10x/reviews/2026-07-20-dynamic-content-vector-dimensions-shaping-review.md` records independent PASS on repaired head `9445030`; the user then ratified phase 1 exactly as reviewed. Both specifications are active.
- **Downstream work:** `.10x/tickets/done/2026-07-20-bootstrap-crow-plus-immutable-cache.md` was the smallest next owner and is now independently reviewed and done. `.10x/tickets/2026-07-20-measure-crow-plus-bounded-runtime.md` is the blocked phase 3 owner pending separate approval; later phases remain governed and blocked without premature executable tickets.

## Retrospective

This shaping established that dynamic content dimensions are safely reviewable only when content and routing vectors remain explicitly separate, model identity includes every role/pooling/normalization/precision field, complete staging precedes any remote client, and resource discovery is split into independently approved immutable bootstrap and bounded measurement phases. Those durable behaviors live in the two active focused specifications; no additional knowledge or skill record is needed. The independently reviewed phase 2 owner now preserves the completed bootstrap evidence, while the blocked phase 3 owner preserves the only eligible next approval checkpoint without laundering phase 1 or phase 2 success into model-load authority.
