Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: semantic metadata/tagging/catalog/graph workstream through `develop` commit `78f2c0f1866383ef6eb4d74c44e81e594b33f873`
Verdict: concerns

# Holistic Semantic Routing Workstream Review

## Target

Review the complete direction from the user's original questions about Turbopuffer chunk metadata, tagging, many namespaces, concepts/relationships, and knowledge graphs through the current research, Data Vault scope correction, active specifications, pilot plan, and existing Buoy code.

Reviewed targets at the time of review:

- `.10x/decisions/data-vault-is-analogy-not-architecture.md`
- `.10x/tickets/done/2026-07-15-semantic-retrieval-research-plan.md`
- `.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md`
- `.10x/specs/superseded/controlled-taxonomy-pilot.md`
- `.10x/specs/superseded/semantic-namespace-catalog-pilot.md`
- `.10x/specs/superseded/offline-semantic-routing-evaluation.md`
- `.10x/tickets/cancelled/2026-07-15-build-controlled-taxonomy-fixture.md`

Local implementation inspected:

- `src/buoy_search/namespaces.py`
- `src/buoy_search/retriever.py`
- `src/buoy_search/chunker.py`
- `src/buoy_search/plan_artifacts.py`
- `src/buoy_search/evals.py`
- `src/buoy_search/autoresearch.py`
- `tests/test_multi_namespace_retrieval.py`
- `docs/retrieval.md`
- active namespace discovery, multi-namespace retrieval, and eval/autoresearch specifications

## Executive assessment

The **problem and strategic direction still make sense**:

- Turbopuffer already supports per-chunk attributes, and Buoy already stores structural tags and strong source metadata.
- Buoy can only discover namespace IDs and requires explicit namespace selection. At large namespace counts, semantic catalog/routing is a real missing capability.
- Controlled metadata should be tested before concept graphs, and graphs should be justified only by residual multi-hop/global retrieval gaps.
- The Data Vault correction was necessary and correct.

However, the **current five-child synthetic pilot should not be executed unchanged if the goal is to improve the codebase**. It is explicitly designed to produce deterministic plumbing evidence, not evidence that routing improves real retrieval. It also has no ratified product consumer. Implementing it now risks adding a generic taxonomy/catalog/evaluator framework that is correct in isolation but unused and unvalidated against the problem that motivated it.

Strategic direction: **pass**. Current implementation plan: **concerns; rescope before execution**.

## Findings

### Significant — The planned pilot cannot establish the improvement the user is asking about

