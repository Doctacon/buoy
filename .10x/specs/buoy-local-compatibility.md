Status: active
Created: 2026-07-14
Updated: 2026-07-15

# Buoy Local Compatibility

## Purpose and scope

Preserve local state, old plans, and configuration through Buoy 0.3 without copying, moving, or silently splitting durable state.

## State-root resolution

For commands that use the implicit state-root default:

1. If `.buoy` exists and `.turbo-search` does not, use `.buoy`.
2. If neither exists, use `.buoy`.
3. If `.turbo-search` exists and `.buoy` does not, use `.turbo-search` in place and emit a concise deprecation warning to stderr.
4. If both exist, fail before planning, embedding, local-state mutation, or remote calls. The error MUST identify both paths and require an explicit `--state-root` choice.
5. An explicit `--state-root` always wins and MUST bypass implicit fallback logic.

No command may automatically copy, move, merge, or delete either root. JSON stdout remains clean; warnings use stderr.

## Existing artifacts and remote identity

- Existing schema-supported plans that record `.turbo-search` paths MUST continue to preflight/apply when the resolved or explicit root matches.
- Artifact hashes MUST NOT change merely because the product was renamed.
- Existing DuckDB schemas and rows MUST remain readable without rewriting identity fields.
- Deterministic row IDs, namespace names, remote rows, and state history MUST NOT be renamed or re-upserted solely for branding.
- `.gitignore` and repository-source exclusions MUST recognize both `.buoy` and `.turbo-search` during the transition.

## Environment configuration

- New branded variables use `BUOY_*`; current vendor variables `TURBOPUFFER_API_KEY`, `TURBOPUFFER_REGION`, and `TURBOPUFFER_NAMESPACE` remain unchanged.
- `BUOY_EMBEDDING_MODEL` replaces `TURBO_SEARCH_EMBEDDING_MODEL`.
- Through 0.3, an old branded variable is accepted only when the corresponding new variable is absent and emits a deprecation warning.
- If old and new variables are both set to different values, configuration MUST fail with a user-friendly conflict error rather than silently choosing an embedding profile.
- Version 0.4 is the announced removal target for old branded environment aliases. State-root fallback removal is not implied; any future state migration requires a separate decision and migration contract.

## Verification

Tests MUST cover all state-root cases, explicit override, warning/JSON separation, old-plan preflight, no filesystem copy/move, environment fallback/conflict behavior, and unchanged row/namespace identities. No live remote operation is required.
