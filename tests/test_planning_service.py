from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.chunker import process_corpus
from buoy_search.cli import main
from buoy_search.crawler import CrawlExecution, CrawlOptions
from buoy_search.database_relation import DatabaseRelationError
from buoy_search.plan_artifacts import verify_plan_artifacts, write_plan_artifacts
from buoy_search.planning_service import (
    MAX_PROGRESS_MESSAGE_LENGTH,
    MAX_PROGRESS_STAGE_LENGTH,
    PlanProgress,
    PlanningRequest,
    PlanningService,
    emit_progress,
)


def write_page(pages_dir: Path) -> None:
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
                'crawl_timestamp: "2026-07-23T00:00:00+00:00"',
                'fetcher: "test"',
                "---",
                "",
                "# Intro",
                "",
                "Shared planning service content.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def crawl_summary(options: CrawlOptions) -> dict[str, object]:
    return {
        "command": "crawl",
        "dry_run": True,
        "credentials_required": False,
        "source_credentials_required": False,
        "source_api_calls_occurred": False,
        "turbopuffer_api_calls": False,
        "api_calls_occurred": False,
        "source_kind": "website",
        "base_url": options.base_url,
        "allowed_host": "example.com",
        "namespace_candidate": "site-example-com-v1",
        "crawl_strategy": options.crawl_strategy,
        "requested_crawl_strategy": options.crawl_strategy,
        "docs_version_policy": options.docs_version_policy,
        "language_policy": options.language_policy,
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
        "files_discovered": 1,
        "files_seen": 1,
        "files_error": 0,
        "chunks_generated": 1,
        "limit_reached": False,
        "sample_chunks": [],
        "errors": [],
    }


