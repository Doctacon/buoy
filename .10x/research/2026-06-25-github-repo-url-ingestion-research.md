Status: done
Created: 2026-06-25
Updated: 2026-06-25

# GitHub Repository URL Ingestion Research

## Question

How should `turbo-search plan <url>` automatically handle a public GitHub repository URL such as `https://github.com/Doctacon/open-streaming-lab` so the repository can be crawled, chunked, planned, applied, and retrieved through the same generic RAG workflow used for websites?

The immediate problem observed in the codebase is that `https://github.com/<owner>/<repo>` currently passes HTTP(S) URL validation and is treated as an ordinary website. That creates host-only defaults such as `site-github-com-v1`, `artifacts/site-crawls/github-com`, and `.turbo-search/state/github-com/...`, so unrelated repositories collide unless users manually override namespace and output directory.

## Sources and methods

### Codebase inspection

- `src/turbo_search/crawler.py`
  - `validate_base_url` accepts any absolute HTTP(S) URL and strips fragments.
  - `namespace_candidate`, `default_out_dir`, and `site_id_for_url` are host-based, so all GitHub repositories currently resolve to GitHub-host-level identities.
  - `crawl_site` uses Scrapling and emits Markdown pages under `pages/*.md`.
- `src/turbo_search/chunker.py`
  - `process_corpus` currently discovers only `*.md` files and chunks Markdown sections.
  - Existing plan/apply artifacts depend on a Markdown corpus, which is useful as a stable adapter boundary for non-web sources.
- `src/turbo_search/plan_artifacts.py`
  - Plan artifacts and row identity already operate over chunk manifests and do not require pages to have come from Scrapling specifically.
- `.loom/specs/generic-site-rag-incremental-plan-apply.md`
  - Existing workflow contract is Terraform-like: local-only `plan`, local-only `apply` preflight, approved live `apply --approve`, stale-delete guardrail.
- `.loom/decisions/generic-site-rag-incremental-state.md`
  - Stable namespace + local applied-state manifest is the current incremental baseline.
- `.loom/decisions/turbopuffer-cost-first-reorientation.md`
  - Live writes and queries require explicit approval; plans should minimize needless chunks/storage.

### External research

- GitHub REST repository docs: `https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository`
  - `GET /repos/{owner}/{repo}` can be used without authentication for public repositories.
  - Response includes `clone_url`, `html_url`, `default_branch`, `archive_url`, `size`, `language`, visibility fields, and status codes such as `200`, `301`, `403`, `404`.
- Git clone docs: `https://git-scm.com/docs/git-clone.html`
  - `--depth <n>` creates a shallow clone and implies `--single-branch` unless overridden.
  - `--single-branch`, `--branch <name>`, and `--no-tags` are appropriate for a minimal default-branch checkout.
  - `--filter=blob:none` supports partial clone by omitting blobs until needed; useful for advanced acquisition, but less useful if the ingestion must read most eligible file contents anyway.
  - `--sparse` and sparse checkout can limit checkout to specific paths.
- GitHub Code Search syntax source: `https://github.com/github/docs/blob/main/content/search-github/github-code-search/understanding-github-code-search-syntax.md`
  - GitHub code search treats bare terms as matching either file content or file path.
  - It has first-class qualifiers for `repo:`, `language:`, `path:`, `content:`, and `symbol:`.
  - `is:vendored` and `is:generated` exist as concepts in GitHub search, underscoring the need to filter vendor/generated code from local ingestion.
  - Symbol search is based on the open-source Tree-sitter parser ecosystem.
- Tree-sitter docs: `https://tree-sitter.github.io/tree-sitter/`
  - Tree-sitter is an open-source parser generator/incremental parsing library intended to parse programming languages quickly and robustly, including in the presence of syntax errors.
  - It has official Python bindings and parsers for many common languages.
