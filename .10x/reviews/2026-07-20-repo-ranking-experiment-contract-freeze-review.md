Status: recorded
Created: 2026-07-20
Updated: 2026-07-20
Target: PR #59 at commit `2d11a2ea89f8a70db1106506014a56855b091a57`
Verdict: pass

# Repo Ranking Experiment Contract Freeze Review

## Target and method

Independent adversarial review of PR #59 head `2d11a2e` against `origin/develop` at `fcb7abb` after PR #57. The review inspected the C1 ticket and parent graph, governing spec/decision, frozen evidence and JSON artifacts, validator implementation and tests, source/dataset hash preservation, diff hygiene, and hosted checks.

## Findings

- The checked-in inventory and standard-library validator agree on exactly 13 expected datasets, 90 unique composite `repo_key:case_id` identities, 370 unchanged judgments, 13 repository-held-out folds, and the frozen dataset/source bundle hashes. Dataset-local IDs remain unchanged and the known cross-repository duplicate local ID remains valid only through composite identity.
- The deterministic source-path bundle is sufficient clean-checkout authority without the ignored crawl artifacts. The validator exhaustively checks dataset hashes, schemas, identities, path membership, mapping crosswalks, fold assignments, namespace pattern, corpus hashes, baseline status, and sufficiency derivation.
- Click is correctly pinned to its compatible existing v4 commit/corpus and resolves all 36 judgments. Buoy alone is explicitly insufficient: 32 of 33 judgments resolve, the absent grade-1 path is internal `.10x` material intentionally excluded from the public corpus, and the exact proposed 903-row same-source baseline remains unapproved and unwritten.
- The contract cleanly separates the three-repository experiment-escalation gate from the active full-basket promotion policy. It makes neither gate promotion authority.
- Raw candidate/cache identity, required ANN/BM25/fused/default fields, model/corpus/namespace compatibility, canonical hashing, deterministic tolerances, request accounting, credential redaction, and missing-repository stop behavior are concrete enough for dependent consumers without creating a namespace.
- C7 material-weight/sign/order thresholds and C8 oracle-gap semantics remain explicitly unresolved and user-gated. C1 does not launder them into schema, tests, or executable acceptance.
- Focused tests cover clean regeneration, source-path sorting/distinctness, exact namespace/corpus field names, and standalone standard-library command execution. The full validator supplies the broader deterministic invariant coverage.
- The reviewed diff changes only the bounded contract records/artifacts, validator/tests, and CI invocation. It does not edit datasets, runtime ranking behavior, dependencies, credentials, models, namespaces, catalogs, or defaults. `git diff --check` passed.
- Hosted checks on reviewed head `2d11a2e` passed for Python 3.11, Python 3.13, and distribution build. GitHub reported PR #59 merge state `CLEAN` at review time.

### Blockers

None.

## Verdict

Pass. C1 may close with the exact outcome: **contract frozen; Buoy insufficient; C3+ remains blocked**. The insufficient Buoy state is a valid frozen outcome, not evidence that Buoy or the full basket is executable.

## Residual risk

- Buoy lacks a compatible populated same-source baseline and therefore cannot participate in the frozen 13-repository comparisons.
- The user's subsequent ratification to remove the one grade-1 internal `.10x` judgment is not part of reviewed head `2d11a2e`; it requires a separate follow-up owner, dataset edit, complete rehash, validation, and review. Until then, contract v1 remains unchanged and Buoy remains insufficient.
- Even after that future label removal, Buoy must remain insufficient until the separately approval-gated baseline exists and compatibility is verified.
- C7/C8 remain independently blocked on their pre-registered user-ratified thresholds. Final checks must pass again after adding this review and closure-only records.
