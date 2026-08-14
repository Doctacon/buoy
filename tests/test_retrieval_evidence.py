from __future__ import annotations

from dataclasses import dataclass
import json
import unittest

from buoy_search.config import RuntimeConfig
from buoy_search.retriever import (
    CalibratedEvidenceAssessor,
    EvidenceRouteContext,
    HybridRetriever,
    MultiNamespaceRetriever,
    ProviderCallError,
    RetrievalOptions,
    SearchHit,
)


class RecordingEmbedder:
    def encode(self, _texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2, 0.3]]


class Namespace:
    def __init__(
        self,
        name: str,
        ids: list[str],
        calls: list[str],
        *,
        fails: bool = False,
    ) -> None:
        self.name = name
        self.ids = ids
        self.calls = calls
        self.fails = fails

    def multi_query(self, **_kwargs: object) -> dict[str, object]:
        self.calls.append(self.name)
        if self.fails:
            raise RuntimeError("secret provider detail")
        return {
            "rows": [
                {
                    "id": row_id,
                    "attributes": {
                        "title": f"{self.name} {row_id}",
                        "url": f"https://example.test/{self.name}/{row_id}",
                        "content": f"content for {row_id}",
                    },
                }
                for row_id in self.ids
            ]
        }


class OrdinalReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str]) -> list[float]:
        self.calls.append((query, list(passages)))
        return [float(len(passages) - index) for index in range(len(passages))]


@dataclass(frozen=True)
class Decision:
    status: str
    is_weak: bool | None

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "reason": "test_decision",
            "model": "test-model",
        }


class RecordingAssessor:
    def __init__(
        self,
        mode: str,
        decisions: list[Decision],
        *,
        error: Exception | None = None,
    ) -> None:
        self.mode = mode
        self.decisions = list(decisions)
        self.error = error
        self.calls: list[dict[str, object]] = []

    def assess(self, **kwargs: object) -> Decision:
        self.calls.append(dict(kwargs))
        if self.error is not None:
            raise self.error
        return self.decisions.pop(0)


ROUTE_CONTEXT = EvidenceRouteContext(
    selection_reason="high_confidence_semantic",
    semantic_score=0.81,
    semantic_margin=0.11,
)


