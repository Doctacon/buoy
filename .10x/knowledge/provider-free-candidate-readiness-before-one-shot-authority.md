Status: active
Created: 2026-08-25
Updated: 2026-08-25

# Provider-Free Candidate Readiness Before One-Shot Authority

## Purpose

One-shot build and live-command authority should constrain an already proven
mechanism, not serve as the first test of packaging or environment assumptions.
This knowledge guides future shaping; it does not activate a ticket, authorize a
build, or grant live access.

## Prove version and cache viability before one-build authority

When package versions are derived dynamically from VCS state, provider-free
preparation MUST prove that version discovery works with the exact source form
the authorized build will receive. A VCS-bearing clone proves only a VCS-bearing
clone. An explicit version override proves only that exact override. Neither
proves that a metadata-free detached export can derive its version without an
explicit, accepted version input.

The build MUST also be proven with an owned isolated UV cache that can supply the
exact pinned build backends while offline. Success through an established global
cache is not isolated-cache proof. A transient global-cache workspace that is
later absent does not prove cache-wide equality and cannot satisfy a no-global-
cache-touch boundary.

Both exact-source version discovery and isolated-cache viability MUST be proven
provider-free before granting one-build/no-rebuild authority. The proof must not
read credentials, construct a model, open telemetry, or access provider or
network behavior.

## Prepare and review the immutable candidate before live authority

One-shot live-command authority MUST begin only after provider-free preparation
has:

1. produced the complete candidate from the exact authorized source;
2. bound its immutable identities and retained those exact bytes;
3. completed isolated installation and all required provider-free validation;
4. reconciled owned cache and other permitted side effects within the approved
   boundary; and
5. passed independent review against that complete retained candidate and
   preparation evidence.

Build/preparation activation is not live GO. Candidate absence, preparation
failure, deleted candidate bytes, incomplete validation, unresolved side-effect
findings, drift, or a review that does not bind the complete immutable candidate
forbids live authorization.

## Incident application

The terminal provider-invocation receipt successor failure illustrates both
preconditions. The selected metadata-free export did not supply accepted VCS
version discovery, and the build used the established global offline cache
rather than a proven isolated cache. These are preparation/harness failures,
not evidence of a product defect. The governing evidence and independent review
are:

- `.10x/evidence/2026-08-25-provider-invocation-receipt-successor-preparation-failure.md`
- `.10x/reviews/2026-08-25-provider-invocation-receipt-successor-preparation-failure-review.md`

Any future attempt needs separately shaped owner authority. This knowledge does
not create a retry, rebuild, GO, credential/model/provider/network access, or
live-command entitlement.
