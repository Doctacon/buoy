Status: candidate
Created: 2026-08-13
Updated: 2026-08-13
Ticket: .10x/tickets/2026-08-13-harden-github-repository-file-containment.md

# GitHub Repository File Containment Evidence

## Candidate

- Branch: `work/github-repo-symlink-containment`
- Base: `origin/develop` `7c5cc96d4c8995f06c7991ea5c2b8948dbb748a5`
- Source boundary: `src/buoy_search/github_repo.py`
- Focused regression boundary: `tests/test_github_repo.py`

## Implemented control

The acquired commit tree is parsed from exact NUL-framed `git ls-tree -rz -l
--full-tree` bytes. Only regular blob modes enter path filtering and filesystem
inspection. Content and size come from one bounded, identity-checked regular
file descriptor; unsafe entries produce repository-relative errors only.

## Focused observations

- `uv run --python 3.13 python -m unittest tests.test_github_repo -q`: 35 tests passed.
- Real Git fixtures cover external absolute/relative links, internal/dangling
  and directory links, a link payload materialized as a regular checkout file,
  an explicit include plus oversize-card attempt, a gitlink, final/ancestor
  checkout replacement, executable mode, ordinary filtering/stats, and Git
  tree subdirectory validation.
- Parser fixtures cover NUL framing, an empty tree, tab/newline and valid POSIX
  filenames, malformed/duplicate object metadata, and traversal.
- Portable-reader fixtures cover normal content, POSIX link rejection, a fake
  Windows reparse point at the root/intermediate/final entry, pre-read identity
  drift rejected before read, post-read drift discarded, Windows path/device
  ambiguity, and exact bounded oversize sampling.
- Existing CRLF regression confirms universal-newline compatibility.

## Complete local validation

- Locked Python 3.11 suite: 472 tests passed.
- Locked Python 3.13 suite: 472 tests passed.
- `uv lock --check`, `validate-source`, ranking-contract validation, C6 syntax
  forecast validation, and `git diff --check`: passed.
- Exact deterministic Python 3.13 builds were byte-identical across two output
  directories. Wheel SHA-256:
  `fb474eb3220709b33b9cbd71578a90323317d07803e423cd15c3a9e09a8d843b`.
  Source archive SHA-256:
  `64be001a8d32adc195b07227d4fdf77a8cdfafc015561976f837fb8e14632127`.
  Candidate command used source commit timestamp `1785447001`:
  `SETUPTOOLS_SCM_PRETEND_VERSION=0.5.1 SOURCE_DATE_EPOCH=1785447001
  PYTHONHASHSEED=0 TZ=UTC LC_ALL=C uv build --python 3.13 --out-dir dist`.
- Distribution inspection found exactly the v0.5.1 wheel/sdist, matching 0.5.1
  metadata and generated version modules, the sole `buoy` entry point, bundled
  tokenizer, and focused package boundary.
- Clean Python 3.13 wheel installation reported package/module/CLI version
  0.5.1; both help paths and the exact nine-token offline smoke passed.
- Independent focused review:
  `.10x/reviews/2026-08-13-github-repository-file-containment-review.md`,
  provisional pass with no source blocker.

Hosted public CI remains an integration gate. This candidate evidence does not
authorize release or advisory publication before the reviewed PR and exact-main
checks pass.

## External effects

No Turbopuffer, namespace, stale-row, PyPI, tag, Release, advisory publication,
branch-protection, or user-data operation occurred during focused validation.
