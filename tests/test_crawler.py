from __future__ import annotations

import gzip
import hashlib
import tempfile
import zlib
from pathlib import Path
import json
import unittest
from unittest.mock import patch

from buoy_search.crawler import (
    DEFAULT_CRAWL_MAX_CHUNKS,
    DEFAULT_CRAWL_MAX_PAGES,
    DEFAULT_GITHUB_REPO_MAX_CHUNKS,
    DEFAULT_GITHUB_REPO_MAX_FILES,
    ROBOTS_RESPONSE_MAX_BYTES,
    SITEMAP_DECOMPRESSED_MAX_BYTES,
    SITEMAP_TRANSFER_MAX_BYTES,
    CrawledPage,
    CrawlOptions,
    FetchedResource,
    GitHubRepoSource,
    LocalFileSource,
    SitemapResourceError,
    PdfSource,
    WebsiteSource,
    analyze_docs_version_urls,
    apply_docs_version_policy,
    apply_language_policy,
    analyze_language_urls,
    build_sitemap_spider_class,
    docs_version_block_message,
    canonicalize_page_url,
    allowed_domains_for_url,
    crawl_pages,
    crawl_pdf,
    crawl_local_document,
    crawl_site,
    crawled_page_from_response,
    default_out_dir,
    detect_source,
    discover_sitemap_page_urls,
    elapsed_since,
    fetch_url_bytes,
    maybe_decompress_sitemap,
    observe_monotonic,
    url_allowed_by_path_filters,
    namespace_candidate,
    page_filename,
    parse_github_repo_url,
    sitemap_locations_from_xml,
    sitemap_page_progress_label,
    sitemap_seed_urls,
    source_id_for_url,
    validate_base_url,
    write_markdown_corpus,
)
from buoy_search.chunker import process_corpus


