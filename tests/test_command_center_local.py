from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

from buoy_search.applied_state import AppliedStateRow, build_applied_state, save_applied_state
from buoy_search.chunker import process_corpus
from buoy_search.command_center_local import InventoryLookupError, LocalInventoryService
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts


def write_plan(
    root: Path,
    *,
    body: str = "# Guide\n\nChanged local content.",
    state=None,  # noqa: ANN001 - fixture accepts AppliedState or None.
    state_present: bool = False,
    originating_job_id: str | None = None,
) -> tuple[str, Path]:
    corpus = root / "corpus"
    corpus.mkdir(parents=True)
    (corpus / "page.md").write_text(
        "---\nurl: https://example.com/docs/page\ntitle: Guide\nstatus: 200\n"
        "content_type: text/markdown\nsource_kind: website\n---\n\n" + body + "\n",
        encoding="utf-8",
    )
    artifacts = build_plan_artifacts(
        indexing_plan=process_corpus(corpus),
        base_url="https://example.com/docs",
        out_dir=root,
        applied_state=state,
        state_present=state_present,
        originating_job_id=originating_job_id,
    )
    output = root / "plan"
    write_plan_artifacts(artifacts, output)
    return artifacts.plan.plan_id, output


def write_large_stale_plan(root: Path, *, row_count: int) -> tuple[str, Path]:
    """Create a valid large delta without retaining all fixture rows in Python."""

    from buoy_search.plan_artifacts import (
        _create_delta_schema,
        artifact_identity,
        normalize_json_object,
        stable_hash,
        stable_json_dumps,
    )
    import duckdb

    _, template_output = write_plan(root / "template")
    plan = json.loads((template_output / "plan.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    digest.update(b'{"schema_version":1,"stale_rows":[')
    for index in range(row_count):
        if index:
            digest.update(b",")
        row = {
            "category": "stale",
            "row_id": f"ts_{index:032x}",
            "canonical_url": f"https://example.com/docs/removed/{index:06d}",
            "page_hash": "a" * 64,
            "chunk_hash": "b" * 64,
            "embedding_text_hash": "c" * 64,
            "prior_plan_id": "plan_" + "d" * 16,
            "prior_applied_at": "2026-07-25T00:00:00+00:00",
            "prior_status": "active",
            "reason": "not_in_desired_source",
        }
        digest.update(stable_json_dumps(normalize_json_object(row)).encode("utf-8"))
    digest.update(b'],"upsert_rows":[]}')
    plan["applied_state"] = {"schema_version": 1, "present": True, "hash": "e" * 64}
    plan["delta"].update(
        logical_hash=digest.hexdigest(), upsert_count=0, stale_count=row_count,
        retained_stale_count=0,
    )
    plan["diff"].update(
        chunks_to_embed=0, chunks_unchanged=0, first_apply=False, pages_added=0,
        pages_changed=0, pages_removed=0, pages_unchanged=0,
        retained_stale_rows=0, rows_to_upsert=0, stale_rows=row_count,
    )
    plan["artifact_hash"] = stable_hash(artifact_identity(plan))
    plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"

    output = root / "large-plan"
    output.mkdir(parents=True)
    (output / "plan.json").write_text(
        stable_json_dumps(plan, indent=2) + "\n", encoding="utf-8"
    )
    with duckdb.connect(str(output / "delta.duckdb")) as connection:
        _create_delta_schema(connection)
        connection.execute(
            "INSERT INTO delta_metadata VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                1, plan["plan_id"], plan["site_id"], plan["namespace"],
                plan["source"]["kind"], plan["source"]["uri"],
                plan["applied_state"]["hash"], plan["delta"]["logical_hash"],
                0, row_count, 0,
            ],
        )
        connection.execute(
            """
            INSERT INTO stale_rows
            SELECT i, 'stale', 'ts_' || printf('%032x', i),
                   'https://example.com/docs/removed/' || printf('%06d', i),
                   repeat('a', 64), repeat('b', 64), repeat('c', 64),
                   'plan_' || repeat('d', 16), '2026-07-25T00:00:00+00:00',
                   'active', 'not_in_desired_source'
            FROM range(?) rows(i)
            """,
            [row_count],
        )
        connection.execute("CHECKPOINT")
    return str(plan["plan_id"]), output


def changed_and_stale_state(root: Path):  # noqa: ANN201 - fixture.
    first = root / "first"
    plan_id, output = write_plan(first, body="# Guide\n\nOld content.")
    from buoy_search.plan_artifacts import verify_plan_artifacts

    old = verify_plan_artifacts(output / "plan.json").upsert_rows[0]
    return build_applied_state(
        site_id="example-com",
        namespace="site-example-com-v1",
        base_url="https://example.com/docs",
        last_plan_id=plan_id,
        last_apply_id="apply_old",
        updated_at="2026-07-25T00:00:00+00:00",
        rows=[
            AppliedStateRow(
                row_id=str(old["row_id"]),
                canonical_url=str(old["canonical_url"]),
                page_hash=str(old["page_hash"]),
                chunk_hash=str(old["chunk_hash"]),
                embedding_text_hash=str(old["embedding_text_hash"]),
                plan_id=plan_id,
                applied_at="2026-07-25T00:00:00+00:00",
            ),
            AppliedStateRow(
                row_id="ts_" + "d" * 32,
                canonical_url="https://example.com/docs/removed",
                page_hash="a" * 64,
                chunk_hash="b" * 64,
                embedding_text_hash="c" * 64,
                plan_id=plan_id,
                applied_at="2026-07-25T00:00:00+00:00",
            ),
        ],
    )


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value


class CompactDeltaInventoryTests(unittest.TestCase):
    def test_plan_directories_are_leaves_before_any_parse_outcome(self) -> None:
        import os

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, template_output = write_plan(root / "template")
            plan_bytes = (template_output / "plan.json").read_bytes()
            delta_bytes = (template_output / "delta.duckdb").read_bytes()
            artifacts = root / "artifacts"
            cases = {
                "valid": plan_bytes,
                "legacy": b'{"schema_version":1}',
                "malformed": b"{not-json",
                "unsupported": b'{"schema_version":999}',
                "missing-delta": plan_bytes,
            }
            nested_paths: list[Path] = []
            for name, payload in cases.items():
                directory = artifacts / name
                nested = directory / "payload" / "nested-plan"
                nested.mkdir(parents=True)
                (directory / "plan.json").write_bytes(payload)
                if name != "missing-delta":
                    (directory / "delta.duckdb").write_bytes(delta_bytes)
                (nested / "plan.json").write_bytes(plan_bytes)
                (nested / "delta.duckdb").write_bytes(delta_bytes)
                nested_paths.extend([directory / "payload", nested])
            sibling_id, _ = write_plan(artifacts / "sibling")
            walked: list[Path] = []
            real_walk = os.walk

            def tracing_walk(top, *args, **kwargs):  # noqa: ANN001, ANN202
                for item in real_walk(top, *args, **kwargs):
                    walked.append(Path(item[0]))
                    yield item

            with patch("buoy_search.command_center_local.os.walk", side_effect=tracing_walk):
                inventory = LocalInventoryService(
                    artifacts_root=artifacts, state_root=root / "state"
                ).list_plans(limit=100)

        self.assertIn(sibling_id, [item.plan_id for item in inventory.items])
        self.assertTrue(all(path not in walked for path in nested_paths))
        self.assertEqual(len(inventory.errors), 3)
        self.assertEqual({error.code for error in inventory.errors}, {"malformed_plan"})

    def test_summary_cache_reuses_errors_expires_invalidates_and_bounds_ttl(self) -> None:
        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            malformed = root / "artifacts" / "malformed"
            malformed.mkdir(parents=True)
            (malformed / "plan.json").write_text("{bad", encoding="utf-8")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                clock=clock,
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                wraps=__import__(
                    "buoy_search.command_center_local", fromlist=["_discover_plans"]
                )._discover_plans,
            ) as plans, patch(
                "buoy_search.command_center_local._discover_states",
                wraps=__import__(
                    "buoy_search.command_center_local", fromlist=["_discover_states"]
                )._discover_states,
            ) as states:
                self.assertEqual(service.dashboard().artifact_error_count, 1)
                (malformed / "plan.json").write_text(
                    '{"schema_version":1}', encoding="utf-8"
                )
                self.assertEqual(service.list_namespaces().errors[0].code, "malformed_plan")
                service.list_plans()
                self.assertEqual((plans.call_count, states.call_count), (1, 1))

                clock.value = 1.0
                self.assertEqual(service.dashboard().artifact_error_count, 0)
                self.assertEqual((plans.call_count, states.call_count), (2, 2))

                service.invalidate()
                service.list_plans()
                self.assertEqual((plans.call_count, states.call_count), (3, 3))

        for ttl in (float("nan"), float("inf"), 0.49, 2.01, True):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                LocalInventoryService(cache_ttl=ttl)  # type: ignore[arg-type]
        LocalInventoryService(cache_ttl=0.5)
        LocalInventoryService(cache_ttl=2.0)

    def test_slow_rebuild_is_immediately_expired_and_exposes_external_plan(self) -> None:
        import buoy_search.command_center_local as local_module

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_discover = local_module._discover_plans
            external_plan_id: str | None = None

            def slow_first_discover(path):  # noqa: ANN001, ANN202
                nonlocal external_plan_id
                result = real_discover(path)
                if external_plan_id is None:
                    external_plan_id, _ = write_plan(path / "external")
                    clock.value = 1.0
                return result

            service = LocalInventoryService(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                clock=clock,
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                side_effect=slow_first_discover,
            ) as plans:
                self.assertEqual(service.list_plans().total, 0)
                refreshed = service.list_plans()

        self.assertEqual(plans.call_count, 2)
        self.assertEqual([item.plan_id for item in refreshed.items], [external_plan_id])

    def test_direct_miss_refreshes_after_concurrent_rebuild_expires(self) -> None:
        import buoy_search.command_center_local as local_module

        clock = FakeClock()
        direct_miss_observed = threading.Event()
        continue_direct_miss = threading.Event()
        forced_refresh_attempted = threading.Event()
        concurrent_scan_finished = threading.Event()
        release_concurrent_rebuild = threading.Event()
        discover_calls = 0
        discover_lock = threading.Lock()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, staged_plan = write_plan(root / "staging")
            real_discover = local_module._discover_plans

            def slow_concurrent_discover(path):  # noqa: ANN001, ANN202
                nonlocal discover_calls
                with discover_lock:
                    discover_calls += 1
                    call = discover_calls
                result = real_discover(path)
                if call == 2:
                    concurrent_scan_finished.set()
                    self.assertTrue(release_concurrent_rebuild.wait(timeout=5))
                return result

            service = LocalInventoryService(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                clock=clock,
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                side_effect=slow_concurrent_discover,
            ):
                old = service._snapshot()
                real_snapshot = service._snapshot

                def coordinated_snapshot(*, force=False, previous=None):  # noqa: ANN001, ANN202
                    if force:
                        forced_refresh_attempted.set()
                    snapshot = real_snapshot(force=force, previous=previous)
                    if (
                        threading.current_thread().name.startswith("direct-miss")
                        and not force
                        and previous is None
                    ):
                        self.assertIs(snapshot, old)
                        direct_miss_observed.set()
                        self.assertTrue(continue_direct_miss.wait(timeout=5))
                    return snapshot

                service._snapshot = coordinated_snapshot  # type: ignore[method-assign]
                with ThreadPoolExecutor(
                    max_workers=1, thread_name_prefix="direct-miss"
                ) as direct_executor, ThreadPoolExecutor(max_workers=1) as rebuild_executor:
                    direct = direct_executor.submit(service.get_plan, plan_id)
                    self.assertTrue(direct_miss_observed.wait(timeout=5))

                    clock.value = 1.0
                    concurrent = rebuild_executor.submit(service.list_plans)
                    self.assertTrue(concurrent_scan_finished.wait(timeout=5))
                    external_plan = root / "artifacts" / "external" / "plan"
                    external_plan.parent.mkdir(parents=True)
                    staged_plan.rename(external_plan)
                    clock.value = 2.0

                    continue_direct_miss.set()
                    self.assertTrue(forced_refresh_attempted.wait(timeout=5))
                    release_concurrent_rebuild.set()

                    self.assertEqual(concurrent.result(timeout=5).total, 0)
                    self.assertEqual(direct.result(timeout=5).summary.plan_id, plan_id)

        self.assertEqual(discover_calls, 3)

    def test_unavailable_state_summary_primitive_is_an_isolated_safe_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_applied_state(
                changed_and_stale_state(root / "fixture"), state_root=root / "state"
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )

            with patch.object(os, "O_DIRECTORY", None):
                dashboard = service.dashboard()
                namespaces = service.list_namespaces()
                plans = service.list_plans()

        self.assertIsNone(dashboard.active_row_count)
        self.assertEqual(dashboard.artifact_error_count, 1)
        self.assertEqual(namespaces.items, [])
        self.assertEqual(plans.items, [])
        for errors in (dashboard.artifact_errors, namespaces.errors, plans.errors):
            self.assertEqual([error.code for error in errors], ["malformed_state"])
            self.assertIn("primitives are unavailable", errors[0].message)

    def test_summary_cache_prevents_concurrent_rebuild_stampede(self) -> None:
        import buoy_search.command_center_local as local_module

        counts = {"plans": 0, "states": 0}
        count_lock = threading.Lock()
        real_plans = local_module._discover_plans
        real_states = local_module._discover_states

        def discover_plans(root):  # noqa: ANN001, ANN202
            with count_lock:
                counts["plans"] += 1
            time.sleep(0.05)
            return real_plans(root)

        def discover_states(root):  # noqa: ANN001, ANN202
            with count_lock:
                counts["states"] += 1
            return real_states(root)

        clock = FakeClock()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = LocalInventoryService(
                artifacts_root=root / "artifacts",
                state_root=root / "state",
                clock=clock,
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                side_effect=discover_plans,
            ), patch(
                "buoy_search.command_center_local._discover_states",
                side_effect=discover_states,
            ), ThreadPoolExecutor(max_workers=12) as executor:
                dashboards = list(executor.map(lambda _: service.dashboard(), range(24)))
                self.assertEqual(counts, {"plans": 1, "states": 1})
                clock.value = 1.0
                dashboards.extend(executor.map(lambda _: service.dashboard(), range(24)))
                self.assertEqual(counts, {"plans": 2, "states": 2})
                service.invalidate()
                dashboards.extend(executor.map(lambda _: service.dashboard(), range(24)))

        self.assertTrue(all(item.plan_count == 0 for item in dashboards))
        self.assertEqual(counts, {"plans": 3, "states": 3})

    def test_direct_plan_and_namespace_misses_force_one_refresh(self) -> None:
        import buoy_search.command_center_local as local_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                wraps=local_module._discover_plans,
            ) as plans:
                service.list_plans()
                plan_id, _ = write_plan(root / "artifacts" / "new")
                self.assertEqual(service.get_plan(plan_id).summary.plan_id, plan_id)
                self.assertEqual(plans.call_count, 2)

            state_service = LocalInventoryService(
                artifacts_root=root / "other-artifacts", state_root=root / "other-state"
            )
            with patch(
                "buoy_search.command_center_local._discover_states",
                wraps=local_module._discover_states,
            ) as states:
                state_service.list_namespaces()
                save_applied_state(changed_and_stale_state(root / "state-fixture"), state_root=root / "other-state")
                namespace = state_service.get_namespace("site-example-com-v1")
                self.assertEqual(namespace.summary.namespace, "site-example-com-v1")
                self.assertEqual(states.call_count, 2)

            missing = LocalInventoryService(
                artifacts_root=root / "missing-artifacts", state_root=root / "missing-state"
            )
            with patch(
                "buoy_search.command_center_local._discover_plans",
                wraps=local_module._discover_plans,
            ) as missing_plans:
                with self.assertRaisesRegex(InventoryLookupError, "not found"):
                    missing.get_plan("plan_missing")
                self.assertEqual(missing_plans.call_count, 2)

    def test_invalidate_is_non_raising_even_if_lock_fails(self) -> None:
        class BrokenLock:
            def __enter__(self):  # noqa: ANN204
                raise RuntimeError("lock failed")

            def __exit__(self, *args):  # noqa: ANN002, ANN204
                return None

        service = LocalInventoryService()
        service._cache_lock = BrokenLock()  # type: ignore[assignment]
        self.assertIsNone(service.invalidate())

    def test_summary_cache_imports_no_remote_provider_model_or_source_adapter(self) -> None:
        script = """
import sys
from pathlib import Path
from buoy_search.command_center_local import LocalInventoryService
artifacts = Path(sys.argv[1])
plan_id = sys.argv[2]
service = LocalInventoryService(artifacts_root=artifacts, state_root=artifacts.parent / 'state')
inventory = service.list_plans()
if inventory.total != 1 or inventory.items[0].plan_id != plan_id:
    raise SystemExit('valid schema-v2 plan was not summary-qualified')
service.dashboard()
forbidden = {
    'buoy_search.apply', 'buoy_search.bigquery_relation', 'buoy_search.command_center_remote',
    'buoy_search.crawler', 'buoy_search.database_relation', 'buoy_search.duckdb_relation',
    'buoy_search.github_repo', 'buoy_search.planning_service', 'buoy_search.retriever',
    'buoy_search.snowflake_relation',
}
loaded = sorted(forbidden.intersection(sys.modules))
if loaded:
    raise SystemExit(','.join(loaded))
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, _ = write_plan(root / "artifacts" / "valid")
            result = subprocess.run(
                [sys.executable, "-c", script, str(root / "artifacts"), plan_id],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_summary_inventory_never_opens_delta_and_schema1_is_inert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, _ = write_plan(root / "artifacts" / "v2")
            legacy = root / "artifacts" / "legacy"
            legacy.mkdir()
            (legacy / "plan.json").write_text(
                json.dumps({"schema_version": 1, "plan_id": "plan_legacy"}), encoding="utf-8"
            )
            (legacy / "manifest.json").write_text("not json", encoding="utf-8")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                side_effect=AssertionError("inventory opened a delta"),
            ):
                plans = service.list_plans()
                dashboard = service.dashboard()
                namespaces = service.list_namespaces()

        self.assertEqual([item.plan_id for item in plans.items], [plan_id])
        self.assertEqual(plans.items[0].payload_verification, "not_checked")
        self.assertEqual(dashboard.plan_count, 1)
        self.assertEqual(namespaces.total, 1)
        self.assertEqual(plans.errors, [])

    def test_summary_qualification_recomputes_plan_only_identity_and_errors_on_schema3(self) -> None:
        from buoy_search.plan_artifacts import artifact_identity, stable_hash

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, output = write_plan(root / "template")
            template = json.loads((output / "plan.json").read_text(encoding="utf-8"))
            artifacts = root / "artifacts"
            cases = []

            bad_hash = json.loads(json.dumps(template))
            bad_hash["artifact_hash"] = "f" * 64
            cases.append(bad_hash)

            bad_plan_id = json.loads(json.dumps(template))
            bad_plan_id["plan_id"] = "plan_" + "f" * 16
            cases.append(bad_plan_id)

            bad_source_identity = json.loads(json.dumps(template))
            bad_source_identity["source"]["uri"] = "https://example.org/docs"
            bad_source_identity["artifact_hash"] = stable_hash(artifact_identity(bad_source_identity))
            bad_source_identity["plan_id"] = f"plan_{bad_source_identity['artifact_hash'][:16]}"
            cases.append(bad_source_identity)

            bad_counts = json.loads(json.dumps(template))
            bad_counts["diff"]["rows_to_upsert"] += 1
            bad_counts["artifact_hash"] = stable_hash(artifact_identity(bad_counts))
            bad_counts["plan_id"] = f"plan_{bad_counts['artifact_hash'][:16]}"
            cases.append(bad_counts)

            bad_first_apply = json.loads(json.dumps(template))
            bad_first_apply["diff"]["first_apply"] = False
            bad_first_apply["artifact_hash"] = stable_hash(artifact_identity(bad_first_apply))
            bad_first_apply["plan_id"] = f"plan_{bad_first_apply['artifact_hash'][:16]}"
            cases.append(bad_first_apply)

            schema3 = json.loads(json.dumps(template))
            schema3["schema_version"] = 3
            cases.append(schema3)

            for index, plan in enumerate(cases):
                directory = artifacts / f"invalid-{index}"
                directory.mkdir(parents=True)
                (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                (directory / "delta.duckdb").write_bytes(b"must-not-open")

            legacy = artifacts / "legacy"
            legacy.mkdir(parents=True)
            (legacy / "plan.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            (legacy / "delta.duckdb").write_bytes(b"must-not-open")

            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                side_effect=AssertionError("summary qualification opened a delta"),
            ):
                inventory = LocalInventoryService(
                    artifacts_root=artifacts, state_root=root / "state"
                ).list_plans(limit=100)

        self.assertEqual(inventory.total, 0)
        self.assertEqual(len(inventory.errors), len(cases))
        self.assertEqual({error.code for error in inventory.errors}, {"malformed_plan"})

    def test_missing_or_symlinked_delta_isolated_as_safe_summary_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, output = write_plan(root / "artifacts" / "valid")
            missing = root / "artifacts" / "missing"
            missing.mkdir()
            (missing / "plan.json").write_bytes((output / "plan.json").read_bytes())
            linked = root / "artifacts" / "linked"
            linked.mkdir()
            (linked / "plan.json").write_bytes((output / "plan.json").read_bytes())
            (linked / "delta.duckdb").symlink_to(output / "delta.duckdb")
            inventory = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            ).list_plans()

        self.assertEqual(inventory.total, 1)
        self.assertEqual(len(inventory.errors), 2)
        self.assertEqual({error.code for error in inventory.errors}, {"malformed_plan"})
        self.assertNotIn(str(root), json.dumps([error.__dict__ for error in inventory.errors]))

    def test_combined_review_loads_no_provider_model_or_source_specific_adapter(self) -> None:
        script = """
