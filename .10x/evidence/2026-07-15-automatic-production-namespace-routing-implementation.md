Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Relates-To: .10x/tickets/done/2026-07-15-add-automatic-production-namespace-routing.md, .10x/specs/automatic-production-namespace-routing.md

# Automatic Production Namespace Routing Implementation Evidence

## What was observed

The `work/add-automatic-production-namespace-routing` implementation adds opt-in `retrieve --auto-route` without changing the explicit retrieval path. Automatic routing resolves the canonical local catalog, fully validates it, applies enabled and runtime compatibility gates before relevance scoring, embeds one prefixed routing query with the pinned local-only model, combines exact lexical and persisted-vector semantic ranks with the existing `RRF_K=60`, and truncates the selected route before retrieval.

Dry routed previews return an explicit multi-namespace plan even for one card and include catalog/model/revision, eligibility/exclusion counts, ordered selected-card lexical/semantic/hybrid components, and per-card retrieval plans without persisted vector values. Live routed retrieval constructs validated per-card runtime/ranking options, preserves route order, and hands the route to the existing sequential `MultiNamespaceRetriever` and namespace-qualified `cross_namespace_rrf` path.

Focused fake/sentinel tests cover:

- activation conflicts, route-only flag rejection, top-k bounds, catalog CLI/environment precedence, whitespace rejection, environment namespace replacement on stderr, explicit retrieval avoiding catalog/model routing, and preservation of explicit missing-namespace-before-empty-query error precedence;
- enabled/region/model/precision eligibility before scoring, lexical normalization/phrase/frequency/ties, persisted-vector cosine ranks, query-vector validation, equal-weight `RRF_K=60` fusion, one-list contribution, deterministic ties, and pre-retrieval truncation;
- default top-three dry preview, no credential read, no SDK/retriever construction, no remote discovery, no catalog write, pinned query prefix, explicit routed one-card shape, output redaction, and credential-read sentinels proving missing/corrupt catalog and missing route model failures occur before `TURBOPUFFER_API_KEY` lookup;
- live route order, one retrieval embedding, fixed 384-number ANN query vector, mixed per-card ranking contracts, independent field overrides, global candidates/doc-kind/top-k, existing cross-namespace RRF/identity, and no partial stdout after a selected namespace failure.

## Procedure

From the task worktree at develop base `ac6a3ca`:

```text
uv run python -m unittest tests.test_automatic_routing tests.test_retriever tests.test_multi_namespace_retrieval tests.test_catalog tests.test_catalog_cli tests.test_cli
...........................................................................................................Warning: could not remove plan artifact directory under state root: <temporary>/state
.................
----------------------------------------------------------------------
Ran 125 tests in 3.299s

OK
```

```text
uv run python -m unittest discover -s tests -p 'test_*.py'
....................................................................................................................................................................Warning: could not remove plan artifact directory under state root: <temporary>/state
......................................................................................................................................................................................................
----------------------------------------------------------------------
Ran 363 tests in 7.296s

OK
```

```text
uv run python -m compileall -q src tests
# no output; exit 0
```

```text
git diff --check
# no output; exit 0
```

No validation command made a live Turbopuffer call or read a real credential. Live coverage used injected routing/retrieval models and namespace fakes. Credential-read sentinels cover both dry preview safety and the live-request early failures for missing/corrupt catalogs and a missing route model.

## Review corrections

The two minor review findings were applied without widening scope:

1. Explicit retrieval again resolves its namespace selection before validating an empty query, preserving the pre-feature error precedence. Auto-route continues to validate its query before catalog/model work because it intentionally has no explicit namespace-selection requirement.
2. Missing catalog, corrupt catalog, and missing route-model live invocations now have direct credential-read sentinel coverage proving each fails before any `TURBOPUFFER_API_KEY` lookup.

## What this supports

This supports the ticket acceptance claims for opt-in activation, local catalog authority/path behavior, compatibility-before-score, deterministic lexical/semantic/hybrid routing, default/overridden fan-out, dry local safety, route-order handoff, per-card/global retrieval controls, namespace-qualified downstream RRF, explicit routed output, redaction, and all-or-nothing failure behavior.

## Limits

- No live Turbopuffer service was contacted, so SDK/network behavior remains covered by existing integration boundaries and injected fakes rather than an external call.
- The pinned routing model was injected in focused tests; constructor revision and `local_files_only=True` remain independently covered by `tests.test_catalog`.
- This evidence is implementation evidence, not independent review. The ticket remains active pending the required reviewer gate.
