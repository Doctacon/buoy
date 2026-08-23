Status: recorded
Created: 2026-08-23
Updated: 2026-08-23
Target: runtime 6bfd0d4cec784cec18e9050bef4a8d0787f354e7; documentation c9f0f44348a51ece48cacee97c6cd6335f3f0df2; evidence 4391e9cd0befc37268937ba6b36ab7b8d379c07a
Verdict: fail

# Retrieve Command Telemetry V2 Integrated Review

## Target

Two fresh read-only reviewers independently assessed:

- runtime implementation `6bfd0d4cec784cec18e9050bef4a8d0787f354e7`,
  tree `269310974768aafb2d79d62c50f0753d94ac8491`;
- documentation target `c9f0f44348a51ece48cacee97c6cd6335f3f0df2`,
  tree `b2656e3402548e8ca439e79405a8f21b6fb56114`;
- integrated evidence through
  `4391e9cd0befc37268937ba6b36ab7b8d379c07a`;
- both active focused specifications and all nine validation-ticket criteria;
- raw parent timing, migration, package, test, and documentation artifacts.

One reviewer returned PASS with no findings. The closure/spec-drift reviewer
returned FAIL for one significant acceptance-evidence gap. The adverse finding
controls closure until repaired and re-reviewed.

## Findings

### Significant: bootstrap and pipeline controlled-delay comparisons are absent

Validation-ticket criterion 3 requires controlled delays to independently prove
bootstrap, routing, initialization, pipeline, and rendering attribution without
summing nested spans. Current baseline-versus-delay subprocess coverage in
`tests/test_retrieve_command_telemetry.py` and
`tests/fixtures/retrieve_command_timing_probe.py` exercises initialization,
routing, and rendering only.

The exact fake-clock test proves fixed command, bootstrap, preparation,
pipeline, nested-stage, and render durations plus enclosure. It does not inject
baseline-versus-delayed bootstrap or pipeline work. The integrated evidence
therefore overstates criterion 3 where it treats the fixed fake-clock assertions
as controlled-delay observations for those two seams.

Required bounded repair:

1. add controlled baseline-versus-delay bootstrap observations proving command
   duration increases while pipeline duration remains unchanged;
2. add controlled baseline-versus-delay pipeline observations proving both
   authoritative command and pipeline durations increase appropriately;
3. record raw values and use the authoritative command/pipeline columns rather
   than summing nested spans; and
4. rerun the bounded integrated validation and obtain a fresh PASS review.

No production runtime change is currently indicated. The validation ticket
already authorizes only defects that block its acceptance.

### Timing arithmetic: pass

Both reviewers independently recalculated the five parent-observed values.
Median shell-minus-command is exactly `117.155667` ms and median command/shell
is exactly `0.9500946372682385`, without rounding. Both satisfy the ratified
gates. The ratio margin is narrow—approximately `0.0000946373` above 0.95—but
that is a bounded reference-host residual risk, not a failed criterion.

### Migration, privacy, compatibility, and documentation: pass

Both reviewers accepted the exact-wheel migration rehearsal, immutable backup
and v1 equivalence, view identities, pending-v2 recovery, idempotent rerun,
privacy/no-network/provider-free management evidence, enabled/disabled and
v1 compatibility evidence, and documentation/help/SQL reconciliation.

The documentation commit changes only README and CHANGELOG outside `.10x`.
The clean documentation-target build reproduced unchanged CLI, envelope, and
routing-artifact bytes across source, wheel, source distribution, and isolated
install. Its expected VCS-derived package version differs from the earlier
runtime package; this is not runtime or test drift.

## Criterion assessment

| Criterion | Verdict |
| --- | --- |
| 1. Focused-spec maps | pass |
| 2. Five-run parent timing | pass |
| 3. Five controlled attribution seams | **fail** |
| 4. Built-console migration | pass |
| 5. Fault/privacy/no-network matrix | pass |
| 6. CLI and direct-v1 compatibility | pass |
| 7. Dual-runtime/static/package matrix | pass |
| 8. Documentation/help/SQL | pass |
| 9. Independent passing review | **fail pending repair and rereview** |

## Verdict

**Fail.** Closure is blocked only by controlled bootstrap-delay and
pipeline-delay evidence plus a fresh independent PASS after repair.

## Residual risk

- Reference-host ratio passed narrowly and is intentionally not portable.
- Runtime and deterministic crash evidence remains bounded to macOS arm64,
  DuckDB 1.5.4/1.5.5, and injected process failure rather than hardware power
  loss or other filesystems.
- Full suites exclude the separately owned stale
  `tests/test_dynamic_version.py` collector; its active owner is
  `.10x/tickets/2026-08-20-reconcile-missing-release-checks-test-harness.md`.
- No live provider/model/content/credential/catalog mutation, real home, remote,
  release, or publication operation was performed.
