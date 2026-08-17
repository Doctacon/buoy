from __future__ import annotations

import copy
from dataclasses import replace
import os
from types import SimpleNamespace
import traceback
import unittest
from unittest.mock import patch

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    CardFields,
    CatalogError,
    NamespaceCard,
    card_revision,
    card_to_dict,
    parse_card,
    prepare_card,
    vector_hash,
)
from buoy_search.plan_artifacts import PLAN_SCHEMA_VERSION
from buoy_search.remote_catalog import (
    CARD_PAGE_SIZE,
    DISTANCE_METRIC,
    MAX_PAGES_PER_PASS,
    NAMESPACE_PAGE_SIZE,
    REMOTE_CARD_ATTRIBUTES,
    REMOTE_CARD_ATTRIBUTES_V1,
    REMOTE_CARD_ATTRIBUTES_V2,
    REMOTE_CARD_ATTRIBUTES_V3,
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_CATALOG_SCHEMA,
    REMOTE_CATALOG_SCHEMA_V1,
    REMOTE_CATALOG_SCHEMA_V2,
    REMOTE_CATALOG_SCHEMA_V2_ADDITIONS,
    REMOTE_CATALOG_SCHEMA_V3,
    REMOTE_CATALOG_SCHEMA_V3_ADDITIONS,
    REMOTE_SCHEMA_V1,
    REMOTE_SCHEMA_V2,
    REMOTE_SCHEMA_V3,
    CatalogCounts,
    CompatibilityContract,
    RemoteCatalogError,
    RemoteCatalogMissingError,
    card_from_remote_row,
    card_to_remote_row,
    classify_remote_catalog,
    create_client,
    create_remote_cards,
    migrate_remote_catalog_schema_v2,
    migrate_remote_catalog_schema_v3,
    normalize_remote_schema,
    read_remote_catalog,
    require_complete_routing_coverage,
    require_eligible,
    redact_remote_error,
    remote_card_id,
    remote_catalog_projection_sha256,
    remote_catalog_schema_fingerprint,
    update_remote_card,
    validate_remote_schema,
)

UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)
REGION = "gcp-us-central1"
MODEL = "BAAI/bge-small-en-v1.5"


def formatted_remote_failure(call) -> str:  # noqa: ANN001 - focused traceback sentinel.
    try:
        call()
    except RemoteCatalogError as exc:
        return "".join(traceback.format_exception(exc))
    raise AssertionError("expected RemoteCatalogError")


class FixedEmbedder:
    def __init__(self, vector: list[float] | None = None) -> None:
        self.vector = vector or list(UNIT_VECTOR)
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001
        self.calls.append(list(texts))
        return [list(self.vector) for _ in texts]


def make_card(namespace: str = "site-example-v1", **overrides: object) -> NamespaceCard:
    values: dict[str, object] = {
        "namespace": namespace,
        "enabled": True,
        "source_kind": "website",
        "source_uri": f"https://{namespace}.example.com/",
        "site_id": namespace.removesuffix("-v1"),
        "title": namespace,
        "summary": f"Knowledge for {namespace}.",
        "aliases": [],
        "tags": ["website"],
        "semantic_origin": "manual",
        "region": REGION,
        "embedding_model": MODEL,
        "embedding_precision": "float32",
        "plan_schema_version": 1,
        "ranking_mode": "page",
        "ranking_profile": "none",
        "ranking_pool": 20,
        "ranking_aggregation": "max",
        "last_plan_id": None,
        "last_apply_id": None,
    }
    field_names = set(CardFields.__dataclass_fields__)
    field_overrides = {key: value for key, value in overrides.items() if key in field_names}
    values.update(field_overrides)
    card = prepare_card(
        CardFields(**values),  # type: ignore[arg-type]
        embedder=FixedEmbedder(),
        now=str(overrides.get("now", "2026-07-18T12:00:00+00:00")),
    )
    direct = {
        key: value
        for key, value in overrides.items()
        if key not in field_names and key != "now"
    }
    if direct:
        card = replace(card, **direct, card_revision="pending")
        card = replace(card, card_revision=card_revision(card))
    return card


EXPECTED_REMOTE_SCHEMA: dict[str, object] = {
    "vector": {"type": "[384]f32", "filterable": False, "ann": {"distance_metric": "cosine_distance"}},
    "namespace": {"type": "string", "filterable": True},
    "enabled": {"type": "bool", "filterable": True},
    "created_at": {"type": "string", "filterable": False},
    "updated_at": {"type": "string", "filterable": False},
    "card_revision": {"type": "string", "filterable": True},
    "last_plan_id": {"type": "string", "filterable": False},
    "last_apply_id": {"type": "string", "filterable": False},
    "source_kind": {"type": "string", "filterable": False},
    "source_uri": {"type": "string", "filterable": False},
    "site_id": {"type": "string", "filterable": False},
    "title": {"type": "string", "filterable": False},
    "summary": {"type": "string", "filterable": False},
    "aliases": {"type": "[]string", "filterable": False},
    "tags": {"type": "[]string", "filterable": False},
    "semantic_origin": {"type": "string", "filterable": False},
    "region": {"type": "string", "filterable": True},
    "embedding_model": {"type": "string", "filterable": False},
    "embedding_precision": {"type": "string", "filterable": True},
    "vector_dimensions": {"type": "uint", "filterable": False},
    "plan_schema_version": {"type": "uint", "filterable": False},
    "ranking_mode": {"type": "string", "filterable": False},
    "ranking_profile": {"type": "string", "filterable": False},
    "ranking_pool": {"type": "uint", "filterable": False},
    "ranking_aggregation": {"type": "string", "filterable": False},
    "routing_model": {"type": "string", "filterable": False},
    "routing_model_revision": {"type": "string", "filterable": False},
    "semantic_hash": {"type": "string", "filterable": False},
    "vector_hash": {"type": "string", "filterable": False},
}
EXPECTED_REMOTE_SCHEMA_V2: dict[str, object] = {
    **EXPECTED_REMOTE_SCHEMA,
    "routing_examples": {"type": "[]string", "filterable": False},
    "routing_prototype_hash": {"type": "string", "filterable": False},
    "routing_prototype_vector": {"type": "[]float", "filterable": False},
    "routing_prototype_vector_hash": {
        "type": "string",
        "filterable": False,
    },
}
EXPECTED_REMOTE_SCHEMA_V3: dict[str, object] = {
    **EXPECTED_REMOTE_SCHEMA_V2,
    "routing_passages": {"type": "[]string", "filterable": False},
    "routing_evidence_vectors": {"type": "[]float", "filterable": False},
    "routing_evidence_vectors_hash": {"type": "string", "filterable": False},
}


def metadata_schema(
    *,
    ann_true: bool = False,
    schema_version: int = REMOTE_SCHEMA_V1,
) -> dict[str, object]:
    schema: dict[str, object] = {"id": {"type": "string"}}
    expected = {
        REMOTE_SCHEMA_V1: EXPECTED_REMOTE_SCHEMA,
        REMOTE_SCHEMA_V2: EXPECTED_REMOTE_SCHEMA_V2,
        REMOTE_SCHEMA_V3: EXPECTED_REMOTE_SCHEMA_V3,
    }[schema_version]
    schema.update(copy.deepcopy(expected))
    for config in schema.values():
        if isinstance(config, dict) and config.get("filterable") is True:
            config.pop("filterable")
    if ann_true:
        schema["vector"]["ann"] = True  # type: ignore[index]
    return {"schema": schema}


class NamespacePage:
    def __init__(
        self,
        ids: list[str],
        next_page: "NamespacePage | None" = None,
        *,
        next_cursor: str | None = None,
    ) -> None:
        self.namespaces = [SimpleNamespace(id=value) for value in ids]
        self._next = next_page
        self.next_cursor = next_cursor
        self.next_calls = 0

    def has_next_page(self) -> bool:
        return self._next is not None

    def next_page_info(self) -> dict[str, str]:
        return {"cursor": self.next_cursor} if self.next_cursor else {}

    def get_next_page(self):  # noqa: ANN201
        self.next_calls += 1
        return self._next


class QueryResource:
    def __init__(
        self,
        cards: list[NamespaceCard],
        *,
        metadata: object | None = None,
        second_pass_cards: list[NamespaceCard] | None = None,
    ) -> None:
        self.cards = list(cards)
        self.metadata_value = metadata or metadata_schema()
        metadata_value = self.metadata_value
        schema = (
            metadata_value.get("schema")
            if isinstance(metadata_value, dict)
            else getattr(metadata_value, "schema", None)
        )
        self.schema_version = (
            REMOTE_SCHEMA_V3
            if isinstance(schema, dict) and "routing_passages" in schema
            else REMOTE_SCHEMA_V2
            if isinstance(schema, dict) and "routing_examples" in schema
            else REMOTE_SCHEMA_V1
        )
        self.second_pass_cards = second_pass_cards
        self.query_calls: list[dict[str, object]] = []
        self.metadata_calls = 0
        self._completed_passes = 0

    def metadata(self, **kwargs: object) -> object:
        self.metadata_calls += 1
        return self.metadata_value

    def query(self, **kwargs: object) -> object:
        self.query_calls.append(kwargs)
        source = self.cards
        if self.second_pass_cards is not None and self._completed_passes >= 1:
            source = self.second_pass_cards
        rows = sorted(
            (
                card_to_remote_row(card, schema_version=self.schema_version)
                for card in source
            ),
            key=lambda row: row["id"],
        )
        filters = kwargs.get("filters")
        if filters is not None:
            field, operator, value = filters  # type: ignore[misc]
            if (field, operator) == ("id", "Gt"):
                rows = [row for row in rows if row["id"] > value]
            elif (field, operator) == ("id", "Eq"):
                rows = [row for row in rows if row["id"] == value]
        limit = int(kwargs.get("top_k", CARD_PAGE_SIZE))
        selected = rows[:limit]
        # A short page completes one full pass.
        if filters is None or (filters[0], filters[1]) == ("id", "Gt"):  # type: ignore[index]
            if len(selected) < limit:
                self._completed_passes += 1
        return {
            "rows": selected,
            "billing": {"billable_logical_bytes_queried": 123, "secret": "tpuf_SHOULD_REDACT"},
        }

    def write(self, **kwargs: object) -> object:
        raise AssertionError(f"read path must not write: {kwargs}")


