# Routing prototype float canonicalization review

Status: pass

Independent review found no blocker in the bounded incident fix.

The sole source change is in `src/buoy_search/catalog.py`.  One shared
IEEE-754 big-endian binary32 round trip is applied only to non-empty routing
prototype vectors at preparation and persisted-parse boundaries, before the
prototype-vector hash and card revision are computed or checked.  Empty and
schema-v1 prototypes remain on the exact legacy base-vector path.  Base routing
vectors are unchanged.

Regression coverage proves that provider decimals in the same float32 bucket
restore the exact intended card, an adjacent bucket fails closed, the live
pre-canonical failure shape can be repaired by its hash and revision, and both
post-write verification reads accept harmless decimal drift.  Existing base
card revisions, empty bundles, integer vectors, and v1/v2 round trips remain
green.

Independent focused validation passed 90 tests under Python 3.11.5 and the same
90 tests under Python 3.13.0.  Parent closure then passed the complete 757-test
suite under each version, source validation, frozen ranking-contract
validation, the intentionally blocked C6 forecast validator, compilation, and
diff checks.

There is no routing selection, remote schema, model, dependency, lockfile,
content, provider-call, or activation change.  No provider operation was made
by implementation or review.  The separate live Dagster two-scalar recovery
remains unauthorized until this exact fix is integrated and deployed.
