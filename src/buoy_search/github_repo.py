"""GitHub repository acquisition and corpus helpers.

The acquisition path is local-only with respect to turbopuffer: it never reads
Turbopuffer credentials, embeds text, or performs vector writes. Public GitHub
metadata is used only to resolve clone/default-branch information; git remains
the source-of-truth content acquisition mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any, Callable, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from buoy_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
    IndexingPlan,
    IndexingStats,
    MarkdownChunk,
    MarkdownDocument,
    chunk_document,
    clean_markdown_inline,
    derive_doc_kind_and_tags,
    deterministic_chunk_id,
    discover_markdown_files,
    parse_markdown_file,
    process_corpus,
    sha256_text,
)
from buoy_search.repo_syntax_chunking import (
    PYTHON_SYNTAX_ARMS,
    REPO_CHUNKING_ARMS,
    RepoSyntaxChunkingError,
    SourceChunking,
    SourceRange,
    chunk_source,
    source_payload,
)
from buoy_search.treatment_token_budget import (
    MAX_EMBEDDING_TOKENS,
    TOKENIZER_MODEL,
    TOKENIZER_REVISION,
    Tokenizer,
    TreatmentTokenBudgetError,
    UnsplittableSourceLine,
    exact_token_count,
    exhaustive_maximal_subdivision,
    load_pinned_tokenizer,
)
from buoy_search.crawler import (
    DEFAULT_GITHUB_REPO_MAX_FILE_BYTES,
    GitHubRepoSource,
    CrawlExecution,
    CrawlOptions,
    elapsed_since,
    emit_progress,
    namespace_candidate,
    observe_monotonic,
    page_filename,
    summarize_sample_chunks,
    yaml_scalar,
)

DEFAULT_GITHUB_API_TIMEOUT = 15
DEFAULT_GIT_TIMEOUT = 300
GITHUB_API_VERSION = "2022-11-28"
USER_AGENT = "buoy-search/0.2"
DEFAULT_REPO_MAX_FILE_BYTES = DEFAULT_GITHUB_REPO_MAX_FILE_BYTES
DEFAULT_CODE_CHUNK_LINES = 80
OVERSIZE_FILE_CARD_SAMPLE_BYTES = 200 * 1024
REPO_MARKDOWN_EXTENSIONS = {".md", ".markdown", ".mdx"}
REPO_PROSE_EXTENSIONS = {".txt", ".rst", ".adoc"}
REPO_SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".lua",
    ".m",
    ".php",
    ".py",
    ".rb",
    ".rs",
    ".sh",
    ".sql",
    ".swift",
    ".toml",
    ".ts",
    ".tsx",
    ".vue",
    ".xml",
    ".yaml",
    ".yml",
    ".zig",
}
DEFAULT_EXCLUDED_DIRS = {
    ".10x",
    ".buoy",
    ".claude",
    ".cursor",
    ".git",
    ".hg",
    ".loom",
    ".mypy_cache",
    ".next",
    ".pi",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".turbo",
    ".turbo-search",
    "__pycache__",
    "artifacts",
    "autoresearch",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}
DEFAULT_EXCLUDED_FILENAMES = {
    "bun.lockb",
    "cargo.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}

Runner = Callable[..., subprocess.CompletedProcess[str]]
UrlOpen = Callable[..., Any]


class GitHubRepoError(RuntimeError):
    """Raised when a GitHub repository cannot be acquired safely."""


@dataclass(frozen=True)
class GitHubRepoMetadata:
    """Repository metadata needed before cloning."""

    owner: str
    repo: str
    repo_full_name: str
    repo_root_url: str
    clone_url: str
    default_branch: str
    size_kb: int | None = None
    language: str = ""
    private: bool = False


@dataclass(frozen=True)
class GitHubRepoAcquisition:
    """Local checkout details for an acquired public GitHub repository."""

    source: GitHubRepoSource
    metadata: GitHubRepoMetadata
    checkout_dir: Path
    requested_ref: str | None
    resolved_ref: str
    repo_subdir: str
    commit_sha: str
    clone_url: str
    acquisition_strategy: str = "git-shallow-clone"


@dataclass(frozen=True)
class GitHubRepoFile:
    """One selected repository file prepared for corpus generation."""

    repo_path: str
    absolute_path: Path
    size_bytes: int
    language: str
    text: str
    source_hash: str
    blob_url: str


@dataclass
class GitHubRepoCorpusStats:
    """Selection and generation counts for a repository corpus."""

    files_discovered: int = 0
    files_selected: int = 0
    file_card_pages_generated: int = 0
    files_skipped_binary: int = 0
    files_skipped_empty: int = 0
    files_skipped_oversize: int = 0
    files_skipped_filtered: int = 0
    files_skipped_limit: int = 0
    files_error: int = 0
    python_parse_fallbacks: int = 0
    non_python_fallbacks: int = 0
    repo_header_chunks: int = 0
    repo_source_chunks: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)
    limit_reached: bool = False


@dataclass(frozen=True)
class GitHubRepoCorpus:
    """Generated Markdown corpus details for repository files."""

    pages_dir: Path
    selected_files: list[GitHubRepoFile]
    page_paths: dict[str, Path]
    stats: GitHubRepoCorpusStats


def resolve_github_repo_metadata(
    source: GitHubRepoSource,
    *,
    urlopen_func: UrlOpen = urlopen,
    runner: Runner = subprocess.run,
    api_timeout: int = DEFAULT_GITHUB_API_TIMEOUT,
    git_timeout: int = DEFAULT_GIT_TIMEOUT,
) -> GitHubRepoMetadata:
    """Return clone/default-branch metadata for a public GitHub repository.

    Unauthenticated GitHub REST metadata is preferred. If that lookup is
    unavailable, fall back to ``git ls-remote --symref`` for the default branch.
    """

    try:
        return fetch_github_repo_metadata(source, urlopen_func=urlopen_func, timeout=api_timeout)
    except GitHubRepoError:
        if source.requested_ref:
            return GitHubRepoMetadata(
                owner=source.owner,
                repo=source.repo,
                repo_full_name=source.repo_full_name,
                repo_root_url=source.repo_root_url,
                clone_url=source.clone_url,
                default_branch=source.requested_ref,
            )
        try:
            default_branch = resolve_default_branch_with_git(
                source.clone_url,
                runner=runner,
                timeout=git_timeout,
            )
        except GitHubRepoError as git_error:
            raise GitHubRepoError(
                "Could not resolve GitHub repository metadata or default branch for "
                f"{source.repo_full_name}. Public repositories can be used without a token; "
                "private repositories are not supported by this command."
            ) from git_error
        return GitHubRepoMetadata(
            owner=source.owner,
            repo=source.repo,
            repo_full_name=source.repo_full_name,
            repo_root_url=source.repo_root_url,
            clone_url=source.clone_url,
            default_branch=default_branch,
        )


def fetch_github_repo_metadata(
    source: GitHubRepoSource,
    *,
    urlopen_func: UrlOpen = urlopen,
    timeout: int = DEFAULT_GITHUB_API_TIMEOUT,
) -> GitHubRepoMetadata:
    """Fetch unauthenticated public repository metadata from GitHub REST."""

    api_url = f"https://api.github.com/repos/{source.owner}/{source.repo}"
    request = Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen_func(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise GitHubRepoError(github_http_error_message(source, exc.code)) from exc
    except (URLError, OSError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise GitHubRepoError(f"Could not fetch GitHub repository metadata for {source.repo_full_name}: {exc}") from exc

    if not isinstance(payload, dict):
        raise GitHubRepoError(f"GitHub repository metadata for {source.repo_full_name} was not a JSON object")
    if bool(payload.get("private", False)):
        raise GitHubRepoError(
            f"GitHub repository {source.repo_full_name} is private; private repository ingestion is not supported"
        )
    clone_url = str(payload.get("clone_url") or source.clone_url)
    default_branch = str(payload.get("default_branch") or source.requested_ref or "")
    if not default_branch:
        raise GitHubRepoError(f"GitHub repository metadata for {source.repo_full_name} did not include a default branch")
    full_name = str(payload.get("full_name") or source.repo_full_name)
    owner, repo = split_repo_full_name(full_name, fallback_owner=source.owner, fallback_repo=source.repo)
    return GitHubRepoMetadata(
        owner=owner,
        repo=repo,
        repo_full_name=full_name,
        repo_root_url=str(payload.get("html_url") or source.repo_root_url).removesuffix("/"),
        clone_url=clone_url,
        default_branch=default_branch,
        size_kb=parse_optional_int(payload.get("size")),
        language=str(payload.get("language") or ""),
        private=False,
    )


def github_http_error_message(source: GitHubRepoSource, status_code: int) -> str:
    if status_code in {401, 403, 404}:
        return (
            f"GitHub repository {source.repo_full_name} is inaccessible in unauthenticated public mode "
            f"(HTTP {status_code}); private repositories are not supported by this command"
        )
    return f"GitHub repository metadata request for {source.repo_full_name} failed with HTTP {status_code}"


def resolve_default_branch_with_git(
    clone_url: str,
    *,
    runner: Runner = subprocess.run,
    timeout: int = DEFAULT_GIT_TIMEOUT,
) -> str:
    """Resolve a repository default branch using ``git ls-remote --symref``."""

    output = run_git_stdout(
        ["git", "ls-remote", "--symref", clone_url, "HEAD"],
        runner=runner,
        timeout=timeout,
        purpose="resolve GitHub default branch",
    )
    for line in output.splitlines():
        if not line.startswith("ref:"):
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
            branch = parts[1].removeprefix("refs/heads/")
            if branch:
                return branch
    raise GitHubRepoError(f"Could not parse default branch from git ls-remote output for {clone_url}")


def acquire_github_repo(
    source: GitHubRepoSource,
    out_dir: Path,
    *,
    urlopen_func: UrlOpen = urlopen,
    runner: Runner = subprocess.run,
    api_timeout: int = DEFAULT_GITHUB_API_TIMEOUT,
    git_timeout: int = DEFAULT_GIT_TIMEOUT,
) -> GitHubRepoAcquisition:
    """Shallow-clone a public GitHub repository into a generated checkout path."""

    if source.blob_hint is not None:
        raise GitHubRepoError(
            "GitHub blob URLs are recognized, but single-file repository ingestion is not implemented yet; "
            "pass the repository root or a /tree/<ref>/<path> URL"
        )

    metadata = resolve_github_repo_metadata(
        source,
        urlopen_func=urlopen_func,
        runner=runner,
        api_timeout=api_timeout,
        git_timeout=git_timeout,
    )
    resolved_ref = source.requested_ref or metadata.default_branch
    if not resolved_ref:
        raise GitHubRepoError(f"Could not determine a Git ref to clone for {source.repo_full_name}")

    checkout_dir = Path(out_dir) / "repo-checkout"
    if checkout_dir.exists():
        shutil.rmtree(checkout_dir)
    checkout_dir.parent.mkdir(parents=True, exist_ok=True)

    run_git_stdout(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--single-branch",
            "--branch",
            resolved_ref,
            "--no-tags",
            metadata.clone_url,
            str(checkout_dir),
        ],
        runner=runner,
        timeout=git_timeout,
        purpose=f"clone GitHub repository {source.repo_full_name}",
    )
    commit_sha = run_git_stdout(
        ["git", "-C", str(checkout_dir), "rev-parse", "HEAD"],
        runner=runner,
        timeout=git_timeout,
        purpose=f"read GitHub repository commit for {source.repo_full_name}",
    ).strip()
    if not commit_sha:
        raise GitHubRepoError(f"Could not read checked-out commit SHA for {source.repo_full_name}")

    repo_subdir = source.repo_subdir
    if repo_subdir:
        subdir = checkout_dir / repo_subdir
        if not subdir.exists() or not subdir.is_dir():
            raise GitHubRepoError(
                f"Requested GitHub repository subdirectory {repo_subdir!r} was not found in {source.repo_full_name}"
            )

    return GitHubRepoAcquisition(
        source=source,
        metadata=metadata,
        checkout_dir=checkout_dir,
        requested_ref=source.requested_ref,
        resolved_ref=resolved_ref,
        repo_subdir=repo_subdir,
        commit_sha=commit_sha,
        clone_url=metadata.clone_url,
    )


def crawl_github_repo_with_plan(source: GitHubRepoSource, options: CrawlOptions) -> CrawlExecution:
    """Acquire a repository and retain its already-built indexing plan."""

    validate_repo_chunking_options(options)
    total_started_at = observe_monotonic()
    crawl_started_at = observe_monotonic()
    emit_progress(options.progress_callback, "clone: acquiring public GitHub repository")
    acquisition = acquire_github_repo(source, options.out_dir)
    crawl_seconds = elapsed_since(crawl_started_at)
    pages_dir = options.out_dir / "pages"
    corpus_started_at = observe_monotonic()
    emit_progress(options.progress_callback, "processing: materializing repository files")
    corpus = build_github_repo_corpus(
        acquisition,
        pages_dir,
        include_paths=options.include_paths,
        exclude_paths=options.exclude_paths,
        max_files=options.max_pages,
        max_file_bytes=options.repo_max_file_bytes,
        include_search_metadata=options.repo_search_metadata,
        include_file_cards=options.repo_file_cards,
        include_oversize_file_cards=options.repo_oversize_file_cards,
    )
    corpus_write_seconds = elapsed_since(corpus_started_at)
    chunk_started_at = observe_monotonic()
    emit_progress(options.progress_callback, "chunk: chunking repository pages")
    if options.repo_chunking_arm in PYTHON_SYNTAX_ARMS:
        plan = process_syntax_repo_corpus(
            corpus,
            arm=options.repo_chunking_arm,
            limit_chunks=options.max_chunks,
            target_tokens=options.target_tokens,
            overlap_sentences=options.overlap_sentences,
        )
    else:
        plan = process_corpus(
            pages_dir,
            limit_chunks=options.max_chunks,
            target_tokens=options.target_tokens,
            overlap_sentences=options.overlap_sentences,
        )
        if options.repo_chunking_arm == "current-default":
            validate_and_count_control_chunks(
                corpus,
                plan,
                target_tokens=options.target_tokens,
                overlap_sentences=options.overlap_sentences,
            )
    chunking_seconds = elapsed_since(chunk_started_at)
    summary = build_github_repo_summary(
        source=source,
        options=options,
        acquisition=acquisition,
        corpus=corpus,
        plan=plan,
        pages_dir=pages_dir,
    )
    summary["timing"] = {
        "elapsed_seconds": elapsed_since(total_started_at),
        "sitemap_policy_seconds": 0.0,
        "crawl_seconds": crawl_seconds,
        "corpus_write_seconds": corpus_write_seconds,
        "chunking_seconds": chunking_seconds,
    }
    options.out_dir.mkdir(parents=True, exist_ok=True)
    (options.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return CrawlExecution(summary=summary, indexing_plan=plan)


def crawl_github_repo(source: GitHubRepoSource, options: CrawlOptions) -> dict[str, object]:
    """Acquire a GitHub repository, write a local corpus, and return a dry-run summary."""

    return crawl_github_repo_with_plan(source, options).summary


def validate_repo_chunking_options(options: CrawlOptions) -> None:
    arm = options.repo_chunking_arm
    if arm is None:
        return
    if arm not in REPO_CHUNKING_ARMS:
        raise GitHubRepoError(f"unsupported repository chunking arm: {arm}")
    incompatible = []
    if options.repo_search_metadata:
        incompatible.append("--repo-search-metadata")
    if options.repo_file_cards:
        incompatible.append("--repo-file-cards")
    if options.repo_oversize_file_cards:
        incompatible.append("--repo-oversize-file-cards")
    if incompatible:
        raise GitHubRepoError(
            f"--repo-chunking-arm {arm} cannot be combined with {', '.join(incompatible)}"
        )
    if options.target_tokens != DEFAULT_TARGET_TOKENS or options.overlap_sentences != DEFAULT_OVERLAP_SENTENCES:
        raise GitHubRepoError(
            "--repo-chunking-arm requires the experiment's fixed --target-tokens 300 and --overlap-sentences 2"
        )


def build_github_repo_summary(
    *,
    source: GitHubRepoSource,
    options: CrawlOptions,
    acquisition: GitHubRepoAcquisition,
    corpus: GitHubRepoCorpus,
    plan: IndexingPlan,
    pages_dir: Path,
) -> dict[str, object]:
    stats = corpus.stats
    summary: dict[str, object] = {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "source_kind": "github_repo",
        "base_url": source.repo_root_url,
        "repo_root_url": source.repo_root_url,
        "repo_owner": acquisition.metadata.owner,
        "repo_name": acquisition.metadata.repo,
        "repo_full_name": acquisition.metadata.repo_full_name,
        "repo_ref": acquisition.resolved_ref,
        "requested_ref": acquisition.requested_ref,
        "repo_subdir": acquisition.repo_subdir,
        "commit_sha": acquisition.commit_sha,
        "clone_url": acquisition.clone_url,
        "acquisition_strategy": acquisition.acquisition_strategy,
        "repo_size_kb": acquisition.metadata.size_kb,
        "primary_language": acquisition.metadata.language,
        "allowed_host": "github.com",
        "namespace_candidate": namespace_candidate(source.repo_root_url),
        "crawl_strategy": acquisition.acquisition_strategy,
        "requested_crawl_strategy": options.crawl_strategy,
        "sitemap_seed_urls": [],
        "out_dir": str(options.out_dir),
        "pages_dir": str(pages_dir),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "repo_max_file_bytes": options.repo_max_file_bytes,
        "repo_search_metadata": options.repo_search_metadata,
        "repo_file_cards": options.repo_file_cards,
        "repo_oversize_file_cards": options.repo_oversize_file_cards,
        "file_card_pages_generated": stats.file_card_pages_generated,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": stats.files_selected,
        "files_discovered": stats.files_discovered,
        "files_selected": stats.files_selected,
        "files_skipped_binary": stats.files_skipped_binary,
        "files_skipped_empty": stats.files_skipped_empty,
        "files_skipped_oversize": stats.files_skipped_oversize,
        "files_skipped_filtered": stats.files_skipped_filtered,
        "files_skipped_limit": stats.files_skipped_limit,
        "requests_count": 0,
        "robots_disallowed_count": 0,
        "blocked_requests_count": 0,
        "failed_requests_count": 0,
        "files_seen": plan.stats.files_seen,
        "files_error": plan.stats.files_error + stats.files_error,
        "chunks_generated": plan.stats.chunks_generated,
        "limit_reached": plan.limit_reached or stats.limit_reached,
        "sample_chunks": summarize_sample_chunks(plan),
        "errors": [*stats.errors, *[error.__dict__ for error in plan.stats.errors[:10]]],
    }
    if options.repo_chunking_arm is not None:
        summary.update(
            {
                "repo_chunking_arm": options.repo_chunking_arm,
                "selected_files": [repo_file.repo_path for repo_file in corpus.selected_files],
                "python_parse_fallbacks": stats.python_parse_fallbacks,
                "non_python_fallbacks": stats.non_python_fallbacks,
                "repo_header_chunks": stats.repo_header_chunks,
                "repo_source_chunks": stats.repo_source_chunks,
            }
        )
    return summary


def build_github_repo_corpus(
    acquisition: GitHubRepoAcquisition,
    pages_dir: Path,
    *,
    include_paths: Sequence[str] = (),
    exclude_paths: Sequence[str] = (),
    max_files: int | None = None,
    max_file_bytes: int = DEFAULT_REPO_MAX_FILE_BYTES,
    code_chunk_lines: int = DEFAULT_CODE_CHUNK_LINES,
    include_search_metadata: bool = False,
    include_file_cards: bool = False,
    include_oversize_file_cards: bool = False,
    runner: Runner = subprocess.run,
    git_timeout: int = DEFAULT_GIT_TIMEOUT,
) -> GitHubRepoCorpus:
    """Select repository files and write generated Markdown pages."""

    tracked_paths = list_tracked_files(acquisition.checkout_dir, runner=runner, timeout=git_timeout)
    stats = GitHubRepoCorpusStats(files_discovered=len(tracked_paths))
    selected: list[GitHubRepoFile] = []
    oversize_file_cards: list[GitHubRepoFile] = []
    pages_dir.mkdir(parents=True, exist_ok=True)
    for stale_page in pages_dir.glob("*.md"):
        stale_page.unlink()

    for repo_path in tracked_paths:
        try:
            decision = repo_file_skip_reason(
                acquisition,
                repo_path,
                include_paths=include_paths,
                exclude_paths=exclude_paths,
                max_file_bytes=max_file_bytes,
            )
            if decision is not None:
                increment_skip(stats, decision)
                if decision == "oversize" and include_oversize_file_cards:
                    oversize_card = github_repo_file_for_oversize_card(acquisition, repo_path)
                    if oversize_card is not None:
                        oversize_file_cards.append(oversize_card)
                continue
            if max_files is not None and len(selected) >= max_files:
                stats.files_skipped_limit += 1
                stats.limit_reached = True
                continue
            absolute_path = acquisition.checkout_dir / repo_path
            text = absolute_path.read_text(encoding="utf-8")
            language = language_for_path(repo_path)
            blob_url = github_blob_url(acquisition, repo_path)
            selected.append(
                GitHubRepoFile(
                    repo_path=repo_path,
                    absolute_path=absolute_path,
                    size_bytes=absolute_path.stat().st_size,
                    language=language,
                    text=text,
                    source_hash=sha256_text(text),
                    blob_url=blob_url,
                )
            )
        except UnicodeDecodeError:
            stats.files_skipped_binary += 1
        except OSError as exc:
            stats.files_error += 1
            stats.errors.append({"path": repo_path, "message": str(exc)})

    if not selected:
        raise GitHubRepoError("No eligible repository files remained after GitHub file filtering")

    crawl_timestamp = datetime.now(timezone.utc).isoformat()
    page_paths: dict[str, Path] = {}
    for index, repo_file in enumerate(selected, start=1):
        markdown = markdown_for_repo_file(
            repo_file,
            code_chunk_lines=code_chunk_lines,
            include_search_metadata=include_search_metadata,
        )
        path = pages_dir / page_filename(repo_file.blob_url, repo_file.repo_path, index)
        page_paths[repo_file.repo_path] = path
        write_repo_markdown_page(
            path,
            repo_file,
            acquisition=acquisition,
            crawl_timestamp=crawl_timestamp,
            markdown=markdown,
            title=repo_file.repo_path,
            page_kind="source",
        )

    file_card_count = 0
    if include_file_cards:
        for index, repo_file in enumerate(selected, start=len(selected) + 1):
            path = pages_dir / page_filename(repo_file.blob_url, f"{repo_file.repo_path}-file-card", index)
            write_repo_markdown_page(
                path,
                repo_file,
                acquisition=acquisition,
                crawl_timestamp=crawl_timestamp,
                markdown=markdown_for_repo_file_card(repo_file),
                title=f"{repo_file.repo_path} file metadata",
                page_kind="file_card",
            )
            file_card_count += 1
    if include_oversize_file_cards:
        start_index = len(selected) + file_card_count + 1
        for index, repo_file in enumerate(oversize_file_cards, start=start_index):
            path = pages_dir / page_filename(repo_file.blob_url, f"{repo_file.repo_path}-oversize-file-card", index)
            write_repo_markdown_page(
                path,
                repo_file,
                acquisition=acquisition,
                crawl_timestamp=crawl_timestamp,
                markdown=markdown_for_repo_file_card(repo_file),
                title=f"{repo_file.repo_path} file metadata",
                page_kind="oversize_file_card",
            )
            file_card_count += 1
    stats.file_card_pages_generated = file_card_count

    stats.files_selected = len(selected)
    return GitHubRepoCorpus(
        pages_dir=pages_dir,
        selected_files=selected,
        page_paths=page_paths,
        stats=stats,
    )


def validate_and_count_control_chunks(
    corpus: GitHubRepoCorpus,
    plan: IndexingPlan,
    *,
    target_tokens: int,
    overlap_sentences: int,
) -> None:
    """Assert the unchanged control header invariant and count final code rows."""

    for repo_file in corpus.selected_files:
        if Path(repo_file.repo_path).suffix.lower() in REPO_MARKDOWN_EXTENSIONS | REPO_PROSE_EXTENSIONS:
            continue
        document = parse_markdown_file(
            corpus.page_paths[repo_file.repo_path].resolve(),
            corpus.pages_dir.resolve(),
        )
        document_chunks = chunk_document(
            document,
            target_tokens=target_tokens,
            overlap_sentences=overlap_sentences,
        )
        expected_section = clean_markdown_inline(repo_file.repo_path)
        expected_header = (
            f"Repository file: `{repo_file.repo_path}`\n"
            f"Language: `{repo_file.language}`"
        )
        headers = [
            chunk
            for chunk in document_chunks
            if chunk.section_path == expected_section and chunk.content == expected_header
        ]
        if len(headers) != 1 or document_chunks[0] != headers[0]:
            raise RepoSyntaxChunkingError(
                f"common repository header for {repo_file.repo_path} is not exactly one unchanged final chunk"
            )
        actual = [chunk for chunk in plan.chunks if chunk.url == repo_file.blob_url]
        if actual != document_chunks:
            raise RepoSyntaxChunkingError(
                "explicit current-default requires one header and complete source chunks for every selected "
                f"code file; --max-chunks omitted part or all of {repo_file.repo_path}"
            )
        corpus.stats.repo_header_chunks += 1
        corpus.stats.repo_source_chunks += len(actual) - 1


def process_syntax_repo_corpus(
    corpus: GitHubRepoCorpus,
    *,
    arm: str,
    limit_chunks: int | None,
    target_tokens: int,
    overlap_sentences: int,
) -> IndexingPlan:
    """Build one complete token-compatible Python-aware repository plan."""

    if arm not in PYTHON_SYNTAX_ARMS:
        raise ValueError(f"unsupported Python syntax chunking arm: {arm}")
    tokenizer = load_pinned_tokenizer()
    corpus_dir = corpus.pages_dir.resolve()
    files = discover_markdown_files(corpus_dir)
    source_by_page = {
        corpus.page_paths[repo_file.repo_path].resolve(): repo_file
        for repo_file in corpus.selected_files
    }
    stats = IndexingStats()
    chunks: list[MarkdownChunk] = []

    for path in files:
        stats.files_seen += 1
        document = parse_markdown_file(path, corpus_dir)
        repo_file = source_by_page.get(path.resolve())
        if repo_file is None or Path(repo_file.repo_path).suffix.lower() in (
            REPO_MARKDOWN_EXTENSIONS | REPO_PROSE_EXTENSIONS
        ):
            document_chunks = chunk_document(
                document,
                target_tokens=target_tokens,
                overlap_sentences=overlap_sentences,
            )
            _require_compatible_rows(document_chunks, tokenizer, document, arm, "prose")
            if not document_chunks:
                stats.files_skipped_empty += 1
            chunks.extend(document_chunks)
            continue

        generic_chunks = chunk_document(
            document,
            target_tokens=target_tokens,
            overlap_sentences=overlap_sentences,
        )
        expected_section = clean_markdown_inline(repo_file.repo_path)
        expected_header = (
            f"Repository file: `{repo_file.repo_path}`\n"
            f"Language: `{repo_file.language}`"
        )
        headers = [
            chunk
            for chunk in generic_chunks
            if chunk.section_path == expected_section and chunk.content == expected_header
        ]
        if len(headers) != 1 or generic_chunks[0] != headers[0]:
            raise RepoSyntaxChunkingError(
                f"common repository header for {repo_file.repo_path} is not exactly one unchanged final chunk"
            )
        header = headers[0]
        _require_compatible_rows((header,), tokenizer, document, arm, "header")
        chunks.append(header)
        corpus.stats.repo_header_chunks += 1

        source_chunking = chunk_source(repo_file.text, repo_file.repo_path, repo_file.language, arm)
        if source_chunking.fallback == "python-parse":
            corpus.stats.python_parse_fallbacks += 1
        elif source_chunking.fallback == "non-python":
            corpus.stats.non_python_fallbacks += 1
        longest_backtick_run = max(
            (len(match.group(0)) for match in re.finditer(r"`+", repo_file.text)),
            default=0,
        )
        fence = "`" * max(3, longest_backtick_run + 1)
        language = repo_file.language if repo_file.language != "text" else ""
        doc_kind, tags = derive_doc_kind_and_tags(document.url, document.relative_path)

        def render(source_range: SourceRange, chunk_index: int = 0) -> MarkdownChunk:
            return render_syntax_source_chunk(
                document=document,
                source_chunking=source_chunking,
                source_range=source_range,
                expected_section=expected_section,
                fence=fence,
                language=language,
                chunk_index=chunk_index,
                doc_kind=doc_kind,
                tags=tags,
            )

        final_ranges: list[SourceRange] = []
        for parent in source_chunking.ranges:
            try:
                final_ranges.extend(
                    exhaustive_maximal_subdivision(
                        parent,
                        lambda candidate: render(candidate).embedding_text,
                        lambda text: exact_token_count(tokenizer, text),
                    )
                )
            except UnsplittableSourceLine as exc:
                repository = document.metadata.get("repo_full_name", "unknown-repository")
                raise TreatmentTokenBudgetError(
                    f"repository={repository} arm={arm} path={repo_file.repo_path} "
                    f"line={exc.line} tokens={exc.token_count} "
                    f"tokenizer={TOKENIZER_MODEL}@{TOKENIZER_REVISION} max={MAX_EMBEDDING_TOKENS}"
                ) from None

        for chunk_index, source_range in enumerate(final_ranges, start=1):
            chunk = render(source_range, chunk_index)
            if exact_token_count(tokenizer, chunk.embedding_text) > MAX_EMBEDDING_TOKENS:
                raise TreatmentTokenBudgetError("emitted source payload exceeds pinned token maximum")
            chunks.append(chunk)
            corpus.stats.repo_source_chunks += 1

    if limit_chunks is not None and len(chunks) > limit_chunks:
        raise RepoSyntaxChunkingError(
            "Python-aware repository plan exceeds --max-chunks; refusing partial source coverage"
        )
    stats.chunks_generated = len(chunks)
    return IndexingPlan(
        corpus_dir=corpus_dir,
        files_discovered=len(files),
        chunks=chunks,
        stats=stats,
        limit_reached=False,
    )


def render_syntax_source_chunk(
    *,
    document: MarkdownDocument,
    source_chunking: SourceChunking,
    source_range: SourceRange,
    expected_section: str,
    fence: str,
    language: str,
    chunk_index: int,
    doc_kind: str,
    tags: list[str],
) -> MarkdownChunk:
    """Render the production treatment source chunk used by counting and emission."""

    content_parts: list[str] = []
    if source_range.breadcrumbs:
        content_parts.extend(
            [f"Symbol breadcrumbs: {'; '.join(source_range.breadcrumbs)}", ""]
        )
    content_parts.extend(
        [
            f"{fence}{language}",
            source_payload(source_chunking, source_range),
            fence,
        ]
    )
    content = "\n".join(content_parts)
    return MarkdownChunk(
        id=deterministic_chunk_id(
            document.relative_path,
            chunk_index,
            document.source_hash,
            content,
        ),
        content=content,
        title=document.title,
        url=document.url,
        path=document.relative_path,
        section_path=f"{expected_section} > Lines {source_range.start}-{source_range.end}",
        chunk_index=chunk_index,
        doc_kind=doc_kind,
        tags=tags,
        source_hash=document.source_hash,
    )


def _require_compatible_rows(
    chunks: Sequence[MarkdownChunk],
    tokenizer: Tokenizer,
    document: MarkdownDocument,
    arm: str,
    row_class: str,
) -> None:
    for chunk in chunks:
        token_count = exact_token_count(tokenizer, chunk.embedding_text)
        if token_count > MAX_EMBEDDING_TOKENS:
            repository = document.metadata.get("repo_full_name", "unknown-repository")
            repo_path = document.metadata.get("repo_path", document.relative_path)
            raise TreatmentTokenBudgetError(
                f"repository={repository} arm={arm} path={repo_path} class={row_class} "
                f"tokens={token_count} tokenizer={TOKENIZER_MODEL}@{TOKENIZER_REVISION} "
                f"max={MAX_EMBEDDING_TOKENS}"
            )


def write_repo_markdown_page(
    path: Path,
    repo_file: GitHubRepoFile,
    *,
    acquisition: GitHubRepoAcquisition,
    crawl_timestamp: str,
    markdown: str,
    title: str,
    page_kind: str,
) -> None:
    frontmatter = {
        "url": repo_file.blob_url,
        "title": title,
        "status": 200,
        "content_type": "text/plain; charset=utf-8",
        "source_kind": "github_repo",
        "repo_full_name": acquisition.metadata.repo_full_name,
        "repo_owner": acquisition.metadata.owner,
        "repo_name": acquisition.metadata.repo,
        "repo_ref": acquisition.resolved_ref,
        "commit_sha": acquisition.commit_sha,
        "repo_path": repo_file.repo_path,
        "language": repo_file.language,
        "repo_page_kind": page_kind,
        "source_hash": repo_file.source_hash,
        "crawl_timestamp": crawl_timestamp,
        "fetcher": acquisition.acquisition_strategy,
    }
    lines = ["---"]
    lines.extend(f"{key}: {yaml_scalar(value)}" for key, value in frontmatter.items())
    lines.extend(["---", "", markdown.strip(), ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def list_tracked_files(
    checkout_dir: Path,
    *,
    runner: Runner = subprocess.run,
    timeout: int = DEFAULT_GIT_TIMEOUT,
) -> list[str]:
    output = run_git_stdout(
        ["git", "-C", str(checkout_dir), "ls-files", "-z"],
        runner=runner,
        timeout=timeout,
        purpose="list tracked repository files",
    )
    return [path for path in output.split("\0") if path]


def github_repo_file_for_oversize_card(
    acquisition: GitHubRepoAcquisition,
    repo_path: str,
    *,
    sample_bytes: int = OVERSIZE_FILE_CARD_SAMPLE_BYTES,
) -> GitHubRepoFile | None:
    absolute_path = acquisition.checkout_dir / repo_path
    try:
        sample = absolute_path.read_bytes()[:sample_bytes]
        if b"\0" in sample:
            return None
        text = sample.decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    return GitHubRepoFile(
        repo_path=repo_path,
        absolute_path=absolute_path,
        size_bytes=absolute_path.stat().st_size,
        language=language_for_path(repo_path),
        text=text,
        source_hash=sha256_text(text),
        blob_url=github_blob_url(acquisition, repo_path),
    )


def repo_file_skip_reason(
    acquisition: GitHubRepoAcquisition,
    repo_path: str,
    *,
    include_paths: Sequence[str],
    exclude_paths: Sequence[str],
    max_file_bytes: int,
) -> str | None:
    normalized_path = repo_path.strip("/")
    if acquisition.repo_subdir and not path_is_under(normalized_path, acquisition.repo_subdir):
        return "filtered"
    if matches_repo_patterns(normalized_path, exclude_paths):
        return "filtered"
    user_included = matches_repo_patterns(normalized_path, include_paths)
    if include_paths and not user_included:
        return "filtered"
    if not user_included and default_repo_path_excluded(normalized_path):
        return "filtered"

    absolute_path = acquisition.checkout_dir / normalized_path
    if not absolute_path.is_file():
        return "filtered"
    size = absolute_path.stat().st_size
    if size == 0:
        return "empty"
    if size > max_file_bytes:
        return "oversize"
    if is_binary_file(absolute_path):
        return "binary"
    return None


def increment_skip(stats: GitHubRepoCorpusStats, reason: str) -> None:
    if reason == "binary":
        stats.files_skipped_binary += 1
    elif reason == "empty":
        stats.files_skipped_empty += 1
    elif reason == "oversize":
        stats.files_skipped_oversize += 1
    else:
        stats.files_skipped_filtered += 1


def matches_repo_patterns(repo_path: str, patterns: Sequence[str]) -> bool:
    normalized_path = repo_path.strip("/")
    for pattern in patterns:
        normalized_pattern = normalize_repo_pattern(pattern)
        if not normalized_pattern:
            continue
        if normalized_pattern.endswith("/**"):
            prefix = normalized_pattern[:-3].rstrip("/")
            if normalized_path == prefix or normalized_path.startswith(f"{prefix}/"):
                return True
        if fnmatchcase(normalized_path, normalized_pattern):
            return True
    return False


def normalize_repo_pattern(pattern: str) -> str:
    return pattern.strip().lstrip("/").rstrip("/")


def path_is_under(repo_path: str, subdir: str) -> bool:
    normalized_subdir = subdir.strip("/")
    return not normalized_subdir or repo_path == normalized_subdir or repo_path.startswith(f"{normalized_subdir}/")


def default_repo_path_excluded(repo_path: str) -> bool:
    path = Path(repo_path)
    parts = set(path.parts)
    if parts & DEFAULT_EXCLUDED_DIRS:
        return True
    name = path.name.lower()
    if name in DEFAULT_EXCLUDED_FILENAMES:
        return True
    lower_path = repo_path.casefold()
    if name.endswith(".json") and "/data/" in lower_path and any(
        marker in lower_path for marker in ("eval", "fixture", "seed", "dataset")
    ):
        return True
    return name.endswith(".min.js") or name.endswith(".min.css") or name.endswith(".map")


def is_binary_file(path: Path) -> bool:
    sample = path.read_bytes()[:8192]
    if b"\0" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def language_for_path(repo_path: str) -> str:
    suffix = Path(repo_path).suffix.lower()
    return {
        ".adoc": "asciidoc",
        ".c": "c",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cs": "csharp",
        ".css": "css",
        ".go": "go",
        ".h": "c",
        ".hpp": "cpp",
        ".html": "html",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "jsx",
        ".json": "json",
        ".kt": "kotlin",
        ".md": "markdown",
        ".markdown": "markdown",
        ".mdx": "mdx",
        ".php": "php",
        ".py": "python",
        ".rb": "ruby",
        ".rs": "rust",
        ".rst": "rst",
        ".sh": "shell",
        ".sql": "sql",
        ".swift": "swift",
        ".toml": "toml",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".txt": "text",
        ".vue": "vue",
        ".xml": "xml",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".zig": "zig",
    }.get(suffix, suffix.removeprefix(".") or "text")


def github_blob_url(acquisition: GitHubRepoAcquisition, repo_path: str) -> str:
    ref = quote(acquisition.resolved_ref, safe="/")
    path = quote(repo_path, safe="/")
    return f"{acquisition.metadata.repo_root_url}/blob/{ref}/{path}"


def markdown_for_repo_file(
    repo_file: GitHubRepoFile,
    *,
    code_chunk_lines: int = DEFAULT_CODE_CHUNK_LINES,
    include_search_metadata: bool = False,
) -> str:
    suffix = Path(repo_file.repo_path).suffix.lower()
    if suffix in REPO_MARKDOWN_EXTENSIONS:
        return repo_file.text
    if suffix in REPO_PROSE_EXTENSIONS:
        return f"# {repo_file.repo_path}\n\n{repo_file.text.strip()}"
    return code_markdown_for_repo_file(
        repo_file,
        code_chunk_lines=code_chunk_lines,
        include_search_metadata=include_search_metadata,
    )


def code_markdown_for_repo_file(
    repo_file: GitHubRepoFile,
    *,
    code_chunk_lines: int,
    include_search_metadata: bool = False,
) -> str:
    lines = repo_file.text.splitlines()
    fence = "~~~~" if "```" in repo_file.text else "```"
    language = repo_file.language if repo_file.language != "text" else ""
    chunks = [
        f"# {repo_file.repo_path}",
        "",
        f"Repository file: `{repo_file.repo_path}`",
        f"Language: `{repo_file.language}`",
    ]
    symbol_positions = extract_repo_symbol_positions(lines, repo_file.language) if include_search_metadata else []
    if include_search_metadata:
        chunks.extend(["", *repo_search_metadata_lines(repo_file)])
    for start in range(0, len(lines), code_chunk_lines):
        end = min(start + code_chunk_lines, len(lines))
        block_lines = lines[start:end]
        block = "\n".join(block_lines)
        chunk_symbols = [symbol for line_number, symbol in symbol_positions if start < line_number <= end]
        prior_symbols = [symbol for line_number, symbol in symbol_positions if line_number <= start + 1]
        breadcrumb_symbols = chunk_symbols or prior_symbols[-3:]
        section_lines = [
            "",
            f"## Lines {start + 1}-{end}",
            "",
        ]
        if include_search_metadata and breadcrumb_symbols:
            section_lines.extend([f"Symbol breadcrumbs: {', '.join(breadcrumb_symbols[:20])}", ""])
        section_lines.extend(
            [
                f"{fence}{language}",
                block,
                fence,
            ]
        )
        chunks.extend(section_lines)
    return "\n".join(chunks)


def markdown_for_repo_file_card(repo_file: GitHubRepoFile) -> str:
    return "\n".join(
        [
            f"# File metadata: {repo_file.repo_path}",
            "",
            f"Repository file: `{repo_file.repo_path}`",
            f"Language: `{repo_file.language}`",
            "",
            *repo_search_metadata_lines(repo_file),
        ]
    )


def repo_search_metadata_lines(repo_file: GitHubRepoFile) -> list[str]:
    symbols = extract_repo_symbols(repo_file.text, repo_file.language)
    path_tokens = split_identifier_tokens(Path(repo_file.repo_path).with_suffix("").as_posix().replace("/", " "))
    symbol_tokens = split_identifier_tokens(" ".join(symbols))
    lines = [
        "Search metadata:",
        f"Path tokens: {' '.join(path_tokens[:80])}",
        f"File stem: {Path(repo_file.repo_path).stem}",
    ]
    if symbols:
        lines.append(f"Symbols: {', '.join(symbols[:80])}")
    if symbol_tokens:
        lines.append(f"Symbol tokens: {' '.join(symbol_tokens[:120])}")
    return lines


def extract_repo_symbols(text: str, language: str) -> list[str]:
    return unique_symbols(symbol for _line_number, symbol in extract_repo_symbol_positions(text.splitlines(), language))


def extract_repo_symbol_positions(lines: Sequence[str], language: str) -> list[tuple[int, str]]:
    if language != "python":
        return []
    positions: list[tuple[int, str]] = []
    pattern = re.compile(r"^\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)")
    for line_number, line in enumerate(lines, start=1):
        match = pattern.match(line)
        if match:
            positions.append((line_number, match.group(1)))
    return positions


def unique_symbols(symbols: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for symbol in symbols:
        if symbol not in seen:
            seen.add(symbol)
            unique.append(symbol)
    return unique


def split_identifier_tokens(value: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw_token in re.split(r"[^A-Za-z0-9]+", value):
        for token in re.findall(r"[A-Z]+(?=[A-Z][a-z]|$)|[A-Z]?[a-z]+|[0-9]+", raw_token):
            cleaned = token.casefold()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                tokens.append(cleaned)
    return tokens


def run_git_stdout(
    command: list[str],
    *,
    runner: Runner = subprocess.run,
    timeout: int = DEFAULT_GIT_TIMEOUT,
    purpose: str,
) -> str:
    """Run a git command and return stdout with consistent user-friendly errors."""

    try:
        result = runner(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        raise GitHubRepoError("git executable was not found; install git to ingest GitHub repository URLs") from exc
    except subprocess.TimeoutExpired as exc:
        raise GitHubRepoError(f"Timed out while trying to {purpose}") from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise GitHubRepoError(f"Could not {purpose}{detail}")
    return result.stdout or ""


def split_repo_full_name(full_name: str, *, fallback_owner: str, fallback_repo: str) -> tuple[str, str]:
    if "/" not in full_name:
        return fallback_owner, fallback_repo
    owner, repo = full_name.split("/", 1)
    return owner or fallback_owner, repo or fallback_repo


def parse_optional_int(value: object) -> int | None:
    try:
        return None if value is None or value == "" else int(value)
    except (TypeError, ValueError):
        return None