class FakeClient:
    def __init__(self, list_passes: list[NamespacePage], resource: object) -> None:
        self.list_passes = list(list_passes)
        self.resource = resource
        self.namespace_calls: list[str] = []
        self.namespaces_calls: list[dict[str, object]] = []

    def namespaces(self, **kwargs: object) -> object:
        self.namespaces_calls.append(kwargs)
        if not self.list_passes:
            raise AssertionError("unexpected namespace-list call")
        return self.list_passes.pop(0)

    def namespace(self, namespace: str):  # noqa: ANN201
        self.namespace_calls.append(namespace)
        return self.resource


class StatefulResource(QueryResource):
    def __init__(
        self,
        cards: list[NamespaceCard],
        *,
        metadata: object | None = None,
    ) -> None:
        super().__init__(cards, metadata=metadata)
        self.write_calls: list[dict[str, object]] = []
        self.force_affected_ids: list[str] | None = None

    def write(self, **kwargs: object) -> object:
        self.write_calls.append(kwargs)
        upserts = list(kwargs.get("upsert_rows", []))
        deletes = list(kwargs.get("deletes", []))
        affected: list[str] = []
        by_id = {remote_card_id(card.namespace): card for card in self.cards}
        if upserts:
            condition = kwargs.get("upsert_condition")
            for row in upserts:
                row_id = row["id"]
                current = by_id.get(row_id)
                allowed = False
                if condition == ("id", "Eq", None):
                    allowed = current is None
                elif isinstance(condition, tuple) and condition[:2] == ("card_revision", "Eq"):
                    allowed = current is not None and current.card_revision == condition[2]
                if allowed:
                    card = card_from_remote_row(
                        dict(row),
                        region=REGION,
                        schema_version=self.schema_version,
                    )
                    by_id[row_id] = card
                    affected.append(row_id)
            self.cards = list(by_id.values())
            if self.force_affected_ids is not None:
                affected = list(self.force_affected_ids)
            return {
                "rows_affected": len(affected),
                "upserted_ids": affected or None,
            }
        if deletes:
            condition = kwargs.get("delete_condition")
            for row_id in deletes:
                current = by_id.get(row_id)
                allowed = (
                    current is not None
                    and isinstance(condition, tuple)
                    and condition[:2] == ("card_revision", "Eq")
                    and current.card_revision == condition[2]
                )
                if allowed:
                    del by_id[row_id]
                    affected.append(row_id)
            self.cards = list(by_id.values())
            return {"rows_affected": len(affected), "deleted_ids": affected or None}
        raise AssertionError("unexpected write shape")


class ProviderRow:
    """Provider-shaped row object whose serialization omits null attributes."""

    def __init__(self, row: dict[str, object], *, omit: set[str] | None = None) -> None:
        self.row = row
        self.omit = omit or set()

    def model_dump(self) -> dict[str, object]:
        return {key: value for key, value in self.row.items() if key not in self.omit}


