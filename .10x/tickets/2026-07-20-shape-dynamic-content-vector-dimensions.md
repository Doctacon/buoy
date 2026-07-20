Status: active
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md

# Shape Dynamic Content-Vector Dimensions

## Outcome

Produce a user-legible architecture and product checkpoint for whether and how Buoy could support non-384-dimensional **content** embeddings. This is shaping only. It MUST NOT activate a behavior specification, select or approve a model, implement plumbing, download or load weights, run inference, or perform namespace/card/catalog/default writes.

## Approval provenance

On 2026-07-20, after C2 established that no credible native 384-dimensional candidate fits the current boundary, the user explicitly approved opening separate shaping for dynamic content-vector dimensions. The approved shaping surface covers the retained 768- and 3,584-dimensional candidates, namespace schema/card/routing compatibility, isolation or migration, resource bounds, offline revision-pinned loading, and Nomic's query-only prefix. No implementation or external side effect was approved.

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
- The output ends at a user decision checkpoint. It does not create an active specification or executable implementation/evaluation ticket.
- The shaping work records that no model/dependency download or install, model load, inference, credential access, live service call, source/test/lockfile change, or namespace/card/catalog/default write occurred.

## Blockers

The shaping output is complete but this ticket remains active pending independent review of the record-only PR. All behavior selection, implementation, downloads, model loading, and remote writes remain blocked pending review, explicit semantic ratification at the recorded checkpoint, focused active specifications where required, bounded executable tickets, and exact resource/write approvals.

## Explicit exclusions

Active behavior specifications or decisions; model selection/promotion; source, tests, configuration, dependencies, or lockfile changes; model/dependency downloads or installs; model loading or inference; credentials or live service calls; namespace, card, catalog, or default mutation; C4 execution or unblocking; migration execution; public CLI/API behavior.

## Evidence expectations

C2's immutable model evidence, inspected current source and locked open-source package contracts, a compatibility/resource/options matrix, explicit unknowns and decision questions, and a no-download/no-load/no-source/no-remote-write statement.

## References

- `.10x/tickets/done/2026-07-19-research-code-aware-embedding-candidate.md`
- `.10x/research/2026-07-19-code-aware-embedding-candidate.md`
- `.10x/evidence/2026-07-19-code-aware-embedding-feasibility-research.md`
- `.10x/reviews/2026-07-20-code-aware-embedding-candidate-review.md`
- `.10x/research/2026-07-20-dynamic-content-vector-dimensions.md`
- `.10x/evidence/2026-07-20-dynamic-content-vector-dimension-shaping.md`
- `.10x/tickets/2026-07-19-evaluate-code-aware-embedding-pilot.md`
- `src/buoy_search/chunker.py`
- `src/buoy_search/apply.py`
- `src/buoy_search/catalog.py`
- `src/buoy_search/remote_catalog.py`
- `src/buoy_search/config.py`
- `src/buoy_search/plan_artifacts.py`

## Progress and notes

- 2026-07-20: Opened from the user's explicit approval to shape dynamic content-vector dimensions after C2's reviewed stop. No active behavior spec, candidate approval, download/install, model load, inference, source/test/lockfile change, namespace/card/catalog/default write, credential access, or live Buoy operation was authorized or performed.
- 2026-07-20: Completed record-only shaping at `.10x/research/2026-07-20-dynamic-content-vector-dimensions.md` with immutable 768/3,584 candidate bytes, explicit unmeasured RAM/device categories, strict 384 routing separation, versioned-card options, new-namespace/no-migration isolation, plan/apply/retrieval/automatic-routing failure contracts, pinned offline bootstrap/runtime controls, model-specific role semantics, implementation implications, stop conditions, and a confirm-or-correct checkpoint. Evidence: `.10x/evidence/2026-07-20-dynamic-content-vector-dimension-shaping.md`. Ticket remains active pending required independent review; no model was selected and no behavior/spec/decision/ticket was activated.
