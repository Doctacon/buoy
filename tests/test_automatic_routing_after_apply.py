from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import buoy_search.apply as apply_module
import buoy_search.catalog as catalog_module
import buoy_search.cli as cli_module
import buoy_search.retriever as retriever_module
from buoy_search.applied_state import load_applied_state
from buoy_search.apply import load_verified_apply_plan, run_approved_apply
from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    CardFields,
    prepare_card,
)
from buoy_search.cli import main
from buoy_search.config import RuntimeConfig
from buoy_search.plan_artifacts import write_plan_artifacts
from buoy_search.remote_catalog import REMOTE_CATALOG_NAMESPACE, REMOTE_SCHEMA_V3
from buoy_search.routing_quality import load_routing_confidence_calibration
from tests.test_apply_cli import build_for_current_state, write_page
from tests.test_remote_catalog import (
    FakeClient,
    NamespacePage,
    StatefulResource,
    metadata_schema,
)


REGION = "gcp-us-central1"
TARGET_PHRASE = "quantum barnacle failover"


def unit_vector(index: int) -> list[float]:
    vector = [0.0] * ROUTING_DIMENSIONS
    vector[index] = 1.0
    return vector


def cosine_vector(score: float) -> list[float]:
    vector = [0.0] * ROUTING_DIMENSIONS
    vector[0] = score
    vector[1] = math.sqrt(1.0 - score * score)
    return vector