- Gitingest: `https://gitingest.com/` and `https://github.com/coderamp-labs/gitingest`
  - Open-source prior art for turning a Git repository into prompt-friendly text.
  - Its public service uses conservative handling such as file-size limits (example UI says “Include files under: 50kB”) and temporary clones.
- Practice-oriented RAG/library search:
  - LangChain and LlamaIndex repo readers/loaders generally follow `loader -> splitter/chunker -> vector store/retrieval` patterns.
  - Practical repository RAG recommendations converge on metadata-rich chunks, file/path filtering, hybrid retrieval, and code-aware chunking when possible.

## Findings

### Acquisition: clone/archive/API tradeoffs

1. Crawling rendered GitHub HTML is the wrong default for repository ingestion.
   - It indexes GitHub UI chrome, repository navigation, and rendered views rather than the actual source corpus.
   - It is hard to avoid collisions because current identity is host-based.
   - It depends on GitHub web page structure and robots/crawler behavior rather than the repository object model.

2. A shallow default-branch `git clone` is the best MVP acquisition path for public repositories.
   - It is open source, standard, does not require proprietary SDKs, and works for public repositories without credentials.
   - `git clone --depth 1 --single-branch --branch <ref> --no-tags <clone_url> <checkout_dir>` keeps network/history cost low.
   - It naturally yields tracked files via `git ls-files`, respecting the repository’s committed corpus rather than web-rendered HTML.

3. GitHub REST metadata is useful but should not become a required content-ingestion dependency.
   - `GET /repos/{owner}/{repo}` gives reliable `default_branch`, canonical `clone_url`, and redirect/error information for public repositories.
   - If unauthenticated metadata fails due to rate limits/network, `git ls-remote --symref <clone_url> HEAD` can resolve default branch as a fallback.
   - Private repository authentication should stay out of MVP unless explicitly requested; no PATs should be persisted.

4. Archive/tarball download is a viable fallback but less flexible than clone for MVP.
   - Archives avoid `.git` directories and can be simple to unpack, but default-branch resolution still needs metadata or redirect behavior.
   - Clone gives commit SHA, tracked file inventory, branch/ref verification, and future incremental acquisition paths more naturally.

### Identity and URLs

1. Repository source identity must include owner and repo.
   - Default namespace should be repo-specific, e.g. `github-doctacon-open-streaming-lab-v1`, not `site-github-com-v1`.
   - Default out dir should be repo-specific, e.g. `artifacts/site-crawls/github-doctacon-open-streaming-lab-plan` or similar.
   - Local state path should use a repo-specific `site_id`, e.g. `github-doctacon-open-streaming-lab`.

2. Plan `base_url` should canonicalize to the repository root.
   - For `https://github.com/owner/repo`, `https://github.com/owner/repo/`, `.git`, and supported `tree/<ref>/<subdir>` inputs, the plan should persist a canonical repo root plus source metadata.
   - Tree/subdirectory inputs can be represented by `repo_subdir` or include filters rather than by changing source identity.

3. File citations should point to GitHub blob URLs.
   - Stable display/citation URL: `https://github.com/<owner>/<repo>/blob/<ref>/<path>`.
   - Metadata should also include `commit_sha` so users can understand the exact snapshot.
   - Whether canonical row identity uses branch/ref URLs or commit-pinned URLs is a tradeoff:
     - Branch/ref URLs preserve stable citation URLs across runs and row IDs change only when chunk content changes.
     - Commit-pinned URLs make every changed file’s URL change per run, causing more stale rows.
   - For incremental behavior, prefer branch/ref blob URLs as `canonical_url` plus separate `commit_sha` metadata.

### File filtering and cost/noise control

1. Repository ingestion must filter before chunking.
   - Skip binary files, empty files, oversized files, generated/vendor/build output, dependency directories, caches, and `.git` internals.
   - Use tracked files (`git ls-files`) instead of raw recursive filesystem traversal.
   - Provide include/exclude globs that operate on repo-relative paths.

