Status: recorded
Created: 2026-07-21
Updated: 2026-07-21
Target: PR #89 (`work/implement-simple-release`)
Verdict: concerns

# Simple Main Release Automation Implementation Review

## Target

PR #89 implementation of `.10x/specs/main-push-automatic-github-release.md`, limited to the four reported blockers.

## Findings

1. **Blocker — stable SemVer/date validation was syntactic only. Resolved in repair.** Core numeric identifiers now reject leading zeros and older changelog dates must parse as real ISO calendar dates. Focused tests cover each numeric position and invalid day/month values.
2. **Blocker — ref-creation 422 inspected only the tag and could continue mutation. Resolved in repair.** The actual publication shell now performs one full tag, Release, API asset, downloaded digest, and provenance readback. Exact complete state emits `resolved_action=noop`; attestation and Release creation require `resolved_action=create`. Partial fixtures fail before either subsequent mutation.
3. **Blocker — final no-op verification exited without fresh published-asset inspection. Resolved in repair.** The unconditional final step now reinspects tag/Release, downloads exactly the hosted assets, compares exact digests, and verifies provenance for both initial actions. Executable fake-host tests run the workflow shell rather than relying only on YAML text assertions.
4. **Blocker — forbidden release behavior scan was limited to two workflow files. Resolved in repair.** Readiness Policy now scans a bounded repository-wide release surface: all workflow YAML files and both release helper scripts. Tests inject each forbidden service into every path class and prove failure while ignoring non-release paths.

## Verdict

The implementation has targeted fixes and local evidence for all four findings. Verdict remains `concerns` until an independent reviewer examines the final diff and final-head hosted CI passes; this record does not self-ratify the required review gate.

## Residual risk

The GitHub-hosted 422 race and publication flow were not exercised against live state, by explicit scope. Deterministic executable fakes cover control flow, readbacks, digest checks, provenance command arguments, and mutation suppression. No live release or configuration action was performed.
