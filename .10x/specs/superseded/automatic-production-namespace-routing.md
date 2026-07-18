Status: superseded
Created: 2026-07-15
Updated: 2026-07-16

# Automatic Production Namespace Routing

## Purpose and scope

Add opt-in production namespace selection to `buoy retrieve` using enabled compatible cards from the canonical local catalog, then reuse existing explicit multi-namespace retrieval and cross-namespace RRF.

This specification extends `.10x/specs/explicit-multi-namespace-retrieval.md` only for invocations that explicitly pass `--auto-route`. Existing explicit namespace and environment behavior remains unchanged otherwise.

## CLI activation

`buoy retrieve` MUST add:

- `--auto-route`: activate catalog routing;
- `--route-top-k N`: positive integer, default `3`, maximum `10`, valid only with `--auto-route`;
- `--catalog PATH`: override catalog path for this command.

Activation rules:

- one or more CLI `--namespace` arguments and `--auto-route` are mutually exclusive and MUST fail before model, credential, catalog mutation, or Turbopuffer work;
- `--auto-route` MUST ignore `TURBOPUFFER_NAMESPACE` and emit a concise warning that explicit environment selection was replaced by the CLI routing request;
- explicit namespace retrieval without `--auto-route` MUST not load or validate the catalog and MUST retain current behavior byte-for-byte where practical;
- `--route-top-k` or `--catalog` on retrieve without `--auto-route` MUST fail clearly rather than be ignored;
- CLI catalog path overrides non-empty `BUOY_CATALOG_PATH`, which overrides resolved/default state-root catalog; whitespace-only paths fail configuration;
- automatic routing MUST never activate merely because namespace selection is absent;
- all environment-replacement/deprecation warnings MUST use stderr so JSON stdout remains valid.

## Catalog load and eligibility

Before scoring, load and fully validate the catalog under `.10x/specs/superseded/production-local-namespace-catalog.md`.

A card is eligible only when:

- `enabled=true`;
- card region equals resolved runtime region;
- card embedding model and precision equal resolved retrieval model/precision;
- card retrieval vector dimensions equal the current supported Turbopuffer schema dimension `384`; no other retrieval dimension is eligible in this release;
- plan schema version is supported;
- ranking mode/profile/aggregation and pool are supported;
- persisted routing model/revision/hash/vector contract is valid.

Eligibility MUST run before lexical or semantic scoring. Disabled/incompatible cards MUST not contribute scores or appear in selected routes. Local diagnostics MAY report aggregate exclusion counts by reason; ordinary output MUST NOT dump vector values.

No ACL/group/freshness policy exists in this single-user release. Enabled state is the explicit local eligibility control. The router MUST NOT call remote namespace discovery or infer missing cards from IDs.

If no eligible card exists, routing MUST fail before credential lookup or Turbopuffer work and point to `buoy catalog list --all`, manual upsert, and compatibility settings.

## Routing algorithms

All strategies MUST use the same eligible cards and deterministic `repo_key` equivalent of namespace ID as the final tie-breaker.

### Canonical lexical routing

Normalize question and descriptors with Unicode NFKC, `casefold()`, maximal non-alphanumeric runs to one ASCII space, whitespace collapse, and trim.

Descriptors are the deduplicated non-empty normalized title, aliases, and tags. A descriptor contributes at most once when it occurs as a contiguous complete token phrase. Repeated query occurrences do not increase score.

Rank matched cards by:

1. descending distinct matched descriptor count;
2. descending sum of token lengths of matched descriptors;
3. ascending namespace ID.

Unmatched cards remain absent from the lexical list.

### Semantic routing

- Load the fixed pinned routing model with exact revision and `local_files_only=True`.
- Apply the documented BGE query prefix to the stripped non-empty query.
- Encode one normalized float32 query vector.
- Score eligible persisted card vectors by cosine similarity.
- Rank descending similarity, then ascending namespace ID.

The router MUST NOT re-embed cards during retrieval. A stale/incompatible card vector is a catalog validation failure, not a lazy repair.

### Hybrid route RRF

Fuse lexical and semantic namespace ranks with equal weight:

`score(namespace) = sum(1 / (RRF_K + one_based_rank))`

The implementation MUST import Buoy's existing `RRF_K` and fail tests if it is not 60. Only lists containing a namespace contribute. Sort descending fused score, then ascending namespace ID.

Truncate the final route to `route_top_k` before retrieval. Store and output only selected route entries in ordinary results; diagnostic JSON MAY include bounded top-ten strategy ranks without vectors.

## Local dry-run route preview

`buoy retrieve QUERY --auto-route` without `--live` MUST:

- validate arguments/query/catalog;
- load the local pinned routing model;
- perform eligibility and routing;
- print/return a route-aware retrieval plan for the selected namespaces;
- perform no credential read, Turbopuffer client construction, remote namespace listing, or remote query;
- perform no catalog or state mutation.

Text preview MUST show selected namespaces in route order, hybrid scores, catalog revision, eligible/excluded counts, retrieval model contract, and the existing per-namespace retrieval plans.

JSON preview MUST include:

- existing command/query/dry-run safety fields;
- `routing`: activation, strategy `hybrid_rrf`, catalog path/revision, route model/revision, requested limit, eligible count, exclusion counts, selected cards with namespace and lexical/semantic/hybrid rank/score components;
- ordered `namespaces`;
- per-namespace retrieval plans.

