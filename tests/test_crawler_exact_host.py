from __future__ import annotations

from collections import Counter
from contextlib import contextmanager, redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
import json
from pathlib import Path
import tempfile
from threading import Thread
from typing import Callable, Iterator
import unittest
from unittest.mock import patch
from urllib.parse import urlparse

import anyio

from buoy_search.cli import print_crawl_text
from buoy_search.crawler import (
    CrawlOptions,
    _assert_scrapling_runtime_shape,
    build_link_spider_class,
    crawl_site,
    discover_sitemap_page_urls,
    summary_content_preview,
)


ResponseSpec = tuple[int, dict[str, str], str]
Router = Callable[[str], ResponseSpec]


class _FixtureServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _FixtureHandler)
        self.counts: Counter[str] = Counter()
        self.router: Router = lambda _path: (404, {}, "not found")


class _FixtureHandler(BaseHTTPRequestHandler):
    server: _FixtureServer

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler hook.
        parsed = urlparse(self.path)
        self.server.counts[parsed.path] += 1
        status, headers, body = self.server.router(self.path)
        payload = body.encode("utf-8")
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


@contextmanager
def fixture_server() -> Iterator[_FixtureServer]:
    server = _FixtureServer()
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def html_page(title: str, links: list[str] | None = None) -> str:
    anchors = "".join(f'<a href="{link}">link</a>' for link in links or [])
    return f"<html><head><title>{title}</title></head><body><main><h1>{title}</h1><p>Useful local fixture content.</p>{anchors}</main></body></html>"


def crawl_options(base_url: str, out_dir: Path, *, strategy: str) -> CrawlOptions:
    return CrawlOptions(
        base_url=base_url,
        out_dir=out_dir,
        max_pages=100,
        max_chunks=1000,
        concurrent_requests=1,
        concurrent_requests_per_domain=1,
        download_delay=0,
        crawl_strategy=strategy,
        docs_version_policy="all",
        language_policy="all",
    )


