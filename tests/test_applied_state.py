from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest import mock
import unittest

import duckdb

from buoy_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    DUCKDB_STATE_SCHEMA_VERSION,
    ROW_STATUS_ACTIVE,
    ROW_STATUS_DELETED,
    ROW_STATUS_RETAINED_STALE,
    ApplyRunSummary,
    AppliedStateError,
    AppliedStateRow,
    acquire_namespace_apply_lock,
    applied_state_paths,
    applied_state_to_json,
    build_applied_state,
    load_applied_state,
    load_apply_run_summaries,
    resolve_state_root,
    save_applied_state,
)


def sample_row(row_id: str = "ts_abc", *, status: str = ROW_STATUS_ACTIVE) -> AppliedStateRow:
    return AppliedStateRow(
        row_id=row_id,
        canonical_url="https://example.com/docs/page",
        page_hash="page-hash",
        chunk_hash="chunk-hash",
        embedding_text_hash="embedding-hash",
        plan_id="plan_123",
        applied_at="2026-06-20T12:00:00+00:00",
        status=status,  # type: ignore[arg-type]
    )


def sample_state(rows: list[AppliedStateRow] | None = None):
    return build_applied_state(
        site_id="example-com",
        namespace="site-example-com-v1",
        base_url="https://example.com/docs/",
        last_plan_id="plan_123",
        last_apply_id="apply_123",
        rows=rows if rows is not None else [sample_row()],
        updated_at="2026-06-20T12:30:00+00:00",
    )