import sys
from pathlib import Path
from buoy_search.command_center_local import LocalInventoryService
service = LocalInventoryService(artifacts_root=Path(sys.argv[1]), state_root=Path(sys.argv[2]))
review = service.get_plan_review(sys.argv[3], chunk_limit=1, stale_limit=1)
if review.detail.summary.plan_id != sys.argv[3]:
    raise SystemExit('combined review returned the wrong plan')
forbidden = {
    'buoy_search.apply', 'buoy_search.bigquery_relation',
    'buoy_search.command_center_remote', 'buoy_search.duckdb_relation',
    'buoy_search.github_repo', 'buoy_search.planning_service',
    'buoy_search.retriever', 'buoy_search.snowflake_relation',
    'turbopuffer', 'sentence_transformers', 'transformers',
    'google.cloud.bigquery', 'snowflake.connector',
}
loaded = sorted(forbidden.intersection(sys.modules))
if loaded:
    raise SystemExit(','.join(loaded))
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root / "fixture")
            plan_id, _ = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    script,
                    str(root / "artifacts"),
                    str(root / "state"),
                    plan_id,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_selected_detail_fully_verifies_and_chunks_and_stale_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root)
            plan_id, _ = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            detail = service.get_plan(plan_id)
            chunks = service.list_plan_chunks(plan_id, limit=1, max_chars=8)
            stale = service.list_plan_stale_rows(plan_id, limit=1)

        self.assertEqual(detail.payload_verification, "verified")
        self.assertTrue(detail.applied_state_present)
        self.assertEqual(len(detail.applied_state_hash), 64)
        self.assertEqual(chunks.total, 1)
        self.assertEqual(chunks.items[0].action, "changed")
        self.assertTrue(chunks.items[0].truncated)
        self.assertEqual(len(chunks.items[0].content), 8)
        self.assertEqual(stale.total, 2)
        self.assertEqual(len(stale.items), 1)

    def test_selected_record_replacement_and_aba_fail_for_all_payload_routes(self) -> None:
        from buoy_search.plan_artifacts import verify_plan_artifacts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root)
            plan_id, output_a = write_plan(
                root / "artifacts" / "a", state=state, state_present=True
            )
            _, output_b = write_plan(
                root / "replacement", body="# Guide\n\nDifferent replacement content."
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            record = service._plan_record(plan_id)
            original_plan = (output_a / "plan.json").read_bytes()
            original_delta = (output_a / "delta.duckdb").read_bytes()
            replacement_plan = (output_b / "plan.json").read_bytes()
            replacement_delta = (output_b / "delta.duckdb").read_bytes()

            operations = (
                lambda: service.get_plan(plan_id),
                lambda: service.get_plan_review(
                    plan_id, chunk_limit=1, stale_limit=1
                ),
                lambda: service.list_plan_chunks(plan_id, limit=1),
                lambda: service.list_plan_stale_rows(plan_id, limit=1),
            )
            for operation in operations:
                with self.subTest(kind="replacement", operation=operation):
                    (output_a / "plan.json").write_bytes(replacement_plan)
                    (output_a / "delta.duckdb").write_bytes(replacement_delta)
                    with patch.object(service, "_plan_record", return_value=record):
                        with self.assertRaisesRegex(InventoryLookupError, "fully verified"):
                            operation()
                    (output_a / "plan.json").write_bytes(original_plan)
                    (output_a / "delta.duckdb").write_bytes(original_delta)

                with self.subTest(kind="aba", operation=operation):
                    def verify_replacement_then_restore(path, **kwargs):  # noqa: ANN001, ANN202
                        (output_a / "plan.json").write_bytes(replacement_plan)
                        (output_a / "delta.duckdb").write_bytes(replacement_delta)
                        try:
                            return verify_plan_artifacts(path, **kwargs)
                        finally:
                            (output_a / "plan.json").write_bytes(original_plan)
                            (output_a / "delta.duckdb").write_bytes(original_delta)

                    with patch.object(service, "_plan_record", return_value=record), patch(
                        "buoy_search.command_center_local._verify_plan_artifacts",
                        side_effect=verify_replacement_then_restore,
                    ):
                        with self.assertRaisesRegex(InventoryLookupError, "fully verified"):
                            operation()

    def test_all_payload_routes_reject_transient_identity_excluded_metadata_aba(self) -> None:
        from buoy_search.plan_artifacts import verify_plan_artifacts

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root)
            plan_id, output = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            record = service._plan_record(plan_id)
            plan_path = output / "plan.json"
            original_plan = plan_path.read_bytes()
            transient = json.loads(original_plan)
            transient["created_at"] = "2026-07-28T23:59:59+00:00"
            transient["originating_job_id"] = "planjob_" + "e" * 32
            transient_plan = json.dumps(transient).encode("utf-8")

            operations = (
                lambda: service.get_plan(plan_id),
                lambda: service.get_plan_review(
                    plan_id, chunk_limit=1, stale_limit=1
                ),
                lambda: service.list_plan_chunks(plan_id, limit=1),
                lambda: service.list_plan_stale_rows(plan_id, limit=1),
            )
            for operation in operations:
                def verify_transient_then_restore(path, **kwargs):  # noqa: ANN001, ANN202
                    plan_path.write_bytes(transient_plan)
                    try:
                        return verify_plan_artifacts(path, **kwargs)
                    finally:
                        plan_path.write_bytes(original_plan)

                with self.subTest(operation=operation), patch.object(
                    service, "_plan_record", return_value=record
                ), patch(
                    "buoy_search.command_center_local._verify_plan_artifacts",
                    side_effect=verify_transient_then_restore,
                ):
                    with self.assertRaisesRegex(InventoryLookupError, "fully verified"):
                        operation()

    def test_payload_routes_reconstruct_identity_excluded_metadata_after_cached_rewrite(self) -> None:
        import buoy_search.command_center_local as local_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, output = write_plan(root / "artifacts" / "plan")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            cached = service.list_plans().items[0]
            plan_path = output / "plan.json"
            plan_inode = plan_path.stat().st_ino
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            rewritten_created_at = "2026-07-27T23:59:59+00:00"
            rewritten_job_id = "planjob_" + "b" * 32
            plan["created_at"] = rewritten_created_at
            plan["originating_job_id"] = rewritten_job_id
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            self.assertEqual(plan_path.stat().st_ino, plan_inode)

            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                wraps=local_module._verify_plan_artifacts,
            ) as verify:
                detail = service.get_plan(plan_id)
                review = service.get_plan_review(plan_id)

        self.assertNotEqual(cached.created_at, rewritten_created_at)
        self.assertEqual(detail.summary.created_at, rewritten_created_at)
        self.assertEqual(detail.originating_job_id, rewritten_job_id)
        self.assertEqual(review.detail.summary.created_at, rewritten_created_at)
        self.assertEqual(review.detail.originating_job_id, rewritten_job_id)
        self.assertEqual(verify.call_count, 2)

    def test_selected_corrupt_delta_fails_without_breaking_summary_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, output = write_plan(root / "artifacts" / "plan")
            (output / "delta.duckdb").write_text("damaged", encoding="utf-8")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            self.assertEqual(service.list_plans().total, 1)
            for operation in (
                lambda: service.get_plan(plan_id),
                lambda: service.get_plan_review(plan_id),
            ):
                with self.subTest(operation=operation), self.assertRaisesRegex(
                    InventoryLookupError, "fully verified"
                ):
                    operation()

    def test_namespace_combines_summary_plan_and_compact_applied_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root)
            plan_id, _ = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            save_applied_state(state, state_root=root / "state")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            namespace = service.get_namespace("site-example-com-v1")
            dashboard = service.dashboard()

        self.assertEqual(namespace.summary.latest_plan_id, plan_id)
        self.assertEqual(namespace.summary.local_status, "pending_changes")
        self.assertEqual(namespace.summary.active_rows, 2)
        self.assertEqual(dashboard.plan_count, 1)
        self.assertEqual(dashboard.pending_namespace_count, 1)

    def test_namespace_error_status_uses_only_attributable_snapshot_errors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            attributable = (
                root
                / "state"
                / "state"
                / "error-site"
                / "error-namespace"
                / "state.duckdb"
            )
            attributable.parent.mkdir(parents=True)
            attributable.write_bytes(b"malformed state")
            unattributable = root / "state" / "state" / "not-a-namespace" / "state.duckdb"
            unattributable.parent.mkdir(parents=True)
            unattributable.write_bytes(b"malformed state")
            malformed_plan = root / "artifacts" / "fabricated-namespace"
            malformed_plan.mkdir(parents=True)
            (malformed_plan / "plan.json").write_text("{bad", encoding="utf-8")

            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            inventory = service.list_namespaces()
            errors = service.list_namespaces(local_status="error")

        self.assertEqual([item.namespace for item in inventory.items], ["error-namespace"])
        self.assertEqual([item.namespace for item in errors.items], ["error-namespace"])
        self.assertEqual(errors.items[0].local_status, "error")
        self.assertEqual(errors.total, 1)
        self.assertEqual(
            {error.code for error in inventory.errors},
            {"malformed_plan", "malformed_state"},
        )
        self.assertNotIn(
            "fabricated-namespace", [item.namespace for item in inventory.items]
        )
        self.assertNotIn(
            "not-a-namespace", [item.namespace for item in inventory.items]
        )

    def test_summary_maps_every_schema_v2_source_without_adapter_imports(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, template_output = write_plan(root / "template")
            template = json.loads((template_output / "plan.json").read_text(encoding="utf-8"))
            from buoy_search.plan_artifacts import (
                artifact_identity,
                namespace_candidate,
                site_id_for_url,
                stable_hash,
            )

            sources = [
                {"kind": "website", "uri": "https://example.com/docs", "title": "example.com", "attributes": {}},
                {"kind": "github_repo", "uri": "https://github.com/acme/docs", "title": "acme/docs", "attributes": {"repo_full_name": "acme/docs", "repo_owner": "acme", "repo_name": "docs", "repo_ref": "main", "commit_sha": "a" * 40, "repo_subdir": None}},
                {"kind": "local_file", "uri": "file://notes-source", "title": "notes.md", "attributes": {"filename": "notes.md", "extension": "md", "sha256": "b" * 64, "source_id": "notes-source"}},
                {"kind": "pdf", "uri": "pdf://guide-source", "title": "guide.pdf", "attributes": {"filename": "guide.pdf", "sha256": "c" * 64, "source_id": "guide-source"}},
                {"kind": "duckdb_relation", "uri": "duckdb://product-docs", "title": "product-docs (corpus.docs)", "attributes": {"database_backend": "duckdb", "database_source_id": "product-docs", "database_relation": "corpus.docs"}},
                {"kind": "bigquery_relation", "uri": "bigquery://product-docs", "title": "product-docs (source-project.corpus.docs)", "attributes": {"database_backend": "bigquery", "database_source_id": "product-docs", "database_relation": "source-project.corpus.docs"}},
                {"kind": "snowflake_relation", "uri": "snowflake://product-docs", "title": "product-docs (ANALYTICS.CORPUS.DOCS)", "attributes": {"database_backend": "snowflake", "database_source_id": "product-docs", "database_relation": "ANALYTICS.CORPUS.DOCS"}},
            ]
            artifacts = root / "artifacts"
            for index, source in enumerate(sources):
                directory = artifacts / str(index)
                directory.mkdir(parents=True)
                plan = json.loads(json.dumps(template))
                plan["source"] = source
                plan["site_id"] = site_id_for_url(source["uri"])
                plan["namespace"] = f"source-kind-{index}"
                plan["namespace_candidate"] = namespace_candidate(source["uri"])
                plan["artifact_hash"] = stable_hash(artifact_identity(plan))
                plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
                (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                (directory / "delta.duckdb").write_bytes(b"")
            with patch.dict("sys.modules", {"buoy_search.bigquery_relation": None, "buoy_search.snowflake_relation": None}):
                service = LocalInventoryService(
                    artifacts_root=artifacts, state_root=root / "state"
                )
                items = service.list_plans(limit=100).items
                plan_kind_counts = {
                    kind: service.list_plans(source_kind=kind).total
                    for kind in ("website", "github_repo", "document", "database", "unknown")
                }
                namespace_kind_counts = {
                    kind: service.list_namespaces(source_kind=kind).total
                    for kind in ("website", "github_repo", "document", "database", "unknown")
                }

        by_uri = {item.source.uri: item for item in items}
        self.assertEqual(len(by_uri), len(sources))
        self.assertEqual(
            plan_kind_counts,
            {"website": 1, "github_repo": 1, "document": 2, "database": 3, "unknown": 0},
        )
        self.assertEqual(
            namespace_kind_counts,
            {"website": 1, "github_repo": 1, "document": 2, "database": 3, "unknown": 0},
        )
        self.assertEqual(by_uri["https://github.com/acme/docs"].source.repository, "acme/docs")
        self.assertEqual(by_uri["file://notes-source"].source.filename, "notes.md")
        self.assertEqual(by_uri["pdf://guide-source"].source.filename, "guide.pdf")
        self.assertEqual(by_uri["duckdb://product-docs"].source.database_backend, "duckdb")
        self.assertFalse(by_uri["duckdb://product-docs"].source_activity.api_calls_occurred)
        self.assertTrue(by_uri["bigquery://product-docs"].source_activity.credentials_required)
        self.assertTrue(by_uri["snowflake://product-docs"].source_activity.api_calls_occurred)

    def test_managed_origin_and_source_are_read_from_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            job_id = "planjob_" + "a" * 32
            plan_id, _ = write_plan(
                root / "artifacts" / "managed", originating_job_id=job_id
            )
            detail = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            ).get_plan(plan_id)

        self.assertEqual(detail.originating_job_id, job_id)
        self.assertEqual(detail.summary.source.kind, "website")
        self.assertEqual(detail.summary.source.uri, "https://example.com/docs")
        self.assertEqual(detail.summary.source_activity.credentials_required, False)

    def test_namespace_plan_history_is_bounded_with_accurate_window_metadata(self) -> None:
        from buoy_search.plan_artifacts import artifact_identity, stable_hash

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, template_output = write_plan(root / "template")
            template = json.loads(
                (template_output / "plan.json").read_text(encoding="utf-8")
            )
            artifacts = root / "artifacts"
            for index in range(125):
                directory = artifacts / f"plan-{index:03d}"
                directory.mkdir(parents=True)
                plan = json.loads(json.dumps(template))
                plan["crawl_options"] = {"history_fixture": index}
                plan["created_at"] = f"2026-07-28T00:{index // 60:02d}:{index % 60:02d}+00:00"
                plan["artifact_hash"] = stable_hash(artifact_identity(plan))
                plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
                (directory / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
                (directory / "delta.duckdb").write_bytes(b"summary-only")
            service = LocalInventoryService(
                artifacts_root=artifacts, state_root=root / "state"
            )

            first = service.get_namespace("site-example-com-v1")
            middle = service.get_namespace(
                "site-example-com-v1", plan_offset=20, plan_limit=100
            )
            end = service.get_namespace(
                "site-example-com-v1", plan_offset=120, plan_limit=100
            )

        self.assertEqual(
            (first.plan_total, first.plan_offset, first.plan_limit), (125, 0, 20)
        )
        self.assertEqual(len(first.plans), 20)
        self.assertTrue(first.plans_truncated)
        self.assertEqual(len(middle.plans), 100)
        self.assertTrue(middle.plans_truncated)
        self.assertEqual(len(end.plans), 5)
        self.assertTrue(end.plans_truncated)
        self.assertEqual(
            [item.plan_id for item in middle.plans],
            [item.summary.plan_id for item in service._snapshot().plans[20:120]],
        )

    def test_combined_review_and_standalone_routes_each_verify_exactly_once(self) -> None:
        import buoy_search.command_center_local as local_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = changed_and_stale_state(root)
            plan_id, _ = write_plan(
                root / "artifacts" / "current", state=state, state_present=True
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                wraps=local_module._verify_plan_artifacts,
            ) as verify:
                review = service.get_plan_review(
                    plan_id,
                    chunk_offset=0,
                    chunk_limit=1,
                    max_chars=8,
                    stale_offset=1,
                    stale_limit=1,
                )
                self.assertEqual(verify.call_count, 1)
                self.assertEqual(
                    verify.call_args.kwargs,
                    {
                        "materialize": False,
                        "upsert_window": (0, 1),
                        "stale_window": (1, 1),
                    },
                )
                service.get_plan(plan_id)
                self.assertEqual(verify.call_count, 2)
                service.list_plan_chunks(plan_id, limit=1)
                self.assertEqual(verify.call_count, 3)
                service.list_plan_stale_rows(plan_id, limit=1)
                self.assertEqual(verify.call_count, 4)

        self.assertEqual(review.detail.summary.plan_id, plan_id)
        self.assertEqual(review.detail.payload_verification, "verified")
        self.assertEqual(review.chunks.total, 1)
        self.assertEqual(len(review.chunks.items[0].content), 8)
        self.assertEqual(review.stale_rows.total, 2)
        self.assertEqual(review.stale_rows.items[0].index, 1)

    def test_pagination_filters_and_review_windows_fail_before_verification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, _ = write_plan(root / "artifacts" / "plan")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts"
            ) as verify:
                for operation in (
                    lambda: service.list_plans(offset=-1),
                    lambda: service.list_plans(q="x" * 257),
                    lambda: service.list_plans(namespace="not/a/namespace"),
                    lambda: service.list_plans(source_kind="pdf"),
                    lambda: service.list_namespaces(source_kind="local_file"),
                    lambda: service.list_namespaces(local_status="broken"),
                    lambda: service.get_namespace(
                        "site-example-com-v1", plan_limit=101
                    ),
                    lambda: service.list_plan_chunks(plan_id, limit=101),
                    lambda: service.list_plan_chunks(plan_id, max_chars=20_001),
                    lambda: service.list_plan_stale_rows(plan_id, limit=0),
                    lambda: service.get_plan_review(plan_id, chunk_offset=-1),
                    lambda: service.get_plan_review(plan_id, chunk_limit=101),
                    lambda: service.get_plan_review(plan_id, stale_limit=0),
                    lambda: service.get_plan_review(plan_id, max_chars=20_001),
                ):
                    with self.subTest(operation=operation), self.assertRaises(
                        InventoryLookupError
                    ):
                        operation()
                verify.assert_not_called()

    def test_large_delta_review_is_windowed_and_deterministic(self) -> None:
        import duckdb

        queries: list[tuple[str, object]] = []
        limited_materializations: list[int] = []
        real_connect = duckdb.connect

        class TracingConnection:
            def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
                self.inner = real_connect(*args, **kwargs)
                self.last_sql = ""

            def __enter__(self):  # noqa: ANN204
                return self

            def __exit__(self, exc_type, exc, traceback):  # noqa: ANN001
                self.inner.close()

            def execute(self, sql, parameters=None):  # noqa: ANN001, ANN201
                self.last_sql = str(sql)
                queries.append((self.last_sql, parameters))
                if parameters is None:
                    self.inner.execute(sql)
                else:
                    self.inner.execute(sql, parameters)
                return self

            def fetchall(self):  # noqa: ANN201
                rows = self.inner.fetchall()
                if "FROM stale_rows ORDER BY ordinal LIMIT" in self.last_sql:
                    limited_materializations.append(len(rows))
                return rows

            def fetchone(self):  # noqa: ANN201
                return self.inner.fetchone()

            def fetchmany(self, size=None):  # noqa: ANN001, ANN201
                return self.inner.fetchmany() if size is None else self.inner.fetchmany(size)

            def __getattr__(self, name):  # noqa: ANN001, ANN204
                return getattr(self.inner, name)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_id, output = write_large_stale_plan(
                root / "artifacts", row_count=100_000
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            started = time.perf_counter()
            with patch(
                "buoy_search.plan_artifacts.duckdb.connect", side_effect=TracingConnection
            ) as connect:
                last = service.list_plan_stale_rows(plan_id, offset=99_990, limit=10)
            elapsed = time.perf_counter() - started

        self.assertEqual(connect.call_count, 1)
        self.assertEqual(Path(connect.call_args.args[0]), output / "delta.duckdb")
        self.assertEqual(connect.call_args.kwargs, {"read_only": True})
        self.assertIn(
            (
                "SELECT * FROM stale_rows ORDER BY ordinal LIMIT ? OFFSET ?",
                [10, 99_990],
            ),
            queries,
        )
        self.assertEqual(limited_materializations, [10])
        self.assertEqual(last.total, 100_000)
        self.assertEqual([row.index for row in last.items], list(range(99_990, 100_000)))
        self.assertEqual(last.items[-1].row_id, f"ts_{99_999:032x}")
        self.assertLess(elapsed, 30.0)

    def test_delta_window_query_uses_bound_limit_and_offset(self) -> None:
        from buoy_search.plan_artifacts import _read_stale_window

        connection = MagicMock()
        connection.execute.return_value.fetchall.return_value = []
        self.assertEqual(_read_stale_window(connection, (99_990, 10)), [])
        connection.execute.assert_called_once_with(
            "SELECT * FROM stale_rows ORDER BY ordinal LIMIT ? OFFSET ?", [10, 99_990]
        )

    def test_many_summary_inventory_filters_before_pagination_and_reuses_snapshot(self) -> None:
        import buoy_search.command_center_local as local_module

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, output = write_plan(root / "template")
            template = json.loads((output / "plan.json").read_text(encoding="utf-8"))
            artifacts = root / "artifacts"
            from buoy_search.plan_artifacts import artifact_identity, stable_hash

            from buoy_search.command_center_local import MAX_PLAN_JSON_BYTES
            import os

            for index in range(1_000):
                directory = artifacts / f"plan-{index:04d}"
                directory.mkdir(parents=True)
                plan = json.loads(json.dumps(template))
                plan["namespace"] = f"fixture-{index:04d}"
                plan["crawl_options"] = {"inventory_fixture": index}
                plan["artifact_hash"] = stable_hash(artifact_identity(plan))
                plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
                payload = json.dumps(plan, sort_keys=True, separators=(",", ":"))
                payload += " " * (MAX_PLAN_JSON_BYTES - len(payload.encode("utf-8")))
                (directory / "plan.json").write_text(payload, encoding="utf-8")
                self.assertEqual((directory / "plan.json").stat().st_size, MAX_PLAN_JSON_BYTES)
                (directory / "delta.duckdb").write_bytes(b"")
            service = LocalInventoryService(
                artifacts_root=artifacts, state_root=root / "state"
            )
            original_open = os.open

            def reject_delta_open(path, *args, **kwargs):  # noqa: ANN001, ANN202 - spy.
                if str(path).endswith("delta.duckdb"):
                    raise AssertionError("inventory opened delta")
                return original_open(path, *args, **kwargs)

            started = time.perf_counter()
            with patch(
                "buoy_search.command_center_local._verify_plan_artifacts",
                side_effect=AssertionError("inventory verified delta"),
            ), patch(
                "buoy_search.applied_state.duckdb.connect",
                side_effect=AssertionError("inventory connected to DuckDB"),
            ), patch(
                "buoy_search.command_center_local.os.open", side_effect=reject_delta_open
            ), patch(
                "buoy_search.command_center_local._discover_plans",
                wraps=local_module._discover_plans,
            ) as scans:
                inventory = service.list_plans(limit=100)
                expected = [
                    record.summary.plan_id
                    for record in service._snapshot().plans
                    if "fixture-09" in record.summary.namespace
                ]
                filtered = service.list_plans(q="FIXTURE-09", offset=10, limit=15)
                exact = service.list_plans(namespace="fixture-0999")
                by_uri = service.list_plans(q="EXAMPLE.COM/DOCS", limit=100)
                by_kind = service.list_plans(source_kind="website", limit=100)
                missing_kind = service.list_plans(source_kind="unknown")
                namespaces = service.list_namespaces(
                    q="FIXTURE-09", offset=10, limit=15
                )
                namespace_kind = service.list_namespaces(
                    source_kind="website", limit=100
                )
                namespace_status = service.list_namespaces(
                    local_status="pending_changes", limit=100
                )
                dashboard = service.dashboard()
            elapsed = time.perf_counter() - started

        self.assertEqual(scans.call_count, 1)
        self.assertEqual(inventory.total, 1_000)
        self.assertEqual(len(inventory.items), 100)
        self.assertEqual(filtered.total, 100)
        self.assertEqual(
            [item.plan_id for item in filtered.items], expected[10:25]
        )
        self.assertEqual(exact.total, 1)
        self.assertEqual(exact.items[0].namespace, "fixture-0999")
        self.assertEqual(by_uri.total, 1_000)
        self.assertEqual(by_kind.total, 1_000)
        self.assertEqual(missing_kind.total, 0)
        self.assertEqual(namespaces.total, 100)
        self.assertEqual(len(namespaces.items), 15)
        self.assertEqual(namespace_kind.total, 1_000)
        self.assertEqual(namespace_status.total, 1_000)
        self.assertEqual(dashboard.plan_count, 1_000)
        self.assertLess(elapsed, 10.0)


if __name__ == "__main__":
    unittest.main()
