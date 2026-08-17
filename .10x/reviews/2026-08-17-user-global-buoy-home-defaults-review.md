Status: pending
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/2026-08-17-default-local-assets-to-user-home.md
Evidence: .10x/evidence/2026-08-17-user-global-buoy-home-defaults.md
Decision: .10x/decisions/buoy-defaults-local-assets-to-one-user-home.md
Specification: .10x/specs/user-global-buoy-home-defaults.md

# User-Global Buoy Home Defaults Review

Independent review is pending the settled implementation and validation
evidence.

The review must challenge:

- every remaining implicit working-directory path in source, help, docs, and
  tests;
- home-boundary permissions and symlink/non-directory behavior;
- exact precedence and compatibility for explicit legacy paths;
- multi-candidate implicit apply failure ordering;
- canonical managed-plan cleanup containment, symlink/race resistance, and
  preservation of the state subtree and all noncanonical/historical assets;
- consistency between cleanup tests and the explicit portable threat boundary,
  without claiming atomic child-entry compare-and-unlink against an actively
  malicious same-UID actor;
- source/namespace/row/artifact identity stability;
- complete absence of migration, backfill, provider, credential, model-cache,
  install, publication, or integration effects; and
- the final exact branch/commit/tree, test receipts, and distribution bytes.

Verdict: PENDING.