class RetrievalEvidenceOrchestrationTests(unittest.TestCase):
    def make_retriever(
        self,
        namespaces: list[Namespace],
        *,
        reranker: OrdinalReranker | None = None,
    ) -> MultiNamespaceRetriever:
        embedder = RecordingEmbedder()
        retrievers = [
            HybridRetriever(
                namespace=namespace,
                embedder=embedder,
                config=RuntimeConfig(namespace=f"namespace-{index}"),
            )
            for index, namespace in enumerate(namespaces)
        ]
        scorer = reranker or OrdinalReranker()
        return MultiNamespaceRetriever(
            retrievers=retrievers,
            embedder=embedder,
            reranker_loader=lambda: scorer,
        )

    def test_explicit_call_without_assessor_keeps_payload_unchanged(self) -> None:
        calls: list[str] = []
        result = self.make_retriever(
            [Namespace("one", ["a"], calls)]
        ).retrieve("query", [RetrievalOptions()])

        self.assertNotIn("evidence", result.to_dict())
        self.assertEqual([hit.id for hit in result.hits], ["a"])

    def test_strong_singleton_assesses_exact_returned_top_k(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "active", [Decision("supported", False)]
        )
        result = self.make_retriever(
            [
                Namespace("one", [f"a{index}" for index in range(7)], calls),
                Namespace("two", ["b"], calls),
                Namespace("three", ["c"], calls),
            ]
        ).retrieve(
            "query",
            [RetrievalOptions(top_k=2)] * 3,
            initial_fanout=1,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertEqual(calls, ["one"])
        self.assertEqual(len(assessor.calls), 1)
        self.assertEqual(len(assessor.calls[0]["hits"]), 2)
        self.assertIsNone(assessor.calls[0]["existing_scores"])
        self.assertEqual([hit.id for hit in result.hits], ["a0", "a1"])
        self.assertEqual(result.evidence["status"], "supported")
        self.assertFalse(result.fallback.widened)

    def test_weak_singleton_widens_once_and_reuses_final_reranker_scores(self) -> None:
        calls: list[str] = []
        reranker = OrdinalReranker()
        assessor = RecordingAssessor(
            "active",
            [
                Decision("no_relevant_evidence", True),
                Decision("supported", False),
            ],
        )
        result = self.make_retriever(
            [
                Namespace("one", ["a1", "a2"], calls),
                Namespace("two", ["b1", "b2"], calls),
                Namespace("three", ["c1", "c2"], calls),
            ],
            reranker=reranker,
        ).retrieve(
            "query",
            [RetrievalOptions(top_k=2)] * 3,
            initial_fanout=1,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertCountEqual(calls, ["one", "two", "three"])
        self.assertEqual(result.fallback.reason, "weak_top1")
        self.assertEqual(len(assessor.calls), 2)
        self.assertIsNone(assessor.calls[0]["existing_scores"])
        self.assertEqual(len(assessor.calls[1]["existing_scores"]), 2)
        self.assertEqual(len(reranker.calls), 1)
        self.assertEqual(len(result.hits), 2)
        self.assertEqual(result.evidence["status"], "supported")
        self.assertTrue(
            result.evidence["widening_triggered_by_weak_evidence"]
        )

    def test_final_weak_complete_active_result_abstains(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "active", [Decision("no_relevant_evidence", True)]
        )
        result = self.make_retriever(
            [
                Namespace("one", ["a"], calls),
                Namespace("two", ["b"], calls),
            ]
        ).retrieve(
            "query",
            [RetrievalOptions()] * 2,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertEqual(result.hits, [])
        self.assertFalse(result.incomplete)
        self.assertEqual(result.evidence["status"], "no_relevant_evidence")

    def test_final_weak_partial_active_result_is_inconclusive(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "active", [Decision("inconclusive", True)]
        )
        result = self.make_retriever(
            [
                Namespace("one", ["a"], calls),
                Namespace("two", [], calls, fails=True),
            ]
        ).retrieve(
            "query",
            [RetrievalOptions()] * 2,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertEqual(result.hits, [])
        self.assertTrue(result.incomplete)
        self.assertEqual(result.evidence["status"], "inconclusive")
        self.assertEqual(assessor.calls[0]["namespace_failure_count"], 1)

    def test_shadow_weak_widens_but_preserves_final_hits(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "shadow",
            [
                Decision("would_abstain", True),
                Decision("would_abstain", True),
            ],
        )
        result = self.make_retriever(
            [
                Namespace("one", ["a"], calls),
                Namespace("two", ["b"], calls),
            ]
        ).retrieve(
            "query",
            [RetrievalOptions()] * 2,
            initial_fanout=1,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertEqual(result.fallback.reason, "weak_top1")
        self.assertEqual(result.evidence["status"], "would_abstain")
        self.assertNotEqual(result.hits, [])

    def test_collect_preserves_singleton_and_does_not_invent_widening(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "collect", [Decision("unassessed", None)]
        )
        result = self.make_retriever(
            [
                Namespace("one", ["a"], calls),
                Namespace("two", ["b"], calls),
            ]
        ).retrieve(
            "query",
            [RetrievalOptions()] * 2,
            initial_fanout=1,
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        self.assertEqual(calls, ["one"])
        self.assertEqual(result.evidence["status"], "unassessed")
        self.assertEqual([hit.id for hit in result.hits], ["a"])

    def test_assessment_failure_is_fatal_active_but_redacted_shadow(self) -> None:
        for mode, fatal in (("active", True), ("shadow", False)):
            with self.subTest(mode=mode):
                calls: list[str] = []
                assessor = RecordingAssessor(
                    mode,
                    [],
                    error=RuntimeError("model leaked secret"),
                )
                retriever = self.make_retriever(
                    [Namespace("one", ["a"], calls)]
                )
                if fatal:
                    with self.assertRaisesRegex(
                        RuntimeError, "Automatic evidence assessment failed"
                    ) as raised:
                        retriever.retrieve(
                            "query",
                            [RetrievalOptions()],
                            evidence_assessor=assessor,
                            evidence_route_context=ROUTE_CONTEXT,
                        )
                    self.assertNotIn("secret", str(raised.exception))
                else:
                    result = retriever.retrieve(
                        "query",
                        [RetrievalOptions()],
                        evidence_assessor=assessor,
                        evidence_route_context=ROUTE_CONTEXT,
                    )
                    payload = result.to_dict()
                    self.assertEqual(payload["evidence"]["status"], "assessment_failed")
                    self.assertEqual([hit.id for hit in result.hits], ["a"])
                    self.assertNotIn("secret", json.dumps(payload))

    def test_custom_assessor_cannot_add_content_to_public_diagnostics(self) -> None:
        @dataclass(frozen=True)
        class ContentBearingDecision:
            status: str = "unassessed"
            is_weak: bool | None = None

            def to_dict(self) -> dict[str, object]:
                return {
                    "status": self.status,
                    "reason": "test_decision",
                    "query": "private query",
                    "content": "private result content",
                }

        calls: list[str] = []
        assessor = RecordingAssessor("collect", [ContentBearingDecision()])
        result = self.make_retriever(
            [Namespace("one", ["a"], calls)]
        ).retrieve(
            "private query",
            [RetrievalOptions()],
            evidence_assessor=assessor,
            evidence_route_context=ROUTE_CONTEXT,
        )

        rendered = json.dumps(result.evidence)
        self.assertNotIn("private query", rendered)
        self.assertNotIn("private result content", rendered)

    def test_all_namespace_failure_remains_provider_error(self) -> None:
        calls: list[str] = []
        assessor = RecordingAssessor(
            "active", [Decision("inconclusive", True)]
        )
        retriever = self.make_retriever(
            [
                Namespace("one", [], calls, fails=True),
                Namespace("two", [], calls, fails=True),
            ]
        )

        with self.assertRaises(ProviderCallError):
            retriever.retrieve(
                "query",
                [RetrievalOptions()] * 2,
                evidence_assessor=assessor,
                evidence_route_context=ROUTE_CONTEXT,
            )
        self.assertEqual(assessor.calls, [])


class CalibratedEvidenceAssessorTests(unittest.TestCase):
    def test_existing_scores_bypass_model_and_bind_route_context(self) -> None:
        from unittest.mock import patch

        calibration = type("Calibration", (), {"mode": "collect"})()
        decision = Decision("unassessed", None)
        with patch(
            "buoy_search.retriever.observe_evidence_scores",
            return_value="observation",
        ) as observe, patch(
            "buoy_search.retriever.decide_evidence", return_value=decision
        ) as decide:
            assessor = CalibratedEvidenceAssessor(
                calibration,  # type: ignore[arg-type]
                reranker_loader=lambda: (_ for _ in ()).throw(
                    AssertionError("model loaded")
                ),
            )
            actual = assessor.assess(
                query="query",
                hits=[SearchHit(id="one")],
                existing_scores=[0.75],
                route_context=ROUTE_CONTEXT,
                namespace_failure_count=1,
                widening_triggered_by_weak_evidence=True,
            )

        self.assertIs(actual, decision)
        observe.assert_called_once_with(
            [0.75],
            route_selection_reason="high_confidence_semantic",
            route_semantic_score=0.81,
            route_semantic_margin=0.11,
            namespace_failure_count=1,
        )
        decide.assert_called_once_with(
            calibration,
            "observation",
            widening_triggered_by_weak_evidence=True,
        )

    def test_missing_existing_scores_scores_the_exact_hits_once(self) -> None:
        from unittest.mock import patch

        calibration = type("Calibration", (), {"mode": "collect"})()
        decision = Decision("unassessed", None)
        reranker = OrdinalReranker()
        hits = [
            SearchHit(
                id="one",
                title="First",
                url="https://example.test/first",
                content="first evidence",
            ),
            SearchHit(id="two", title="Second", content="second evidence"),
        ]
        with patch(
            "buoy_search.retriever.observe_evidence_scores",
            return_value="observation",
        ) as observe, patch(
            "buoy_search.retriever.decide_evidence", return_value=decision
        ):
            assessor = CalibratedEvidenceAssessor(
                calibration,  # type: ignore[arg-type]
                reranker_loader=lambda: reranker,
            )
            assessor.assess(
                query="query",
                hits=hits,
                existing_scores=None,
                route_context=ROUTE_CONTEXT,
                namespace_failure_count=0,
                widening_triggered_by_weak_evidence=False,
            )

        self.assertEqual(len(reranker.calls), 1)
        self.assertEqual(len(reranker.calls[0][1]), 2)
        self.assertIn("First", reranker.calls[0][1][0])
        self.assertIn("first evidence", reranker.calls[0][1][0])
        observe.assert_called_once_with(
            [2.0, 1.0],
            route_selection_reason="high_confidence_semantic",
            route_semantic_score=0.81,
            route_semantic_margin=0.11,
            namespace_failure_count=0,
        )


if __name__ == "__main__":
    unittest.main()
