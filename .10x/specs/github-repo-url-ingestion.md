Status: active
Created: 2026-06-25
Updated: 2026-06-25

# GitHub Repository URL Ingestion

## Purpose and scope

This spec defines automatic handling for public GitHub repository URLs in the existing `turbo-search` generic RAG plan/apply workflow.

The motivating example is:

```text
https://github.com/Doctacon/open-streaming-lab
```

Today this URL is accepted as a generic HTTP(S) website and would be crawled as rendered GitHub HTML, with host-only defaults such as `site-github-com-v1`. The desired behavior is that GitHub repository URLs are automatically detected and ingested as repository source content while still producing the same review/apply artifacts used for ordinary websites.

Related records:

- Research: `.loom/research/2026-06-25-github-repo-url-ingestion-research.md`
- Existing generic plan/apply spec: `.loom/specs/generic-site-rag-incremental-plan-apply.md`
- Existing incremental state decision: `.loom/decisions/generic-site-rag-incremental-state.md`
- Cost guardrail decision: `.loom/decisions/turbopuffer-cost-first-reorientation.md`

## Out of scope

MVP GitHub repository ingestion does not cover:

- private repositories;
- GitHub issues, pull requests, releases, discussions, projects, or wikis;
- recursive submodule ingestion by default;
- storing or reading GitHub personal access tokens;
- browser-rendered GitHub HTML crawling as the primary repository ingestion path;
- semantic Tree-sitter chunking for every language in the first pass, unless separately approved;
- changing the existing explicit live `apply --approve` safety model.

## Behavior

### Source detection

`turbo-search plan <url>` and `turbo-search crawl --base-url <url>` should use an automatic source detector.

Source kinds:

```text
website      existing Scrapling website behavior
github_repo  new repository-source behavior for github.com/<owner>/<repo>
```

A URL should be classified as `github_repo` when all of the following are true:

- scheme is `https` or `http`;
- host is `github.com` or `www.github.com`;
- the path begins with at least two non-empty segments: `<owner>/<repo>`;
- the path is not a GitHub global page such as `/features`, `/pricing`, `/topics`, `/marketplace`, `/settings`, `/login`, or `/orgs/...` without a repo segment.

Supported MVP forms:

```text
https://github.com/owner/repo
https://github.com/owner/repo/
https://github.com/owner/repo.git
https://github.com/owner/repo/tree/<branch-or-ref>/<optional-subdir>
https://github.com/owner/repo/blob/<branch-or-ref>/<path>   # treated as repo URL plus include-path candidate, or rejected clearly if single-file ingestion is not implemented
```

The persisted repository root should be canonicalized to:

```text
https://github.com/<owner>/<repo>
```

Fragments and query parameters should be ignored for source identity.

### Default identity

GitHub repository identity must include owner and repo, not just `github.com`.

For `https://github.com/Doctacon/open-streaming-lab`, defaults should be:

```text
source_kind: github_repo
repo_full_name: Doctacon/open-streaming-lab
site_id: github-doctacon-open-streaming-lab
namespace_candidate: github-doctacon-open-streaming-lab-v1
out_dir: artifacts/site-crawls/github-doctacon-open-streaming-lab-plan
state_path: .turbo-search/state/github-doctacon-open-streaming-lab/github-doctacon-open-streaming-lab-v1/last-applied.json
```

If `--namespace` or `--out-dir` is supplied, explicit user values still win.

### Acquisition

For public repositories, the MVP acquisition path should:

1. Resolve repository metadata:
   - preferred: unauthenticated `GET https://api.github.com/repos/<owner>/<repo>`;
   - fallback: `git ls-remote --symref https://github.com/<owner>/<repo>.git HEAD`.
2. Determine:
   - canonical owner/repo casing when available;
   - clone URL;
   - default branch/ref;
   - current commit SHA after clone;
   - repository size when metadata is available.
3. Shallow clone into a generated artifact/cache directory:

```bash
git clone --depth 1 --single-branch --branch <ref> --no-tags <clone_url> <checkout_dir>
```

If a `tree/<ref>/<subdir>` URL is provided, ingestion should either:

- clone the named ref and restrict file selection to the subdirectory; or
- fail clearly if the ref/subdir cannot be resolved.

Acquisition must not read credentials by default and must not persist any GitHub tokens.

### File discovery and filtering

Repository corpus generation should enumerate tracked files using Git, not raw recursive traversal:

```bash
git -C <checkout_dir> ls-files -z
```

Default include behavior:

- include Markdown/prose docs (`*.md`, `*.mdx`, `*.rst`, `*.txt`) and common source/config files;
- include files only under the selected repo subdir when a tree URL or include filter narrows scope;
- use `--max-pages` as a max-file cap for repository sources;
- use `--max-chunks` as the existing max-chunk cap.

Default exclude behavior:

