"""Dry-run website crawling helpers for generic site RAG indexing.

This module intentionally contains no turbopuffer write path and does not read
credentials. Scrapling is imported lazily by the crawl execution path so helper
functions and tests can run without network access.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import dis
from fnmatch import fnmatchcase
from gzip import GzipFile
import hashlib
from importlib.metadata import version as distribution_version
from io import BytesIO
import json
import mimetypes
from pathlib import Path
import re
import time
from typing import Any, Callable, Literal, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urljoin, urlparse, urlunparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from buoy_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
    IndexingPlan,
    process_corpus,
    sha256_text,
)

DEFAULT_CRAWL_MAX_PAGES = 3000
DEFAULT_CRAWL_MAX_CHUNKS = 120000
DEFAULT_GITHUB_REPO_MAX_FILES = 5000
DEFAULT_GITHUB_REPO_MAX_CHUNKS = 100000
DEFAULT_GITHUB_REPO_MAX_FILE_BYTES = 50 * 1024
DEFAULT_CRAWL_CONCURRENT_REQUESTS = 2
DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN = 4
DEFAULT_CRAWL_DOWNLOAD_DELAY = 0.25
DEFAULT_CRAWL_OUT_DIR = Path("artifacts/site-crawls")
DEFAULT_CRAWL_STRATEGY = "sitemap"
CRAWL_STRATEGIES = ("sitemap", "link", "hybrid")
DEFAULT_DOCS_VERSION_POLICY = "warn"
DOCS_VERSION_POLICIES = ("warn", "all", "latest", "stable-latest", "latest-nightly")
DEFAULT_LANGUAGE_POLICY = "english"
LANGUAGE_POLICIES = ("english", "all")
MAX_REDIRECT_HOPS = 20
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})
SUPPORTED_SCRAPLING_VERSION = "0.4.9"
BLOCKED_WEBSITE_SAMPLE_REDACTION = "[redacted: blocked website crawl boundary]"


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001 - urllib hook.
        return None


_NO_REDIRECT_OPENER = build_opener(_NoRedirectHandler())


@dataclass(frozen=True)
class CrawlExecution:
    """Internal crawl result retaining the already-built indexing plan."""

    summary: dict[str, object]
    indexing_plan: IndexingPlan


def observe_monotonic() -> float | None:
    """Return a diagnostic timestamp without allowing the clock to fail work."""

    try:
        return time.monotonic()
    except Exception:
        return None


def elapsed_since(started_at: float | None) -> float:
    if started_at is None:
        return 0.0
    try:
        return max(0.0, time.monotonic() - started_at)
    except Exception:
        return 0.0
DOCS_VERSION_CURRENT_ALIASES = {"latest", "current", "stable"}
DOCS_VERSION_PREVIEW_ALIASES = {"nightly", "main", "master", "dev", "snapshot"}
DOCS_VERSION_MIN_VERSION_COUNT = 3
DOCS_VERSION_MIN_URL_COUNT = 30
LANGUAGE_POLICY_MIN_NON_ENGLISH_URL_COUNT = 20
LANGUAGE_POLICY_MIN_UNPREFIXED_URL_COUNT = 10
LANGUAGE_POLICY_MIN_NON_ENGLISH_LOCALE_COUNT = 2
LANGUAGE_POLICY_MIN_TAIL_OVERLAP_COUNT = 5
ENGLISH_LANGUAGE_PRIMARY_CODES = {"en"}
SUPPORTED_LANGUAGE_PRIMARY_CODES = {
    "ar",
    "bg",
    "ca",
    "cs",
    "da",
    "de",
    "el",
    "en",
    "es",
    "et",
    "fi",
    "fr",
    "he",
    "hi",
    "hr",
    "hu",
    "id",
    "it",
    "ja",
    "ko",
    "lt",
    "lv",
    "nl",
    "no",
    "pl",
    "pt",
    "ro",
    "ru",
    "sk",
    "sl",
    "sv",
    "th",
    "tr",
    "uk",
    "vi",
    "zh",
}
MAX_SITEMAP_ANALYSIS_URLS = 100
MAX_SITEMAP_ANALYSIS_PAGE_URLS = 100_000
SITEMAP_ANALYSIS_TIMEOUT_SECONDS = 10
ProgressCallback = Callable[[str], None]
GITHUB_HOSTS = {"github.com", "www.github.com"}
GITHUB_NON_REPO_PATHS = {
    "about",
    "collections",
    "customer-stories",
    "enterprise",
    "events",
    "explore",
    "features",
    "login",
    "marketplace",
    "new",
    "notifications",
    "orgs",
    "organizations",
    "pricing",
    "pulls",
    "search",
    "settings",
    "sponsors",
    "topics",
}
SUPPORTED_LOCAL_FILE_EXTENSIONS = (
    ".pdf",
    ".docx",
    ".pptx",
    ".xlsx",
    ".xls",
    ".csv",
    ".html",
    ".htm",
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".json",
    ".jsonl",
    ".xml",
    ".ipynb",
    ".epub",
)
LOCAL_FILE_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".xls": "application/vnd.ms-excel",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".text": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
    ".json": "application/json",
    ".jsonl": "application/jsonl",
    ".xml": "application/xml",
    ".ipynb": "application/x-ipynb+json",
    ".epub": "application/epub+zip",
}
MARKITDOWN_EXTRA_BY_EXTENSION = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".pptx": "pptx",
    ".xlsx": "xlsx",
    ".xls": "xls",
}


@dataclass(frozen=True)
class WebsiteSource:
    """An ordinary HTTP(S) website source that should use Scrapling crawling."""

    kind: Literal["website"]
    url: str

    @property
    def base_url(self) -> str:
        return self.url


@dataclass(frozen=True)
class GitHubBlobHint:
    """Structured hint for a GitHub blob URL pending single-file ingestion."""

    ref: str
    path: str


@dataclass(frozen=True)
class GitHubRepoSource:
    """A public GitHub repository URL parsed into stable local identity defaults."""

    kind: Literal["github_repo"]
    original_url: str
    repo_root_url: str
    owner: str
    repo: str
    repo_full_name: str
    site_id: str
    namespace_candidate: str
    default_out_dir: Path
    tree_ref: str | None = None
    tree_path: str | None = None
    blob_hint: GitHubBlobHint | None = None

    @property
    def base_url(self) -> str:
        return self.repo_root_url

    @property
    def clone_url(self) -> str:
        return f"{self.repo_root_url}.git"

    @property
    def requested_ref(self) -> str | None:
        if self.tree_ref is not None:
            return self.tree_ref
        if self.blob_hint is not None:
            return self.blob_hint.ref
        return None

    @property
    def repo_subdir(self) -> str:
        return self.tree_path or ""


@dataclass(frozen=True)
class PdfSource:
    """A single local PDF file parsed into stable, path-private identity defaults."""

    kind: Literal["pdf"]
    path: Path
    filename: str
    file_sha256: str
    source_id: str
    namespace_candidate: str
    default_out_dir: Path

    @property
    def base_url(self) -> str:
        return f"pdf://{self.source_id}"

    @property
    def document_url(self) -> str:
        return f"pdf://{self.source_id}/{quote(self.filename, safe='')}"

    @property
    def file_extension(self) -> str:
        return "pdf"

    @property
    def content_type(self) -> str:
        return "application/pdf"


@dataclass(frozen=True)
class LocalFileSource:
    """A single non-PDF local file parsed into stable, path-private identity defaults."""

    kind: Literal["local_file"]
    path: Path
    filename: str
    file_extension: str
    content_type: str
    file_sha256: str
    source_id: str
    namespace_candidate: str
    default_out_dir: Path

    @property
    def base_url(self) -> str:
        return f"file://{self.source_id}"

    @property
    def document_url(self) -> str:
        return f"file://{self.source_id}/{quote(self.filename, safe='')}"


LocalDocumentSource = PdfSource | LocalFileSource
Source = WebsiteSource | GitHubRepoSource | LocalDocumentSource


@dataclass(frozen=True)
class CrawlOptions:
    """Options for the local-only Scrapling dry-run crawl."""

    base_url: str
    out_dir: Path
    max_pages: int = DEFAULT_CRAWL_MAX_PAGES
    max_chunks: int = DEFAULT_CRAWL_MAX_CHUNKS
    repo_max_file_bytes: int = DEFAULT_GITHUB_REPO_MAX_FILE_BYTES
    repo_search_metadata: bool = False
    repo_file_cards: bool = False
    repo_oversize_file_cards: bool = False
    concurrent_requests: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS
    concurrent_requests_per_domain: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN
    download_delay: float = DEFAULT_CRAWL_DOWNLOAD_DELAY
    crawl_strategy: str = DEFAULT_CRAWL_STRATEGY
    docs_version_policy: str = DEFAULT_DOCS_VERSION_POLICY
    language_policy: str = DEFAULT_LANGUAGE_POLICY
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    strip_trailing_slash: bool = True
    css_selector: str | None = None
    target_tokens: int = DEFAULT_TARGET_TOKENS
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES
    progress_callback: ProgressCallback | None = None


def emit_progress(callback: ProgressCallback | None, message: str) -> None:
    if callback is not None:
        callback(message)


def progress_url_label(url: str, *, max_length: int = 80) -> str:
    text = url.strip()
    if len(text) <= max_length:
        return text
    return f"{text[: max_length - 1]}…"


def sitemap_attempt_total(sitemap_url_count: int, cap: int) -> int | None:
    if sitemap_url_count <= 0:
        return None
    return min(sitemap_url_count, cap)


def sitemap_page_progress_label(
    pages_scraped: int, *, sitemap_url_count: int, cap: int
) -> str:
    total = sitemap_attempt_total(sitemap_url_count, cap)
    if total is None:
        return f"{pages_scraped}; cap={cap}"
    if sitemap_url_count > cap:
        return f"{pages_scraped}/{total}; sitemap={sitemap_url_count}; cap={cap}"
    return f"{pages_scraped}/{total}; cap={cap}"


@dataclass(frozen=True)
class CrawledPage:
    """One page extracted by Scrapling for dry-run chunking."""

    url: str
    title: str
    markdown: str
    status: int
    content_type: str = ""
    source_hash: str = ""
    fetcher: str = "scrapling-static-spider"

    def with_hash(self) -> "CrawledPage":
        if self.source_hash:
            return self
        return CrawledPage(
            url=self.url,
            title=self.title,
            markdown=self.markdown,
            status=self.status,
            content_type=self.content_type,
            source_hash=sha256_text(self.markdown),
            fetcher=self.fetcher,
        )


def validate_base_url(url: str) -> str:
    """Return the normalized source base URL or raise ``ValueError``."""

    parsed = urlparse(url)
    if parsed.scheme == "pdf":
        if (
            not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
        ):
            raise ValueError("PDF base URL must be an internal pdf://<source-id> URI")
        return urlunparse(parsed._replace(path="", params="", query="", fragment=""))
    if parsed.scheme == "file":
        if (
            not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
        ):
            raise ValueError(
                "local file base URL must be an internal file://<source-id> URI"
            )
        return urlunparse(parsed._replace(path="", params="", query="", fragment=""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute http(s) URL")
    normalized = parsed._replace(fragment="")
    return urlunparse(normalized)


def host_from_url(url: str) -> str:
    """Return the hostname from an absolute HTTP(S) URL."""

    parsed = urlparse(validate_base_url(url))
    return (parsed.hostname or parsed.netloc).lower()


def allowed_domains_for_url(url: str) -> set[str]:
    """Return domain forms accepted by Scrapling's engine and link filters."""

    parsed = urlparse(validate_base_url(url))
    host = (parsed.hostname or parsed.netloc).lower()
    netloc = parsed.netloc.lower()
    return {host, netloc}


