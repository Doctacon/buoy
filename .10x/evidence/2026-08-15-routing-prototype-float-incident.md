# Routing prototype float incident evidence

Status: recorded

The first live `site-dagster-io-v1` routing-example write was conditioned on
card revision `1ef17d69...` and attempted exactly one card row.  No content,
schema, delete, or other-card operation occurred.  Verification failed and all
further example writes stopped.

Content-free read-only diagnostics established:

- intended pre-write vector hash: `01b0ba92...`;
- provider-returned raw vector hash: `37f0bbba...`;
- float32-canonical hash for both intended and returned vectors:
  `17dcbb4e...`;
- 348 of 384 returned coordinates were bit-exact to the intended Python value;
- maximum absolute delta: `2.7755575615628914e-17`;
- RMS delta: `2.065030887300181e-18`;
- base vector/hash, six examples, semantic prototype hash, and all other cards
  remained unchanged.

The current remote Dagster row is intentionally left fail-closed until this
reader/writer fix is reviewed and deployed.  Recovery will conditionally patch
only its prototype-vector hash and card revision, then perform exact readback.

## Source implementation validation

- `src/buoy_search/catalog.py` now uses one shared IEEE-754 binary32
  canonicalizer both when preparing non-empty prototypes and when validating
  persisted non-empty prototype rows.  Empty prototypes retain their exact
  legacy base-vector path.
- Regression coverage proves exact normalized-mean canonicalization,
  same-float32-bucket persisted and remote round trips, adjacent-bucket
  rejection, fail-closed pre-canonical rows followed by bounded hash/revision
  repair, and successful two-read conditional-update verification under
  provider decimal drift.
- The focused catalog, remote-catalog, catalog-operator, and apply-registration
  suites passed 90 tests under Python 3.11.5 and the same 90 tests under Python
  3.13.0.
- Python compilation, `git diff --check`, source-release validation, frozen
  ranking-contract validation, and the C6 forecast validator passed.
- No model, schema, dependency, provider, content, catalog, credential,
  activation, commit, push, or merge operation occurred.  The installed
  turbopuffer 2.8.0 versus locked 2.4.0 drift was not changed here: their
  relevant JSON and request-transform files are byte-identical, the live
  coordinate evidence independently proves the application float-identity
  seam, and dependency policy is outside this bounded recovery fix.

The complete 757-test suite passed locally under both Python 3.11.5 and Python
3.13.0.  Independent review passed with no blocker and confirmed that the only
source behavior change is the non-empty prototype-vector identity boundary;
schema-v1, empty prototypes, base vectors, schema, ranking, provider calls,
models, dependencies, and lockfiles remain unchanged.  Hosted CI remains the
integration gate.  Live recovery remains separately gated after deployment.
