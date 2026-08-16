from __future__ import annotations

from dataclasses import replace
from contextlib import redirect_stdout
import hashlib
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from buoy_search import routing_quality as routing_quality_module
from buoy_search.plan_artifacts import stable_hash
from buoy_search.multi_corpus_evals import normalize_collected_evidence
from buoy_search.routing import ROUTING_PROTOTYPE_STRATEGY
from buoy_search.cli import print_retrieval_text
from buoy_search.routing_quality import (
    ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
    RoutingCalibrationReceipt,
    RoutingThresholdCalibration,
    routing_certification_dataset,
)
from scripts import evaluate_routing_quality as routing_quality_runner
from tests.test_automatic_routing import (
    AutomaticRoutingCliTests,
    FixedEmbedder,
    FixedReranker,
    active_routing_calibration,
    make_card,
    run_cli,
    snapshot,
)
from tests.routing_confidence_fixtures import (
    load_collect_routing_confidence_fixture,
)


class RoutingActivationCliTests(unittest.TestCase):
    API_KEY = AutomaticRoutingCliTests.API_KEY

    def test_explicit_namespace_bypasses_every_activation_dependency(self) -> None:
        forbidden = AssertionError("automatic activation dependency was accessed")
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                side_effect=forbidden,
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=forbidden,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                side_effect=forbidden,
            ),
            patch(
                "buoy_search.cli.ROUTING_RERANKER_FACTORY",
                side_effect=forbidden,
            ),
        ):
            result, stdout, stderr = run_cli(
                [
                    "retrieve",
                    "query",
                    "--namespace",
                    "site-one-v1",
                    "--plan",
                    "--json",
                ]
            )

        self.assertEqual((result, stderr), (0, ""))
        self.assertEqual(json.loads(stdout)["namespace"], "site-one-v1")

    def test_invalid_activation_artifact_fails_before_credentials_or_runtime(self) -> None:
        forbidden = AssertionError("automatic runtime was accessed")
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                side_effect=ValueError("Bearer secret-provider-payload"),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                side_effect=forbidden,
            ),
            patch("buoy_search.cli.config_from_args", side_effect=forbidden),
            patch("buoy_search.cli.load_evidence_calibration", side_effect=forbidden),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--plan", "--json"],
                env={},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertEqual(
            stderr,
            "Automatic routing failed: routing confidence artifact is invalid.\n",
        )
        self.assertNotIn("secret-provider-payload", stderr)

    def test_collect_artifact_preserves_legacy_router(self) -> None:
        cards = [make_card("one"), make_card("two"), make_card("three")]
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=load_collect_routing_confidence_fixture(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                return_value=FixedEmbedder(),
            ),
            patch(
                "buoy_search.cli.prototype_route",
                side_effect=AssertionError("collect mode invoked prototype routing"),
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "descriptor free question", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        routing = json.loads(stdout)["routing"]
        self.assertEqual(routing["strategy"], "title_alias_then_semantic")

    def test_active_descriptor_free_route_uses_certified_prototypes(self) -> None:
        cards = [make_card("one"), make_card("two"), make_card("three")]
        reranker = FixedReranker([10.0, 0.0, -1.0])
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.routing.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                return_value=FixedEmbedder(),
            ),
            patch(
                "buoy_search.cli.ROUTING_RERANKER_FACTORY",
                return_value=reranker,
            ),
            patch(
                "buoy_search.cli.hybrid_route",
                side_effect=AssertionError("active mode invoked legacy routing"),
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "descriptor free question", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        routing = json.loads(stdout)["routing"]
        self.assertTrue(routing["active"])
        self.assertEqual(routing["strategy"], ROUTING_PROTOTYPE_STRATEGY)
        self.assertEqual(routing["selection_reason"], "high_confidence_prototype")
        self.assertEqual(routing["initial_fanout"], 1)
        self.assertEqual(len(reranker.calls), 1)
        authority = routing["confidence_artifact"]
        self.assertEqual(
            authority["catalog_projection_sha256"],
            ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
        )
        self.assertEqual(authority["source_report_sha256"], "ab" * 32)
        self.assertEqual(authority["source_commit"], "bc" * 20)
        self.assertEqual(authority["source_tree"], "cd" * 20)
        self.assertNotIn("routing_examples", json.dumps(routing))
        self.assertNotIn("vector", json.dumps(routing))

    def test_active_named_route_never_loads_routing_reranker(self) -> None:
        cards = [
            make_card("dagster", title="Dagster"),
            make_card("two"),
            make_card("three"),
        ]
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.routing.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                return_value=FixedEmbedder(),
            ),
            patch(
                "buoy_search.cli.ROUTING_RERANKER_FACTORY",
                side_effect=AssertionError("named route loaded MiniLM"),
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "How does Dagster work?", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        routing = json.loads(stdout)["routing"]
        self.assertEqual(routing["selection_reason"], "unique_title_or_alias")
        self.assertEqual(routing["initial_fanout"], 1)

    def test_active_live_route_passes_prototype_context_and_fallbacks_to_retrieval(self) -> None:
        cards = [make_card("one"), make_card("two"), make_card("three")]
        captured: dict[str, object] = {}

        class FakeResult:
            def to_dict(self) -> dict[str, object]:
                return {
                    "dry_run": False,
                    "namespaces": ["one", "two", "three"],
                    "hits": [],
                    "evidence": {
                        "mode": "active",
                        "status": "supported",
                        "widening_triggered_by_weak_evidence": True,
                    },
                }

        class FakeRetriever:
            def retrieve(self, _query, options, **kwargs):  # noqa: ANN001
                captured["option_count"] = len(options)
                captured.update(kwargs)
                return FakeResult()

        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.routing.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                return_value=FixedEmbedder(),
            ),
            patch(
                "buoy_search.cli.ROUTING_RERANKER_FACTORY",
                return_value=FixedReranker([10.0, 0.0, -1.0]),
            ),
            patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                return_value=FakeRetriever(),
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "descriptor free question", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stderr), (0, ""))
        payload = json.loads(stdout)
        self.assertEqual(payload["routing"]["selection_reason"], "high_confidence_prototype")
        self.assertEqual(captured["initial_fanout"], 1)
        self.assertEqual(captured["option_count"], 3)
        route_context = captured["evidence_route_context"]
        self.assertEqual(route_context.selection_reason, "high_confidence_prototype")
        self.assertTrue(payload["evidence"]["widening_triggered_by_weak_evidence"])

    def test_active_routing_model_failure_is_redacted_before_content(self) -> None:
        cards = [make_card("one"), make_card("two"), make_card("three")]
        secret = "secret-routing-model-payload"
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.routing.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                return_value=FixedEmbedder(),
            ),
            patch(
                "buoy_search.cli.ROUTING_RERANKER_FACTORY",
                side_effect=RuntimeError(f"Bearer {secret}"),
            ),
            patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                side_effect=AssertionError("content retriever constructed"),
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "descriptor free question", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("routing shortlist reranker loading failed", stderr)
        self.assertNotIn(secret, stderr)
        self.assertNotIn("Bearer", stderr)

    def test_active_routing_embedder_load_failure_is_redacted_before_content(self) -> None:
        cards = [make_card("one"), make_card("two"), make_card("three")]
        secret = "secret-routing-embedder-payload"
        forbidden = AssertionError("reranker or content path was reached")
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch(
                "buoy_search.cli.validate_routing_confidence_catalog",
                return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
            ),
            patch(
                "buoy_search.cli.ROUTING_EMBEDDER_FACTORY",
                side_effect=RuntimeError(f"Bearer {secret}"),
            ),
            patch("buoy_search.cli.ROUTING_RERANKER_FACTORY", side_effect=forbidden),
            patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                side_effect=forbidden,
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "descriptor free question", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("routing query embedder loading failed", stderr)
        self.assertNotIn(secret, stderr)
        self.assertNotIn("Bearer", stderr)

    def test_active_catalog_drift_fails_before_models_or_content(self) -> None:
        cards = [make_card("one"), make_card("two")]
        forbidden = AssertionError("model or content path was reached")
        with (
            patch(
                "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
                return_value=active_routing_calibration(),
            ),
            patch(
                "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
                return_value=object(),
            ),
            patch("buoy_search.cli.read_remote_catalog", return_value=snapshot(cards)),
            patch("buoy_search.cli.ROUTING_EMBEDDER_FACTORY", side_effect=forbidden),
            patch("buoy_search.cli.ROUTING_RERANKER_FACTORY", side_effect=forbidden),
            patch(
                "buoy_search.cli.MultiNamespaceRetriever.from_configs",
                side_effect=forbidden,
            ),
        ):
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--plan", "--json"],
                env={"TURBOPUFFER_API_KEY": self.API_KEY},
            )

        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("does not match the active confidence artifact", stderr)

    def test_explained_text_exposes_active_authority_without_private_inputs(self) -> None:
        class Output:
            def to_dict(self) -> dict[str, object]:
                return {
                    "dry_run": False,
                    "namespaces": ["one"],
                    "fusion": "cross_namespace_equal_weight_ordinal_rrf",
                    "embedding_precision": "float32",
                    "hits": [],
                    "routing": {
                        "strategy": ROUTING_PROTOTYPE_STRATEGY,
                        "confidence_artifact": {
                            "id": "automatic-routing-confidence-v2",
                            "revision": "active-revision",
                            "mode": "active",
                            "canary_suite_sha256": "a" * 64,
                            "catalog_projection_sha256": "b" * 64,
                            "source_report_sha256": "c" * 64,
                            "source_commit": "d" * 40,
                            "source_tree": "e" * 40,
                        },
                    },
                }

        stdout = StringIO()
        with redirect_stdout(stdout):
            print_retrieval_text(Output(), explain=True)  # type: ignore[arg-type]

        rendered = stdout.getvalue()
        self.assertIn("route authority:", rendered)
        self.assertIn("automatic-routing-confidence-v2@active-revision", rendered)
        self.assertIn(f"suite={'a' * 64}", rendered)
        self.assertNotIn("routing_examples", rendered)
        self.assertNotIn("vector", rendered)


