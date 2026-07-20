Status: recorded
Created: 2026-07-19
Updated: 2026-07-19
Target: PR #55 at commit `66a27b6cf4160f191b0a41a18c4931c911c3a1e9`
Verdict: pass

# Retrieval Tag Output Shaping Review

## Target and method

Independent adversarial review of PR #55's record-only shaping commit against its parent `5647cc6f08eeaf6319ac53f62b1bf136d0a67d80`, the ratified output-only direction, current retrieval source and tests, the active multi-namespace contract, and affected `.10x` references and statuses.

## Findings

- `.10x/specs/retrieval-tag-output.md` limits tags to additive per-hit output metadata. It explicitly excludes filtering, ranking effects, derivation, taxonomy/governance, schema mutation, migration, backfill, and live operations.
- JSON presence, conditional text rendering, stored order/value preservation, representative-hit behavior, and identical single-, explicit-multi-, and automatic-multi-namespace semantics are concrete and testable.
- Old-schema portability treats `tags` and `repo_path` as independently optional, bounds retries to necessary attribute variants, applies each variant consistently across ANN/BM25 subqueries, scopes fallback per namespace, and preserves failure for unrelated errors and the existing no-partial-results contract.
- `.10x/tickets/done/2026-07-19-return-retrieval-tags.md` is a bounded executable child with focused tests, full validation, documentation, evidence, review, no-live-operation, and explicit-exclusion requirements sufficient for cold-start implementation without widening into tag filtering or governance.
- The shaping parent satisfies its acceptance criteria and closes only the product-decision/specification slice. Its retrospective captures the reusable separation between output and filtering and the independent optional-attribute portability rule. Implementation remains open under the child ticket.
- Historical and active references consistently distinguish the terminal shaping owner from the open implementation owner. The obsolete active shaping-ticket path has no remaining literal reference.
- The reviewed commit changes only `.10x/` records. It does not change source, tests, user documentation, dependencies, data, remote state, or product behavior. Diff hygiene passed.
- Hosted CI passed on the reviewed head for Python 3.11, Python 3.13, and distribution builds.

### Blockers

None.

## Verdict

Pass. The ratified retrieval-tag output behavior is regeneration-grade, the shaping closure is supported, and the separately owned executable child is ready for implementation only after this record-only PR integrates. This review does not authorize implementation on PR #55.

## Residual risk

- Current source still does not return tags, and current documentation remains ahead of runtime behavior until the executable child is implemented, validated, independently reviewed, and integrated.
- Provider missing-attribute message matching and successive fallback call sequences require focused deterministic implementation tests; this review proves the contract and ticket are adequate, not that runtime behavior exists.
- Final PR checks must pass again after this review record and current `develop` are added to the branch.
