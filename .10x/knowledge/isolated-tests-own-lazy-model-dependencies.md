Status: active
Created: 2026-08-23
Updated: 2026-08-23

# Isolated tests own lazy model dependencies

## Rule

A test that claims to use local fakes MUST inject every lazily loaded model or
provider component on the exercised path. Passing on a developer machine is not
evidence that the test is model-free: a default lazy loader may silently use a
model already present in the user's cache.

Run model-free acceptance tests with a fresh isolated `HOME` and offline model
settings. A cache-miss failure under that environment is evidence of an
uninjected dependency, not permission to read the user's cache or download the
model.

## Buoy example

`MultiNamespaceRetriever` loads its reranker only when fanout requires it. A
privacy test constructed fake embedders and namespaces but omitted
`reranker_loader`; it passed on a host with the pinned cross-encoder cached and
failed under an isolated home. Injecting the existing ordinal fake made the test
deterministic while preserving the real entrypoint, worker-context, queue,
writer, store, and privacy boundaries.

## Validation pattern

1. Use a mode-0700 temporary home and isolated cache paths.
2. Set dependency tooling to offline/frozen operation.
3. Exercise the exact path that triggers lazy loading, not a shortened mock.
4. Assert the intended fake's call/result behavior.
5. Confirm no real telemetry home, provider, model cache, or network state was
   read or created.
