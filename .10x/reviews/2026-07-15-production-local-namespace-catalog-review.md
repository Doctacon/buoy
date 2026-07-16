Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `f8a89ddf4cf98ef175bc6b09664bbc2b05c31132` and `e13d3e1`
Verdict: pass

# Production Local Namespace Catalog Review

## Target

Independent review of the production catalog core, CLI, tests, documentation, evidence, and active ticket against `.10x/specs/production-local-namespace-catalog.md`.

## Findings and resolution

Initial review found significant gaps in persisted lineage invariants, exact-integer JSON validation, and source-URI validation, plus minor gaps around malformed source metadata, fsync verification, credential-read sentinels, catalog recovery guidance, and documentation.

Corrective commit `e13d3e1` resolved them:

- persisted generated cards require plan/apply lineage and manual cards require paired or null lineage;
- prospective non-persistable generated cards are separated from strict persisted parsing;
- schema, plan schema, vector dimensions, pools, and other integer fields reject booleans/floats;
- non-string source kinds fail closed;
- URI validation is source-kind-aware and rejects whitespace, malformed host/port, unsupported schemes, and contradictions before model load;
- atomic persistence tests cover file and best-effort directory fsync;
- credential sentinels detect reads, not only remote calls;
- ambiguous state-root catalog errors direct users to `--catalog`;
- catalog documentation correctly retains environment namespace retrieval.

Two fresh re-reviewers reported pass with no blocker.

## Correct

- Golden semantic/vector hashes reproduce the active specification.
- Catalog/card hashes, strict unknown-field loading, vector finiteness/dimension/norm/hash checks, pinned revision, and local-only model construction are correct.
- Canonical ordering, non-blocking lock, atomic replacement, and prior-byte preservation are covered.
- Manual upsert and apply-facing merge preserve lineage/manual semantics/enabled/vector state correctly.
- List/show hide vectors by default; enable/disable are idempotent; remove previews and mutates only with approval.
- CLI/environment/default path precedence and stderr/JSON separation are correct.
- Explicit retrieval remains independent of catalog state.
- No apply registration, reconcile/abandon wiring, automatic routing, remote call, credential use, dependency, ACL, taxonomy, or graph was introduced.
- Thirty-seven focused and 329 full-suite tests, compilation, and `git diff --check` passed.

## Verdict

Pass. No unresolved significant finding remains.

## Residual risk

- Catalog authority is local/single-user and is not remote namespace existence proof.
- Card vector generation requires the exact model revision to exist locally.
- Apply registration and automatic routing remain owned by their sequential child tickets.
