from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import mock
import unittest

from turbo_search import applied_state as state_module
from turbo_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    ROW_STATUS_ACTIVE,
    ROW_STATUS_DELETED,
    ROW_STATUS_RETAINED_STALE,
    AppliedStateError,
    AppliedStateRow,
    applied_state_paths,
    applied_state_to_json,
    build_applied_state,
    load_applied_state,
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


class AppliedStateStoreTests(unittest.TestCase):
    def test_default_paths_include_state_root_site_namespace_and_history(self) -> None:
        paths = applied_state_paths(site_id="example-com", namespace="site-example-com-v1")

        self.assertEqual(
            paths.last_applied_path,
            Path(".turbo-search/state/example-com/site-example-com-v1/last-applied.json"),
        )
        self.assertEqual(
            paths.history_path("apply_123"),
            Path(".turbo-search/state/example-com/site-example-com-v1/history/apply_123.json"),
        )

    def test_missing_state_loads_as_first_apply_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/#ignored",
                state_root=Path(tmp),
            )

        self.assertTrue(state.first_apply)
        self.assertEqual(state.schema_version, APPLIED_STATE_SCHEMA_VERSION)
        self.assertEqual(state.site_id, "example-com")
        self.assertEqual(state.namespace, "site-example-com-v1")
        self.assertEqual(state.base_url, "https://example.com/docs/")
        self.assertEqual(state.rows, [])

    def test_save_writes_history_and_atomically_replaces_last_applied(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            state = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                rows=[sample_row()],
                updated_at="2026-06-20T12:30:00+00:00",
            )
            original_replace = state_module.os.replace
            replace_calls: list[tuple[str, str]] = []

            def replacing(src: str | Path, dst: str | Path) -> None:
                replace_calls.append((str(src), str(dst)))
                original_replace(src, dst)

            with mock.patch("turbo_search.applied_state.os.replace", side_effect=replacing):
                paths = save_applied_state(state, state_root=state_root)

            self.assertEqual(len(replace_calls), 2)
            for src, dst in replace_calls:
                self.assertEqual(Path(src).parent, Path(dst).parent)
                self.assertIn(".tmp-", Path(src).name)
            self.assertTrue(paths.history_path("apply_123").exists())
            self.assertTrue(paths.last_applied_path.exists())
            self.assertEqual(
                json.loads(paths.last_applied_path.read_text(encoding="utf-8")),
                json.loads(paths.history_path("apply_123").read_text(encoding="utf-8")),
            )
            self.assertFalse(list(paths.state_dir.glob("*.tmp-*")))
            self.assertFalse(list(paths.history_dir.glob("*.tmp-*")))

    def test_existing_state_loads_and_validates_expected_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            expected = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                rows=[sample_row()],
                updated_at="2026-06-20T12:30:00+00:00",
            )
            save_applied_state(expected, state_root=state_root)

            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

        self.assertFalse(loaded.first_apply)
        self.assertEqual(loaded.last_apply_id, "apply_123")
        self.assertEqual(loaded.rows, [sample_row()])

    def test_retained_stale_and_deleted_rows_can_be_represented_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            retained = sample_row("ts_retained", status=ROW_STATUS_RETAINED_STALE)
            deleted = sample_row("ts_deleted", status=ROW_STATUS_DELETED)
            state = build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                rows=[retained, deleted],
                updated_at="2026-06-20T12:30:00+00:00",
            )
            save_applied_state(state, state_root=state_root)

            loaded = load_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                state_root=state_root,
            )

        self.assertEqual([row.status for row in loaded.rows], [ROW_STATUS_RETAINED_STALE, ROW_STATUS_DELETED])
        self.assertEqual(loaded.rows[0].row_id, "ts_retained")

    def test_invalid_schema_version_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(
                site_id="example-com",
                namespace="site-example-com-v1",
                state_root=state_root,
            )
            paths.state_dir.mkdir(parents=True)
            payload = applied_state_to_json(
                build_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    last_plan_id="plan_123",
                    last_apply_id="apply_123",
                    rows=[sample_row()],
                )
            )
            payload["schema_version"] = 999
            paths.last_applied_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(AppliedStateError, "unsupported applied state schema_version"):
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                )

    def test_conflicting_site_namespace_or_base_url_fails_clearly(self) -> None:
        base_payload = applied_state_to_json(
            build_applied_state(
                site_id="example-com",
                namespace="site-example-com-v1",
                base_url="https://example.com/docs/",
                last_plan_id="plan_123",
                last_apply_id="apply_123",
                rows=[sample_row()],
            )
        )

        for field, bad_value, expected_error in (
            ("site_id", "other-site", "site_id mismatch"),
            ("namespace", "other-namespace", "namespace mismatch"),
            ("base_url", "https://example.com/other/", "base_url mismatch"),
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                state_root = Path(tmp)
                paths = applied_state_paths(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    state_root=state_root,
                )
                paths.state_dir.mkdir(parents=True)
                payload = dict(base_payload)
                payload[field] = bad_value
                paths.last_applied_path.write_text(json.dumps(payload), encoding="utf-8")

                with self.assertRaisesRegex(AppliedStateError, expected_error):
                    load_applied_state(
                        site_id="example-com",
                        namespace="site-example-com-v1",
                        base_url="https://example.com/docs/",
                        state_root=state_root,
                    )

    def test_invalid_row_status_fails_clearly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp)
            paths = applied_state_paths(
                site_id="example-com",
                namespace="site-example-com-v1",
                state_root=state_root,
            )
            paths.state_dir.mkdir(parents=True)
            payload = applied_state_to_json(
                build_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    last_plan_id="plan_123",
                    last_apply_id="apply_123",
                    rows=[sample_row()],
                )
            )
            payload["rows"][0]["status"] = "weird"
            paths.last_applied_path.write_text(json.dumps(payload), encoding="utf-8")

            with self.assertRaisesRegex(AppliedStateError, "invalid status"):
                load_applied_state(
                    site_id="example-com",
                    namespace="site-example-com-v1",
                    base_url="https://example.com/docs/",
                    state_root=state_root,
                )


if __name__ == "__main__":
    unittest.main()
