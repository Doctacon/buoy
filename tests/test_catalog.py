from __future__ import annotations

from contextlib import nullcontext
from dataclasses import replace
import json
import math
import traceback
import unittest
from unittest.mock import patch

from buoy_search.catalog import (
    MAX_ROUTING_EXAMPLES,
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_PROJECTION,
    CardFields,
    CatalogError,
    NamespaceCard,
    canonical_text,
    card_passage_text,
    card_revision,
    card_to_dict,
    catalog_revision,
    generated_semantics,
    load_routing_embedder,
    merge_system_card,
    parse_card,
    parse_catalog,
    prepare_card,
    prepare_prospective_card,
    routing_example_passage_text,
    routing_prototype_hash_for_fields,
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


class SequenceEmbedder:
    def __init__(self, vectors: list[list[float]]) -> None:
        self.vectors = vectors
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001 - test protocol implementation.
        self.calls.append(list(texts))
        return [list(vector) for vector in self.vectors]


class SecretEchoEmbedder:
    def encode(self, texts):  # noqa: ANN001 - adversarial test sentinel.
        raise RuntimeError("Authorization: Bearer routing-secret-sentinel")


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

        legacy = make_card()
        legacy_payload = card_to_dict(legacy, include_vector=True)
        self.assertEqual(len(legacy_payload), 29)
        self.assertNotIn("routing_examples", legacy_payload)
        self.assertEqual(
            legacy.card_revision,
            "fc5239d6b296c29dbd8f070fbb8a703fdc4775bcfe61a35ca53ad5a2c69326d8",
        )
        self.assertEqual(parse_card(legacy_payload), legacy)

    def test_routing_examples_project_as_normalized_mean_and_round_trip(self) -> None:
        second_unit = [0.0, 1.0] + [0.0] * (ROUTING_DIMENSIONS - 2)
        example = "How do I configure request retries?"
        embedder = SequenceEmbedder([UNIT_VECTOR, second_unit])

        card = prepare_card(
            fields(routing_examples=[example]),
            embedder=embedder,
            now="2026-07-15T12:00:00+00:00",
        )

        self.assertEqual(
            embedder.calls,
            [[
                card_passage_text(
                    title="Example",
                    summary="Example source.",
                    aliases=["example docs", "example project"],
                    tags=["docs", "python"],
                ),
                routing_example_passage_text(
                    title="Example",
                    summary="Example source.",
                    example=example,
                ),
            ]],
        )
        expected_coordinate = 1 / math.sqrt(2)
        self.assertEqual(card.vector, UNIT_VECTOR)
        self.assertAlmostEqual(
            card.routing_prototype_vector[0], expected_coordinate
        )
        self.assertAlmostEqual(
            card.routing_prototype_vector[1], expected_coordinate
        )
        self.assertEqual(
            card.routing_prototype_vector[2:],
            [0.0] * (ROUTING_DIMENSIONS - 2),
        )
        self.assertEqual(card.routing_examples, [example])
        self.assertEqual(
            card.semantic_hash,
            semantic_hash_for_fields(
                title=card.title,
                summary=card.summary,
                aliases=card.aliases,
                tags=card.tags,
            ),
        )
        self.assertEqual(
            card.routing_prototype_hash,
            routing_prototype_hash_for_fields(
                title=card.title,
                summary=card.summary,
                aliases=card.aliases,
                tags=card.tags,
                routing_examples=[example],
            ),
        )
        self.assertEqual(
            ROUTING_PROJECTION,
            "separate_prototype_vector_normalized_mean_v1",
        )
        payload = card_to_dict(card, include_vector=True)
        self.assertEqual(payload["routing_examples"], [example])
        self.assertIn("routing_prototype_hash", payload)
        self.assertIn("routing_prototype_vector", payload)
        self.assertIn("routing_prototype_vector_hash", payload)
        self.assertEqual(parse_card(payload), card)
        public_payload = card_to_dict(card)
        self.assertNotIn("vector", public_payload)
        self.assertNotIn("routing_prototype_vector", public_payload)
        self.assertEqual(public_payload["routing_examples"], [example])

    def test_example_only_edit_reuses_base_projection_but_recomputes_prototype(self) -> None:
        original = make_card()
        second_unit = [0.0, 1.0] + [0.0] * (ROUTING_DIMENSIONS - 2)
        embedder = SequenceEmbedder([second_unit, second_unit])

        updated = prepare_card(
            fields(routing_examples=["How do I configure retries?"]),
            existing=original,
            embedder=embedder,
        )

        self.assertEqual(len(embedder.calls), 1)
        self.assertEqual(updated.semantic_hash, original.semantic_hash)
        self.assertEqual(updated.vector, original.vector)
        self.assertEqual(updated.vector_hash, original.vector_hash)
        self.assertEqual(updated.routing_prototype_vector, second_unit)
        self.assertNotEqual(
            updated.routing_prototype_vector_hash, original.vector_hash
        )

    def test_v2_bundle_is_all_or_nothing_and_empty_bundle_equals_base(self) -> None:
        legacy = make_card()
        explicit = card_to_dict(
            legacy,
            include_vector=True,
            include_routing_examples=True,
        )
        self.assertEqual(parse_card(explicit), legacy)
        for field in (
            "routing_examples",
            "routing_prototype_hash",
            "routing_prototype_vector",
            "routing_prototype_vector_hash",
        ):
            with self.subTest(field=field):
                partial = json.loads(json.dumps(explicit))
                partial.pop(field)
                with self.assertRaisesRegex(CatalogError, "missing"):
                    parse_card(partial)

        mismatched = json.loads(json.dumps(explicit))
        mismatched["routing_prototype_hash"] = "0" * 64
        with self.assertRaisesRegex(CatalogError, "routing_prototype_hash"):
            parse_card(mismatched)

    def test_routing_examples_are_canonical_arrays_bounded_at_eight(self) -> None:
        card = prepare_card(
            fields(routing_examples=["z question", "A question"]),
            embedder=FixedEmbedder(),
        )
        self.assertEqual(card.routing_examples, ["A question", "z question"])
        self.assertEqual(MAX_ROUTING_EXAMPLES, 8)
        for value, message in (
            (["Question"] * 2, "duplicate normalized"),
            ([f"Question {index}" for index in range(9)], "at most 8"),
            (["q" * 513], "at most 512 characters"),
            ("not-an-array", "must be an array"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(CatalogError, message):
                prepare_card(
                    fields(routing_examples=value),  # type: ignore[arg-type]
                    embedder=FailingEmbedder(),
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

    def test_embedder_failure_is_content_free_and_has_no_exception_chain(self) -> None:
        with self.assertRaises(CatalogError) as raised:
            prepare_card(fields(), embedder=SecretEchoEmbedder())

        self.assertEqual(
            str(raised.exception),
            "namespace 'site-example-v1': routing model failed",
        )
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        formatted = "".join(
            traceback.format_exception(
                type(raised.exception),
                raised.exception,
                raised.exception.__traceback__,
            )
        )
        self.assertNotIn("routing-secret-sentinel", formatted)

    def test_duplicate_normalized_alias_tag_and_title_alias_fail(self) -> None:
        for override, message in (
            ({"aliases": ["Straße", "STRASSE"]}, "duplicate normalized"),
            ({"tags": ["data_vault", "data vault"]}, "duplicate normalized"),
            ({"aliases": ["Ｅｘａｍｐｌｅ"]}, "normalized title"),
        ):
            with self.subTest(override=override), self.assertRaisesRegex(CatalogError, message):
                prepare_card(fields(**override), embedder=FailingEmbedder())
        self.assertEqual(canonical_text("  Data___Vault!!! "), "data vault")

    def test_persisted_and_prospective_lineage_is_strict(self) -> None:
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


class CatalogParsingTests(unittest.TestCase):
    def test_unknown_fields_stale_hashes_order_duplicates_and_schema_fail_closed(self) -> None:
        first = make_card(namespace="a")
        second = make_card(namespace="b")
        valid = catalog_payload_for_parse([first, second])
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
        valid = catalog_payload_for_parse([make_card()])
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

    def test_integer_json_vectors_validate_against_their_exact_stable_hash(self) -> None:
        card = make_card()
        integer_vector = [1] + [0] * 383
        provisional = replace(
            card,
            vector=integer_vector,
            vector_hash=vector_hash(integer_vector),
            routing_prototype_vector=integer_vector,
            routing_prototype_vector_hash=vector_hash(integer_vector),
            card_revision="pending",
        )
        integer_card = replace(provisional, card_revision=card_revision(provisional))
        parsed = parse_catalog(catalog_payload_for_parse([integer_card]))
        self.assertEqual(parsed.cards[0].vector[0], 1)


def catalog_payload_for_parse(cards: list[NamespaceCard]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "catalog_revision": catalog_revision(cards),
        "updated_at": "2026-07-15T12:00:00+00:00",
        "cards": [card_to_dict(card, include_vector=True) for card in cards],
    }


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
        self.assertEqual(merged.routing_examples, existing.routing_examples)
        self.assertEqual(
            merged.routing_prototype_vector,
            existing.routing_prototype_vector,
        )
        self.assertEqual(merged.region, "gcp-us-east4")
        self.assertEqual((merged.last_plan_id, merged.last_apply_id), ("plan-new", "apply-new"))
        self.assertEqual(merged.created_at, existing.created_at)

    def test_generated_merge_preserves_concurrent_disable(self) -> None:
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

        merged = merge_system_card(current, incoming)

        self.assertFalse(merged.enabled)
        self.assertEqual(merged.title, incoming.title)
        self.assertEqual((merged.last_plan_id, merged.last_apply_id), ("plan-new", "apply-new"))

    def test_generated_repository_website_pdf_file_and_legacy_file(self) -> None:
        repo = generated_semantics(
            base_url="https://github.com/Doctacon/buoy",
            site_id="repo-site",
            plan_schema_version=2,
            source_metadata=[{"source_kind": "github_repo", "repo_full_name": "Doctacon/buoy"}],
        )
        self.assertEqual(repo.source_kind, "github_repo")
        self.assertEqual(repo.title, "Doctacon/buoy")
        self.assertEqual(repo.aliases, ["buoy"])
        self.assertEqual(repo.tags, ["github", "repository"])
        self.assertEqual(repo.routing_examples, [])
        legacy_repo = generated_semantics(
            base_url="https://github.com/Doctacon/buoy",
            site_id="repo-site",
            plan_schema_version=2,
            source_metadata=[],
        )
        self.assertEqual(legacy_repo.title, "Doctacon/buoy")

        website = generated_semantics(
            base_url="https://Docs.Example.com/path",
            site_id="site",
            plan_schema_version=2,
            source_metadata=[],
        )
        self.assertEqual((website.source_kind, website.title, website.tags), ("website", "docs.example.com", ["website"]))

        database = generated_semantics(
            base_url="duckdb://gong-calls",
            site_id="duckdb-gong-calls",
            plan_schema_version=2,
            source_metadata=[
                {
                    "source_kind": "duckdb_relation",
                    "duckdb_source_id": "gong-calls",
                    "duckdb_relation": "analytics.calls",
                    "duckdb_document_id": "call-1",
                },
                {
                    "source_kind": "duckdb_relation",
                    "duckdb_source_id": "gong-calls",
                    "duckdb_relation": "analytics.calls",
                    "duckdb_document_id": "call-2",
                },
            ],
        )
        self.assertEqual(database.source_kind, "database")
        self.assertEqual(database.source_uri, "duckdb://gong-calls")
        self.assertEqual(database.title, "gong-calls (analytics.calls)")
        self.assertEqual(
            database.summary,
            "DuckDB document relation analytics.calls from logical source gong-calls.",
        )
        self.assertEqual(database.aliases, ["analytics.calls", "gong-calls"])
        self.assertEqual(
            database.tags,
            ["database", "duckdb", "relation analytics.calls", "source gong-calls"],
        )

        for backend, raw_kind, relation in (
            ("duckdb", "duckdb_relation", "analytics.calls"),
            ("bigquery", "bigquery_relation", "source-project.corpus.calls"),
            ("snowflake", "snowflake_relation", "ANALYTICS.CORPUS.CALLS"),
        ):
            with self.subTest(backend=backend):
                generated = generated_semantics(
                    base_url=f"{backend}://gong-calls",
                    site_id=f"{backend}-gong-calls",
                    plan_schema_version=2,
                    source_metadata=[
                        {
                            "source_kind": raw_kind,
                            "database_backend": backend,
                            "database_source_id": "gong-calls",
                            "database_relation": relation,
                            "database_document_id": "call-1",
                        }
                    ],
                )
                self.assertEqual(generated.source_kind, "database")
                self.assertEqual(generated.source_uri, f"{backend}://gong-calls")
                self.assertEqual(generated.title, f"gong-calls ({relation})")
                self.assertIn("database", generated.tags)
                self.assertIn(backend, generated.tags)

        for raw_kind, filename_key, filename, base_url in (
            ("pdf", "pdf_filename", "Research Notes.pdf", "pdf://opaque-source-id"),
            ("local_file", "file_filename", "Research Notes.csv", "file://opaque-source-id"),
        ):
            document = generated_semantics(
                base_url=base_url,
                site_id="stable-site-id",
                plan_schema_version=2,
                source_metadata=[{"source_kind": raw_kind, filename_key: filename}],
            )
            self.assertEqual(document.source_kind, "document")
            self.assertEqual(document.title, filename)
            self.assertEqual(document.aliases, ["Research Notes"])
            self.assertEqual(document.tags, ["document"])

        legacy = generated_semantics(
            base_url="file://opaque-source-id",
            site_id="stable-site-id",
            plan_schema_version=2,
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
            ("database", "duckdb://stable-source-id"),
            ("database", "bigquery://stable-source-id"),
            ("database", "snowflake://stable-source-id"),
        ):
            with self.subTest(valid=source_uri):
                card = prepare_card(
                    fields(source_kind=source_kind, source_uri=source_uri),
                    embedder=FixedEmbedder(),
                )
                self.assertEqual(card.source_uri, source_uri)

    def test_database_source_uri_validation_fails_closed_on_shape_and_kind_mismatches(self) -> None:
        invalid = (
            ("database", "duckdb://user@gong-calls"),
            ("database", "bigquery://gong-calls:1234"),
            ("database", "snowflake://gong-calls/"),
            ("database", "duckdb://gong-calls/document-1"),
            ("database", "bigquery://gong-calls?mode=read-only"),
            ("database", "snowflake://gong-calls#fragment"),
            ("database", "duckdb://Gong-calls"),
            ("database", "bigquery://gong_calls"),
            ("database", "https://example.com/database"),
            ("database", "file://gong-calls"),
            ("website", "duckdb://gong-calls"),
            ("website", "bigquery://gong-calls"),
            ("document", "snowflake://gong-calls"),
        )
        for source_kind, source_uri in invalid:
            with self.subTest(source_kind=source_kind, source_uri=source_uri), self.assertRaises(CatalogError):
                prepare_card(
                    fields(source_kind=source_kind, source_uri=source_uri),
                    embedder=FailingEmbedder(),
                )

    def test_generated_database_requires_verified_duckdb_relation_source_kind(self) -> None:
        metadata = {
            "duckdb_source_id": "gong-calls",
            "duckdb_relation": "analytics.calls",
        }
        for source_metadata in (
            [metadata],
            [{**metadata, "source_kind": "local_file"}],
        ):
            with self.subTest(source_metadata=source_metadata), self.assertRaisesRegex(
                CatalogError,
                "requires source_kind 'duckdb_relation'",
            ):
                generated_semantics(
                    base_url="duckdb://gong-calls",
                    site_id="duckdb-gong-calls",
                    plan_schema_version=2,
                    source_metadata=source_metadata,
                )

        for backend, wrong_kind in (
            ("bigquery", "snowflake_relation"),
            ("snowflake", "bigquery_relation"),
        ):
            with self.subTest(backend=backend), self.assertRaisesRegex(
                CatalogError, f"requires source_kind '{backend}_relation'"
            ):
                generated_semantics(
                    base_url=f"{backend}://gong-calls",
                    site_id=f"{backend}-gong-calls",
                    plan_schema_version=2,
                    source_metadata=[{"source_kind": wrong_kind}],
                )

    def test_manual_database_semantics_survive_generated_refresh(self) -> None:
        existing = make_card(
            namespace="customer-conversations",
            source_kind="database",
            source_uri="bigquery://gong-calls",
            site_id="bigquery-gong-calls",
            title="Customer calls",
            summary="Curated sales conversation corpus.",
            aliases=["calls"],
            tags=["sales"],
            last_plan_id="plan-old",
            last_apply_id="apply-old",
        )
        incoming = make_card(
            namespace="customer-conversations",
            source_kind="database",
            source_uri="bigquery://gong-calls",
            site_id="bigquery-gong-calls",
            semantic_origin="generated",
            title="gong-calls (source-project.corpus.calls)",
            summary="BigQuery document relation source-project.corpus.calls from logical source gong-calls.",
            aliases=["gong-calls"],
            tags=["bigquery", "database"],
            last_plan_id="plan-new",
            last_apply_id="apply-new",
        )

        merged = merge_system_card(existing, incoming)

        self.assertEqual(merged.title, "Customer calls")
        self.assertEqual(merged.summary, "Curated sales conversation corpus.")
        self.assertEqual(merged.aliases, ["calls"])
        self.assertEqual(merged.tags, ["sales"])
        self.assertEqual(merged.semantic_origin, "manual")
        self.assertEqual((merged.last_plan_id, merged.last_apply_id), ("plan-new", "apply-new"))

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
            ({"base_url": "https://example.com", "source_metadata": [{"source_kind": "duckdb_relation"}]}, "contradicts"),
            ({"base_url": "duckdb://gong-calls", "source_metadata": [{"source_kind": "duckdb_relation", "duckdb_source_id": "other", "duckdb_relation": "calls"}]}, "contradicts"),
            ({"base_url": "duckdb://gong-calls", "source_metadata": [{"source_kind": "duckdb_relation", "duckdb_source_id": "gong-calls", "duckdb_relation": "bad-name"}]}, "valid database_relation"),
            ({"base_url": "duckdb://gong-calls", "source_metadata": [{"source_kind": "duckdb_relation"}]}, "requires one consistent valid database_source_id"),
        ]
        for values, message in cases:
            with self.subTest(values=values), self.assertRaisesRegex(CatalogError, message):
                generated_semantics(site_id="site", plan_schema_version=2, **values)
        with self.assertRaisesRegex(CatalogError, "plan_schema_version must equal"):
            generated_semantics(base_url="https://example.com", site_id="site", plan_schema_version=1, source_metadata=[])
        with self.assertRaisesRegex(CatalogError, "plan_schema_version must be a JSON integer"):
            generated_semantics(base_url="https://example.com", site_id="site", plan_schema_version=2.0, source_metadata=[])


class CatalogModelTests(unittest.TestCase):
    def test_model_constructor_suppresses_third_party_progress(self) -> None:
        class FakeSentenceTransformer:
            def __init__(self, *_args: object, **_kwargs: object) -> None:
                pass

        import types

        fake_module = types.ModuleType("sentence_transformers")
        fake_module.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
        with patch.dict("sys.modules", {"sentence_transformers": fake_module}), patch(
            "buoy_search.catalog.suppress_model_progress_bars",
            return_value=nullcontext(),
        ) as suppress:
            load_routing_embedder()

        suppress.assert_called_once_with()

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
