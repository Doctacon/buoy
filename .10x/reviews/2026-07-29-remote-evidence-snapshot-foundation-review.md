Status: recorded
Created: 2026-07-29
Updated: 2026-07-29
Target: work/remote-evidence-snapshot-foundation diff from 606c168389e28b09105e8eb139f2cde063994a83
Verdict: concerns

# Remote Evidence Snapshot Foundation Review History

## Target

The Phase 3A implementation, tests, documentation, specification/research/ticket graph, and packaging changes on `work/remote-evidence-snapshot-foundation`.

## Initial implementation self-review

The implementation writer initially recorded a pass after provider-free tests. That verdict was not independent and is superseded by the two independent reviews below. It missed official SDK model serialization, catalog-authentication, cleanup-concurrency, and bounded-memory gaps.

## Independent review findings

Two fresh-context reviews of commit `cf37f5fff20cc05ffe561cbf3010165e779e74eb` returned **fail**. Their retained reports during repair were `/tmp/remote-evidence-correctness-review.md` and `/tmp/remote-evidence-validation-review.md`.

### Critical findings

1. SDK 2.4.0 metadata `to_dict()` preserves `datetime` objects; catalog JSON serialization failed after branch/ledger creation.
2. Cleanup marked resources on ambiguous exceptions and could delete a preexisting, concurrent, or newly completed deterministic namespace.

### Significant findings

3. Remote-only verification trusted catalog source-state hashes instead of recomputing them from ordered ledger rows.
4. Catalog branch names, plan/apply IDs, card revisions, approximate bytes, and other logical metadata were not coherently authenticated.
5. Ledger writes were row-bounded but not byte-bounded below the provider's 512 MiB request limit.
6. Ledger verification retained an O(total rows) ID set despite ordered pagination already detecting duplicate/out-of-order IDs.
7. Branch metadata was not checked again after ledger verification immediately before catalog finalization.
8. Internal `buoy-evidence-` identities could still appear through local Command Center inventory and combined remote rows.
9. Completed-snapshot reuse reported writes that did not occur and omitted verification reads from returned metrics.
10. An explicitly supplied missing manifest was silently treated as no manifest.

### Minor finding

11. CLI snapshot/verify output and package-focused acceptance evidence was thinner than claimed.

## Repair disposition

All supported findings were addressed in the follow-up diff:

- `_plain()` normalizes provider datetime values to ISO 8601 strings; an SDK-shaped metadata test reaches completed catalog publication.
- Branches are marked created only after a definite successful branch response. The ledger's first batch is conditional insert-if-absent, exact affected IDs prove ownership, and transport/count ambiguity is separately reported. Because deterministic names can be reused by another host without a remote lease, Phase 3A now conservatively retains and reports definite/possible incomplete resources rather than issuing an unsafe automatic delete. Completed or uncertain catalog state always suppresses cleanup.
- The catalog stores the full safe deterministic source-identity payload. Verification recomputes each ordered source fingerprint and status counts from the ledger, checks site/ledger/branch/ordinal/document identity, binds plan/apply/card/embedding/schema metadata back to the snapshot-ID digest, enforces deterministic branch/ledger names, reconciles branch observations, and recomputes both snapshot and manifest hashes.
- Ledger requests are capped at 1,000 rows and 16 MiB of canonical encoded payload. The full-ledger hash no longer retains a global ID set; ordered pagination is the duplicate/order authority.
- Every branch's parent and metadata are checked again after ledger verification and immediately before catalog publication.
- Local inventory, local-ID collection, and combined remote status rows all exclude the reserved prefix; focused local and remote Command Center tests cover this.
- Reuse performs zero writes, reports `internal_evidence_writes_occurred=false`, includes verification metrics in the same accumulator, writes only the local manifest, and preserves the completed snapshot's original manifest hash.
- Explicit missing manifests fail. CLI tests now cover snapshot text and verify JSON paths. Distribution archive contents are independently inspected during final validation.

## First independent re-review

A fresh correctness re-review of commit `89a01bd7e23323d7e84088f5d504bf9a69b659fc` confirmed the prior six correctness repairs, then returned **fail** for two remaining findings:

1. Installed SDK 2.4.0 declares `updated_at`, not `last_write_at`, so accepting an absent write marker let later writes evade metadata drift detection.
2. Conservative retention after catalog-finalization failure left an exact deterministic ledger that an identical retry rejected permanently.

## Second repair disposition

The follow-up repair now canonicalizes branch write drift from official `last_write_at` when available or SDK-documented `updated_at` as fallback, fails closed when neither exists, and uses the same observation in reconciliation, final pre-publication checks, and remote verification. SDK-shaped regressions cover fallback drift and missing-marker failure.

An existing deterministic ledger is reused only after exact schema validation, full ordered ledger hash/status scan, deterministic snapshot/source/branch/document identity, per-source site/count/fingerprint comparison to the locked local state, and complete branch reconciliation. Partial and altered ledgers fail without writes or deletion. A catalog-failure retry regression proves branch/ledger reuse and successful finalization.

## Final independent re-review and repair

Fresh reviews of commit `5a3a7c81c4f88b806897449465ff78e01d10a426` confirmed the prior repairs. The validation review passed with one minor package-regression concern. The correctness review found one final blocker: a newly written ledger received only hash/status validation before completion, so a provider-side mutation after an acknowledged write could be incorporated into a complete catalog row; a reused ledger had the same mutation window after its initial exact collision check.

The final repair replaces the pre-publication hash/status-only pass with a complete exact validation for both paths. Immediately before catalog publication, it re-reads the ledger, validates deterministic row/source/branch/site/ordinal identity, recomputes each per-source fingerprint and counts against the locked local fingerprints, and reconciles each source branch against that ledger. The final branch metadata comparison remains after this exact pass. Focused regressions mutate `page_hash` after a new ledger write is acknowledged and `plan_id` after a reused ledger's initial validation; both now fail before any catalog row is written.

No archive-building test was added to the normal suite. Existing release-test conventions inspect package configuration and release artifacts without running a nested repository build; adding `uv build` to ordinary unit discovery would create repository artifacts and materially slow every suite run. The provider-free manual `uv build` plus exact wheel/sdist inventory remains an independently repeated, non-blocking validation limit: 72 wheel entries and 168 sdist entries, all evidence modules/docs/tests present where required, and no state/snapshot/node_modules content.

## Current verdict

**Concerns addressed; final repair implemented and validated; independent final acceptance remains with the parent.** This history does not self-ratify the final repair. The owning ticket remains open for fresh acceptance review and closure decision.

## Residual risk

- No opt-in live smoke was authorized; provider permissions and live response behavior remain unobserved.
- Strong consistency and metadata timestamp fidelity retain the provider's documented operational limits.
- Remote catalog rows are authoritative and not cryptographically signed; verification detects incoherent mutation and branch drift but cannot defend against a privileged actor coherently rewriting all authoritative remote metadata and content.
- Conservative failure handling can leave reported internal resources. No deletion or garbage-collection lifecycle is introduced in this phase.
- Scale RSS includes the in-process fake provider's retained branch/ledger state, not only Buoy's bounded buffers.
