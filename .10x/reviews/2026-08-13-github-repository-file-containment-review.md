Status: provisional
Created: 2026-08-13
Updated: 2026-08-13
Target: work/github-repo-symlink-containment diff from 7c5cc96d4c8995f06c7991ea5c2b8948dbb748a5
Verdict: provisional pass

# GitHub Repository File Containment Review

## Scope

Independent review inspected the bounded changes in
`src/buoy_search/github_repo.py` and `tests/test_github_repo.py` against
`.10x/tickets/2026-08-13-harden-github-repository-file-containment.md` and its
provisional evidence record. Release automation and the unrelated release
preparation changes present in the shared worktree were excluded.

## Findings and disposition

Iterative review found and closed four blockers:

1. the first safe-reader implementation rejected all ordinary files on
   Windows because it required descriptor-relative POSIX opens;
2. the bounded byte reader initially lost existing universal-newline behavior;
3. Windows-ambiguous path rules initially rejected otherwise safe POSIX Git
   filenames before the POSIX descriptor walk; and
4. the first test slice did not prove reparse-point rejection, pre-read and
   post-read identity drift, or bounded oversize reads.

The final diff inventories the immutable commit with exact NUL-framed tree
metadata and permits filesystem reads only for regular blob modes `100644` and
`100755`. Link modes, gitlinks, and other entries are filtered before path
access and cannot be restored by an explicit include or oversize-card option.
Requested subdirectories must be Git tree objects.

On supported POSIX hosts, every component is opened relative to held directory
descriptors with no-follow flags and the final descriptor must remain one
stable regular file. The portable path retains ordinary-file behavior while
rejecting Windows drive, separator, ADS, device, trailing-dot/space, symlink,
junction, and other reparse ambiguity. It observes the checkout root, every
ancestor, and the final entry; binds the opened handle to that path before the
first byte read; and revalidates path and handle identity after the bounded
read. Errors disclose only the repository-relative path. Universal-newline
normalization, source hashes, URLs, executable files, filtering, and corpus
statistics remain compatible.

## Verification

- `UV_CACHE_DIR=/private/tmp/buoy-uv-cache uv run --locked python -m unittest tests.test_github_repo -q`: 35 tests passed.
- `git diff --check -- src/buoy_search/github_repo.py tests/test_github_repo.py`: passed.
- Python 3.11 and 3.13 compilation of both changed Python files: passed.

The focused suite covers absolute and relative external links, internal,
dangling, directory, and materialized links, explicit inclusion and oversize
cards, gitlinks, final and ancestor checkout replacement, executable files,
strict tree parsing, POSIX-compatible names, root/intermediate/final reparse
observations, identity drift before and after read, exact oversize sampling,
and CR/LF compatibility. No Turbopuffer or other provider operation occurred.

## Verdict

**Provisional pass.** No blocker remains in the reviewed source and focused
test diff. Hosted CI and the ticket's complete locked Python 3.11/3.13
validation remain external gates; this review does not by itself authorize
integration, release, or disclosure.

## Residual validation limits

- The portable path was forced and exercised with synthetic Windows reparse
  observations, but this review did not execute on a native Windows host.
- Complete locked suites, distribution validation, and hosted branch checks
  were not independently rerun as part of this focused review.