No vector values or credentials may appear.

## Live routed retrieval

`buoy retrieve QUERY --auto-route --live` MUST perform the identical local route first. Only after a non-empty selected route exists may it read `TURBOPUFFER_API_KEY` and construct live retrievers.

Live execution MUST:

- preserve selected route order as multi-namespace order;
- construct one `RuntimeConfig` per selected card using validated catalog retrieval contracts;
- start each selected namespace's options from its catalog ranking mode/profile/pool/aggregation;
- each explicitly supplied `--ranking-mode`, `--ranking-profile`, `--ranking-pool`, or `--ranking-aggregation` independently overrides only that field for every selected card; unsupplied ranking fields remain card-specific;
- existing `--candidates` and `--doc-kind` apply to every selected namespace, while `--top-k` remains the final global merged-hit limit;
- reuse `MultiNamespaceRetriever` query embedding, sequential namespace execution, namespace-qualified evidence identity, all-or-nothing failure, and `cross_namespace_rrf` exactly;
- apply existing global `--top-k` to final merged evidence;
- never query disabled, incompatible, unselected, or uncataloged namespaces.

Because eligibility requires one region/model/precision cohort, the existing embed-once multi-namespace contract remains valid.

An explicit routed invocation MUST return a routed multi-namespace result shape even if only one card is selected. This new shape prevents it from masquerading as an explicitly selected single-namespace result.

## Live and dry output

Routed JSON results MUST add the same `routing` object used by preview plus existing multi-namespace retrieval fields and hits. Every hit retains source namespace. Text output MUST print a concise routing header before existing citations.

Failure after routing begins MUST identify whether failure occurred in catalog load, route model load, route scoring, selected namespace preparation, or namespace retrieval. If any selected namespace fails, no partial result payload may be printed.

## Failure and fallback

The router MUST fail closed for:

- missing/corrupt catalog;
- no enabled compatible cards;
- missing local routing model;
- invalid vectors/hashes/contracts;
- non-finite semantic scores;
- empty selected route;
- any selected namespace retrieval failure.

It MUST NOT silently:

- fall back to `TURBOPUFFER_NAMESPACE`;
- query every visible namespace;
- drop a failed routed namespace and return partial results;
- substitute lexical-only routing when semantic routing fails;
- repair catalog state during retrieve;
- download or substitute a routing model.

The actionable fallback is an explicit `--namespace` invocation or local catalog repair.

## Observability and privacy

- Normal text logs MUST include selected namespace IDs and route ranks but not query vectors or card vectors.
- JSON includes the user-supplied query because existing retrieval output already does; it MUST not persist queries to catalog/state.
- No new telemetry, hosted logging, analytics, or background persistence is allowed.
- Errors for excluded cards SHOULD report aggregate reason counts, not entire disabled card contents.

## Acceptance scenarios

### Explicit behavior unchanged

Given one or more explicit namespaces without `--auto-route`, when retrieval runs, then no catalog/model routing path executes and existing output/retrieval semantics remain compatible.

### Dry preview

Given enabled compatible cards and a cached route model, when dry-run auto-route runs, then exactly the top three by default are planned locally with routing metadata and no credential or remote call.

### Environment replacement

Given `TURBOPUFFER_NAMESPACE` and CLI `--auto-route`, when routing runs, then the environment namespace is not selected implicitly and a warning explains the CLI override.

### Compatibility before relevance

Given an incompatible card with the strongest lexical/semantic match, when routing runs, then it is excluded before scoring and never appears in diagnostics as a scored route.

### Live route

Given three selected compatible cards, when live retrieval succeeds, then the query is embedded once for retrieval, namespaces run sequentially in route order, hits merge with existing namespace-qualified RRF, and routed metadata accompanies the result.

### Selected namespace failure

Given one routed namespace fails after another succeeds, when live retrieval runs, then the command fails naming the namespace and emits no partial result payload.

### Missing model

Given the pinned route model is absent locally, when preview or live auto-route starts, then it fails before credentials or Turbopuffer calls and does not download a model.

## Tests and verification

Focused tests MUST cover:

- CLI activation/conflicts, catalog-path precedence/empty values, environment replacement, stderr/JSON separation, and route-top-k bounds;
- explicit retrieval regression proving catalog code is not called;
- eligibility-before-score including disabled and high-score incompatible canaries;
- lexical normalization/phrase/frequency/ties;
- semantic vector validation/cosine/ties with injected embeddings;
- hybrid RRF, one-list membership, ties, and pre-retrieval truncation;
- dry-run no-credential/no-SDK/no-remote/no-write behavior;
- live selected order, embed once, fixed 384 retrieval dimension, mixed per-card ranking contracts with field-level CLI overrides, global candidates/doc-kind/top-k, existing downstream RRF, identity, and all-or-nothing failures with fakes;
- routed text/JSON safety and no vector leakage;
- missing/corrupt catalog/model fail-closed behavior;
- no model download/substitution.

Full tests and `git diff --check` MUST pass.

## Explicit exclusions

- automatic activation without `--auto-route`;
- routing over uncataloged remote IDs;
- remote catalog lookup/sync;
- ACL groups or multi-user permissions;
- concurrent namespace retrieval;
- partial-success retrieval;
- online learning, feedback persistence, or query logging;
- card repair during retrieval;
- taxonomy/chunk-tag filtering or boosting;
- query decomposition, graph, concept, or relationship traversal.
