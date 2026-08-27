Status: superseded
Created: 2026-08-27
Updated: 2026-08-27
Supersedes: .10x/decisions/superseded/buoy-migrates-frozen-repo-eval-paths-with-subpackage-layout.md

# Buoy Refreshes Repository-Eval Corpus Identity for the Subpackage Layout

## Context

The superseded path-only migration decision proved insufficient. The ranking validator requires every judged path to belong to `.10x/evidence/.storage/2026-07-20-repo-ranking-source-path-manifests.json`, whose selected paths are bound to a historical source commit and corpus artifact hash. Replacing paths while retaining that identity would create false provenance. The earlier decision correctly prohibited that inconsistency and execution stopped before mutating evaluation-contract files.

On 2026-08-27 the owner selected an honest corpus-identity refresh for the reorganized source. The intent remains structural: preserve all evaluation judgments while advancing the source manifest and mechanically derived identities to describe the actual post-migration files.

## Decision

Buoy MAY refresh the Buoy repository-evaluation source-manifest entry against the current reorganized source and assign the resulting truthful source/corpus identity. Execution MAY update:

- moved judged path strings in `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`;
- matching candidate paths in test/evaluation fixtures;
- the Buoy entry in `.10x/evidence/.storage/2026-07-20-repo-ranking-source-path-manifests.json`, including selected paths and exact source/corpus identities required to make that entry truthful; and
- dataset, manifest, inventory, or bundle hashes mechanically derived from those authorized bytes.

Execution MUST use deterministic local inspection only. It MUST prove that judgment queries, IDs, labels, grades, reasons, and all other non-path semantics are unchanged; that the refreshed manifest describes the current files and exact bytes; and that every derived identity reproduces.

No retrieval, embedding, reranking, model, provider, namespace, catalog, credential, or live operation is authorized. No judgment may be added, removed, relabeled, regraded, or reinterpreted. No non-Buoy corpus manifest or unrelated dataset may change.

Focused ranking-contract/autoresearch validation, the full repository suite, package validation, and independent review MUST pass before closure.

## Alternatives considered

### Rewrite paths while retaining the old corpus identity

Rejected as historically inconsistent and false provenance.

### Preserve the historical contract unchanged

Rejected because its active judged paths no longer exist after the approved package migration.

### Re-run retrieval or rebuild judgments

Rejected because the structural relocation does not authorize or require semantic evaluation changes.

## Consequences

The Buoy corpus/source identity and its derived hashes will advance to truthfully represent the reorganized tree. Historical identities remain preserved in prior evidence and the superseded decision. Judgment semantics remain frozen.