class LocalContentAwareEmbedder:
    """Tiny deterministic stand-in for the pinned local routing model."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001 - routing embedder protocol fake.
        values = list(texts)
        self.calls.append(values)
        vectors: list[list[float]] = []
        for value in values:
            lowered = value.casefold()
            if TARGET_PHRASE in lowered:
                vectors.append(unit_vector(0))
                continue
            for index in range(1, 8):
                if f"orthogonal topic {index}" in lowered:
                    vectors.append(unit_vector(index))
                    break
            else:
                vectors.append(unit_vector(8))
        return vectors


class QueryEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts, *, batch_size: int = 32):  # noqa: ANN001 - model fake.
        del batch_size
        values = list(texts)
        self.calls.append(values)
        return [unit_vector(0) for _value in values]


class ContentAwareReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages):  # noqa: ANN001 - reranker protocol fake.
        values = list(passages)
        self.calls.append((query, values))
        return [
            10.0 if TARGET_PHRASE in value.casefold() else 0.0
            for value in values
        ]


class FixedVectorEmbedder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = list(vector)

    def encode(self, texts):  # noqa: ANN001 - routing embedder protocol fake.
        return [list(self.vector) for _value in texts]


def distractor_card(namespace: str):  # noqa: ANN201 - focused fixture helper.
    return prepare_card(
        CardFields(
            namespace=namespace,
            enabled=True,
            source_kind="website",
            source_uri=f"https://{namespace}.example/docs",
            site_id=f"site-{namespace}",
            title=f"Competitor {namespace}",
            summary="Generic documentation with no matching specialist capability.",
            aliases=[],
            tags=["website"],
            semantic_origin="manual",
            region=REGION,
            embedding_model=ROUTING_MODEL,
            embedding_precision="float32",
            plan_schema_version=3,
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
        ),
        embedder=FixedVectorEmbedder(cosine_vector(0.4)),
        now="2026-08-16T00:00:00+00:00",
    )


class FakeContentNamespace:
    def __init__(self, provider: "FakeProvider", namespace: str) -> None:
        self.provider = provider
        self.namespace = namespace

    def multi_query(self, **kwargs: object) -> dict[str, object]:
        self.provider.content_query_calls.append((self.namespace, dict(kwargs)))
        rows = self.provider.content_rows.get(self.namespace, {})
        return {"rows": [dict(row) for row in rows.values()]}


class FakeContentWriter:
    def __init__(self, provider: "FakeProvider", *, config: RuntimeConfig) -> None:
        self.provider = provider
        self.namespace = config.namespace

    def upsert_rows(self, rows) -> None:  # noqa: ANN001 - writer protocol fake.
        stored = self.provider.content_rows.setdefault(self.namespace, {})
        for row in rows:
            stored[str(row["id"])] = dict(row)

    def delete_rows(self, row_ids) -> None:  # noqa: ANN001 - writer protocol fake.
        stored = self.provider.content_rows.setdefault(self.namespace, {})
        for row_id in row_ids:
            stored.pop(str(row_id), None)


class FakeProvider:
    """One in-memory provider shared by apply, catalog read, and retrieval."""

    def __init__(self, *, target_namespace: str, distractors: list[object]) -> None:
        self.target_namespace = target_namespace
        self.catalog_resource = StatefulResource(
            list(distractors),
            metadata=metadata_schema(schema_version=REMOTE_SCHEMA_V3),
        )
        self.live_namespaces = list(dict.fromkeys([
            REMOTE_CATALOG_NAMESPACE,
            *(card.namespace for card in distractors),
            target_namespace,
        ]))
        self.catalog_clients: list[FakeClient] = []
        self.content_rows: dict[str, dict[str, dict[str, object]]] = {}
        self.content_query_calls: list[tuple[str, dict[str, object]]] = []
        self.apply_embedding_calls: list[list[str]] = []
        self.retrieval_embedding_calls: list[list[str]] = []

    def catalog_client(self, **_kwargs: object) -> FakeClient:
        client = FakeClient(
            [
                NamespacePage(list(self.live_namespaces)),
                NamespacePage(list(self.live_namespaces)),
            ],
            self.catalog_resource,
        )
        self.catalog_clients.append(client)
        return client

    def writer(self, *, config: RuntimeConfig, **_kwargs: object) -> FakeContentWriter:
        return FakeContentWriter(self, config=config)

    def content_namespace(
        self,
        *,
        config: RuntimeConfig,
        api_key: str,
    ) -> FakeContentNamespace:
        if api_key != "test-key":
            raise AssertionError("unexpected fake-provider credential")
        return FakeContentNamespace(self, config.namespace)

    def apply_embedder(self, *_args: object, **_kwargs: object) -> QueryEmbedder:
        embedder = QueryEmbedder()
        original_encode = embedder.encode

        def encode(texts, *, batch_size: int = 32):  # noqa: ANN001, ANN202
            values = list(texts)
            self.apply_embedding_calls.append(values)
            return original_encode(values, batch_size=batch_size)

        embedder.encode = encode  # type: ignore[method-assign]
        return embedder

    def retrieval_embedder(self, *_args: object, **_kwargs: object) -> QueryEmbedder:
        embedder = QueryEmbedder()
        original_encode = embedder.encode

        def encode(texts, *, batch_size: int = 32):  # noqa: ANN001, ANN202
            values = list(texts)
            self.retrieval_embedding_calls.append(values)
            return original_encode(values, batch_size=batch_size)

        embedder.encode = encode  # type: ignore[method-assign]
        return embedder


class AutomaticRoutingAfterApplyAcceptanceTests(unittest.TestCase):
    def test_approved_apply_is_immediately_namespace_free_retrievable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / "pages"
            write_page(
                corpus,
                "00-specialist.md",
                "https://example.com/docs/specialist",
                "Specialist guide",
                (
                    "# Reliability\n\nConfigure quantum barnacle failover for "
                    "interplanetary request recovery."
                ),
            )
            for index in range(1, 8):
                write_page(
                    corpus,
                    f"{index:02d}.md",
                    f"https://example.com/docs/topic-{index}",
                    f"Topic {index}",
                    f"# Topic {index}\n\nOrthogonal topic {index} reference material.",
                )

            state_root = root / "state"
            out_dir = root / "plan"
            namespace = "fresh-docs"
            artifacts = build_for_current_state(
                corpus=corpus,
                out_dir=out_dir,
                state_root=state_root,
                namespace=namespace,
            )
            write_plan_artifacts(artifacts, out_dir)
            verified = load_verified_apply_plan(
                plan_path=out_dir / "plan.json",
                namespace=namespace,
                state_root=state_root,
            )
            overlap_passage = str(
                verified.routing_prototypes[-1]["passage_text"]
            )
            existing_target = prepare_card(
                CardFields(
                    namespace=namespace,
                    enabled=True,
                    source_kind="website",
                    source_uri="https://operator.example/docs",
                    site_id="operator-target",
                    title="Operator target",
                    summary="Generic operator-owned routing summary.",
                    aliases=[],
                    tags=["website"],
                    semantic_origin="manual",
                    region=REGION,
                    embedding_model=ROUTING_MODEL,
                    embedding_precision="float32",
                    plan_schema_version=3,
                    ranking_mode="page",
                    ranking_profile="none",
                    ranking_pool=20,
                    ranking_aggregation="max",
                    routing_examples=[overlap_passage],
                ),
                embedder=LocalContentAwareEmbedder(),
                now="2026-08-16T00:00:00+00:00",
            )
            distractors = [
                existing_target,
                *[
                    distractor_card(f"competitor-{index:02d}")
                    for index in range(12)
                ],
            ]
            provider = FakeProvider(
                target_namespace=namespace,
                distractors=distractors,
            )
            card_embedder = LocalContentAwareEmbedder()
            route_embedder = QueryEmbedder()
            route_reranker = ContentAwareReranker()
            retrieval_reranker = ContentAwareReranker()
            confidence = load_routing_confidence_calibration()

            with patch.dict(
                os.environ,
                {"TURBOPUFFER_API_KEY": "test-key"},
                clear=True,
            ), patch.object(
                apply_module,
                "SentenceTransformerEmbedder",
                side_effect=provider.apply_embedder,
            ), patch.object(
                apply_module,
                "TurbopufferWriter",
                side_effect=provider.writer,
            ), patch.object(
                apply_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=provider.catalog_client,
            ), patch.object(
                catalog_module,
                "load_routing_embedder",
                return_value=card_embedder,
            ), patch.object(
                cli_module,
                "REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=provider.catalog_client,
            ), patch.object(
                cli_module,
                "ROUTING_CONFIDENCE_FACTORY",
                return_value=confidence,
            ), patch.object(
                cli_module,
                "ROUTING_EMBEDDER_FACTORY",
                return_value=route_embedder,
            ), patch.object(
                cli_module,
                "ROUTING_RERANKER_FACTORY",
                return_value=route_reranker,
            ), patch.object(
                retriever_module,
                "SentenceTransformerEmbedder",
                side_effect=provider.retrieval_embedder,
            ), patch.object(
                retriever_module,
                "build_namespace",
                side_effect=provider.content_namespace,
            ), patch.object(
                retriever_module,
                "load_cross_encoder_reranker",
                return_value=retrieval_reranker,
            ):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(region=REGION, namespace=namespace),
                    namespace=namespace,
                    batch_size=4,
                    embedding_batch_size=4,
                )

                stdout = StringIO()
                stderr = StringIO()
                with redirect_stdout(stdout), redirect_stderr(stderr):
                    result = main(
                        [
                            "retrieve",
                            "How do I configure quantum barnacle failover?",
                            "--json",
                        ]
                    )

            payload = json.loads(stdout.getvalue())
            state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            applied_card = next(
                card
                for card in provider.catalog_resource.cards
                if card.namespace == namespace
            )

        self.assertEqual(result, 0, stderr.getvalue())
        self.assertFalse(summary["partial_success"])
        self.assertTrue(summary["content_applied"])
        self.assertTrue(summary["state_updated"])
        self.assertTrue(summary["catalog_registered"])
        self.assertTrue(summary["automatic_retrieval_ready"])
        self.assertEqual(summary["rows_upserted"], 8)
        self.assertEqual(len(provider.content_rows[namespace]), 8)
        self.assertEqual(len(state.rows), 8)
        self.assertEqual(state.last_apply_id, summary["apply_id"])

        reviewed_passages = [
            str(prototype["passage_text"])
            for prototype in verified.routing_prototypes
        ]
        self.assertEqual(applied_card.routing_examples, [overlap_passage])
        self.assertNotIn(overlap_passage, applied_card.routing_passages)
        self.assertEqual(
            applied_card.routing_passages,
            [passage for passage in reviewed_passages if passage != overlap_passage],
        )
        self.assertEqual(
            len(applied_card.routing_examples) + len(applied_card.routing_passages),
            8,
        )
        self.assertEqual(len(card_embedder.calls), 1)
        self.assertEqual(len(card_embedder.calls[0]), 9)
        self.assertLess(applied_card.routing_prototype_vector[0], 0.4)
        generic_metadata = " ".join(
            (
                applied_card.source_uri,
                applied_card.title,
                applied_card.summary,
                *applied_card.aliases,
                *applied_card.tags,
            )
        ).casefold()
        self.assertNotIn(TARGET_PHRASE, generic_metadata)
        self.assertTrue(
            any(TARGET_PHRASE in passage.casefold() for passage in applied_card.routing_passages)
        )

        # Apply registration and retrieval each construct a fresh catalog client
        # and execute the real strong two-pass catalog reader over shared state.
        self.assertEqual(len(provider.catalog_clients), 2)
        self.assertEqual(provider.catalog_resource.metadata_calls, 2)
        self.assertEqual(
            [len(client.namespaces_calls) for client in provider.catalog_clients],
            [2, 2],
        )

        self.assertTrue(payload["content_retrieval_occurred"])
        self.assertEqual(
            payload["routing"]["selected_cards"][0]["namespace"],
            namespace,
        )
        self.assertEqual(payload["routing"]["initial_fanout"], 3)
        self.assertEqual(payload["routing"]["routing_confidence_mode"], "provisional")
        self.assertEqual(payload["hits"][0]["namespace"], namespace)
        self.assertIn(TARGET_PHRASE, payload["hits"][0]["content"].casefold())
        self.assertNotIn(TARGET_PHRASE, json.dumps(payload["routing"]).casefold())
        self.assertEqual(len(route_embedder.calls), 1)
        self.assertEqual(len(route_reranker.calls), 1)
        self.assertEqual(len(route_reranker.calls[0][1]), 20)
        queried_namespaces = [
            namespace_value
            for namespace_value, _kwargs in provider.content_query_calls
        ]
        self.assertEqual(len(queried_namespaces), 3)
        self.assertIn(namespace, queried_namespaces)
        self.assertGreaterEqual(len(retrieval_reranker.calls), 1)


if __name__ == "__main__":
    unittest.main()
