Status: recorded
Created: 2026-07-18
Updated: 2026-07-18
Target: .10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md
Verdict: pass

# Retrieval Live-by-Default Review

## Target

PR #34 at final reviewed commit `31aeeee27758e4aed9d16d73e7886b62235840b3`, governed by `.10x/tickets/done/2026-07-18-make-retrieval-live-by-default.md`.

## Findings

Initial independent review confirmed default mode switching, generated command quoting, automatic/explicit routing boundaries, all-or-nothing behavior, apply/catalog isolation, and hosted validation, but found one significant output-truthfulness defect: routed automatic preview inherited top-level fields claiming no credentials or Turbopuffer calls despite credentialed read-only catalog routing.

Commit `31aeeee27758e4aed9d16d73e7886b62235840b3` corrected the command-level fields without changing explicit preview or live execution. Regression tests now assert:

- automatic preview top-level credentials and read-only API-call facts;
- nested routing credentials/read-only facts;
- top-level and nested no-content-retrieval facts;
- explicit preview credential/API/model-free behavior.

Final independent re-review found no remaining blocker. PR head matched the reviewed commit. Hosted Python 3.11, Python 3.13, and distribution jobs all passed.

## Verdict

Pass.

## Residual risk

Remote behavior is fake-backed; no real Turbopuffer call was made. This is appropriate for the bounded default/serialization change and does not prove provider availability or account permissions. Plain retrieval now performs authenticated remote reads/content queries by design; scripts requiring preview must use `--dry-run` or `--plan`.