def origin_from_url(url: str) -> str:
    parsed = urlparse(validate_base_url(url))
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def namespace_candidate(base_url: str) -> str:
    """Return the deterministic dry-run namespace candidate for a source."""

    if is_local_document_base_url(base_url):
        return f"{source_id_for_url(base_url)}-v1"
    source = detect_source(base_url)
    if isinstance(source, (GitHubRepoSource, PdfSource, LocalFileSource)):
        return source.namespace_candidate
    host = host_from_url(source.url)
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
    return f"site-{slug}-v1"


def source_id_for_url(base_url: str) -> str:
    """Return the deterministic local source/site ID for a supported URL or local file path."""

    if is_pdf_base_url(base_url):
        return safe_slug(urlparse(validate_base_url(base_url)).netloc, fallback="pdf")
    if is_file_base_url(base_url):
        return safe_slug(urlparse(validate_base_url(base_url)).netloc, fallback="file")
    source = detect_source(base_url)
    if isinstance(source, GitHubRepoSource):
        return source.site_id
    if isinstance(source, (PdfSource, LocalFileSource)):
        return source.source_id
    return safe_slug(host_from_url(source.url), fallback="site")


def default_out_dir(base_url: str) -> Path:
    source = (
        detect_source(base_url) if not is_local_document_base_url(base_url) else None
    )
    if isinstance(source, (GitHubRepoSource, PdfSource, LocalFileSource)):
        return source.default_out_dir
    return DEFAULT_CRAWL_OUT_DIR / source_id_for_url(base_url)


def sitemap_seed_urls(base_url: str) -> list[str]:
    """Return robots/conventional sitemap URLs to try before link crawling."""

    origin = origin_from_url(base_url)
    return [
        f"{origin}/robots.txt",
        f"{origin}/sitemap.xml",
        f"{origin}/sitemap_index.xml",
    ]


def safe_slug(value: str, *, fallback: str = "page") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or fallback


def is_pdf_base_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "pdf" and bool(parsed.netloc)


def is_file_base_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "file" and bool(parsed.netloc)


def is_local_document_base_url(value: str) -> bool:
    return is_pdf_base_url(value) or is_file_base_url(value)


def is_supported_local_file_extension(extension: str) -> bool:
    return extension.lower() in SUPPORTED_LOCAL_FILE_EXTENSIONS


def looks_like_local_pdf_path(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "pdf", "file"}:
        return False
    return Path(value).expanduser().suffix.lower() == ".pdf"


def looks_like_supported_local_file_path(value: str) -> bool:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "pdf", "file"}:
        return False
    return is_supported_local_file_extension(Path(value).expanduser().suffix)


def unsupported_local_file_error(path: Path) -> str:
    suffix = path.suffix.lower() or "<none>"
    supported = ", ".join(SUPPORTED_LOCAL_FILE_EXTENSIONS)
    return f"unsupported local file type {suffix!r}; supported extensions: {supported}"


def local_file_content_type(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in LOCAL_FILE_CONTENT_TYPES:
        return LOCAL_FILE_CONTENT_TYPES[extension]
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def pdf_source_from_path(value: str | Path) -> PdfSource:
    path = Path(value).expanduser()
    if not path.is_file():
        raise ValueError(
            f"local PDF path must point to an existing regular file: {value}"
        )
    file_sha256 = sha256_file(path)
    filename_slug = safe_slug(path.stem, fallback="document")
    source_id = f"pdf-{filename_slug}-{file_sha256[:16]}"
    return PdfSource(
        kind="pdf",
        path=path,
        filename=path.name,
        file_sha256=file_sha256,
        source_id=source_id,
        namespace_candidate=f"{source_id}-v1",
        default_out_dir=DEFAULT_CRAWL_OUT_DIR / source_id,
    )


def local_file_source_from_path(value: str | Path) -> LocalDocumentSource:
    path = Path(value).expanduser()
    extension = path.suffix.lower()
    if not is_supported_local_file_extension(extension):
        raise ValueError(unsupported_local_file_error(path))
    if extension == ".pdf":
        return pdf_source_from_path(path)
    if not path.is_file():
        raise ValueError(
            f"local file path must point to an existing regular file: {value}"
        )
    file_sha256 = sha256_file(path)
    filename_slug = safe_slug(path.stem, fallback="document")
    extension_slug = safe_slug(extension.lstrip("."), fallback="file")
    source_id = f"file-{extension_slug}-{filename_slug}-{file_sha256[:16]}"
    return LocalFileSource(
        kind="local_file",
        path=path,
        filename=path.name,
        file_extension=extension_slug,
        content_type=local_file_content_type(path),
        file_sha256=file_sha256,
        source_id=source_id,
        namespace_candidate=f"{source_id}-v1",
        default_out_dir=DEFAULT_CRAWL_OUT_DIR / source_id,
    )


def detect_source(url: str) -> Source:
    """Classify a source as a website, public GitHub repository, or local file."""

    parsed = urlparse(url)
    if looks_like_supported_local_file_path(url):
        return local_file_source_from_path(url)
    local_path = Path(url).expanduser()
    if parsed.scheme not in {"http", "https", "pdf", "file"} and local_path.is_file():
        raise ValueError(unsupported_local_file_error(local_path))
    normalized = validate_base_url(url)
    if is_pdf_base_url(normalized):
        raise ValueError(
            "pass the local PDF filepath, not the internal pdf:// source URI"
        )
    if is_file_base_url(normalized):
        raise ValueError(
            "pass the local file filepath, not the internal file:// source URI"
        )
    github_source = parse_github_repo_url(normalized)
    if github_source is not None:
        return github_source
    return WebsiteSource(kind="website", url=normalized)


def parse_github_repo_url(url: str) -> GitHubRepoSource | None:
    """Parse supported public GitHub repository URL forms.

    Non-repository GitHub global pages return ``None`` so they can continue
    through ordinary website handling. URLs that look like a repository but point
    at unsupported repo UI subpages raise clearly so callers do not accidentally
    crawl rendered GitHub chrome as source content.
    """

    normalized = validate_base_url(url)
    parsed = urlparse(normalized)
    host = (parsed.hostname or parsed.netloc).lower()
    if host not in GITHUB_HOSTS:
        return None

    segments = [unquote(segment) for segment in parsed.path.split("/") if segment]
    if not segments:
        return None
    if segments[0].lower() in GITHUB_NON_REPO_PATHS:
        return None
    if len(segments) < 2:
        raise ValueError(
            "GitHub repository URL must include both owner and repo, e.g. https://github.com/owner/repo"
        )

    owner = segments[0]
    repo = segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo or owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError(
            "GitHub repository URL must include non-empty owner and repo segments"
        )

    repo_root_url = f"https://github.com/{owner}/{repo}"
    repo_full_name = f"{owner}/{repo}"
    site_id = safe_slug(f"github-{owner}-{repo}", fallback="github-repo")
    source = GitHubRepoSource(
        kind="github_repo",
        original_url=normalized,
        repo_root_url=repo_root_url,
        owner=owner,
        repo=repo,
        repo_full_name=repo_full_name,
        site_id=site_id,
        namespace_candidate=f"{site_id}-v1",
        default_out_dir=DEFAULT_CRAWL_OUT_DIR / site_id,
    )

    remaining = segments[2:]
    if not remaining:
        return source

    qualifier = remaining[0]
    if qualifier == "tree":
        if len(remaining) < 2 or not remaining[1]:
            raise ValueError(
                "GitHub tree URL must include a branch or ref after /tree/"
            )
        return GitHubRepoSource(
            kind="github_repo",
            original_url=normalized,
            repo_root_url=repo_root_url,
            owner=owner,
            repo=repo,
            repo_full_name=repo_full_name,
            site_id=site_id,
            namespace_candidate=f"{site_id}-v1",
            default_out_dir=DEFAULT_CRAWL_OUT_DIR / site_id,
            tree_ref=remaining[1],
            tree_path="/".join(remaining[2:]) or None,
        )
    if qualifier == "blob":
        if len(remaining) < 3 or not remaining[1] or not remaining[2]:
            raise ValueError(
                "GitHub blob URL must include a branch/ref and file path after /blob/"
            )
        return GitHubRepoSource(
            kind="github_repo",
            original_url=normalized,
            repo_root_url=repo_root_url,
            owner=owner,
            repo=repo,
            repo_full_name=repo_full_name,
            site_id=site_id,
            namespace_candidate=f"{site_id}-v1",
            default_out_dir=DEFAULT_CRAWL_OUT_DIR / site_id,
            blob_hint=GitHubBlobHint(ref=remaining[1], path="/".join(remaining[2:])),
        )

    raise ValueError(
        "Unsupported GitHub repository URL path; pass the repository root or a /tree/<ref>/<path> URL"
    )


def normalize_path_pattern(pattern: str) -> str:
    value = pattern.strip()
    if not value:
        return value
    if not value.startswith("/"):
        value = f"/{value}"
    if value != "/" and value.endswith("/"):
        value = value.rstrip("/")
    return value


def normalize_url_path(path: str, *, strip_trailing_slash: bool = True) -> str:
    value = path or "/"
    if not value.startswith("/"):
        value = f"/{value}"
    if strip_trailing_slash and value != "/":
        value = value.rstrip("/")
    return value or "/"


def canonicalize_page_url(url: str, *, strip_trailing_slash: bool = True) -> str:
    parsed = urlparse(url)
    path = normalize_url_path(parsed.path, strip_trailing_slash=strip_trailing_slash)
    return urlunparse(parsed._replace(path=path, fragment=""))


def path_matches_pattern(path: str, pattern: str) -> bool:
    normalized_pattern = normalize_path_pattern(pattern)
    if not normalized_pattern:
        return False
    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3].rstrip("/") or "/"
        return path == prefix or path.startswith(f"{prefix}/")
    return fnmatchcase(path, normalized_pattern)


