Status: superseded
Created: 2026-08-19
Updated: 2026-08-20
Ticket: .10x/tickets/cancelled/2026-08-19-ship-buoy-v0-6-0.md
Evidence: .10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md
Supersedes: .10x/reviews/2026-08-19-annotated-tag-release-workflow-review.md
Superseded-By: .10x/reviews/2026-08-20-buoy-v0-6-1-release-preparation-review.md

# Release Workflow Version-Smoke Repair Review

## Supersession

The reviewed CLI-version smoke repair remains correct, but the later exact
v0.6.0 tag run disproved this review's broader release-readiness conclusion.
Both Python jobs failed because
`DynamicVersionTests.test_clean_editable_install_derives_development_version_from_vcs`
assumed its copied editable checkout always had development history; at the
exact tag it correctly derived stable `0.6.0`. A new independent v0.6.1
release-preparation review must cover the hermetic controlled-history repair
and all public v0.6.1 surfaces before handoff. This superseded verdict grants
no v0.6.1 integration or publication authority.

Target: bounded repair candidate based on exact
`develop@ad57706c10bc16cf71103ef00203b3ea80bfa538`.

## Review

Release readiness provided direct evidence: the v0.6.0 wheel built, validated,
and installed, but the shell assertion compared the CLI output to bare
`0.6.0`. `src/buoy_search/cli.py` intentionally defines argparse's version as
`%(prog)s <version>`, so the correct and already observed output is
`buoy 0.6.0`.

The repair changes only the readiness and tag-workflow assertions to include
that program-name prefix, adds exact focused regression assertions, records the
failed readiness run, and supersedes the overbroad prior PASS. Application
source, package metadata, dependencies, lock, release state machine, workflow
permissions, build commands, assets, tag checks, and publication commands are
byte-identical to reviewed develop.

Validation requires Actionlint, diff hygiene, the focused release-automation
suite, a fresh exact 0.6.0 build/validation/install, and the corrected literal
version assertion. Exact-head CI supplies the unchanged full Python 3.11 and
3.13 suites before integration.

## Historical verdict

At the time, this review concluded PASS because the CLI smoke repair matched
the governed public contract and introduced no new permission, release-state,
package, privacy, or scope risk. That historical verdict authorized only its
bounded repair and handoff. The supersession above now controls; a fresh
independent v0.6.1 review is required.
