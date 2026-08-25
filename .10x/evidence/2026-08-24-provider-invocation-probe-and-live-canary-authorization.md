Status: recorded
Created: 2026-08-24
Updated: 2026-08-24
Relates-To: .10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md, .10x/decisions/one-time-live-provider-invocation-receipt-canary.md, .10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md, .10x/tickets/done/2026-08-24-implement-private-provider-invocation-receipts.md, .10x/evidence/2026-08-24-provider-client-invocation-receipt-authorization.md
Review: .10x/reviews/2026-08-24-provider-invocation-execution-activation-review.md

# Provider-Free Probe and One-Time Live Receipt Canary Authorization

## What was observed

The owner explicitly authorized two separate future operations in the current
workstream and directed this turn to record them durably without executing
either operation. The first approval removes the existing provider-free probe's
model/cache/sequence/evidence blockers. The second approval creates a distinct
one-time live automatic-retrieval canary authority gated behind completed,
independently reviewed fake-only receipt integration.

The records-only candidate is based on exact `develop` commit
`dd0e155d26af6b0cfbc9872606c5861e0d3b4306`, tree
`f9edc5cbaa76d342239901d99f75013846c6e278`. Read-only source inspection bound
these exact governing source SHA-256 identities:

- `pyproject.toml`:
  `f80f4c53b5a6e1fe15e79abf31b40cdf529336a28144cec085ef1c7749861c22`;
- `uv.lock`:
  `ad7508159bc00271b21fc598bad07b56045329c938ed4fbd37a5a18d71c4c254`;
- `src/buoy_search/config.py`:
  `b33407002f60c6ca3429e05043f2c1451902112bf793ce2ae2ed0ae9e4da5620`;
- `src/buoy_search/chunker.py`:
  `98a036fa829cbec675b5fd04cc1dd717a0ccc04c417a25ea33433827cec908d8`;
- `src/buoy_search/retriever.py`:
  `de9e7118c3222b2f8e56a68cbc8cf600d372c1a0728d6525654e35e87646f64c`;
- `src/buoy_search/cli.py`:
  `90e7b2ddf7bbde2daaf0ccd78aa2a779d9e61946a8b7f7ae8f3512dec431ebf9`;
  and
- `src/buoy_search/remote_catalog.py`:
  `9980208230c4743322447b32db75844cfdd2bcb6fc33abda0153d751db8048f1`.

Source shows that production explicit construction loads
`SentenceTransformerEmbedder` before namespace/retriever construction, uses
model `BAAI/bge-small-en-v1.5`, float32 by default, and lets
sentence-transformers select the device automatically. Existing tests establish
fake/injected provider seams. The active receipt specifications define the
private in-process terminal receipt and exact application-boundary attempt
unit. Historical real-store canary/pilot evidence supplies proven privacy,
cache-manifest, credential-source, telemetry-store-identity, no-retry, and
cleanup procedures but grants no surviving execution authority.

## Exact owner approval: provider-free probe

The owner ratified this exact contract:

> model BAAI/bge-small-en-v1.5 revision
> 5c38ec7c405ec4b44b94cc5a9bb96e735b38267a, float32 and production
> auto-device behavior; one discarded fresh-process warm-up followed by five
> retained fresh-process observations; independently time sentence-transformers
> import, local model construction, and fake-provider/retriever/config
> construction without summing nested spans; 120-second elapsed and
> 4,294,967,296-byte child RSS hard limits per process with immediate abort;
> offline/no-download/no-real-credential/no-provider/no-network; current locked
> runtime/source and a fake/injected provider; cache/ref/full-manifest identity
> before and after with any mutation a failure; no OS/model cache clearing;
> temporary harness/raw logs outside repo and deleted after sanitized evidence;
> only content-free component timings and bound runtime/host/model/cache
> identities retained. Define exact failure/no-retry rules, privacy, cleanup,
> validation/review, exclusions, and Blockers None. This user approval removes
> the old blocker but does not execute the probe in this records-only turn.