- skip binary files;
- skip empty files;
- skip files above a conservative default size cap, initially 50 KiB unless implementation evidence suggests a better value;
- skip dependency/vendor/build/cache/generated paths such as:
  - `.git/`, `.github/workflows` only if workflows are explicitly deemed low-value by implementation review;
  - `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `.next/`, `.turbo/`, `coverage/`, `__pycache__/`;
  - common lockfiles and minified bundles by default, unless user include filters opt them back in.

User filters:

- Existing `--include-path` and `--exclude-path` should apply to repo-relative file paths for `github_repo` sources.
- Documentation should make clear that for websites these are URL path globs, while for GitHub repositories they are repo file path globs.

The plan summary must report counts for:

```text
files_discovered
files_selected
files_skipped_binary
files_skipped_oversize
files_skipped_filtered
files_error
chunks_generated
limit_reached
```

### Corpus and chunk model

The GitHub repository source should feed the existing plan/apply artifact model.

Artifacts should still include:

```text
plan.json
summary.json
manifest.json
chunks.jsonl
pages/*.md
```

Generated repository Markdown pages should include frontmatter sufficient for plan/apply and retrieval:

```yaml
---
url: "https://github.com/<owner>/<repo>/blob/<ref>/<path>"
title: "<repo-relative path>"
status: "200"
content_type: "text/plain; charset=utf-8"
source_kind: "github_repo"
repo_full_name: "<owner>/<repo>"
repo_owner: "<owner>"
repo_name: "<repo>"
repo_ref: "<branch-or-ref>"
commit_sha: "<sha>"
repo_path: "<path>"
language: "<language-or-extension>"
source_hash: "<hash>"
fetcher: "git-shallow-clone"
---
```

Markdown and prose files may preserve their body as Markdown.

Code/config files should be represented so retrieval has useful context. MVP options, in recommended order:

1. Add a repo-aware chunking path that chunks non-Markdown text by logical blocks/line windows and stores metadata.
2. If reusing the Markdown chunker directly, wrap code with path/language headings and fenced code blocks, but avoid word/sentence splitting that destroys code locality.

A future Tree-sitter enhancement may split code by functions/classes/symbols and populate symbol metadata.

### Row schema and metadata

The existing generic row schema should continue to work for repository content. Repo ingestion should add, or plan for adding, these attributes where supported:

```text
source_kind
github_repo
repo_owner
repo_name
repo_full_name
repo_ref
commit_sha
repo_path
language
symbol_name      # optional/future
line_start       # optional/future
line_end         # optional/future
```

Existing fields should map as:

```text
title: repo-relative path or document title
url/canonical_url: GitHub blob URL using the selected branch/ref
path: repo-relative file path
section_path: Markdown heading path, code block label, or future symbol path
doc_kind: github_repo, docs, code, config, test, etc.
tags: repo/source/language/path-derived tags
```

### Plan/apply semantics

GitHub repository ingestion must preserve the existing local-only and apply-safety contract:

- `plan` makes no turbopuffer API calls.
- `plan` does not embed text.
- `plan` does not read turbopuffer credentials.
- `apply` without `--approve` remains local-only preflight.
- `apply --approve` embeds/upserts only new or changed chunks.
- `--delete-stale` remains the only stale-delete path.

Incremental identity should remain content-sensitive and stable across repeated default-branch runs:

```text
site_id + canonical_url + section_path + chunk_hash + duplicate ordinal when needed
```

`canonical_url` should use the selected branch/ref blob URL rather than a commit-pinned URL for ordinary default-branch runs. The exact `commit_sha` should be captured separately in metadata so users can reconstruct the source snapshot without causing every commit to churn URLs.

### Error handling

The CLI should fail clearly before generating partial misleading plans when:

- URL looks like GitHub but does not include owner/repo;
- repository metadata and default-branch fallback both fail;
- repository is private or inaccessible in unauthenticated MVP mode;
- `git` is unavailable;
- clone fails;
- requested tree ref/subdir cannot be resolved;
- no eligible files remain after filtering.

Errors must not print tokens or private credential identifiers.

## Acceptance criteria

- `turbo-search plan https://github.com/Doctacon/open-streaming-lab --json` automatically classifies the source as `github_repo`.
- The plan derives repo-specific defaults rather than `site-github-com-v1` / `github-com`.
- The GitHub plan path is local-only: no turbopuffer credentials, embeddings, or turbopuffer API calls.
- The GitHub path uses repository contents from git acquisition, not Scrapling-rendered GitHub UI pages.
- Generated artifacts include `plan.json`, `summary.json`, `manifest.json`, `chunks.jsonl`, and `pages/*.md`.
- `summary.json` reports source kind, repo metadata, file skip counts, selected file count, chunk count, and limit flags.
- Existing website `plan` and `crawl` behavior remains backward compatible.
- Existing `apply` preflight and approved apply can consume GitHub-generated plans without special live-write code paths.
- Tests cover:
  - GitHub URL parser accepts root, trailing slash, `.git`, and tree URLs;
  - GitHub URL parser rejects non-repo GitHub pages clearly;
  - namespace/site_id/out_dir defaults are repo-specific;
  - source dispatch routes GitHub URLs away from Scrapling;
  - git acquisition is mocked/faked and does not require network in unit tests;
  - file filtering skips binary/oversize/vendor/generated paths;
  - generated Markdown frontmatter feeds the existing plan artifact builder;
  - apply preflight accepts a generated GitHub plan;
  - ordinary website tests still pass.
- README/docs show the one-command example and explain path filtering for repository sources.

## Constraints

- Prefer open-source/local components: git CLI, Python standard library, existing local embedding model, optional Tree-sitter only if open-source parsers are introduced deliberately.
- Do not add proprietary managed services or closed-source SDK dependencies.
- Preserve generated artifacts and local state as gitignored local output.
- Preserve current live-write approval guardrails.
- Keep the first implementation deterministic and testable with fakes/mocks instead of live GitHub or turbopuffer calls in unit tests.
