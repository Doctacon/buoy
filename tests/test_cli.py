from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import hashlib
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from buoy_search.applied_state import AppliedStateRow, applied_state_paths, build_applied_state, save_applied_state
from buoy_search.cli import OneLineProgress, build_parser, main, print_eval_text, print_retrieval_text
from buoy_search.crawler import CrawlExecution, CrawlOptions, parse_github_repo_url
from buoy_search.chunker import process_corpus
from buoy_search.github_repo import GitHubRepoAcquisition, GitHubRepoMetadata
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts


def file_snapshot(path: Path) -> tuple[int, int, int, int, bytes]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, path.read_bytes()


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


class TtyStringIO(StringIO):
    def isatty(self) -> bool:
        return True


def write_fake_github_page(pages_dir: Path) -> None:
    pages_dir.mkdir(parents=True, exist_ok=True)
    (pages_dir / "repo-page.md").write_text(
        "\n".join(
            [
                "---",
                'url: "https://github.com/Doctacon/open-streaming-lab/blob/main/README.md"',
                'title: "README.md"',
                'status: "200"',
                'content_type: "text/plain; charset=utf-8"',
                'source_kind: "github_repo"',
                'repo_full_name: "Doctacon/open-streaming-lab"',
                'repo_owner: "Doctacon"',
                'repo_name: "open-streaming-lab"',
                'repo_ref: "main"',
                'commit_sha: "abc123"',
                'repo_path: "README.md"',
                'language: "markdown"',
                'source_hash: "source-hash"',
                'crawl_timestamp: "2026-06-25T00:00:00+00:00"',
                'fetcher: "git-shallow-clone"',
                "---",
                "",
                "# Open Streaming Lab",
                "",
                "Useful repository documentation for retrieval.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def fake_github_crawl_summary(source, options: CrawlOptions) -> dict[str, object]:  # noqa: ANN001 - parser source union.
    return {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "source_kind": "github_repo",
        "base_url": source.repo_root_url,
        "repo_root_url": source.repo_root_url,
        "repo_owner": source.owner,
        "repo_name": source.repo,
        "repo_full_name": source.repo_full_name,
        "repo_ref": "main",
        "requested_ref": source.requested_ref,
        "repo_subdir": source.repo_subdir,
        "commit_sha": "abc123",
        "clone_url": source.clone_url,
        "acquisition_strategy": "git-shallow-clone",
        "repo_size_kb": 1,
        "primary_language": "TypeScript",
        "allowed_host": "github.com",
        "namespace_candidate": source.namespace_candidate,
        "crawl_strategy": "git-shallow-clone",
        "requested_crawl_strategy": options.crawl_strategy,
        "sitemap_seed_urls": [],
        "out_dir": str(options.out_dir),
        "pages_dir": str(options.out_dir / "pages"),
        "max_pages": options.max_pages,
        "max_chunks": options.max_chunks,
        "repo_max_file_bytes": options.repo_max_file_bytes,
        "repo_chunking_arm": options.repo_chunking_arm,
        "repo_search_metadata": options.repo_search_metadata,
        "repo_file_cards": options.repo_file_cards,
        "repo_oversize_file_cards": options.repo_oversize_file_cards,
        "file_card_pages_generated": 1 if options.repo_file_cards else 0,
        "include_paths": list(options.include_paths),
        "exclude_paths": list(options.exclude_paths),
        "strip_trailing_slash": options.strip_trailing_slash,
        "css_selector": options.css_selector,
        "target_tokens": options.target_tokens,
        "overlap_sentences": options.overlap_sentences,
        "pages_scraped": 1,
        "files_discovered": 1,
        "files_selected": 1,
        "files_skipped_binary": 0,
        "files_skipped_empty": 0,
        "files_skipped_oversize": 0,
        "files_skipped_filtered": 0,
        "files_skipped_limit": 0,
        "requests_count": 0,
        "robots_disallowed_count": 0,
        "blocked_requests_count": 0,
        "failed_requests_count": 0,
        "files_seen": 1,
        "files_error": 0,
        "chunks_generated": 1,
        "limit_reached": False,
        "sample_chunks": [],
        "errors": [],
    }


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
        "docs_version_policy": options.docs_version_policy,
        "docs_version_report": {"detected": False, "policy": options.docs_version_policy},
        "language_policy": options.language_policy,
        "language_report": {"detected": False, "policy": options.language_policy},
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
    def test_live_retrieval_and_eval_text_expose_embedding_precision(self) -> None:
        class Output:
            def __init__(self, payload: dict[str, object]) -> None:
                self.payload = payload

            def to_dict(self) -> dict[str, object]:
                return self.payload

        stdout = StringIO()
        with redirect_stdout(stdout):
            print_retrieval_text(Output({"dry_run": False, "hits": [], "fusion": "server_rrf", "ranking_mode": "page", "ranking_profile": "none", "ranking_aggregation": "max", "embedding_precision": "float16"}))
            for dry_run in (True, False):
                print_eval_text({"dry_run": dry_run, "namespace": "site-example-v1", "region": "gcp-us-central1", "embedding_precision": "float16", "total": 0, "top_k": 5, "candidates": 50, "ranking_mode": "page", "ranking_profile": "none", "ranking_aggregation": "max", "passed": 0, "pass_rate": 0.0, "cases": []})

        self.assertEqual(stdout.getvalue().count("embedding_precision: float16"), 3)

    def test_retrieval_text_prints_tags_only_when_non_empty_in_stored_order(self) -> None:
        class Output:
            def to_dict(self) -> dict[str, object]:
                return {
                    "dry_run": False,
                    "fusion": "server_rrf",
                    "ranking_mode": "page",
                    "ranking_profile": "none",
                    "ranking_aggregation": "max",
                    "embedding_precision": "float32",
                    "hits": [
                        {
                            "id": "tagged",
                            "title": "Tagged",
                            "tags": ["library", "guide"],
                            "score_info": {},
                        },
                        {
                            "id": "empty",
                            "title": "Empty",
                            "tags": [],
                            "score_info": {},
                        },
                    ],
                }

        stdout = StringIO()
        with redirect_stdout(stdout):
            print_retrieval_text(Output())  # type: ignore[arg-type]

        self.assertIn("Tags: library, guide", stdout.getvalue())
        self.assertEqual(stdout.getvalue().count("Tags:"), 1)

    def test_help_identifies_primary_buoy_cli(self) -> None:
        parser = build_parser()

        self.assertEqual(parser.prog, "buoy")
        self.assertTrue(parser.format_help().startswith("usage: buoy"))

    def test_removed_embedding_environment_returns_two_with_clean_json_stdout(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, {"TURBO_SEARCH_EMBEDDING_MODEL": "removed/model"}, clear=True), redirect_stdout(
            stdout
        ), redirect_stderr(stderr):
            result = main(
                ["retrieve", "How does this work?", "--dry-run", "--namespace", "site-example-v1", "--json"]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "Removed environment variable is not supported in Buoy 0.4.0: "
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL\n",
        )

    def test_removed_embedding_environment_rejects_matching_current_value(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(
            os.environ,
            {"BUOY_EMBEDDING_MODEL": "same/model", "TURBO_SEARCH_EMBEDDING_MODEL": "same/model"},
            clear=True,
        ), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                ["retrieve", "How does this work?", "--dry-run", "--namespace", "site-example-v1", "--json"]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(
            stderr.getvalue(),
            "Removed environment variable is not supported in Buoy 0.4.0: "
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL\n",
        )

    def test_dual_implicit_state_roots_fail_before_plan_crawl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / ".buoy"
            legacy = root / ".turbo-search"
            current.mkdir()
            legacy.mkdir()
            stdout = StringIO()
            stderr = StringIO()
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ), patch("buoy_search.cli.crawl_source") as crawl_mock, redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(["plan", "https://example.com/", "--json"])

            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("both implicit state roots exist", stderr.getvalue())
            self.assertIn("--state-root", stderr.getvalue())
            crawl_mock.assert_not_called()

    def test_explicit_state_root_bypasses_dual_roots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / ".buoy"
            legacy = root / ".turbo-search"
            explicit = root / "chosen-state"
            out_dir = root / "plan"
            current.mkdir()
            legacy.mkdir()

            def fake_crawl(_source, options):  # noqa: ANN001 - parser source union.
                write_fake_crawl_page(options.out_dir / "pages")
                return fake_plan_crawl_summary(options)

            stdout = StringIO()
            stderr = StringIO()
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ), patch("buoy_search.cli.crawl_source", side_effect=fake_crawl), redirect_stdout(stdout), redirect_stderr(
                stderr
            ):
                result = main(
                    [
                        "plan",
                        "https://example.com/",
                        "--out-dir",
                        str(out_dir),
                        "--state-root",
                        str(explicit),
                        "--json",
                    ]
                )

            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stdout.getvalue())["state_path"], str(explicit / "state/example-com/site-example-com-v1/state.duckdb"))
            self.assertNotIn("legacy state root", stderr.getvalue())
            self.assertFalse((current / "state").exists())
            self.assertFalse((legacy / "state").exists())

    def test_help_mentions_current_safe_workflow_commands(self) -> None:
        parser = build_parser()
        help_text = parser.format_help()
        retrieve_help = parser._subparsers._group_actions[0].choices["retrieve"].format_help()
        apply_help = parser._subparsers._group_actions[0].choices["apply"].format_help()

        self.assertIn("local-only", help_text)
        self.assertNotIn("index", help_text)
        self.assertIn("crawl", help_text)
        self.assertIn("plan", help_text)
        self.assertIn("apply", help_text)
        self.assertIn("retrieve", help_text)
        self.assertIn("evals", help_text)
        self.assertIn("live automatic or explicit namespace routing", " ".join(help_text.split()))
        normalized_retrieve_help = " ".join(retrieve_help.split())
        self.assertIn("Compatibility no-op; retrieval is live by default", normalized_retrieve_help)
        self.assertIn("explicit --namespace remains local and credential-free", normalized_retrieve_help)
        self.assertIn("TURBOPUFFER_NAMESPACE is ignored", retrieve_help)
        self.assertNotIn("--catalog", retrieve_help)
        normalized_apply_help = " ".join(apply_help.split())
        self.assertIn("Plain interactive apply displays the complete local preflight", normalized_apply_help)
        self.assertIn("--dry-run", apply_help)
        self.assertIn("prompt-free automation", normalized_apply_help)

    def test_one_line_progress_reuses_current_terminal_line(self) -> None:
        stream = TtyStringIO()
        progress = OneLineProgress(enabled=True, stream=stream, min_interval=0.0)

        progress.update("crawl: pages=1")
        progress.update("crawl: pages=2")
        progress.finish()

        output = stream.getvalue()
        self.assertIn("\rcrawl: pages=1", output.replace("\x1b[K", ""))
        self.assertIn("\rcrawl: pages=2", output.replace("\x1b[K", ""))
        self.assertNotIn("\n", output)
        self.assertTrue(output.endswith("\r\x1b[K"))

    def test_one_line_progress_truncates_to_prevent_terminal_wrap(self) -> None:
        stream = TtyStringIO()
        progress = OneLineProgress(enabled=True, stream=stream, min_interval=0.0, terminal_width=20)

        progress.update("crawl sitemap: https://example.com/really/long/url")

        rendered = stream.getvalue().replace("\r\x1b[K", "")
        self.assertLessEqual(len(rendered), 19)
        self.assertEqual(rendered, "crawl sitemap: h...")

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
                "crawl_strategy": "sitemap",
                "requested_crawl_strategy": "sitemap",
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
            with patch("buoy_search.cli.crawl_site", return_value=fake_summary) as crawl_mock:
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
        self.assertEqual(options.crawl_strategy, "sitemap")
        self.assertEqual(options.language_policy, "english")
        self.assertEqual(options.include_paths, ())
        self.assertEqual(options.exclude_paths, ())
        self.assertTrue(options.strip_trailing_slash)
        self.assertEqual(options.css_selector, ".md-content__inner")
        self.assertIsNone(options.progress_callback)

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
                "crawl_strategy": "sitemap",
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
            with patch("buoy_search.cli.crawl_site", return_value=fake_summary):
                with redirect_stdout(stdout):
                    result = main(["crawl", "--base-url", "https://example.com/", "--max-pages", "3", "--max-chunks", "5"])

        output = stdout.getvalue()
        self.assertEqual(result, 0)
        self.assertIn("caps: max_pages=3; max_chunks=5; chunk_limit_reached=True", output)
        self.assertIn("warning: reached page cap, chunk cap", output)

    def test_crawl_command_defaults_to_sitemap_strategy(self) -> None:
        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            self.assertEqual(options.crawl_strategy, "sitemap")
            self.assertEqual(options.docs_version_policy, "warn")
            self.assertEqual(options.language_policy, "english")
            self.assertEqual(options.max_pages, 3000)
            self.assertEqual(options.max_chunks, 120000)
            return fake_plan_crawl_summary(options)

        stdout = StringIO()
        with patch("buoy_search.cli.crawl_site", side_effect=fake_crawl):
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
        self.assertEqual(payload["crawl_strategy"], "sitemap")

    def test_crawl_command_routes_github_repo_urls_to_repo_crawler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "github-crawl"

            def fake_github_crawl(source, options: CrawlOptions) -> dict[str, object]:  # noqa: ANN001
                self.assertEqual(options.max_pages, 5000)
                self.assertEqual(options.max_chunks, 100000)
                self.assertFalse(options.repo_file_cards)
                self.assertFalse(options.repo_oversize_file_cards)
                write_fake_github_page(options.out_dir / "pages")
                return fake_github_crawl_summary(source, options)

            stdout = StringIO()
            with patch("buoy_search.cli.crawl_github_repo", side_effect=fake_github_crawl) as github_mock:
                with patch("buoy_search.cli.crawl_site") as site_mock:
                    with redirect_stdout(stdout):
                        result = main(
                            [
                                "crawl",
                                "--base-url",
                                "https://github.com/Doctacon/open-streaming-lab",
                                "--out-dir",
                                str(out_dir),
                                "--json",
                            ]
                        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["source_kind"], "github_repo")
        self.assertEqual(payload["namespace_candidate"], "github-doctacon-open-streaming-lab-v1")
        github_mock.assert_called_once()
        site_mock.assert_not_called()

    def test_crawl_command_propagates_opt_in_repo_chunking_arm(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "github-crawl"

            def fake_github_crawl(source, options: CrawlOptions) -> dict[str, object]:  # noqa: ANN001
                self.assertEqual(options.repo_chunking_arm, "python-ast")
                self.assertFalse(options.repo_search_metadata)
                self.assertFalse(options.repo_file_cards)
                self.assertFalse(options.repo_oversize_file_cards)
                return fake_github_crawl_summary(source, options)

            stdout = StringIO()
            with patch("buoy_search.cli.crawl_github_repo", side_effect=fake_github_crawl):
                with redirect_stdout(stdout):
                    result = main(
                        [
                            "crawl",
                            "--base-url",
                            "https://github.com/Doctacon/open-streaming-lab",
                            "--out-dir",
                            str(out_dir),
                            "--repo-chunking-arm",
                            "python-ast",
                            "--json",
                        ]
                    )

        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["repo_chunking_arm"], "python-ast")

    def test_repo_chunking_arm_rejects_non_repository_source_before_crawl(self) -> None:
        stderr = StringIO()
        with patch("buoy_search.cli.crawl_site") as crawl_mock:
            with redirect_stderr(stderr):
                result = main(
                    [
                        "crawl",
                        "--base-url",
                        "https://example.com/docs/",
                        "--repo-chunking-arm",
                        "python-ast",
                    ]
                )
        self.assertEqual(result, 2)
        self.assertIn("only for GitHub repositories", stderr.getvalue())
        crawl_mock.assert_not_called()

    def test_crawl_command_accepts_local_pdf_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "Local Handbook.pdf"
            pdf_bytes = b"%PDF-1.4 local handbook bytes"
            pdf_path.write_bytes(pdf_bytes)
            sha16 = hashlib.sha256(pdf_bytes).hexdigest()[:16]
            out_dir = root / "pdf-crawl"

            stdout = StringIO()
            with patch(
                "buoy_search.crawler.markitdown_pdf_to_markdown",
                return_value="# Local Handbook\n\nUseful PDF content for retrieval.",
            ):
                with patch("buoy_search.cli.crawl_site") as site_mock:
                    with redirect_stdout(stdout):
                        result = main(
                            [
                                "crawl",
                                "--base-url",
                                str(pdf_path),
                                "--out-dir",
                                str(out_dir),
                                "--json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["source_kind"], "pdf")
            self.assertEqual(payload["base_url"], f"pdf://pdf-local-handbook-{sha16}")
            self.assertEqual(payload["namespace_candidate"], f"pdf-local-handbook-{sha16}-v1")
            self.assertEqual(payload["pdf_filename"], "Local Handbook.pdf")
            self.assertEqual(payload["file_filename"], "Local Handbook.pdf")
            self.assertEqual(payload["file_extension"], "pdf")
            self.assertEqual(payload["documents_converted"], 1)
            self.assertEqual(payload["pages_scraped"], 1)
            self.assertEqual(payload["chunks_generated"], 1)
            self.assertFalse(payload["turbopuffer_api_calls"])
            site_mock.assert_not_called()

    def test_crawl_command_accepts_supported_local_file_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            csv_path = root / "Local Handbook.csv"
            csv_bytes = b"topic,value\nonboarding,ready\n"
            csv_path.write_bytes(csv_bytes)
            sha16 = hashlib.sha256(csv_bytes).hexdigest()[:16]
            out_dir = root / "file-crawl"

            stdout = StringIO()
            with patch(
                "buoy_search.crawler.markitdown_file_to_markdown",
                return_value="| topic | value |\n| --- | --- |\n| onboarding | ready |",
            ):
                with patch("buoy_search.cli.crawl_site") as site_mock:
                    with redirect_stdout(stdout):
                        result = main(
                            [
                                "crawl",
                                "--base-url",
                                str(csv_path),
                                "--out-dir",
                                str(out_dir),
                                "--json",
                            ]
                        )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(result, 0)
            self.assertEqual(payload["source_kind"], "local_file")
            self.assertEqual(payload["base_url"], f"file://file-csv-local-handbook-{sha16}")
            self.assertEqual(payload["namespace_candidate"], f"file-csv-local-handbook-{sha16}-v1")
            self.assertEqual(payload["file_filename"], "Local Handbook.csv")
            self.assertEqual(payload["file_extension"], "csv")
            self.assertEqual(payload["documents_converted"], 1)
            self.assertEqual(payload["pages_scraped"], 1)
            self.assertEqual(payload["chunks_generated"], 1)
            self.assertFalse(payload["turbopuffer_api_calls"])
            site_mock.assert_not_called()

    def test_plan_command_writes_artifacts_and_first_apply_diff_without_credentials(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "plan"
        state_root = root / "state"
        state_paths = applied_state_paths(
            site_id="example-com", namespace="site-example-com-v1", state_root=state_root
        )
        obsolete_paths = (
            state_paths.state_dir / "last-applied.json",
            state_paths.state_dir / "legacy-json" / "last-applied.json",
        )
        for index, obsolete_path in enumerate(obsolete_paths):
            obsolete_path.parent.mkdir(parents=True, exist_ok=True)
            obsolete_path.write_bytes(f"obsolete plan state {index}\x00".encode())
        obsolete_before = {path: file_snapshot(path) for path in obsolete_paths}

        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            write_fake_crawl_page(options.out_dir / "pages")
            return CrawlExecution(summary=fake_plan_crawl_summary(options), indexing_plan=process_corpus(options.out_dir / "pages"))

        stdout = StringIO()
        with patch(__name__ + ".process_corpus", wraps=process_corpus) as process_mock, patch(
            "buoy_search.crawler.crawl_site_with_plan", side_effect=fake_crawl
        ) as crawl_mock:
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
                        "--docs-version-policy",
                        "latest",
                        "--language-policy",
                        "all",
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
        self.assertEqual(payload["crawl_strategy"], "sitemap")
        self.assertEqual(payload["docs_version_policy"], "latest")
        self.assertEqual(payload["language_policy"], "all")
        self.assertEqual(payload["include_paths"], ["/docs/**"])
        self.assertEqual(payload["exclude_paths"], ["/llms-full.txt"])
        self.assertTrue(payload["strip_trailing_slash"])
        self.assertTrue((out_dir / "plan.json").exists())
        self.assertTrue((out_dir / "manifest.json").exists())
        self.assertTrue((out_dir / "chunks.jsonl").exists())
        self.assertTrue((out_dir / "summary.json").exists())
        self.assertEqual(len(list((out_dir / "pages").glob("*.md"))), 1)
        self.assertEqual({path: file_snapshot(path) for path in obsolete_paths}, obsolete_before)
        self.assertFalse(state_paths.database_path.exists())
        plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        chunks = [json.loads(line) for line in (out_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual(plan["diff"]["rows_to_upsert"], 1)
        self.assertEqual(plan["crawl_options"]["crawl_strategy"], "sitemap")
        self.assertEqual(plan["crawl_options"]["docs_version_policy"], "latest")
        self.assertEqual(plan["crawl_options"]["language_policy"], "all")
        self.assertEqual(plan["crawl_options"]["include_paths"], ["/docs/**"])
        self.assertEqual(plan["crawl_options"]["exclude_paths"], ["/llms-full.txt"])
        self.assertTrue(plan["crawl_options"]["strip_trailing_slash"])
        self.assertEqual(plan["state_path"], str(state_root / "state/example-com/site-example-com-v1/state.duckdb"))
        self.assertEqual(len(manifest["pages"]), 1)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(
            set(payload["timing"]),
            {
                "elapsed_seconds",
                "sitemap_policy_seconds",
                "crawl_seconds",
                "corpus_write_seconds",
                "chunking_seconds",
                "diff_seconds",
                "artifact_seconds",
                "publication_seconds",
            },
        )
        crawl_mock.assert_called_once()
        process_mock.assert_called_once()

    def test_plan_command_removes_verified_superseded_same_namespace_plan(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        plans_root = root / "plans"
        old_dir = plans_root / "old"
        old_pages = old_dir / "pages"
        write_fake_crawl_page(old_pages)
        old_artifacts = build_plan_artifacts(
            indexing_plan=process_corpus(old_pages),
            base_url="https://example.com/docs/",
            out_dir=old_dir,
            state_root=root / "state",
        )
        write_plan_artifacts(old_artifacts, old_dir)
        out_dir = plans_root / "new"

        def fake_crawl(options: CrawlOptions) -> dict[str, object]:
            write_fake_crawl_page(options.out_dir / "pages")
            return CrawlExecution(summary=fake_plan_crawl_summary(options), indexing_plan=process_corpus(options.out_dir / "pages"))

        stdout = StringIO()
        with patch("buoy_search.crawler.crawl_site_with_plan", side_effect=fake_crawl):
            with redirect_stdout(stdout):
                result = main(
                    [
                        "plan",
                        "https://example.com/docs/",
                        "--out-dir",
                        str(out_dir),
                        "--state-root",
                        str(root / "state"),
                        "--json",
                    ]
                )

        self.assertEqual(result, 0)
        self.assertFalse(old_dir.exists())
        self.assertTrue((out_dir / "plan.json").exists())

    def test_plan_command_stops_default_docs_version_warning_before_crawl(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        urls = []
        for version in ("1.0.0", "1.1.0", "latest"):
            for page in range(10):
                urls.append(f"https://example.com/docs/{version}/page-{page}/")

        stdout = StringIO()
        stderr = StringIO()
        with patch("buoy_search.crawler.discover_sitemap_page_urls", return_value=urls):
            with patch("buoy_search.crawler.crawl_pages") as crawl_pages_mock:
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(
                        [
                            "plan",
                            "https://example.com/",
                            "--out-dir",
                            str(root / "plan"),
                            "--state-root",
                            str(root / "state"),
                            "--no-progress",
                        ]
                    )

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("detected versioned docs under /docs", stderr.getvalue())
        self.assertIn("--docs-version-policy latest", stderr.getvalue())
        crawl_pages_mock.assert_not_called()

    def test_plan_command_routes_github_repo_urls_to_repo_corpus_and_artifacts(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "github-plan"
        state_root = root / "state"

        def fake_github_crawl(source, options: CrawlOptions) -> dict[str, object]:  # noqa: ANN001
            self.assertEqual(options.max_pages, 5000)
            self.assertEqual(options.max_chunks, 100000)
            self.assertEqual(options.repo_max_file_bytes, 123456)
            self.assertTrue(options.repo_search_metadata)
            self.assertTrue(options.repo_file_cards)
            self.assertTrue(options.repo_oversize_file_cards)
            write_fake_github_page(options.out_dir / "pages")
            return CrawlExecution(summary=fake_github_crawl_summary(source, options), indexing_plan=process_corpus(options.out_dir / "pages"))

        stdout = StringIO()
        with patch(__name__ + ".process_corpus", wraps=process_corpus) as process_mock, patch(
            "buoy_search.github_repo.crawl_github_repo_with_plan", side_effect=fake_github_crawl
        ) as github_mock:
            with patch("buoy_search.crawler.crawl_site_with_plan") as site_mock:
                with redirect_stdout(stdout):
                    result = main(
                        [
                            "plan",
                            "https://github.com/Doctacon/open-streaming-lab",
                            "--out-dir",
                            str(out_dir),
                            "--state-root",
                            str(state_root),
                            "--repo-max-file-bytes",
                            "123456",
                            "--repo-search-metadata",
                            "--repo-file-cards",
                            "--repo-oversize-file-cards",
                            "--json",
                        ]
                    )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["source_kind"], "github_repo")
        self.assertEqual(payload["base_url"], "https://github.com/Doctacon/open-streaming-lab")
        self.assertEqual(payload["namespace"], "github-doctacon-open-streaming-lab-v1")
        self.assertEqual(payload["site_id"], "github-doctacon-open-streaming-lab")
        self.assertEqual(
            payload["state_path"],
            str(state_root / "state/github-doctacon-open-streaming-lab/github-doctacon-open-streaming-lab-v1/state.duckdb"),
        )
        self.assertEqual(payload["files_selected"], 1)
        self.assertTrue((out_dir / "plan.json").exists())
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        chunk = manifest["chunks"][0]
        self.assertEqual(chunk["source_metadata"]["source_kind"], "github_repo")
        self.assertEqual(chunk["source_metadata"]["repo_path"], "README.md")
        plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
        self.assertEqual(plan["crawl_options"]["repo_max_file_bytes"], 123456)
        self.assertNotIn("repo_chunking_arm", plan["crawl_options"])
        self.assertTrue(plan["crawl_options"]["repo_search_metadata"])
        self.assertTrue(plan["crawl_options"]["repo_file_cards"])
        self.assertTrue(plan["crawl_options"]["repo_oversize_file_cards"])
        github_mock.assert_called_once()
        site_mock.assert_not_called()
        process_mock.assert_called_once()

    def test_plan_command_propagates_repo_chunking_arm_into_bounded_artifacts(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        checkout = root / "checkout"
        source_path = checkout / "src/app.py"
        source_path.parent.mkdir(parents=True)
        source_path.write_text(
            "MODULE = 1\nclass App:\n    def run(self):\n        return MODULE",
            encoding="utf-8",
        )
        source = parse_github_repo_url("https://github.com/owner/repo")
        assert source is not None
        acquisition = GitHubRepoAcquisition(
            source=source,
            metadata=GitHubRepoMetadata(
                owner="owner",
                repo="repo",
                repo_full_name="owner/repo",
                repo_root_url=source.repo_root_url,
                clone_url=source.clone_url,
                default_branch="main",
            ),
            checkout_dir=checkout,
            requested_ref=None,
            resolved_ref="main",
            repo_subdir="",
            commit_sha="abc123",
            clone_url=source.clone_url,
        )
        out_dir = root / "plan"

        stdout = StringIO()
        with patch("buoy_search.github_repo.acquire_github_repo", return_value=acquisition), patch(
            "buoy_search.github_repo.list_tracked_files", return_value=["src/app.py"]
        ), redirect_stdout(stdout):
            result = main(
                [
                    "plan",
                    source.repo_root_url,
                    "--out-dir",
                    str(out_dir),
                    "--state-root",
                    str(root / "state"),
                    "--max-pages",
                    "1",
                    "--max-chunks",
                    "10",
                    "--repo-chunking-arm",
                    "python-ast",
                    "--no-progress",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(result, 0)
        self.assertEqual(payload["repo_chunking_arm"], "python-ast")
        self.assertEqual(payload["selected_files"], ["src/app.py"])
        self.assertEqual(payload["repo_header_chunks"], 1)
        self.assertEqual(plan["crawl_options"]["repo_chunking_arm"], "python-ast")
        self.assertEqual(plan["crawl_options"]["max_pages"], 1)
        self.assertEqual(plan["crawl_options"]["max_chunks"], 10)
        self.assertFalse(payload["api_calls_occurred"])
        app_rows = [row for row in manifest["chunks"] if row["source_metadata"]["repo_path"] == "src/app.py"]
        self.assertEqual(app_rows[0]["section_path"], "src/app.py")
        self.assertTrue(all(" > Lines " in row["section_path"] for row in app_rows[1:]))

    def test_plan_command_writes_pdf_artifacts_without_source_path(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "pdf-plan"
        state_root = root / "state"
        pdf_path = root / "Research Notes.pdf"
        pdf_bytes = b"%PDF-1.4 research notes bytes"
        pdf_path.write_bytes(pdf_bytes)
        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
        source_id = f"pdf-research-notes-{pdf_sha256[:16]}"

        stdout = StringIO()
        with patch(
            "buoy_search.crawler.markitdown_pdf_to_markdown",
            return_value="# Research Notes\n\nUseful PDF text for retrieval and planning.",
        ), patch("buoy_search.crawler.process_corpus", wraps=process_corpus) as process_mock:
            with patch("buoy_search.crawler.crawl_site_with_plan") as site_mock:
                with patch("buoy_search.github_repo.crawl_github_repo_with_plan") as github_mock:
                    with redirect_stdout(stdout):
                        result = main(
                            [
                                "plan",
                                str(pdf_path),
                                "--out-dir",
                                str(out_dir),
                                "--state-root",
                                str(state_root),
                                "--json",
                            ]
                        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["source_kind"], "pdf")
        self.assertEqual(payload["base_url"], f"pdf://{source_id}")
        self.assertEqual(payload["namespace"], f"{source_id}-v1")
        self.assertEqual(payload["namespace_candidate"], f"{source_id}-v1")
        self.assertEqual(payload["site_id"], source_id)
        self.assertEqual(payload["pdf_filename"], "Research Notes.pdf")
        self.assertEqual(payload["pdf_sha256"], pdf_sha256)
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertEqual(payload["diff"]["rows_to_upsert"], 1)
        self.assertEqual(payload["state_path"], str(state_root / "state" / source_id / f"{source_id}-v1" / "state.duckdb"))
        self.assertTrue((out_dir / "plan.json").exists())
        self.assertTrue((out_dir / "manifest.json").exists())
        self.assertTrue((out_dir / "chunks.jsonl").exists())
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        chunk = manifest["chunks"][0]
        self.assertEqual(manifest["base_url"], f"pdf://{source_id}")
        self.assertEqual(manifest["pages"][0]["canonical_url"], f"pdf://{source_id}/Research%20Notes.pdf")
        self.assertEqual(chunk["source_metadata"]["source_kind"], "pdf")
        self.assertEqual(chunk["source_metadata"]["pdf_filename"], "Research Notes.pdf")
        self.assertEqual(chunk["source_metadata"]["pdf_sha256"], pdf_sha256)
        serialized_artifacts = "\n".join(
            [
                (out_dir / "plan.json").read_text(encoding="utf-8"),
                (out_dir / "manifest.json").read_text(encoding="utf-8"),
                (out_dir / "chunks.jsonl").read_text(encoding="utf-8"),
                (out_dir / "summary.json").read_text(encoding="utf-8"),
            ]
        )
        self.assertNotIn(str(pdf_path), serialized_artifacts)
        site_mock.assert_not_called()
        github_mock.assert_not_called()
        process_mock.assert_called_once()

    def test_plan_command_writes_local_file_artifacts_without_source_path(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        out_dir = root / "file-plan"
        state_root = root / "state"
        csv_path = root / "Research Notes.csv"
        csv_bytes = b"topic,value\nonboarding,ready\n"
        csv_path.write_bytes(csv_bytes)
        file_sha256 = hashlib.sha256(csv_bytes).hexdigest()
        source_id = f"file-csv-research-notes-{file_sha256[:16]}"

        stdout = StringIO()
        with patch(
            "buoy_search.crawler.markitdown_file_to_markdown",
            return_value="| topic | value |\n| --- | --- |\n| onboarding | ready |",
        ):
            with patch("buoy_search.crawler.crawl_site_with_plan") as site_mock:
                with patch("buoy_search.github_repo.crawl_github_repo_with_plan") as github_mock:
                    with redirect_stdout(stdout):
                        result = main(
                            [
                                "plan",
                                str(csv_path),
                                "--out-dir",
                                str(out_dir),
                                "--state-root",
                                str(state_root),
                                "--json",
                            ]
                        )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["source_kind"], "local_file")
        self.assertEqual(payload["base_url"], f"file://{source_id}")
        self.assertEqual(payload["namespace"], f"{source_id}-v1")
        self.assertEqual(payload["namespace_candidate"], f"{source_id}-v1")
        self.assertEqual(payload["site_id"], source_id)
        self.assertEqual(payload["file_filename"], "Research Notes.csv")
        self.assertEqual(payload["file_extension"], "csv")
        self.assertEqual(payload["file_sha256"], file_sha256)
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertEqual(payload["diff"]["rows_to_upsert"], 1)
        self.assertEqual(payload["state_path"], str(state_root / "state" / source_id / f"{source_id}-v1" / "state.duckdb"))
        self.assertTrue((out_dir / "plan.json").exists())
        self.assertTrue((out_dir / "manifest.json").exists())
        self.assertTrue((out_dir / "chunks.jsonl").exists())
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        chunk = manifest["chunks"][0]
        self.assertEqual(manifest["base_url"], f"file://{source_id}")
        self.assertEqual(manifest["pages"][0]["canonical_url"], f"file://{source_id}/Research%20Notes.csv")
        self.assertEqual(chunk["source_metadata"]["source_kind"], "local_file")
        self.assertEqual(chunk["source_metadata"]["file_filename"], "Research Notes.csv")
        self.assertEqual(chunk["source_metadata"]["file_extension"], "csv")
        self.assertEqual(chunk["source_metadata"]["file_sha256"], file_sha256)
        self.assertNotIn("pdf_filename", chunk["source_metadata"])
        serialized_artifacts = "\n".join(
            [
                (out_dir / "plan.json").read_text(encoding="utf-8"),
                (out_dir / "manifest.json").read_text(encoding="utf-8"),
                (out_dir / "chunks.jsonl").read_text(encoding="utf-8"),
                (out_dir / "summary.json").read_text(encoding="utf-8"),
            ]
        )
        self.assertNotIn(str(csv_path), serialized_artifacts)
        site_mock.assert_not_called()
        github_mock.assert_not_called()

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
            return CrawlExecution(summary=fake_plan_crawl_summary(options), indexing_plan=process_corpus(options.out_dir / "pages"))

        stdout = StringIO()
        with patch("buoy_search.crawler.crawl_site_with_plan", side_effect=fake_crawl):
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
        self.assertIn("source URL/path is required", stderr.getvalue())

    def test_retrieve_command_dry_run_plan_needs_no_credentials(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "What are DORA metrics?",
                    "--dry-run",
                    "--namespace",
                    "site-example-v1",
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
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")
        self.assertEqual(payload["retrieval"]["rerank_by"], ["RRF"])
        include_attributes = payload["retrieval"]["subqueries"][0]["include_attributes"]
        self.assertIn("tags", include_attributes)
        self.assertIn("repo_path", include_attributes)
        self.assertNotIn("vector", include_attributes)

    def test_retrieve_command_uses_repo_defaults_for_github_namespace_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "Where is repo routing implemented?",
                    "--dry-run",
                    "--namespace",
                    "github-doctacon-buoy-search-v1",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["ranking_mode"], "file")
        self.assertEqual(payload["ranking_profile"], "repo_code")
        self.assertEqual(payload["ranking_pool"], 100)
        self.assertEqual(payload["ranking_aggregation"], "adaptive_sum_3")

    def test_retrieve_command_uses_document_defaults_for_pdf_namespace_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "What does the PDF say?",
                    "--dry-run",
                    "--namespace",
                    "pdf-research-notes-abc123-v1",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")

    def test_retrieve_command_uses_document_defaults_for_file_namespace_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "What does the file say?",
                    "--dry-run",
                    "--namespace",
                    "file-csv-research-notes-abc123-v1",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")

    def test_retrieve_command_accepts_page_ranking_mode_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "retrieve",
                    "Where is the query API documented?",
                    "--dry-run",
                    "--namespace",
                    "site-example-v1",
                    "--ranking-mode",
                    "page",
                    "--ranking-profile",
                    "none",
                    "--ranking-pool",
                    "20",
                    "--ranking-aggregation",
                    "capped-sum-3",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "capped_sum_3")
        self.assertFalse(payload["turbopuffer_api_calls"])

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
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")

    def test_plain_and_compatibility_live_explicit_retrieval_require_api_key(self) -> None:
        for extra in ([], ["--live"]):
            stdout = StringIO()
            stderr = StringIO()
            with self.subTest(extra=extra), patch.dict("os.environ", {}, clear=True):
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(
                        [
                            "retrieve",
                            "How does LinkExtractor filter links?",
                            "--namespace",
                            "site-scrapling-readthedocs-io-v1",
                            *extra,
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
        self.assertGreaterEqual(payload["total"], 4)
        self.assertEqual(payload["top_k"], 3)
        self.assertEqual(payload["candidates"], 30)
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")
        first_case = payload["cases"][0]
        self.assertIn("question", first_case)
        self.assertIn("expected_urls", first_case)
        self.assertEqual(first_case["status"], "not_run")
        self.assertEqual(first_case["top_hits"], [])

    def test_evals_command_uses_repo_defaults_for_github_namespace_in_dry_run(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "evals",
                    "--dry-run",
                    "--dataset",
                    "src/buoy_search/data/buoy_search_repo_search_seed_evals.json",
                    "--namespace",
                    "github-doctacon-buoy-search-v1",
                    "--json",
                ]
            )

        payload = json.loads(stdout.getvalue())
        self.assertEqual(result, 0)
        self.assertEqual(payload["ranking_mode"], "file")
        self.assertEqual(payload["ranking_profile"], "repo_code")
        self.assertEqual(payload["ranking_pool"], 100)
        self.assertEqual(payload["ranking_aggregation"], "adaptive_sum_3")

    def test_evals_command_supports_scrapling_dataset_and_generic_runtime_overrides(self) -> None:
        stdout = StringIO()
        with redirect_stdout(stdout):
            result = main(
                [
                    "evals",
                    "--dry-run",
                    "--dataset",
                    "src/buoy_search/data/scrapling_retrieval_smoke_evals.json",
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
        self.assertEqual(payload["ranking_mode"], "page")
        self.assertEqual(payload["ranking_profile"], "none")
        self.assertEqual(payload["ranking_pool"], 20)
        self.assertEqual(payload["ranking_aggregation"], "max")
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
                        "src/buoy_search/data/scrapling_retrieval_smoke_evals.json",
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
