Status: done
Created: 2026-06-20
Updated: 2026-06-20
Parent: .loom/tickets/2026-06-20-turbopuffer-jellyfish-rag-plan.md
Depends-On: .loom/specs/turbopuffer-jellyfish-rag.md, .loom/decisions/turbopuffer-jellyfish-rag-baseline.md

# Configure turbopuffer credentials and runtime settings

## Scope

Prepare runtime configuration for turbopuffer without persisting secrets in the repository.

In scope:

- Identify the Proton Pass item containing the turbopuffer API key.
- Retrieve the key only after user approval and only into the active shell/session environment.
- Establish environment variables:
  - `TURBOPUFFER_API_KEY`
  - `TURBOPUFFER_REGION`
  - `TURBOPUFFER_NAMESPACE`
- Document the chosen region/namespace in non-secret project docs if useful.

Out of scope:

- Committing API keys or generated `.env` files containing secrets.
- Calling turbopuffer write/query APIs beyond a minimal auth/config smoke check if explicitly approved.

## Acceptance criteria

- The implementation can read turbopuffer config from environment variables.
- No secret value is written to project files, Loom records, logs, or committed output.
- If Proton Pass is used, access is justified with `PROTON_PASS_AGENT_REASON` and follows the `proton-pass-agent` skill.
- The ticket progress log records only non-secret facts: item title/vault if acceptable, region, namespace, and whether config was verified.

## Progress and notes

- 2026-06-20: Ticket created only. API key was not accessed.
- Future executor should read `/Users/crlough/.pi/agent/skills/proton-pass-agent/SKILL.md` before any Proton Pass commands.
- 2026-06-20: User approved these future execution defaults: search accessible Proton Pass items for the turbopuffer credential, `TURBOPUFFER_REGION=gcp-us-central1`, and `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`.
- 2026-06-20: Activated for execution under `/loom-driver`.
- 2026-06-20: Verified `pass-cli` availability and authenticated an isolated Proton Pass session after the default session was absent.
- 2026-06-20: Searched accessible Proton Pass item metadata and found exactly one turbopuffer candidate: item title `<private turbopuffer credential item>` in the accessible vault. No secret fields were printed or written.
- 2026-06-20: Retrieved the `API Key` field from the `<private turbopuffer credential item>` item into shell memory only, using `PROTON_PASS_AGENT_REASON`; verified it was non-empty without exposing the value.
- 2026-06-20: Recorded runtime defaults: `TURBOPUFFER_REGION=gcp-us-central1` and `TURBOPUFFER_NAMESPACE=jellyfish-site-docs-v1`.
- 2026-06-20: Ran a non-mutating turbopuffer smoke check: `GET /v1/namespaces?page_size=1000` in region `gcp-us-central1` succeeded with the retrieved key. The first page contained 0 namespaces; `jellyfish-site-docs-v1` is not yet present, as expected before indexing/writes. Evidence: `.loom/evidence/2026-06-20-turbopuffer-config-verification.md`.
- 2026-06-20: No project `.env` was created and no indexing or turbopuffer writes were run.

## Blockers

- None.
