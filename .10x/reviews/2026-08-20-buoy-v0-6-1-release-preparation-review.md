Status: pass
Created: 2026-08-20
Updated: 2026-08-20
Ticket: .10x/tickets/done/2026-08-20-ship-buoy-v0-6-1.md
Evidence: .10x/evidence/2026-08-20-buoy-v0-6-1-github-release.md
Decision: .10x/decisions/annotated-tag-triggered-github-releases.md
Specification: .10x/specs/annotated-tag-triggered-github-release.md

# Buoy v0.6.1 Release Preparation Review

## Target and method

Independent review covered the complete unstaged candidate on
`work/ship-buoy-v0-6-1` from exact
`develop@788c377c57bc1b4f1bfd4aba05d39ad67fe48ead`, tree
`cc619214f5eff4585e6a4df2394d6f45a37a9d5f`. The reviewer inspected the full
diff, every new and changed governing record, VCS-version test behavior,
public version surfaces, standing workflows, package/version configuration,
local and authoritative GitHub state, validation outputs, diagnostic
distributions, and isolated installed-wheel smoke. This review file is the
only reviewer-authored addition.

The bounded candidate changes only:

- the v0.6.1 changelog, README wheel URL, supported-version row, and their
  focused validator expectations;
- the dynamic-version test fixture and exact annotated-tag regression case;
- the truthful v0.6.0 stopped-run disposition, successor ticket/evidence,
  standing specification, and superseded historical reviews; and
- this independent review.

The active v0.6.0 ticket blob
`1595a8ca85db285b942e2a556e46982835bc7821` is removed from its active path
and replaced by the truthful cancelled record. No application module,
dependency, lockfile, package-version mechanism, Release workflow, readiness
workflow, or release helper changes.

## Frozen candidate blobs

The reviewed candidate's Git blob IDs before adding this review were:

- `CHANGELOG.md`: `c99942ad9e1e08084d69b3ae98ba5da86b9b66a3`;
- `README.md`: `379b0c9fb658e0f995d5006073aa74522a8588b0`;
- `SECURITY.md`: `fbd0747cec6331097d23e9f219bb1e6032b317fa`;
- `tests/test_dynamic_version.py`:
  `1a7474c4ac2a20f976a135c26d4c43978693d724`;
- `tests/test_release_automation.py`:
  `44bfbc70a687279a0bb46071bfa728cefe3c991a`;
- `.10x/specs/annotated-tag-triggered-github-release.md`:
  `7677f5ebcb9c6ba0a8523bd714e7c4ed05f0dd25`;
- `.10x/specs/buoy-v0-6-0-one-time-github-release.md`:
  `f5a1bbb95b40610d9b82d78ea8f2b52000a94c58`;
- `.10x/tickets/done/2026-08-20-ship-buoy-v0-6-1.md`:
  `c6fb2d76e6e25580f728dabcc4314cdfbdb49c6f`;
- `.10x/evidence/2026-08-20-buoy-v0-6-1-github-release.md`:
  `d7ec32e576d8abbf9a8446abf4206d001e087685`;
- `.10x/tickets/cancelled/2026-08-19-ship-buoy-v0-6-0.md`:
  `303b725dc47bf3ae9f5ebfab7cc3e513c73f74e9`;
- `.10x/evidence/2026-08-19-buoy-v0-6-0-github-release.md`:
  `ce7bee5ca14092c8435b724f1700c47e10dcc6ae`;
- `.10x/reviews/2026-08-19-annotated-tag-release-workflow-review.md`:
  `42dd47312176379cc10e60fcf3162bdcd7ef48ef`; and
- `.10x/reviews/2026-08-19-annotated-tag-release-workflow-smoke-repair-review.md`:
  `24978532826ed5a25d2c17b3d0f8fb6a8b019551`.

The unchanged critical blobs are `.github/workflows/release.yml` at
`57a63b8f309794292d7d85940504c5a4e77ba70c`,
`.github/workflows/release-readiness.yml` at
`a950a070af0714414e85d182b4d7a6f5a9347684`, and
`scripts/release_automation.py` at
`b6fad8e6d97e123fefefc40c1016045bda74d5d4`. `pyproject.toml`, `uv.lock`,
and `src/` are also unchanged. Thus the previously reviewed pinned action,
permission, tag-validation, draft-verification, immutable-publication, and
fail-closed controls remain exact.

