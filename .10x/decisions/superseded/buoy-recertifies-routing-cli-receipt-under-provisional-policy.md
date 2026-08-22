Status: superseded
Created: 2026-08-21
Updated: 2026-08-22
Superseded-By: .10x/decisions/buoy-recertifies-final-reviewed-cli-receipt.md
Supersedes: .10x/decisions/superseded/buoy-recertifies-routing-cli-for-command-telemetry.md
Amends: .10x/decisions/buoy-records-command-and-pipeline-retrieve-latency.md, .10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md

# Buoy Recertifies the CLI Receipt under the Provisional Routing Policy

## Context

Command telemetry changes `src/buoy_search/cli.py`, whose exact raw bytes are
bound by the packaged routing-confidence artifact. The first candidate
correctly failed closed against the old CLI receipt. The owner initially chose
the disclosed full dormant 65-case recertification path, and final production
source was committed with the exact collect-only artifact at
`369c5d461f616e89df492b497175312f36b5dcc9`, tree
`ba5c3933d835e5b9d2c7f3664f4847721e880c78`.

The live collector then stopped before inference and before report publication
because `site-docs-aurelio-ai-v1` is a live content namespace without a routing
card. It made the stable catalog reads only: two namespace-list pages, one
metadata request, and two catalog-query pages. It made zero query/reranker
inferences, content queries, content-resource acquisitions, provider writes,
or model downloads. No report exists and the artifact remains collect-only.

This is not newly discovered product corruption. The missing card was recorded
and independently reviewed during the 2026-08-16 catalog-v3 migration as a
real, intentionally unregistered coverage gap distinct from the eligible
`site-www-aurelio-ai-v1` card. That migration granted no registration or
backfill authority.

More importantly, the later active decision
`.10x/decisions/buoy-derives-routing-prototypes-from-reviewed-plans.md` and its
active specification
`.10x/specs/automatic-routing-after-apply.md` amend the original bounded-
routing activation contract. Missing-card live namespaces are diagnostics,
not a global availability stop. Any valid catalog drift produces provisional
top-three routing while the frozen seven-namespace certified anchor alone
retains singleton threshold authority. That implementation revised exact
routing/CLI source receipts through local source, package, installed-byte,
behavior, and independent review gates without replacing the frozen original
65-case report.

Creating a card merely to satisfy the older evaluator would require unratified
title, summary, aliases, tags, source semantics, enabled state, examples,
passages, vectors, and operational ownership. It would also mutate the live
candidate catalog and could change routing behavior. A missing card is not
permission to invent it.

After this conflict and the newer active authority were explained, the owner
selected “Re-certify CLI locally.”

## Decision

Buoy will preserve the existing schema-v3 active routing artifact's frozen
certified anchor, thresholds, original authorization report, dormant report,
suite, projection, calibration, certification, evaluator, routing, and
evidence receipts. It will reactivate command telemetry by replacing only the
artifact's `cli_module_sha256` with the measured SHA-256 of the exact final
instrumented `src/buoy_search/cli.py` bytes.

This local receipt recertification MUST prove:

- production source is byte-identical to clean dormant commit `369c5d4` after
  the stopped collector;
- the changed CLI bytes affect telemetry observation only and preserve routing
  validation order, catalog calls, model calls, selection, fanout, evidence,
  provider/content behavior, output, errors, and explicit bypass behavior;
- the strict loader rejects the old receipt and accepts only the exact new
  measured receipt;
- source, wheel, source distribution, and isolated installed package reproduce
  the same CLI receipt and exact active artifact bytes;
- the active artifact retains exact schema 3, revision
  `active-anchor-e559a8aa-v1`, the seven certified namespaces, provisional
  policy `certified-exact-otherwise-provisional-v1`, and every non-CLI field
  byte/semantically unchanged;
- focused automatic-routing, routing-quality, command-telemetry, privacy,
  failure-isolation, full supported-runtime, build, installed-package, source,
  ranking, and diff gates pass; and
- an independent exact-commit review confirms the receipt change does not
  launder a routing-semantic change.

No new 65-case report is claimed. The stopped live attempt remains evidence of
a correct drift gate and contributes no routing-quality result. No card is
created, updated, enabled, disabled, or deleted. `site-docs-aurelio-ai-v1`
remains an explicit missing-card diagnostic outside the certified anchor and
outside automatic candidates.

## Alternatives considered

### Backfill the missing card and rerun 65 cases

Rejected. No record or source provides the exact card semantics, and the owner
chose not to authorize a provider write. Inventing a card to unblock a source
receipt would conflate telemetry delivery with live catalog design and change
the routing candidate set.

### Remove the complete-coverage gate and rerun against current live cards

Rejected. That would alter the evaluator and likely the catalog projection and
65-case observations, requiring a new routing-quality contract rather than a
CLI-only receipt recertification. The current task changes no routing semantic.

### Keep the collect-only artifact

Rejected. It would leave automatic routing on the legacy collect path and make
the completed command telemetry source unavailable under the active production
routing authority.

### Replace the hash without package and behavior proof

Rejected. A bare hash edit would bypass the purpose of the source receipt.

## Consequences

The final branch can reactivate the already-approved schema-v3 routing policy
without provider mutation or a fabricated quality report. The frozen anchor
continues to own calibrated singleton authority; current valid drift remains
provisional exactly as before. The known missing card remains visible and
unmanaged.

The earlier decision requiring a new live dormant report is superseded because
it failed to account for the newer active provisional-routing amendment. Its
stopped attempt and reasoning remain historical evidence, not current execution
authority.

This decision authorizes only the local artifact receipt update, deterministic
validation, isolated package builds/installs, evidence, and independent review.
It authorizes no provider/card/content/schema write, credential retrieval,
further live certification run, installed-tool replacement, branch
integration, `main`, release, tag, deployment, or publication.
