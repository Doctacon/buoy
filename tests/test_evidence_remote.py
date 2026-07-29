from __future__ import annotations

import copy
from pathlib import Path
from types import SimpleNamespace
import resource
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import duckdb

from buoy_search.applied_state import (
    AppliedStateRow,
    acquire_namespace_apply_lock,
    build_applied_state,
    save_applied_state,
)
from buoy_search.catalog import NamespaceCard
from buoy_search.evidence_remote import (
    CATALOG_SCHEMA,
    LEDGER_ATTRIBUTES,
    LEDGER_SCHEMA,
    RECONCILIATION_ATTRIBUTES,
    _query_rows,
    create_evidence_snapshot,
    estimate_evidence_snapshot,
    verify_evidence_snapshot,
)
from buoy_search.evidence_snapshot import EvidenceSnapshotError

REGION = "gcp-us-central1"
MODEL = "BAAI/bge-small-en-v1.5"
PLAN = "plan_0123456789abcdef"
APPLY = "apply_0123456789abcdef"


def state_row(index: int, status: str = "active") -> AppliedStateRow:
    return AppliedStateRow(
        row_id=f"ts_{index:032x}",
        canonical_url=f"https://example.com/{index}",
        page_hash=f"p{index:063d}",
        chunk_hash=f"c{index:063d}",
        embedding_text_hash=f"e{index:063d}",
        plan_id=PLAN,
        applied_at="2026-07-29T00:00:00+00:00",
        status=status,  # type: ignore[arg-type]
    )


def remote_row(row: AppliedStateRow) -> dict[str, object]:
    return {
        "id": row.row_id,
        "canonical_url": row.canonical_url,
        "page_hash": row.page_hash,
        "chunk_hash": row.chunk_hash,
        "embedding_text_hash": row.embedding_text_hash,
        "plan_id": row.plan_id,
        "applied_at": row.applied_at,
        "content": "must never be requested",
        "vector": [1.0],
        "title": "not requested",
    }


def card(namespace: str, site_id: str) -> NamespaceCard:
    return NamespaceCard(
        namespace=namespace,
        enabled=True,
        created_at="2026-07-29T00:00:00+00:00",
        updated_at="2026-07-29T00:00:00+00:00",
        card_revision=f"revision-{namespace}",
        last_plan_id=PLAN,
        last_apply_id=APPLY,
        source_kind="website",
        source_uri="https://example.com/",
        site_id=site_id,
        title=namespace,
        summary="summary",
        aliases=[], tags=[], semantic_origin="generated", region=REGION,
        embedding_model=MODEL, embedding_precision="float32", vector_dimensions=384,
        plan_schema_version=2, ranking_mode="page", ranking_profile="none",
        ranking_pool=20, ranking_aggregation="max", routing_model=MODEL,
        routing_model_revision="route-revision", semantic_hash="s" * 64,
        vector=[], vector_hash="v" * 64,
    )