The parent and evaluator explicitly limit the result to “deterministic plumbing evidence” (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:9-12,57-62`; `.10x/specs/superseded/offline-semantic-routing-evaluation.md:7-11,154-168`). All cards, vectors, labels, ACLs, and cached evidence are synthetic and repository-visible.

That can prove validation, determinism, ACL gating, and rank-fusion compatibility. It cannot show that semantic namespace cards select the right real namespaces, improve real evidence recall, reduce operator effort, or improve answer quality. Therefore completing all five children would not support the claim “this improves Buoy”; it would support only “the new framework behaves as designed on data designed for it.”

**Required before implementation:** restate the first outcome as either:

1. a deliberately throwaway plumbing prototype with no production-module commitment; or
2. a value experiment over representative real/public namespace cards and reviewed queries.

Do not call the synthetic run a routing-value pilot.

### Significant — No product integration boundary consumes the proposed taxonomy/catalog code

Current behavior is concrete:

- namespace discovery is identifier-only (`.10x/specs/turbopuffer-namespace-discovery.md:10-24`; `src/buoy_search/namespaces.py:8-31`);
- multi-namespace retrieval requires an explicit ordered set (`.10x/specs/explicit-multi-namespace-retrieval.md:8-24`; `docs/retrieval.md:58-72`);
- current runtime cannot infer per-namespace model settings (`docs/retrieval.md:50-54,70-72`).

The new specs intentionally exclude CLI/API behavior, live namespace registration, production persistence, and catalog synchronization. Consequently the open taxonomy ticket can add source code before any user-facing or internal production path needs it.

A standalone normalization/taxonomy subsystem is not automatically an improvement. Without a named consumer, it is speculative framework code.

**Required before production-shaped implementation:** identify the eventual integration seam—local plan/apply registration, a read-only catalog command, automatic retrieve routing, or another explicit surface. The first experiment need not implement that seam, but its code should not masquerade as a reusable production subsystem until the seam is chosen.

### Significant — The five-ticket process is disproportionate for synthetic plumbing

The plan serializes taxonomy, catalog, evaluator, fixture freeze, and execution into five separately integrated children (`.10x/tickets/cancelled/2026-07-15-semantic-routing-offline-pilot-plan.md:43-59`). The freeze exists to protect held-out discipline, while the governing spec simultaneously states that visible synthetic labels cannot establish real quality (`.10x/specs/superseded/offline-semantic-routing-evaluation.md:154-168`).

The freeze is rigorous but adds little information to a synthetic plumbing check. Unit tests plus a canonical fixture already establish determinism. A separate preregistration/freeze becomes valuable when representative judgments or real model/card choices can be tuned—not before.

**Recommendation:** collapse the first slice to one bounded experimental implementation plus independent review. Add a separate freeze/run pair only for a later representative quality dataset.

### Significant — The plan risks duplicating existing evaluation infrastructure

Buoy already has:

- deterministic eval dataset loading and scoring in `src/buoy_search/evals.py`;
- a one-shot fixture/live-safe experiment runner that writes plan/result/report artifacts in `src/buoy_search/autoresearch.py:279-402`;
- source-mutation/live-write safety validation in `src/buoy_search/autoresearch.py:253-274`;
- exact namespace-qualified downstream RRF in `src/buoy_search/retriever.py:504-524`;
- extensive eval/autoresearch and multi-namespace tests.

The new plan correctly requires reuse of `cross_namespace_rrf`, but it does not require reuse or extension of the existing fixture runner/reporting path. A parallel catalog-specific runner, case schema, output writer, and report renderer would increase maintenance burden in an already substantial retrieval/eval surface (`retriever.py`, `evals.py`, and `autoresearch.py` total more than 2,500 lines).

**Recommendation:** the implementation plan should prefer a narrowly extended experiment mode or shared low-level helpers. Do not force semantic routing into repository-search scoring types, but do reuse one-shot safety, artifact writing, and established RRF rather than creating a second framework.

### Significant — The most immediate “tagging” defect remains unresolved

Buoy stores `tags: []string` (`src/buoy_search/chunker.py:57-70`; `src/buoy_search/plan_artifacts.py:444-482`), while retrieval does not request or expose them and the documentation says it does (`docs/retrieval.md:54`). The drift is correctly owned by `.10x/tickets/2026-07-15-reconcile-retrieval-tag-output.md`.

The taxonomy pilot intentionally avoids public tag behavior. That separation is safe, but it means the first implementation does not improve the currently observable tagging surface.

This is not an argument to rush tag filters. It is a sequencing warning: before a production taxonomy is considered, the project must decide whether tags are output metadata, query filters, ranking signals, or internal-only fields.

### Correct — Semantic namespace routing addresses a real architectural gap

At large namespace counts, explicit operator selection does not scale. Turbopuffer queries remain namespace-local, namespace listing exposes IDs rather than semantics, and Buoy does not maintain per-namespace embedding/retrieval contracts. A catalog that gates authorization/compatibility before semantic ranking is a coherent solution.

The research recommendation of a canonical local catalog plus disposable semantic cards is appropriately reversible. It does not require a graph database or managed catalog service.

### Correct — The workstream now follows a sensible complexity ladder

The current direction correctly orders the options:

1. exact metadata/taxonomy;
2. semantic namespace-card routing;
3. hybrid routing;
4. query decomposition/iteration for residual multi-hop cases;
5. concepts/reified assertions;
6. graph storage/traversal only after measured need.

This is substantially better than starting with a knowledge graph. Provenance, deletion, ACL, and namespace-qualified citations are treated as safety invariants rather than optional polish.

### Correct — Data Vault removal improved coherence

`.10x/decisions/data-vault-is-analogy-not-architecture.md` prevents warehouse terminology from becoming implementation scope. Stable concept identity, typed relationships, versioned observations, and provenance remain useful ideas without hubs/links/satellites or Data Vault loading.

## Recommended smallest path

### Phase 1 — One bounded experiment, not a framework

Before executing the current taxonomy ticket, reshape the first slice to:

- use a small set of representative public/project namespace cards and reviewed questions rather than vectors designed solely for acceptance tests;
- compare explicit/oracle selection, simple lexical tags, semantic cards, and hybrid routing;
- reuse `cross_namespace_rrf` and the safe one-shot experiment/reporting mechanics where practical;
- keep code in an explicitly experimental boundary until a product integration seam is ratified;
- retain deterministic ACL/compatibility canaries, but omit a separate synthetic held-out freeze;
- produce results that clearly distinguish plumbing assertions from representative routing evidence.

No live Turbopuffer write is needed. Read-only live validation is optional and separately authorizable later.

### Phase 2 — Decide whether production code is justified

Only if representative routing evidence shows useful namespace recall/fan-out/downstream evidence behavior:

- specify how namespaces are registered and updated;
- choose the product interface that consumes the catalog;
- resolve tag output/filtering behavior;
- define real access/freshness/lifecycle semantics;
- then implement the smallest production path.

### Phase 3 — Concepts/graph only for a residual measured gap

Do not build concept or graph infrastructure unless metadata/card routing and decomposition fail on named entity-centric, multi-hop, temporal, or global cases and an oracle graph demonstrates a useful ceiling.

## Verdict

**Concerns.** The user's overall idea is coherent and targets a real limitation in Buoy. The research and scope correction improved architectural understanding. A semantic namespace catalog could materially improve usability when many namespaces exist.

But the current executable plan is too framework-heavy and too synthetic to justify codebase growth. Running it unchanged is more likely to add well-tested experimental abstractions than to improve the product. Reshape the first slice around representative routing evidence and explicit reuse of existing evaluation infrastructure before implementing the taxonomy ticket.

## Residual risk

- Without representative namespace cards and reviewed queries, semantic-routing value remains unknown.
- Without a named product integration seam, even a successful experiment can become orphaned code.
- Real ACLs, model compatibility, freshness, deletion, latency, and cost remain untested.
- Existing retrieval/tag documentation drift remains unresolved under its blocked ticket.
- Knowledge-graph value remains hypothetical and should stay deferred.