class RoutingActivationRunnerTests(unittest.TestCase):
    def test_dormant_report_binds_exact_routing_cli_and_evidence_bytes(self) -> None:
        from tests.test_routing_quality_runner import (
            synthetic_dataset,
            synthetic_snapshot,
        )

        dataset = synthetic_dataset(approved=True)
        provenance = routing_quality_runner._provenance(
            dataset,
            snapshot=synthetic_snapshot(),
            confidence_artifact=load_collect_routing_confidence_fixture(),
            catalog_projection_sha256="f" * 64,
            collector_invocation=("collect",),
            code={
                "commit": "1" * 40,
                "tree": "2" * 40,
                "working_tree_clean": True,
            },
        )
        package_dir = Path(routing_quality_module.__file__).resolve().parent
        evaluator = provenance["evaluator"]
        for field, filename in (
            ("routing_module_sha256", "routing.py"),
            ("cli_module_sha256", "cli.py"),
            ("evidence_module_sha256", "evidence.py"),
        ):
            self.assertEqual(
                evaluator[field],
                hashlib.sha256((package_dir / filename).read_bytes()).hexdigest(),
            )

    def test_activation_gate_recomputes_every_calibration_and_source_receipt(self) -> None:
        from tests.test_routing_quality_runner import synthetic_dataset

        dataset = synthetic_dataset(approved=True)
        certification = routing_certification_dataset(dataset)
        threshold = RoutingThresholdCalibration(
            score_floor=3.0,
            margin_floor=1.0,
            calibration_case_count=1,
            correct_high_confidence_singletons=1,
            incorrect_high_confidence_singletons=0,
            average_initial_fanout=1.0,
            calibration_case_ids_sha256=stable_hash(["alpha-calibration"]),
        )
        quality_verdict: dict[str, object] = {
            "passed": True,
            "failed_checks": [],
            "checks": {"synthetic": {"passed": True}},
        }
        base = active_routing_calibration()
        runner_hash = hashlib.sha256(
            Path(routing_quality_runner.__file__).read_bytes()
        ).hexdigest()
        scorer_hash = hashlib.sha256(
            Path(routing_quality_module.__file__).read_bytes()
        ).hexdigest()
        confidence = replace(
            base,
            score_floor=threshold.score_floor,
            margin_floor=threshold.margin_floor,
            bindings=replace(
                base.bindings,
                canary_suite_sha256=dataset.suite_sha256,
                catalog_projection_sha256="f" * 64,
            ),
            calibration=RoutingCalibrationReceipt(
                case_count=threshold.calibration_case_count,
                case_ids_sha256=threshold.calibration_case_ids_sha256,
                incorrect_high_confidence_singletons=0,
            ),
            certification_passed=True,
            certification_case_count=len(certification.cases),
            certification_case_ids_sha256=stable_hash(
                [case.id for case in certification.cases]
            ),
            certification_verdict_sha256=(
                routing_quality_runner._canonical_sha256(quality_verdict)
            ),
            receipts=replace(
                base.receipts,
                evaluator_runner_sha256=runner_hash,
                evaluator_scorer_sha256=scorer_hash,
            ),
        )
        verdict = routing_quality_runner._activation_verdict(
            dataset=dataset,
            confidence_artifact=confidence,
            threshold_calibration=threshold,
            certification=certification,
            quality_verdict=quality_verdict,
            catalog_projection_sha256="f" * 64,
            calls={
                "provider": {
                    "shortlist_or_per_card_queries": 0,
                    "content_queries": 0,
                    "writes": 0,
                },
                "model_downloads": 0,
            },
            code={"working_tree_clean": True},
        )

        self.assertTrue(verdict["ready"])
        self.assertEqual(verdict["failed_checks"], [])

        self.assertIsNotNone(confidence.calibration)
        self.assertIsNotNone(confidence.receipts)
        calibration = confidence.calibration
        receipts = confidence.receipts
        assert calibration is not None
        assert receipts is not None
        mismatches = (
            (
                "score floor",
                replace(confidence, score_floor=threshold.score_floor + 0.5),
                True,
                "confidence_threshold_calibration_receipt",
            ),
            (
                "margin floor",
                replace(confidence, margin_floor=threshold.margin_floor + 0.5),
                True,
                "confidence_threshold_calibration_receipt",
            ),
            (
                "calibration count",
                replace(
                    confidence,
                    calibration=replace(calibration, case_count=2),
                ),
                True,
                "confidence_threshold_calibration_receipt",
            ),
            (
                "calibration IDs",
                replace(
                    confidence,
                    calibration=replace(calibration, case_ids_sha256="0" * 64),
                ),
                True,
                "confidence_threshold_calibration_receipt",
            ),
            (
                "calibration incorrect-singleton count",
                replace(
                    confidence,
                    calibration=replace(
                        calibration,
                        incorrect_high_confidence_singletons=1,
                    ),
                ),
                True,
                "confidence_threshold_calibration_receipt",
            ),
            (
                "certification count",
                replace(confidence, certification_case_count=999),
                True,
                "confidence_certification_receipt",
            ),
            (
                "certification IDs",
                replace(confidence, certification_case_ids_sha256="0" * 64),
                True,
                "confidence_certification_receipt",
            ),
            (
                "certification verdict",
                replace(confidence, certification_verdict_sha256="0" * 64),
                True,
                "confidence_certification_receipt",
            ),
            (
                "runner source",
                replace(
                    confidence,
                    receipts=replace(receipts, evaluator_runner_sha256="0" * 64),
                ),
                True,
                "confidence_evaluator_source_receipts",
            ),
            (
                "scorer source",
                replace(
                    confidence,
                    receipts=replace(receipts, evaluator_scorer_sha256="0" * 64),
                ),
                True,
                "confidence_evaluator_source_receipts",
            ),
            (
                "dirty source",
                confidence,
                False,
                "clean_source_checkout",
            ),
        )
        for label, mismatched, clean, expected_check in mismatches:
            with self.subTest(label=label):
                failed = routing_quality_runner._activation_verdict(
                    dataset=dataset,
                    confidence_artifact=mismatched,
                    threshold_calibration=threshold,
                    certification=certification,
                    quality_verdict=quality_verdict,
                    catalog_projection_sha256="f" * 64,
                    calls={
                        "provider": {
                            "shortlist_or_per_card_queries": 0,
                            "content_queries": 0,
                            "writes": 0,
                        },
                        "model_downloads": 0,
                    },
                    code={"working_tree_clean": clean},
                )
                self.assertIn(expected_check, failed["failed_checks"])

    def test_evaluation_contract_accepts_both_prototype_route_reasons(self) -> None:
        from tests.test_multi_corpus_eval_runner import active_evidence

        for reason in ("high_confidence_prototype", "ambiguous_prototype"):
            with self.subTest(reason=reason):
                payload = active_evidence(widening=False)
                payload["route_selection_reason"] = reason
                normalized = normalize_collected_evidence(
                    payload,
                    where="activation evidence",
                    automatic_failure_count=0,
                )
                self.assertEqual(normalized["route_selection_reason"], reason)


if __name__ == "__main__":
    unittest.main()
