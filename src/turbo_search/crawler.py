"""Dry-run website crawling helpers for generic site RAG indexing.

This module intentionally contains no turbopuffer write path and does not read
credentials. Scrapling is imported lazily by the crawl execution path so helper
functions and tests can run without network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from fnmatch import fnmatchcase
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal, Sequence
from urllib.parse import unquote, urlparse, urlunparse

from turbo_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
    IndexingPlan,
    process_corpus,
    sha256_text,
)

DEFAULT_CRAWL_MAX_PAGES = 250
DEFAULT_CRAWL_MAX_CHUNKS = 10000
DEFAULT_GITHUB_REPO_MAX_FILES = 5000
DEFAULT_GITHUB_REPO_MAX_CHUNKS = 100000
DEFAULT_CRAWL_CONCURRENT_REQUESTS = 2
DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN = 1
DEFAULT_CRAWL_DOWNLOAD_DELAY = 0.25
DEFAULT_CRAWL_OUT_DIR = Path("artifacts/site-crawls")
DEFAULT_CRAWL_STRATEGY = "hybrid"
CRAWL_STRATEGIES = ("sitemap", "link", "hybrid")
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


Source = WebsiteSource | GitHubRepoSource


@dataclass(frozen=True)
class CrawlOptions:
    """Options for the local-only Scrapling dry-run crawl."""

    base_url: str
    out_dir: Path
    max_pages: int = DEFAULT_CRAWL_MAX_PAGES
    max_chunks: int = DEFAULT_CRAWL_MAX_CHUNKS
    concurrent_requests: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS
    concurrent_requests_per_domain: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN
    download_delay: float = DEFAULT_CRAWL_DOWNLOAD_DELAY
    crawl_strategy: str = DEFAULT_CRAWL_STRATEGY
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    strip_trailing_slash: bool = True
    css_selector: str | None = None
    target_tokens: int = DEFAULT_TARGET_TOKENS
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES


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
    """Return the normalized base URL or raise ``ValueError``."""

    parsed = urlparse(url)
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

    source = detect_source(base_url)
    if isinstance(source, GitHubRepoSource):
        return source.namespace_candidate
    host = host_from_url(source.url)
    slug = re.sub(r"[^a-z0-9]+", "-", host).strip("-")
    return f"site-{slug}-v1"


def source_id_for_url(base_url: str) -> str:
    """Return the deterministic local source/site ID for a supported URL."""

    source = detect_source(base_url)
    if isinstance(source, GitHubRepoSource):
        return source.site_id
    return safe_slug(host_from_url(source.url), fallback="site")


def default_out_dir(base_url: str) -> Path:
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


def detect_source(url: str) -> Source:
    """Classify a URL as an ordinary website or a first-class GitHub repository."""

    normalized = validate_base_url(url)
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
        raise ValueError("GitHub repository URL must include both owner and repo, e.g. https://github.com/owner/repo")

    owner = segments[0]
    repo = segments[1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    if not owner or not repo or owner in {".", ".."} or repo in {".", ".."}:
        raise ValueError("GitHub repository URL must include non-empty owner and repo segments")

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
            raise ValueError("GitHub tree URL must include a branch or ref after /tree/")
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
            raise ValueError("GitHub blob URL must include a branch/ref and file path after /blob/")
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
    path = normalize_url_path(urlparse(url).path, strip_trailing_slash=strip_trailing_slash)
    includes = [normalize_path_pattern(pattern) for pattern in include_paths if normalize_path_pattern(pattern)]
    excludes = [normalize_path_pattern(pattern) for pattern in exclude_paths if normalize_path_pattern(pattern)]
    if includes and not any(path_matches_pattern(path, pattern) for pattern in includes):
        return False
    return not any(path_matches_pattern(path, pattern) for pattern in excludes)


def yaml_scalar(value: object) -> str:
    text = str(value if value is not None else "")
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def page_filename(url: str, title: str, index: int) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    parsed = urlparse(url)
    path_slug = safe_slug(parsed.path.strip("/") or title or parsed.netloc, fallback=f"page-{index}")
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
    title = response.css("title::text").get() or response.css("h1::text").get() or response.url
    content_type = ""
    headers = getattr(response, "headers", None)
    if headers:
        content_type = headers.get("content-type") or headers.get("Content-Type") or ""
    return CrawledPage(
        url=canonicalize_page_url(str(response.url), strip_trailing_slash=strip_trailing_slash),
        title=str(title).strip(),
        markdown=markdown,
        status=int(response.status),
        content_type=str(content_type),
        source_hash=sha256_text(markdown),
    )


def build_link_spider_class(options: CrawlOptions, allowed_host: str):
    """Build a Scrapling Spider subclass for same-host fallback link crawling."""

    from scrapling.spiders import LinkExtractor, Spider

    _base_url = validate_base_url(options.base_url)
    _allowed_host = allowed_host
    _allowed_domains = allowed_domains_for_url(_base_url)
    _max_pages = options.max_pages
    _css_selector = options.css_selector
    _include_paths = options.include_paths
    _exclude_paths = options.exclude_paths
    _strip_trailing_slash = options.strip_trailing_slash

    class SiteLinkDryRunSpider(Spider):
        name = "site_link_dry_crawl"
        robots_txt_obey = True
        start_urls = [_base_url]
        allowed_domains = _allowed_domains
        concurrent_requests = options.concurrent_requests
        concurrent_requests_per_domain = options.concurrent_requests_per_domain
        download_delay = options.download_delay
        max_blocked_retries = 1
        logging_level = 40  # ERROR; keep --json output clean unless something is genuinely wrong.

        def __init__(self) -> None:
            self._scheduled_urls: set[str] = {page_identity_url(_base_url, strip_trailing_slash=_strip_trailing_slash)}
            self._links = LinkExtractor(allow_domains=_allowed_host)
            super().__init__()

        async def parse(self, response):
            page_allowed = url_allowed_by_path_filters(
                response.url,
                include_paths=_include_paths,
                exclude_paths=_exclude_paths,
                strip_trailing_slash=_strip_trailing_slash,
            )
            page = crawled_page_from_response(
                response,
                css_selector=_css_selector,
                strip_trailing_slash=_strip_trailing_slash,
            ) if page_allowed else None
            if page:
                yield page.__dict__

            if len(self._scheduled_urls) >= _max_pages:
                return

            for url in self._links.extract(response):
                if len(self._scheduled_urls) >= _max_pages:
                    break
                if not url_allowed_by_path_filters(
                    url,
                    include_paths=_include_paths,
                    exclude_paths=_exclude_paths,
                    strip_trailing_slash=_strip_trailing_slash,
                ):
                    continue
                url_key = page_identity_url(url, strip_trailing_slash=_strip_trailing_slash)
                if url_key in self._scheduled_urls:
                    continue
                self._scheduled_urls.add(url_key)
                yield response.follow(url, callback=self.parse)

    return SiteLinkDryRunSpider


def build_sitemap_spider_class(options: CrawlOptions, allowed_host: str):
    """Build a Scrapling SitemapSpider subclass for sitemap-first crawling."""

    from scrapling.spiders import LinkExtractor, SitemapSpider

    _sitemap_urls = sitemap_seed_urls(options.base_url)
    _allowed_host = allowed_host
    _allowed_domains = allowed_domains_for_url(options.base_url)
    _max_pages = options.max_pages
    _css_selector = options.css_selector
    _include_paths = options.include_paths
    _exclude_paths = options.exclude_paths
    _strip_trailing_slash = options.strip_trailing_slash

    class SiteSitemapDryRunSpider(SitemapSpider):
        name = "site_sitemap_dry_crawl"
        robots_txt_obey = True
        sitemap_urls = _sitemap_urls
        allowed_domains = _allowed_domains
        concurrent_requests = options.concurrent_requests
        concurrent_requests_per_domain = options.concurrent_requests_per_domain
        download_delay = options.download_delay
        max_blocked_retries = 1
        logging_level = 40  # ERROR; keep --json output clean unless something is genuinely wrong.

        def __init__(self) -> None:
            self._scheduled_page_urls: set[str] = set()
            self._allowed_links = LinkExtractor(allow_domains=_allowed_host)
            super().__init__()

        def _dispatch(self, response, url, rules):  # noqa: ANN001 - matches Scrapling template hook.
            if len(self._scheduled_page_urls) >= _max_pages:
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
            if url_key in self._scheduled_page_urls:
                return None
            self._scheduled_page_urls.add(url_key)
            return response.follow(url, callback=self.parse)

        async def parse(self, response):
            page = crawled_page_from_response(
                response,
                css_selector=_css_selector,
                strip_trailing_slash=_strip_trailing_slash,
            )
            if page:
                yield page.__dict__

    return SiteSitemapDryRunSpider


def run_scrapling_spider(spider_cls: type) -> tuple[list[CrawledPage], dict[str, object]]:
    """Run a Scrapling spider and normalize its item/stat output."""

    result = spider_cls().start()
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
    }
    return pages, stats


def crawl_pages(options: CrawlOptions) -> tuple[list[CrawledPage], dict[str, object], str]:
    """Crawl pages using sitemap, link-only, or hybrid discovery."""

    if options.crawl_strategy not in CRAWL_STRATEGIES:
        raise ValueError(f"crawl strategy must be one of: {', '.join(CRAWL_STRATEGIES)}")

    allowed_host = host_from_url(options.base_url)
    if options.crawl_strategy == "link":
        link_spider = build_link_spider_class(options, allowed_host)
        pages, stats = run_scrapling_spider(link_spider)
        return pages[: options.max_pages], stats, "link"

    sitemap_spider = build_sitemap_spider_class(options, allowed_host)
    sitemap_pages, sitemap_stats = run_scrapling_spider(sitemap_spider)
    if options.crawl_strategy == "sitemap":
        if sitemap_pages:
            return sitemap_pages[: options.max_pages], sitemap_stats, "sitemap"
        link_spider = build_link_spider_class(options, allowed_host)
        fallback_pages, fallback_stats = run_scrapling_spider(link_spider)
        combined_stats = combine_stats(sitemap_stats, fallback_stats)
        return fallback_pages[: options.max_pages], combined_stats, "link_fallback"

    link_spider = build_link_spider_class(options, allowed_host)
    link_pages, link_stats = run_scrapling_spider(link_spider)
    combined_stats = combine_stats(sitemap_stats, link_stats)
    merged_pages = merge_unique_pages(sitemap_pages, link_pages, strip_trailing_slash=options.strip_trailing_slash)
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


def combine_stats(first: dict[str, object], second: dict[str, object]) -> dict[str, object]:
    keys = {
        "requests_count",
        "robots_disallowed_count",
        "blocked_requests_count",
        "failed_requests_count",
    }
    return {key: int(first.get(key, 0) or 0) + int(second.get(key, 0) or 0) for key in keys}


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
        lines.extend(f"{key}: {yaml_scalar(value)}" for key, value in frontmatter.items())
        lines.extend(["---", "", page.markdown.strip(), ""])
        path.write_text("\n".join(lines), encoding="utf-8")


def summarize_sample_chunks(plan: IndexingPlan, sample_size: int = 3) -> list[dict[str, object]]:
    return [
        {
            "id": chunk.id,
            "title": chunk.title,
            "url": chunk.url,
            "section_path": chunk.section_path,
            "content_preview": chunk.content[:240].replace("\n", " "),
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
) -> dict[str, object]:
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
        "files_discovered": plan.files_discovered,
        "files_seen": plan.stats.files_seen,
        "files_error": plan.stats.files_error,
        "chunks_generated": plan.stats.chunks_generated,
        "limit_reached": plan.limit_reached,
        "sample_chunks": summarize_sample_chunks(plan),
        "errors": [error.__dict__ for error in plan.stats.errors[:10]],
    }


def crawl_site(options: CrawlOptions) -> dict[str, object]:
    """Run the local-only Scrapling crawl and return a dry-run summary."""

    options = CrawlOptions(
        base_url=validate_base_url(options.base_url),
        out_dir=options.out_dir,
        max_pages=options.max_pages,
        max_chunks=options.max_chunks,
        concurrent_requests=options.concurrent_requests,
        concurrent_requests_per_domain=options.concurrent_requests_per_domain,
        download_delay=options.download_delay,
        crawl_strategy=options.crawl_strategy,
        include_paths=options.include_paths,
        exclude_paths=options.exclude_paths,
        strip_trailing_slash=options.strip_trailing_slash,
        css_selector=options.css_selector,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
    )
    pages, stats, crawl_strategy = crawl_pages(options)
    pages_dir = options.out_dir / "pages"
    write_markdown_corpus(pages, pages_dir)
    plan = process_corpus(
        pages_dir,
        limit_chunks=options.max_chunks,
        target_tokens=options.target_tokens,
        overlap_sentences=options.overlap_sentences,
    )
    summary = build_summary(
        options=options,
        pages=pages,
        stats=stats,
        crawl_strategy=crawl_strategy,
        plan=plan,
        pages_dir=pages_dir,
    )
    options.out_dir.mkdir(parents=True, exist_ok=True)
    (options.out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary
