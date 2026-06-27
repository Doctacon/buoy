from __future__ import annotations

import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from turbo_search.crawler import (
    DEFAULT_CRAWL_MAX_CHUNKS,
    DEFAULT_CRAWL_MAX_PAGES,
    DEFAULT_GITHUB_REPO_MAX_CHUNKS,
    DEFAULT_GITHUB_REPO_MAX_FILES,
    CrawledPage,
    CrawlOptions,
    GitHubRepoSource,
    WebsiteSource,
    canonicalize_page_url,
    allowed_domains_for_url,
    crawl_pages,
    crawled_page_from_response,
    default_out_dir,
    detect_source,
    url_allowed_by_path_filters,
    namespace_candidate,
    page_filename,
    parse_github_repo_url,
    sitemap_seed_urls,
    source_id_for_url,
    validate_base_url,
    write_markdown_corpus,
)
from turbo_search.chunker import process_corpus


class CrawlerHelperTests(unittest.TestCase):
    def test_default_caps_are_useful_for_site_plans(self) -> None:
        self.assertEqual(DEFAULT_CRAWL_MAX_PAGES, 250)
        self.assertEqual(DEFAULT_CRAWL_MAX_CHUNKS, 10000)
        self.assertEqual(DEFAULT_GITHUB_REPO_MAX_FILES, 5000)
        self.assertEqual(DEFAULT_GITHUB_REPO_MAX_CHUNKS, 100000)

    def test_validate_base_url_accepts_absolute_http_urls_and_strips_fragment(self) -> None:
        self.assertEqual(
            validate_base_url("https://example.com/docs/#section"),
            "https://example.com/docs/",
        )
        self.assertEqual(validate_base_url("http://example.com"), "http://example.com")

    def test_validate_base_url_rejects_relative_and_non_http_urls(self) -> None:
        for url in ("/docs", "example.com/docs", "file:///tmp/page.html", "ftp://example.com"):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    validate_base_url(url)

    def test_namespace_candidate_and_default_out_dir_are_host_based_for_websites(self) -> None:
        url = "https://Scrapling.ReadTheDocs.io/en/latest/"

        self.assertEqual(namespace_candidate(url), "site-scrapling-readthedocs-io-v1")
        self.assertEqual(source_id_for_url(url), "scrapling-readthedocs-io")
        self.assertEqual(default_out_dir(url), Path("artifacts/site-crawls/scrapling-readthedocs-io"))

    def test_github_repo_url_root_defaults_are_repo_specific(self) -> None:
        url = "https://github.com/Doctacon/open-streaming-lab"

        source = detect_source(url)

        self.assertIsInstance(source, GitHubRepoSource)
        assert isinstance(source, GitHubRepoSource)
        self.assertEqual(source.kind, "github_repo")
        self.assertEqual(source.repo_root_url, "https://github.com/Doctacon/open-streaming-lab")
        self.assertEqual(source.repo_full_name, "Doctacon/open-streaming-lab")
        self.assertEqual(source.clone_url, "https://github.com/Doctacon/open-streaming-lab.git")
        self.assertEqual(source.site_id, "github-doctacon-open-streaming-lab")
        self.assertEqual(source.namespace_candidate, "github-doctacon-open-streaming-lab-v1")
        self.assertEqual(source.default_out_dir, Path("artifacts/site-crawls/github-doctacon-open-streaming-lab"))
        self.assertEqual(namespace_candidate(url), "github-doctacon-open-streaming-lab-v1")
        self.assertEqual(source_id_for_url(url), "github-doctacon-open-streaming-lab")
        self.assertEqual(default_out_dir(url), Path("artifacts/site-crawls/github-doctacon-open-streaming-lab"))

    def test_github_repo_url_parser_accepts_trailing_slash_dot_git_and_tree_urls(self) -> None:
        trailing = parse_github_repo_url("https://github.com/owner/repo/")
        dot_git = parse_github_repo_url("https://github.com/owner/repo.git#readme")
        tree = parse_github_repo_url("https://github.com/owner/repo/tree/main/docs/examples")

        self.assertIsNotNone(trailing)
        self.assertIsNotNone(dot_git)
        self.assertIsNotNone(tree)
        assert trailing is not None and dot_git is not None and tree is not None
        self.assertEqual(trailing.repo_root_url, "https://github.com/owner/repo")
        self.assertEqual(dot_git.repo_root_url, "https://github.com/owner/repo")
        self.assertEqual(tree.tree_ref, "main")
        self.assertEqual(tree.tree_path, "docs/examples")
        self.assertEqual(tree.repo_root_url, "https://github.com/owner/repo")

    def test_github_blob_url_returns_structured_hint(self) -> None:
        source = parse_github_repo_url("https://github.com/owner/repo/blob/main/src/app.py")

        self.assertIsNotNone(source)
        assert source is not None
        self.assertIsNotNone(source.blob_hint)
        assert source.blob_hint is not None
        self.assertEqual(source.blob_hint.ref, "main")
        self.assertEqual(source.blob_hint.path, "src/app.py")

    def test_github_non_repo_pages_fall_back_to_website_source(self) -> None:
        source = detect_source("https://github.com/features")

        self.assertIsInstance(source, WebsiteSource)
        assert isinstance(source, WebsiteSource)
        self.assertEqual(source.url, "https://github.com/features")

    def test_github_repo_like_invalid_urls_fail_clearly(self) -> None:
        for url in (
            "https://github.com/owner-only",
            "https://github.com/owner/repo/issues",
            "https://github.com/owner/repo/tree/",
        ):
            with self.subTest(url=url):
                with self.assertRaises(ValueError):
                    detect_source(url)

    def test_allowed_domains_include_host_and_port_netloc(self) -> None:
        self.assertEqual(
            allowed_domains_for_url("https://example.com:8443/docs"),
            {"example.com", "example.com:8443"},
        )

    def test_sitemap_seed_urls_include_robots_and_conventional_sitemaps(self) -> None:
        self.assertEqual(
            sitemap_seed_urls("https://example.com/docs/page"),
            [
                "https://example.com/robots.txt",
                "https://example.com/sitemap.xml",
                "https://example.com/sitemap_index.xml",
            ],
        )

    def test_url_path_filters_support_include_exclude_and_globs(self) -> None:
        self.assertTrue(
            url_allowed_by_path_filters(
                "https://example.com/docs/query/",
                include_paths=("/docs/**",),
                exclude_paths=("/docs/private/**",),
            )
        )
        self.assertTrue(
            url_allowed_by_path_filters(
                "https://example.com/docs",
                include_paths=("/docs/**",),
            )
        )
        self.assertFalse(
            url_allowed_by_path_filters(
                "https://example.com/blog/post",
                include_paths=("/docs/**",),
            )
        )
        self.assertFalse(
            url_allowed_by_path_filters(
                "https://example.com/llms-full.txt",
                exclude_paths=("/llms-full.txt",),
            )
        )

    def test_canonicalize_page_url_strips_fragments_and_trailing_slashes(self) -> None:
        self.assertEqual(
            canonicalize_page_url("https://example.com/docs/query/#top"),
            "https://example.com/docs/query",
        )
        self.assertEqual(canonicalize_page_url("https://example.com/"), "https://example.com/")
        self.assertEqual(
            canonicalize_page_url("https://example.com/docs/query/", strip_trailing_slash=False),
            "https://example.com/docs/query/",
        )

    def test_page_filename_is_deterministic_and_markdown(self) -> None:
        first = page_filename("https://example.com/docs/page", "Title", 1)
        second = page_filename("https://example.com/docs/page", "Different Title", 1)

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("0001-docs-page-"))
        self.assertTrue(first.endswith(".md"))

    def test_write_markdown_corpus_removes_stale_generated_pages(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pages_dir = Path(tmp) / "pages"
            pages_dir.mkdir()
            (pages_dir / "stale.md").write_text("---\ntitle: Stale\n---\n\nOld text.", encoding="utf-8")

            write_markdown_corpus([], pages_dir)

            self.assertEqual(list(pages_dir.glob("*.md")), [])

    def test_write_markdown_corpus_frontmatter_feeds_existing_chunker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pages_dir = Path(tmp) / "pages"
            write_markdown_corpus(
                [
                    CrawledPage(
                        url="https://example.com/docs/page",
                        title="Docs Page",
                        status=200,
                        content_type="text/html; charset=utf-8",
                        markdown="## Intro\nUseful documentation text for retrieval.",
                    )
                ],
                pages_dir,
            )

            files = list(pages_dir.glob("*.md"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text(encoding="utf-8")
            self.assertIn('url: "https://example.com/docs/page"', text)
            self.assertIn('title: "Docs Page"', text)
            self.assertIn('status: "200"', text)
            self.assertIn('content_type: "text/html; charset=utf-8"', text)
            self.assertIn('fetcher: "scrapling-static-spider"', text)

            plan = process_corpus(pages_dir)
            self.assertEqual(plan.stats.files_seen, 1)
            self.assertEqual(plan.stats.files_error, 0)
            self.assertEqual(plan.stats.chunks_generated, 1)
            self.assertEqual(plan.chunks[0].title, "Docs Page")
            self.assertEqual(plan.chunks[0].url, "https://example.com/docs/page")

    def test_crawled_page_from_response_skips_unextractable_html(self) -> None:
        class Response:
            status = 200
            url = "https://example.com/control-chars"

        with patch("turbo_search.crawler.markdown_from_response", side_effect=ValueError("bad html")):
            self.assertIsNone(crawled_page_from_response(Response()))

    def test_hybrid_crawl_merges_sitemap_and_link_pages(self) -> None:
        class SitemapSpider:
            pass

        class LinkSpider:
            pass

        sitemap_page = CrawledPage(
            url="https://example.com/docs/",
            title="Docs",
            status=200,
            markdown="Docs home",
        )
        duplicate_link_page = CrawledPage(
            url="https://example.com/docs/#top",
            title="Docs duplicate",
            status=200,
            markdown="Duplicate docs home",
        )
        link_only_page = CrawledPage(
            url="https://example.com/docs/pinning",
            title="Pinning",
            status=200,
            markdown="Pinning documentation",
        )

        def fake_run(spider_cls):
            if spider_cls is SitemapSpider:
                return [sitemap_page], {"requests_count": 2}
            if spider_cls is LinkSpider:
                return [duplicate_link_page, link_only_page], {"requests_count": 3}
            raise AssertionError("unexpected spider")

        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=10,
            crawl_strategy="hybrid",
        )
        with patch("turbo_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider):
            with patch("turbo_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("turbo_search.crawler.run_scrapling_spider", side_effect=fake_run):
                    pages, stats, strategy = crawl_pages(options)

        self.assertEqual(strategy, "hybrid")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/", "https://example.com/docs/pinning"])
        self.assertEqual(stats["requests_count"], 5)

    def test_link_crawl_strategy_skips_sitemap(self) -> None:
        class SitemapSpider:
            pass

        class LinkSpider:
            pass

        link_page = CrawledPage(
            url="https://example.com/docs/pinning",
            title="Pinning",
            status=200,
            markdown="Pinning documentation",
        )

        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=10,
            crawl_strategy="link",
        )
        with patch("turbo_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider) as sitemap_mock:
            with patch("turbo_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("turbo_search.crawler.run_scrapling_spider", return_value=([link_page], {"requests_count": 1})):
                    pages, stats, strategy = crawl_pages(options)

        self.assertEqual(strategy, "link")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/pinning"])
        self.assertEqual(stats["requests_count"], 1)
        sitemap_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
