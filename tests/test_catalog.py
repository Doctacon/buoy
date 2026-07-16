from __future__ import annotations

from dataclasses import replace
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import portalocker

from buoy_search.catalog import (
    CATALOG_SCHEMA_VERSION,
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    CardFields,
    CatalogError,
    NamespaceCard,
    canonical_text,
    card_passage_text,
    card_revision,
    card_to_dict,
    catalog_lock,
    commit_system_card,
    document_to_dict,
    generated_semantics,
    load_catalog,
    load_routing_embedder,
    merge_system_card,
    parse_card,
    parse_catalog,
    prepare_card,
    prepare_prospective_card,
    resolve_catalog_path,
    save_catalog,
    semantic_hash_for_fields,
    vector_hash,
)
from buoy_search.plan_artifacts import stable_hash, stable_json_dumps


UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)


class FixedEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or list(UNIT_VECTOR)
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001 - test protocol implementation.
        self.calls.append(list(texts))
        return [list(self.vector) for _ in texts]


class FailingEmbedder:
    def encode(self, texts):  # noqa: ANN001 - test sentinel.
        raise AssertionError(f"model must not be called: {texts}")


def fields(**overrides: object) -> CardFields:
    values: dict[str, object] = {
        "namespace": "site-example-v1",
        "enabled": True,
        "source_kind": "website",
        "source_uri": "https://example.com/docs",
        "site_id": "site-example",
        "title": "Example",
        "summary": "Example source.",
        "aliases": ["example docs", "example project"],
        "tags": ["docs", "python"],
        "semantic_origin": "manual",
        "region": "gcp-us-central1",
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "embedding_precision": "float32",
        "plan_schema_version": 1,
        "ranking_mode": "page",
        "ranking_profile": "none",
        "ranking_pool": 20,
        "ranking_aggregation": "max",
        "last_plan_id": None,
        "last_apply_id": None,
    }
    values.update(overrides)
    return CardFields(**values)  # type: ignore[arg-type]


def make_card(**overrides: object) -> NamespaceCard:
    field_names = set(CardFields.__dataclass_fields__)
    field_overrides = {key: value for key, value in overrides.items() if key in field_names}
    card = prepare_card(
        fields(**field_overrides),
        embedder=FixedEmbedder(),
        now=str(overrides.get("now", "2026-07-15T12:00:00+00:00")),
    )
    direct = {key: value for key, value in overrides.items() if key not in field_names and key != "now"}
    if direct:
        card = replace(card, **direct, card_revision="pending")
        card = replace(card, card_revision=card_revision(card))
    return card


