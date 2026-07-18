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
    NamespaceCard,
    card_revision,
    card_to_dict,
    prepare_card,
    vector_hash,
)
from buoy_search.remote_catalog import (
    CARD_PAGE_SIZE,
    DISTANCE_METRIC,
    MAX_PAGES_PER_PASS,
    NAMESPACE_PAGE_SIZE,
    REMOTE_CARD_ATTRIBUTES,
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_CATALOG_SCHEMA,
    CatalogCounts,
    CompatibilityContract,
    RemoteCatalogError,
    card_from_remote_row,
    card_to_remote_row,
    classify_migration_state,
    classify_remote_catalog,
    create_client,
    create_remote_cards,
    delete_remote_card,
    normalize_remote_schema,
    read_remote_catalog,
    rebase_remote_card,
    require_eligible,
    redact_remote_error,
    remote_card_id,
    update_remote_card,
    validate_accept_remote,
    validate_remote_schema,
)

UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)
SECOND_UNIT_VECTOR = [0.0, 1.0] + [0.0] * (ROUTING_DIMENSIONS - 2)
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


def metadata_schema(*, ann_true: bool = False) -> dict[str, object]:
    schema: dict[str, object] = {"id": {"type": "string"}}
    schema.update(copy.deepcopy(EXPECTED_REMOTE_SCHEMA))
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
        rows = sorted((card_to_remote_row(card) for card in source), key=lambda row: row["id"])
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
    def __init__(self, cards: list[NamespaceCard]) -> None:
        super().__init__(cards)
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
                    card = card_from_remote_row(dict(row), region=REGION)
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
        with self.assertRaisesRegex(RemoteCatalogError, "does not exist"):
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


class MutationAndMigrationTests(unittest.TestCase):
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
        with self.assertRaisesRegex(RemoteCatalogError, "reserved routing catalog"):
            delete_remote_card(
                resource,
                namespace=REMOTE_CATALOG_NAMESPACE,
                expected_revision=card.card_revision,
                region=REGION,
            )
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

    def test_two_card_partial_create_race_is_detected(self) -> None:
        cards = [make_card("site-a-v1"), make_card("site-b-v1")]
        resource = StatefulResource([])
        resource.force_affected_ids = [remote_card_id(cards[0].namespace)]
        with self.assertRaisesRegex(RemoteCatalogError, "unexpected IDs"):
            create_remote_cards(resource, cards, region=REGION)

    def test_update_and_delete_bind_exact_revision_and_affected_id(self) -> None:
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

        with self.assertRaisesRegex(RemoteCatalogError, "newer remote revision"):
            delete_remote_card(
                resource,
                namespace=new.namespace,
                expected_revision=old.card_revision,
                region=REGION,
            )
        deleted = delete_remote_card(
            resource,
            namespace=new.namespace,
            expected_revision=new.card_revision,
            region=REGION,
        )
        self.assertTrue(deleted.changed)
        self.assertEqual(resource.write_calls[-1]["distance_metric"], DISTANCE_METRIC)
        self.assertEqual(resource.write_calls[-1]["delete_condition"], ("card_revision", "Eq", new.card_revision))
        with self.assertRaisesRegex(RemoteCatalogError, "card is absent"):
            delete_remote_card(
                resource,
                namespace=new.namespace,
                expected_revision=new.card_revision,
                region=REGION,
            )

    def test_migration_classifier_covers_absent_empty_partial_exact_and_conflicts(self) -> None:
        first = make_card("site-a-v1")
        second = make_card("site-b-v1")
        intended = [first, second]
        self.assertEqual(
            classify_migration_state(catalog_exists=False, existing_cards=[], intended_cards=intended).state,
            "absent",
        )
        self.assertEqual(
            classify_migration_state(catalog_exists=True, existing_cards=[], intended_cards=intended).state,
            "empty",
        )
        partial = classify_migration_state(
            catalog_exists=True,
            existing_cards=[first],
            intended_cards=intended,
        )
        self.assertEqual(partial.state, "partial")
        self.assertEqual([card.namespace for card in partial.missing_cards], [second.namespace])
        self.assertEqual(
            classify_migration_state(catalog_exists=True, existing_cards=intended, intended_cards=intended).state,
            "exact",
        )
        changed = make_card("site-a-v1", title="Different", aliases=[])
        self.assertEqual(
            classify_migration_state(
                catalog_exists=True,
                existing_cards=[changed],
                intended_cards=intended,
            ).state,
            "conflict",
        )
        extra = make_card("site-extra-v1")
        self.assertEqual(
            classify_migration_state(
                catalog_exists=True,
                existing_cards=[first, extra],
                intended_cards=intended,
            ).state,
            "conflict",
        )
        self.assertEqual(
            classify_migration_state(
                catalog_exists=True,
                schema_valid=False,
                existing_cards=[],
                intended_cards=intended,
            ).state,
            "conflict",
        )


