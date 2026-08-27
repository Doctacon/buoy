Status: active
Created: 2026-08-27
Updated: 2026-08-27
Amends: .10x/decisions/buoy-versions-repo-evals-and-gates-only-default-promotion.md

# Buoy Advances the Current Repo Eval for Test Layout

## Context

The approved concern-based test reorganization moves five paths referenced by immutable current repository-evaluation v2. Mutating v2 would violate versioned artifact immutability; retaining its paths as the active version would fail current path-membership validation; leaving those tests unmoved would make the requested layout partial.

On 2026-08-27 the owner selected a path-only v3 successor after this dependency was explained.

## Decision

Create repository-evaluation v3 as the active current successor to v2. V2 MUST remain byte-for-byte immutable. V3 MUST carry every query, case identity, judgment grade, reason, and non-path semantic forward unchanged, add exactly the five test-path mappings required by `.10x/specs/buoy-test-suite-layout.md`, and reference a new deterministic path-membership manifest.

V3 MUST remain `baseline_status=pending` and `promotion_eligible=false`; it makes no benchmark, corpus, or promotion claim. The production promotion-basket registry remains empty. No retrieval, model, provider, credential, namespace, catalog, release, publication, or deployment operation is authorized.

## Alternatives considered

- Mutate v2: rejected because versioned eval artifacts are immutable.
- Leave the reorganization blocked: rejected because a truthful successor can preserve semantics.
- Leave five tests at the root: rejected because it violates the complete concern-layout contract.

## Consequences

Current path validation advances to v3 without rewriting history or changing judgment meaning. Future current-path refactors must follow the same successor-version pattern when they affect active judgments.