class CatalogProjectionTests(unittest.TestCase):
    def test_golden_passage_semantic_hash_and_vector_hash(self) -> None:
        passage = card_passage_text(
            title="Example",
            summary="Example source.",
            aliases=["example docs", "example project"],
            tags=["docs", "python"],
        )
        self.assertEqual(
            passage,
            "Title: Example\nSummary: Example source.\nAliases: example docs; example project\nTags: docs; python",
        )
        self.assertFalse(passage.endswith("\n"))
        self.assertEqual(
            semantic_hash_for_fields(
                title="Example",
                summary="Example source.",
                aliases=["example docs", "example project"],
                tags=["docs", "python"],
            ),
            "94093fa7c81ea1549f6ef7005110dbc9adc4defa2d8fc4b60043fd231986a85f",
        )
        self.assertEqual(
            vector_hash(UNIT_VECTOR),
            "ba682adfaa5fe942ba23457dbe6188c5ebd9f2fb0fa009e7a8cab5773452fae8",
        )

    def test_stable_json_contract_remains_compact_unicode_and_recursive(self) -> None:
        value = {"z": True, "é": {"b": None, "a": [2, 1]}}
        self.assertEqual(stable_json_dumps(value), '{"z":true,"é":{"a":[2,1],"b":null}}')
        self.assertEqual(stable_hash(value), stable_hash({"é": {"a": [2, 1], "b": None}, "z": True}))

    def test_prepare_card_normalizes_semantics_and_reuses_unchanged_vector(self) -> None:
        initial_embedder = FixedEmbedder()
        card = prepare_card(
            fields(aliases=["z alias", "A alias"], tags=["z", "a"]),
            embedder=initial_embedder,
            now="2026-07-15T12:00:00+00:00",
        )
        self.assertEqual(card.aliases, ["A alias", "z alias"])
        self.assertEqual(card.tags, ["a", "z"])
        self.assertEqual(len(initial_embedder.calls), 1)

        updated = prepare_card(
            fields(
                aliases=["A alias", "z alias"],
                tags=["a", "z"],
                region="gcp-us-east4",
                enabled=False,
            ),
            existing=card,
            embedder=FailingEmbedder(),
            now="2026-07-15T13:00:00+00:00",
        )
        self.assertEqual(updated.vector, card.vector)
        self.assertEqual(updated.vector_hash, card.vector_hash)
        self.assertEqual(updated.created_at, card.created_at)
        self.assertFalse(updated.enabled)

    def test_semantic_change_embeds_exact_passage(self) -> None:
        embedder = FixedEmbedder()
        card = prepare_card(fields(title="New title", aliases=[]), embedder=embedder)
        self.assertEqual(
            embedder.calls,
            [[card_passage_text(title="New title", summary="Example source.", aliases=[], tags=["docs", "python"])]],
        )
        self.assertEqual(card.routing_model, ROUTING_MODEL)
        self.assertEqual(card.routing_model_revision, ROUTING_MODEL_REVISION)
        self.assertEqual(card.vector_dimensions, 384)

    def test_duplicate_normalized_alias_tag_and_title_alias_fail(self) -> None:
        for override, message in (
            ({"aliases": ["Straße", "STRASSE"]}, "duplicate normalized"),
            ({"tags": ["data_vault", "data vault"]}, "duplicate normalized"),
            ({"aliases": ["Ｅｘａｍｐｌｅ"]}, "normalized title"),
        ):
            with self.subTest(override=override), self.assertRaisesRegex(CatalogError, message):
                prepare_card(fields(**override), embedder=FailingEmbedder())
        self.assertEqual(canonical_text("  Data___Vault!!! "), "data vault")

    def test_persisted_lineage_is_strict_and_prospective_cards_cannot_be_saved(self) -> None:
        invalid_fields = (
            ({"last_apply_id": "apply-only"}, "last_apply_id requires"),
            ({"last_plan_id": "plan-only"}, "both IDs null or both non-empty"),
            ({"semantic_origin": "generated"}, "generated card requires"),
            (
                {"semantic_origin": "generated", "last_plan_id": "plan-only"},
                "generated card requires",
            ),
        )
        for overrides, message in invalid_fields:
            with self.subTest(overrides=overrides), self.assertRaisesRegex(CatalogError, message):
                prepare_card(fields(**overrides), embedder=FailingEmbedder())

        prospective_fields = fields(
            semantic_origin="generated", last_plan_id="plan-new", last_apply_id=None
        )
        prospective = prepare_prospective_card(
            prospective_fields,
            embedder=FixedEmbedder(),
            now="2026-07-15T12:00:00+00:00",
        )
        self.assertEqual((prospective.last_plan_id, prospective.last_apply_id), ("plan-new", None))
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(
            CatalogError, "generated card requires"
        ):
            save_catalog(Path(tmp) / "catalog.json", [prospective])
        finalized = prepare_card(
            replace(prospective_fields, last_apply_id="apply-new"),
            existing=prospective,
            embedder=FailingEmbedder(),
            now="2026-07-15T13:00:00+00:00",
        )
        self.assertEqual((finalized.last_plan_id, finalized.last_apply_id), ("plan-new", "apply-new"))

    def test_vector_validation_rejects_wrong_dimension_bool_nonfinite_zero_and_norm(self) -> None:
        bad_vectors = [
            [1.0],
            [True] + [0.0] * 383,
            [math.nan] + [0.0] * 383,
            [math.inf] + [0.0] * 383,
            [0.0] * 384,
            [2.0] + [0.0] * 383,
        ]
        for vector in bad_vectors:
            with self.subTest(first=vector[0], length=len(vector)), self.assertRaises(CatalogError):
                prepare_card(fields(), embedder=FixedEmbedder(vector))


