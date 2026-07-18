Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Target: commits `43b4bbb`, `2f3ee64`, `ba4b1da`, `6744bcc`, and `c0bc4b0`
Verdict: pass

# Remote Semantic Routing Shaping Review

## Findings and repairs

Initial reviewer/oracle audits confirmed Turbopuffer feasibility and user intent but rejected incomplete remote schema/CLI/recovery/rollout contracts. Repaired shaping now includes:

- exact active provider-neutral card semantics/hashes/golden vectors/generated metadata;
- exact Turbopuffer schema, hashed IDs, strong two-pass card and namespace-list stability, pagination, classification counts, request/billing/retry/timeout bounds, and conditional create/update/delete;
- complete authenticated public catalog CLI including exact `migrate-local` operator entrypoint;
- user-ratified permission/metadata exposure and managed-provider exception boundaries;
- apply preview, ledger-based confirmation promotion, safe rebase including first-apply manual race, exact-revision operator `accept-remote`, and no clock-causal ordering;
- inert backend followed by one mutation-frozen atomic CLI/apply/retrieval cutover, preventing split authority;
- exact migration preconditions/races and five-ID count fixture;
- deletion bound to the verified canonical file/hash/revisions with any lock appearance blocking deletion;
- cancellation of the unimplemented local-default ticket and coherent supersession/reference graph.

Final independent review passed with no blocker. The parent has exactly two sequential children; the backend child is cold-executable and changes no public behavior. Cutover remains dependency-blocked and owns all authorized live side effects.

## Verdict

Pass. `.10x/tickets/done/2026-07-18-build-remote-routing-backend.md` is executable. No runtime or remote mutation occurred during shaping.

## Residual risk

The remote provider's exact hosted behavior is validated initially through SDK contracts/fakes; the cutover ticket requires reviewed implementation plus fail-closed live preflight before the authorized two-card write. Automatic routing will depend on network/API availability and bill read-only control-plane queries by explicit user choice.
