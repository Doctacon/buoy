Status: recorded
Created: 2026-07-23
Updated: 2026-07-23
Target: work/harden-database-relation-adapters uncommitted diff
Verdict: pass

# Database relation adapter hardening review

## Findings

Independent review found no critical, significant, or minor issues.

The review verified that BigQuery now uses one exact read-only query, one uncapped dry run, Buoy-side estimate/cap comparison before execution, and one actual job with the provider cap and existing timeout/cancellation safeguards. The query preserves global ID and duplicate validation, accurate counts, deterministic bounded documents, and read-only behavior.

Shared bounded validation rejects null/blank/duplicate converted IDs and null/blank content while preserving valid complex IDs and title fallback. Both cloud adapters invoke it inside backend-safe error wrapping. BigQuery and Snowflake selected-document SQL requires valid IDs and nonblank content.

Snowflake keeps short tags unchanged and bounds oversized tags to 2,000 characters with a deterministic full SHA-256 suffix. CLI help and indexing documentation accurately describe shared database caps and cloud cost/mutation behavior. Source identities, stable filenames, lazy imports, apply isolation, catalog/ranking, and DuckDB behavior remain unchanged.

## Verdict

Pass. Acceptance criteria are supported by source inspection, focused regression tests, 609-test full discovery, validators, locked dependency resolution, optional-extra resolution, and successful packaging.

## Residual risk

Cloud tests are fake-backed by requirement. Provider SQL execution and optimizer behavior were not live-verified. Snowflake's multiple statements do not provide snapshot isolation, though invalid selected rows are blocked before materialization. No follow-up is required absent a separately ratified live integration or snapshot-consistency requirement.