## Failure truth and hosted state

Fresh authenticated inspection found remote
`main@701d73ebbf6a8c3b2c664a0295374dcb4283283c` and
`develop@788c377c57bc1b4f1bfd4aba05d39ad67fe48ead`. Annotated tag object
`1ffb70f5656f48c782defbe252dab44426134343` still names `v0.6.0`, has message
`Buoy v0.6.0`, and peels to that exact main commit. Release run `32329737394`
is completed with failure on attempt one: both locked matrix jobs reached the
complete suite and exposed the same non-hermetic development-version fixture;
build and publish were skipped and the run retained zero artifacts.

Complete authenticated Release inspection, including drafts, found no v0.6.0
or v0.6.1 Release and therefore no target Release asset. Local and remote
v0.6.1 tags are absent, no Release workflow run is active, and repository
immutable Releases remain enabled. The candidate records those facts without
moving or deleting v0.6.0 and without adding a recovery or manual-dispatch
path.

The fixture repair is exact: its development-version case creates one
controlled empty post-tag commit before requiring a development version and
commit identity, while a separate controlled annotated-tag case proves an
exact tag derives the stable metadata, module, and CLI version. Both global
and distribution-normalized pretend-version variables are removed from those
test environments. The repair does not weaken Hatch-VCS version authority or
alter package runtime behavior.

## Validation

Validation on the frozen candidate passed:

- focused release and dynamic-version suite: 28 tests;
- locked Python 3.11 complete suite: 1,034 tests in 106.846 seconds;
- locked Python 3.13 complete suite: 1,034 tests in 63.949 seconds;
- source, lock, ranking, C6, in-memory Python compilation, local record-link
  and status checks, and diff hygiene;
- diagnostic exact-version distribution validation; and
- isolated clean dependency installation plus version, CLI help, module help,
  telemetry help, import, and packaged-tokenizer smoke, reporting
  `buoy 0.6.1` while the isolated home remained empty.

The diagnostic distributions were:

- `buoy_search-0.6.1-py3-none-any.whl`, 697,772 bytes, SHA-256
  `03ee8a83a0c579ddaa771b4f50c2492d6a5e1fab4ff1f96d613be7414e7764ca`;
- `buoy_search-0.6.1.tar.gz`, 1,227,662 bytes, SHA-256
  `5f94f4e96964e6f411a4da4978c21cc493dbbb07a7a196f4b8600c35c141a672`.

These are diagnostic candidate artifacts only; the tag workflow must build,
validate, attest, and publish its own exact tagged-source pair. Early review
replays that could not open the sandboxed user-level uv cache or resolve
build dependencies under restricted network access failed before exercising
the candidate. They were environment-only invalid attempts, not source-test
failures, and were superseded by the dependency-enabled 28-test PASS and the
two locked full-suite PASS results above.

## Findings and residual gates

The v0.6.1 public surfaces are internally consistent and truthfully publish
the accumulated changes since v0.5.1 while preserving the failed v0.6.0 tag
history. Governing links and statuses are coherent after this review exists,
and `git diff --check` is clean. No permission expansion, application,
dependency, package-layout, privacy, provider, model, data, real-home, global
installation, PyPI, tag movement, or hosted release mutation is present.

The remaining risk is entirely in later integration and publication state.
Before tagging, the branch must pass exact-head task CI, separate-role squash
integration into still-current `develop`, all four release-readiness jobs,
separate-role merge-commit promotion into still-current `main`, exact-main CI,
and a fresh hosted preflight proving v0.6.1 tag/Release absence plus enabled
immutable Releases. Any failed v0.6.1 run or unpublished partial state is a
STOP for read-only inspection and receives no blind-rerun authority. Only a
rerun against an already successfully published exact Release is
verification-only.

## Verdict

PASS. No correctness, versioning, packaging, workflow-boundary, governance,
privacy, or scope blocker remains in the reviewed release-preparation
candidate. This review authorizes only the bounded commit and ordinary task
PR handoff. It does not authorize self-merge, direct protected-branch push,
the later main merge, a tag before every residual gate passes, a v0.6.0
recovery, or any Release/PyPI/provider/user-home mutation.