def url_allowed_by_path_filters(
    url: str,
    *,
    include_paths: Sequence[str] = (),
    exclude_paths: Sequence[str] = (),
    strip_trailing_slash: bool = True,
) -> bool:
    path = normalize_url_path(
        urlparse(url).path, strip_trailing_slash=strip_trailing_slash
    )
    includes = [
        normalize_path_pattern(pattern)
        for pattern in include_paths
        if normalize_path_pattern(pattern)
    ]
    excludes = [
        normalize_path_pattern(pattern)
        for pattern in exclude_paths
        if normalize_path_pattern(pattern)
    ]
    if includes and not any(
        path_matches_pattern(path, pattern) for pattern in includes
    ):
        return False
    return not any(path_matches_pattern(path, pattern) for pattern in excludes)


def local_xml_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def increment_boundary_stat(stats: dict[str, object] | None, key: str) -> None:
    if stats is not None:
        stats[key] = int(stats.get(key, 0) or 0) + 1


def redirect_location(response: Any) -> str | None:
    if int(getattr(response, "status", getattr(response, "code", 0)) or 0) not in REDIRECT_STATUSES:
        return None
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    location = headers.get("location") or headers.get("Location")
    return str(location) if location else None


def fetch_url_bytes(
    url: str,
    *,
    timeout: int = SITEMAP_ANALYSIS_TIMEOUT_SECONDS,
    allowed_host: str | None = None,
    boundary_stats: dict[str, object] | None = None,
) -> bytes | None:
    """Fetch bytes while checking each redirect before its destination request."""

    current_url = url
    for redirect_hops in range(MAX_REDIRECT_HOPS + 1):
        if allowed_host is not None and not same_host_url(current_url, allowed_host):
            increment_boundary_stat(boundary_stats, "blocked_redirect_count")
            return None
        try:
            request = Request(
                current_url,
                headers={"User-Agent": "buoy-search-sitemap-analysis/0.2"},
            )
            try:
                response = _NO_REDIRECT_OPENER.open(request, timeout=timeout)
            except HTTPError as error:
                response = error
            with response:
                final_url = str(response.geturl())
                if allowed_host is not None and not same_host_url(final_url, allowed_host):
                    increment_boundary_stat(boundary_stats, "blocked_redirect_count")
                    return None
                location = redirect_location(response)
                if location is None:
                    return response.read() if int(response.status) == 200 else None
                if redirect_hops >= MAX_REDIRECT_HOPS:
                    increment_boundary_stat(boundary_stats, "blocked_redirect_count")
                    return None
                target = urljoin(final_url, location)
                if allowed_host is not None and not same_host_url(target, allowed_host):
                    increment_boundary_stat(boundary_stats, "blocked_redirect_count")
                    return None
                current_url = target
        except (HTTPError, URLError, TimeoutError, OSError, ValueError):
            return None
    return None


def sitemap_urls_from_robots(body: bytes) -> list[str]:
    text = body.decode("utf-8", errors="replace")
    urls: list[str] = []
    for line in text.splitlines():
        name, sep, value = line.partition(":")
        if sep and name.strip().lower() == "sitemap" and value.strip():
            urls.append(value.strip())
    return urls


def maybe_decompress_sitemap(body: bytes, url: str) -> bytes:
    if urlparse(url).path.endswith(".gz") or body[:2] == b"\x1f\x8b":
        try:
            out = bytearray()
            with GzipFile(fileobj=BytesIO(body)) as gzip_file:
                while chunk := gzip_file.read1(8192):
                    out.extend(chunk)
            return bytes(out)
        except OSError:
            return body
    return body


def sitemap_locations_from_xml(body: bytes, url: str) -> tuple[list[str], list[str]]:
    from xml.etree import ElementTree

    try:
        root = ElementTree.fromstring(maybe_decompress_sitemap(body, url))
    except ElementTree.ParseError:
        return [], []

    root_name = local_xml_name(root.tag)
    page_urls: list[str] = []
    child_sitemaps: list[str] = []
    if root_name == "urlset":
        for url_el in root:
            if local_xml_name(url_el.tag) != "url":
                continue
            for child in url_el:
                if (
                    local_xml_name(child.tag) == "loc"
                    and child.text
                    and child.text.strip()
                ):
                    page_urls.append(child.text.strip())
                    break
    elif root_name == "sitemapindex":
        for sitemap_el in root:
            if local_xml_name(sitemap_el.tag) != "sitemap":
                continue
            for child in sitemap_el:
                if (
                    local_xml_name(child.tag) == "loc"
                    and child.text
                    and child.text.strip()
                ):
                    child_sitemaps.append(child.text.strip())
                    break
    return page_urls, child_sitemaps


def same_host_url(url: str, allowed_host: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme in {"http", "https"}
        and (parsed.hostname or parsed.netloc).lower() == allowed_host
    )


def discover_sitemap_page_urls(
    options: CrawlOptions, *, boundary_stats: dict[str, object] | None = None
) -> list[str]:
    allowed_host = host_from_url(options.base_url)
    queue = sitemap_seed_urls(options.base_url)
    visited: set[str] = set()
    page_urls: list[str] = []
    seen_pages: set[str] = set()

    def enqueue_declarations(values: Sequence[str], declaration_url: str) -> None:
        for value in values:
            candidate = urljoin(declaration_url, value)
            if not same_host_url(candidate, allowed_host):
                if urlparse(candidate).scheme in {"http", "https"}:
                    increment_boundary_stat(boundary_stats, "blocked_discovery_count")
                continue
            if candidate not in visited:
                queue.append(candidate)

    while (
        queue
        and len(visited) < MAX_SITEMAP_ANALYSIS_URLS
        and len(page_urls) < MAX_SITEMAP_ANALYSIS_PAGE_URLS
    ):
        url = queue.pop(0)
        if url in visited or not same_host_url(url, allowed_host):
            continue
        visited.add(url)
        body = fetch_url_bytes(
            url, allowed_host=allowed_host, boundary_stats=boundary_stats
        )
        if body is None:
            continue
        if urlparse(url).path.endswith("/robots.txt"):
            enqueue_declarations(sitemap_urls_from_robots(body), url)
            continue

        pages, child_sitemaps = sitemap_locations_from_xml(body, url)
        enqueue_declarations(child_sitemaps, url)
        for declared_page_url in pages:
            page_url = urljoin(url, declared_page_url)
            if not same_host_url(page_url, allowed_host):
                if urlparse(page_url).scheme in {"http", "https"}:
                    increment_boundary_stat(boundary_stats, "blocked_discovery_count")
                continue
            if not url_allowed_by_path_filters(
                page_url,
                include_paths=options.include_paths,
                exclude_paths=options.exclude_paths,
                strip_trailing_slash=options.strip_trailing_slash,
            ):
                continue
            canonical = page_identity_url(
                page_url, strip_trailing_slash=options.strip_trailing_slash
            )
            if canonical in seen_pages:
                continue
            seen_pages.add(canonical)
            page_urls.append(canonical)
            if len(page_urls) >= MAX_SITEMAP_ANALYSIS_PAGE_URLS:
                break
    return page_urls


def parse_docs_semver(segment: str) -> tuple[int, ...] | None:
    value = segment.lower().removeprefix("v")
    if not re.fullmatch(r"\d+(?:\.\d+){1,3}(?:[-+][a-z0-9.-]+)?", value):
        return None
    core = re.split(r"[-+]", value, maxsplit=1)[0]
    return tuple(int(part) for part in core.split("."))


def docs_version_kind(segment: str) -> str | None:
    value = segment.lower()
    if value in DOCS_VERSION_CURRENT_ALIASES:
        return "current"
    if value in DOCS_VERSION_PREVIEW_ALIASES:
        return "preview"
    if parse_docs_semver(value) is not None:
        return "semver"
    return None


def version_sort_key(version: str) -> tuple[int, tuple[int, ...] | str]:
    semver = parse_docs_semver(version)
    if semver is not None:
        return (0, semver)
    return (1, version.lower())