class PlanningServiceTests(unittest.TestCase):
    def test_one_source_writes_one_verified_namespace_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "plan"
            events: list[PlanProgress] = []

            def fake_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                write_page(options.out_dir / "pages")
                if options.progress_callback is not None:
                    options.progress_callback("crawl: pages=1; chunks=1")
                return CrawlExecution(
                    summary=crawl_summary(options),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            result = PlanningService(
                crawl_runner=fake_crawl,
                cleanup_runner=lambda *_args, **_kwargs: [],
            ).plan(
                PlanningRequest(
                    source="https://example.com/docs/",
                    out_dir=out_dir,
                    state_root=root / "state",
                    namespace="docs-explicit-v1",
                ),
                progress_callback=events.append,
            )

            self.assertEqual(result.summary["namespace"], "docs-explicit-v1")
            self.assertEqual({path.name for path in out_dir.iterdir()}, {"plan.json", "delta.duckdb"})
            verified = verify_plan_artifacts(out_dir / "plan.json")
            self.assertEqual(verified.plan["namespace"], "docs-explicit-v1")
            self.assertEqual(events[-1].stage, "complete")

    def test_progress_stage_and_message_are_sanitized_and_bounded(self) -> None:
        events: list[PlanProgress] = []
        emit_progress(
            events.append,
            "stage\n" + "s" * MAX_PROGRESS_STAGE_LENGTH,
            "message\t" + "m" * MAX_PROGRESS_MESSAGE_LENGTH,
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(len(events[0].stage), MAX_PROGRESS_STAGE_LENGTH)
        self.assertEqual(len(events[0].message), MAX_PROGRESS_MESSAGE_LENGTH)
        self.assertNotRegex(events[0].stage + events[0].message, r"[\n\t]")

    def test_delta_integrity_failure_prevents_service_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events: list[PlanProgress] = []

            def fake_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                write_page(options.out_dir / "pages")
                return CrawlExecution(
                    summary=crawl_summary(options),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            def corrupt_writer(artifacts, out_dir: Path) -> None:  # noqa: ANN001
                write_plan_artifacts(artifacts, out_dir)
                with duckdb.connect(str(out_dir / "delta.duckdb")) as connection:
                    connection.execute("UPDATE upsert_rows SET content = 'tampered'")

            request = PlanningRequest(
                source="https://example.com/docs/",
                out_dir=root / "plan",
                state_root=root / "state",
            )
            with self.assertRaisesRegex(ValueError, "logical hash does not match"):
                PlanningService(
                    crawl_runner=fake_crawl,
                    artifact_writer=corrupt_writer,
                    cleanup_runner=lambda *_args, **_kwargs: [],
                ).plan(request, progress_callback=events.append)
            self.assertNotIn("complete", [event.stage for event in events])

    def test_unexpected_output_prevents_service_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events: list[PlanProgress] = []

            def fake_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                write_page(options.out_dir / "pages")
                return CrawlExecution(
                    summary=crawl_summary(options),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            def corrupt_writer(artifacts, out_dir: Path) -> None:  # noqa: ANN001
                write_plan_artifacts(artifacts, out_dir)
                (out_dir / "unexpected.txt").write_text("must not persist", encoding="utf-8")

            request = PlanningRequest(
                source="https://example.com/docs/",
                out_dir=root / "plan",
                state_root=root / "state",
            )
            with self.assertRaisesRegex(ValueError, "must contain exactly"):
                PlanningService(
                    crawl_runner=fake_crawl,
                    artifact_writer=corrupt_writer,
                    cleanup_runner=lambda *_args, **_kwargs: [],
                ).plan(request, progress_callback=events.append)
            self.assertNotIn("complete", [event.stage for event in events])

    def test_cli_database_source_is_constructed_once_and_uses_service_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database_path = root / "docs.duckdb"
            database_path.touch()
            source = SimpleNamespace(
                kind="duckdb_relation",
                base_url="duckdb://docs",
                default_out_dir=root / "default-plan",
            )
            stdout = StringIO()
            stderr = StringIO()
            with patch(
                "buoy_search.duckdb_relation.duckdb_relation_source",
                return_value=source,
            ) as constructor, patch(
                "buoy_search.planning_service.crawl_source_with_plan",
                side_effect=DatabaseRelationError("service default dispatch reached"),
            ) as service_dispatch, patch(
                "buoy_search.cli.source_from_cli_args",
                side_effect=AssertionError("CLI source dispatch must not run for plan"),
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(
                    [
                        "plan",
                        str(database_path),
                        "--relation",
                        "docs",
                        "--source-id",
                        "docs",
                        "--state-root",
                        str(root / "state"),
                        "--no-progress",
                    ]
                )

            self.assertEqual(result, 2)
            self.assertEqual(stdout.getvalue(), "")
            self.assertIn("service default dispatch reached", stderr.getvalue())
            constructor.assert_called_once()
            service_dispatch.assert_called_once()

    def test_cli_delegates_typed_options_and_preserves_json_output(self) -> None:
        stdout = StringIO()
        stderr = StringIO()
        service_result = SimpleNamespace(
            summary={"command": "plan", "plan_id": "plan-delegated"},
            cleanup_warnings=(),
        )
        with patch(
            "buoy_search.cli.PlanningService.plan", return_value=service_result
        ) as plan_mock, redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(
                [
                    "plan",
                    "https://example.com/docs/",
                    "--state-root",
                    ".buoy-test",
                    "--max-pages",
                    "9",
                    "--max-chunks",
                    "13",
                    "--namespace",
                    "delegated-v1",
                    "--include-path",
                    "/docs/**",
                    "--json",
                    "--no-progress",
                ]
            )

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertEqual(json.loads(stdout.getvalue())["plan_id"], "plan-delegated")
        delegated = plan_mock.call_args.args[0]
        self.assertIsInstance(delegated, PlanningRequest)
        self.assertEqual(delegated.source, "https://example.com/docs/")
        self.assertEqual((delegated.max_pages, delegated.max_chunks), (9, 13))
        self.assertEqual(delegated.namespace, "delegated-v1")
        self.assertEqual(delegated.include_paths, ("/docs/**",))
        self.assertIsNone(plan_mock.call_args.kwargs["progress_callback"])


if __name__ == "__main__":
    unittest.main()
