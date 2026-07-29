from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import resource
import sys
import tempfile
import unittest

import duckdb

from buoy_search.applied_state import (
    AppliedStateRow,
    build_applied_state,
    save_applied_state,
    stream_applied_state_rows,
)
from buoy_search.catalog import NamespaceCard
from buoy_search.evidence_snapshot import (
    EvidenceSnapshotError,
    derive_snapshot_names,
    discover_local_sources,
    fingerprint_source,
    ledger_document_id,
    validate_namespace_selection,
)


def row(index: int, *, status: str = "active") -> AppliedStateRow:
    return AppliedStateRow(
        row_id=f"ts_{index:032x}",
        canonical_url=f"https://example.com/{index}",
        page_hash=f"p{index:063d}",
        chunk_hash=f"c{index:063d}",
        embedding_text_hash=f"e{index:063d}",
        plan_id="plan_0123456789abcdef",
        applied_at="2026-07-29T00:00:00+00:00",
        status=status,  # type: ignore[arg-type]
    )


def save_fixture(root: Path, namespace: str = "site-example-v1", rows=None) -> Path:  # noqa: ANN001
    state = build_applied_state(
        site_id="example",
        namespace=namespace,
        base_url="https://example.com/",
        last_plan_id="plan_0123456789abcdef",
        last_apply_id="apply_0123456789abcdef",
        rows=list(rows if rows is not None else [row(1)]),
        updated_at="2026-07-29T00:00:00+00:00",
    )
    return save_applied_state(state, state_root=root).database_path


def card(namespace: str = "site-example-v1", revision: str = "r1") -> NamespaceCard:
    return NamespaceCard(
        namespace=namespace,
        enabled=True,
        created_at="2026-07-29T00:00:00+00:00",
        updated_at="2026-07-29T00:00:00+00:00",
        card_revision=revision,
        last_plan_id="plan_0123456789abcdef",
        last_apply_id="apply_0123456789abcdef",
        source_kind="website",
        source_uri="https://example.com/",
        site_id="example",
        title="Example",
        summary="Example",
        aliases=[],
        tags=[],
        semantic_origin="generated",
        region="gcp-us-central1",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_precision="float32",
        vector_dimensions=384,
        plan_schema_version=2,
        ranking_mode="page",
        ranking_profile="none",
        ranking_pool=20,
        ranking_aggregation="max",
        routing_model="BAAI/bge-small-en-v1.5",
        routing_model_revision="revision",
        semantic_hash="s" * 64,
        vector=[],
        vector_hash="v" * 64,
    )


class SelectionTests(unittest.TestCase):
    def test_selection_is_explicit_unique_sorted_and_reserved_safe(self) -> None:
        self.assertEqual(validate_namespace_selection(["z", "a"]), ("a", "z"))
        for values in ([], ["a", "a"], ["bad*"], ["buoy-routing-catalog-v1"], ["buoy-evidence-ledger-x"]):
            with self.subTest(values=values), self.assertRaises(EvidenceSnapshotError):
                validate_namespace_selection(values)
        with self.assertRaises(EvidenceSnapshotError):
            validate_namespace_selection([str(index) for index in range(65)])

    def test_zero_row_completed_state_fails_before_remote_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            save_fixture(root, rows=[])
            with self.assertRaisesRegex(EvidenceSnapshotError, "empty remote ledger"):
                discover_local_sources(namespaces=["site-example-v1"], state_root=root)

    def test_missing_and_ambiguous_state_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "state").mkdir()
            with self.assertRaisesRegex(EvidenceSnapshotError, "missing"):
                discover_local_sources(namespaces=["site-example-v1"], state_root=root)
            save_fixture(root)
            second = build_applied_state(
                site_id="other",
                namespace="site-example-v1",
                base_url="https://other.example.com/",
                last_plan_id="plan_0123456789abcdef",
                last_apply_id="apply_0123456789abcdef",
                rows=[row(2)],
            )
            save_applied_state(second, state_root=root)
            with self.assertRaisesRegex(EvidenceSnapshotError, "ambiguous"):
                discover_local_sources(namespaces=["site-example-v1"], state_root=root)


class FingerprintTests(unittest.TestCase):
    def test_stream_and_identity_are_deterministic_and_state_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = save_fixture(
                root,
                rows=[row(1), row(2, status="retained_stale"), row(3, status="deleted")],
            )
            source = discover_local_sources(namespaces=["site-example-v1"], state_root=root)[0]
            first = fingerprint_source(source, state_root=root)
            second = fingerprint_source(source, state_root=root)
            self.assertEqual(first, second)
            self.assertEqual((first.active_rows, first.retained_stale_rows, first.deleted_rows), (1, 1, 1))
            names = derive_snapshot_names(
                region="gcp-us-central1", fingerprints=[first], cards={source.namespace: card()}
            )
            reversed_names = derive_snapshot_names(
                region="gcp-us-central1", fingerprints=list(reversed([first])), cards={source.namespace: card()}
            )
            self.assertEqual(names, reversed_names)
            self.assertTrue(all(len(value.encode()) <= 128 for value in [names.ledger_namespace, *names.branches.values()]))
            changed_card = replace(card(), card_revision="r2")
            self.assertNotEqual(
                names.snapshot_id,
                derive_snapshot_names(
                    region="gcp-us-central1",
                    fingerprints=[first],
                    cards={source.namespace: changed_card},
                ).snapshot_id,
            )
            with duckdb.connect(str(database)) as connection:
                connection.execute("UPDATE applied_rows SET page_hash = ? WHERE row_id = ?", ["x" * 64, row(1).row_id])
            changed_source = discover_local_sources(namespaces=["site-example-v1"], state_root=root)[0]
            changed = fingerprint_source(changed_source, state_root=root)
            self.assertNotEqual(first.logical_hash, changed.logical_hash)

    def test_ledger_id_is_bounded_and_deterministic(self) -> None:
        first = ledger_document_id(snapshot_id="evidence_1234567890abcdef", source_namespace="source", source_row_id="x" * 128)
        self.assertEqual(first, ledger_document_id(snapshot_id="evidence_1234567890abcdef", source_namespace="source", source_row_id="x" * 128))
        self.assertLessEqual(len(first.encode()), 64)

    def test_100000_rows_stream_with_fetchmany_and_bounded_objects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            database = save_fixture(root, rows=[])
            with duckdb.connect(str(database)) as connection:
                connection.execute(
                    """
                    INSERT INTO applied_rows
                    SELECT printf('ts_%032x', i),
                           'https://example.com/' || i,
                           repeat('p', 64), repeat('c', 64), repeat('e', 64),
                           'plan_0123456789abcdef', '2026-07-29T00:00:00+00:00', 'active'
                    FROM range(100000) AS values(i)
                    """
                )
            source = discover_local_sources(namespaces=["site-example-v1"], state_root=root)[0]
            before_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            fingerprint = fingerprint_source(source, state_root=root)
            after_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            self.assertEqual(fingerprint.total_rows, 100000)
            self.assertEqual(fingerprint.active_rows, 100000)
            rss_delta = after_rss - before_rss
            rss_delta_bytes = rss_delta if sys.platform == "darwin" else rss_delta * 1024
            self.assertLess(rss_delta_bytes, 96 * 1024 * 1024)
            with stream_applied_state_rows(database_path=database, state_root=root, batch_size=777) as stream:
                iterator = stream.rows
                self.assertFalse(isinstance(iterator, list))
                self.assertEqual(sum(1 for _ in iterator), 100000)


if __name__ == "__main__":
    unittest.main()
