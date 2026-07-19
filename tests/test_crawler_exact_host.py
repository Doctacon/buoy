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
from urllib.parse import urlparse

from buoy_search.cli import print_crawl_text
from buoy_search.crawler import (
    CrawlOptions,
    build_link_spider_class,
    crawl_site,
    discover_sitemap_page_urls,
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
                "/external",
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
                f"{destination_ip}/external?secret=external-query",
                f"//127.0.0.1:{destination.server_port}/protocol-relative?secret=protocol-query",
                f"http://allowed.example@127.0.0.1:{destination.server_port}/oauth?code=oauth-code",
                f"http://sibling.localhost:{destination.server_port}/sibling?token=sibling-token",
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

            serialized = json.dumps(summary, sort_keys=True)
            for secret in (
                "external-query",
                "protocol-query",
                "oauth-code",
                "sibling-token",
                "open-query",
                "chain-code",
            ):
                self.assertNotIn(secret, serialized)

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