def highest_semver_version(versions: Sequence[str]) -> str | None:
    semver_versions = [(parse_docs_semver(version), version) for version in versions]
    semver_versions = [
        (key, version) for key, version in semver_versions if key is not None
    ]
    if not semver_versions:
        return None
    return max(semver_versions, key=lambda item: item[0])[1]


def selected_docs_versions(versions: Sequence[str], policy: str) -> list[str]:
    version_set = set(versions)
    current = sorted(version_set & DOCS_VERSION_CURRENT_ALIASES)
    preview = sorted(version_set & DOCS_VERSION_PREVIEW_ALIASES)
    stable_latest = highest_semver_version(versions)
    if policy == "stable-latest":
        return [stable_latest] if stable_latest else current[:1] or preview[:1]
    if policy == "latest-nightly":
        selected = current + preview
        if not selected and stable_latest:
            selected.append(stable_latest)
        return selected
    if policy == "latest":
        if current:
            return current
        return [stable_latest] if stable_latest else preview[:1]
    return []


def path_docs_version_parts(path: str) -> tuple[str, str] | None:
    segments = [segment for segment in normalize_url_path(path).split("/") if segment]
    for index in range(len(segments) - 1):
        version = segments[index + 1]
        if docs_version_kind(version) is None:
            continue
        root_path = "/" + "/".join(segments[: index + 1])
        return root_path, version
    return None


def normalize_language_prefix(segment: str) -> str | None:
    value = segment.lower().replace("_", "-")
    if not re.fullmatch(r"[a-z]{2}(?:-[a-z]{2}|-[a-z]{4}|-\d{3})?", value):
        return None
    primary = value.split("-", 1)[0]
    if primary not in SUPPORTED_LANGUAGE_PRIMARY_CODES:
        return None
    return value


def language_prefix_and_tail_for_path(path: str) -> tuple[str | None, str]:
    normalized_path = normalize_url_path(path)
    segments = [segment for segment in normalized_path.split("/") if segment]
    if not segments:
        return None, "/"
    prefix = normalize_language_prefix(unquote(segments[0]))
    if prefix is None:
        return None, normalized_path
    tail = "/" + "/".join(segments[1:]) if len(segments) > 1 else "/"
    return prefix, tail


def language_prefix_for_path(path: str) -> str | None:
    prefix, _tail = language_prefix_and_tail_for_path(path)
    return prefix


def is_english_language_prefix(prefix: str) -> bool:
    return prefix.split("-", 1)[0] in ENGLISH_LANGUAGE_PRIMARY_CODES


def analyze_language_urls(urls: Sequence[str], *, policy: str) -> dict[str, object]:
    if policy not in LANGUAGE_POLICIES:
        raise ValueError(
            f"language policy must be one of: {', '.join(LANGUAGE_POLICIES)}"
        )

    url_count_by_language: dict[str, int] = {}
    tail_paths_by_language: dict[str, set[str]] = {}
    english_tail_paths: set[str] = set()
    unprefixed_url_count = 0
    for url in urls:
        prefix, tail_path = language_prefix_and_tail_for_path(urlparse(url).path)
        if prefix is None:
            unprefixed_url_count += 1
            english_tail_paths.add(tail_path)
            continue
        url_count_by_language[prefix] = url_count_by_language.get(prefix, 0) + 1
        tail_paths_by_language.setdefault(prefix, set()).add(tail_path)
        if is_english_language_prefix(prefix):
            english_tail_paths.add(tail_path)

    english_locales = sorted(
        prefix for prefix in url_count_by_language if is_english_language_prefix(prefix)
    )
    non_english_locales = sorted(
        prefix
        for prefix in url_count_by_language
        if not is_english_language_prefix(prefix)
    )
    non_english_url_count = sum(
        url_count_by_language[prefix] for prefix in non_english_locales
    )
    overlap_count_by_language = {
        prefix: len(tail_paths_by_language.get(prefix, set()) & english_tail_paths)
        for prefix in non_english_locales
    }
    has_english_content = (
        bool(english_locales)
        or unprefixed_url_count >= LANGUAGE_POLICY_MIN_UNPREFIXED_URL_COUNT
    )
    has_language_family_signal = len(
        non_english_locales
    ) >= LANGUAGE_POLICY_MIN_NON_ENGLISH_LOCALE_COUNT or any(
        count >= LANGUAGE_POLICY_MIN_TAIL_OVERLAP_COUNT
        for count in overlap_count_by_language.values()
    )
    detected = bool(
        non_english_locales
        and has_english_content
        and non_english_url_count >= LANGUAGE_POLICY_MIN_NON_ENGLISH_URL_COUNT
        and has_language_family_signal
    )
    added_excludes = (
        [f"/{prefix}/**" for prefix in non_english_locales]
        if detected and policy == "english"
        else []
    )
    return {
        "detected": detected,
        "policy": policy,
        "applied": bool(added_excludes),
        "english_locales": english_locales,
        "excluded_languages": non_english_locales if added_excludes else [],
        "non_english_locales": non_english_locales,
        "localized_url_count": sum(url_count_by_language.values()),
        "non_english_url_count": non_english_url_count,
        "unprefixed_url_count": unprefixed_url_count,
        "url_count_by_language": dict(sorted(url_count_by_language.items())),
        "tail_overlap_count_by_language": dict(
            sorted(overlap_count_by_language.items())
        ),
        "selected_languages": ["unprefixed"] + english_locales
        if detected and policy == "english"
        else [],
        "added_exclude_paths": added_excludes,
    }


def analyze_docs_version_urls(urls: Sequence[str], *, policy: str) -> dict[str, object]:
    groups: dict[str, dict[str, set[str]]] = {}
    for url in urls:
        parts = path_docs_version_parts(urlparse(url).path)
        if parts is None:
            continue
        root_path, version = parts
        groups.setdefault(root_path, {}).setdefault(version, set()).add(url)

    candidates: list[tuple[int, int, str, dict[str, set[str]]]] = []
    for root_path, versions in groups.items():
        version_count = len(versions)
        url_count = sum(len(values) for values in versions.values())
        if (
            version_count >= DOCS_VERSION_MIN_VERSION_COUNT
            and url_count >= DOCS_VERSION_MIN_URL_COUNT
        ):
            candidates.append((url_count, version_count, root_path, versions))
    if not candidates:
        return {"detected": False, "policy": policy}

    _url_count, _version_count, root_path, versions = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    version_names = sorted(versions, key=version_sort_key)
    selected = selected_docs_versions(version_names, policy)
    excluded = (
        [version for version in version_names if version not in selected]
        if selected
        else []
    )
    added_excludes = [f"{root_path}/{version}/**" for version in excluded]
    report: dict[str, object] = {
        "detected": True,
        "policy": policy,
        "root_path": root_path,
        "version_count": len(version_names),
        "versions": version_names,
        "versioned_url_count": sum(len(values) for values in versions.values()),
        "url_count_by_version": {
            version: len(versions[version]) for version in version_names
        },
        "selected_versions": selected,
        "excluded_versions": excluded,
        "added_exclude_paths": added_excludes,
        "applied": bool(
            selected and policy in {"latest", "stable-latest", "latest-nightly"}
        ),
    }
    if policy == "warn":
        report["suggested_policy"] = "latest"
    return report


def docs_version_block_message(report: dict[str, object]) -> str | None:
    if (
        not report.get("detected")
        or report.get("applied")
        or report.get("policy") != "warn"
    ):
        return None
    suggested = report.get("suggested_policy")
    if not suggested:
        return None
    return (
        "detected versioned docs "
        f"under {report.get('root_path')} "
        f"({report.get('version_count')} versions, {report.get('versioned_url_count')} sitemap URLs); "
        "stopping before page crawl. "
        f"Rerun with --docs-version-policy {suggested} to keep current docs and prune old versions, "
        "or --docs-version-policy all to keep every version."
    )


def apply_docs_version_policy(
    options: CrawlOptions,
    *,
    sitemap_page_urls: Sequence[str] | None = None,
) -> tuple[CrawlOptions, dict[str, object]]:
    policy = options.docs_version_policy
    if policy not in DOCS_VERSION_POLICIES:
        raise ValueError(
            f"docs version policy must be one of: {', '.join(DOCS_VERSION_POLICIES)}"
        )
    if policy == "all" or options.crawl_strategy == "link":
        return options, {"detected": False, "policy": policy}

    urls = (
        list(sitemap_page_urls)
        if sitemap_page_urls is not None
        else discover_sitemap_page_urls(options)
    )
    report = analyze_docs_version_urls(urls, policy=policy)
    if not report.get("applied"):
        return options, report

    existing_excludes = list(options.exclude_paths)
    added_excludes = [str(pattern) for pattern in report.get("added_exclude_paths", [])]
    for pattern in added_excludes:
        if pattern not in existing_excludes:
            existing_excludes.append(pattern)
    return replace(options, exclude_paths=tuple(existing_excludes)), report


def apply_language_policy(
    options: CrawlOptions,
    *,
    sitemap_page_urls: Sequence[str] | None = None,
) -> tuple[CrawlOptions, dict[str, object]]:
    policy = options.language_policy
    if policy not in LANGUAGE_POLICIES:
        raise ValueError(
            f"language policy must be one of: {', '.join(LANGUAGE_POLICIES)}"
        )
    if policy == "all" or options.crawl_strategy == "link":
        return options, {"detected": False, "policy": policy}

    urls = (
        list(sitemap_page_urls)
        if sitemap_page_urls is not None
        else discover_sitemap_page_urls(options)
    )
    report = analyze_language_urls(urls, policy=policy)
    if not report.get("applied"):
        return options, report

    existing_excludes = list(options.exclude_paths)
    added_excludes = [str(pattern) for pattern in report.get("added_exclude_paths", [])]
    for pattern in added_excludes:
        if pattern not in existing_excludes:
            existing_excludes.append(pattern)
    return replace(options, exclude_paths=tuple(existing_excludes)), report