class ExactHostCrawlBoundaryTests(unittest.TestCase):
    def test_link_discovery_and_redirects_never_request_unreviewed_hosts(self) -> None:
        with fixture_server() as allowed, fixture_server() as destination, tempfile.TemporaryDirectory() as tmp:
            allowed_origin = f"http://localhost:{allowed.server_port}"
            destination_localhost = f"http://localhost:{destination.server_port}"
            destination_ip = f"http://127.0.0.1:{destination.server_port}"
            blocked_paths = {
                "/external_(nested)",
                "/protocol-relative",
                "/oauth",
                "/sibling",
                "/open-destination",
                "/chained-destination",
            }

            destination.router = lambda path: (
                200,
                {"Content-Type": "text/html"},
                html_page("Same host, different port")
                if urlparse(path).path == "/same-host-port"
                else "unauthorized destination",
            )

            links = [
                "/same-one",
                "/chain-one",
                "/denied",
                "/redirect-denied",
                f"{destination_localhost}/same-host-port",
                f"{destination_ip}/external_(nested)?secret=external-query&SENTINEL_EXTERNAL=1",
                f"//127.0.0.1:{destination.server_port}/protocol-relative?secret=protocol-query&SENTINEL_PROTOCOL=1",
                f"http://allowed.example@127.0.0.1:{destination.server_port}/oauth?code=oauth-code&SENTINEL_OAUTH=1",
                f"http://sibling.localhost:{destination.server_port}/sibling?token=sibling-token&SENTINEL_SIBLING=1",
                "/open",
                "/chained-start",
                "/limit/0",
                "/over/0",
            ]

            def allowed_router(raw_path: str) -> ResponseSpec:
                path = urlparse(raw_path).path
                if path == "/robots.txt":
                    return 200, {"Content-Type": "text/plain"}, "User-agent: *\nDisallow: /denied\n"
                if path == "/":
                    return 200, {"Content-Type": "text/html"}, html_page("Home", links)
                if path == "/same-one":
                    return 302, {"Location": "/final-one"}, ""
                if path == "/redirect-denied":
                    return 302, {"Location": "/denied"}, ""
                if path == "/chain-one":
                    return 301, {"Location": "/chain-two"}, ""
                if path == "/chain-two":
                    return 307, {"Location": "/final-two"}, ""
                if path in {"/final-one", "/final-two"}:
                    return 200, {"Content-Type": "text/html"}, html_page(path)
                if path == "/open":
                    return 302, {"Location": f"{destination_ip}/open-destination?secret=open-query"}, ""
                if path == "/chained-start":
                    return 302, {"Location": "/chained-middle"}, ""
                if path == "/chained-middle":
                    return 302, {"Location": f"{destination_ip}/chained-destination?code=chain-code"}, ""
                if path.startswith("/limit/"):
                    hop = int(path.rsplit("/", 1)[-1])
                    if hop < 20:
                        return 302, {"Location": f"/limit/{hop + 1}"}, ""
                    return 200, {"Content-Type": "text/html"}, html_page("Twenty hop final")
                if path.startswith("/over/"):
                    hop = int(path.rsplit("/", 1)[-1])
                    return 302, {"Location": f"/over/{hop + 1}"}, ""
                return 404, {}, "not found"

            allowed.router = allowed_router
            summary = crawl_site(
                crawl_options(f"{allowed_origin}/", Path(tmp), strategy="link")
            )

            self.assertGreaterEqual(int(summary["blocked_discovery_count"]), 4)
            self.assertGreaterEqual(int(summary["blocked_redirect_count"]), 3)
            self.assertEqual(allowed.counts["/denied"], 0)
            self.assertEqual(allowed.counts["/limit/20"], 1)
            self.assertEqual(allowed.counts["/over/20"], 1)
            self.assertEqual(allowed.counts["/over/21"], 0)
            self.assertGreaterEqual(destination.counts["/same-host-port"], 1)
            for path in blocked_paths:
                self.assertEqual(destination.counts[path], 0, path)

            stdout = StringIO()
            with redirect_stdout(stdout):
                print_crawl_text(summary)
            rendered_summaries = json.dumps(summary, sort_keys=True) + stdout.getvalue()
            for blocked_detail in (
                "127.0.0.1",
                "allowed.example@",
                "external_(nested)",
                "external-query",
                "protocol-query",
                "oauth-code",
                "sibling-token",
                "open-query",
                "chain-code",
                "SENTINEL_EXTERNAL",
                "SENTINEL_PROTOCOL",
                "SENTINEL_OAUTH",
                "SENTINEL_SIBLING",
            ):
                self.assertNotIn(blocked_detail, rendered_summaries)

    def test_summary_redacts_autolinks_and_url_like_visible_labels(self) -> None:
        with fixture_server() as allowed, fixture_server() as destination, tempfile.TemporaryDirectory() as tmp:
            allowed_origin = f"http://localhost:{allowed.server_port}"
            autolink_url = (
                f"http://AUTOLINK_USER@127.0.0.1:{destination.server_port}"
                "/autolink_(nested)/oauth/callback?code=AUTOLINK_QUERY#AUTOLINK_SENTINEL"
            )
            visible_url = (
                f"http://VISIBLE_USER@127.0.0.1:{destination.server_port}"
                "/visible_(nested)/oauth/callback?token=VISIBLE_QUERY#VISIBLE_SENTINEL"
            )
            visible_destination = visible_url.replace(
                "VISIBLE_SENTINEL", "DESTINATION_SENTINEL"
            )

            destination.router = lambda _path: (
                200,
                {"Content-Type": "text/html"},
                "unauthorized destination",
            )

            def allowed_router(raw_path: str) -> ResponseSpec:
                path = urlparse(raw_path).path
                if path == "/robots.txt":
                    return 200, {"Content-Type": "text/plain"}, "User-agent: *\n"
                if path == "/":
                    return (
                        200,
                        {"Content-Type": "text/html"},
                        "<html><head><title>Sanitizer fixture</title></head><body><main>"
                        "<p>Useful sanitizer fixture content before links.</p>"
                        f"<p>&lt;{autolink_url}&gt;</p>"
                        f'<a href="{autolink_url}">{autolink_url}</a>'
                        f'<a href="{visible_destination}">{visible_url}</a>'
                        "<p>Useful sanitizer fixture content after links.</p>"
                        "</main></body></html>",
                    )
                return 404, {}, "not found"

            allowed.router = allowed_router
            summary = crawl_site(
                crawl_options(f"{allowed_origin}/", Path(tmp), strategy="link")
            )

            crawled_markdown = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (Path(tmp) / "pages").glob("*.md")
            )
            self.assertIn(r"<http://AUTOLINK\_USER@", crawled_markdown)
            self.assertIn("<http://AUTOLINK_USER@", crawled_markdown)
            self.assertIn(r"[http://VISIBLE\_USER@", crawled_markdown)
            self.assertEqual(destination.counts["/autolink_(nested)/oauth/callback"], 0)
            self.assertEqual(destination.counts["/visible_(nested)/oauth/callback"], 0)

            stdout = StringIO()
            with redirect_stdout(stdout):
                print_crawl_text(summary)
            rendered_summaries = json.dumps(summary, sort_keys=True) + stdout.getvalue()
            for blocked_detail in (
                "127.0.0.1",
                "AUTOLINK_USER@",
                "VISIBLE_USER@",
                "autolink_(nested)",
                "visible_(nested)",
                "oauth/callback",
                "AUTOLINK_QUERY",
                "VISIBLE_QUERY",
                "AUTOLINK_SENTINEL",
                "VISIBLE_SENTINEL",
                "DESTINATION_SENTINEL",
            ):
                self.assertNotIn(blocked_detail, rendered_summaries)
            self.assertIn("Useful sanitizer fixture content", rendered_summaries)

    def test_sitemap_and_robots_declarations_and_redirects_stay_on_host(self) -> None:
        with fixture_server() as allowed, fixture_server() as destination, tempfile.TemporaryDirectory() as tmp:
            allowed_origin = f"http://localhost:{allowed.server_port}"
            destination_ip = f"http://127.0.0.1:{destination.server_port}"

            destination.router = lambda _path: (200, {"Content-Type": "text/xml"}, "unauthorized")

            def allowed_router(raw_path: str) -> ResponseSpec:
                path = urlparse(raw_path).path
                if path == "/robots.txt":
                    return 302, {"Location": "/actual-robots.txt"}, ""
                if path == "/actual-robots.txt":
                    return (
                        200,
                        {"Content-Type": "text/plain"},
                        "User-agent: *\nDisallow: /sitemap-denied\n"
                        f"Sitemap: {allowed_origin}/robots-sitemap.xml\n"
                        f"Sitemap: {destination_ip}/robots-external.xml?token=robots-token\n",
                    )
                if path == "/sitemap.xml":
                    return 302, {"Location": "/actual-sitemap.xml"}, ""
                if path == "/sitemap_index.xml":
                    return 302, {"Location": f"{destination_ip}/redirected-index.xml?secret=index-query"}, ""
                if path == "/actual-sitemap.xml":
                    return (
                        200,
                        {"Content-Type": "application/xml"},
                        "<urlset>"
                        f"<url><loc>{allowed_origin}/sitemap-page-redirect</loc></url>"
                        f"<url><loc>{allowed_origin}/sitemap-denied</loc></url>"
                        f"<url><loc>{destination_ip}/external-page?secret=page-query</loc></url>"
                        f"<url><loc>//127.0.0.1:{destination.server_port}/protocol-page?code=protocol-code</loc></url>"
                        "</urlset>",
                    )
                if path == "/robots-sitemap.xml":
                    return (
                        200,
                        {"Content-Type": "application/xml"},
                        "<sitemapindex>"
                        f"<sitemap><loc>{allowed_origin}/child.xml</loc></sitemap>"
                        f"<sitemap><loc>{destination_ip}/external-child.xml?token=child-token</loc></sitemap>"
                        "</sitemapindex>",
                    )
                if path == "/child.xml":
                    return 200, {"Content-Type": "application/xml"}, "<urlset></urlset>"
                if path == "/sitemap-page-redirect":
                    return 308, {"Location": "/sitemap-final"}, ""
                if path == "/sitemap-final":
                    return 200, {"Content-Type": "text/html"}, html_page("Sitemap final")
                if path == "/sitemap-denied":
                    return 200, {"Content-Type": "text/html"}, html_page("Denied")
                return 404, {}, "not found"

            allowed.router = allowed_router
            summary = crawl_site(
                crawl_options(f"{allowed_origin}/", Path(tmp), strategy="sitemap")
            )

            self.assertEqual(summary["crawl_strategy"], "sitemap")
            self.assertGreaterEqual(int(summary["blocked_discovery_count"]), 4)
            self.assertGreaterEqual(int(summary["blocked_redirect_count"]), 1)
            self.assertEqual(allowed.counts["/sitemap-denied"], 0)
            self.assertGreaterEqual(allowed.counts["/sitemap-final"], 1)
            for path in (
                "/robots-external.xml",
                "/redirected-index.xml",
                "/external-page",
                "/protocol-page",
                "/external-child.xml",
            ):
                self.assertEqual(destination.counts[path], 0, path)

            serialized = json.dumps(summary, sort_keys=True)
            for secret in (
                "robots-token",
                "index-query",
                "page-query",
                "protocol-code",
                "child-token",
            ):
                self.assertNotIn(secret, serialized)

    def test_sitemap_policy_analysis_checks_redirects_and_declarations(self) -> None:
        with fixture_server() as allowed, fixture_server() as destination:
            allowed_origin = f"http://localhost:{allowed.server_port}"
            destination_ip = f"http://127.0.0.1:{destination.server_port}"
            destination.router = lambda _path: (200, {"Content-Type": "application/xml"}, "<urlset></urlset>")

            def allowed_router(raw_path: str) -> ResponseSpec:
                path = urlparse(raw_path).path
                if path == "/robots.txt":
                    return (
                        200,
                        {"Content-Type": "text/plain"},
                        f"Sitemap: {allowed_origin}/declared.xml\n"
                        f"Sitemap: {destination_ip}/blocked-declared.xml?token=declaration-token\n",
                    )
                if path == "/sitemap.xml":
                    return 302, {"Location": "/actual-policy-sitemap.xml"}, ""
                if path == "/sitemap_index.xml":
                    return 302, {"Location": f"{destination_ip}/blocked-redirect.xml?code=redirect-code"}, ""
                if path in {"/actual-policy-sitemap.xml", "/declared.xml"}:
                    return (
                        200,
                        {"Content-Type": "application/xml"},
                        "<urlset>"
                        f"<url><loc>{allowed_origin}/policy-page</loc></url>"
                        f"<url><loc>{destination_ip}/blocked-page?secret=page-secret</loc></url>"
                        "</urlset>",
                    )
                return 404, {}, "not found"

            allowed.router = allowed_router
            stats: dict[str, object] = {}
            urls = discover_sitemap_page_urls(
                crawl_options(allowed_origin, Path("unused"), strategy="sitemap"),
                boundary_stats=stats,
            )

            self.assertEqual(urls, [f"{allowed_origin}/policy-page"])
            self.assertGreaterEqual(int(stats["blocked_discovery_count"]), 2)
            self.assertEqual(int(stats["blocked_redirect_count"]), 1)
            for path in ("/blocked-declared.xml", "/blocked-redirect.xml", "/blocked-page"):
                self.assertEqual(destination.counts[path], 0, path)

    def test_unexpected_off_host_final_response_is_rejected(self) -> None:
        spider = build_link_spider_class(
            crawl_options("http://localhost:8000/", Path("unused"), strategy="link"),
            "localhost",
        )()

        class Response:
            url = "http://127.0.0.1:9000/final?secret=unexpected-query"
            history: list[object] = []

        self.assertFalse(spider._response_stayed_on_host(Response()))
        self.assertEqual(spider._blocked_redirect_count, 1)

    def test_summary_destination_sanitizer_consumes_valid_complex_destinations(self) -> None:
        content = (
            r'Before [nested](https://allowed.example@blocked.invalid/a_(b\)c)?code=oauth-query&SENTINEL_NESTED=1 "title (safe)") '
            r"and [angle](<https://blocked.invalid/a(unbalanced?token=query-sentinel&SENTINEL_ANGLE=1> 'OAuth title)') after."
        )

        preview = summary_content_preview(content)

        self.assertEqual(preview, "Before [nested] and [angle] after.")
        for blocked_detail in (
            "blocked.invalid",
            "allowed.example@",
            "oauth-query",
            "query-sentinel",
            "SENTINEL_NESTED",
            "SENTINEL_ANGLE",
        ):
            self.assertNotIn(blocked_detail, preview)

    def test_summary_destination_sanitizer_redacts_autolinks_and_url_labels(self) -> None:
        content = (
            r"Useful before <https://AUTO_USER@blocked.invalid/a_(b\)c)?code=AUTO_QUERY#AUTO_SENTINEL> "
            r"and [https://LABEL_USER@blocked.invalid/label_(nested)?token=LABEL_QUERY#LABEL_SENTINEL]"
            r"(https://DEST_USER@blocked.invalid/destination_(nested)?secret=DEST_QUERY#DEST_SENTINEL) "
            r"plus //PROTO_USER@blocked.invalid/protocol_(nested)?key=PROTO_QUERY#PROTO_SENTINEL useful after."
        )

        preview = summary_content_preview(content, max_length=500)

        self.assertIn("Useful before", preview)
        self.assertIn("useful after", preview)
        self.assertGreaterEqual(preview.count("[redacted URL]"), 3)
        for blocked_detail in (
            "blocked.invalid",
            "AUTO_USER@",
            "LABEL_USER@",
            "DEST_USER@",
            "PROTO_USER@",
            "_(nested)",
            "AUTO_QUERY",
            "LABEL_QUERY",
            "DEST_QUERY",
            "PROTO_QUERY",
            "AUTO_SENTINEL",
            "LABEL_SENTINEL",
            "DEST_SENTINEL",
            "PROTO_SENTINEL",
        ):
            self.assertNotIn(blocked_detail, preview)

    def test_redirected_robots_denial_is_used_before_page_requests(self) -> None:
        with fixture_server() as allowed, tempfile.TemporaryDirectory() as tmp:
            origin = f"http://localhost:{allowed.server_port}"

            def router(raw_path: str) -> ResponseSpec:
                path = urlparse(raw_path).path
                if path == "/robots.txt":
                    return 302, {"Location": "/redirected-robots.txt"}, ""
                if path == "/redirected-robots.txt":
                    return 200, {"Content-Type": "text/plain"}, "User-agent: *\nDisallow: /denied\n"
                if path == "/":
                    return 200, {"Content-Type": "text/html"}, html_page("Home", ["/denied"])
                if path == "/denied":
                    return 200, {"Content-Type": "text/html"}, html_page("Denied")
                return 404, {}, "not found"

            allowed.router = router
            summary = crawl_site(crawl_options(origin, Path(tmp), strategy="link"))

            self.assertGreaterEqual(allowed.counts["/robots.txt"], 1)
            self.assertGreaterEqual(allowed.counts["/redirected-robots.txt"], 1)
            self.assertEqual(allowed.counts["/denied"], 0)
            self.assertGreaterEqual(int(summary["robots_disallowed_count"]), 1)

    def test_scrapling_version_and_private_usage_changes_fail_before_requests(self) -> None:
        from scrapling.spiders.engine import CrawlerEngine
        from scrapling.spiders.robotstxt import RobotsTxtManager
        from scrapling.spiders.session import SessionManager

        async def changed_integration(*_args, **_kwargs):
            return None

        with patch("buoy_search.crawler.distribution_version", return_value="0.5.0"):
            with self.assertRaisesRegex(RuntimeError, "requires Scrapling 0.4.9"):
                _assert_scrapling_runtime_shape()

        for owner, attribute in (
            (CrawlerEngine, "crawl"),
            (RobotsTxtManager, "_get_parser"),
            (SessionManager, "fetch"),
        ):
            with self.subTest(integration=f"{owner.__name__}.{attribute}"):
                with patch.object(owner, attribute, changed_integration):
                    with self.assertRaisesRegex(RuntimeError, "refusing to request pages"):
                        _assert_scrapling_runtime_shape()

    def test_missing_runtime_robots_manager_fails_before_fetch(self) -> None:
        from scrapling.spiders.engine import CrawlerEngine

        spider = build_link_spider_class(
            crawl_options("http://localhost:8000/", Path("unused"), strategy="link"),
            "localhost",
        )()
        engine = CrawlerEngine(spider, spider._session_manager)
        engine._robots_manager = None
        spider._engine = engine

        with self.assertRaisesRegex(RuntimeError, "robots integration changed"):
            anyio.run(spider.on_start)

    def test_text_summary_reports_counts_without_blocked_url_details(self) -> None:
        payload: dict[str, object] = {
            "source_kind": "website",
            "base_url": "http://localhost:8000/",
            "namespace_candidate": "site-localhost-v1",
            "crawl_strategy": "link",
            "pages_scraped": 1,
            "chunks_generated": 1,
            "max_pages": 10,
            "max_chunks": 10,
            "limit_reached": False,
            "include_paths": [],
            "exclude_paths": [],
            "strip_trailing_slash": True,
            "docs_version_report": {"detected": False},
            "language_report": {"detected": False},
            "blocked_discovery_count": 4,
            "blocked_redirect_count": 2,
            "out_dir": "unused",
        }
        stdout = StringIO()
        with redirect_stdout(stdout):
            print_crawl_text(payload)

        output = stdout.getvalue()
        self.assertIn("blocked_discoveries=4; blocked_redirects=2", output)
        self.assertNotIn("?", output)
        self.assertNotIn("127.0.0.1", output)


if __name__ == "__main__":
    unittest.main()
