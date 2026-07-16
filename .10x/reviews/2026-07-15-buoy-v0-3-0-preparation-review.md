Status: recorded
Created: 2026-07-15
Updated: 2026-07-15
Target: commits `339b5d1` and `0c23b9e`
Verdict: pass

# Buoy v0.3.0 Preparation Review

## Findings

Initial review confirmed version/build consistency but found stale 0.2-only environment-alias text and an incomplete changelog. Corrective commit `0c23b9e` aligned migration docs, runtime docstrings, active precision/compatibility specs, warnings, and precise regression tests on retention through 0.3/removal in 0.4. It also completed the pending changelog from exact `v0.2.1..HEAD` history.

Two fresh reviewers then confirmed:

- project, module, lock, tests, and rebuilt artifact metadata agree on 0.3.0;
- both console aliases remain and all active alias authorities target 0.4 removal;
- the pending changelog accurately covers float16 inference, planning/apply improvements, namespace discovery, explicit multi-namespace retrieval, apply/retrieval handoff, catalog, registration/recovery, auto-routing, and state-root migration;
- release docs defer date/link finalization until hosted verification;
- 364 tests passed on Python 3.11 and 3.13, 57 focused tests passed, and tag/assets/build/install/reference/diff checks passed;
- no tag, GitHub Release, main, PyPI, credentials, or Turbopuffer mutation occurred.

## Verdict

Pass. The preparation child is ready to close after hosted PR checks pass.

## Residual risk

Local artifact digests are pre-hosted evidence and are not final release-commit asset digests. Hosted Linux PR checks and later tag workflow remain separate gates.