2. Conservative defaults are appropriate because turbopuffer cost is a project-level concern.
   - Use a per-file size cap, defaulting to a small value such as 50 KiB or 100 KiB.
   - Honor `--max-pages` as max files and `--max-chunks` as max chunks for repo sources.
   - Surface skipped counts and reasons in summary artifacts so users can tune filters.

3. Hybrid retrieval benefits from path and symbol metadata.
   - GitHub code search matches path and content and exposes path/language/symbol filtering; local RAG should store analogous metadata.
   - Existing turbopuffer rows already have `title`, `url`, `path`, `section_path`, `doc_kind`, and `tags`; repo rows should enrich those fields rather than requiring a separate retrieval stack initially.

### Chunking approach

1. Current Markdown chunking is a workable boundary, but not sufficient for high-quality code ingestion by itself.
   - It chunks Markdown headings and prose well.
   - If source files are simply wrapped in a single code fence, current oversized-unit logic may split code by words/sentences rather than syntax or lines.

2. Best-practice repository RAG is code-aware.
   - For Markdown/docs: heading-aware chunking is correct.
   - For code: prefer semantic/syntax boundaries such as modules/classes/functions using Tree-sitter where available, with line/token fallback for unsupported languages or oversized symbols.
   - For configs/plain text: split by logical blocks or line windows.

3. MVP can stage quality.
   - Phase 1 can convert repo files to Markdown artifacts and add repo-aware line/block fallback chunking.
   - Tree-sitter symbol extraction can be a follow-up once the source adapter and artifact contract are stable.

## Conclusions

### Recommended architecture

Add a source-adapter layer that dispatches `plan`/`crawl` from a URL:

```text
Source URL
  ├── website source -> existing Scrapling crawl -> pages/*.md -> process_corpus -> plan/apply
  └── github_repo source -> git clone + file selection -> pages/*.md/repo metadata -> repo-aware chunking -> same plan/apply
```

The GitHub path should reuse the existing plan/apply/diff/turbopuffer safety model rather than creating a separate apply path.

### MVP behavior to plan

When a user runs:

```bash
uv run turbo-search plan https://github.com/Doctacon/open-streaming-lab
```

`turbo-search` should automatically:

1. Detect `github.com/<owner>/<repo>` as a GitHub repository source.
2. Normalize owner/repo and strip `.git`, fragments, and query params.
3. Resolve the default branch/ref and clone URL.
4. Shallow clone the public repo into generated artifacts.
5. Enumerate tracked files with `git ls-files`.
6. Filter files with conservative defaults and user include/exclude globs.
7. Generate a reviewable corpus and/or chunks with GitHub metadata.
8. Use repo-specific defaults:
   - namespace: `github-doctacon-open-streaming-lab-v1`
   - site_id: `github-doctacon-open-streaming-lab`
   - out_dir: `artifacts/site-crawls/github-doctacon-open-streaming-lab-plan`
9. Produce the same artifact set as website plans: `plan.json`, `summary.json`, `manifest.json`, `chunks.jsonl`, and generated `pages/*.md`.
10. Preserve local-only guarantees: no turbopuffer calls, no embedding, no credential reads.

### Explicit non-goals for MVP

- Private repository support.
- GitHub issue/PR/wiki/discussion ingestion.
- Submodule recursion by default.
- Live GitHub API tokens or stored PATs.
- Browser-rendered GitHub page crawling as the primary repo ingestion path.
- Namespace deletion or live turbopuffer writes without existing explicit apply approval.

### Follow-up research needed before advanced implementation

- Exact Python Tree-sitter package/parser choices if semantic code chunking is included in the first implementation.
- Whether to integrate GitHub Linguist-style vendored/generated detection through an open-source library or maintain a simpler internal denylist.
- Whether retrieval should add explicit `language`, `repo`, and `source_kind` filters to the turbopuffer schema immediately or wait until repo ingestion is validated.
