from __future__ import annotations

import os
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
    AppliedStateSummary,
    acquire_namespace_apply_lock,
    applied_state_paths,
    build_applied_state,
    load_applied_state,
    load_applied_state_summary,
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


def file_snapshot(path: Path) -> tuple[int, int, int, int, bytes]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, path.read_bytes()


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
    def test_default_paths_are_per_namespace_duckdb(self) -> None:
        paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1")

        self.assertEqual(paths.state_dir, Path(".buoy/state/example-com/site-example-com-v1"))
        self.assertEqual(paths.database_path, paths.state_dir / "state.duckdb")
        self.assertEqual(paths.lock_path, paths.state_dir / "apply.lock")

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
            self.assertFalse((paths.state_dir / "history").exists())
            self.assertEqual(loaded, expected)
            with duckdb.connect(str(paths.database_path), read_only=True) as connection:
                self.assertEqual(connection.execute("SELECT schema_version FROM state_schema").fetchall(), [(DUCKDB_STATE_SCHEMA_VERSION,)])
                self.assertEqual(connection.execute("SELECT count(*) FROM applied_rows").fetchone(), (2,))

    def test_summary_reader_uses_one_read_only_aggregate_connection_for_100k_rows(self) -> None:
        real_connect = duckdb.connect
        connections: list[tuple[Path, dict[str, object]]] = []
        queries: list[str] = []
        materialized_sizes: list[int] = []

        class TracingConnection:
            def __init__(self, path, **kwargs):  # noqa: ANN001
                connections.append((Path(path), kwargs))
                self.inner = real_connect(path, **kwargs)
                self.sql = ""

            def __enter__(self):  # noqa: ANN204
                return self

            def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
                self.inner.close()

            def execute(self, sql, parameters=None):  # noqa: ANN001, ANN201
                self.sql = " ".join(str(sql).split())
                queries.append(self.sql)
                if parameters is None:
                    self.inner.execute(sql)
                else:
                    self.inner.execute(sql, parameters)
                return self

            def fetchall(self):  # noqa: ANN201
                rows = self.inner.fetchall()
                materialized_sizes.append(len(rows))
                return rows

            def fetchone(self):  # noqa: ANN201
                row = self.inner.fetchone()
                materialized_sizes.append(0 if row is None else 1)
                return row

        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            with real_connect(str(paths.database_path)) as connection:
                connection.execute("DELETE FROM applied_rows")
                connection.execute(
                    """
                    INSERT INTO applied_rows
                    SELECT 'ts_' || printf('%032x', i),
                           'https://example.com/docs/' || i,
                           repeat('a', 64), repeat('b', 64), repeat('c', 64),
                           'plan_123', '2026-06-20T12:00:00+00:00',
                           CASE i % 4 WHEN 0 THEN 'active' WHEN 1 THEN 'active'
                                      WHEN 2 THEN 'retained_stale' ELSE 'deleted' END
                    FROM range(100000) rows(i)
                    """
                )
                connection.execute("CHECKPOINT")
            before = file_snapshot(paths.database_path)

            with mock.patch(
                "buoy_search.applied_state.duckdb.connect", side_effect=TracingConnection
            ), mock.patch(
                "buoy_search.applied_state.AppliedStateRow",
                side_effect=AssertionError("summary constructed a full row"),
            ):
                summary = load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

            self.assertEqual(file_snapshot(paths.database_path), before)

        self.assertEqual(
            summary,
            AppliedStateSummary(
                schema_version=1,
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                updated_at="2026-06-20T12:30:00+00:00",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                active_rows=50_000,
                retained_stale_rows=25_000,
                deleted_rows=25_000,
                total_rows=100_000,
            ),
        )
        self.assertEqual(connections, [(paths.database_path, {"read_only": True})])
        self.assertEqual(materialized_sizes, [1, 1, 1])
        self.assertTrue(any("FILTER (WHERE status = 'active')" in sql for sql in queries))
        self.assertFalse(any("ORDER BY canonical_url" in sql for sql in queries))
        self.assertFalse(any("SELECT row_id, canonical_url" in sql for sql in queries))

    def test_summary_reader_requires_safe_descriptor_primitives_and_translates_not_implemented(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)

            for primitive in ("O_NOFOLLOW", "O_DIRECTORY"):
                with self.subTest(primitive=primitive), mock.patch.object(
                    os, primitive, None
                ), self.assertRaisesRegex(AppliedStateError, "primitives are unavailable"):
                    load_applied_state_summary(
                        database_path=paths.database_path, state_root=state_root
                    )

            with self.subTest(primitive="dir_fd"), mock.patch.object(
                os, "supports_dir_fd", set()
            ), self.assertRaisesRegex(AppliedStateError, "primitives are unavailable"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

            unavailable_open = mock.Mock(side_effect=NotImplementedError)
            with self.subTest(primitive="os.open"), mock.patch.object(
                os, "open", unavailable_open
            ), mock.patch.object(
                os, "supports_dir_fd", {unavailable_open}
            ), self.assertRaisesRegex(AppliedStateError, "primitives are unavailable"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

    def test_summary_reader_rejects_unknown_status_identity_and_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute("UPDATE applied_rows SET status = 'unknown'")
            with self.assertRaisesRegex(AppliedStateError, "unknown status"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute("UPDATE applied_rows SET status = 'active'")
                connection.execute("UPDATE state_metadata SET namespace = 'other'")
            with self.assertRaisesRegex(AppliedStateError, "path does not match"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute(
                    "UPDATE state_metadata SET namespace = 'site-example-com-v1'"
                )
            target = paths.state_dir / "target.duckdb"
            paths.database_path.rename(target)
            paths.database_path.symlink_to(target)
            with self.assertRaisesRegex(AppliedStateError, "regular no-follow"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

    def test_summary_reader_detects_database_replacement_during_inspection(self) -> None:
        real_connect = duckdb.connect
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            replacement = state_root / "replacement.duckdb"
            replacement.write_bytes(paths.database_path.read_bytes())

            def connect_then_replace(path, **kwargs):  # noqa: ANN001, ANN202
                connection = real_connect(path, **kwargs)
                original = paths.database_path.with_name("original.duckdb")
                paths.database_path.rename(original)
                replacement.rename(paths.database_path)
                return connection

            with mock.patch(
                "buoy_search.applied_state.duckdb.connect", side_effect=connect_then_replace
            ):
                with self.assertRaisesRegex(AppliedStateError, "changed during"):
                    load_applied_state_summary(
                        database_path=paths.database_path, state_root=state_root
                    )

    def test_summary_reader_detects_database_aba_during_inspection(self) -> None:
        real_connect = duckdb.connect
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state-root"
            paths = save_applied_state(sample_state(), state_root=state_root)
            replacement_root = root / "replacement-root"
            replacement_paths = save_applied_state(
                sample_state([sample_row(), sample_row("ts_other")]),
                state_root=replacement_root,
            )
            replacement = root / "replacement.duckdb"
            replacement_paths.database_path.rename(replacement)

            def connect_to_b_then_restore_a(path, **kwargs):  # noqa: ANN001, ANN202
                held_a = paths.database_path.with_name("held-a.duckdb")
                paths.database_path.rename(held_a)
                replacement.rename(paths.database_path)
                connection = real_connect(path, **kwargs)
                paths.database_path.rename(replacement)
                held_a.rename(paths.database_path)
                return connection

            with mock.patch(
                "buoy_search.applied_state.duckdb.connect",
                side_effect=connect_to_b_then_restore_a,
            ):
                with self.assertRaisesRegex(AppliedStateError, "changed during"):
                    load_applied_state_summary(
                        database_path=paths.database_path, state_root=state_root
                    )

    def test_summary_reader_rejects_root_intermediate_symlink_and_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_root = root / "real-root"
            paths = save_applied_state(sample_state(), state_root=real_root)

            linked_root = root / "linked-root"
            linked_root.symlink_to(real_root, target_is_directory=True)
            with self.assertRaises(AppliedStateError):
                load_applied_state_summary(
                    database_path=linked_root / paths.database_path.relative_to(real_root),
                    state_root=linked_root,
                )

            state_directory = real_root / "state"
            moved_state = real_root / "moved-state"
            state_directory.rename(moved_state)
            state_directory.symlink_to(moved_state, target_is_directory=True)
            with self.assertRaises(AppliedStateError):
                load_applied_state_summary(
                    database_path=real_root / "state" / "example-com" / "site-example-com-v1" / "state.duckdb",
                    state_root=real_root,
                )

            with self.assertRaisesRegex(AppliedStateError, "escapes"):
                load_applied_state_summary(
                    database_path=root / "outside.duckdb", state_root=real_root
                )

    def test_summary_reader_reuses_schema_validator_and_requires_one_metadata_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, mutation, message in (
                (
                    "schema",
                    "UPDATE state_schema SET schema_version = 2",
                    "unsupported DuckDB applied state schema version",
                ),
                ("zero-metadata", "DELETE FROM state_metadata", "exactly one metadata row"),
                (
                    "duplicate-metadata",
                    "INSERT INTO state_metadata SELECT * FROM state_metadata",
                    "exactly one metadata row",
                ),
            ):
                with self.subTest(name=name):
                    state_root = root / name
                    paths = save_applied_state(sample_state(), state_root=state_root)
                    with duckdb.connect(str(paths.database_path)) as connection:
                        connection.execute(mutation)
                    with self.assertRaisesRegex(AppliedStateError, message):
                        load_applied_state_summary(
                            database_path=paths.database_path, state_root=state_root
                        )

    def test_summary_reader_closes_descriptor_when_initial_fstat_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            real_fstat = os.fstat
            real_close = os.close
            closed: list[int] = []
            fstat_calls = 0

            def fail_first_fstat(descriptor: int):  # noqa: ANN202
                nonlocal fstat_calls
                fstat_calls += 1
                if fstat_calls == 1:
                    raise OSError("forced initial fstat failure")
                return real_fstat(descriptor)

            def record_close(descriptor: int) -> None:
                closed.append(descriptor)
                real_close(descriptor)

            with mock.patch(
                "buoy_search.applied_state.os.fstat", side_effect=fail_first_fstat
            ), mock.patch(
                "buoy_search.applied_state.os.close", side_effect=record_close
            ), self.assertRaisesRegex(AppliedStateError, "unsafe no-follow path"):
                load_applied_state_summary(
                    database_path=paths.database_path, state_root=state_root
                )

            self.assertEqual(fstat_calls, 1)
            self.assertEqual(len(closed), 1)
            with self.assertRaises(OSError):
                real_fstat(closed[0])

    def test_summary_reader_closes_connection_and_all_descriptors_on_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            connection_closed = False

            class FailingConnection:
                def __enter__(self):  # noqa: ANN204
                    return self

                def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
                    nonlocal connection_closed
                    connection_closed = True

                def execute(self, sql, parameters=None):  # noqa: ANN001, ANN201
                    raise duckdb.IOException("forced query failure")

            with mock.patch(
                "buoy_search.applied_state.duckdb.connect",
                return_value=FailingConnection(),
            ):
                with self.assertRaisesRegex(AppliedStateError, "could not load"):
                    load_applied_state_summary(
                        database_path=paths.database_path, state_root=state_root
                    )
            self.assertTrue(connection_closed)

            closed: list[int] = []

            def close_then_fail_first(descriptor: int) -> None:
                closed.append(descriptor)
                real_close(descriptor)
                if len(closed) == 1:
                    raise OSError("forced close failure")

            real_close = __import__("os").close
            with mock.patch(
                "buoy_search.applied_state.os.close", side_effect=close_then_fail_first
            ):
                with self.assertRaisesRegex(AppliedStateError, "close.*descriptors"):
                    load_applied_state_summary(
                        database_path=paths.database_path, state_root=state_root
                    )
            self.assertEqual(len(closed), 6)

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

    def test_obsolete_json_files_are_inert_without_duckdb_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            obsolete_paths = (
                paths.state_dir / "last-applied.json",
                paths.state_dir / "legacy-json" / "last-applied.json",
            )
            for index, obsolete_path in enumerate(obsolete_paths):
                obsolete_path.parent.mkdir(parents=True, exist_ok=True)
                obsolete_path.write_bytes(f"not valid json {index}\x00".encode())
            before = {path: file_snapshot(path) for path in obsolete_paths}

            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertTrue(loaded.first_apply)
            self.assertEqual(loaded.rows, [])
            self.assertFalse(paths.database_path.exists())
            self.assertEqual({path: file_snapshot(path) for path in obsolete_paths}, before)

    def test_obsolete_json_files_are_inert_during_duckdb_save_and_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1", state_root=state_root)
            obsolete_paths = (
                paths.state_dir / "last-applied.json",
                paths.state_dir / "legacy-json" / "last-applied.json",
            )
            for index, obsolete_path in enumerate(obsolete_paths):
                obsolete_path.parent.mkdir(parents=True, exist_ok=True)
                obsolete_path.write_bytes(f"obsolete {index}\n".encode())
            before = {path: file_snapshot(path) for path in obsolete_paths}

            expected = sample_state()
            save_applied_state(expected, state_root=state_root)
            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertEqual(loaded, expected)
            self.assertEqual({path: file_snapshot(path) for path in obsolete_paths}, before)

    def test_valid_initialized_empty_duckdb_is_first_apply_with_obsolete_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = save_applied_state(sample_state(), state_root=state_root)
            with duckdb.connect(str(paths.database_path)) as connection:
                connection.execute("DELETE FROM applied_rows")
                connection.execute("DELETE FROM state_metadata")
            obsolete_path = paths.state_dir / "last-applied.json"
            obsolete_path.write_bytes(b'{"rows": ["must not parse"]}\n')
            before = file_snapshot(obsolete_path)

            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

            self.assertTrue(loaded.first_apply)
            self.assertEqual(loaded.rows, [])
            self.assertEqual(file_snapshot(obsolete_path), before)

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
            obsolete_path = paths.state_dir / "last-applied.json"
            obsolete_path.write_bytes(b"invalid duckdb must still fail closed\n")
            before = file_snapshot(obsolete_path)

            with self.assertRaisesRegex(AppliedStateError, "unsupported DuckDB applied state schema version"):
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                )
            self.assertEqual(file_snapshot(obsolete_path), before)

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