class CatalogPersistenceTests(unittest.TestCase):
    def test_save_load_is_canonical_sorted_and_revision_validated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            second = make_card(namespace="z-namespace", title="Z", aliases=[])
            first = make_card(namespace="a-namespace", title="A", aliases=[])
            document = save_catalog(path, [second, first], now="2026-07-15T13:00:00+00:00")
            self.assertEqual([card.namespace for card in document.cards], ["a-namespace", "z-namespace"])
            self.assertEqual(load_catalog(path), document)
            self.assertTrue(path.read_bytes().endswith(b"\n"))
            self.assertEqual(
                document.catalog_revision,
                stable_hash([card_to_dict(first, include_vector=True), card_to_dict(second, include_vector=True)]),
            )

    def test_save_rejects_duplicate_namespaces_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            with self.assertRaisesRegex(CatalogError, "duplicate namespaces"):
                save_catalog(path, [make_card(), make_card()])
            self.assertFalse(path.exists())

    def test_missing_catalog_is_empty_without_creating_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "missing" / "catalog.json"
            document = load_catalog(path)
            self.assertEqual(document.schema_version, CATALOG_SCHEMA_VERSION)
            self.assertEqual(document.cards, [])
            self.assertEqual(document.catalog_revision, stable_hash([]))
            self.assertFalse(path.parent.exists())

    def test_unknown_fields_stale_hashes_order_duplicates_and_schema_fail_closed(self) -> None:
        first = make_card(namespace="a")
        second = make_card(namespace="b")
        valid = document_to_dict(
            save_document_for_parse([first, second])
        )
        mutations = []
        document_unknown = json.loads(json.dumps(valid)); document_unknown["typo"] = True
        mutations.append((document_unknown, "unknown"))
        card_unknown = json.loads(json.dumps(valid)); card_unknown["cards"][0]["typo"] = True
        mutations.append((card_unknown, "unknown"))
        stale_vector = json.loads(json.dumps(valid)); stale_vector["cards"][0]["vector_hash"] = "0" * 64
        mutations.append((stale_vector, "vector_hash"))
        stale_semantic = json.loads(json.dumps(valid)); stale_semantic["cards"][0]["semantic_hash"] = "0" * 64
        mutations.append((stale_semantic, "semantic_hash"))
        stale_card = json.loads(json.dumps(valid)); stale_card["cards"][0]["card_revision"] = "0" * 64
        mutations.append((stale_card, "card_revision"))
        stale_catalog = json.loads(json.dumps(valid)); stale_catalog["catalog_revision"] = "0" * 64
        mutations.append((stale_catalog, "catalog_revision"))
        future = json.loads(json.dumps(valid)); future["schema_version"] = 2
        mutations.append((future, "schema_version"))
        unordered = json.loads(json.dumps(valid)); unordered["cards"].reverse()
        mutations.append((unordered, "sorted"))
        duplicate = json.loads(json.dumps(valid)); duplicate["cards"] = [duplicate["cards"][0], duplicate["cards"][0]]
        duplicate["catalog_revision"] = stable_hash(duplicate["cards"])
        mutations.append((duplicate, "duplicate"))
        for payload, message in mutations:
            with self.subTest(message=message), self.assertRaisesRegex(CatalogError, message):
                parse_catalog(payload)

    def test_integer_only_fields_reject_json_floats_and_booleans(self) -> None:
        valid = document_to_dict(save_document_for_parse([make_card()]))
        cases = []
        for field, value in (
            ("plan_schema_version", 1.0),
            ("vector_dimensions", 384.0),
            ("ranking_pool", 20.0),
        ):
            payload = json.loads(json.dumps(valid))
            payload["cards"][0][field] = value
            cases.append((payload, field))
        for value in (1.0, True):
            payload = json.loads(json.dumps(valid))
            payload["schema_version"] = value
            cases.append((payload, "schema_version"))
        for payload, field in cases:
            with self.subTest(field=field), self.assertRaisesRegex(
                CatalogError, f"{field} must be a JSON integer"
            ):
                parse_catalog(payload)
        for overrides, field in (
            ({"plan_schema_version": 1.0}, "plan_schema_version"),
            ({"ranking_pool": 20.0}, "ranking_pool"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(CatalogError, "JSON integer"):
                prepare_card(fields(**overrides), embedder=FailingEmbedder())

    def test_json_nan_and_malformed_file_report_path_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            for contents in ("{", '{"schema_version": NaN}'):
                path.write_text(contents, encoding="utf-8")
                with self.subTest(contents=contents), self.assertRaisesRegex(CatalogError, "repair or restore") as raised:
                    load_catalog(path)
                self.assertIn(str(path), str(raised.exception))

    def test_atomic_save_fsyncs_file_and_best_effort_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            directory_fd = 987654
            fsync_fds: list[int] = []
            real_open = os.open
            real_close = os.close
            open_calls: list[tuple[object, int]] = []
            close_calls: list[int] = []

            def recording_open(target, flags, *args):  # noqa: ANN001 - mirrors os.open.
                if Path(target) == path.parent and flags == os.O_RDONLY:
                    open_calls.append((target, flags))
                    return directory_fd
                return real_open(target, flags, *args)

            def recording_close(fd: int) -> None:
                if fd == directory_fd:
                    close_calls.append(fd)
                    return
                real_close(fd)

            with patch("buoy_search.catalog.os.open", side_effect=recording_open), patch(
                "buoy_search.catalog.os.fsync", side_effect=fsync_fds.append
            ), patch("buoy_search.catalog.os.close", side_effect=recording_close):
                save_catalog(path, [make_card()])
            self.assertEqual(len(fsync_fds), 2)
            self.assertNotEqual(fsync_fds[0], directory_fd)
            self.assertEqual(fsync_fds[1], directory_fd)
            self.assertEqual(open_calls, [(path.parent, os.O_RDONLY)])
            self.assertEqual(close_calls, [directory_fd])

            second_path = Path(tmp) / "catalog-no-directory-fsync.json"

            def unsupported_directory_open(target, flags, *args):  # noqa: ANN001
                if Path(target) == second_path.parent and flags == os.O_RDONLY:
                    raise OSError("unsupported")
                return real_open(target, flags, *args)

            with patch("buoy_search.catalog.os.open", side_effect=unsupported_directory_open), patch(
                "buoy_search.catalog.os.fsync"
            ) as fsync_mock:
                save_catalog(second_path, [make_card()])
            fsync_mock.assert_called_once()
            self.assertTrue(second_path.exists())

    def test_failed_atomic_replace_preserves_previous_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            save_catalog(path, [make_card()], now="2026-07-15T12:00:00+00:00")
            before = path.read_bytes()
            with patch("buoy_search.catalog.os.replace", side_effect=OSError("disk failure")):
                with self.assertRaisesRegex(CatalogError, "atomic save failed"):
                    save_catalog(path, [make_card(title="Changed", aliases=[])])
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(list(path.parent.glob(".catalog.json.*.tmp")), [])

    def test_lock_contention_fails_fast_and_preserves_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            save_catalog(path, [make_card()])
            before = path.read_bytes()
            lock_path = path.with_name("catalog.json.lock")
            with portalocker.Lock(str(lock_path), mode="a+", timeout=0, fail_when_locked=True):
                with self.assertRaisesRegex(CatalogError, "another catalog mutation"):
                    with catalog_lock(path):
                        self.fail("lock unexpectedly acquired")
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(load_catalog(path).cards[0].namespace, "site-example-v1")

    def test_integer_json_vectors_validate_against_their_exact_stable_hash(self) -> None:
        card = make_card()
        integer_vector = [1] + [0] * 383
        provisional = replace(card, vector=integer_vector, vector_hash=vector_hash(integer_vector), card_revision="pending")
        integer_card = replace(provisional, card_revision=card_revision(provisional))
        document = save_document_for_parse([integer_card])
        parsed = parse_catalog(document_to_dict(document))
        self.assertEqual(parsed.cards[0].vector[0], 1)


def save_document_for_parse(cards: list[NamespaceCard]):
    from buoy_search.catalog import CatalogDocument, catalog_revision
    return CatalogDocument(
        schema_version=1,
        catalog_revision=catalog_revision(cards),
        updated_at="2026-07-15T12:00:00+00:00",
        cards=cards,
    )


class CatalogMergeAndGeneratedSemanticsTests(unittest.TestCase):
    def test_manual_merge_preserves_semantics_enabled_vector_and_refreshes_system_fields(self) -> None:
        existing = make_card(enabled=False, last_plan_id="plan-old", last_apply_id="apply-old")
        incoming = make_card(
            enabled=True,
            semantic_origin="generated",
            title="Generated replacement",
            summary="Generated.",
            aliases=[],
            tags=["website"],
            region="gcp-us-east4",
            last_plan_id="plan-new",
            last_apply_id="apply-new",
            now="2026-07-15T14:00:00+00:00",
        )
        merged = merge_system_card(existing, incoming)
        self.assertFalse(merged.enabled)
        self.assertEqual(
            (merged.title, merged.summary, merged.aliases, merged.tags, merged.semantic_origin),
            (existing.title, existing.summary, existing.aliases, existing.tags, "manual"),
        )
        self.assertEqual(merged.vector, existing.vector)
        self.assertEqual(merged.region, "gcp-us-east4")
        self.assertEqual((merged.last_plan_id, merged.last_apply_id), ("plan-new", "apply-new"))
        self.assertEqual(merged.created_at, existing.created_at)

    def test_concurrent_generated_disable_is_preserved_during_system_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            current = make_card(
                enabled=False,
                semantic_origin="generated",
                title="Current generated",
                aliases=[],
                last_plan_id="plan-current",
                last_apply_id="apply-current",
            )
            incoming = make_card(
                enabled=True,
                semantic_origin="generated",
                title="Refreshed generated",
                summary="Refreshed.",
                aliases=[],
                last_plan_id="plan-new",
                last_apply_id="apply-new",
                now="2026-07-15T15:00:00+00:00",
            )
            save_catalog(path, [current])
            _document, committed, changed = commit_system_card(path, incoming)

        self.assertTrue(changed)
        self.assertFalse(committed.enabled)
        self.assertEqual(committed.title, incoming.title)
        self.assertEqual((committed.last_plan_id, committed.last_apply_id), ("plan-new", "apply-new"))

    def test_commit_api_validates_merges_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            existing = make_card()
            save_catalog(path, [existing])
            incoming = make_card(
                semantic_origin="generated",
                title="Generated",
                aliases=[],
                summary="Generated.",
                last_plan_id="plan-new",
                last_apply_id="apply-new",
            )
            document, committed, changed = commit_system_card(path, incoming)
            self.assertTrue(changed)
            self.assertEqual(committed.title, existing.title)
            self.assertEqual(document.cards, [committed])
            repeated_document, repeated, repeated_changed = commit_system_card(path, incoming)
            self.assertFalse(repeated_changed)
            self.assertEqual(repeated, committed)
            self.assertEqual(repeated_document.catalog_revision, document.catalog_revision)

    def test_generated_repository_website_pdf_file_and_legacy_file(self) -> None:
        repo = generated_semantics(
            base_url="https://github.com/Doctacon/buoy-search",
            site_id="repo-site",
            plan_schema_version=1,
            source_metadata=[{"source_kind": "github_repo", "repo_full_name": "Doctacon/buoy-search"}],
        )
        self.assertEqual(repo.source_kind, "github_repo")
        self.assertEqual(repo.title, "Doctacon/buoy-search")
        self.assertEqual(repo.aliases, ["buoy-search"])
        self.assertEqual(repo.tags, ["github", "repository"])
        legacy_repo = generated_semantics(
            base_url="https://github.com/Doctacon/buoy-search",
            site_id="repo-site",
            plan_schema_version=1,
            source_metadata=[],
        )
        self.assertEqual(legacy_repo.title, "Doctacon/buoy-search")

        website = generated_semantics(
            base_url="https://Docs.Example.com/path",
            site_id="site",
            plan_schema_version=1,
            source_metadata=[],
        )
        self.assertEqual((website.source_kind, website.title, website.tags), ("website", "docs.example.com", ["website"]))

        for raw_kind, filename_key, filename, base_url in (
            ("pdf", "pdf_filename", "Research Notes.pdf", "pdf://opaque-source-id"),
            ("local_file", "file_filename", "Research Notes.csv", "file://opaque-source-id"),
        ):
            document = generated_semantics(
                base_url=base_url,
                site_id="stable-site-id",
                plan_schema_version=1,
                source_metadata=[{"source_kind": raw_kind, filename_key: filename}],
            )
            self.assertEqual(document.source_kind, "document")
            self.assertEqual(document.title, filename)
            self.assertEqual(document.aliases, ["Research Notes"])
            self.assertEqual(document.tags, ["document"])

        legacy = generated_semantics(
            base_url="file://opaque-source-id",
            site_id="stable-site-id",
            plan_schema_version=1,
            source_metadata=[],
        )
        self.assertEqual(legacy.title, "stable-site-id")
        self.assertEqual(legacy.aliases, [])
        self.assertNotIn("opaque-source-id", legacy.title)

    def test_source_uri_validation_is_kind_aware_and_rejects_malformed_values(self) -> None:
        invalid = (
            ("website", " https://example.com", "whitespace"),
            ("website", "https://example.com/a b", "whitespace"),
            ("website", "https://example.com:not-a-port", "malformed"),
            ("website", "https://bad_host.example", "malformed hostname"),
            ("website", "example.com/docs", "unsupported scheme"),
            ("website", "urn:example", "unsupported scheme"),
            ("website", "file://site-example", "requires HTTP"),
            ("document", "ftp://example.com/file.pdf", "unsupported scheme"),
            ("document", "file://", "supported file"),
            ("document", "file://source/path", "supported file"),
            ("document", "pdf://", "supported file"),
            ("document", "pdf://source/path", "supported file"),
        )
        for source_kind, source_uri, message in invalid:
            with self.subTest(source_uri=source_uri), self.assertRaisesRegex(CatalogError, message):
                prepare_card(
                    fields(source_kind=source_kind, source_uri=source_uri),
                    embedder=FailingEmbedder(),
                )
        for source_kind, source_uri in (
            ("github_repo", "http://github.com/owner/repo"),
            ("website", "https://docs.example.com:8443/path"),
            ("document", "https://example.com/document.pdf"),
            ("document", "file://stable-source-id"),
            ("document", "pdf://stable-source-id"),
        ):
            with self.subTest(valid=source_uri):
                card = prepare_card(
                    fields(source_kind=source_kind, source_uri=source_uri),
                    embedder=FixedEmbedder(),
                )
                self.assertEqual(card.source_uri, source_uri)

    def test_generated_metadata_contradictions_and_unsupported_inputs_fail(self) -> None:
        cases = [
            ({"base_url": "https://example.com", "source_metadata": [{"source_kind": "github_repo"}]}, "contradicts"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": "pdf"}, {"source_kind": "local_file"}]}, "contradictory source_kind"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": "pdf", "pdf_filename": "a.pdf"}]}, "non-pdf"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": "video"}]}, "unsupported"),
            ({"base_url": "https://github.com/a/b", "source_metadata": [{"source_kind": "github_repo", "repo_full_name": "a/c"}]}, "contradicts"),
            ({"base_url": "pdf://source", "source_metadata": [{"source_kind": "pdf", "pdf_filename": "a.pdf"}, {"source_kind": "pdf", "pdf_filename": "b.pdf"}]}, "contradictory pdf_filename"),
            ({"base_url": "pdf://source", "source_metadata": [{"source_kind": "pdf"}]}, "requires one consistent.*pdf_filename"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": "local_file"}]}, "requires one consistent.*file_filename"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": 1}]}, "source_kind must be a string"),
            ({"base_url": "file://source", "source_metadata": [{"source_kind": None}]}, "source_kind must be a string"),
        ]
        for values, message in cases:
            with self.subTest(values=values), self.assertRaisesRegex(CatalogError, message):
                generated_semantics(site_id="site", plan_schema_version=1, **values)
        with self.assertRaisesRegex(CatalogError, "plan_schema_version must equal"):
            generated_semantics(base_url="https://example.com", site_id="site", plan_schema_version=2, source_metadata=[])
        with self.assertRaisesRegex(CatalogError, "plan_schema_version must be a JSON integer"):
            generated_semantics(base_url="https://example.com", site_id="site", plan_schema_version=1.0, source_metadata=[])


