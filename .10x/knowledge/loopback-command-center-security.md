Status: active
Created: 2026-07-23
Updated: 2026-07-23

# Loopback Command Center Security Boundary

A loopback bind is not sufficient protection for a credential-capable local web UI. Browser requests can still be induced cross-site, and DNS rebinding can target localhost services.

Buoy command-center rules:

- Accept only explicit loopback bind hosts and validate the HTTP `Host` header.
- Keep same-origin deployment and do not enable permissive CORS.
- Guard every provider-capable POST with a non-simple project-owned request header and same-origin request checks; a bodyless POST alone is forgeable by a cross-origin form.
- Remote/provider/model activity occurs only after an explicit guarded request, never startup or local browsing.
- Sanitized activity fields must distinguish pre-call failures from failures after a provider call or response.
- Citation sanitizers are scheme-specific contracts, not generic URL allowlists. HTTP(S) drops query/fragment data; local document and database schemes accept only their canonical persisted, bounded one-segment shapes.
- Local artifact APIs expose stable IDs and indexes, never arbitrary paths, and reject symlink escapes.

Regression tests should include hostile Host, cross-origin/simple POST, pre-call and post-call failures, tokenized URLs/fragments, private path-shaped internal URIs, and canonical generated citations.