class RecoveryAndErrorTests(unittest.TestCase):
    def test_rebase_preserves_manual_semantics_enabled_and_pending_system_lineage(self) -> None:
        base = make_card(last_plan_id="plan-old", last_apply_id="apply-old")
        current = make_card(
            enabled=False,
            title="Human title",
            summary="Human summary.",
            aliases=["human alias"],
            tags=["manual"],
            last_plan_id="plan-old",
            last_apply_id="apply-old",
            now="2026-07-18T13:00:00+00:00",
        )
        current = replace(current, created_at=base.created_at, card_revision="pending")
        current = replace(current, card_revision=card_revision(current))
        pending = make_card(
            semantic_origin="generated",
            title="Generated",
            summary="Generated.",
            aliases=[],
            tags=["website"],
            last_plan_id="plan-new",
            last_apply_id="apply-new",
            ranking_pool=30,
            now="2026-07-18T14:00:00+00:00",
        )
        embedder = FixedEmbedder(SECOND_UNIT_VECTOR)
        rebased = rebase_remote_card(base=base, current=current, pending=pending, embedder=embedder)
        self.assertFalse(rebased.enabled)
        self.assertEqual((rebased.title, rebased.summary), (current.title, current.summary))
        self.assertEqual((rebased.last_plan_id, rebased.last_apply_id), ("plan-new", "apply-new"))
        self.assertEqual(rebased.ranking_pool, 30)
        self.assertEqual(rebased.vector, SECOND_UNIT_VECTOR)
        self.assertEqual(len(embedder.calls), 1)

        unsafe = replace(current, region="gcp-us-east4", card_revision="pending")
        unsafe = replace(unsafe, card_revision=card_revision(unsafe))
        with self.assertRaisesRegex(RemoteCatalogError, "unsafe concurrent"):
            rebase_remote_card(base=base, current=unsafe, pending=pending)
        changed_creation = replace(current, created_at="2026-07-18T11:00:00+00:00", card_revision="pending")
        changed_creation = replace(changed_creation, card_revision=card_revision(changed_creation))
        with self.assertRaisesRegex(RemoteCatalogError, "created_at"):
            rebase_remote_card(base=base, current=changed_creation, pending=pending)

        tampered = replace(
            base,
            enabled=False,
            updated_at="2026-07-18T13:00:00+00:00",
            vector=SECOND_UNIT_VECTOR,
            vector_hash=vector_hash(SECOND_UNIT_VECTOR),
            card_revision="pending",
        )
        tampered = replace(tampered, card_revision=card_revision(tampered))
        with self.assertRaisesRegex(RemoteCatalogError, "projection differs from base"):
            rebase_remote_card(base=base, current=tampered, pending=pending)

        enabled_only = replace(
            base,
            enabled=False,
            updated_at="2026-07-18T13:00:00+00:00",
            card_revision="pending",
        )
        enabled_only = replace(enabled_only, card_revision=card_revision(enabled_only))
        unchanged = rebase_remote_card(base=base, current=enabled_only, pending=pending)
        self.assertFalse(unchanged.enabled)
        self.assertEqual(unchanged.vector, base.vector)

    def test_first_apply_manual_race_requires_exact_system_contract_and_null_lineage(self) -> None:
        current = make_card(title="Human", aliases=["human alias"])
        pending = make_card(
            semantic_origin="generated",
            title="Generated",
            aliases=[],
            last_plan_id="plan-new",
            last_apply_id="apply-new",
        )
        embedder = FixedEmbedder(SECOND_UNIT_VECTOR)
        rebased = rebase_remote_card(base=None, current=current, pending=pending, embedder=embedder)
        self.assertEqual(rebased.title, "Human")
        self.assertEqual(rebased.last_apply_id, "apply-new")
        self.assertEqual(rebased.vector, SECOND_UNIT_VECTOR)
        self.assertEqual(len(embedder.calls), 1)
        with self.assertRaisesRegex(RemoteCatalogError, "injected routing embedder"):
            rebase_remote_card(base=None, current=current, pending=pending)
        mismatch = make_card(title="Human", aliases=["human alias"], ranking_pool=30)
        with self.assertRaisesRegex(RemoteCatalogError, "ranking_pool differs"):
            rebase_remote_card(base=None, current=mismatch, pending=pending)
        lineage = make_card(last_plan_id="other-plan", last_apply_id="other-apply")
        with self.assertRaisesRegex(RemoteCatalogError, "lineage-free"):
            rebase_remote_card(base=None, current=lineage, pending=pending)

    def test_accept_remote_binds_exact_revision_and_different_complete_lineage_without_clock(self) -> None:
        pending = make_card(last_plan_id="plan-z", last_apply_id="apply_2099_future")
        current = make_card(last_plan_id="plan-a", last_apply_id="apply_2000_past")
        accepted = validate_accept_remote(
            current_reads=[current, current],
            pending=pending,
            expected_remote_revision=current.card_revision,
        )
        self.assertEqual(accepted, current)
        with self.assertRaisesRegex(RemoteCatalogError, "operator-supplied"):
            validate_accept_remote(
                current_reads=[current, current],
                pending=pending,
                expected_remote_revision="0" * 64,
            )
        no_lineage = make_card()
        with self.assertRaisesRegex(RemoteCatalogError, "complete apply lineage"):
            validate_accept_remote(
                current_reads=[no_lineage, no_lineage],
                pending=pending,
                expected_remote_revision=no_lineage.card_revision,
            )
        same = make_card(last_plan_id="plan-z", last_apply_id="apply_2099_future")
        with self.assertRaisesRegex(RemoteCatalogError, "different apply lineage"):
            validate_accept_remote(
                current_reads=[same, same],
                pending=pending,
                expected_remote_revision=same.card_revision,
            )
        changed = make_card(
            title="Changed between reads",
            aliases=[],
            last_plan_id="plan-a",
            last_apply_id="apply_2000_past",
        )
        with self.assertRaisesRegex(RemoteCatalogError, "changed between strong reads"):
            validate_accept_remote(
                current_reads=[current, changed],
                pending=pending,
                expected_remote_revision=current.card_revision,
            )
        with self.assertRaisesRegex(RemoteCatalogError, "exactly two"):
            validate_accept_remote(
                current_reads=[current],
                pending=pending,
                expected_remote_revision=current.card_revision,
            )

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
