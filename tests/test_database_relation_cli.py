from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.apply import load_verified_apply_plan
from buoy_search.bigquery_relation import BigQueryRelationError, BigQueryRelationSource
from buoy_search.catalog import GeneratedSemantics
from buoy_search.cli import build_parser, main, source_from_cli_args
from buoy_search.database_relation import DatabaseDocument, DatabaseScanResult
from buoy_search.duckdb_relation import DuckDBRelationSource
from buoy_search.snowflake_relation import SnowflakeRelationError, SnowflakeRelationSource


class DatabaseRelationCliTests(unittest.TestCase):
    def run_cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_importing_cli_for_apply_does_not_import_database_adapters(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import buoy_search.cli; "
                "assert not ({'buoy_search.duckdb_relation', 'buoy_search.bigquery_relation', "
                "'buoy_search.snowflake_relation'} & set(sys.modules))",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)

    def test_plan_constructs_bigquery_source_without_local_path(self) -> None:
        args = build_parser().parse_args(
            [
                "plan",
                "--database-backend",
                "bigquery",
                "--relation",
                "source-project.corpus.documents",
                "--source-id",
                "product-docs",
                "--bigquery-project",
                "billing-project",
                "--bigquery-location",
                "US",
                "--bigquery-maximum-bytes-billed",
                "1000",
                "--source-query-timeout",
                "12.5",
            ]
        )
        source = source_from_cli_args(args, None)
        self.assertIsInstance(source, BigQueryRelationSource)
        self.assertEqual(source.relation, "source-project.corpus.documents")
        self.assertEqual(source.query_project, "billing-project")
        self.assertEqual(source.location, "US")
        self.assertEqual(source.maximum_bytes_billed, 1000)
        self.assertEqual(source.query_timeout, 12.5)
        self.assertEqual(source.operation, "plan")

    def test_crawl_constructs_snowflake_source_without_base_url(self) -> None:
        args = build_parser().parse_args(
            [
                "crawl",
                "--database-backend",
                "snowflake",
                "--relation",
                "analytics.corpus.documents",
                "--source-id",
                "product-docs",
                "--snowflake-connection",
                "analytics",
                "--source-query-timeout",
                "30",
            ]
        )
        source = source_from_cli_args(args, args.base_url)
        self.assertIsInstance(source, SnowflakeRelationSource)
        self.assertEqual(source.relation, "ANALYTICS.CORPUS.DOCUMENTS")
        self.assertEqual(source.operation, "crawl")
        self.assertEqual(source.query_timeout, 30)

    def test_implicit_and_explicit_duckdb_remain_compatible(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            database = Path(tmp) / "docs.duckdb"
            database.touch()
            parser = build_parser()
            implicit = parser.parse_args(
                ["plan", str(database), "--relation", "docs", "--source-id", "docs"]
            )
            explicit = parser.parse_args(
                [
                    "plan",
                    str(database),
                    "--database-backend",
                    "duckdb",
                    "--relation",
                    "docs",
                    "--source-id",
                    "docs",
                ]
            )
            implicit_source = source_from_cli_args(implicit, str(database))
            explicit_source = source_from_cli_args(explicit, str(database))
            self.assertIsInstance(implicit_source, DuckDBRelationSource)
            self.assertEqual(implicit_source, explicit_source)

    def test_bigquery_plan_writes_source_independent_artifacts_and_truthful_summary(self) -> None:
        scan = DatabaseScanResult(
            documents=[DatabaseDocument("call/1", "Transcript body.", "Call one")],
            rows_discovered=1,
            documents_skipped_empty=0,
            documents_skipped_limit=0,
            title_column="title",
            diagnostics={"bigquery_query_job_id": "volatile-job"},
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "plan"
            with patch(
                "buoy_search.bigquery_relation.scan_bigquery_relation", return_value=scan
            ):
                result, stdout, stderr = self.run_cli(
                    [
                        "plan",
                        "--database-backend",
                        "bigquery",
                        "--relation",
                        "source-project.corpus.documents",
                        "--source-id",
                        "docs",
                        "--bigquery-project",
                        "billing-project",
                        "--bigquery-location",
                        "US",
                        "--namespace",
                        "customer-conversations",
                        "--out-dir",
                        str(out),
                        "--state-root",
                        str(root / "state"),
                        "--no-progress",
                        "--json",
                    ]
                )
            self.assertEqual(result, 0, stderr)
            import json

            summary = json.loads(stdout)
            self.assertTrue(summary["credentials_required"])
            self.assertTrue(summary["api_calls_occurred"])
            self.assertTrue(summary["source_credentials_required"])
            self.assertTrue(summary["source_api_calls_occurred"])
            self.assertFalse(summary["turbopuffer_credentials_required"])
            self.assertFalse(summary["turbopuffer_api_calls"])
            self.assertEqual(summary["catalog_registration"]["source_kind"], "database")
            self.assertEqual(summary["catalog_registration"]["ranking_mode"], "page")
            self.assertEqual(summary["catalog_registration"]["ranking_profile"], "none")
            self.assertEqual(summary["catalog_registration"]["ranking_pool"], 20)
            self.assertEqual(summary["catalog_registration"]["ranking_aggregation"], "max")
            plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
            serialized = "\n".join(
                path.read_text(encoding="utf-8")
                for path in (out / "plan.json", out / "manifest.json", out / "chunks.jsonl")
            )
            self.assertEqual(plan["crawl_options"]["source_kind"], "bigquery_relation")
            self.assertEqual(plan["crawl_options"]["database_backend"], "bigquery")
            self.assertNotIn("billing-project", serialized)
            self.assertNotIn("volatile-job", serialized)
            semantics = GeneratedSemantics(
                source_kind="database",
                source_uri="bigquery://docs",
                title="docs",
                summary="BigQuery documents.",
                aliases=[],
                tags=["database", "bigquery"],
            )
            with (
                patch("buoy_search.bigquery_relation._load_bigquery", side_effect=AssertionError("source access")),
                patch("buoy_search.snowflake_relation._load_connector", side_effect=AssertionError("source access")),
                patch("buoy_search.apply.generated_semantics", return_value=semantics),
            ):
                verified = load_verified_apply_plan(
                    plan_path=out / "plan.json",
                    namespace=None,
                    state_root=root / "state",
                )
                apply_result, apply_stdout, apply_stderr = self.run_cli(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(out / "plan.json"),
                        "--state-root",
                        str(root / "state"),
                        "--no-progress",
                        "--json",
                    ]
                )
            self.assertEqual(verified.manifest.base_url, "bigquery://docs")
            self.assertEqual(apply_result, 0, apply_stderr)
            self.assertTrue(json.loads(apply_stdout)["artifact_verified"])

    def test_remote_plan_and_crawl_reach_lazy_dependency_boundary(self) -> None:
        commands = [
            (
                [
                    "plan",
                    "--database-backend",
                    "bigquery",
                    "--relation",
                    "source-project.corpus.documents",
                    "--source-id",
                    "docs",
                    "--state-root",
                    ".buoy-test-not-created",
                    "--no-progress",
                ],
                "buoy_search.bigquery_relation._load_bigquery",
                BigQueryRelationError("BigQuery support is not installed. Install the `bigquery` extra."),
                "BigQuery support is not installed",
            ),
            (
                [
                    "crawl",
                    "--database-backend",
                    "bigquery",
                    "--relation",
                    "source-project.corpus.documents",
                    "--source-id",
                    "docs",
                    "--no-progress",
                ],
                "buoy_search.bigquery_relation._load_bigquery",
                BigQueryRelationError("BigQuery support is not installed. Install the `bigquery` extra."),
                "BigQuery support is not installed",
            ),
            (
                [
                    "plan",
                    "--database-backend",
                    "snowflake",
                    "--relation",
                    "DB.SCHEMA.DOCS",
                    "--source-id",
                    "docs",
                    "--snowflake-connection",
                    "analytics",
                    "--state-root",
                    ".buoy-test-not-created",
                    "--no-progress",
                ],
                "buoy_search.snowflake_relation._load_connector",
                SnowflakeRelationError("Snowflake support is not installed. Install the `snowflake` extra."),
                "Snowflake support is not installed",
            ),
            (
                [
                    "crawl",
                    "--database-backend",
                    "snowflake",
                    "--relation",
                    "DB.SCHEMA.DOCS",
                    "--source-id",
                    "docs",
                    "--snowflake-connection",
                    "analytics",
                    "--no-progress",
                ],
                "buoy_search.snowflake_relation._load_connector",
                SnowflakeRelationError("Snowflake support is not installed. Install the `snowflake` extra."),
                "Snowflake support is not installed",
            ),
        ]
        for argv, target, error, expected in commands:
            with self.subTest(argv=argv), patch(target, side_effect=error):
                result, stdout, stderr = self.run_cli(argv)
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn(expected, stderr)

    def test_invalid_backend_flag_and_path_combinations_fail_clearly(self) -> None:
        cases = [
            (
                ["plan", "db.duckdb", "--relation", "docs", "--source-id", "docs", "--bigquery-project", "billing"],
                "supported only with --database-backend bigquery",
            ),
            (
                ["plan", "--database-backend", "bigquery", "--relation", "p.d.t", "--source-id", "docs", "--snowflake-connection", "x"],
                "supported only with --database-backend snowflake",
            ),
            (
                ["plan", "local.db", "--database-backend", "bigquery", "--relation", "p.d.t", "--source-id", "docs"],
                "local source path/--base-url is not accepted",
            ),
            (
                ["crawl", "--base-url", "local.db", "--database-backend", "snowflake", "--relation", "DB.S.T", "--source-id", "docs", "--snowflake-connection", "x"],
                "local source path/--base-url is not accepted",
            ),
            (
                ["plan", "--database-backend", "snowflake", "--relation", "DB.S.T", "--source-id", "docs"],
                "--snowflake-connection is required",
            ),
            (
                ["crawl", "--database-backend", "bigquery", "--relation", "p.d.t"],
                "--source-id is required",
            ),
            (
                ["plan", "https://example.com", "--id-column", "id"],
                "require --relation",
            ),
            (
                ["plan", "db.duckdb", "--relation", "docs", "--source-id", "docs", "--source-query-timeout", "3"],
                "supported only with BigQuery or Snowflake",
            ),
        ]
        for argv, expected in cases:
            with self.subTest(argv=argv):
                result, stdout, stderr = self.run_cli(argv)
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn(expected, stderr)

    def test_nonfinite_source_query_timeout_fails_cli_validation(self) -> None:
        for value in ("nan", "inf", "-inf"):
            stderr = StringIO()
            with self.subTest(value=value), redirect_stderr(stderr), self.assertRaises(SystemExit):
                build_parser().parse_args(
                    [
                        "plan",
                        "--database-backend",
                        "bigquery",
                        "--relation",
                        "project.dataset.documents",
                        "--source-id",
                        "docs",
                        f"--source-query-timeout={value}",
                    ]
                )
            self.assertIn("finite value greater than zero", stderr.getvalue())

    def test_explicit_empty_column_mappings_are_not_defaulted(self) -> None:
        for flag in ("--id-column", "--content-column"):
            with self.subTest(flag=flag):
                result, stdout, stderr = self.run_cli(
                    [
                        "plan",
                        "--database-backend",
                        "bigquery",
                        "--relation",
                        "project.dataset.documents",
                        "--source-id",
                        "docs",
                        flag,
                        "",
                    ]
                )
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn("ordinary unquoted identifier", stderr)

    def test_help_names_all_backends_authentication_and_one_relation(self) -> None:
        parser = build_parser()
        for command in ("plan", "crawl"):
            help_text = parser._subparsers._group_actions[0].choices[command].format_help()
            self.assertIn("DuckDB", help_text)
            self.assertIn("BigQuery", help_text)
            self.assertIn("Snowflake", help_text)
            self.assertIn("--database-backend", help_text)
            self.assertIn("--bigquery-project", help_text)
            self.assertIn("--snowflake-connection", help_text)
            self.assertIn("one", help_text.lower())
            self.assertIn("websites and database relations", help_text)
            self.assertNotIn("websites and DuckDB relations", help_text)


if __name__ == "__main__":
    unittest.main()
