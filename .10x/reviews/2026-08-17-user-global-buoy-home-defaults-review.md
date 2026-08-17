Status: pass
Created: 2026-08-17
Updated: 2026-08-17
Ticket: .10x/tickets/done/2026-08-17-default-local-assets-to-user-home.md
Evidence: .10x/evidence/2026-08-17-user-global-buoy-home-defaults.md
Decision: .10x/decisions/buoy-defaults-local-assets-to-one-user-home.md
Specification: .10x/specs/user-global-buoy-home-defaults.md

# User-Global Buoy Home Defaults Review

Target: implementation commit
`3c5f2e9b38b752594a68d46eaf4c60b8da3738f0`, tree
`f0eb52f15dd5f4bde7d8ba6ee4e7a3c897bf1d24`, based directly on exact
`develop@e101690bc351d92cc6b24a46cb5bc30f00bd6df0`.

## Review performed

Independent review challenged:

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

The reviewer reproduced and drove repairs for canonical cleanup containment,
ancestor and quarantine replacement, explicit-path compatibility when home
resolution fails, lazy source defaults, custom-state-root protection, and
test isolation from the real home. The settled tree passed the reviewer's
235-test focused basket and every cited source/path/diff inspection.

The exact active `cli.py` receipt remains valid. The legacy option help text is
prominently disclosed and requires separate routing recertification rather
than an unauthorized receipt rewrite. Existing project assets remain
implicit-inert; explicit plans retain normal verified cleanup. Multi-account
or multi-region use requires explicit separate roots. Changes to internal
source dataclass constructor/constant surfaces are a disclosed non-CLI risk.

Both runtime validators then passed the complete 883-test suite, their focused
baskets, source/ranking/C6/lock/compile checks, byte-identical distribution
builds, and clean-wheel behavior. They observed no real-home residue, provider,
credential, model, external-network, installed-tool, publication, or
integration effect.

## Verdict

PASS. The exact implementation commit has no remaining correctness,
compatibility, containment, or documentation blocker. This verdict authorizes
only bounded closure records, task-branch push, and one ordinary draft PR for
owner review. It does not authorize self-integration, migration/backfill,
provider/catalog/content work, global-tool installation, publication, or any
`develop`/`main` mutation.