class CatalogPathAndModelTests(unittest.TestCase):
    def test_catalog_path_precedence_and_empty_values(self) -> None:
        explicit, warning = resolve_catalog_path("chosen/catalog.json", environ={"BUOY_CATALOG_PATH": "env.json"})
        self.assertEqual(explicit, Path("chosen/catalog.json"))
        self.assertIsNone(warning)
        environment, warning = resolve_catalog_path(None, environ={"BUOY_CATALOG_PATH": "env.json"})
        self.assertEqual(environment, Path("env.json"))
        self.assertIsNone(warning)
        for explicit_value, environment_value in (("", {}), ("   ", {}), (None, {"BUOY_CATALOG_PATH": "  "})):
            with self.subTest(explicit=explicit_value), self.assertRaisesRegex(CatalogError, "non-whitespace"):
                resolve_catalog_path(explicit_value, environ=environment_value)

    def test_default_and_legacy_path_resolution_and_ambiguity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / ".buoy"
            legacy = root / ".turbo-search"
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                path, warning = resolve_catalog_path(None, environ={})
                self.assertEqual(path, current / "catalog.json")
                self.assertIsNone(warning)
                legacy.mkdir()
                path, warning = resolve_catalog_path(None, environ={})
                self.assertEqual(path, legacy / "catalog.json")
                self.assertIn("legacy state root", warning or "")
                current.mkdir()
                with self.assertRaisesRegex(CatalogError, "both implicit state roots") as raised:
                    resolve_catalog_path(None, environ={})
                self.assertIn("--catalog", str(raised.exception))
                self.assertNotIn("--state-root", str(raised.exception))

    def test_model_constructor_is_exact_pinned_local_only_and_missing_cache_fails_closed(self) -> None:
        calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

        class FakeSentenceTransformer:
            def __init__(self, *args: object, **kwargs: object) -> None:
                calls.append((args, kwargs))

            def encode(self, texts, **kwargs):  # noqa: ANN001
                return [UNIT_VECTOR for _ in texts]

        import types
        fake_module = types.ModuleType("sentence_transformers")
        fake_module.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"sentence_transformers": fake_module}):
            embedder = load_routing_embedder()
            self.assertEqual(embedder.encode(["passage"]), [UNIT_VECTOR])
        self.assertEqual(calls[0][0], (ROUTING_MODEL,))
        self.assertEqual(
            calls[0][1],
            {"revision": ROUTING_MODEL_REVISION, "local_files_only": True},
        )

        class MissingSentenceTransformer:
            def __init__(self, *args: object, **kwargs: object) -> None:
                raise OSError("not cached")

        missing_module = types.ModuleType("sentence_transformers")
        missing_module.SentenceTransformer = MissingSentenceTransformer  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"sentence_transformers": missing_module}), self.assertRaisesRegex(
            CatalogError, "not cached locally.*downloads and substitutions are disabled"
        ):
            load_routing_embedder()


if __name__ == "__main__":
    unittest.main()
