Status: superseded
Created: 2026-08-27
Updated: 2026-08-27

# Buoy Migrates Frozen Repository-Eval Paths with the Subpackage Layout

## Context

The approved subpackage migration removed flat source paths referenced by the frozen Buoy repository-search evaluation dataset. Ten path-existence checks now fail even though judgment meaning is unchanged. Leaving the old strings would make the dataset point to nonexistent files; restoring duplicate compatibility modules was explicitly rejected.

On 2026-08-27 the owner approved a narrow evaluation-contract path migration limited to moved path strings, matching fixture candidate paths, and mechanically derived integrity hashes. Judgment labels, grades, reasons, queries, case identities, and ranking semantics remain frozen.

## Decision

Buoy MAY replace only repository path strings that name modules moved by `.10x/specs/buoy-search-subpackage-layout.md` in:

- `src/buoy_search/data/buoy_search_repo_search_seed_evals.json`; and
- test/evaluation fixtures whose candidate paths must match those judgments.

The migration MAY update only integrity hashes mechanically derived from that dataset or its bundle. Execution MUST prove that all non-path judgment content is unchanged, every migrated path exists, old moved paths are absent from the active dataset/fixtures, and all derived hashes exactly reproduce from the migrated bytes.

The migration MUST NOT add, remove, relabel, regrade, or reinterpret judgments; change queries, case IDs, reasons, scores, thresholds, folds, source corpus identity, namespace identity, or ranking behavior; regenerate candidates; invoke retrieval/providers/models; or alter unrelated datasets.

After the path migration, the full ranking-contract validation, autoresearch tests, complete repository suite, package validation, and independent review MUST pass before related tickets close.

## Alternatives considered

### Keep nonexistent frozen paths

Rejected because the active dataset would no longer truthfully identify judged source files and its path-integrity checks would remain broken.

### Restore files at old paths

Rejected because compatibility copies violate the owner-selected breaking cleanup and create duplicate module authority.

### Rebuild the evaluation corpus

Rejected because no judgment or corpus-semantic change is required or authorized.

## Consequences

The dataset and bundle hashes will advance solely because source locations changed. Prior hashes remain historical evidence. Judgment semantics and ranking acceptance remain unchanged.
