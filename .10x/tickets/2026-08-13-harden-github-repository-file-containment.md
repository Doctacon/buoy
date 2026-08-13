Status: active
Created: 2026-08-13
Updated: 2026-08-13
Parent: .10x/tickets/2026-08-13-ship-buoy-v0-5-1.md
Depends-On: None

# Harden GitHub Repository File Containment

## Outcome

Prevent a public GitHub repository from causing `buoy plan` to read content
outside its acquired checkout through a tracked link or a replaced checkout
entry, without changing ordinary repository-plan output.

## Scope

- Inventory the immutable acquired commit with NUL-safe Git tree metadata.
- Permit content reads only for regular blob modes `100644` and `100755`.
- Filter links, gitlinks/submodules, and special entries before filesystem use;
  explicit include patterns cannot override that gate.
- Bind size and bounded content to one opened regular file, rejecting unsafe
  paths, link/reparse components, and identity drift.
- Validate requested repository subdirectories as Git tree objects.
- Preserve current statistics, filtering, CR/LF normalization, hashes, URLs,
  max-files behavior, and all non-GitHub source behavior.

## Acceptance

- Absolute/relative external, internal, dangling, directory, materialized-link,
  oversize-card, explicit-include, gitlink, final-replacement, and
  ancestor-replacement cases never expose target bytes or target paths.
- Strict NUL framing handles tabs/newlines in filenames and rejects malformed,
  duplicate, traversal, backslash/drive/ADS-ambiguous records.
- The descriptor-relative reader is used where supported; its portable path
  rejects Windows reparse points and identity drift before reading.
- Ordinary executable/text/binary/empty/oversize files and existing corpus
  statistics remain compatible.
- Focused and complete locked Python 3.11/3.13 suites pass with no external
  writes or Turbopuffer operations.

## Owned paths

- `src/buoy_search/github_repo.py`
- `tests/test_github_repo.py`
- `docs/indexing.md`
- `CHANGELOG.md`
- `.10x/evidence/2026-08-13-github-repository-file-containment.md`

## Exclusions

Apply/retrieve behavior, other source adapters, live repository indexing,
Turbopuffer, stale-row deletion, private-repository support, release automation,
and unrelated refactoring or hardening.

## Progress

- 2026-08-13: Implementation and adversarial tests are present on
  `work/github-repo-symlink-containment`. Focused validation (35 tests), full
  locked Python 3.11/3.13 validation (472 tests each), frozen validators,
  reproducible v0.5.1 builds, distribution/clean-install smoke, and independent
  focused review pass locally. Hosted CI remains before integration.

## Blockers

Hosted public CI and separate integration review.
