Status: open
Created: 2026-07-20
Updated: 2026-07-20
Parent: .10x/tickets/2026-06-28-repo-search-heavy-ranking-experiments.md
Depends-On: .10x/tickets/done/2026-07-19-freeze-repo-ranking-experiment-contract.md, .10x/tickets/done/2026-07-20-remove-buoy-internal-ranking-judgment.md

# Implement Fail-Closed Experimental Buoy Baseline Executor

## Outcome

Implement and test the smallest isolated executor that exactly satisfies `.10x/specs/experimental-buoy-baseline-executor.md`. This ticket authorizes source and focused test changes only. It does not authorize reading a credential, loading or invoking a model, contacting Turbopuffer, or mutating namespace, catalog, pending, or DuckDB applied state during implementation or validation.

## Scope

- Add one explicitly experimental, non-default executor path for only the immutable Buoy baseline operation defined by the active specification. Do not route ordinary `apply`, retrieval, catalog, or public defaults through it.
- Reuse existing verified-plan, embedding-text, schema, card, pending, lock, and DuckDB state primitives where they preserve the contract; isolate stricter provider request interception/accounting and commit ordering rather than weakening shared production behavior.
- Validate every exact region/plan/artifact/source/model/cache/README/license/row/namespace/card/local-state value and all 903 unique intended row IDs before credential access. Set both offline environment controls before model import/construction.
- Construct every locked `turbopuffer==2.4.0` client with `max_retries=0` and reject any path that cannot prove SDK/wrapper retries, fallbacks, pagination, and repeated calls are disabled.
- Enforce the specification's exact preflight target/catalog reads, 15 fixed content batches, response/accounting contract, bounded target/card post-write reads, 26-attempt global ledger, per-operation ceilings, 904 write-row-position ceiling, 1,817 returned-row-position ceiling, and zero-delete invariant.
- Enforce exact response checks and commit order: no catalog mutation or local applied-state commit after content mismatch; no local commit/card-success claim after catalog mismatch; preserve the pending record and partial/indeterminate accounting; remove pending only after exact target and card verification plus local commit.
- Emit a secret-free evidence artifact that maps all 26 slots to attempted or unused and contains the exact accounting fields required by the active specification.
- Add deterministic focused tests using injected fakes and temporary local state only. Tests MUST NOT import/load/invoke the real embedding model, read `TURBOPUFFER_API_KEY`, construct a real provider client, make network calls, or touch the retained `/tmp` plan/state.

## Acceptance criteria

- Exact input/cache/license/ledger validation occurs before credential access, provider-client construction, or model construction and fails closed on every mismatch.
- All provider resources are mechanically attested `max_retries=0`; no retry, signature/schema fallback, pagination, cleanup delete, rollback delete, repeated call, or unused-slot reassignment is possible.
- The only allowed operation sequence and ceilings are encoded exactly: target metadata/optional empty probe; catalog metadata/two exact-card reads; `14 × 64 + 1 × 7` content upserts; target metadata/two `top_k=904` reads; at most one conditional card upsert; two `top_k=2` exact-card reads; 26 attempts, 904 write-row positions, 1,817 returned-row positions, and zero deletes.
- Accounting is appended before every fake physical attempt and finalized for success, failure, timeout, malformed response, and indeterminate outcome with exact/present markers for `rows_affected` and redacted billing, plus request/operation numbering and cumulative counters.
- Focused tests prove abort-before-write on ambiguous/non-empty/incompatible preflight; abort-before-card/local-commit on any content response or target verification mismatch; abort-before-local-commit/card-success on any card response or verification mismatch; exact success ordering; stable repeated-read requirements; pending retention on every partial failure; pending removal only after final verified commit; and secret/raw-request redaction.
- Successful simulated verification requires exactly 903 intended IDs and attributes, no 904th row, stable order, finite normalized-shape-compatible 384-dimensional vectors, exact schema/cosine distance, and one complete stable expected card revision.
- The evidence format maps every possible slot to attempted or unused, reports dollar cost as unknown absent authoritative pricing, and cannot claim success unless every contract invariant passes.
- Focused tests, the full existing test suite, static/type/lint checks used by the repository, and `git diff --check` pass. Independent implementation review records PASS before this ticket can close or Approval A can become eligible.

## Stop conditions

- Stop implementation and return to shaping if the locked SDK cannot expose or mechanically guarantee `max_retries=0`, bounded direct operations, exact response fields, or a no-pagination/no-fallback path without changing the ratified contract.
- Stop if current primitives cannot preserve the exact plan/card/pending/DuckDB commit order without widening the operation or weakening ordinary behavior.
- Do not simulate success by relaxing missing `rows_affected`, billing-presence markers, exact row/card comparisons, stable repeated reads, or any physical-attempt counter.
- Do not run the executor against retained artifacts or real local/remote state. Approval A is ungranted.

## Explicit exclusions

Any live execution; credential access; real model import/load/inference; provider or other network call; namespace/card/catalog/pending/DuckDB mutation outside temporary test directories; source corpus, dataset, judgment, default, dependency, or lockfile change; ordinary apply/retrieval behavior change; recrawl/replan; another namespace/card; delete; C3 retrieval; Approval A or B; promotion.

## Evidence expectations

Focused and full-test output; static inspection proving `max_retries=0` and no fallback/pagination/delete path; fake-call sequence and exact attempt-slot ledger for success and each failure phase; precondition-before-credential/model/provider proof; response-accounting/redaction fixtures; target/card stable-read and local-commit ordering evidence; changed-file/diff hygiene; independent review; explicit no-live/no-model/no-domain-write statement.

## References

- `.10x/specs/experimental-buoy-baseline-executor.md`
- `.10x/reviews/2026-07-20-experimental-buoy-baseline-executor-spec-review.md`
- `.10x/evidence/2026-07-20-experimental-buoy-baseline-executor-ratification.md`
- `.10x/evidence/2026-07-20-c3-buoy-baseline-approval-checkpoint.md`
- `.10x/tickets/2026-07-19-capture-current-repo-candidates-and-baselines.md`

## Blockers

None for bounded source/test implementation. Approval A remains ungranted and blocks every real credential/model/provider/domain-state operation. Approval B and C3 remain separately blocked.

## Progress and notes

- 2026-07-20: Opened after the user ratified the independently reviewed PR #65 specification unchanged. No source/test implementation, credential read, model operation, provider call, or namespace/card/catalog/pending/DuckDB mutation occurred in this record turn. Approval A and Approval B remain ungranted; C3 remains blocked.