class RemoteSchemaAndCardTests(unittest.TestCase):
    def test_schema_golden_is_complete_independent_and_normalizes_server_defaults(self) -> None:
        self.assertEqual(len(EXPECTED_REMOTE_SCHEMA), 29)
        self.assertEqual(len(REMOTE_CATALOG_SCHEMA), 29)
        self.assertEqual(len(REMOTE_CARD_ATTRIBUTES), 29)
        self.assertEqual(set(EXPECTED_REMOTE_SCHEMA), set(REMOTE_CARD_ATTRIBUTES))
        self.assertEqual(REMOTE_CATALOG_SCHEMA, EXPECTED_REMOTE_SCHEMA)
        self.assertEqual(
            REMOTE_CATALOG_SCHEMA["vector"],
            {
                "type": "[384]f32",
                "filterable": False,
                "ann": {"distance_metric": "cosine_distance"},
            },
        )
        self.assertEqual(REMOTE_CATALOG_SCHEMA["aliases"], {"type": "[]string", "filterable": False})
        normalized = validate_remote_schema(metadata_schema(ann_true=True))
        self.assertEqual(normalized, REMOTE_CATALOG_SCHEMA)

        bad_cases = []
        missing = metadata_schema(); del missing["schema"]["title"]  # type: ignore[index]
        bad_cases.append((missing, "missing"))
        extra = metadata_schema(); extra["schema"]["extra"] = {"type": "string"}  # type: ignore[index]
        bad_cases.append((extra, "extra"))
        changed = metadata_schema(); changed["schema"]["enabled"] = {"type": "string"}  # type: ignore[index]
        bad_cases.append((changed, "changed"))
        indexed = metadata_schema(); indexed["schema"]["summary"]["full_text_search"] = True  # type: ignore[index]
        bad_cases.append((indexed, "changed"))
        wrong_id = metadata_schema(); wrong_id["schema"]["id"] = {"type": "uint"}  # type: ignore[index]
        bad_cases.append((wrong_id, "implicit id"))
        for payload, message in bad_cases:
            with self.subTest(message=message), self.assertRaisesRegex(RemoteCatalogError, message):
                validate_remote_schema(payload)

    def test_schema_v2_v3_are_exact_and_v1_aliases_remain_legacy(self) -> None:
        self.assertIs(REMOTE_CATALOG_SCHEMA_V1, REMOTE_CATALOG_SCHEMA)
        self.assertEqual(REMOTE_CARD_ATTRIBUTES_V1, REMOTE_CARD_ATTRIBUTES)
        self.assertEqual(len(REMOTE_CATALOG_SCHEMA_V2), 33)
        self.assertEqual(len(REMOTE_CARD_ATTRIBUTES_V2), 33)
        self.assertEqual(REMOTE_CATALOG_SCHEMA_V2, EXPECTED_REMOTE_SCHEMA_V2)
        self.assertEqual(len(REMOTE_CATALOG_SCHEMA_V3), 36)
        self.assertEqual(len(REMOTE_CARD_ATTRIBUTES_V3), 36)
        self.assertEqual(REMOTE_CATALOG_SCHEMA_V3, EXPECTED_REMOTE_SCHEMA_V3)
        self.assertEqual(
            validate_remote_schema(
                metadata_schema(schema_version=REMOTE_SCHEMA_V2, ann_true=True)
            ),
            REMOTE_CATALOG_SCHEMA_V2,
        )
        self.assertEqual(
            validate_remote_schema(
                metadata_schema(schema_version=REMOTE_SCHEMA_V3, ann_true=True)
            ),
            REMOTE_CATALOG_SCHEMA_V3,
        )

        hybrid = metadata_schema(schema_version=REMOTE_SCHEMA_V2)
        hybrid["schema"]["routing_examples"] = {"type": "[]string"}  # type: ignore[index]
        with self.assertRaisesRegex(RemoteCatalogError, "changed"):
            validate_remote_schema(hybrid)

        indexed_prototype = metadata_schema(schema_version=REMOTE_SCHEMA_V2)
        indexed_prototype["schema"]["routing_prototype_vector"]["ann"] = {  # type: ignore[index]
            "distance_metric": "cosine_distance"
        }
        with self.assertRaisesRegex(RemoteCatalogError, "changed"):
            validate_remote_schema(indexed_prototype)

        indexed_passages = metadata_schema(schema_version=REMOTE_SCHEMA_V3)
        indexed_passages["schema"]["routing_passages"]["filterable"] = True  # type: ignore[index]
        with self.assertRaisesRegex(RemoteCatalogError, "changed"):
            validate_remote_schema(indexed_passages)

    def test_migration_bindings_are_exact_and_projection_is_schema_stable(self) -> None:
        self.assertEqual(
            REMOTE_CATALOG_SCHEMA_V2_ADDITIONS,
            {
                "routing_examples": {"type": "[]string", "filterable": False},
                "routing_prototype_hash": {"type": "string", "filterable": False},
                "routing_prototype_vector": {"type": "[]float", "filterable": False},
                "routing_prototype_vector_hash": {
                    "type": "string",
                    "filterable": False,
                },
            },
        )
        self.assertEqual(
            REMOTE_CATALOG_SCHEMA_V3_ADDITIONS,
            {
                "routing_passages": {"type": "[]string", "filterable": False},
                "routing_evidence_vectors": {
                    "type": "[]float",
                    "filterable": False,
                },
                "routing_evidence_vectors_hash": {
                    "type": "string",
                    "filterable": False,
                },
            },
        )
        self.assertNotEqual(
            remote_catalog_schema_fingerprint(REMOTE_SCHEMA_V1),
            remote_catalog_schema_fingerprint(REMOTE_SCHEMA_V2),
        )
        self.assertNotEqual(
            remote_catalog_schema_fingerprint(REMOTE_SCHEMA_V2),
            remote_catalog_schema_fingerprint(REMOTE_SCHEMA_V3),
        )
        cards = [make_card("site-a-v1"), make_card("site-b-v1", enabled=False)]
        compatibility = CompatibilityContract(REGION, MODEL, "float32")
        v1 = classify_remote_catalog(
            live_namespace_ids=(
                REMOTE_CATALOG_NAMESPACE,
                "site-a-v1",
                "site-b-v1",
            ),
            cards=cards,
            compatibility=compatibility,
            catalog_schema_version=REMOTE_SCHEMA_V1,
        )
        v2 = replace(v1, catalog_schema_version=REMOTE_SCHEMA_V2)
        v3 = replace(v1, catalog_schema_version=REMOTE_SCHEMA_V3)
        self.assertEqual(
            remote_catalog_projection_sha256(v1),
            remote_catalog_projection_sha256(v2),
        )
        self.assertEqual(
            remote_catalog_projection_sha256(v2),
            remote_catalog_projection_sha256(v3),
        )
        changed_inventory = classify_remote_catalog(
            live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, "site-a-v1"),
            cards=cards,
            compatibility=compatibility,
            catalog_schema_version=REMOTE_SCHEMA_V1,
        )
        self.assertNotEqual(
            remote_catalog_projection_sha256(v1),
            remote_catalog_projection_sha256(changed_inventory),
        )

    def test_provider_shaped_full_schema_omits_only_vector_filterable(self) -> None:
        provider_metadata = SimpleNamespace(schema={
            "id": {"type": "string", "filterable": True},
            "vector": {"type": "[384]f32", "ann": {"distance_metric": "cosine_distance"}},
            "namespace": {"type": "string", "filterable": True},
            "enabled": {"type": "bool", "filterable": True},
            "created_at": {"type": "string", "filterable": False},
            "updated_at": {"type": "string", "filterable": False},
            "card_revision": {"type": "string", "filterable": True},
            "last_plan_id": {"type": "string", "filterable": False},
            "last_apply_id": {"type": "string", "filterable": False},
            "source_kind": {"type": "string", "filterable": False},
            "source_uri": {"type": "string", "filterable": False},
            "site_id": {"type": "string", "filterable": False},
            "title": {"type": "string", "filterable": False},
            "summary": {"type": "string", "filterable": False},
            "aliases": {"type": "[]string", "filterable": False},
            "tags": {"type": "[]string", "filterable": False},
            "semantic_origin": {"type": "string", "filterable": False},
            "region": {"type": "string", "filterable": True},
            "embedding_model": {"type": "string", "filterable": False},
            "embedding_precision": {"type": "string", "filterable": True},
            "vector_dimensions": {"type": "uint", "filterable": False},
            "plan_schema_version": {"type": "uint", "filterable": False},
            "ranking_mode": {"type": "string", "filterable": False},
            "ranking_profile": {"type": "string", "filterable": False},
            "ranking_pool": {"type": "uint", "filterable": False},
            "ranking_aggregation": {"type": "string", "filterable": False},
            "routing_model": {"type": "string", "filterable": False},
            "routing_model_revision": {"type": "string", "filterable": False},
            "semantic_hash": {"type": "string", "filterable": False},
            "vector_hash": {"type": "string", "filterable": False},
        })

        self.assertEqual(validate_remote_schema(provider_metadata), REMOTE_CATALOG_SCHEMA)

    def test_vector_filterable_omission_does_not_weaken_strict_schema_validation(self) -> None:
        other_vector = normalize_remote_schema(
            {"schema": {"other": {"type": "[384]f32"}}}
        )
        self.assertIs(other_vector["other"]["filterable"], True)
        wrong_dimension = normalize_remote_schema(
            {"schema": {"vector": {"type": "[383]f32"}}}
        )
        self.assertIs(wrong_dimension["vector"]["filterable"], True)

        bad_cases: list[tuple[str, dict[str, object]]] = []
        vector_filterable = metadata_schema()
        vector_filterable["schema"]["vector"]["filterable"] = True  # type: ignore[index]
        bad_cases.append(("vector filterable true", vector_filterable))
        wrong_vector_type = metadata_schema()
        wrong_vector_type["schema"]["vector"] = {  # type: ignore[index]
            "type": "[383]f32",
            "ann": {"distance_metric": "cosine_distance"},
        }
        bad_cases.append(("wrong vector type", wrong_vector_type))
        wrong_ann = metadata_schema()
        wrong_ann["schema"]["vector"] = {  # type: ignore[index]
            "type": "[384]f32",
            "ann": {"distance_metric": "euclidean_squared"},
        }
        bad_cases.append(("wrong vector ANN", wrong_ann))
        missing_scalar_flag = metadata_schema()
        missing_scalar_flag["schema"]["summary"].pop("filterable")  # type: ignore[index]
        bad_cases.append(("missing nonfilterable scalar flag", missing_scalar_flag))
        true_scalar_flag = metadata_schema()
        true_scalar_flag["schema"]["summary"]["filterable"] = True  # type: ignore[index]
        bad_cases.append(("true nonfilterable scalar flag", true_scalar_flag))
        wrong_filterable_scalar_flag = metadata_schema()
        wrong_filterable_scalar_flag["schema"]["namespace"]["filterable"] = False  # type: ignore[index]
        bad_cases.append(("false filterable scalar flag", wrong_filterable_scalar_flag))

        for case, payload in bad_cases:
            with self.subTest(case=case), self.assertRaisesRegex(RemoteCatalogError, "changed"):
                validate_remote_schema(payload)

    def test_remote_row_enforces_application_nullability_independently_of_schema(self) -> None:
        card = make_card("site-oscilar-com-v1")
        row = card_to_remote_row(card)
        self.assertIsNone(row["last_plan_id"])
        self.assertIsNone(row["last_apply_id"])
        self.assertEqual(card_from_remote_row(row, region=REGION), card)
        for field in REMOTE_CARD_ATTRIBUTES:
            if field in {"last_plan_id", "last_apply_id"}:
                continue
            invalid = dict(row)
            invalid[field] = None
            with self.subTest(field=field), self.assertRaises(RemoteCatalogError):
                card_from_remote_row(invalid, region=REGION)
        half_lineage = dict(row)
        half_lineage["last_plan_id"] = "plan-only"
        with self.assertRaisesRegex(RemoteCatalogError, "both IDs null or both non-empty"):
            card_from_remote_row(half_lineage, region=REGION)

    def test_provider_row_with_both_nullable_nulls_omitted_is_normalized(self) -> None:
        card = make_card("site-oscilar-com-v1")
        provider_row = ProviderRow(
            card_to_remote_row(card),
            omit={"last_plan_id", "last_apply_id"},
        )
        self.assertEqual(card_from_remote_row(provider_row, region=REGION), card)

    def test_provider_row_with_explicit_nullable_nulls_is_accepted(self) -> None:
        card = make_card("site-oscilar-com-v1")
        self.assertEqual(
            card_from_remote_row(ProviderRow(card_to_remote_row(card)), region=REGION),
            card,
        )

    def test_provider_row_with_one_nullable_null_omitted_is_normalized(self) -> None:
        card = make_card("site-oscilar-com-v1")
        provider_row = ProviderRow(card_to_remote_row(card), omit={"last_apply_id"})
        self.assertEqual(card_from_remote_row(provider_row, region=REGION), card)

    def test_provider_row_with_non_nullable_attribute_omitted_is_rejected(self) -> None:
        card = make_card("site-oscilar-com-v1")
        provider_row = ProviderRow(card_to_remote_row(card), omit={"title"})
        with self.assertRaisesRegex(RemoteCatalogError, "missing=\\['title'\\]"):
            card_from_remote_row(provider_row, region=REGION)

    def test_provider_float_decimal_in_same_float32_bucket_restores_exact_card(self) -> None:
        card = make_card("site-oscilar-com-v1")
        row = card_to_remote_row(card)
        provider_vector = list(card.vector)
        provider_vector[0] = 1.00000001
        row["vector"] = provider_vector

        restored = card_from_remote_row(ProviderRow(row), region=REGION)

        self.assertEqual(restored.vector, card.vector)
        self.assertEqual(restored.vector_hash, vector_hash(card.vector))
        self.assertEqual(restored.card_revision, card_revision(card))
        self.assertEqual(restored, card)

    def test_provider_float_decimal_in_adjacent_float32_bucket_rejects_stale_hash(self) -> None:
        card = make_card("site-oscilar-com-v1")
        row = card_to_remote_row(card)
        provider_vector = list(card.vector)
        provider_vector[0] = 0.99999994
        row["vector"] = provider_vector

        with self.assertRaisesRegex(RemoteCatalogError, "vector_hash is stale or invalid"):
            card_from_remote_row(ProviderRow(row), region=REGION)

    def test_provider_prototype_decimal_in_same_float32_bucket_restores_exact_card(self) -> None:
        card = make_card(
            "site-oscilar-com-v1",
            routing_examples=["Where are retry policies configured?"],
        )
        row = card_to_remote_row(card, schema_version=REMOTE_SCHEMA_V2)
        provider_vector = list(card.routing_prototype_vector)
        provider_vector[0] = 1.00000001
        row["routing_prototype_vector"] = provider_vector

        restored = card_from_remote_row(
            ProviderRow(row),
            region=REGION,
            schema_version=REMOTE_SCHEMA_V2,
        )

        self.assertEqual(restored.routing_prototype_vector, card.routing_prototype_vector)
        self.assertEqual(
            restored.routing_prototype_vector_hash,
            vector_hash(card.routing_prototype_vector),
        )
        self.assertEqual(restored.card_revision, card_revision(card))
        self.assertEqual(restored, card)

    def test_provider_prototype_decimal_in_adjacent_float32_bucket_rejects_stale_hash(self) -> None:
        card = make_card(
            "site-oscilar-com-v1",
            routing_examples=["Where are retry policies configured?"],
        )
        row = card_to_remote_row(card, schema_version=REMOTE_SCHEMA_V2)
        provider_vector = list(card.routing_prototype_vector)
        provider_vector[0] = 0.99999994
        row["routing_prototype_vector"] = provider_vector

        with self.assertRaisesRegex(
            RemoteCatalogError,
            "routing_prototype_vector_hash is stale or invalid",
        ):
            card_from_remote_row(
                ProviderRow(row),
                region=REGION,
                schema_version=REMOTE_SCHEMA_V2,
            )

    def test_provider_empty_prototype_decimal_in_same_float32_bucket_restores_exact_card(self) -> None:
        card = make_card("site-empty-prototype-v1")
        for schema_version in (REMOTE_SCHEMA_V2, REMOTE_SCHEMA_V3):
            with self.subTest(schema_version=schema_version):
                row = card_to_remote_row(card, schema_version=schema_version)
                provider_vector = list(card.routing_prototype_vector)
                provider_vector[0] = 1.00000001
                row["routing_prototype_vector"] = provider_vector

                restored = card_from_remote_row(
                    ProviderRow(row),
                    region=REGION,
                    schema_version=schema_version,
                )

                self.assertEqual(
                    restored.routing_prototype_vector,
                    card.routing_prototype_vector,
                )
                self.assertEqual(
                    restored.routing_prototype_vector_hash,
                    card.routing_prototype_vector_hash,
                )
                self.assertEqual(restored.card_revision, card.card_revision)
                self.assertEqual(restored, card)

    def test_provider_empty_prototype_decimal_in_adjacent_float32_bucket_rejects_stale_hash(self) -> None:
        card = make_card("site-empty-prototype-v1")
        for schema_version in (REMOTE_SCHEMA_V2, REMOTE_SCHEMA_V3):
            row = card_to_remote_row(card, schema_version=schema_version)
            provider_vector = list(card.routing_prototype_vector)
            provider_vector[0] = 0.99999994
            row["routing_prototype_vector"] = provider_vector

            with self.subTest(schema_version=schema_version), self.assertRaisesRegex(
                RemoteCatalogError,
                "routing_prototype_vector_hash is stale or invalid",
            ):
                card_from_remote_row(
                    ProviderRow(row),
                    region=REGION,
                    schema_version=schema_version,
                )

    def test_local_empty_prototype_decimal_drift_remains_strict(self) -> None:
        card = make_card("site-empty-prototype-v1")
        payload = card_to_dict(
            card,
            include_vector=True,
            include_routing_examples=True,
        )
        prototype = list(payload["routing_prototype_vector"])
        prototype[0] = 1.00000001
        payload["routing_prototype_vector"] = prototype

        with self.assertRaisesRegex(
            CatalogError,
            "routing_prototype_vector_hash is stale or invalid",
        ):
            parse_card(payload)

    def test_provider_evidence_decimal_is_float32_canonical_and_hash_bound(self) -> None:
        card = make_card(
            "site-evidence-float-v1",
            routing_passages=["Retry policy defaults and backoff."],
        )
        row = card_to_remote_row(card, schema_version=REMOTE_SCHEMA_V3)
        row["routing_evidence_vectors"][0] = 1.00000001
        self.assertEqual(
            card_from_remote_row(
                ProviderRow(row),
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            ),
            card,
        )

        adjacent = card_to_remote_row(card, schema_version=REMOTE_SCHEMA_V3)
        adjacent["routing_evidence_vectors"][0] = 0.99999994
        with self.assertRaisesRegex(
            RemoteCatalogError,
            "routing_evidence_vectors_hash is stale or invalid",
        ):
            card_from_remote_row(
                ProviderRow(adjacent),
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            )

    def test_provider_vector_rejects_nonfinite_overflow_and_type_errors(self) -> None:
        card = make_card("site-oscilar-com-v1")
        for value in (float("nan"), float("inf"), float("-inf"), 3.5e38, "1.0", True):
            row = card_to_remote_row(card)
            provider_vector = list(card.vector)
            provider_vector[0] = value  # type: ignore[assignment]
            row["vector"] = provider_vector
            with self.subTest(value=value), self.assertRaisesRegex(
                RemoteCatalogError, "vector\\[0\\] must be a finite float32 number"
            ):
                card_from_remote_row(ProviderRow(row), region=REGION)

    def test_provider_exact_float32_vector_is_unchanged(self) -> None:
        card = make_card("site-oscilar-com-v1")

        restored = card_from_remote_row(ProviderRow(card_to_remote_row(card)), region=REGION)

        self.assertEqual(restored.vector, card.vector)
        self.assertEqual(restored, card)

    def test_verification_retry_reads_provider_rows_with_omitted_nulls(self) -> None:
        first = make_card("site-oscilar-com-v1")
        second = make_card("site-turbopuffer-com-v1")

        class OmittedNullQueryResource(QueryResource):
            def query(self, **kwargs: object) -> object:
                response = super().query(**kwargs)
                response["rows"] = [
                    ProviderRow(row, omit={"last_plan_id", "last_apply_id"})
                    for row in response["rows"]
                ]
                return response

        ids = [REMOTE_CATALOG_NAMESPACE, first.namespace, second.namespace]
        client = FakeClient(
            [NamespacePage(ids), NamespacePage(ids)],
            OmittedNullQueryResource([first, second]),
        )
        snapshot = read_remote_catalog(
            client,
            region=REGION,
            compatibility=CompatibilityContract(REGION, MODEL, "float32"),
        )
        self.assertEqual(snapshot.cards, (first, second))
        self.assertEqual(snapshot.counts.card_count, 2)

    def test_remote_id_and_card_row_round_trip_are_provider_neutral(self) -> None:
        card = make_card("site-oscilar-com-v1")
        row_id = remote_card_id(card.namespace)
        self.assertEqual(len(row_id.encode("ascii")), 64)
        self.assertTrue(row_id.startswith("bc_"))
        row = card_to_remote_row(card)
        self.assertEqual(set(row), {"id", *REMOTE_CARD_ATTRIBUTES})
        self.assertEqual(card_from_remote_row(row, region=REGION), card)
        self.assertNotIn("id", card_to_dict(card, include_vector=True))

        wrong_id = dict(row); wrong_id["id"] = "bc_wrong"
        with self.assertRaisesRegex(RemoteCatalogError, "ID mismatch"):
            card_from_remote_row(wrong_id, region=REGION)
        extra = dict(row); extra["typo"] = True
        with self.assertRaisesRegex(RemoteCatalogError, "unknown"):
            card_from_remote_row(extra, region=REGION)
        with self.assertRaisesRegex(RemoteCatalogError, "does not match catalog region"):
            card_from_remote_row(row, region="gcp-us-east4")

    def test_remote_rows_are_schema_versioned_without_incidental_migration(self) -> None:
        legacy = make_card("site-legacy-v1")
        legacy_row = card_to_remote_row(legacy)
        self.assertNotIn("routing_examples", legacy_row)
        self.assertEqual(set(legacy_row), {"id", *REMOTE_CARD_ATTRIBUTES_V1})

        v2_legacy_row = card_to_remote_row(
            legacy, schema_version=REMOTE_SCHEMA_V2
        )
        self.assertEqual(v2_legacy_row["routing_examples"], [])
        self.assertEqual(
            v2_legacy_row["routing_prototype_hash"], legacy.semantic_hash
        )
        self.assertEqual(
            v2_legacy_row["routing_prototype_vector"], legacy.vector
        )
        self.assertEqual(
            v2_legacy_row["routing_prototype_vector_hash"], legacy.vector_hash
        )
        provider_null_row = dict(v2_legacy_row)
        for field in (
            "routing_examples",
            "routing_prototype_hash",
            "routing_prototype_vector",
            "routing_prototype_vector_hash",
        ):
            provider_null_row.pop(field)
        self.assertEqual(
            card_from_remote_row(
                provider_null_row,
                region=REGION,
                schema_version=REMOTE_SCHEMA_V2,
            ),
            legacy,
        )

        v3_legacy_row = card_to_remote_row(
            legacy,
            schema_version=REMOTE_SCHEMA_V3,
        )
        self.assertEqual(v3_legacy_row["routing_passages"], [])
        self.assertEqual(set(v3_legacy_row), {"id", *REMOTE_CARD_ATTRIBUTES_V3})
        v3_bundle = (
            "routing_passages",
            "routing_evidence_vectors",
            "routing_evidence_vectors_hash",
        )
        for null_value in (None, "omitted"):
            provider_null_passages = dict(v3_legacy_row)
            if null_value is None:
                for field in v3_bundle:
                    provider_null_passages[field] = None
            else:
                for field in v3_bundle:
                    provider_null_passages.pop(field)
            with self.subTest(null_value=null_value):
                self.assertEqual(
                    card_from_remote_row(
                        provider_null_passages,
                        region=REGION,
                        schema_version=REMOTE_SCHEMA_V3,
                    ),
                    legacy,
                )

        partial_v3 = dict(v3_legacy_row)
        partial_v3.pop("routing_evidence_vectors_hash")
        with self.assertRaisesRegex(RemoteCatalogError, "missing"):
            card_from_remote_row(
                partial_v3,
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            )

        enhanced = make_card(
            "site-enhanced-v1",
            routing_examples=["How do I configure retries?"],
        )
        with self.assertRaisesRegex(RemoteCatalogError, "reader-first"):
            card_to_remote_row(enhanced, schema_version=REMOTE_SCHEMA_V1)
        enhanced_row = card_to_remote_row(
            enhanced, schema_version=REMOTE_SCHEMA_V2
        )
        self.assertEqual(
            enhanced_row["routing_examples"],
            ["How do I configure retries?"],
        )
        self.assertEqual(set(enhanced_row), {"id", *REMOTE_CARD_ATTRIBUTES_V2})
        self.assertEqual(
            card_from_remote_row(
                enhanced_row,
                region=REGION,
                schema_version=REMOTE_SCHEMA_V2,
            ),
            enhanced,
        )

        passage_card = make_card(
            "site-passage-v1",
            routing_examples=["How do I configure retries?"],
            routing_passages=["Retry policy defaults and exponential backoff."],
        )
        with self.assertRaisesRegex(RemoteCatalogError, "reader-first"):
            card_to_remote_row(passage_card, schema_version=REMOTE_SCHEMA_V1)
        with self.assertRaisesRegex(RemoteCatalogError, "schema-v3 migration"):
            card_to_remote_row(passage_card, schema_version=REMOTE_SCHEMA_V2)
        passage_row = card_to_remote_row(
            passage_card,
            schema_version=REMOTE_SCHEMA_V3,
        )
        self.assertEqual(
            passage_row["routing_passages"],
            ["Retry policy defaults and exponential backoff."],
        )
        self.assertEqual(
            len(passage_row["routing_evidence_vectors"]),
            2 * ROUTING_DIMENSIONS,
        )
        self.assertEqual(
            passage_row["routing_evidence_vectors_hash"],
            vector_hash(passage_row["routing_evidence_vectors"]),
        )
        self.assertEqual(set(passage_row), {"id", *REMOTE_CARD_ATTRIBUTES_V3})
        self.assertEqual(
            card_from_remote_row(
                passage_row,
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            ),
            passage_card,
        )
        passage_without_bank = dict(passage_row)
        passage_without_bank["routing_evidence_vectors"] = []
        passage_without_bank["routing_evidence_vectors_hash"] = ""
        with self.assertRaisesRegex(
            RemoteCatalogError,
            "non-empty routing_passages requires routing_evidence_vectors",
        ):
            card_from_remote_row(
                passage_without_bank,
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            )

        v3_example = make_card(
            "site-v3-example-v1",
            plan_schema_version=PLAN_SCHEMA_VERSION,
            routing_examples=["Where are retry policies configured?"],
        )
        with self.assertRaisesRegex(RemoteCatalogError, "schema-v3 migration"):
            card_to_remote_row(v3_example, schema_version=REMOTE_SCHEMA_V2)
        self.assertEqual(
            card_from_remote_row(
                card_to_remote_row(v3_example, schema_version=REMOTE_SCHEMA_V3),
                region=REGION,
                schema_version=REMOTE_SCHEMA_V3,
            ),
            v3_example,
        )
        for missing_field in (
            "routing_examples",
            "routing_prototype_hash",
            "routing_prototype_vector",
            "routing_prototype_vector_hash",
        ):
            with self.subTest(missing_field=missing_field):
                partial = dict(enhanced_row)
                partial.pop(missing_field)
                with self.assertRaisesRegex(RemoteCatalogError, "partial"):
                    card_from_remote_row(
                        partial,
                        region=REGION,
                        schema_version=REMOTE_SCHEMA_V2,
                    )

    def test_hash_id_collisions_fail_before_classification_or_write(self) -> None:
        cards = [make_card("site-a-v1"), make_card("site-b-v1")]
        with patch("buoy_search.remote_catalog.remote_card_id", return_value="bc_" + "0" * 61):
            with self.assertRaisesRegex(RemoteCatalogError, "ID collision"):
                classify_remote_catalog(
                    live_namespace_ids=[REMOTE_CATALOG_NAMESPACE, "site-a-v1", "site-b-v1"],
                    cards=cards,
                    compatibility=CompatibilityContract(REGION, MODEL, "float32"),
                )
            resource = StatefulResource([])
            with self.assertRaisesRegex(RemoteCatalogError, "ID collision"):
                create_remote_cards(resource, cards, region=REGION)
            self.assertEqual(resource.write_calls, [])

    def test_normalize_schema_rejects_unknown_config_and_bad_ann(self) -> None:
        unknown = metadata_schema(); unknown["schema"]["title"]["mystery"] = True  # type: ignore[index]
        with self.assertRaisesRegex(RemoteCatalogError, "unknown config"):
            normalize_remote_schema(unknown)
        bad_ann = metadata_schema(); bad_ann["schema"]["vector"]["ann"] = "yes"  # type: ignore[index]
        with self.assertRaisesRegex(RemoteCatalogError, "invalid ANN"):
            normalize_remote_schema(bad_ann)