class CrawlerHelperTests(unittest.TestCase):
    def test_diagnostic_clock_failures_are_best_effort(self) -> None:
        with patch("buoy_search.crawler.time.monotonic", side_effect=RuntimeError("clock failed")):
            self.assertIsNone(observe_monotonic())
            self.assertEqual(elapsed_since(1.0), 0.0)

    def test_default_caps_are_useful_for_site_plans(self) -> None:
        self.assertEqual(DEFAULT_CRAWL_MAX_PAGES, 3000)
        self.assertEqual(DEFAULT_CRAWL_MAX_CHUNKS, 120000)
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

    def test_local_pdf_path_defaults_are_filename_and_hash_based(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pdf_path = Path(tmp) / "Quarterly Report.PDF"
            pdf_bytes = b"%PDF-1.4 fake text pdf bytes"
            pdf_path.write_bytes(pdf_bytes)
            sha256 = hashlib.sha256(pdf_bytes).hexdigest()

            source = detect_source(str(pdf_path))

            self.assertIsInstance(source, PdfSource)
            assert isinstance(source, PdfSource)
            self.assertEqual(source.kind, "pdf")
            self.assertEqual(source.filename, "Quarterly Report.PDF")
            self.assertEqual(source.file_sha256, sha256)
            self.assertEqual(source.source_id, f"pdf-quarterly-report-{sha256[:16]}")
            self.assertEqual(source.base_url, f"pdf://pdf-quarterly-report-{sha256[:16]}")
            self.assertEqual(source.document_url, f"pdf://pdf-quarterly-report-{sha256[:16]}/Quarterly%20Report.PDF")
            self.assertEqual(source.namespace_candidate, f"pdf-quarterly-report-{sha256[:16]}-v1")
            self.assertEqual(namespace_candidate(str(pdf_path)), source.namespace_candidate)
            self.assertEqual(source_id_for_url(str(pdf_path)), source.source_id)
            self.assertEqual(default_out_dir(str(pdf_path)), Path("artifacts/site-crawls") / source.source_id)

    def test_local_file_path_defaults_are_extension_filename_and_hash_based(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            csv_path = Path(tmp) / "Quarterly Report.csv"
            csv_bytes = b"metric,value\nrevenue,42\n"
            csv_path.write_bytes(csv_bytes)
            sha256 = hashlib.sha256(csv_bytes).hexdigest()

            source = detect_source(str(csv_path))

            self.assertIsInstance(source, LocalFileSource)
            assert isinstance(source, LocalFileSource)
            self.assertEqual(source.kind, "local_file")
            self.assertEqual(source.filename, "Quarterly Report.csv")
            self.assertEqual(source.file_extension, "csv")
            self.assertEqual(source.file_sha256, sha256)
            self.assertEqual(source.source_id, f"file-csv-quarterly-report-{sha256[:16]}")
            self.assertEqual(source.base_url, f"file://file-csv-quarterly-report-{sha256[:16]}")
            self.assertEqual(source.document_url, f"file://file-csv-quarterly-report-{sha256[:16]}/Quarterly%20Report.csv")
            self.assertEqual(source.namespace_candidate, f"file-csv-quarterly-report-{sha256[:16]}-v1")
            self.assertEqual(namespace_candidate(str(csv_path)), source.namespace_candidate)
            self.assertEqual(source_id_for_url(str(csv_path)), source.source_id)
            self.assertEqual(default_out_dir(str(csv_path)), Path("artifacts/site-crawls") / source.source_id)

    def test_local_file_unsupported_existing_extension_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "diagram.png"
            image_path.write_bytes(b"not indexed")

            with self.assertRaisesRegex(ValueError, "unsupported local file type '.png'"):
                detect_source(str(image_path))

    def test_pdf_internal_base_url_supports_plan_artifact_identity(self) -> None:
        self.assertEqual(namespace_candidate("pdf://pdf-quarterly-report-abc123"), "pdf-quarterly-report-abc123-v1")
        self.assertEqual(source_id_for_url("pdf://pdf-quarterly-report-abc123"), "pdf-quarterly-report-abc123")
        self.assertEqual(default_out_dir("pdf://pdf-quarterly-report-abc123"), Path("artifacts/site-crawls/pdf-quarterly-report-abc123"))
        self.assertEqual(validate_base_url("pdf://pdf-quarterly-report-abc123#ignored"), "pdf://pdf-quarterly-report-abc123")

    def test_local_file_internal_base_url_supports_plan_artifact_identity(self) -> None:
        self.assertEqual(namespace_candidate("file://file-csv-quarterly-report-abc123"), "file-csv-quarterly-report-abc123-v1")
        self.assertEqual(source_id_for_url("file://file-csv-quarterly-report-abc123"), "file-csv-quarterly-report-abc123")
        self.assertEqual(default_out_dir("file://file-csv-quarterly-report-abc123"), Path("artifacts/site-crawls/file-csv-quarterly-report-abc123"))
        self.assertEqual(validate_base_url("file://file-csv-quarterly-report-abc123#ignored"), "file://file-csv-quarterly-report-abc123")

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

    def test_incremental_resource_read_accepts_exact_robots_and_sitemap_boundaries(self) -> None:
        class Response:
            status = 200
            headers: dict[str, str] = {}

            def __init__(self, url: str, body: bytes) -> None:
                self.url = url
                self.body = body
                self.offset = 0
                self.max_read_size = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self) -> str:
                return self.url

            def read(self, size: int) -> bytes:
                self.max_read_size = max(self.max_read_size, size)
                chunk = self.body[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        cases = (
            (
                "https://example.com/robots.txt",
                ROBOTS_RESPONSE_MAX_BYTES,
                "robots response body",
            ),
            (
                "https://example.com/sitemap.xml.gz",
                SITEMAP_TRANSFER_MAX_BYTES,
                "sitemap transferred bytes",
            ),
        )
        for url, ceiling, limit_type in cases:
            with self.subTest(limit_type=limit_type):
                response = Response(url, b"a" * ceiling)
                with patch(
                    "buoy_search.crawler._NO_REDIRECT_OPENER.open",
                    return_value=response,
                ):
                    resource = fetch_url_bytes(
                        url,
                        ceiling=ceiling,
                        limit_type=limit_type,
                    )

                self.assertIsNotNone(resource)
                assert resource is not None
                self.assertEqual(resource.final_url, url)
                self.assertEqual(len(resource.body), ceiling)
                self.assertLessEqual(response.max_read_size, 64 * 1024)

    def test_resource_read_preserves_validated_final_redirect_url(self) -> None:
        class Response:
            def __init__(
                self,
                url: str,
                *,
                status: int,
                body: bytes = b"",
                headers: dict[str, str] | None = None,
            ) -> None:
                self.url = url
                self.status = status
                self.body = body
                self.headers = headers or {}
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self) -> str:
                return self.url

            def read(self, size: int) -> bytes:
                chunk = self.body[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        original_url = "https://example.com/sitemap.xml"
        final_url = "https://example.com/final.xml.gz"
        responses = (
            Response(
                original_url,
                status=302,
                headers={"location": "/final.xml.gz"},
            ),
            Response(final_url, status=200, body=b"body"),
        )
        with patch(
            "buoy_search.crawler._NO_REDIRECT_OPENER.open",
            side_effect=responses,
        ):
            resource = fetch_url_bytes(
                original_url,
                ceiling=SITEMAP_TRANSFER_MAX_BYTES,
                limit_type="sitemap transferred bytes",
                allowed_host="example.com",
            )

        self.assertIsNotNone(resource)
        assert resource is not None
        self.assertEqual(resource.final_url, final_url)

    def test_incremental_resource_read_rejects_over_limit_robots_and_sitemap(self) -> None:
        class Response:
            status = 200
            headers: dict[str, str] = {}

            def __init__(self, url: str, body: bytes) -> None:
                self.url = url
                self.body = body
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self) -> str:
                return self.url

            def read(self, size: int) -> bytes:
                chunk = self.body[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        cases = (
            (
                "https://example.com/robots.txt",
                ROBOTS_RESPONSE_MAX_BYTES,
                "robots response body",
            ),
            (
                "https://example.com/sitemap.xml.gz",
                SITEMAP_TRANSFER_MAX_BYTES,
                "sitemap transferred bytes",
            ),
        )
        for url, ceiling, limit_type in cases:
            with self.subTest(limit_type=limit_type):
                response = Response(url, b"a" * (ceiling + 1))
                with patch(
                    "buoy_search.crawler._NO_REDIRECT_OPENER.open",
                    return_value=response,
                ):
                    with self.assertRaisesRegex(
                        SitemapResourceError,
                        rf"{limit_type} limit exceeded for {url}.*ceiling={ceiling} bytes",
                    ):
                        fetch_url_bytes(
                            url,
                            ceiling=ceiling,
                            limit_type=limit_type,
                        )

    def test_gzip_sitemap_accepts_exact_decompressed_boundary_and_stops_bomb(self) -> None:
        exact_xml = b"<urlset></urlset>" + b" " * (
            SITEMAP_DECOMPRESSED_MAX_BYTES - 17
        )
        compressed_exact = gzip.compress(exact_xml)
        self.assertEqual(
            len(
                maybe_decompress_sitemap(
                    compressed_exact,
                    "https://example.com/sitemap.xml",
                )
            ),
            SITEMAP_DECOMPRESSED_MAX_BYTES,
        )

        bomb = gzip.compress(
            b"a" * (SITEMAP_DECOMPRESSED_MAX_BYTES + 1), compresslevel=9
        )
        with self.assertRaisesRegex(
            SitemapResourceError,
            rf"sitemap decompressed bytes limit exceeded.*https://example.com/bomb.xml.gz.*ceiling={SITEMAP_DECOMPRESSED_MAX_BYTES} bytes",
        ):
            maybe_decompress_sitemap(bomb, "https://example.com/bomb.xml.gz")

    def test_malformed_declared_or_detected_gzip_fails_closed(self) -> None:
        cases = (
            (b"not gzip", "https://example.com/sitemap.xml.gz", "", ""),
            (b"\x1f\x8bbroken", "https://example.com/sitemap.xml", "", ""),
            (
                b"not gzip",
                "https://example.com/sitemap.xml",
                "application/gzip",
                "",
            ),
            (
                b"not gzip",
                "https://example.com/sitemap.xml",
                "",
                "gzip",
            ),
        )
        for body, url, content_type, content_encoding in cases:
            with self.subTest(
                url=url,
                content_type=content_type,
                content_encoding=content_encoding,
            ):
                with self.assertRaisesRegex(
                    SitemapResourceError, rf"malformed gzip sitemap at {url}"
                ):
                    sitemap_locations_from_xml(
                        body,
                        url,
                        content_type=content_type,
                        content_encoding=content_encoding,
                    )

    def test_corrupt_deflate_is_wrapped_as_url_specific_malformed_gzip(self) -> None:
        corrupt_deflate = bytes.fromhex("1f8b08000000000000ff07") + b"\x00" * 8
        url = "https://example.com/corrupt.xml.gz"

        with self.assertRaisesRegex(
            SitemapResourceError, rf"malformed gzip sitemap at {url}"
        ) as raised:
            maybe_decompress_sitemap(corrupt_deflate, url)

        self.assertIsInstance(raised.exception.__cause__, zlib.error)

    def test_redirected_declared_gzip_fails_closed_before_link_fallback(self) -> None:
        class Response:
            def __init__(
                self,
                url: str,
                *,
                status: int,
                body: bytes = b"",
                headers: dict[str, str] | None = None,
            ) -> None:
                self.url = url
                self.status = status
                self.body = body
                self.headers = headers or {}
                self.offset = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return None

            def geturl(self) -> str:
                return self.url

            def read(self, size: int) -> bytes:
                chunk = self.body[self.offset : self.offset + size]
                self.offset += len(chunk)
                return chunk

        original_url = "https://example.com/sitemap.xml"
        final_url = "https://example.com/redirected.xml.gz"
        requested_urls: list[str] = []

        def fake_open(request, **_kwargs):
            requested_url = request.full_url
            requested_urls.append(requested_url)
            if requested_url == original_url:
                return Response(
                    original_url,
                    status=302,
                    headers={"location": "/redirected.xml.gz"},
                )
            if requested_url == final_url:
                return Response(final_url, status=200, body=b"not gzip")
            return Response(requested_url, status=404)

        options = CrawlOptions(
            base_url="https://example.com/", out_dir=Path("unused")
        )
        with patch(
            "buoy_search.crawler._NO_REDIRECT_OPENER.open", side_effect=fake_open
        ):
            with patch("buoy_search.crawler.build_link_spider_class") as link_mock:
                with self.assertRaisesRegex(
                    SitemapResourceError,
                    rf"malformed gzip sitemap at {final_url}",
                ):
                    crawl_pages(options)

        self.assertEqual(
            requested_urls,
            [
                "https://example.com/robots.txt",
                original_url,
                final_url,
            ],
        )
        link_mock.assert_not_called()

    def test_multiple_sitemap_queue_propagates_late_limit_error(self) -> None:
        options = CrawlOptions(
            base_url="https://example.com/", out_dir=Path("unused")
        )
        index_url = "https://example.com/index.xml"
        first_url = "https://example.com/first.xml"
        oversized_url = "https://example.com/oversized.xml"
        resources = {
            "https://example.com/robots.txt": FetchedResource(
                f"Sitemap: {index_url}\n".encode(),
                "https://example.com/robots.txt",
            ),
            index_url: FetchedResource(
                (
                    "<sitemapindex><sitemap><loc>"
                    f"{first_url}</loc></sitemap><sitemap><loc>{oversized_url}"
                    "</loc></sitemap></sitemapindex>"
                ).encode(),
                index_url,
            ),
            first_url: FetchedResource(
                b"<urlset><url><loc>https://example.com/docs/first</loc></url></urlset>",
                first_url,
            ),
        }

        def fake_fetch(url: str, **_kwargs):
            if url == oversized_url:
                raise SitemapResourceError(
                    f"sitemap transferred bytes limit exceeded for {url}: ceiling={SITEMAP_TRANSFER_MAX_BYTES} bytes"
                )
            return resources.get(url)

        with patch(
            "buoy_search.crawler.fetch_url_bytes", side_effect=fake_fetch
        ):
            with self.assertRaisesRegex(SitemapResourceError, "oversized.xml"):
                discover_sitemap_page_urls(options)

    def test_sitemap_resource_errors_never_start_link_fallback(self) -> None:
        options = CrawlOptions(
            base_url="https://example.com/", out_dir=Path("unused")
        )
        errors = (
            SitemapResourceError(
                f"sitemap transferred bytes limit exceeded for https://example.com/oversized.xml: ceiling={SITEMAP_TRANSFER_MAX_BYTES} bytes"
            ),
            SitemapResourceError(
                "malformed gzip sitemap at https://example.com/malformed.xml.gz"
            ),
        )
        for error in errors:
            with self.subTest(error=str(error)):
                with patch(
                    "buoy_search.crawler.discover_sitemap_page_urls",
                    side_effect=error,
                ):
                    with patch(
                        "buoy_search.crawler.build_link_spider_class"
                    ) as link_mock:
                        with self.assertRaises(SitemapResourceError):
                            crawl_pages(options)
                link_mock.assert_not_called()

    def test_sitemap_page_progress_label_uses_estimate_not_cap_when_available(self) -> None:
        self.assertEqual(sitemap_page_progress_label(1, sitemap_url_count=0, cap=3000), "1; cap=3000")
        self.assertEqual(sitemap_page_progress_label(1, sitemap_url_count=842, cap=3000), "1/842; cap=3000")
        self.assertEqual(
            sitemap_page_progress_label(1, sitemap_url_count=5231, cap=3000),
            "1/3000; sitemap=5231; cap=3000",
        )

    def test_analyze_docs_version_urls_detects_iceberg_style_version_family(self) -> None:
        urls = []
        for version in ("1.10.0", "1.10.1", "1.10.2", "latest", "nightly"):
            for page in range(8):
                urls.append(f"https://iceberg.apache.org/docs/{version}/page-{page}/")
        urls.append("https://iceberg.apache.org/blog/release/")

        warning = analyze_docs_version_urls(urls, policy="warn")
        latest = analyze_docs_version_urls(urls, policy="latest")
        stable = analyze_docs_version_urls(urls, policy="stable-latest")
        latest_nightly = analyze_docs_version_urls(urls, policy="latest-nightly")

        self.assertTrue(warning["detected"])
        self.assertEqual(warning["root_path"], "/docs")
        self.assertEqual(warning["version_count"], 5)
        self.assertEqual(warning["versioned_url_count"], 40)
        self.assertEqual(warning["suggested_policy"], "latest")
        self.assertEqual(latest["selected_versions"], ["latest"])
        self.assertIn("/docs/1.10.2/**", latest["added_exclude_paths"])
        self.assertEqual(stable["selected_versions"], ["1.10.2"])
        self.assertEqual(latest_nightly["selected_versions"], ["latest", "nightly"])

    def test_apply_docs_version_policy_adds_effective_excludes(self) -> None:
        urls = []
        for version in ("1.0.0", "1.1.0", "latest"):
            for page in range(10):
                urls.append(f"https://example.com/docs/{version}/page-{page}/")
        options = CrawlOptions(
            base_url="https://example.com/",
            out_dir=Path("unused"),
            docs_version_policy="latest",
            exclude_paths=("/private/**",),
        )

        with patch("buoy_search.crawler.discover_sitemap_page_urls", return_value=urls):
            effective, report = apply_docs_version_policy(options)

        self.assertTrue(report["applied"])
        self.assertEqual(report["selected_versions"], ["latest"])
        self.assertEqual(effective.exclude_paths, ("/private/**", "/docs/1.0.0/**", "/docs/1.1.0/**"))

    def test_analyze_language_urls_detects_multilingual_locale_prefixes(self) -> None:
        urls = [f"https://blowfish.page/samples/page-{page}/" for page in range(12)]
        for locale in ("de", "fr", "it", "pt-br", "zh-cn"):
            for page in range(10):
                urls.append(f"https://blowfish.page/{locale}/samples/page-{page}/")

        report = analyze_language_urls(urls, policy="english")

        self.assertTrue(report["detected"])
        self.assertTrue(report["applied"])
        self.assertEqual(report["non_english_url_count"], 50)
        self.assertEqual(report["selected_languages"], ["unprefixed"])
        self.assertEqual(report["added_exclude_paths"], ["/de/**", "/fr/**", "/it/**", "/pt-br/**", "/zh-cn/**"])

    def test_apply_language_policy_adds_effective_excludes(self) -> None:
        urls = [f"https://example.com/docs/page-{page}/" for page in range(12)]
        for locale in ("de", "fr", "es"):
            for page in range(8):
                urls.append(f"https://example.com/{locale}/docs/page-{page}/")
        options = CrawlOptions(
            base_url="https://example.com/",
            out_dir=Path("unused"),
            language_policy="english",
            exclude_paths=("/private/**",),
        )

        with patch("buoy_search.crawler.discover_sitemap_page_urls", return_value=urls):
            effective, report = apply_language_policy(options)

        self.assertTrue(report["applied"])
        self.assertEqual(effective.exclude_paths, ("/private/**", "/de/**", "/es/**", "/fr/**"))

    def test_language_policy_all_keeps_localized_paths(self) -> None:
        urls = [f"https://example.com/de/docs/page-{page}/" for page in range(20)]
        options = CrawlOptions(
            base_url="https://example.com/",
            out_dir=Path("unused"),
            language_policy="all",
        )

        with patch("buoy_search.crawler.discover_sitemap_page_urls", return_value=urls) as discover_mock:
            effective, report = apply_language_policy(options)

        self.assertFalse(report["detected"])
        self.assertEqual(effective.exclude_paths, ())
        discover_mock.assert_not_called()

    def test_docs_version_block_message_recommends_explicit_policy(self) -> None:
        message = docs_version_block_message(
            {
                "detected": True,
                "policy": "warn",
                "root_path": "/docs",
                "version_count": 22,
                "versioned_url_count": 837,
                "suggested_policy": "latest",
            }
        )

        self.assertIsNotNone(message)
        assert message is not None
        self.assertIn("detected versioned docs under /docs", message)
        self.assertIn("stopping before page crawl", message)
        self.assertIn("--docs-version-policy latest", message)
        self.assertIn("--docs-version-policy all", message)

    def test_crawl_site_stops_default_warn_policy_before_page_crawl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            urls = []
            for version in ("1.0.0", "1.1.0", "latest"):
                for page in range(10):
                    urls.append(f"https://example.com/docs/{version}/page-{page}/")

            options = CrawlOptions(
                base_url="https://example.com/",
                out_dir=Path(tmp),
                docs_version_policy="warn",
            )
            with patch("buoy_search.crawler.discover_sitemap_page_urls", return_value=urls):
                with patch("buoy_search.crawler.crawl_pages") as crawl_pages_mock:
                    with self.assertRaisesRegex(RuntimeError, "stopping before page crawl"):
                        crawl_site(options)

        crawl_pages_mock.assert_not_called()

    def test_sitemap_spider_estimates_unique_filtered_urls_beyond_cap(self) -> None:
        events: list[str] = []
        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=2,
            include_paths=("/docs/**",),
            progress_callback=events.append,
        )
        spider_cls = build_sitemap_spider_class(options, "example.com")
        spider = spider_cls()

        class Response:
            def follow(self, url, callback=None):
                return (url, callback)

        response = Response()

        self.assertIsNotNone(spider._dispatch(response, "https://example.com/docs/a", []))
        self.assertIsNotNone(spider._dispatch(response, "https://example.com/docs/b", []))
        self.assertIsNone(spider._dispatch(response, "https://example.com/blog/c", []))
        self.assertIsNone(spider._dispatch(response, "https://example.com/docs/a#duplicate", []))
        self.assertIsNone(spider._dispatch(response, "https://example.com/docs/c", []))

        self.assertIn("crawl sitemap: discovering pages; cap=2", events)
        self.assertIn("crawl sitemap: sitemap=1; queued=1; cap=2; https://example.com/docs/a", events)
        self.assertIn("crawl sitemap: sitemap=2; queued=2; cap=2; https://example.com/docs/b", events)
        self.assertIn("crawl sitemap: sitemap=3; queued=2; cap=2; https://example.com/docs/c", events)

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

    def test_crawl_pdf_uses_markitdown_output_without_storing_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "Annual Plan.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 text pdf fixture")
            source = detect_source(str(pdf_path))
            assert isinstance(source, PdfSource)
            options = CrawlOptions(base_url=source.base_url, out_dir=root / "crawl", max_chunks=10)

            with patch(
                "buoy_search.crawler.markitdown_pdf_to_markdown",
                return_value=(
                    "# Annual Plan\n\nUseful PDF [reference](file:///retained.pdf?field=value) "
                    "text for retrieval."
                ),
            ):
                summary = crawl_pdf(source, options)

            self.assertEqual(summary["source_kind"], "pdf")
            self.assertEqual(summary["base_url"], source.base_url)
            self.assertEqual(summary["document_url"], source.document_url)
            self.assertEqual(summary["pdf_filename"], "Annual Plan.pdf")
            self.assertEqual(summary["pdf_sha256"], source.file_sha256)
            self.assertEqual(summary["namespace_candidate"], source.namespace_candidate)
            self.assertEqual(summary["crawl_strategy"], "markitdown-pdf")
            self.assertEqual(summary["pages_scraped"], 1)
            self.assertEqual(summary["chunks_generated"], 1)
            self.assertNotIn("blocked_discovery_count", summary)
            self.assertNotIn("blocked_redirect_count", summary)
            self.assertIn(
                "[reference](file:///retained.pdf?field=value)",
                str(summary["sample_chunks"][0]["content_preview"]),
            )
            page_files = list((root / "crawl" / "pages").glob("*.md"))
            self.assertEqual(len(page_files), 1)
            page_text = page_files[0].read_text(encoding="utf-8")
            self.assertIn('source_kind: "pdf"', page_text)
            self.assertIn('pdf_filename: "Annual Plan.pdf"', page_text)
            self.assertIn(f'pdf_sha256: "{source.file_sha256}"', page_text)
            serialized = json.dumps(summary, sort_keys=True) + page_text
            self.assertNotIn(str(pdf_path), serialized)

    def test_crawl_local_file_uses_markitdown_output_without_storing_source_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "Annual Plan.csv"
            csv_path.write_bytes(b"metric,value\nrevenue,42\n")
            source = detect_source(str(csv_path))
            assert isinstance(source, LocalFileSource)
            options = CrawlOptions(base_url=source.base_url, out_dir=root / "crawl", max_chunks=10)

            with patch(
                "buoy_search.crawler.markitdown_file_to_markdown",
                return_value=(
                    "| metric | value |\n| --- | --- |\n| revenue | "
                    "[42](file:///retained.csv?field=value) |"
                ),
            ):
                summary = crawl_local_document(source, options)

            self.assertEqual(summary["source_kind"], "local_file")
            self.assertEqual(summary["base_url"], source.base_url)
            self.assertEqual(summary["document_url"], source.document_url)
            self.assertEqual(summary["file_filename"], "Annual Plan.csv")
            self.assertEqual(summary["file_extension"], "csv")
            self.assertEqual(summary["file_sha256"], source.file_sha256)
            self.assertEqual(summary["namespace_candidate"], source.namespace_candidate)
            self.assertEqual(summary["crawl_strategy"], "markitdown-local-file")
            self.assertEqual(summary["documents_converted"], 1)
            self.assertEqual(summary["pages_scraped"], 1)
            self.assertEqual(summary["chunks_generated"], 1)
            self.assertNotIn("blocked_discovery_count", summary)
            self.assertNotIn("blocked_redirect_count", summary)
            self.assertIn(
                "[42](file:///retained.csv?field=value)",
                str(summary["sample_chunks"][0]["content_preview"]),
            )
            page_files = list((root / "crawl" / "pages").glob("*.md"))
            self.assertEqual(len(page_files), 1)
            page_text = page_files[0].read_text(encoding="utf-8")
            self.assertIn('source_kind: "local_file"', page_text)
            self.assertIn('file_filename: "Annual Plan.csv"', page_text)
            self.assertIn('file_extension: "csv"', page_text)
            self.assertIn(f'file_sha256: "{source.file_sha256}"', page_text)
            self.assertNotIn("pdf_filename", page_text)
            serialized = json.dumps(summary, sort_keys=True) + page_text
            self.assertNotIn(str(csv_path), serialized)

    def test_crawl_pdf_rejects_empty_markitdown_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "scan.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 image-only fixture")
            source = detect_source(str(pdf_path))
            assert isinstance(source, PdfSource)
            options = CrawlOptions(base_url=source.base_url, out_dir=root / "crawl")

            with patch("buoy_search.crawler.markitdown_pdf_to_markdown", return_value=" \n"):
                with self.assertRaisesRegex(RuntimeError, "No text was extracted"):
                    crawl_pdf(source, options)

            self.assertFalse((root / "crawl" / "summary.json").exists())

    def test_crawl_local_file_rejects_empty_markitdown_extraction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text_path = root / "empty.txt"
            text_path.write_text("", encoding="utf-8")
            source = detect_source(str(text_path))
            assert isinstance(source, LocalFileSource)
            options = CrawlOptions(base_url=source.base_url, out_dir=root / "crawl")

            with patch("buoy_search.crawler.markitdown_file_to_markdown", return_value=" \n"):
                with self.assertRaisesRegex(RuntimeError, "No text was extracted"):
                    crawl_local_document(source, options)

            self.assertFalse((root / "crawl" / "summary.json").exists())

    def test_crawled_page_from_response_skips_unextractable_html(self) -> None:
        class Response:
            status = 200
            url = "https://example.com/control-chars"

        with patch("buoy_search.crawler.markdown_from_response", side_effect=ValueError("bad html")):
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
        with patch("buoy_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider):
            with patch("buoy_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("buoy_search.crawler.run_scrapling_spider", side_effect=fake_run):
                    pages, stats, strategy = crawl_pages(
                        options,
                        sitemap_page_urls=["https://example.com/sitemap-page"],
                    )

        self.assertEqual(strategy, "hybrid")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/", "https://example.com/docs/pinning"])
        self.assertEqual(stats["requests_count"], 5)

    def test_default_sitemap_strategy_skips_link_crawl_when_sitemap_has_pages(self) -> None:
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

        def fake_run(spider_cls):
            if spider_cls is SitemapSpider:
                return [sitemap_page], {"requests_count": 2}
            raise AssertionError("link spider should not run when sitemap has pages")

        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=10,
        )
        with patch("buoy_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider):
            with patch("buoy_search.crawler.build_link_spider_class", return_value=LinkSpider) as link_mock:
                with patch("buoy_search.crawler.run_scrapling_spider", side_effect=fake_run):
                    pages, stats, strategy = crawl_pages(
                        options,
                        sitemap_page_urls=["https://example.com/sitemap-page"],
                    )

        self.assertEqual(strategy, "sitemap")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/"])
        self.assertEqual(stats["requests_count"], 2)
        link_mock.assert_not_called()

    def test_sitemap_strategy_falls_back_to_link_crawl_when_sitemap_is_empty(self) -> None:
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

        def fake_run(spider_cls):
            if spider_cls is SitemapSpider:
                return [], {"requests_count": 1}
            if spider_cls is LinkSpider:
                return [link_page], {"requests_count": 3}
            raise AssertionError("unexpected spider")

        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=10,
            crawl_strategy="sitemap",
        )
        with patch("buoy_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider):
            with patch("buoy_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("buoy_search.crawler.run_scrapling_spider", side_effect=fake_run):
                    pages, stats, strategy = crawl_pages(
                        options,
                        sitemap_page_urls=["https://example.com/sitemap-page"],
                    )

        self.assertEqual(strategy, "link_fallback")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/pinning"])
        self.assertEqual(stats["requests_count"], 4)

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
        with patch("buoy_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider) as sitemap_mock:
            with patch("buoy_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("buoy_search.crawler.run_scrapling_spider", return_value=([link_page], {"requests_count": 1})):
                    pages, stats, strategy = crawl_pages(options)

        self.assertEqual(strategy, "link")
        self.assertEqual([page.url for page in pages], ["https://example.com/docs/pinning"])
        self.assertEqual(stats["requests_count"], 1)
        sitemap_mock.assert_not_called()

    def test_crawl_pages_emits_high_level_progress_events(self) -> None:
        class SitemapSpider:
            pass

        class LinkSpider:
            pass

        events: list[str] = []
        sitemap_page = CrawledPage(url="https://example.com/docs/", title="Docs", status=200, markdown="Docs home")
        link_page = CrawledPage(url="https://example.com/docs/pinning", title="Pinning", status=200, markdown="Pinning")

        def fake_run(spider_cls):
            if spider_cls is SitemapSpider:
                return [sitemap_page], {"requests_count": 2}
            if spider_cls is LinkSpider:
                return [link_page], {"requests_count": 3}
            raise AssertionError("unexpected spider")

        options = CrawlOptions(
            base_url="https://example.com/docs/",
            out_dir=Path("unused"),
            max_pages=10,
            crawl_strategy="hybrid",
            progress_callback=events.append,
        )
        with patch("buoy_search.crawler.build_sitemap_spider_class", return_value=SitemapSpider):
            with patch("buoy_search.crawler.build_link_spider_class", return_value=LinkSpider):
                with patch("buoy_search.crawler.run_scrapling_spider", side_effect=fake_run):
                    pages, _stats, strategy = crawl_pages(
                        options,
                        sitemap_page_urls=["https://example.com/sitemap-page"],
                    )

        self.assertEqual(strategy, "hybrid")
        self.assertEqual(len(pages), 2)
        self.assertIn("crawl: starting sitemap crawl for example.com", events)
        self.assertIn("crawl: sitemap done pages=1; requests=2", events)
        self.assertIn("crawl: starting link crawl for example.com", events)
        self.assertIn("crawl: link done pages=1; requests=3", events)
        self.assertIn("crawl: merged unique pages=2", events)


if __name__ == "__main__":
    unittest.main()
