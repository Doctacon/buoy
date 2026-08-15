# Canonicalize routing prototype floats

Status: done

## Problem

The first approved schema-v2 routing-example update wrote one Dagster row, but
post-write verification failed.  The provider returned the non-ANN prototype
vector with harmless IEEE-754 last-bit changes, while its hash and card revision
had been computed from the pre-write Python floats.  The exact remote reader
therefore rejected the row and automatic routing failed closed.

## Scope

- canonicalize non-empty routing prototype vectors through IEEE-754 float32
  before hashing and card-revision calculation;
- apply the same canonicalization at the remote read boundary;
- preserve legacy base-vector, schema-v1, and empty-prototype behavior exactly;
- add regression coverage for provider round-trip drift;
- record the incident evidence and independent review.

No schema, routing selection, confidence, content retrieval, model, example,
canary, provider, or activation change is authorized by this ticket.  Live
Dagster recovery remains a separate conditional, independently reviewed
operation after this fix is integrated and deployed.

## Acceptance

- mathematically equivalent prototype values within one float32 bucket parse to
  one stable hash and card revision;
- preparation writes canonical float32 prototype coordinates for non-empty
  examples;
- legacy golden cards and empty bundles remain byte-compatible;
- full source validation and Python 3.11/3.13 tests pass;
- independent review records PASS before integration.