class FakeNamespace:
    def __init__(self, client: "FakeClient", name: str) -> None:
        self.client = client
        self.name = name

    @property
    def data(self) -> dict[str, object]:
        return self.client.data.setdefault(self.name, {"exists": False, "rows": {}, "schema": {}, "parent": None})

    def exists(self, **kwargs):  # noqa: ANN001
        del kwargs
        return bool(self.data["exists"])

    def metadata(self, **kwargs):  # noqa: ANN001
        del kwargs
        if not self.data["exists"]:
            raise RuntimeError("not found")
        result = {
            "schema": {"id": {"type": "string"}, **copy.deepcopy(self.data["schema"])},
            "approx_row_count": len(self.data["rows"]),
            "approx_logical_bytes": self.data.get("approx_logical_bytes", len(self.data["rows"]) * 100),
            "created_at": self.data.get("created_at", "2026-07-29T00:00:00+00:00"),
            "last_write_at": self.data.get("last_write_at", "2026-07-29T00:00:01+00:00"),
        }
        if self.data.get("parent") is not None:
            result["branching"] = {"parent": self.data["parent"]}
        if self.data.get("sharded"):
            result["sharding"] = {"num_shards": 2}
        return result

    def branch_from(self, *, source_namespace: str, **kwargs):  # noqa: ANN001
        del kwargs
        self.client.branch_calls.append((self.name, source_namespace))
        if self.client.fail_branch == source_namespace:
            raise RuntimeError("branch failed")
        if self.data["exists"]:
            raise RuntimeError("exists")
        source = self.client.data[source_namespace]
        self.client.data[self.name] = {
            "exists": True,
            "rows": copy.deepcopy(source["rows"]),
            "schema": copy.deepcopy(source["schema"]),
            "parent": source_namespace,
            "created_at": "2026-07-29T00:01:00+00:00",
            "last_write_at": "2026-07-29T00:01:00+00:00",
            "approx_logical_bytes": source["approx_logical_bytes"],
        }
        return {"rows_affected": 0}

    def query(self, **kwargs):  # noqa: ANN001
        self.client.query_calls.append((self.name, copy.deepcopy(kwargs)))
        if self.client.mutate_branch_on_query and self.data.get("parent") is not None:
            self.data["last_write_at"] = "2026-07-29T10:00:00+00:00"
        rows = list(self.data["rows"].values())

        def matches(row, expression):  # noqa: ANN001
            if expression is None:
                return True
            if expression[0] == "And":
                return all(matches(row, item) for item in expression[1])
            field, operation, value = expression
            if operation == "Eq":
                return row.get(field) == value
            if operation == "Gt":
                return row.get(field) > value
            raise AssertionError(expression)

        rows = [row for row in rows if matches(row, kwargs.get("filters"))]
        field, direction = kwargs.get("rank_by", ("id", "asc"))
        rows.sort(key=lambda item: item[field], reverse=direction == "desc")
        limit = kwargs.get("limit", kwargs.get("top_k", 10))
        include = kwargs.get("include_attributes", [])
        projected = [
            {"id": item["id"], **{name: item[name] for name in include if name in item}}
            for item in rows[:limit]
        ]
        return {
            "rows": projected,
            "billing": {
                "billable_logical_bytes_queried": 100,
                "billable_logical_bytes_returned": len(projected) * 10,
            },
        }

    def write(self, **kwargs):  # noqa: ANN001
        self.client.write_calls.append((self.name, copy.deepcopy(kwargs)))
        if self.name.startswith("site-") or self.data.get("parent") is not None:
            raise AssertionError("source/evidence branch write attempted")
        if self.client.fail_catalog and self.name == "buoy-evidence-catalog-v1":
            raise RuntimeError("catalog failed")
        self.data["exists"] = True
        if "schema" in kwargs:
            self.data["schema"] = copy.deepcopy(kwargs["schema"])
        affected = 0
        affected_ids = []
        for row in kwargs.get("upsert_rows", []):
            if kwargs.get("upsert_condition") == ("id", "Eq", None) and row["id"] in self.data["rows"]:
                continue
            self.data["rows"][row["id"]] = copy.deepcopy(row)
            affected += 1
            affected_ids.append(row["id"])
        if self.client.bad_ledger_count and self.name.startswith("buoy-evidence-ledger-"):
            affected += 1
        self.data["last_write_at"] = "2026-07-29T00:02:00+00:00"
        return {"rows_affected": affected, "upserted_ids": affected_ids}

    def delete_all(self, **kwargs):  # noqa: ANN001
        del kwargs
        self.client.delete_calls.append(self.name)
        self.client.data[self.name] = {"exists": False, "rows": {}, "schema": {}, "parent": None}
        return {"rows_affected": 0}


