Status: active
Created: 2026-08-22
Updated: 2026-08-22
Supersedes: .10x/decisions/superseded/buoy-recertifies-routing-cli-receipt-under-provisional-policy.md
Amends: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md, .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md

# Buoy Recertifies the Final Reviewed Command-Telemetry CLI Receipt

## Context

The owner selected local CLI-receipt recertification under the active
provisional-routing policy, with no missing-card backfill or further live
collector run. Candidate `40ef5f74` correctly restored the exact schema-v3
active artifact and changed only its CLI receipt to the then-current command-
telemetry source hash.

Three independent reviews then found bounded command-telemetry defects,
including a broken-stderr compatibility regression in `cli.py`. The reviews
failed the candidate before closure. Repairing an accepted source defect must
not be prohibited merely because the prior decision named the pre-review
dormant commit as final; doing so would freeze a known failing candidate or
encourage a stale receipt.

## Decision

The local recertification authority applies to the final independently reviewed
command-telemetry source, not specifically to pre-review commit `369c5d4`.
That commit and receipt remain historical checkpoints.

Accepted review repairs MAY change command-telemetry source and tests within
`.10x/reviews/2026-08-22-retrieve-command-pipeline-telemetry-review.md`. After
each source repair, the implementation MUST:

1. measure the new exact `src/buoy_search/cli.py` SHA-256;
2. restore the pre-instrumentation schema-v3 active artifact and change exactly
   `receipts.cli_module_sha256` to that measured value;
3. prove every other parsed artifact field and text line unchanged;
4. rerun source, behavior, privacy/failure, dual-runtime, wheel, source-
   distribution, installed-package, and strict old/new receipt validation; and
5. obtain fresh independent exact-commit review before closure.

Every routing semantic remains frozen: schema/revision, seven-namespace anchor,
provisional policy, thresholds, reports, suite, projection, evaluator, routing,
evidence, and collect receipt. No card, catalog, provider, content, credential,
model, or live evaluator operation is authorized. The known Aurelio docs
missing card remains diagnostic and unmanaged.

## Alternatives considered

### Keep the pre-review CLI receipt

Rejected. It would bind an artifact to source with a known broken-stream
regression and would fail once the defect was repaired.

### Waive the review defect to preserve source identity

Rejected. Source receipts are safety evidence, not authority to retain a known
behavior violation.

### Repeat live certification or backfill the missing card

Rejected for the same reasons in the superseded decision: current provisional
routing makes the missing card nonblocking, no exact card semantics are
ratified, and the command telemetry repair changes no routing behavior.

## Consequences

The artifact hash may advance once more as review-required CLI repairs land,
but only to measured final bytes and only after exact non-CLI equality and
package validation. Previous candidate hashes remain evidence history and are
not active authority.

This decision grants no scope beyond accepted review repairs and local receipt
validation. It grants no integration, installed-tool replacement, `main`,
release, deployment, tag, provider mutation, or publication.