def yaml_scalar(value: object) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def page_filename(url: str, title: str, index: int) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    path_slug = safe_slug(
        parsed.path.strip("/") or title or parsed.netloc, fallback=f"page-{index}"
    )
    return f"{index:04d}-{path_slug}-{digest}.md"


def markdown_from_response(response: Any, *, css_selector: str | None = None) -> str:
    """Use Scrapling's conversion path to extract Markdown from a response."""

    from scrapling.core.shell import Convertor

    parts = Convertor._extract_content(  # noqa: SLF001 - Scrapling's CLI uses this extraction helper.
        response,
        extraction_type="markdown",
        css_selector=css_selector,
        main_content_only=True,
    )
    return "".join(parts).strip()


def crawled_page_from_response(
    response: Any,
    *,
    css_selector: str | None = None,
    strip_trailing_slash: bool = True,
) -> CrawledPage | None:
    """Convert a Scrapling response into a local dry-run page item."""

    if getattr(response, "status", None) != 200:
        return None
    try:
        markdown = markdown_from_response(response, css_selector=css_selector)
    except ValueError:
        return None
    if not markdown:
        return None
    title = (
        response.css("title::text").get()
        or response.css("h1::text").get()
        or response.url
    )
    content_type = ""
    headers = getattr(response, "headers", None)
    if headers:
        content_type = headers.get("content-type") or headers.get("Content-Type") or ""
    return CrawledPage(
        url=canonicalize_page_url(
            str(response.url), strip_trailing_slash=strip_trailing_slash
        ),
        title=str(title).strip(),
        markdown=markdown,
        status=int(response.status),
        content_type=str(content_type),
        source_hash=sha256_text(markdown),
    )


def _loaded_method_names(function: Callable[..., object]) -> list[str]:
    return [
        str(instruction.argval)
        for instruction in dis.get_instructions(function)
        if instruction.opname in {"LOAD_ATTR", "LOAD_METHOD"}
    ]


def _assert_scrapling_runtime_shape() -> None:
    """Abort if the pinned Scrapling lifecycle no longer enforces our hooks."""

    installed_version = distribution_version("scrapling")
    if installed_version != SUPPORTED_SCRAPLING_VERSION:
        raise RuntimeError(
            "Website crawling requires Scrapling "
            f"{SUPPORTED_SCRAPLING_VERSION}; found {installed_version}."
        )

    from scrapling.spiders.engine import CrawlerEngine
    from scrapling.spiders.robotstxt import RobotsTxtManager
    from scrapling.spiders.session import SessionManager

    required_names = (
        (CrawlerEngine._prefetch_robots_txt, {"_robots_manager", "prefetch"}),
        (
            CrawlerEngine._process_request,
            {"_robots_manager", "can_fetch", "session_manager", "fetch"},
        ),
        (RobotsTxtManager._get_parser, {"_fetch_fn"}),
        (SessionManager.fetch, {"_session_kwargs", "_make_request"}),
    )
    for function, names in required_names:
        code = getattr(function, "__code__", None)
        if code is None or not names.issubset(set(code.co_names)):
            raise RuntimeError(
                "Scrapling's website crawl integration changed; refusing to request pages."
            )

    try:
        lifecycle_names = _loaded_method_names(CrawlerEngine.crawl)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            "Scrapling's website crawl lifecycle changed; refusing to request pages."
        ) from exc
    try:
        lifecycle_positions = [
            lifecycle_names.index(name)
            for name in ("on_start", "_prefetch_robots_txt", "start_requests")
        ]
    except ValueError as exc:
        raise RuntimeError(
            "Scrapling's website crawl lifecycle changed; refusing to request pages."
        ) from exc
    if lifecycle_positions != sorted(lifecycle_positions):
        raise RuntimeError(
            "Scrapling's robots lifecycle is no longer installed before requests; refusing to crawl."
        )


class _ExactHostSpiderMixin:
    """Disable client redirects and validate each hop before scheduling it."""

    _allowed_host: str
    _include_paths: Sequence[str]
    _exclude_paths: Sequence[str]
    _strip_trailing_slash: bool

    def _init_exact_host_boundary(self) -> None:
        self._blocked_discovery_count = 0
        self._blocked_redirect_count = 0

    def configure_sessions(self, manager) -> None:  # noqa: ANN001 - Scrapling hook.
        from scrapling.fetchers import FetcherSession

        _assert_scrapling_runtime_shape()
        session = FetcherSession(follow_redirects=False)
        if getattr(session, "_default_follow_redirects", None) is not False:
            raise RuntimeError(
                "Scrapling did not disable automatic redirects; refusing to crawl."
            )
        manager.add("default", session)
        if manager.get("default") is not session:
            raise RuntimeError(
                "Scrapling did not retain the redirect-safe session; refusing to crawl."
            )

    async def on_start(self, resuming: bool = False) -> None:
        _assert_scrapling_runtime_shape()
        from scrapling.spiders.engine import CrawlerEngine
        from scrapling.spiders.robotstxt import RobotsTxtManager
        from scrapling.spiders.session import SessionManager

        engine = getattr(self, "_engine", None)
        if not isinstance(engine, CrawlerEngine) or engine.spider is not self:
            raise RuntimeError(
                "Scrapling's crawler engine integration changed; refusing to request pages."
            )
        if (
            not isinstance(engine.session_manager, SessionManager)
            or engine.session_manager is not self._session_manager
            or not callable(getattr(engine.session_manager, "fetch", None))
        ):
            raise RuntimeError(
                "Scrapling's fetch integration changed; refusing to request pages."
            )
        robots_manager = getattr(engine, "_robots_manager", None)
        if (
            not isinstance(robots_manager, RobotsTxtManager)
            or not callable(getattr(robots_manager, "_fetch_fn", None))
            or getattr(robots_manager, "_cache", None) != {}
        ):
            raise RuntimeError(
                "Scrapling's robots integration changed or ran too early; refusing to request pages."
            )
        robots_manager._fetch_fn = self._fetch_robots_with_exact_host_redirects
        installed_fetch = robots_manager._fetch_fn
        if (
            getattr(installed_fetch, "__self__", None) is not self
            or getattr(installed_fetch, "__func__", None)
            is not type(self)._fetch_robots_with_exact_host_redirects
        ):
            raise RuntimeError(
                "Scrapling did not retain the redirect-safe robots fetcher; refusing to crawl."
            )
        await super().on_start(resuming=resuming)

    def _response_stayed_on_host(self, response: Any) -> bool:
        for historical_response in getattr(response, "history", ()) or ():
            historical_url = str(getattr(historical_response, "url", ""))
            if not same_host_url(historical_url, self._allowed_host):
                self._blocked_redirect_count += 1
                return False
            location = redirect_location(historical_response)
            if location and not same_host_url(
                urljoin(historical_url, location), self._allowed_host
            ):
                self._blocked_redirect_count += 1
                return False
        if not same_host_url(str(response.url), self._allowed_host):
            self._blocked_redirect_count += 1
            return False
        return True

    def _redirect_request(
        self, response: Any, callback: Any, *, enforce_path_filters: bool
    ) -> tuple[bool, Any | None]:
        if not self._response_stayed_on_host(response):
            return True, None
        status = int(getattr(response, "status", 0) or 0)
        if status not in REDIRECT_STATUSES:
            return False, None
        location = redirect_location(response)
        if location is None:
            return True, None
        target = urljoin(str(response.url), location)
        redirect_hops = int(getattr(response, "meta", {}).get("_buoy_redirect_hops", 0) or 0)
        if redirect_hops >= MAX_REDIRECT_HOPS or not same_host_url(
            target, self._allowed_host
        ):
            self._blocked_redirect_count += 1
            return True, None
        if enforce_path_filters and not url_allowed_by_path_filters(
            target,
            include_paths=self._include_paths,
            exclude_paths=self._exclude_paths,
            strip_trailing_slash=self._strip_trailing_slash,
        ):
            self._blocked_redirect_count += 1
            return True, None
        request = response.follow(
            target,
            callback=callback,
            meta={"_buoy_redirect_hops": redirect_hops + 1},
            follow_redirects=False,
        )
        return True, request

    async def _fetch_robots_with_exact_host_redirects(self, url: str, sid: str):
        from scrapling.spiders import Request as SpiderRequest

        current_url = url
        response = None
        for redirect_hops in range(MAX_REDIRECT_HOPS + 1):
            if not same_host_url(current_url, self._allowed_host):
                self._blocked_redirect_count += 1
                return response
            response = await self._engine.session_manager.fetch(
                SpiderRequest(current_url, sid=sid, follow_redirects=False)
            )
            if not self._response_stayed_on_host(response):
                return response
            status = int(getattr(response, "status", 0) or 0)
            if status not in REDIRECT_STATUSES:
                return response
            location = redirect_location(response)
            if location is None:
                return response
            if redirect_hops >= MAX_REDIRECT_HOPS:
                self._blocked_redirect_count += 1
                return response
            target = urljoin(str(response.url), location)
            if not same_host_url(target, self._allowed_host):
                self._blocked_redirect_count += 1
                return response
            current_url = target
        return response

    def _record_discovery_if_off_host(self, url: str) -> bool:
        if same_host_url(url, self._allowed_host):
            return False
        if urlparse(url).scheme in {"http", "https"}:
            self._blocked_discovery_count += 1
        return True