class RemoteReadTests(unittest.TestCase):
    def compatibility(self, **overrides: object) -> CompatibilityContract:
        values = {
            "region": REGION,
            "embedding_model": MODEL,
            "embedding_precision": "float32",
        }
        values.update(overrides)
        return CompatibilityContract(**values)  # type: ignore[arg-type]

    def test_current_compatibility_accepts_plan_lineage_one_two_and_three(self) -> None:
        compatibility = self.compatibility()
        self.assertEqual(compatibility.plan_schema_version, PLAN_SCHEMA_VERSION)
        cards = [
            make_card(
                f"site-plan-{version}-v1",
                plan_schema_version=version,
            )
            for version in (1, 2, PLAN_SCHEMA_VERSION)
        ]

        snapshot = classify_remote_catalog(
            live_namespace_ids=[
                REMOTE_CATALOG_NAMESPACE,
                *(card.namespace for card in cards),
            ],
            cards=cards,
            compatibility=compatibility,
        )

        self.assertEqual(snapshot.incompatible_ids, ())
        self.assertEqual(snapshot.eligible_cards, tuple(cards))

    def test_two_namespace_and_card_passes_capture_exact_requests_counts_and_billing(self) -> None:
        cards = [make_card("site-dagster-io-benchmark-v1"), make_card("site-oscilar-com-v1")]
        ids = [
            REMOTE_CATALOG_NAMESPACE,
            "site-dagster-io-benchmark-v1",
            "site-dagster-io-v1",
            "site-oscilar-com-v1",
            "site-www-thistle-co-v1",
        ]
        first_tail = NamespacePage(ids[3:])
        second_tail = NamespacePage(ids[3:])
        resource = QueryResource(cards)
        client = FakeClient(
            [NamespacePage(ids[:3], first_tail), NamespacePage(ids[:3], second_tail)],
            resource,
        )
        snapshot = read_remote_catalog(client, region=REGION, compatibility=self.compatibility())
        self.assertEqual(
            snapshot.counts,
            CatalogCounts(5, 1, 4, 2, 0, 2, 0, 0, 2),
        )
        self.assertEqual(snapshot.missing_card_ids, ("site-dagster-io-v1", "site-www-thistle-co-v1"))
        self.assertEqual([card.namespace for card in snapshot.eligible_cards], sorted(card.namespace for card in cards))
        self.assertEqual(snapshot.metrics.namespace_list_pages, 4)
        self.assertEqual(snapshot.metrics.metadata_requests, 1)
        self.assertEqual(snapshot.metrics.card_query_pages, 2)
        self.assertEqual(len(snapshot.metrics.billing), 2)
        self.assertEqual(client.namespaces_calls, [{"page_size": NAMESPACE_PAGE_SIZE}] * 2)
        self.assertEqual(client.namespace_calls, [REMOTE_CATALOG_NAMESPACE])
        self.assertEqual(resource.metadata_calls, 1)
        self.assertEqual(len(resource.query_calls), 2)
        for call in resource.query_calls:
            self.assertEqual(call["rank_by"], ("id", "asc"))
            self.assertEqual(call["top_k"], CARD_PAGE_SIZE)
            self.assertEqual(call["include_attributes"], list(REMOTE_CARD_ATTRIBUTES))
            self.assertEqual(call["vector_encoding"], "float")
            self.assertEqual(call["consistency"], {"level": "strong"})
            self.assertNotIn("filters", call)
        self.assertNotIn("tpuf_", str(snapshot.metrics.billing))

    def test_schema_v2_reader_requests_examples_and_normalizes_legacy_nulls(self) -> None:
        card = make_card("site-schema-v2-reader-v1")
        ids = [REMOTE_CATALOG_NAMESPACE, card.namespace]
        resource = QueryResource(
            [card],
            metadata=metadata_schema(schema_version=REMOTE_SCHEMA_V2),
        )
        client = FakeClient([NamespacePage(ids), NamespacePage(ids)], resource)

        snapshot = read_remote_catalog(
            client,
            region=REGION,
            compatibility=self.compatibility(),
        )

        self.assertEqual(snapshot.catalog_schema_version, REMOTE_SCHEMA_V2)
        self.assertEqual(snapshot.cards, (card,))
        self.assertEqual(len(resource.query_calls), 2)
        for call in resource.query_calls:
            self.assertEqual(
                call["include_attributes"], list(REMOTE_CARD_ATTRIBUTES_V2)
            )

    def test_schema_v3_reader_requests_passages_and_normalizes_provider_nulls(self) -> None:
        card = make_card("site-schema-v3-reader-v1")
        ids = [REMOTE_CATALOG_NAMESPACE, card.namespace]
        resource = QueryResource(
            [card],
            metadata=metadata_schema(schema_version=REMOTE_SCHEMA_V3),
        )
        client = FakeClient([NamespacePage(ids), NamespacePage(ids)], resource)

        snapshot = read_remote_catalog(
            client,
            region=REGION,
            compatibility=self.compatibility(),
        )

        self.assertEqual(snapshot.catalog_schema_version, REMOTE_SCHEMA_V3)
        self.assertEqual(snapshot.cards, (card,))
        self.assertEqual(snapshot.cards[0].routing_passages, [])
        for call in resource.query_calls:
            self.assertEqual(
                call["include_attributes"], list(REMOTE_CARD_ATTRIBUTES_V3)
            )

    def test_card_pagination_uses_advancing_id_filter_on_both_passes(self) -> None:
        cards = [make_card(f"site-{index:03d}-v1") for index in range(101)]
        ids = [REMOTE_CATALOG_NAMESPACE, *(card.namespace for card in cards)]
        resource = QueryResource(cards)
        client = FakeClient([NamespacePage(ids), NamespacePage(ids)], resource)
        snapshot = read_remote_catalog(client, region=REGION, compatibility=self.compatibility())
        self.assertEqual(snapshot.counts.eligible_count, 101)
        self.assertEqual(snapshot.metrics.card_query_pages, 4)
        self.assertEqual(len(resource.query_calls), 4)
        self.assertNotIn("filters", resource.query_calls[0])
        self.assertEqual(resource.query_calls[1]["filters"][:2], ("id", "Gt"))
        self.assertNotIn("filters", resource.query_calls[2])
        self.assertEqual(resource.query_calls[3]["filters"][:2], ("id", "Gt"))

    def test_card_and_namespace_instability_fail_closed(self) -> None:
        card = make_card()
        changed = make_card(title="Changed", aliases=[])
        client = FakeClient(
            [
                NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
                NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
            ],
            QueryResource([card], second_pass_cards=[changed]),
        )
        with self.assertRaisesRegex(RemoteCatalogError, "changed between"):
            read_remote_catalog(client, region=REGION, compatibility=self.compatibility())

        resource = QueryResource([card])
        client = FakeClient(
            [
                NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace]),
                NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace, "site-new-v1"]),
            ],
            resource,
        )
        with self.assertRaisesRegex(RemoteCatalogError, "namespace listing changed"):
            read_remote_catalog(client, region=REGION, compatibility=self.compatibility())

    def test_missing_catalog_schema_error_duplicate_listing_and_nonadvancing_pages_fail(self) -> None:
        card = make_card()
        missing_client = FakeClient([NamespacePage([card.namespace])], QueryResource([card]))
        with self.assertRaisesRegex(RemoteCatalogMissingError, "does not exist"):
            read_remote_catalog(missing_client, region=REGION, compatibility=self.compatibility())

        bad_schema = metadata_schema(); bad_schema["schema"]["title"] = {"type": "uint"}  # type: ignore[index]
        schema_client = FakeClient(
            [NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace])],
            QueryResource([card], metadata=bad_schema),
        )
        with self.assertRaisesRegex(RemoteCatalogError, "schema mismatch"):
            read_remote_catalog(schema_client, region=REGION, compatibility=self.compatibility())

        duplicate_client = FakeClient(
            [NamespacePage([REMOTE_CATALOG_NAMESPACE, card.namespace, card.namespace])],
            QueryResource([card]),
        )
        with self.assertRaisesRegex(RemoteCatalogError, "repeated ID"):
            read_remote_catalog(duplicate_client, region=REGION, compatibility=self.compatibility())

        empty_next = NamespacePage([], NamespacePage([REMOTE_CATALOG_NAMESPACE]))
        nonadvance_client = FakeClient([empty_next], QueryResource([card]))
        with self.assertRaisesRegex(RemoteCatalogError, "did not advance"):
            read_remote_catalog(nonadvance_client, region=REGION, compatibility=self.compatibility())

    def test_pagination_repeated_cursor_and_page_bounds_fail_closed(self) -> None:
        card = make_card()
        repeated_cursor = FakeClient(
            [
                NamespacePage(
                    [REMOTE_CATALOG_NAMESPACE],
                    NamespacePage([card.namespace], next_cursor="same"),
                    next_cursor="same",
                )
            ],
            QueryResource([card]),
        )
        with self.assertRaisesRegex(RemoteCatalogError, "cursor/signature"):
            read_remote_catalog(repeated_cursor, region=REGION, compatibility=self.compatibility())

        three_pages = NamespacePage(
            [REMOTE_CATALOG_NAMESPACE],
            NamespacePage([card.namespace], NamespacePage(["site-third-v1"], next_cursor="c3"), next_cursor="c2"),
            next_cursor="c1",
        )
        with patch("buoy_search.remote_catalog.MAX_PAGES_PER_PASS", 2):
            with self.assertRaisesRegex(RemoteCatalogError, "exceeded 2 pages"):
                read_remote_catalog(FakeClient([three_pages], QueryResource([card])), region=REGION, compatibility=self.compatibility())

        cards = [make_card(f"site-{index:03d}-v1") for index in range(101)]
        ids = [REMOTE_CATALOG_NAMESPACE, *(item.namespace for item in cards)]
        with patch("buoy_search.remote_catalog.MAX_PAGES_PER_PASS", 1):
            with self.assertRaisesRegex(RemoteCatalogError, "card query exceeded 1 pages"):
                read_remote_catalog(
                    FakeClient([NamespacePage(ids)], QueryResource(cards)),
                    region=REGION,
                    compatibility=self.compatibility(),
                )

    def test_generic_zero_eligible_snapshot_is_diagnostic_but_routing_requirement_fails(self) -> None:
        snapshot = classify_remote_catalog(
            live_namespace_ids=[REMOTE_CATALOG_NAMESPACE, "site-missing-v1"],
            cards=[],
            compatibility=self.compatibility(),
        )
        self.assertEqual(snapshot.counts.eligible_count, 0)
        self.assertEqual(snapshot.missing_card_ids, ("site-missing-v1",))
        with self.assertRaisesRegex(RemoteCatalogError, "buoy catalog list --all"):
            require_eligible(snapshot)

        resource = QueryResource([])
        read_snapshot = read_remote_catalog(
            FakeClient(
                [
                    NamespacePage([REMOTE_CATALOG_NAMESPACE, "site-missing-v1"]),
                    NamespacePage([REMOTE_CATALOG_NAMESPACE, "site-missing-v1"]),
                ],
                resource,
            ),
            region=REGION,
            compatibility=self.compatibility(),
        )
        self.assertEqual(read_snapshot.counts.eligible_count, 0)
        with self.assertRaisesRegex(RemoteCatalogError, "no eligible live remote namespace cards"):
            require_eligible(read_snapshot)

    def test_classification_precedence_stale_missing_disabled_incompatible_eligible(self) -> None:
        eligible = make_card("site-eligible-v1")
        disabled = make_card("site-disabled-v1", enabled=False)
        incompatible = make_card("site-incompatible-v1", embedding_precision="float16")
        stale = make_card("site-stale-v1", enabled=False, embedding_precision="float16")
        snapshot = classify_remote_catalog(
            live_namespace_ids=[
                REMOTE_CATALOG_NAMESPACE,
                eligible.namespace,
                disabled.namespace,
                incompatible.namespace,
                "site-missing-v1",
            ],
            cards=[eligible, disabled, incompatible, stale],
            compatibility=self.compatibility(),
        )
        self.assertEqual(snapshot.stale_target_ids, (stale.namespace,))
        self.assertEqual(snapshot.missing_card_ids, ("site-missing-v1",))
        self.assertEqual(snapshot.disabled_ids, (disabled.namespace,))
        self.assertEqual(snapshot.incompatible_ids, (incompatible.namespace,))
        self.assertEqual([card.namespace for card in snapshot.eligible_cards], [eligible.namespace])
        self.assertEqual(snapshot.counts, CatalogCounts(5, 1, 4, 4, 1, 1, 1, 1, 1))

    def test_complete_routing_coverage_blocks_missing_and_incompatible_only(self) -> None:
        eligible = make_card("eligible")
        disabled = make_card("disabled", enabled=False)
        incompatible = make_card("incompatible", embedding_model="other/model")
        stale = make_card("stale")
        snapshot = classify_remote_catalog(
            live_namespace_ids=(
                REMOTE_CATALOG_NAMESPACE,
                "eligible",
                "disabled",
                "incompatible",
                "missing",
            ),
            cards=(eligible, disabled, incompatible, stale),
            compatibility=self.compatibility(),
        )

        with self.assertRaises(RemoteCatalogError) as raised:
            require_complete_routing_coverage(snapshot)
        message = str(raised.exception)
        self.assertIn("missing cards: 'missing'", message)
        self.assertIn("incompatible cards: 'incompatible'", message)
        self.assertIn("buoy catalog upsert missing ... --approve", message)
        self.assertNotIn("disabled cards", message)
        self.assertNotIn("stale cards", message)

        complete = classify_remote_catalog(
            live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, "eligible", "disabled"),
            cards=(eligible, disabled, stale),
            compatibility=self.compatibility(),
        )
        self.assertIs(require_complete_routing_coverage(complete), complete)

    def test_internal_evidence_namespaces_are_not_content_or_missing_cards(self) -> None:
        eligible = make_card("site-eligible-v1")
        snapshot = classify_remote_catalog(
            live_namespace_ids=[
                REMOTE_CATALOG_NAMESPACE,
                eligible.namespace,
                "buoy-evidence-branch-deadbeef-source",
                "buoy-evidence-ledger-deadbeef",
            ],
            cards=[eligible],
            compatibility=self.compatibility(),
        )
        self.assertEqual(snapshot.live_namespace_ids, (eligible.namespace,))
        self.assertEqual(snapshot.missing_card_ids, ())
        self.assertEqual(snapshot.counts.content_live_count, 1)
        self.assertEqual(snapshot.counts.control_plane_count, 3)
        self.assertEqual(snapshot.counts.listed_total, 4)

    def test_account_inventory_counts_five_content_and_three_control_namespaces(self) -> None:
        content_ids = tuple(f"site-content-{index}-v1" for index in range(5))
        snapshot = classify_remote_catalog(
            live_namespace_ids=[
                REMOTE_CATALOG_NAMESPACE,
                *content_ids,
                "buoy-evidence-branch-deadbeef-source",
                "buoy-evidence-ledger-deadbeef",
            ],
            cards=[make_card(namespace) for namespace in content_ids],
            compatibility=self.compatibility(),
        )

        self.assertEqual(snapshot.counts.listed_total, 8)
        self.assertEqual(snapshot.counts.content_live_count, 5)
        self.assertEqual(snapshot.counts.control_plane_count, 3)
        self.assertEqual(
            snapshot.counts.listed_total,
            snapshot.counts.content_live_count + snapshot.counts.control_plane_count,
        )


