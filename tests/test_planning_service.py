from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.apply import ApplyPlanError, load_verified_apply_plan
from buoy_search.chunker import process_corpus
from buoy_search.cli import main
from buoy_search.crawler import CrawlExecution, CrawlOptions
from buoy_search.database_relation import DatabaseRelationError
from buoy_search.plan_artifacts import PLAN_SCHEMA_VERSION, write_plan_artifacts
from buoy_search.planning_service import (
    MAX_MANAGED_SOURCE_URL_LENGTH,
    MAX_PROGRESS_MESSAGE_LENGTH,
    MAX_PROGRESS_STAGE_LENGTH,
    ManagedPublicPlanningRequest,
    PlanProgress,
    PlanningRequest,
    PlanningService,
    emit_progress,
)
import buoy_search.planning_service as planning_service


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
    def test_managed_website_writes_unique_verified_artifacts_with_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "artifacts/command-center/plans/job-1"
            state_root = root / "state"
            calls: list[CrawlOptions] = []
            events: list[PlanProgress] = []

            def fake_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                calls.append(options)
                if options.progress_callback is not None:
                    options.progress_callback("crawl: pages=1; chunks=1")
                write_page(options.out_dir / "pages")
                return CrawlExecution(
                    summary=crawl_summary(options),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            request = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs/",
                out_dir=out_dir,
                state_root=state_root,
                max_pages_or_files=7,
                max_chunks=11,
                namespace="review-docs-v1",
                include_paths=("/docs/**",),
                exclude_paths=("/docs/archive/**",),
                originating_job_id=f"planjob_{'a' * 32}",
            )
            forbidden_adapters = {
                "buoy_search.duckdb_relation",
                "buoy_search.bigquery_relation",
                "buoy_search.snowflake_relation",
                "markitdown",
            }
            before_modules = set(sys.modules)
            environment_get = os.environ.get

            def guarded_environment_get(key: str, default: str | None = None) -> str | None:
                if key == "TURBOPUFFER_API_KEY":
                    raise AssertionError("turbopuffer credentials read")
                return environment_get(key, default)

            with patch.object(os.environ, "get", side_effect=guarded_environment_get), patch(
                "buoy_search.chunker.SentenceTransformerEmbedder",
                side_effect=AssertionError("embedding model loaded"),
            ) as embedder:
                result = PlanningService(crawl_runner=fake_crawl).plan(
                    request, progress_callback=events.append
                )

            self.assertEqual(result.source_kind, "website")
            self.assertEqual(result.summary["namespace"], "review-docs-v1")
            self.assertFalse(result.summary["turbopuffer_credentials_required"])
            self.assertFalse(result.summary["turbopuffer_api_calls"])
            self.assertEqual(result.summary["originating_job_id"], f"planjob_{'a' * 32}")
            self.assertEqual((calls[0].max_pages, calls[0].max_chunks), (7, 11))
            self.assertEqual(calls[0].include_paths, ("/docs/**",))
            self.assertEqual(calls[0].exclude_paths, ("/docs/archive/**",))
            self.assertEqual(events[1].counts, {"pages": 1, "chunks": 1})
            self.assertEqual(events[-1].stage, "complete")
            self.assertTrue(all(len(event.stage) <= 64 and len(event.message) <= 500 for event in events))
            self.assertEqual(
                {"plan.json", "manifest.json", "chunks.jsonl", "summary.json", "pages"},
                {path.name for path in out_dir.iterdir()},
            )
            plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
            persisted_summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["schema_version"], PLAN_SCHEMA_VERSION)
            self.assertNotIn("originating_job_id", plan)
            self.assertEqual(persisted_summary["originating_job_id"], f"planjob_{'a' * 32}")
            verified = load_verified_apply_plan(
                plan_path=out_dir / "plan.json", namespace=None, state_root=state_root
            )
            self.assertEqual(verified.plan["plan_id"], result.summary["plan_id"])
            self.assertFalse((state_root / "state").exists())
            embedder.assert_not_called()
            self.assertFalse(forbidden_adapters & (set(sys.modules) - before_modules))
            self.assertNotIn("subprocess", inspect.getsource(planning_service))

            with self.assertRaisesRegex(ValueError, "output directory already exists"):
                PlanningService(crawl_runner=fake_crawl).plan(request)
            self.assertEqual(len(calls), 1)

    def test_private_staged_managed_plan_persists_only_logical_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            out_dir = root / "artifacts/command-center/plans/job-1"
            out_dir.mkdir(parents=True)
            descriptor = os.open(
                out_dir,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            write_dirs: list[Path] = []

            def fake_crawl(_source: object, options: CrawlOptions) -> CrawlExecution:
                write_dirs.append(options.out_dir)
                write_page(options.out_dir / "pages")
                return CrawlExecution(
                    summary=crawl_summary(options),
                    indexing_plan=process_corpus(options.out_dir / "pages"),
                )

            request = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs/",
                out_dir=out_dir,
                state_root=root / "state",
                precreated_output_identity=(
                    os.fstat(descriptor).st_dev,
                    os.fstat(descriptor).st_ino,
                ),
                precreated_output_ancestor_identities=tuple(
                    (ancestor.stat().st_dev, ancestor.stat().st_ino)
                    for ancestor in (root / "artifacts", root / "artifacts/command-center", out_dir.parent)
                ),
                precreated_output_descriptor=descriptor,
            )
            try:
                result = PlanningService(crawl_runner=fake_crawl).plan(request)
            finally:
                os.close(descriptor)

            self.assertEqual(len(write_dirs), 1)
            self.assertNotEqual(write_dirs[0], out_dir)
            self.assertIn("buoy-managed-plan-", write_dirs[0].name)
            self.assertFalse(write_dirs[0].exists())
            plan = json.loads((out_dir / "plan.json").read_text(encoding="utf-8"))
            summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["manifest_path"], str(out_dir / "manifest.json"))
            self.assertEqual(plan["chunks_path"], str(out_dir / "chunks.jsonl"))
            self.assertEqual(plan["pages_dir"], str(out_dir / "pages"))
            self.assertEqual(summary["out_dir"], str(out_dir))
            self.assertEqual(result.out_dir, out_dir)
            persisted = "\n".join(
                path.read_text(encoding="utf-8")
                for path in out_dir.rglob("*")
                if path.is_file()
            )
            self.assertNotIn("buoy-managed-plan-", persisted)
            self.assertNotIn("/dev/fd/", persisted)
            self.assertNotIn("/proc/", persisted)

    def test_managed_github_request_uses_current_defaults_and_rejects_advanced_forms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            request = ManagedPublicPlanningRequest(
                source_url="https://github.com/Doctacon/buoy",
                out_dir=root / "job",
                state_root=root / "state",
            ).to_planning_request()

            self.assertEqual(request.source, "https://github.com/Doctacon/buoy")
            self.assertIsNone(request.max_pages)
            self.assertIsNone(request.max_chunks)
            self.assertTrue(request.require_new_output)
            self.assertFalse(request.cleanup_superseded)
            self.assertIsNone(request.originating_job_id)
            with self.assertRaisesRegex(ValueError, "safe managed plan-job ID"):
                ManagedPublicPlanningRequest(
                    source_url="https://example.com/docs",
                    out_dir=root / "unsafe-origin",
                    state_root=root / "state",
                    originating_job_id="../../../job",
                ).to_planning_request()
            website_with_query_and_fragment = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs?language=en#install",
                out_dir=root / "website",
                state_root=root / "state",
            ).to_planning_request()
            self.assertEqual(
                website_with_query_and_fragment.source,
                "https://example.com/docs?language=en",
            )
            exact_length_url = "https://example.com/" + "x" * (
                MAX_MANAGED_SOURCE_URL_LENGTH - len("https://example.com/")
            )
            self.assertEqual(
                ManagedPublicPlanningRequest(
                    source_url=exact_length_url,
                    out_dir=root / "exact",
                    state_root=root / "state",
                ).to_planning_request().source,
                exact_length_url,
            )
            for valid_authority in (
                "https://bücher.example/docs",
                "https://127.0.0.1:1/docs",
                "https://[::1]:65535/docs",
            ):
                with self.subTest(valid_authority=valid_authority):
                    self.assertEqual(
                        ManagedPublicPlanningRequest(
                            source_url=valid_authority,
                            out_dir=root / "valid-authority",
                            state_root=root / "state",
                        ).to_planning_request().source,
                        valid_authority,
                    )
            for source_url in (
                "https://github.com/Doctacon/buoy/tree/main/src",
                "https://github.com/Doctacon/buoy/blob/main/README.md",
                "https://user@example.com/docs",
                "file:///tmp/document.pdf",
                "https://example.com:bad/docs",
                "https://example.com:99999/docs",
                "https://example.com:0/docs",
                "https://example.com:/docs",
                "https://:443/docs",
                "https://exa mple.com/docs",
                " https://example.com/docs",
                "https://example.com/docs\t",
                "https://-invalid.example/docs",
                "https://example..com/docs",
                "https://999.999.999.999/docs",
                "https://[v1.fe]/docs",
                exact_length_url + "x",
            ):
                with self.subTest(source_url=source_url[:80]):
                    with self.assertRaises(ValueError):
                        ManagedPublicPlanningRequest(
                            source_url=source_url,
                            out_dir=root / "other",
                            state_root=root / "state",
                        ).to_planning_request()

    def test_managed_output_rejects_dangling_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "job"
            out_dir.symlink_to(root / "missing", target_is_directory=True)
            request = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs/",
                out_dir=out_dir,
                state_root=root / "state",
            )

            with self.assertRaisesRegex(ValueError, "output directory already exists"):
                PlanningService(
                    crawl_runner=lambda _source, _options: self.fail("crawl must not run")
                ).plan(request)

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

    def test_chunks_integrity_failure_prevents_service_success(self) -> None:
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
                (out_dir / "chunks.jsonl").write_text("{}\n", encoding="utf-8")

            request = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs/",
                out_dir=root / "job",
                state_root=root / "state",
            )
            with self.assertRaisesRegex(ApplyPlanError, "chunks.jsonl does not match"):
                PlanningService(
                    crawl_runner=fake_crawl, artifact_writer=corrupt_writer
                ).plan(request, progress_callback=events.append)
            self.assertNotIn("complete", [event.stage for event in events])

    def test_page_content_corruption_prevents_service_success(self) -> None:
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
                page_path = out_dir / "pages/page.md"
                page_path.write_text(
                    page_path.read_text(encoding="utf-8") + "CORRUPTED AFTER MANIFEST BUILD\n",
                    encoding="utf-8",
                )

            request = ManagedPublicPlanningRequest(
                source_url="https://example.com/docs/",
                out_dir=root / "job",
                state_root=root / "state",
            )
            with self.assertRaisesRegex(ValueError, "page artifact content hash does not match"):
                PlanningService(
                    crawl_runner=fake_crawl, artifact_writer=corrupt_writer
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