def build_link_spider_class(options: CrawlOptions, allowed_host: str):
    """Build a Scrapling Spider subclass for same-host fallback link crawling."""

    from scrapling.spiders import LinkExtractor, Spider

    _base_url = validate_base_url(options.base_url)
    _allowed_host = allowed_host
    _allowed_domains: set[str] = set()
    _max_pages = options.max_pages
    _css_selector = options.css_selector
    _include_paths = options.include_paths
    _exclude_paths = options.exclude_paths
    _strip_trailing_slash = options.strip_trailing_slash
    _progress_callback = options.progress_callback

    class SiteLinkDryRunSpider(_ExactHostSpiderMixin, Spider):
        name = "site_link_dry_crawl"
        robots_txt_obey = True
        start_urls = [_base_url]
        allowed_domains = _allowed_domains
        concurrent_requests = options.concurrent_requests
        concurrent_requests_per_domain = options.concurrent_requests_per_domain
        download_delay = options.download_delay
        max_blocked_retries = 1
        logging_level = (
            40  # ERROR; keep --json output clean unless something is genuinely wrong.
        )

        def __init__(self) -> None:
            self._allowed_host = _allowed_host
            self._include_paths = _include_paths
            self._exclude_paths = _exclude_paths
            self._strip_trailing_slash = _strip_trailing_slash
            self._init_exact_host_boundary()
            self._scheduled_urls: set[str] = {
                page_identity_url(_base_url, strip_trailing_slash=_strip_trailing_slash)
            }
            self._pages_scraped = 0
            self._links = LinkExtractor()
            emit_progress(
                _progress_callback,
                f"crawl link: pages=0; queued=1; cap={_max_pages}; {progress_url_label(_base_url)}",
            )
            super().__init__()

        async def parse(self, response):
            handled, redirect_request = self._redirect_request(
                response, self.parse, enforce_path_filters=True
            )
            if handled:
                if redirect_request is not None:
                    yield redirect_request
                return

            page_allowed = url_allowed_by_path_filters(
                response.url,
                include_paths=_include_paths,
                exclude_paths=_exclude_paths,
                strip_trailing_slash=_strip_trailing_slash,
            )
            page = (
                crawled_page_from_response(
                    response,
                    css_selector=_css_selector,
                    strip_trailing_slash=_strip_trailing_slash,
                )
                if page_allowed
                else None
            )
            if page:
                self._pages_scraped += 1
                emit_progress(
                    _progress_callback,
                    f"crawl link: pages={self._pages_scraped}; queued={len(self._scheduled_urls)}; cap={_max_pages}; {progress_url_label(page.url)}",
                )
                yield page.__dict__

            if len(self._scheduled_urls) >= _max_pages:
                return

            for url in self._links.extract(response):
                if len(self._scheduled_urls) >= _max_pages:
                    break
                if self._record_discovery_if_off_host(url):
                    continue
                if not url_allowed_by_path_filters(
                    url,
                    include_paths=_include_paths,
                    exclude_paths=_exclude_paths,
                    strip_trailing_slash=_strip_trailing_slash,
                ):
                    continue
                url_key = page_identity_url(
                    url, strip_trailing_slash=_strip_trailing_slash
                )
                if url_key in self._scheduled_urls:
                    continue
                self._scheduled_urls.add(url_key)
                emit_progress(
                    _progress_callback,
                    f"crawl link: pages={self._pages_scraped}; queued={len(self._scheduled_urls)}; cap={_max_pages}; {progress_url_label(url)}",
                )
                yield response.follow(url, callback=self.parse)

    return SiteLinkDryRunSpider


def build_sitemap_spider_class(options: CrawlOptions, allowed_host: str):
    """Build a Scrapling SitemapSpider subclass for sitemap-first crawling."""

    from scrapling.spiders import LinkExtractor, SitemapSpider

    _base_url = validate_base_url(options.base_url)
    _sitemap_urls = sitemap_seed_urls(_base_url)
    _allowed_host = allowed_host
    _allowed_domains: set[str] = set()
    _max_pages = options.max_pages
    _css_selector = options.css_selector
    _include_paths = options.include_paths
    _exclude_paths = options.exclude_paths
    _strip_trailing_slash = options.strip_trailing_slash
    _progress_callback = options.progress_callback

    class SiteSitemapDryRunSpider(_ExactHostSpiderMixin, SitemapSpider):
        name = "site_sitemap_dry_crawl"
        robots_txt_obey = True
        sitemap_urls = _sitemap_urls
        allowed_domains = _allowed_domains
        concurrent_requests = options.concurrent_requests
        concurrent_requests_per_domain = options.concurrent_requests_per_domain
        download_delay = options.download_delay
        max_blocked_retries = 1
        logging_level = (
            40  # ERROR; keep --json output clean unless something is genuinely wrong.
        )

        def __init__(self) -> None:
            self._allowed_host = _allowed_host
            self._include_paths = _include_paths
            self._exclude_paths = _exclude_paths
            self._strip_trailing_slash = _strip_trailing_slash
            self._init_exact_host_boundary()
            self._scheduled_page_urls: set[str] = set()
            self._estimated_sitemap_page_urls: set[str] = set()
            self._pages_scraped = 0
            self._allowed_links = LinkExtractor()
            emit_progress(
                _progress_callback,
                f"crawl sitemap: discovering pages; cap={_max_pages}",
            )
            super().__init__()

        def _dispatch(self, response, url, rules):  # noqa: ANN001 - matches Scrapling template hook.
            resolved_url = urljoin(str(getattr(response, "url", _base_url)), url)
            if self._record_discovery_if_off_host(resolved_url):
                return None
            url = resolved_url
            if (
                _progress_callback is None
                and len(self._scheduled_page_urls) >= _max_pages
            ):
                return None
            if not self._allowed_links.matches(url):
                return None
            if not url_allowed_by_path_filters(
                url,
                include_paths=_include_paths,
                exclude_paths=_exclude_paths,
                strip_trailing_slash=_strip_trailing_slash,
            ):
                return None
            url_key = page_identity_url(url, strip_trailing_slash=_strip_trailing_slash)
            if _progress_callback is not None:
                if url_key in self._estimated_sitemap_page_urls:
                    return None
                self._estimated_sitemap_page_urls.add(url_key)
            elif url_key in self._scheduled_page_urls:
                return None
            if len(self._scheduled_page_urls) >= _max_pages:
                emit_progress(
                    _progress_callback,
                    f"crawl sitemap: sitemap={len(self._estimated_sitemap_page_urls)}; queued={len(self._scheduled_page_urls)}; cap={_max_pages}; {progress_url_label(url)}",
                )
                return None
            self._scheduled_page_urls.add(url_key)
            emit_progress(
                _progress_callback,
                f"crawl sitemap: sitemap={len(self._estimated_sitemap_page_urls)}; queued={len(self._scheduled_page_urls)}; cap={_max_pages}; {progress_url_label(url)}",
            )
            return response.follow(url, callback=self.parse)

        async def start_requests(self):
            from scrapling.spiders import Request as SpiderRequest

            for url in self.sitemap_urls:
                kind = "robots" if urlparse(url).path.endswith("/robots.txt") else "sitemap"
                yield SpiderRequest(
                    url,
                    callback=self._parse_sitemap,
                    meta={"_buoy_sitemap_kind": kind},
                    follow_redirects=False,
                )

        async def _parse_sitemap(self, response):
            handled, redirect_request = self._redirect_request(
                response, self._parse_sitemap, enforce_path_filters=False
            )
            if handled:
                if redirect_request is not None:
                    yield redirect_request
                return
            if getattr(response, "meta", {}).get("_buoy_sitemap_kind") == "robots":
                for declared_url in self._robots_body(response):
                    sitemap_url = urljoin(str(response.url), declared_url)
                    if self._record_discovery_if_off_host(sitemap_url):
                        continue
                    yield response.follow(
                        sitemap_url,
                        callback=self._parse_sitemap,
                        meta={"_buoy_sitemap_kind": "sitemap"},
                    )
                return
            async for result in super()._parse_sitemap(response):
                result_url = str(getattr(result, "url", ""))
                if result_url and self._record_discovery_if_off_host(result_url):
                    continue
                yield result

        async def parse(self, response):
            handled, redirect_request = self._redirect_request(
                response, self.parse, enforce_path_filters=True
            )
            if handled:
                if redirect_request is not None:
                    yield redirect_request
                return
            page = crawled_page_from_response(
                response,
                css_selector=_css_selector,
                strip_trailing_slash=_strip_trailing_slash,
            )
            if page:
                self._pages_scraped += 1
                emit_progress(
                    _progress_callback,
                    f"crawl sitemap: pages={sitemap_page_progress_label(self._pages_scraped, sitemap_url_count=len(self._estimated_sitemap_page_urls), cap=_max_pages)}; queued={len(self._scheduled_page_urls)}; {progress_url_label(page.url)}",
                )
                yield page.__dict__

    return SiteSitemapDryRunSpider


def run_scrapling_spider(
    spider_cls: type,
) -> tuple[list[CrawledPage], dict[str, object]]:
    """Run a Scrapling spider and normalize its item/stat output."""

    spider = spider_cls()
    result = spider.start()
    pages: list[CrawledPage] = []
    for item in result.items:
        if isinstance(item, CrawledPage):
            pages.append(item.with_hash())
        elif isinstance(item, dict):
            pages.append(
                CrawledPage(
                    url=str(item.get("url", "")),
                    title=str(item.get("title", "")),
                    markdown=str(item.get("markdown", "")),
                    status=int(item.get("status", 0) or 0),
                    content_type=str(item.get("content_type", "")),
                    source_hash=str(item.get("source_hash", "")),
                    fetcher=str(item.get("fetcher", "scrapling-static-spider")),
                ).with_hash()
            )
    stats = {
        "requests_count": getattr(result.stats, "requests_count", 0),
        "robots_disallowed_count": getattr(result.stats, "robots_disallowed_count", 0),
        "blocked_requests_count": getattr(result.stats, "blocked_requests_count", 0),
        "failed_requests_count": getattr(result.stats, "failed_requests_count", 0),
        "blocked_discovery_count": getattr(spider, "_blocked_discovery_count", 0),
        "blocked_redirect_count": getattr(spider, "_blocked_redirect_count", 0),
    }
    return pages, stats


