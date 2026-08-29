Status: recorded
Created: 2026-08-29
Updated: 2026-08-29
Target: .10x/tickets/done/2026-08-28-validate-retrieval-telemetry-v3-integration.md
Verdict: pass

# Retrieval Telemetry V3 Integration Review

## Target

The complete production-default retrieval telemetry v3 diff: inference attribution, provider invocation accounting, distinct queue/writer/store/migration, stable views, privacy, compatibility, documentation, packaging, and provider-free installed lifecycle.

## Review history

Three-angle aggregate review initially found:

- valid telemetry databases/backups larger than 16 MiB were incorrectly rejected during interrupted migration recovery;
- final lifecycle evidence lacked exact replay commands and cleanup proof;
- current SQL examples, migration wording, compatibility naming, changelog, and docstrings had stale v1/v2 language.

The integration worker repaired those issues. Follow-up review then found the literal lifecycle build/version/dependency identity was calendar/cache dependent. The final repair fixed and asserted the distribution-specific VCS version, `SOURCE_DATE_EPOCH`, `uv.lock`, hash-bearing frozen dependency export, no-resolution local-wheel install, installed identity, deterministic two-build hashes, and cleanup.

Final fresh-context review confirmed:

- exact build controls and installed identity are asserted;
- two wheel and sdist builds are byte-identical;
- schema-v3 flush/status and exact command/stage/inference/provider view rows match recorded evidence;
- process cleanup and literal absence checks pass;
- migration databases/backups are governed by exact content identity rather than initialization size while WAL remains bounded;
- strict privacy, opt-in/local-only behavior, disabled zero-side-effect, v1/v2 compatibility, output/routing/ranking/evidence/provider-call preservation, and package lifecycle remain covered; and
- current documentation truthfully describes inference wait, provider-attempt unit, migration reconciliation, current views, and compatibility fields.

No P0, P1, or P2 issue remained. Final verdict: pass.

## Parent-observed validation

The parent ran the literal retained script on the reconciled worktree:

```text
bash .10x/evidence/scripts/2026-08-29-retrieval-telemetry-v3-installed-wheel-lifecycle.sh
```

It passed and emitted the exact expected bounded facts:

- fixed VCS version, `SOURCE_DATE_EPOCH`, uv 0.11.7, and asserted `uv.lock` hash;
- byte-identical deterministic wheel/sdist hashes;
- exact 108-distribution frozen runtime and installed identity;
- one schema-v3 preview observation committed;
- healthy schema-3 status, empty v1/v2/v3 queues, complete provider accounting;
- exact privacy-safe v3 command/stage/provider rows and zero inference rows for explicit preview;
- zero process survivors; and
- all temporary dist/repeat-dist/HOME/venv/run roots absent.

`git diff --check` passed before the script. No provider call, credential read, model operation, real telemetry-store access, stage, commit, or release occurred.

## Acceptance map

- Child criteria and raw evidence: pass.
- Python 3.11/3.13 full suites: `1327 passed, 1408 subtests passed` on each runtime.
- Build and isolated installed-wheel lifecycle: pass, reproducible.
- Provider-free worker/in-process/fallback/failure/provider/view scenarios: pass.
- Disabled zero-side-effect and behavior equivalence: pass.
- Synthetic v2 migration and immutable backup/history preservation: pass.
- Privacy and truthful documentation: pass.
- Independent review findings: repaired and passed.
- Live provider execution: not necessary for implementation acceptance; zero live calls consumed.

## Residual risk and no-action rationale

No real Turbopuffer response traversed the ordinary v3 surface, and the owner's real schema-v2 telemetry store remains unmigrated. Both are intentional limits, not unmet ticket criteria: governed provider call sites are unchanged and exhaustively fake-tested, while real-store migration is explicitly excluded.

The owner's optional “20 bounded calls” phrase remained ambiguous between CLI commands and SDK call expressions. Because provider-free evidence proved the implementation and an automatic command cannot be statically bounded to 20 SDK attempts, no live operation ran and no interpretation was needed. A future live campaign requires a new exact unit/case decision.