That approval is implemented as the executable but inactive open research
ticket
`.10x/tickets/2026-08-24-measure-provider-free-retriever-construction.md`.

## Exact owner approval: one-time live receipt canary

The owner separately ratified this exact contract:

> only after fake-only implementation/integration passes independent review;
> build/use an isolated exact candidate wheel (no global install/release);
> exactly one no-retry automatic live retrieval via the private in-process
> receipt harness using the existing credential source and current remote
> catalog; telemetry disabled and real telemetry store untouched; exact cached
> model above, float32 production auto-device, offline/no download/cache
> mutation; provider reads only and no provider/catalog/content writes; receipt
> acceptance budgets at most catalog 5 and content 18
> provider_client_invocation attempts; budgets are post-operation sanitized
> receipt acceptance gates rather than claims about wire sends and cannot be
> inferred if receipt is missing; missing/invalid/over-budget/interrupted/error
> receipt fails with no retry; preserve original command outcome truthfully;
> retain indefinitely only canonical validated sanitized receipt plus bounded
> evidence; delete query/argv/namespace/content/result/credential/path/raw-output/
> harness/runtime artifacts; credential value never printed/persisted; no
> telemetry-v2 change, migration, global install, release, deployment, retry,
> or transport/billing/rate-limit claim. Include pre/post cache and
> telemetry-store identity, process/external side-effect inventory, cleanup,
> exact receipt validation, review, and no-unrelated-mutation requirements.
> This ticket remains open/inactive and may not execute in the same turn it is
> created.

That approval is implemented by
`.10x/decisions/one-time-live-provider-invocation-receipt-canary.md` and
`.10x/tickets/2026-08-24-run-one-time-live-provider-invocation-receipt-canary.md`.
The previously owner-approved automatic case
`m01-dagster-turbopuffer-quality`, loaded privately from the digest-bound
`automatic-multi-corpus-retrieval-v1` dataset, is the record-backed input seam;
no literal query or namespace is duplicated here.

## Authorized records-only scope for this turn

Authorized now:

- update the blocked probe into an open, fully executable, inactive research
  ticket with `Blockers: None`;
- create this focused authorization evidence;
- create one focused one-time live-canary decision and one bounded open/inactive
  ticket;
- update the existing implementation parent and four children only for exact
  authorization references and truthful dependency/activation sequence; and
- perform read-only Git/source/record inspection, records-only validation, and
  commit the bounded `.10x` candidate.

Not authorized now:

- activation or execution of either operation;
- source/test/specification/review edits;
- model/provider/network/credential/catalog/content operation;
- telemetry/store/database operation or migration;
- build, test, wheel, install, release, deployment, global-tool, hosted, or ref
  operation; or
- creation of probe/canary harnesses, raw logs, runtime artifacts, receipts, or
  operational evidence.

## What this supports

This evidence supports the exact future operational authority and removes only
the provider-free ticket's prior blockers. It supports the one-time canary
decision/ticket after their fake-only reviewed-integration dependency is
satisfied and the ticket is separately activated. It also establishes that the
receipt implementation core is the next eligible source child, while no source
child is activated in this records-only turn.

## Limits

This record does not prove implementation, independent review of implementation,
probe execution, canary execution, provider calls, receipt validity, cache/store
identity, cleanup, command success, physical transport sends, billing, or
rate-limit use. Validator and canary acceptance counts are application-boundary
receipt gates only. Missing receipt remains unknown. Previous canary/pilot
operational authority is consumed and historical; this record does not renew it.

## Independent activation review

Independent review passed exact authorization candidate
`21f6a7b21d950f086ac6dfd7ab4f633883d6e066`, tree
`4d044b44d492757dad80466968809aebdb76f161`, with no blocker, significant,
minor, or privacy finding. The review establishes record-contract coherence
only. No probe, implementation child, or canary was activated or executed.