def crawl_pages(
    options: CrawlOptions,
) -> tuple[list[CrawledPage], dict[str, object], str]:
    """Crawl pages using sitemap, link-only, or hybrid discovery."""

    if options.crawl_strategy not in CRAWL_STRATEGIES:
        raise ValueError(
            f"crawl strategy must be one of: {', '.join(CRAWL_STRATEGIES)}"
        )

    allowed_host = host_from_url(options.base_url)
    if options.crawl_strategy == "link":
        emit_progress(
            options.progress_callback, f"crawl: starting link crawl for {allowed_host}"
        )
        link_spider = build_link_spider_class(options, allowed_host)
        pages, stats = run_scrapling_spider(link_spider)
        emit_progress(
            options.progress_callback,
            f"crawl: link done pages={len(pages)}; requests={stats.get('requests_count', 0)}",
        )
        return pages[: options.max_pages], stats, "link"

    emit_progress(
        options.progress_callback, f"crawl: starting sitemap crawl for {allowed_host}"
    )
    sitemap_spider = build_sitemap_spider_class(options, allowed_host)
    sitemap_pages, sitemap_stats = run_scrapling_spider(sitemap_spider)
    emit_progress(
        options.progress_callback,
        f"crawl: sitemap done pages={len(sitemap_pages)}; requests={sitemap_stats.get('requests_count', 0)}",
    )
    if options.crawl_strategy == "sitemap":
        if sitemap_pages:
            return sitemap_pages[: options.max_pages], sitemap_stats, "sitemap"
        emit_progress(
            options.progress_callback, "crawl: sitemap empty; starting link fallback"
        )
        link_spider = build_link_spider_class(options, allowed_host)
        fallback_pages, fallback_stats = run_scrapling_spider(link_spider)
        combined_stats = combine_stats(sitemap_stats, fallback_stats)
        emit_progress(
            options.progress_callback,
            f"crawl: link fallback done pages={len(fallback_pages)}; requests={fallback_stats.get('requests_count', 0)}",
        )
        return fallback_pages[: options.max_pages], combined_stats, "link_fallback"

    emit_progress(
        options.progress_callback, f"crawl: starting link crawl for {allowed_host}"
    )
    link_spider = build_link_spider_class(options, allowed_host)
    link_pages, link_stats = run_scrapling_spider(link_spider)
    emit_progress(
        options.progress_callback,
        f"crawl: link done pages={len(link_pages)}; requests={link_stats.get('requests_count', 0)}",
    )
    combined_stats = combine_stats(sitemap_stats, link_stats)
    merged_pages = merge_unique_pages(
        sitemap_pages, link_pages, strip_trailing_slash=options.strip_trailing_slash
    )
    emit_progress(
        options.progress_callback, f"crawl: merged unique pages={len(merged_pages)}"
    )
    return merged_pages[: options.max_pages], combined_stats, "hybrid"


def merge_unique_pages(
    *page_groups: Sequence[CrawledPage],
    strip_trailing_slash: bool = True,
) -> list[CrawledPage]:
    """Merge crawl results by URL while preserving first-seen order."""

    pages: list[CrawledPage] = []
    seen_urls: set[str] = set()
    for group in page_groups:
        for page in group:
            key = page_identity_url(page.url, strip_trailing_slash=strip_trailing_slash)
            if key in seen_urls:
                continue
            seen_urls.add(key)
            pages.append(page)
    return pages


def page_identity_url(url: str, *, strip_trailing_slash: bool = True) -> str:
    return canonicalize_page_url(url, strip_trailing_slash=strip_trailing_slash)


def combine_stats(
    first: dict[str, object], second: dict[str, object]
) -> dict[str, object]:
    keys = {
        "requests_count",
        "robots_disallowed_count",
        "blocked_requests_count",
        "failed_requests_count",
        "blocked_discovery_count",
        "blocked_redirect_count",
    }
    return {
        key: int(first.get(key, 0) or 0) + int(second.get(key, 0) or 0) for key in keys
    }


def write_markdown_corpus(pages: Sequence[CrawledPage], pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    for stale_page in pages_dir.glob("*.md"):
        stale_page.unlink()
    crawl_timestamp = datetime.now(timezone.utc).isoformat()
    for index, page in enumerate(pages, start=1):
        page = page.with_hash()
        path = pages_dir / page_filename(page.url, page.title, index)
        frontmatter = {
            "url": page.url,
            "title": page.title,
            "status": page.status,
            "content_type": page.content_type,
            "source_hash": page.source_hash,
            "crawl_timestamp": crawl_timestamp,
            "fetcher": page.fetcher,
        }
        lines = ["---"]
        lines.extend(
            f"{key}: {yaml_scalar(value)}" for key, value in frontmatter.items()
        )
        lines.extend(["---", "", page.markdown.strip(), ""])
        path.write_text("\n".join(lines), encoding="utf-8")


def markitdown_file_to_markdown(path: Path) -> str:
    """Convert one local file to Markdown with MarkItDown's package-facing interface."""

    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "MarkItDown local file support is not installed; install markitdown with the needed local document extras."
        ) from exc

    extension = path.suffix.lower()
    extra = MARKITDOWN_EXTRA_BY_EXTENSION.get(extension)
    dependency_hint = (
        f" Install markitdown[{extra}] for {extension} support if needed."
        if extra
        else ""
    )
    try:
        result = MarkItDown(enable_plugins=False).convert(path)
    except Exception as exc:  # pragma: no cover - exact converter exceptions depend on markitdown stack.
        raise RuntimeError(
            f"MarkItDown failed to convert local file {path.name!r}.{dependency_hint} "
            f"Converter error: {type(exc).__name__}"
        ) from exc
    return str(getattr(result, "markdown", "") or "")


def markitdown_pdf_to_markdown(path: Path) -> str:
    """Convert one local PDF to Markdown with MarkItDown's package-facing interface."""

    return markitdown_file_to_markdown(path)


def convert_local_document_to_markdown(source: LocalDocumentSource) -> str:
    if isinstance(source, PdfSource):
        return markitdown_pdf_to_markdown(source.path)
    return markitdown_file_to_markdown(source.path)


def local_document_frontmatter(
    source: LocalDocumentSource, page: CrawledPage
) -> dict[str, object]:
    frontmatter: dict[str, object] = {
        "url": page.url,
        "title": page.title,
        "status": page.status,
        "content_type": page.content_type,
        "source_kind": source.kind,
        "file_filename": source.filename,
        "file_extension": source.file_extension,
        "file_sha256": source.file_sha256,
        "file_source_id": source.source_id,
        "source_hash": page.source_hash,
        "crawl_timestamp": datetime.now(timezone.utc).isoformat(),
        "fetcher": page.fetcher,
    }
    if isinstance(source, PdfSource):
        frontmatter.update(
            {
                "pdf_filename": source.filename,
                "pdf_sha256": source.file_sha256,
                "pdf_source_id": source.source_id,
            }
        )
    return frontmatter


def write_local_document_corpus(
    source: LocalDocumentSource, markdown: str, pages_dir: Path
) -> CrawledPage:
    pages_dir.mkdir(parents=True, exist_ok=True)
    for stale_page in pages_dir.glob("*.md"):
        stale_page.unlink()

    page = CrawledPage(
        url=source.document_url,
        title=source.filename,
        markdown=markdown,
        status=200,
        content_type=source.content_type,
        source_hash=sha256_text(markdown),
        fetcher="markitdown",
    ).with_hash()
    path = pages_dir / page_filename(page.url, page.title, 1)
    lines = ["---"]
    lines.extend(
        f"{key}: {yaml_scalar(value)}"
        for key, value in local_document_frontmatter(source, page).items()
    )
    lines.extend(["---", "", page.markdown.strip(), ""])
    path.write_text("\n".join(lines), encoding="utf-8")
    return page


def write_pdf_corpus(source: PdfSource, markdown: str, pages_dir: Path) -> CrawledPage:
    return write_local_document_corpus(source, markdown, pages_dir)


def summarize_sample_chunks(
    plan: IndexingPlan,
    sample_size: int = 3,
    *,
    redact_untrusted_fields: bool = False,
) -> list[dict[str, object]]:
    return [
        {
            "id": chunk.id,
            "title": (
                BLOCKED_WEBSITE_SAMPLE_REDACTION
                if redact_untrusted_fields
                else chunk.title
            ),
            "url": chunk.url,
            "section_path": chunk.section_path,
            "content_preview": (
                BLOCKED_WEBSITE_SAMPLE_REDACTION
                if redact_untrusted_fields
                else chunk.content[:240].replace("\n", " ")
            ),
        }
        for chunk in plan.chunks[:sample_size]
    ]


def build_summary(
    *,
    options: CrawlOptions,
    pages: Sequence[CrawledPage],
    stats: dict[str, object],
    crawl_strategy: str,
    plan: IndexingPlan,
    pages_dir: Path,
    docs_version_report: dict[str, object],
    language_report: dict[str, object],
) -> dict[str, object]:
    blocked_discovery_count = int(stats.get("blocked_discovery_count", 0) or 0)
    blocked_redirect_count = int(stats.get("blocked_redirect_count", 0) or 0)
    return {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "base_url": validate_base_url(options.base_url),
        "allowed_host": host_from_url(options.base_url),
        "namespace_candidate": namespace_candidate(options.base_url),
        "crawl_strategy": crawl_strategy,
        "requested_crawl_strategy": options.crawl_strategy,
        "docs_version_policy": options.docs_version_policy,
        "docs_version_report": docs_version_report,
        "language_policy": options.language_policy,
        "language_report": language_report,
        "sitemap_seed_urls": sitemap_seed_urls(options.base_url),
        "out_dir": str(options.out_dir),
        "pages_dir": str(pages_dir),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": len(pages),
        "requests_count": int(stats.get("requests_count", 0) or 0),
        "robots_disallowed_count": int(stats.get("robots_disallowed_count", 0) or 0),
        "blocked_requests_count": int(stats.get("blocked_requests_count", 0) or 0),
        "failed_requests_count": int(stats.get("failed_requests_count", 0) or 0),
        "blocked_discovery_count": blocked_discovery_count,
        "blocked_redirect_count": blocked_redirect_count,
        "files_discovered": plan.files_discovered,
        "files_seen": plan.stats.files_seen,
        "files_error": plan.stats.files_error,
        "chunks_generated": plan.stats.chunks_generated,
        "limit_reached": plan.limit_reached,
        "sample_chunks": summarize_sample_chunks(
            plan,
            redact_untrusted_fields=bool(
                blocked_discovery_count or blocked_redirect_count
            ),
        ),
        "errors": [error.__dict__ for error in plan.stats.errors[:10]],
    }