class AppliedStateStoreTests(unittest.TestCase):
    def test_default_paths_are_per_namespace_duckdb_and_legacy_cleanup(self) -> None:
        paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1")

        self.assertEqual(paths.database_path, Path(".buoy/state/example-com/site-example-com-v1/state.duckdb"))
        self.assertEqual(paths.legacy_state_path, Path(".buoy/state/example-com/site-example-com-v1/last-applied.json"))
        self.assertEqual(
            paths.legacy_archive_path,
            Path(".buoy/state/example-com/site-example-com-v1/legacy-json/last-applied.json"),
        )

    def test_implicit_state_root_defaults_to_buoy_without_creating_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / ".buoy"
            legacy = Path(tmp) / ".turbo-search"
            with mock.patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), mock.patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                resolved, warning = resolve_state_root(None)

            self.assertEqual(resolved, current)
            self.assertIsNone(warning)
            self.assertFalse(current.exists())
            self.assertFalse(legacy.exists())

    def test_implicit_state_root_uses_existing_buoy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / ".buoy"
            legacy = Path(tmp) / ".turbo-search"
            current.mkdir()
            with mock.patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), mock.patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                resolved, warning = resolve_state_root(None)

            self.assertEqual(resolved, current)
            self.assertIsNone(warning)

    def test_implicit_state_root_uses_legacy_in_place_without_copying(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / ".buoy"
            legacy = Path(tmp) / ".turbo-search"
            legacy.mkdir()
            marker = legacy / "marker"
            marker.write_text("preserve", encoding="utf-8")
            before = sorted(path.relative_to(Path(tmp)) for path in Path(tmp).rglob("*"))
            with mock.patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), mock.patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                resolved, warning = resolve_state_root(None)
            after = sorted(path.relative_to(Path(tmp)) for path in Path(tmp).rglob("*"))

            self.assertEqual(resolved, legacy)
            self.assertIn("using legacy state root", warning or "")
            self.assertEqual(after, before)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
            self.assertFalse(current.exists())

    def test_implicit_state_root_refuses_dual_roots_without_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / ".buoy"
            legacy = Path(tmp) / ".turbo-search"
            current.mkdir()
            legacy.mkdir()
            before = sorted(path.relative_to(Path(tmp)) for path in Path(tmp).rglob("*"))
            with mock.patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), mock.patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                with self.assertRaisesRegex(AppliedStateError, "both implicit state roots exist"):
                    resolve_state_root(None)
            after = sorted(path.relative_to(Path(tmp)) for path in Path(tmp).rglob("*"))
            self.assertEqual(after, before)

    def test_explicit_state_root_bypasses_dual_root_detection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            current = Path(tmp) / ".buoy"
            legacy = Path(tmp) / ".turbo-search"
            explicit = Path(tmp) / "chosen"
            current.mkdir()
            legacy.mkdir()
            with mock.patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), mock.patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                resolved, warning = resolve_state_root(explicit)

            self.assertEqual(resolved, explicit)
            self.assertIsNone(warning)
            self.assertFalse(explicit.exists())

    def test_missing_state_loads_as_first_apply_without_creating_database(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            state = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/#ignored",
                state_root=state_root,
            )
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            self.assertFalse(paths.database_path.exists())

        self.assertTrue(state.first_apply)
        self.assertEqual(state.schema_version, APPLIED_STATE_SCHEMA_VERSION)
        self.assertEqual(state.base_url, "https://example.com/docs/")
        self.assertEqual(state.rows, [])

    def test_save_loads_current_rows_in_one_duckdb_file_without_json_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            expected = sample_state([sample_row(), sample_row("ts_retained", status=ROW_STATUS_RETAINED_STALE)])

            paths = save_applied_state(expected, state_root=state_root)
            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertTrue(paths.database_path.exists())
            self.assertFalse(paths.legacy_state_path.exists())
            self.assertFalse(paths.legacy_archive_path.exists())
            self.assertFalse((paths.state_dir / "history").exists())
            self.assertEqual(loaded, expected)
            with duckdb.connect(str(paths.database_path), read_only=True) as connection:
                self.assertEqual(connection.execute("SELECT schema_version FROM state_schema").fetchall(), [(DUCKDB_STATE_SCHEMA_VERSION,)])
                self.assertEqual(connection.execute("SELECT count(*) FROM applied_rows").fetchone(), (2,))

    def test_apply_summaries_are_append_only_and_do_not_copy_row_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            state = sample_state()
            summary = ApplyRunSummary(
                apply_id="apply_123",
                plan_id="plan_123",
                applied_at="2026-06-20T12:30:00+00:00",
                rows_upserted=1,
                rows_deleted=0,
                retained_stale_rows=0,
            )
            paths = save_applied_state(state, state_root=state_root, apply_run=summary)
            next_state = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_124",
                last_apply_id="apply_124",
                rows=[sample_row("ts_next")],
                updated_at="2026-06-20T12:31:00+00:00",
            )
            next_summary = ApplyRunSummary(
                apply_id="apply_124",
                plan_id="plan_124",
                applied_at="2026-06-20T12:31:00+00:00",
                rows_upserted=1,
                rows_deleted=0,
                retained_stale_rows=0,
            )
            save_applied_state(next_state, state_root=state_root, apply_run=next_summary)

            summaries = load_apply_run_summaries(
                site_id="example-com",
                namespace="site-example-com-v1",
                state_root=state_root,
            )
            self.assertEqual(summaries, [summary, next_summary])
            self.assertEqual(
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                ),
                next_state,
            )
            self.assertFalse((paths.state_dir / "history").exists())

    def test_legacy_json_is_deleted_and_resets_active_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            paths.state_dir.mkdir(parents=True)
            paths.legacy_state_path.write_text(json.dumps(applied_state_to_json(sample_state())), encoding="utf-8")

            migrated = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertTrue(migrated.first_apply)
            self.assertEqual(migrated.rows, [])
            self.assertTrue(paths.database_path.exists())
            self.assertFalse(paths.legacy_state_path.exists())
            self.assertFalse(paths.legacy_archive_path.exists())
            self.assertFalse(paths.legacy_archive_path.parent.exists())
            self.assertFalse(list(paths.state_dir.glob(".state.duckdb.tmp-*")))

    def test_legacy_json_survives_failed_database_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            paths.state_dir.mkdir(parents=True)
            legacy_payload = json.dumps(applied_state_to_json(sample_state()))
            paths.legacy_state_path.write_text(legacy_payload, encoding="utf-8")

            with mock.patch(
                "buoy_search.applied_state._initialize_schema",
                side_effect=duckdb.Error("simulated initialization failure"),
            ):
                with self.assertRaisesRegex(AppliedStateError, "could not initialize DuckDB applied state"):
                    load_applied_state(
                        site_id="example-com",
                        namespace="site-example-com-v1",
                        base_url="https://example.com/docs/",
                        state_root=state_root,
                    )

            self.assertEqual(paths.legacy_state_path.read_text(encoding="utf-8"), legacy_payload)
            self.assertFalse(paths.database_path.exists())
            self.assertFalse(list(paths.state_dir.glob(".state.duckdb.tmp-*")))

    def test_legacy_migration_is_idempotent_and_purges_prior_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            paths.state_dir.mkdir(parents=True)
            paths.legacy_archive_path.parent.mkdir()
            paths.legacy_archive_path.write_text(json.dumps(applied_state_to_json(sample_state())), encoding="utf-8")
            paths.legacy_state_path.write_text(json.dumps(applied_state_to_json(sample_state())), encoding="utf-8")

            first = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )
            second = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertTrue(first.first_apply)
            self.assertTrue(second.first_apply)
            self.assertFalse(paths.legacy_state_path.exists())
            self.assertFalse(paths.legacy_archive_path.exists())
            self.assertFalse(paths.legacy_archive_path.parent.exists())

    def test_invalid_persisted_state_identity_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute("UPDATE state_metadata SET namespace = 'other-namespace'")

            with self.assertRaisesRegex(AppliedStateError, "namespace mismatch"):
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                )

    def test_invalid_persisted_schema_version_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute("DELETE FROM state_schema")
                connection.execute("INSERT INTO state_schema VALUES (999)")

            with self.assertRaisesRegex(AppliedStateError, "unsupported DuckDB applied state schema version"):
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                )

    def test_applied_rows_without_exactly_one_metadata_row_fail_clearly(self) -> None:
        for mutation, expected_error in (
            ("DELETE FROM state_metadata", "without state metadata"),
            (
                """
                INSERT INTO state_metadata
                SELECT schema_version, site_id, namespace, base_url, updated_at, last_plan_id, last_apply_id
                FROM state_metadata
                """,
                "without exactly one metadata row",
            ),
        ):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                state_root = Path(tmp)
                paths = save_applied_state(sample_state(), state_root=state_root)
                with duckdb.connect(str(paths.database_path)) as connection:
                    connection.execute(mutation)

                with self.assertRaisesRegex(AppliedStateError, expected_error):
                    load_applied_state(
                        site_id="example-com",
                        namespace="site-example-com-v1",
                        base_url="https://example.com/docs/",
                        state_root=state_root,
                    )

    def test_same_namespace_lock_contends_across_processes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            script = """
from pathlib import Path
import sys
import time
from buoy_search.applied_state import acquire_namespace_apply_lock
with acquire_namespace_apply_lock(site_id='example-com', namespace='site-example-com-v1', state_root=Path(sys.argv[1])):
    print('locked', flush=True)
    time.sleep(10)
"""
            process = subprocess.Popen(
                [sys.executable, "-c", script, str(state_root)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(process.stdout.readline().strip(), "locked")
                with self.assertRaisesRegex(AppliedStateError, "already in progress"):
                    with acquire_namespace_apply_lock(
                        site_id="example-com",
                        namespace="site-example-com-v1",
                        state_root=state_root,
                    ):
                        pass
            finally:
                process.terminate()
                process.communicate(timeout=5)

    def test_invalid_apply_summary_is_rejected_before_state_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            baseline = sample_state()
            save_applied_state(baseline, state_root=state_root)
            replacement = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_124",
                last_apply_id="apply_124",
                rows=[sample_row("ts_replacement")],
                updated_at="2026-06-20T12:31:00+00:00",
            )

            with self.assertRaisesRegex(AppliedStateError, "apply_id must match"):
                save_applied_state(
                    replacement,
                    state_root=state_root,
                    apply_run=ApplyRunSummary(
                        apply_id="other-apply",
                        plan_id="plan_124",
                        applied_at="2026-06-20T12:31:00+00:00",
                        rows_upserted=1,
                        rows_deleted=0,
                        retained_stale_rows=0,
                    ),
                )

            self.assertEqual(
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                ),
                baseline,
            )

    def test_apply_summary_plan_mismatch_is_rejected_before_state_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AppliedStateError, "plan_id must match"):
                save_applied_state(
                    sample_state(),
                    state_root=Path(tmp),
                    apply_run=ApplyRunSummary(
                        apply_id="apply_123",
                        plan_id="other-plan",
                        applied_at="2026-06-20T12:30:00+00:00",
                        rows_upserted=1,
                        rows_deleted=0,
                        retained_stale_rows=0,
                    ),
                )


if __name__ == "__main__":
    unittest.main()
