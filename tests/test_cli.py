from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from turbo_search.applied_state import AppliedStateRow, build_applied_state, save_applied_state
from turbo_search.cli import build_parser, main
from turbo_search.crawler import CrawlOptions
from turbo_search.indexer import process_corpus
from turbo_search.plan_artifacts import build_plan_artifacts


def write_fake_crawl_page(pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "page.md").write_text(
        "\n".join(
            [
                "---",
                'url: "https://example.com/docs/page"',
                'title: "Example Page"',
                'status: "200"',
                'content_type: "text/html"',
                'source_hash: "source-hash"',
                'crawl_timestamp: "2026-06-20T00:00:00+00:00"',
                'fetcher: "test"',
                "---",
                "",
                "# Intro",
                "",
                "Useful documentation text for retrieval.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def fake_plan_crawl_summary(options: CrawlOptions) -> dict[str, object]:
    return {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "base_url": options.base_url,
        "allowed_host": "example.com",
        "namespace_candidate": "site-example-com-v1",
        "crawl_strategy": options.crawl_strategy,
        "requested_crawl_strategy": options.crawl_strategy,
        "sitemap_seed_urls": [],
        "out_dir": str(options.out_dir),
        "pages_dir": str(options.out_dir / "pages"),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": 1,
        "requests_count": 1,
        "robots_disallowed_count": 0,
        "blocked_requests_count": 0,
        "failed_requests_count": 0,
        "files_discovered": 1,
        "files_seen": 1,
        "files_error": 0,
        "chunks_generated": 1,
        "limit_reached": False,
        "sample_chunks": [],
        "errors": [],
    }


class CliTests(unittest.TestCase):
    def test_help_mentions_current_safe_workflow_commands(self) -> None:
        help_text = build_parser().format_help()

        self.assertIn("local-only", help_text)
        self.assertNotIn("index", help_text)
        self.assertIn("crawl", help_text)
        self.assertIn("plan", help_text)
        self.assertIn("apply", help_text)
        self.assertIn("retrieve", help_text)
        self.assertIn("evals", help_text)

    def test_crawl_command_validates_base_url_before_crawling(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["crawl", "--base-url", "/relative", "--json"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("base URL must be an absolute http(s) URL", stderr.getvalue())

    def test_crawl_command_is_dry_run_and_needs_no_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "crawl"
            fake_summary = {
                "command": "crawl",
                "dry_run": True,
                "credentials_required": False,
                "turbopuffer_api_calls": False,
                "api_calls_occurred": False,
                "base_url": "https://scrapling.readthedocs.io/en/latest/",
                "allowed_host": "scrapling.readthedocs.io",
                "namespace_candidate": "site-scrapling-readthedocs-io-v1",
                "crawl_strategy": "hybrid",
                "requested_crawl_strategy": "hybrid",
                "out_dir": str(out_dir),
                "pages_dir": str(out_dir / "pages"),
                "max_pages": 3,
                "max_chunks": 5,
                "css_selector": ".md-content__inner",
                "pages_scraped": 2,
                "requests_count": 4,
                "robots_disallowed_count": 0,
                "blocked_requests_count": 0,
                "failed_requests_count": 0,
                "chunks_generated": 5,
                "files_error": 0,
                "limit_reached": True,
                "sample_chunks": [
                    {
                        "id": "chunk-1",
                        "title": "Intro",
                        "url": "https://scrapling.readthedocs.io/en/latest/",
                        "section_path": "",
                        "content_preview": "Scrapling docs",
                    }
                ],
            }
            stdout = StringIO()
            with patch("turbo_search.cli.crawl_site", return_value=fake_summary) as crawl_mock:
                with redirect_stdout(stdout):
                    result = main(
                        [
                            "crawl",
                            "--base-url",
                            "https://scrapling.readthedocs.io/en/latest/",
                            "--out-dir",
                            str(out_dir),
                            "--max-pages",
                            "3",
                            "--max-chunks",
                            "5",
                            "--css-selector",
                            ".md-content__inner",
                            "--json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertFalse(payload["api_calls_occurred"])
        self.assertEqual(payload["namespace_candidate"], "site-scrapling-readthedocs-io-v1")
        self.assertEqual(payload["sample_chunks"][0]["title"], "Intro")
        crawl_mock.assert_called_once()
        options = crawl_mock.call_args.args[0]
        self.assertIsInstance(options, CrawlOptions)
        self.assertEqual(options.max_pages, 3)
        self.assertEqual(options.max_chunks, 5)
        self.assertEqual(options.crawl_strategy, "hybrid")
        self.assertEqual(options.include_paths, ())
        self.assertEqual(options.exclude_paths, ())
        self.assertTrue(options.strip_trailing_slash)
        self.assertEqual(options.css_selector, ".md-content__inner")

    def test_crawl_text_output_warns_when_caps_are_hit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "crawl"
            fake_summary = {
                "command": "crawl",
                "dry_run": True,
                "credentials_required": False,
                "turbopuffer_api_calls": False,
                "api_calls_occurred": False,
                "base_url": "https://example.com/",
                "allowed_host": "example.com",
                "namespace_candidate": "site-example-com-v1",
                "crawl_strategy": "hybrid",
                "out_dir": str(out_dir),
                "pages_dir": str(out_dir / "pages"),
                "max_pages": 3,
                "max_chunks": 5,
                "css_selector": None,
                "pages_scraped": 3,
                "requests_count": 4,
                "robots_disallowed_count": 0,
                "blocked_requests_count": 0,
                "failed_requests_count": 0,
                "chunks_generated": 5,
                "files_error": 0,
                "limit_reached": True,
                "sample_chunks": [],
            }
            stdout = StringIO()
            with patch("turbo_search.cli.crawl_site", return_value=fake_summary):
                with redirect_stdout(stdout):
                    result = main(["crawl", "--base-url", "https://example.com/", "--max-pages", "3", "--max-chunks", "5"])

        output = stdout.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("caps: max_pages=3; max_chunks=5; chunk_limit_reached=True", output)
        self.assertIn("warning: reached page cap, chunk cap", output)

    def test_crawl_command_defaults_to_hybrid_strategy(self) -> None:
        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            self.assertEqual(options.crawl_strategy, "hybrid")
            return fake_plan_crawl_summary(options)

        stdout = StringIO()
        with patch("turbo_search.cli.crawl_site", side_effect=fake_crawl):
            with redirect_stdout(stdout):
                result = main(
                    [
                        "crawl",
                        "--base-url",
                        "https://example.com/docs/",
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["crawl_strategy"], "hybrid")

    def test_plan_command_writes_artifacts_and_first_apply_diff_without_credentials(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "plan"
        state_root = root / "state"

        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            write_fake_crawl_page(options.out_dir / "pages")
            return fake_plan_crawl_summary(options)

        stdout = StringIO()
        with patch("turbo_search.cli.crawl_site", side_effect=fake_crawl) as crawl_mock:
            with redirect_stdout(stdout):
                result = main(
                    [
                        "plan",
                        "https://example.com/docs/",
                        "--out-dir",
                        str(out_dir),
                        "--state-root",
                        str(state_root),
                        "--max-pages",
                        "3",
                        "--max-chunks",
                        "5",
                        "--include-path",
                        "/docs/**",
                        "--exclude-path",
                        "/llms-full.txt",
                        "--css-selector",
                        "main",
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["command"], "plan")
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertFalse(payload["api_calls_occurred"])
        self.assertTrue(payload["state_first_apply"])
        self.assertEqual(payload["diff"]["rows_to_upsert"], 1)
        self.assertEqual(payload["diff"]["chunks_to_embed"], 1)
        self.assertEqual(payload["diff"]["stale_rows"], 0)
        self.assertEqual(payload["namespace"], "site-example-com-v1")
        self.assertEqual(payload["crawl_strategy"], "hybrid")
        self.assertEqual(payload["include_paths"], ["/docs/**"])
        self.assertEqual(payload["exclude_paths"], ["/llms-full.txt"])
        self.assertTrue(payload["strip_trailing_slash"])
        self.assertTrue((out_dir / "plan.json").exists())
        self.assertTrue((out_dir / "manifest.json").exists())
        self.assertTrue((out_dir / "chunks.jsonl").exists())
        self.assertTrue((out_dir / "summary.json").exists())
        self.assertEqual(len(list((out_dir / "pages").glob("*.md"))), 1)
        plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        chunks = [json.loads(line) for line in (out_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(plan["diff"]["rows_to_upsert"], 1)
        self.assertEqual(plan["crawl_options"]["crawl_strategy"], "hybrid")
        self.assertEqual(plan["crawl_options"]["include_paths"], ["/docs/**"])
        self.assertEqual(plan["crawl_options"]["exclude_paths"], ["/llms-full.txt"])
        self.assertTrue(plan["crawl_options"]["strip_trailing_slash"])
        self.assertEqual(plan["state_path"], str(state_root / "state/example-com/site-example-com-v1/last-applied.json"))
        self.assertEqual(len(manifest["pages"]), 1)
        self.assertEqual(len(chunks), 1)
        crawl_mock.assert_called_once()

    def test_plan_command_loads_existing_state_and_reports_unchanged_diff(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "plan"
        state_root = root / "state"
        corpus = root / "corpus"
        write_fake_crawl_page(corpus)
        artifacts = build_plan_artifacts(
            indexing_plan=process_corpus(corpus),
            base_url="https://example.com/docs/",
            out_dir=out_dir,
            state_root=state_root,
        )
        chunk = artifacts.manifest.chunks[0]
        save_applied_state(
            build_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                last_plan_id="plan_previous",
                last_apply_id="apply_previous",
                rows=[
                    AppliedStateRow(
                        row_id=chunk.row_id,
                        canonical_url=chunk.canonical_url,
                        page_hash=chunk.page_hash,
                        chunk_hash=chunk.chunk_hash,
                        embedding_text_hash=chunk.embedding_text_hash,
                        plan_id="plan_previous",
                        applied_at="2026-06-20T12:00:00+00:00",
                    )
                ],
                updated_at="2026-06-20T12:00:00+00:00",
            ),
            state_root=state_root,
        )

        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            write_fake_crawl_page(options.out_dir / "pages")
            return fake_plan_crawl_summary(options)

        stdout = StringIO()
        with patch("turbo_search.cli.crawl_site", side_effect=fake_crawl):
            with redirect_stdout(stdout):
                result = main(
                    [
                        "plan",
                        "--base-url",
                        "https://example.com/docs/",
                        "--out-dir",
                        str(out_dir),
                        "--state-root",
                        str(state_root),
                        "--json",
                    ]
                )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertFalse(payload["state_first_apply"])
        self.assertEqual(payload["diff"]["rows_to_upsert"], 0)
        self.assertEqual(payload["diff"]["chunks_to_embed"], 0)
        self.assertEqual(payload["diff"]["chunks_unchanged"], 1)
        self.assertEqual(payload["diff"]["stale_rows"], 0)
        written_plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(written_plan["diff"]["chunks_unchanged"], 1)

    def test_plan_command_validates_base_url_before_crawling(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["plan", "/relative", "--json"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("base URL must be an absolute http(s) URL", stderr.getvalue())

    def test_plan_command_rejects_conflicting_positional_and_flag_urls(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["plan", "https://example.com/a", "--base-url", "https://example.com/b", "--json"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("either positional URL or --base-url", stderr.getvalue())

    def test_plan_command_requires_url(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["plan", "--json"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("base URL is required", stderr.getvalue())

    def test_retrieve_command_dry_run_plan_needs_no_credentials(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "What are DORA metrics?",
                    "--dry-run",
                    "--top-k",
                    "3",
                    "--candidates",
                    "20",
                    "--doc-kind",
                    "library",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertEqual(payload["top_k"], 3)
        self.assertEqual(payload["candidates"], 20)
        self.assertEqual(payload["doc_kind"], "library")
        self.assertEqual(payload["retrieval"]["rerank_by"], ["RRF"])
        include_attributes = payload["retrieval"]["subqueries"][0]["include_attributes"]
        self.assertNotIn("vector", include_attributes)

    def test_retrieve_command_supports_generic_runtime_overrides_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "How does LinkExtractor filter links?",
                    "--dry-run",
                    "--namespace",
                    "site-scrapling-readthedocs-io-v1",
                    "--region",
                    "gcp-us-central1",
                    "--embedding-model",
                    "BAAI/bge-small-en-v1.5",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertEqual(payload["namespace"], "site-scrapling-readthedocs-io-v1")
        self.assertEqual(payload["region"], "gcp-us-central1")
        self.assertEqual(payload["embedding_model"], "BAAI/bge-small-en-v1.5")

    def test_retrieve_live_with_generic_overrides_is_gated_by_api_key(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict("os.environ", {}, clear=True):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "retrieve",
                        "How does LinkExtractor filter links?",
                        "--live",
                        "--namespace",
                        "site-scrapling-readthedocs-io-v1",
                        "--json",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("TURBOPUFFER_API_KEY must be set", stderr.getvalue())

    def test_evals_command_dry_run_lists_cases_without_credentials(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(["evals", "--dry-run", "--top-k", "3", "--candidates", "30", "--json"])

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertGreaterEqual(payload["total"], 5)
        self.assertEqual(payload["top_k"], 3)
        self.assertEqual(payload["candidates"], 30)
        first_case = payload["cases"][0]
        self.assertIn("question", first_case)
        self.assertIn("expected_urls", first_case)
        self.assertEqual(first_case["status"], "not_run")
        self.assertEqual(first_case["top_hits"], [])

    def test_evals_command_supports_scrapling_dataset_and_generic_runtime_overrides(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "evals",
                    "--dry-run",
                    "--dataset",
                    "src/turbo_search/data/scrapling_retrieval_smoke_evals.json",
                    "--namespace",
                    "site-scrapling-readthedocs-io-v1",
                    "--region",
                    "gcp-us-central1",
                    "--embedding-model",
                    "BAAI/bge-small-en-v1.5",
                    "--top-k",
                    "4",
                    "--candidates",
                    "40",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertEqual(payload["namespace"], "site-scrapling-readthedocs-io-v1")
        self.assertEqual(payload["region"], "gcp-us-central1")
        self.assertEqual(payload["embedding_model"], "BAAI/bge-small-en-v1.5")
        self.assertEqual(payload["top_k"], 4)
        self.assertEqual(payload["candidates"], 40)
        self.assertGreaterEqual(payload["total"], 4)
        self.assertIn("LinkExtractor", payload["cases"][1]["expected_topics"])

    def test_evals_live_with_generic_overrides_is_gated_by_api_key(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict("os.environ", {}, clear=True):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "evals",
                        "--live",
                        "--dataset",
                        "src/turbo_search/data/scrapling_retrieval_smoke_evals.json",
                        "--namespace",
                        "site-scrapling-readthedocs-io-v1",
                        "--json",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("TURBOPUFFER_API_KEY must be set", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