def build_local_document_summary(
    *,
    source: LocalDocumentSource,
    options: CrawlOptions,
    plan: IndexingPlan,
    pages_dir: Path,
) -> dict[str, object]:
    summary: dict[str, object] = {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "source_kind": source.kind,
        "base_url": source.base_url,
        "document_url": source.document_url,
        "file_filename": source.filename,
        "file_extension": source.file_extension,
        "file_sha256": source.file_sha256,
        "file_source_id": source.source_id,
        "allowed_host": "",
        "namespace_candidate": source.namespace_candidate,
        "crawl_strategy": "markitdown-pdf"
        if isinstance(source, PdfSource)
        else "markitdown-local-file",
        "requested_crawl_strategy": options.crawl_strategy,
        "docs_version_policy": options.docs_version_policy,
        "docs_version_report": {
            "detected": False,
            "policy": options.docs_version_policy,
        },
        "language_policy": options.language_policy,
        "language_report": {"detected": False, "policy": options.language_policy},
        "sitemap_seed_urls": [],
        "out_dir": str(options.out_dir),
        "pages_dir": str(pages_dir),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": 1,
        "documents_converted": 1,
        "generated_documents": 1,
        "requests_count": 0,
        "robots_disallowed_count": 0,
        "blocked_requests_count": 0,
        "failed_requests_count": 0,
        "files_discovered": plan.files_discovered,
        "files_seen": plan.stats.files_seen,
        "files_error": plan.stats.files_error,
        "chunks_generated": plan.stats.chunks_generated,
        "limit_reached": plan.limit_reached,
        "sample_chunks": summarize_sample_chunks(plan),
        "errors": [error.__dict__ for error in plan.stats.errors[:10]],
    }
    if isinstance(source, PdfSource):
        summary.update(
            {
                "pdf_filename": source.filename,
                "pdf_sha256": source.file_sha256,
                "pdf_source_id": source.source_id,
            }
        )
    return summary


def build_pdf_summary(
    *,
    source: PdfSource,
    options: CrawlOptions,
    plan: IndexingPlan,
    pages_dir: Path,
) -> dict[str, object]:
    return build_local_document_summary(
        source=source, options=options, plan=plan, pages_dir=pages_dir
    )


def empty_local_document_message(source: LocalDocumentSource) -> str:
    if isinstance(source, PdfSource):
        return (
            f"No text was extracted from PDF {source.filename!r}; scanned/image-only PDFs require OCR, "
            "which is outside local document v1 scope."
        )
    return (
        f"No text was extracted from local file {source.filename!r}; "
        "OCR, image captions, audio transcription, and cloud extraction are outside local document v1 scope."
    )


def crawl_local_document_with_plan(
    source: LocalDocumentSource, options: CrawlOptions
) -> CrawlExecution:
    """Convert one local document and retain its already-built indexing plan."""

    total_started_at = observe_monotonic()
    conversion_started_at = observe_monotonic()
    label = "pdf" if isinstance(source, PdfSource) else "local file"
    emit_progress(
        options.progress_callback,
        f"crawl {label}: converting {source.filename} with MarkItDown",
    )
    markdown = convert_local_document_to_markdown(source).strip()
    crawl_seconds = elapsed_since(conversion_started_at)
    if not markdown:
        raise RuntimeError(empty_local_document_message(source))

    pages_dir = options.out_dir / "pages"
    emit_progress(
        options.progress_callback, f"crawl {label}: writing markdown document"
    )
    corpus_started_at = observe_monotonic()
    write_local_document_corpus(source, markdown, pages_dir)
    corpus_write_seconds = elapsed_since(corpus_started_at)
    emit_progress(options.progress_callback, f"crawl {label}: chunking document")
    chunk_started_at = observe_monotonic()
    plan = process_corpus(
        pages_dir,
        limit_chunks=options.max_chunks,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
    )
    chunking_seconds = elapsed_since(chunk_started_at)
    summary = build_local_document_summary(
        source=source,
        options=options,
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
    (options.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    emit_progress(
        options.progress_callback,
        f"crawl {label}: done documents=1; chunks={summary['chunks_generated']}",
    )
    return CrawlExecution(summary=summary, indexing_plan=plan)


def crawl_local_document(
    source: LocalDocumentSource, options: CrawlOptions
) -> dict[str, object]:
    return crawl_local_document_with_plan(source, options).summary


def crawl_pdf(source: PdfSource, options: CrawlOptions) -> dict[str, object]:
    """Convert one local PDF with MarkItDown and return a local-only dry-run summary."""

    return crawl_local_document(source, options)


def crawl_site_with_plan(options: CrawlOptions) -> CrawlExecution:
    """Run the Scrapling crawl and retain its already-built indexing plan."""

    total_started_at = observe_monotonic()
    options = CrawlOptions(
        base_url=validate_base_url(options.base_url),
        out_dir=options.out_dir,
        max_pages=options.max_pages,
        max_chunks=options.max_chunks,
        concurrent_requests=options.concurrent_requests,
        concurrent_requests_per_domain=options.concurrent_requests_per_domain,
        download_delay=options.download_delay,
        crawl_strategy=options.crawl_strategy,
        docs_version_policy=options.docs_version_policy,
        language_policy=options.language_policy,
        include_paths=options.include_paths,
        exclude_paths=options.exclude_paths,
        strip_trailing_slash=options.strip_trailing_slash,
        css_selector=options.css_selector,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
        progress_callback=options.progress_callback,
    )
    sitemap_policy_started_at = observe_monotonic()
    boundary_stats: dict[str, object] = {
        "blocked_discovery_count": 0,
        "blocked_redirect_count": 0,
    }
    sitemap_page_urls = None
    if options.crawl_strategy != "link" and (
        options.docs_version_policy != "all" or options.language_policy != "all"
    ):
        sitemap_page_urls = discover_sitemap_page_urls(
            options, boundary_stats=boundary_stats
        )
    options, docs_version_report = apply_docs_version_policy(
        options, sitemap_page_urls=sitemap_page_urls
    )
    block_message = docs_version_block_message(docs_version_report)
    if block_message:
        raise RuntimeError(block_message)
    if docs_version_report.get("detected"):
        if docs_version_report.get("applied"):
            emit_progress(
                options.progress_callback,
                "crawl docs versions: "
                f"policy={docs_version_report.get('policy')}; "
                f"selected={','.join(docs_version_report.get('selected_versions', []))}; "
                f"excluded={len(docs_version_report.get('excluded_versions', []))}",
            )
        else:
            emit_progress(
                options.progress_callback,
                "crawl docs versions: "
                f"detected {docs_version_report.get('version_count')} versions under "
                f"{docs_version_report.get('root_path')}; policy={docs_version_report.get('policy')}",
            )
    options, language_report = apply_language_policy(
        options, sitemap_page_urls=sitemap_page_urls
    )
    sitemap_policy_seconds = elapsed_since(sitemap_policy_started_at)
    if language_report.get("applied"):
        emit_progress(
            options.progress_callback,
            "crawl languages: "
            f"policy={language_report.get('policy')}; "
            f"excluded={len(language_report.get('excluded_languages', []))}",
        )
    crawl_started_at = observe_monotonic()
    pages, stats, crawl_strategy = crawl_pages(options)
    stats = combine_stats(boundary_stats, stats)
    crawl_seconds = elapsed_since(crawl_started_at)
    pages_dir = options.out_dir / "pages"
    emit_progress(
        options.progress_callback, f"crawl: writing {len(pages)} markdown pages"
    )
    corpus_started_at = observe_monotonic()
    write_markdown_corpus(pages, pages_dir)
    corpus_write_seconds = elapsed_since(corpus_started_at)
    emit_progress(options.progress_callback, "crawl: chunking pages")
    chunk_started_at = observe_monotonic()
    plan = process_corpus(
        pages_dir,
        limit_chunks=options.max_chunks,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
    )
    chunking_seconds = elapsed_since(chunk_started_at)
    summary = build_summary(
        options=options,
        pages=pages,
        stats=stats,
        crawl_strategy=crawl_strategy,
        plan=plan,
        pages_dir=pages_dir,
        docs_version_report=docs_version_report,
        language_report=language_report,
    )
    summary["timing"] = {
        "elapsed_seconds": elapsed_since(total_started_at),
        "sitemap_policy_seconds": sitemap_policy_seconds,
        "crawl_seconds": crawl_seconds,
        "corpus_write_seconds": corpus_write_seconds,
        "chunking_seconds": chunking_seconds,
    }
    options.out_dir.mkdir(parents=True, exist_ok=True)
    (options.out_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    emit_progress(
        options.progress_callback,
        f"crawl: done pages={summary['pages_scraped']}; chunks={summary['chunks_generated']}",
    )
    return CrawlExecution(summary=summary, indexing_plan=plan)


def crawl_site(options: CrawlOptions) -> dict[str, object]:
    """Run the local-only Scrapling crawl and return a dry-run summary."""

    return crawl_site_with_plan(options).summary