class MutationTests(unittest.TestCase):
    def test_schema_v2_migration_is_one_exact_schema_only_write(self) -> None:
        class SchemaOnlyResource:
            def __init__(self, response: object) -> None:
                self.response = response
                self.write_calls: list[dict[str, object]] = []

            def write(self, **kwargs: object) -> object:
                self.write_calls.append(kwargs)
                return self.response

        resource = SchemaOnlyResource(
            {
                "status": "OK",
                "rows_affected": 0,
                "rows_deleted": 0,
                "rows_patched": 0,
                "rows_upserted": 0,
                "deleted_ids": None,
                "patched_ids": None,
                "upserted_ids": None,
                "billing": {"write_units": 1},
            }
        )
        result = migrate_remote_catalog_schema_v2(resource)  # type: ignore[arg-type]
        self.assertTrue(result.changed)
        self.assertEqual(result.rows_affected, 0)
        self.assertEqual(result.affected_ids, ())
        self.assertEqual(result.metrics.write_requests, 1)
        self.assertEqual(result.metrics.verification_query_requests, 0)
        self.assertEqual(result.metrics.billing, ({"write_units": 1},))
        self.assertEqual(
            resource.write_calls,
            [
                {
                    "distance_metric": DISTANCE_METRIC,
                    "schema": REMOTE_CATALOG_SCHEMA_V2,
                }
            ],
        )

        for response in (
            {"rows_affected": 0},
            {"status": "OK", "rows_affected": 1},
            {"status": "NO", "rows_affected": 0},
            {"status": "OK", "rows_affected": 0, "rows_remaining": True},
            {"status": "OK", "rows_affected": 0, "rows_upserted": 1},
            {"status": "OK", "rows_affected": 0, "upserted_ids": ["row"]},
        ):
            with self.subTest(response=response), self.assertRaises(RemoteCatalogError):
                migrate_remote_catalog_schema_v2(  # type: ignore[arg-type]
                    SchemaOnlyResource(response)
                )

    def test_schema_v3_migration_is_schema_only(self) -> None:
        class SchemaOnlyResource:
            def __init__(self) -> None:
                self.write_calls: list[dict[str, object]] = []

            def write(self, **kwargs: object) -> object:
                self.write_calls.append(kwargs)
                return {
                    "status": "OK",
                    "rows_affected": 0,
                    "rows_deleted": 0,
                    "rows_patched": 0,
                    "rows_upserted": 0,
                    "deleted_ids": None,
                    "patched_ids": None,
                    "upserted_ids": None,
                    "billing": {"write_units": 1},
                }

        resource = SchemaOnlyResource()
        result = migrate_remote_catalog_schema_v3(resource)  # type: ignore[arg-type]
        self.assertTrue(result.changed)
        self.assertEqual(
            resource.write_calls,
            [{"distance_metric": DISTANCE_METRIC, "schema": REMOTE_CATALOG_SCHEMA_V3}],
        )

    def test_mutations_prevalidate_region_reserved_target_duplicates_and_revision(self) -> None:
        card = make_card()
        wrong_region = make_card(region="gcp-us-east4")
        reserved = make_card(REMOTE_CATALOG_NAMESPACE)
        resource = StatefulResource([card])
        for cards, message in (
            ([wrong_region], "does not match resolved region"),
            ([reserved], "reserved routing catalog"),
            ([card, card], "duplicate target namespace"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(RemoteCatalogError, message):
                create_remote_cards(resource, cards, region=REGION)
        self.assertEqual(resource.write_calls, [])

        with self.assertRaisesRegex(RemoteCatalogError, "does not match resolved region"):
            update_remote_card(
                resource,
                wrong_region,
                expected_revision=card.card_revision,
                region=REGION,
            )
        with self.assertRaisesRegex(RemoteCatalogError, "non-empty string"):
            update_remote_card(resource, card, expected_revision="", region=REGION)
        self.assertEqual(resource.write_calls, [])

    def test_create_is_conditional_exact_verified_and_idempotent(self) -> None:
        card = make_card()
        resource = StatefulResource([])
        result = create_remote_cards(resource, [card], region=REGION)
        self.assertTrue(result.changed)
        self.assertEqual(result.affected_ids, (remote_card_id(card.namespace),))
        call = resource.write_calls[0]
        self.assertEqual(call["schema"], REMOTE_CATALOG_SCHEMA)
        self.assertEqual(call["distance_metric"], DISTANCE_METRIC)
        self.assertEqual(call["upsert_condition"], ("id", "Eq", None))
        self.assertTrue(call["return_affected_ids"])
        repeated = create_remote_cards(resource, [card], region=REGION)
        self.assertFalse(repeated.changed)
        self.assertEqual(repeated.rows_affected, 0)

    def test_example_writes_require_explicit_v2_and_keep_the_v2_schema(self) -> None:
        card = make_card(
            "site-example-write-v1",
            routing_examples=["Where are retry policies configured?"],
        )
        v1_resource = StatefulResource([])
        with self.assertRaisesRegex(RemoteCatalogError, "reader-first"):
            create_remote_cards(v1_resource, [card], region=REGION)
        self.assertEqual(v1_resource.write_calls, [])

        v2_resource = StatefulResource(
            [], metadata=metadata_schema(schema_version=REMOTE_SCHEMA_V2)
        )
        result = create_remote_cards(
            v2_resource,
            [card],
            region=REGION,
            schema_version=REMOTE_SCHEMA_V2,
        )
        self.assertTrue(result.changed)
        call = v2_resource.write_calls[0]
        self.assertEqual(call["schema"], REMOTE_CATALOG_SCHEMA_V2)
        self.assertEqual(
            call["upsert_rows"][0]["routing_examples"],
            ["Where are retry policies configured?"],
        )
        self.assertIn("routing_prototype_hash", call["upsert_rows"][0])
        self.assertIn("routing_prototype_vector", call["upsert_rows"][0])
        self.assertIn("routing_prototype_vector_hash", call["upsert_rows"][0])
        self.assertNotIn(
            "ann", call["schema"]["routing_prototype_vector"]
        )

    def test_two_card_partial_create_race_is_detected(self) -> None:
        cards = [make_card("site-a-v1"), make_card("site-b-v1")]
        resource = StatefulResource([])
        resource.force_affected_ids = [remote_card_id(cards[0].namespace)]
        with self.assertRaisesRegex(RemoteCatalogError, "unexpected IDs"):
            create_remote_cards(resource, cards, region=REGION)

    def test_update_binds_exact_revision_and_affected_id(self) -> None:
        old = make_card(last_plan_id="plan-old", last_apply_id="apply-old")
        new = make_card(
            title="Updated",
            aliases=[],
            last_plan_id="plan-new",
            last_apply_id="apply-new",
            now="2026-07-18T13:00:00+00:00",
        )
        resource = StatefulResource([old])
        updated = update_remote_card(
            resource,
            new,
            expected_revision=old.card_revision,
            region=REGION,
        )
        self.assertTrue(updated.changed)
        self.assertEqual(resource.write_calls[-1]["upsert_condition"], ("card_revision", "Eq", old.card_revision))
        with self.assertRaisesRegex(RemoteCatalogError, "newer remote revision"):
            update_remote_card(resource, old, expected_revision=old.card_revision, region=REGION)

    def test_update_verification_accepts_provider_prototype_decimal_drift(self) -> None:
        class PrototypeDriftResource(StatefulResource):
            def query(self, **kwargs: object) -> object:
                response = super().query(**kwargs)
                rows = response["rows"]
                for row in rows:
                    if row.get("routing_examples"):
                        vector = list(row["routing_prototype_vector"])
                        vector[0] = 1.00000001
                        row["routing_prototype_vector"] = vector
                return response

        old = make_card("site-example-v1")
        intended = make_card(
            "site-example-v1",
            routing_examples=["Where are retry policies configured?"],
            now="2026-07-18T13:00:00+00:00",
        )
        resource = PrototypeDriftResource(
            [old],
            metadata=metadata_schema(schema_version=REMOTE_SCHEMA_V2),
        )

        result = update_remote_card(
            resource,
            intended,
            expected_revision=old.card_revision,
            region=REGION,
            schema_version=REMOTE_SCHEMA_V2,
        )

        self.assertTrue(result.changed)
        self.assertEqual(result.card, intended)
        self.assertEqual(result.affected_ids, (remote_card_id(intended.namespace),))
        self.assertEqual(result.metrics.write_requests, 1)
        self.assertEqual(result.metrics.verification_query_requests, 2)


class ErrorTests(unittest.TestCase):
    def test_errors_are_single_call_bounded_and_redacted(self) -> None:
        secret = "tpuf_ABC123SECRET"
        self.assertNotIn(secret, redact_remote_error(f"Authorization: Bearer {secret}"))
        self.assertEqual(redact_remote_error(f"Authorization: Bearer {secret}"), "<redacted provider payload>")

        class FailingClient:
            def __init__(self) -> None:
                self.calls = 0

            def namespaces(self, **kwargs: object) -> object:
                self.calls += 1
                raise RuntimeError(f"429 Authorization=Bearer {secret}")

        client = FailingClient()
        with self.assertRaisesRegex(RemoteCatalogError, "namespace listing failed") as raised:
            read_remote_catalog(
                client,  # type: ignore[arg-type]
                region=REGION,
                compatibility=CompatibilityContract(REGION, MODEL, "float32"),
            )
        self.assertEqual(client.calls, 1)
        self.assertNotIn(secret, str(raised.exception))
        self.assertNotIn("Authorization", str(raised.exception))

        class PermissionFailure(Exception):
            status_code = 403

        dangerous = "tpuf_TOKEN body={'vector':[1.0,2.0], 'secret':'credential'}"
        for error, expected in (
            (PermissionFailure(dangerous), "PermissionFailure, status=403"),
            (TimeoutError(dangerous), "TimeoutError, timeout"),
            (RuntimeError(dangerous), "RuntimeError"),
        ):
            class ErrorClient:
                def namespaces(self, **kwargs: object) -> object:
                    raise error

            with self.subTest(error=error), self.assertRaisesRegex(RemoteCatalogError, expected) as failure:
                read_remote_catalog(
                    ErrorClient(),  # type: ignore[arg-type]
                    region=REGION,
                    compatibility=CompatibilityContract(REGION, MODEL, "float32"),
                )
            rendered = str(failure.exception)
            for forbidden in ("tpuf_TOKEN", "vector", "credential", "1.0", "body"):
                self.assertNotIn(forbidden, rendered)

    def test_formatted_provider_tracebacks_never_chain_raw_factory_list_query_or_write_payloads(self) -> None:
        secret_key = "tpuf_RAW"
        raw = f"{secret_key} credential body={{'vector':[0.1,0.2], 'token':'secret'}}"

        class ProviderFailure(Exception):
            status_code = 403

        class FailingTP:
            def __init__(self, **kwargs: object) -> None:
                raise ProviderFailure(raw)

        with patch.dict("sys.modules", {"turbopuffer": SimpleNamespace(Turbopuffer=FailingTP)}):
            factory_trace = formatted_remote_failure(
                lambda: create_client(api_key=secret_key, region=REGION)
            )

        class ListClient:
            def namespaces(self, **kwargs: object) -> object:
                raise ProviderFailure(raw)

        list_trace = formatted_remote_failure(
            lambda: read_remote_catalog(
                ListClient(),  # type: ignore[arg-type]
                region=REGION,
                compatibility=CompatibilityContract(REGION, MODEL, "float32"),
            )
        )

        class QueryFailureResource(QueryResource):
            def query(self, **kwargs: object) -> object:
                raise ProviderFailure(raw)

        query_trace = formatted_remote_failure(
            lambda: read_remote_catalog(
                FakeClient(
                    [NamespacePage([REMOTE_CATALOG_NAMESPACE, "site-example-v1"])],
                    QueryFailureResource([make_card()]),
                ),
                region=REGION,
                compatibility=CompatibilityContract(REGION, MODEL, "float32"),
            )
        )

        class WriteFailureResource(QueryResource):
            def write(self, **kwargs: object) -> object:
                raise ProviderFailure(raw)

        write_trace = formatted_remote_failure(
            lambda: create_remote_cards(WriteFailureResource([]), [make_card()], region=REGION)
        )

        for rendered, phase in (
            (factory_trace, "client construction"),
            (list_trace, "namespace listing"),
            (query_trace, "card page query"),
            (write_trace, "conditional card create"),
        ):
            with self.subTest(phase=phase):
                self.assertIn(phase, rendered)
                self.assertIn("ProviderFailure, status=403", rendered)
                self.assertNotIn("The above exception", rendered)
                self.assertNotIn("During handling", rendered)
                for forbidden in (
                    "tpuf_RAW",
                    "credential body",
                    "'vector':[0.1,0.2]",
                    "'token':'secret'",
                ):
                    self.assertNotIn(forbidden, rendered)

    def test_every_sdk_shape_boundary_redacts_resource_page_conversion_and_write_failures(self) -> None:
        secret = "tpuf_BOUNDARY_SECRET"
        raw = f"Authorization: Bearer {secret}; body={{'token':'{secret}'}}"

        class ProviderFailure(Exception):
            status_code = 403

        class ResourceFailureClient:
            def namespaces(self, **_kwargs: object) -> object:
                return [
                    SimpleNamespace(id=REMOTE_CATALOG_NAMESPACE),
                    SimpleNamespace(id="site-example-v1"),
                ]

            def namespace(self, _namespace: str) -> object:
                raise ProviderFailure(raw)

        class HasNextFailurePage:
            namespaces = [SimpleNamespace(id=REMOTE_CATALOG_NAMESPACE)]

            def has_next_page(self) -> bool:
                raise ProviderFailure(raw)

        class PageFailureClient:
            def __init__(self, page: object) -> None:
                self.page = page

            def namespaces(self, **_kwargs: object) -> object:
                return self.page

        class FailingIterable:
            def __iter__(self):  # noqa: ANN204 - adversarial provider shape.
                raise ProviderFailure(raw)

        class IterationFailurePage:
            namespaces = FailingIterable()

        class FailingSummary:
            def to_dict(self) -> dict[str, object]:
                raise ProviderFailure(raw)

        class ConversionFailurePage:
            namespaces = [FailingSummary()]

        class FailingWriteResponse:
            def to_dict(self) -> dict[str, object]:
                raise ProviderFailure(raw)

        class WriteResponseFailureResource(QueryResource):
            def write(self, **_kwargs: object) -> object:
                return FailingWriteResponse()

        read_contract = CompatibilityContract(REGION, MODEL, "float32")
        failures = (
            (
                "namespace resource acquisition",
                lambda: read_remote_catalog(
                    ResourceFailureClient(),  # type: ignore[arg-type]
                    region=REGION,
                    compatibility=read_contract,
                ),
            ),
            (
                "namespace pagination state read",
                lambda: read_remote_catalog(
                    PageFailureClient(HasNextFailurePage()),  # type: ignore[arg-type]
                    region=REGION,
                    compatibility=read_contract,
                ),
            ),
            (
                "namespace listing response is not iterable",
                lambda: read_remote_catalog(
                    PageFailureClient(IterationFailurePage()),  # type: ignore[arg-type]
                    region=REGION,
                    compatibility=read_contract,
                ),
            ),
            (
                "namespace summary normalization",
                lambda: read_remote_catalog(
                    PageFailureClient(ConversionFailurePage()),  # type: ignore[arg-type]
                    region=REGION,
                    compatibility=read_contract,
                ),
            ),
            (
                "card write response normalization",
                lambda: create_remote_cards(
                    WriteResponseFailureResource([]),
                    [make_card()],
                    region=REGION,
                ),
            ),
        )
        for phase, call in failures:
            with self.subTest(phase=phase):
                rendered = formatted_remote_failure(call)
                self.assertIn(phase, rendered)
                self.assertIn("ProviderFailure, status=403", rendered)
                self.assertNotIn(secret, rendered)
                self.assertNotIn("Authorization", rendered)
                self.assertNotIn("'token'", rendered)

    def test_explicit_client_adapter_does_not_read_environment(self) -> None:
        calls: list[dict[str, object]] = []

        class FakeTP:
            def __init__(self, **kwargs: object) -> None:
                calls.append(kwargs)

        fake_module = SimpleNamespace(Turbopuffer=FakeTP)
        with patch.dict("sys.modules", {"turbopuffer": fake_module}), patch.dict(
            os.environ,
            {"TURBOPUFFER_API_KEY": "must-not-read", "TURBOPUFFER_REGION": "must-not-read"},
        ):
            client = create_client(api_key="explicit-key", region=REGION)
        self.assertIsInstance(client, FakeTP)
        self.assertEqual(calls, [{"api_key": "explicit-key", "region": REGION}])

        class FailingTP:
            def __init__(self, **kwargs: object) -> None:
                raise RuntimeError(f"bad explicit-secret-key in {kwargs}")

        with patch.dict("sys.modules", {"turbopuffer": SimpleNamespace(Turbopuffer=FailingTP)}):
            with self.assertRaisesRegex(RemoteCatalogError, "RuntimeError") as raised:
                create_client(api_key="explicit-secret-key", region=REGION)
        self.assertNotIn("explicit-secret-key", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
