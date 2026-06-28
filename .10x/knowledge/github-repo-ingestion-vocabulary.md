Status: active
Created: 2026-06-25
Updated: 2026-06-25

# GitHub Repository Ingestion Vocabulary

## Source kind

A classification used before planning to decide how a URL becomes a local corpus.

Current planned source kinds:

- `website`: ordinary HTTP(S) site crawled with Scrapling.
- `github_repo`: GitHub repository URL acquired from git and converted into the same plan/apply artifact shape.

## GitHub repository source

A public repository URL under `github.com/<owner>/<repo>` that should be indexed from repository contents, not from rendered GitHub web UI pages.

## Repo root URL

Canonical source identity for a GitHub repository:

```text
https://github.com/<owner>/<repo>
```

Fragments, query parameters, `.git`, and tree/blob suffixes should not change the repo root identity.

## Repo-relative path

A path inside the repository checkout, such as:

```text
README.md
src/server.ts
docs/install.md
```

For `github_repo` sources, `--include-path` and `--exclude-path` should match repo-relative paths rather than website URL paths.

## Blob URL

A GitHub citation URL for a file at a branch/ref:

```text
https://github.com/<owner>/<repo>/blob/<ref>/<repo-relative-path>
```

This is the planned `canonical_url` / retrieval citation URL for file-backed chunks.

## Commit SHA

The exact git commit checked out for a repository plan. It should be captured in plan/manifest metadata so users can identify the source snapshot. It should not necessarily be part of default row identity because doing so would churn row IDs on every commit.

## Repository corpus

The generated local Markdown representation of selected repository files, written under `pages/*.md` so existing plan/apply artifacts can be reused.

## Repository acquisition

The local-only step that obtains repository contents. MVP recommendation: unauthenticated public metadata lookup when available, then shallow git clone of the selected branch/ref.

## File selection

The deterministic filtering step after acquisition and before chunking. It should enumerate tracked files, then skip binary, oversized, vendor/generated/build/cache, and user-excluded files.