class FakeClient:
    def __init__(self) -> None:
        self.data: dict[str, dict[str, object]] = {}
        self.branch_calls: list[tuple[str, str]] = []
        self.write_calls: list[tuple[str, dict[str, object]]] = []
        self.query_calls: list[tuple[str, dict[str, object]]] = []
        self.delete_calls: list[str] = []
        self.fail_branch: str | None = None
        self.fail_catalog = False
        self.bad_ledger_count = False
        self.mutate_branch_on_query = False

    def namespace(self, namespace: str) -> FakeNamespace:
        return FakeNamespace(self, namespace)

    def add_source(self, namespace: str, rows: list[dict[str, object]], *, logical_bytes: int = 1000, sharded: bool = False) -> None:
        schema = {
            "vector": {"type": "[384]f16", "ann": True},
            **{name: {"type": "string"} for name in RECONCILIATION_ATTRIBUTES},
        }
        self.data[namespace] = {
            "exists": True,
            "rows": {str(row["id"]): copy.deepcopy(row) for row in rows},
            "schema": schema,
            "parent": None,
            "created_at": "2026-07-28T00:00:00+00:00",
            "last_write_at": "2026-07-29T00:00:00+00:00",
            "approx_logical_bytes": logical_bytes,
            "sharded": sharded,
        }


class LeanScaleNamespace(FakeNamespace):
    """Keep provider state but avoid retaining duplicate fake request payloads."""

    def branch_from(self, *, source_namespace: str, **kwargs):  # noqa: ANN001
        del kwargs
        self.client.branch_calls.append((self.name, source_namespace))
        source = self.client.data[source_namespace]
        self.client.data[self.name] = {
            "exists": True,
            "rows": source["rows"],
            "schema": copy.deepcopy(source["schema"]),
            "parent": source_namespace,
            "created_at": "2026-07-29T00:01:00+00:00",
            "last_write_at": "2026-07-29T00:01:00+00:00",
            "approx_logical_bytes": source["approx_logical_bytes"],
        }
        return {"rows_affected": 0}

    def write(self, **kwargs):  # noqa: ANN001
        if self.name.startswith("site-") or self.data.get("parent") is not None:
            raise AssertionError("source/evidence branch write attempted")
        self.data["exists"] = True
        if "schema" in kwargs:
            self.data["schema"] = copy.deepcopy(kwargs["schema"])
        affected = []
        for row in kwargs.get("upsert_rows", []):
            if kwargs.get("upsert_condition") == ("id", "Eq", None) and row["id"] in self.data["rows"]:
                continue
            self.data["rows"][row["id"]] = row
            affected.append(row["id"])
        self.data["last_write_at"] = "2026-07-29T00:02:00+00:00"
        if self.name.startswith("buoy-evidence-ledger-"):
            self.client.ledger_call_count += 1
        elif self.name == "buoy-evidence-catalog-v1":
            self.client.catalog_call_count += 1
        return {"rows_affected": len(affected), "upserted_ids": affected}


class LeanScaleClient(FakeClient):
    def __init__(self) -> None:
        super().__init__()
        self.ledger_call_count = 0
        self.catalog_call_count = 0

    def namespace(self, namespace: str) -> LeanScaleNamespace:
        return LeanScaleNamespace(self, namespace)


def save_state(root: Path, namespace: str, site_id: str, rows: list[AppliedStateRow]) -> None:
    save_applied_state(
        build_applied_state(
            site_id=site_id,
            namespace=namespace,
            base_url="https://example.com/",
            last_plan_id=PLAN,
            last_apply_id=APPLY,
            rows=rows,
            updated_at="2026-07-29T00:00:00+00:00",
        ),
        state_root=root,
    )


def reader_for(cards: list[NamespaceCard]):  # noqa: ANN201
    def reader(client, *, region, compatibility):  # noqa: ANN001
        del client, region, compatibility
        return SimpleNamespace(eligible_cards=tuple(cards))
    return reader


class EvidenceRemoteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "state-root"
        self.out = self.root / "out"
        self.rows = [state_row(1), state_row(2, "retained_stale"), state_row(3, "deleted")]
        save_state(self.state, "site-one-v1", "one", self.rows)
        self.client = FakeClient()
        self.client.add_source("site-one-v1", [remote_row(self.rows[0]), remote_row(self.rows[1])], logical_bytes=4096)
        self.cards = [card("site-one-v1", "one")]
        self.reader = reader_for(self.cards)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def kwargs(self) -> dict[str, object]:
        return {
            "namespaces": ["site-one-v1"],
            "state_root": self.state,
            "region": REGION,
            "embedding_model": MODEL,
            "embedding_precision": "float32",
            "catalog_reader": self.reader,
        }

    def test_estimate_is_exactly_no_write_and_creates_no_artifact(self) -> None:
        result = estimate_evidence_snapshot(self.client, **self.kwargs())
        self.assertEqual(result["local_ledger_rows"], 3)
        self.assertEqual(result["approximate_remote_logical_bytes"], 4096)
        self.assertTrue(result["would_pass_limits"])
        self.assertFalse(result["remote_writes_occurred"])
        self.assertEqual(self.client.write_calls, [])
        self.assertEqual(self.client.branch_calls, [])
        self.assertFalse(self.out.exists())

    def test_snapshot_branches_ledgers_finalizes_and_verifies_without_local_state(self) -> None:
        result = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertEqual(result["active_rows"], 1)
        self.assertEqual(result["retained_stale_rows"], 1)
        self.assertEqual(result["deleted_rows"], 1)
        self.assertEqual(result["branch_create_count"], 1)
        self.assertFalse(result["local_full_corpus_written"])
        manifest = Path(str(result["local_manifest_path"]))
        self.assertEqual([path.name for path in manifest.parent.iterdir()], ["snapshot.json"])
        self.assertLess(manifest.stat().st_size, 256 * 1024)
        branch_name = result["branch_namespaces"][0]
        ledger_name = result["ledger_namespace"]
        ledger_rows = list(self.client.data[ledger_name]["rows"].values())
        self.assertEqual(len(ledger_rows), 3)
        self.assertFalse(any("content" in row or "vector" in row or "title" in row for row in ledger_rows))
        self.assertFalse(any(name == "site-one-v1" or name == branch_name for name, _ in self.client.write_calls))
        requested = [attrs for name, call in self.client.query_calls if name == branch_name for attrs in call.get("include_attributes", [])]
        self.assertNotIn("content", requested)
        self.assertNotIn("vector", requested)
        # Verification is remote-only: remove all local state first.
        for path in sorted(self.state.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        verified = verify_evidence_snapshot(self.client, snapshot_id=str(result["snapshot_id"]), manifest_path=manifest)
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["ledger_row_count"], 3)
        write_count = len(self.client.write_calls)
        verify_evidence_snapshot(self.client, snapshot_id=str(result["snapshot_id"]))
        self.assertEqual(len(self.client.write_calls), write_count)

    def test_identical_snapshot_reuses_completed_remote_state(self) -> None:
        first = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        first_branches = len(self.client.branch_calls)
        first_ledger_writes = len([name for name, _ in self.client.write_calls if name.startswith("buoy-evidence-ledger-")])
        second = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertTrue(second["reused_snapshot"])
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(len(self.client.branch_calls), first_branches)
        self.assertEqual(len([name for name, _ in self.client.write_calls if name.startswith("buoy-evidence-ledger-")]), first_ledger_writes)

    def test_sharded_and_limits_fail_before_branch_creation(self) -> None:
        self.client.data["site-one-v1"]["sharded"] = True
        with self.assertRaisesRegex(EvidenceSnapshotError, "sharded"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertEqual(self.client.branch_calls, [])
        self.client.data["site-one-v1"]["sharded"] = False
        estimate = estimate_evidence_snapshot(
            self.client, maximum_rows=2, **self.kwargs()
        )
        self.assertFalse(estimate["would_pass_limits"])
        self.assertIn("maximum-rows", str(estimate["limit_error"]))
        with self.assertRaisesRegex(EvidenceSnapshotError, "maximum-rows"):
            create_evidence_snapshot(self.client, out_root=self.out, maximum_rows=2, **self.kwargs())
        with self.assertRaisesRegex(EvidenceSnapshotError, "maximum-remote-logical-bytes"):
            create_evidence_snapshot(self.client, out_root=self.out, maximum_remote_logical_bytes=100, **self.kwargs())
        self.assertEqual(self.client.branch_calls, [])

    def test_reconciliation_failure_cleans_only_current_internal_namespaces(self) -> None:
        self.client.data["site-one-v1"]["rows"][self.rows[0].row_id]["page_hash"] = "wrong"
        self.client.data["preexisting"] = {"exists": True, "rows": {}, "schema": {}, "parent": None}
        with self.assertRaisesRegex(EvidenceSnapshotError, "page_hash_mismatch"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertIn(self.client.branch_calls[0][0], self.client.delete_calls)
        ledger = next(name for name in self.client.delete_calls if name.startswith("buoy-evidence-ledger-"))
        self.assertIn(ledger, self.client.delete_calls)
        self.assertNotIn("preexisting", self.client.delete_calls)
        self.assertFalse(any(name == "buoy-evidence-catalog-v1" for name, _ in self.client.write_calls))

    def test_ledger_count_mismatch_and_catalog_failure_cleanup(self) -> None:
        self.client.bad_ledger_count = True
        with self.assertRaisesRegex(EvidenceSnapshotError, "affected"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertTrue(self.client.delete_calls)

        self.client = FakeClient()
        self.client.add_source("site-one-v1", [remote_row(self.rows[0]), remote_row(self.rows[1])], logical_bytes=4096)
        self.client.fail_catalog = True
        with self.assertRaisesRegex(EvidenceSnapshotError, "catalog finalization"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertEqual(len(self.client.delete_calls), 2)

    def test_verify_detects_branch_and_ledger_mutation(self) -> None:
        result = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        branch = str(result["branch_namespaces"][0])
        self.client.data[branch]["last_write_at"] = "2026-07-29T09:00:00+00:00"
        with self.assertRaisesRegex(EvidenceSnapshotError, "metadata changed"):
            verify_evidence_snapshot(self.client, snapshot_id=str(result["snapshot_id"]))
        self.client.data[branch]["last_write_at"] = "2026-07-29T00:01:00+00:00"
        ledger = str(result["ledger_namespace"])
        first = next(iter(self.client.data[ledger]["rows"].values()))
        first["page_hash"] = "mutated"
        with self.assertRaisesRegex(EvidenceSnapshotError, "ledger hash"):
            verify_evidence_snapshot(self.client, snapshot_id=str(result["snapshot_id"]))

    def test_multi_namespace_snapshot_creates_one_branch_per_sorted_source(self) -> None:
        second_rows = [state_row(10)]
        save_state(self.state, "site-two-v1", "two", second_rows)
        self.client.add_source("site-two-v1", [remote_row(second_rows[0])], logical_bytes=2048)
        cards = [*self.cards, card("site-two-v1", "two")]
        result = create_evidence_snapshot(
            self.client,
            namespaces=["site-two-v1", "site-one-v1"],
            state_root=self.state,
            region=REGION,
            embedding_model=MODEL,
            embedding_precision="float32",
            out_root=self.out,
            catalog_reader=reader_for(cards),
        )
        self.assertEqual(result["namespace_count"], 2)
        self.assertEqual([source for _, source in self.client.branch_calls], ["site-one-v1", "site-two-v1"])
        self.assertEqual(result["approximate_remote_logical_bytes"], 6144)

    def test_second_branch_failure_cleans_first_and_releases_all_locks(self) -> None:
        second_rows = [state_row(10)]
        save_state(self.state, "site-two-v1", "two", second_rows)
        self.client.add_source("site-two-v1", [remote_row(second_rows[0])])
        self.client.fail_branch = "site-two-v1"
        with self.assertRaisesRegex(EvidenceSnapshotError, "branch create"):
            create_evidence_snapshot(
                self.client,
                namespaces=["site-one-v1", "site-two-v1"],
                state_root=self.state,
                region=REGION,
                embedding_model=MODEL,
                embedding_precision="float32",
                out_root=self.out,
                catalog_reader=reader_for([*self.cards, card("site-two-v1", "two")]),
            )
        self.assertEqual(len(self.client.delete_calls), 1)
        with acquire_namespace_apply_lock(site_id="one", namespace="site-one-v1", state_root=self.state):
            with acquire_namespace_apply_lock(site_id="two", namespace="site-two-v1", state_root=self.state):
                pass

    def test_held_apply_lock_fails_before_remote_creation(self) -> None:
        with acquire_namespace_apply_lock(site_id="one", namespace="site-one-v1", state_root=self.state):
            with self.assertRaisesRegex(Exception, "apply is already in progress"):
                create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertEqual(self.client.branch_calls, [])
        self.assertEqual(self.client.write_calls, [])

    def test_existing_valid_incomplete_branch_is_reconciled_and_reused(self) -> None:
        first = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        branch = str(first["branch_namespaces"][0])
        self.client.data["buoy-evidence-catalog-v1"]["rows"].clear()
        ledger = str(first["ledger_namespace"])
        self.client.data[ledger] = {"exists": False, "rows": {}, "schema": {}, "parent": None}
        second = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertFalse(second["reused_snapshot"])
        self.assertEqual(second["branch_reuse_count"], 1)
        self.assertEqual(second["branch_create_count"], 0)
        self.assertEqual(len(self.client.branch_calls), 1)
        self.assertNotIn(branch, self.client.delete_calls)

    def test_existing_wrong_parent_branch_is_never_deleted(self) -> None:
        first = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        branch = str(first["branch_namespaces"][0])
        catalog_rows = self.client.data["buoy-evidence-catalog-v1"]["rows"]
        catalog_rows.clear()
        self.client.data[branch]["parent"] = "site-wrong-v1"
        with self.assertRaisesRegex(EvidenceSnapshotError, "collision"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertNotIn(branch, self.client.delete_calls)

    def test_branch_change_during_reconciliation_is_detected(self) -> None:
        self.client.mutate_branch_on_query = True
        with self.assertRaisesRegex(EvidenceSnapshotError, "changed during reconciliation"):
            create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        self.assertTrue(self.client.delete_calls)

    def test_ledger_writes_are_bounded_batches(self) -> None:
        rows = [state_row(index) for index in range(2501)]
        with tempfile.TemporaryDirectory() as temporary:
            state_root = Path(temporary) / "state"
            out = Path(temporary) / "out"
            save_state(state_root, "site-batch-v1", "batch", rows)
            client = FakeClient()
            client.add_source("site-batch-v1", [remote_row(value) for value in rows])
            result = create_evidence_snapshot(
                client,
                namespaces=["site-batch-v1"],
                state_root=state_root,
                region=REGION,
                embedding_model=MODEL,
                embedding_precision="float32",
                out_root=out,
                catalog_reader=reader_for([card("site-batch-v1", "batch")]),
            )
        ledger_writes = [
            call for name, call in client.write_calls if name.startswith("buoy-evidence-ledger-")
        ]
        self.assertEqual([len(call["upsert_rows"]) for call in ledger_writes], [1000, 1000, 501])
        self.assertEqual(result["ledger_write_calls"], 3)

    def test_100000_row_snapshot_is_structurally_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state_root = root / "state"
            out = root / "out"
            database = save_applied_state(
                build_applied_state(
                    site_id="scale",
                    namespace="site-scale-v1",
                    base_url="https://example.com/",
                    last_plan_id=PLAN,
                    last_apply_id=APPLY,
                    rows=[],
                    updated_at="2026-07-29T00:00:00+00:00",
                ),
                state_root=state_root,
            ).database_path
            with duckdb.connect(str(database)) as connection:
                connection.execute(
                    """
                    INSERT INTO applied_rows
                    SELECT printf('ts_%032x', i), 'https://example.com/' || i,
                           repeat('p', 64), repeat('c', 64), repeat('e', 64),
                           ?, ?, 'active'
                    FROM range(100000) values(i)
                    """,
                    [PLAN, "2026-07-29T00:00:00+00:00"],
                )
            client = LeanScaleClient()
            schema = {
                "vector": {"type": "[384]f16", "ann": True},
                **{name: {"type": "string"} for name in RECONCILIATION_ATTRIBUTES},
            }
            source_rows: dict[str, dict[str, object]] = {}
            for index in range(100000):
                row_id = f"ts_{index:032x}"
                source_rows[row_id] = {
                    "id": row_id,
                    "canonical_url": f"https://example.com/{index}",
                    "page_hash": "p" * 64,
                    "chunk_hash": "c" * 64,
                    "embedding_text_hash": "e" * 64,
                    "plan_id": PLAN,
                    "applied_at": "2026-07-29T00:00:00+00:00",
                    "content": "never requested",
                    "vector": [1.0],
                }
            client.data["site-scale-v1"] = {
                "exists": True,
                "rows": source_rows,
                "schema": schema,
                "parent": None,
                "created_at": "2026-07-28T00:00:00+00:00",
                "last_write_at": "2026-07-29T00:00:00+00:00",
                "approx_logical_bytes": 50_000_000,
                "sharded": False,
            }
            before_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            started = time.monotonic()
            result = create_evidence_snapshot(
                client,
                namespaces=["site-scale-v1"],
                state_root=state_root,
                region=REGION,
                embedding_model=MODEL,
                embedding_precision="float32",
                out_root=out,
                catalog_reader=reader_for([card("site-scale-v1", "scale")]),
            )
            elapsed = time.monotonic() - started
            after_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            manifest_files = [
                path.name for path in (out / str(result["snapshot_id"])).iterdir()
            ]
        rss_delta = after_rss - before_rss
        rss_delta_bytes = rss_delta if sys.platform == "darwin" else rss_delta * 1024
        self.assertLess(rss_delta_bytes, 512 * 1024 * 1024)
        self.assertEqual(result["ledger_rows_written"], 100000)
        self.assertEqual(result["ledger_write_calls"], 100)
        self.assertEqual(result["branch_calls"], 1)
        self.assertEqual(result["approximate_remote_logical_bytes"], 50_000_000)
        self.assertLess(result["local_bytes_written"], 256 * 1024)
        self.assertGreaterEqual(elapsed, 0)
        self.assertEqual(client.ledger_call_count, 100)
        self.assertEqual(client.catalog_call_count, 1)
        branch_calls = [call for name, call in client.query_calls if name.startswith("buoy-evidence-branch-")]
        self.assertEqual(len(branch_calls), 11)
        self.assertTrue(all(call["limit"] == 10000 for call in branch_calls))
        self.assertFalse(
            any(
                forbidden in call.get("include_attributes", [])
                for _, call in client.query_calls
                for forbidden in ("content", "vector")
            )
        )
        self.assertEqual(manifest_files, ["snapshot.json"])

    def test_reconciliation_rejects_missing_extra_deleted_and_attribute_mismatches(self) -> None:
        mutations = {
            "missing active": lambda rows: rows.pop(self.rows[0].row_id),
            "missing retained stale": lambda rows: rows.pop(self.rows[1].row_id),
            "deleted present": lambda rows: rows.__setitem__(self.rows[2].row_id, remote_row(self.rows[2])),
            "unexpected": lambda rows: rows.__setitem__("ts_ffffffffffffffffffffffffffffffff", remote_row(state_row(999))),
            "url mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("canonical_url", "https://wrong.example/"),
            "page mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("page_hash", "wrong"),
            "chunk mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("chunk_hash", "wrong"),
            "embedding mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("embedding_text_hash", "wrong"),
            "plan mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("plan_id", "wrong"),
            "applied mismatch": lambda rows: rows[self.rows[0].row_id].__setitem__("applied_at", "wrong"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                client = FakeClient()
                client.add_source("site-one-v1", [remote_row(self.rows[0]), remote_row(self.rows[1])], logical_bytes=4096)
                mutate(client.data["site-one-v1"]["rows"])
                with self.assertRaises(EvidenceSnapshotError):
                    create_evidence_snapshot(
                        client,
                        out_root=self.out / name.replace(" ", "-"),
                        **(self.kwargs() | {"catalog_reader": self.reader}),
                    )

    def test_verify_rejects_missing_noncomplete_parent_row_and_catalog_drift(self) -> None:
        result = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        snapshot_id = str(result["snapshot_id"])
        branch = str(result["branch_namespaces"][0])
        catalog_row = next(iter(self.client.data["buoy-evidence-catalog-v1"]["rows"].values()))

        catalog_row["state"] = "building"
        with self.assertRaisesRegex(EvidenceSnapshotError, "not complete"):
            verify_evidence_snapshot(self.client, snapshot_id=snapshot_id)
        catalog_row["state"] = "complete"
        self.client.data[branch]["parent"] = "wrong"
        with self.assertRaisesRegex(EvidenceSnapshotError, "parent mismatch"):
            verify_evidence_snapshot(self.client, snapshot_id=snapshot_id)
        self.client.data[branch]["parent"] = "site-one-v1"

        removed = self.client.data[branch]["rows"].pop(self.rows[0].row_id)
        with self.assertRaisesRegex(EvidenceSnapshotError, "metadata changed|missing"):
            verify_evidence_snapshot(self.client, snapshot_id=snapshot_id)
        self.client.data[branch]["rows"][self.rows[0].row_id] = removed
        self.client.data[branch]["rows"]["ts_ffffffffffffffffffffffffffffffff"] = remote_row(state_row(999))
        with self.assertRaisesRegex(EvidenceSnapshotError, "metadata changed|unexpected"):
            verify_evidence_snapshot(self.client, snapshot_id=snapshot_id)
        self.client.data[branch]["rows"].pop("ts_ffffffffffffffffffffffffffffffff")
        catalog_row["snapshot_logical_hash"] = "wrong"
        with self.assertRaisesRegex(EvidenceSnapshotError, "logical hash"):
            verify_evidence_snapshot(self.client, snapshot_id=snapshot_id)

        empty = FakeClient()
        with self.assertRaisesRegex(EvidenceSnapshotError, "not found"):
            verify_evidence_snapshot(empty, snapshot_id=snapshot_id)

    def test_manifest_mismatch_and_post_completion_manifest_failure(self) -> None:
        result = create_evidence_snapshot(self.client, out_root=self.out, **self.kwargs())
        manifest = Path(str(result["local_manifest_path"]))
        manifest.write_text('{}', encoding="utf-8")
        with self.assertRaisesRegex(EvidenceSnapshotError, "manifest hash"):
            verify_evidence_snapshot(self.client, snapshot_id=str(result["snapshot_id"]), manifest_path=manifest)

        client = FakeClient()
        client.add_source("site-one-v1", [remote_row(self.rows[0]), remote_row(self.rows[1])], logical_bytes=4096)
        with patch("buoy_search.evidence_remote._write_manifest", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                create_evidence_snapshot(
                    client,
                    out_root=self.out / "failed",
                    **(self.kwargs() | {"catalog_reader": self.reader}),
                )
        catalog = client.data["buoy-evidence-catalog-v1"]
        self.assertEqual(len(catalog["rows"]), 1)
        self.assertEqual(client.delete_calls, [])

    def test_ordered_remote_paging_is_bounded_and_requests_no_content_or_vector(self) -> None:
        client = FakeClient()
        rows = [remote_row(state_row(index)) for index in range(10001)]
        client.add_source("site-many-v1", rows)
        metrics = {
            "remote_queries": 0,
            "billable_logical_bytes_queried": 0,
            "billable_logical_bytes_returned": 0,
        }
        values = list(_query_rows(client.namespace("site-many-v1"), include_attributes=RECONCILIATION_ATTRIBUTES, metrics=metrics))
        self.assertEqual(len(values), 10001)
        self.assertEqual(metrics["remote_queries"], 2)
        calls = [call for name, call in client.query_calls if name == "site-many-v1"]
        self.assertEqual([call["limit"] for call in calls], [10000, 10000])
        self.assertTrue(all("content" not in call["include_attributes"] and "vector" not in call["include_attributes"] for call in calls))


if __name__ == "__main__":
    unittest.main()
