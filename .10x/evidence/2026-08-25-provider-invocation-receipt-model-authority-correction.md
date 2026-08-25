Status: recorded
Created: 2026-08-25
Updated: 2026-08-25
Relates-To: .10x/decisions/one-time-provider-invocation-receipt-final-recovery-model-authority-correction.md, .10x/decisions/superseded/one-time-provider-invocation-receipt-final-recovery.md, .10x/evidence/2026-08-25-provider-invocation-receipt-final-recovery-candidate-repair.md, .10x/tickets/2026-08-25-prepare-provider-invocation-receipt-final-recovery-candidate.md, .10x/tickets/2026-08-25-run-provider-invocation-receipt-final-recovery-live-command.md

# Provider Invocation Receipt Model Authority Correction

## What was observed

The prior candidate NO-GO correctly compared the exact unchanged source and
retained candidate with the then-governing live ticket. That ticket permitted
construction of only `BAAI/bge-small-en-v1.5`, while provider-free static source
inspection proved that the unchanged ordinary automatic path can also construct
the pinned local MiniLM cross-encoder. The NO-GO therefore correctly forbade
PASS/GO and live execution under the flawed one-model authority.

The NO-GO's classification of that mismatch as an exact-candidate product defect
is superseded by stronger product authority:

- `.10x/specs/automatic-multi-corpus-retrieval.md` requires the exact pinned
  MiniLM model for bounded multi-namespace reranking and fallback;
- `.10x/specs/scalable-routing-quality.md` and
  `.10x/specs/bounded-prototype-routing-activation.md` require the same exact
  MiniLM model for active descriptor-free automatic routing;
- `.10x/specs/automatic-retrieval-evidence-abstention.md` requires the same
  exact MiniLM model for automatic evidence assessment and score reuse;
- the active bounded-routing and evidence decisions preserve those production
  behaviors; and
- exact `src/buoy_search/cross_encoder.py`, `src/buoy_search/routing.py`, and
  `src/buoy_search/retriever.py` implement those required paths. Routing loads
  the reranker for descriptor-free prototype selection; retrieval loads or
  reuses it for multi-corpus reranking/fallback; evidence assessment loads it
  when exact existing cross-encoder scores are unavailable.

The owner authorized the unchanged ordinary automatic command. No owner
instruction authorized removing, disabling, bypassing, or substituting its
production reranker. The one-model restriction was therefore a governing-record
defect, not a product defect.

## Corrected authority boundary

Only these two record-backed local models may be constructed or reused by the
future unchanged ordinary automatic command, and only where its production
routing/retrieval behavior requires them:

1. `BAAI/bge-small-en-v1.5` at revision
   `5c38ec7c405ec4b44b94cc5a9bb96e735b38267a`, float32, with unchanged
   production automatic-device behavior; and
2. `cross-encoder/ms-marco-MiniLM-L-6-v2` at revision
   `c5ee24cb16019beea0893ab7796b1df96625c6b8`, CPU-only, local-files-only,
   safetensors-only, remote code disabled, max-length 512, and batch 8.

Both use exact local cache assets under offline/no-download controls. No other
model, download, or substitution is authorized.

## What this supports or challenges

This supports superseding the flawed one-model decision, returning the candidate
ticket to `Status: active` under its existing repeatable provider-free
activation, and retaining the exact source, wheel, runtime, and candidate. It
requires a provider-free exact cache/ref/assets inspection for both models and
corrected harness guards without constructing either model. It also requires a
fresh independent candidate PASS/GO before the live child can become eligible.

This challenges only the repair evidence's product-defect classification and
the old decision/ticket model boundary. It does not challenge the repair's
static reachability findings, exact evidence-gate repair, retained hashes,
prohibited-access observations, or NO-GO against the then-current ticket.

## Procedure and limits

This correction was established only by reading active records and the three
exact source files named above. The immutable candidate preparation and repair
evidence were not edited. No source, specification, test, lock, routing artifact,
or dataset changed. No model/cache was operationally accessed; no model was
imported, constructed, loaded, or run; no build, credential read, telemetry,
provider/network, retrieval, GO, or live operation occurred.

This record does not prove current cache readiness, corrected retained-harness
identity, candidate PASS/GO, live eligibility, provider behavior, receipt
acceptance, physical wire sends, SDK retries, billing, cost, or rate-limit
effects. Those remain subject to the corrected decision and sequential tickets.
