from __future__ import annotations

from dataclasses import replace
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.evidence import (
    CalibrationBindings,
    COLLECT_EVIDENCE_CALIBRATION_REVISION,
    DEFAULT_EVIDENCE_CALIBRATION_PATH,
    EVIDENCE_CALIBRATION_ID,
    EVIDENCE_FEATURE_CONTRACT,
    EvidenceCertification,
    EvidenceCalibrationError,
    NON_COLLECT_ACTIVATION_PAUSED_MESSAGE,
    OWNER_AUTHORIZED_ACTIVE_CALIBRATION,
    OWNER_AUTHORIZED_ACTIVE_CALIBRATION_REVISION,
    OWNER_AUTHORIZED_ACTIVE_THRESHOLD,
    decide_evidence,
    load_evidence_calibration,
    observe_evidence_scores,
)
from buoy_search.retriever import CalibratedEvidenceAssessor


class EvidenceCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.default_payload = json.loads(
            DEFAULT_EVIDENCE_CALIBRATION_PATH.read_text(encoding="utf-8")
        )

    def collect_payload(self) -> dict[str, object]:
        payload = json.loads(json.dumps(self.default_payload))
        payload["mode"] = "collect"
        payload["calibration_revision"] = COLLECT_EVIDENCE_CALIBRATION_REVISION
        payload["threshold"] = None
        payload["owner_approved"] = False
        return payload

    def write_payload(self, payload: object, *, raw: str | None = None) -> Path:
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        path = Path(temporary.name) / "calibration.json"
        path.write_text(
            raw if raw is not None else json.dumps(payload),
            encoding="utf-8",
        )
        return path

    def shadow_payload(self, *, threshold: float = 0.5) -> dict[str, object]:
        payload = self.collect_payload()
        payload["mode"] = "shadow"
        payload["calibration_revision"] = "shadow-candidate-v1"
        payload["threshold"] = threshold
        payload["bindings"] = {
            "retrieval_revision": "9cd80752953e4f48ade343832de8d1e8cfd65f9f",
            "dataset_revision": "dataset-sha256-abcdef0123456789",
            "evaluator_revision": "evaluator-sha256-abcdef0123456789",
            "source_mix_revision": "website-document-repository-database-v1",
        }
        return payload

    def active_payload(self, *, threshold: float = 0.5) -> dict[str, object]:
        payload = self.shadow_payload(threshold=threshold)
        payload["mode"] = "active"
        payload["calibration_revision"] = "owner-approved-active-v1"
        payload["owner_approved"] = True
        payload["certification"] = {
            "false_evidence_accepted_queries": 1,
            "accepted_queries": 100,
            "retained_answer_bearing_queries": 96,
            "pre_gate_answer_bearing_queries": 100,
            "abstained_no_answer_queries": 90,
            "no_answer_queries": 100,
            "max_source_false_evidence_risk_delta": 0.05,
            "max_source_retained_recall_regression": 0.05,
            "observed_max_fanout": 3,
            "question_level_split_verified": True,
            "locked_certification_verified": True,
            "sample_sufficiency_passed": True,
            "source_kind_gates_passed": True,
            "multi_corpus_gates_passed": True,
        }
        return payload

    def shadow_calibration(self, *, threshold: float = 0.5):
        return replace(
            load_evidence_calibration(),
            mode="shadow",
            calibration_revision="shadow-candidate-v1",
            threshold=threshold,
            owner_approved=False,
            bindings=CalibrationBindings(
                retrieval_revision="retrieval-v1",
                dataset_revision="dataset-v1",
                evaluator_revision="evaluator-v1",
                source_mix_revision="source-mix-v1",
            ),
        )

    def active_calibration(self, *, threshold: float = 0.5):
        return replace(
            self.shadow_calibration(threshold=threshold),
            mode="active",
            calibration_revision="owner-approved-active-v1",
            owner_approved=True,
            certification=EvidenceCertification(
                false_evidence_accepted_queries=1,
                accepted_queries=100,
                retained_answer_bearing_queries=96,
                pre_gate_answer_bearing_queries=100,
                abstained_no_answer_queries=90,
                no_answer_queries=100,
                max_source_false_evidence_risk_delta=0.05,
                max_source_retained_recall_regression=0.05,
                observed_max_fanout=3,
                question_level_split_verified=True,
                locked_certification_verified=True,
                sample_sufficiency_passed=True,
                source_kind_gates_passed=True,
                multi_corpus_gates_passed=True,
            ),
        )

    def observation(
        self,
        scores: list[float],
        *,
        failures: int = 0,
    ):
        return observe_evidence_scores(
            scores,
            route_selection_reason="high_confidence_semantic",
            route_semantic_score=0.73,
            route_semantic_margin=0.11,
            namespace_failure_count=failures,
        )

    def test_packaged_artifact_is_exact_owner_authorized_active_mode(self) -> None:
        calibration = load_evidence_calibration()

        self.assertEqual(calibration, OWNER_AUTHORIZED_ACTIVE_CALIBRATION)
        self.assertEqual(calibration.mode, "active")
        self.assertEqual(calibration.threshold, OWNER_AUTHORIZED_ACTIVE_THRESHOLD)
        self.assertTrue(calibration.owner_approved)
        self.assertEqual(calibration.calibration_id, EVIDENCE_CALIBRATION_ID)
        self.assertEqual(
            calibration.calibration_revision,
            OWNER_AUTHORIZED_ACTIVE_CALIBRATION_REVISION,
        )
        self.assertEqual(calibration.model, CROSS_ENCODER_MODEL)
        self.assertEqual(calibration.model_revision, CROSS_ENCODER_REVISION)
        self.assertEqual(calibration.feature_contract, EVIDENCE_FEATURE_CONTRACT)
        self.assertFalse(calibration.bindings.complete)
        self.assertFalse(calibration.certification.passes_bound_gates)

    def test_packaged_minus_8_boundary_is_inclusive(self) -> None:
        calibration = load_evidence_calibration()

        supported = decide_evidence(
            calibration,
            self.observation([OWNER_AUTHORIZED_ACTIVE_THRESHOLD]),
        )
        weak = decide_evidence(
            calibration,
            self.observation([OWNER_AUTHORIZED_ACTIVE_THRESHOLD - 0.000001]),
        )

        self.assertEqual(supported.status, "supported")
        self.assertFalse(supported.is_weak)
        self.assertEqual(supported.reason, "top_score_at_or_above_threshold")
        self.assertEqual(weak.status, "no_relevant_evidence")
        self.assertTrue(weak.is_weak)
        self.assertEqual(weak.reason, "top_score_below_threshold")

    def test_observation_uses_top_two_scores_and_emits_no_content(self) -> None:
        observation = observe_evidence_scores(
            [-2, 3.5, 1.25],
            route_selection_reason="ambiguous_semantic",
            route_semantic_score=0.61,
            route_semantic_margin=None,
            namespace_failure_count=1,
        )

        self.assertEqual(observation.top_score, 3.5)
        self.assertEqual(observation.second_score, 1.25)
        self.assertEqual(observation.score_gap, 2.25)
        self.assertEqual(observation.candidates_scored, 3)
        payload = observation.to_dict()
        self.assertEqual(
            set(payload),
            {
                "top_score",
                "second_score",
                "score_gap",
                "candidates_scored",
                "route_selection_reason",
                "route_semantic_score",
                "route_semantic_margin",
                "namespace_failure_count",
            },
        )
        serialized = json.dumps(payload)
        self.assertNotIn("query", serialized)
        self.assertNotIn("content", serialized)
        self.assertNotIn("passage", serialized)

    def test_empty_observation_is_exact_weak_signal_when_threshold_exists(self) -> None:
        calibration = self.shadow_calibration()
        observation = self.observation([])

        decision = decide_evidence(calibration, observation)

        self.assertIsNone(observation.top_score)
        self.assertIsNone(observation.second_score)
        self.assertIsNone(observation.score_gap)
        self.assertEqual(observation.candidates_scored, 0)
        self.assertTrue(decision.is_weak)
        self.assertEqual(decision.reason, "no_candidates")
        self.assertEqual(decision.status, "would_abstain")

    def test_shadow_computes_outcome_without_activating_it(self) -> None:
        calibration = self.shadow_calibration()

        supported = decide_evidence(calibration, self.observation([0.5]))
        weak = decide_evidence(calibration, self.observation([0.49]))
        incomplete = decide_evidence(
            calibration,
            self.observation([0.49], failures=1),
            widening_triggered_by_weak_evidence=True,
        )

        self.assertEqual(supported.status, "would_support")
        self.assertFalse(supported.is_weak)
        self.assertEqual(weak.status, "would_abstain")
        self.assertTrue(weak.is_weak)
        self.assertEqual(incomplete.status, "would_be_inconclusive")
        self.assertTrue(incomplete.widening_triggered_by_weak_evidence)

    def test_owner_approved_passing_active_artifact_can_decide(self) -> None:
        calibration = self.active_calibration()

        supported = decide_evidence(calibration, self.observation([0.7]))
        absent = decide_evidence(calibration, self.observation([0.1]))
        incomplete = decide_evidence(
            calibration,
            self.observation([0.1], failures=1),
        )

        self.assertTrue(calibration.certification.passes_bound_gates)
        self.assertEqual(supported.status, "supported")
        self.assertEqual(absent.status, "no_relevant_evidence")
        self.assertEqual(incomplete.status, "inconclusive")
        diagnostics = absent.to_dict()
        self.assertEqual(diagnostics["threshold"], 0.5)
        self.assertEqual(diagnostics["model"], CROSS_ENCODER_MODEL)
        self.assertEqual(diagnostics["model_revision"], CROSS_ENCODER_REVISION)
        self.assertNotIn("query", diagnostics)
        self.assertNotIn("hits", diagnostics)

    def test_active_requires_owner_approval_and_every_bound_gate(self) -> None:
        mutations: list[tuple[str, object]] = [
            ("owner_approved", False),
            ("false_evidence_accepted_queries", 6),
            ("retained_answer_bearing_queries", 94),
            ("abstained_no_answer_queries", 89),
            ("max_source_false_evidence_risk_delta", 0.051),
            ("max_source_retained_recall_regression", 0.051),
            ("observed_max_fanout", 4),
            ("question_level_split_verified", False),
            ("locked_certification_verified", False),
            ("sample_sufficiency_passed", False),
            ("source_kind_gates_passed", False),
            ("multi_corpus_gates_passed", False),
        ]
        for field, value in mutations:
            with self.subTest(field=field):
                calibration = self.active_calibration()
                if field == "owner_approved":
                    calibration = replace(calibration, owner_approved=value)
                else:
                    calibration = replace(
                        calibration,
                        certification=replace(
                            calibration.certification,
                            **{field: value},
                        ),
                    )
                with self.assertRaises(EvidenceCalibrationError):
                    decide_evidence(calibration, self.observation([0.7]))

    def test_loader_and_assessor_allow_only_exact_packaged_active_artifact(self) -> None:
        packaged = load_evidence_calibration()
        self.assertEqual(CalibratedEvidenceAssessor(packaged).mode, "active")

        alternatives = (
            self.shadow_payload(),
            self.active_payload(),
            json.loads(json.dumps(self.default_payload)),
        )
        for payload in alternatives:
            with self.subTest(mode=payload["mode"]):
                with self.assertRaisesRegex(
                    EvidenceCalibrationError,
                    "only the exact packaged owner-authorized",
                ):
                    load_evidence_calibration(self.write_payload(payload))
        self.assertIn("provisional -8.0", NON_COLLECT_ACTIVATION_PAUSED_MESSAGE)
        for calibration in (
            self.shadow_calibration(),
            self.active_calibration(),
            replace(
                packaged,
                threshold=OWNER_AUTHORIZED_ACTIVE_THRESHOLD - 0.1,
            ),
            replace(packaged, calibration_revision="substitute-active-v1"),
        ):
            with self.subTest(assessor_mode=calibration.mode):
                with self.assertRaisesRegex(
                    EvidenceCalibrationError,
                    "only the exact packaged owner-authorized",
                ):
                    CalibratedEvidenceAssessor(calibration)

    def test_collect_forbids_threshold_and_shadow_requires_finite_threshold(self) -> None:
        collect = self.collect_payload()
        collect["threshold"] = 0.0
        with self.assertRaises(EvidenceCalibrationError):
            load_evidence_calibration(self.write_payload(collect))

        for threshold in (None, math.inf, math.nan):
            with self.subTest(threshold=threshold):
                shadow = self.shadow_payload()
                shadow["threshold"] = threshold
                with self.assertRaises(EvidenceCalibrationError):
                    load_evidence_calibration(self.write_payload(shadow))

    def test_shadow_and_active_require_complete_exact_bindings(self) -> None:
        for calibration in (self.shadow_calibration(), self.active_calibration()):
            for field in calibration.bindings.__dataclass_fields__:
                with self.subTest(mode=calibration.mode, field=field):
                    invalid = replace(
                        calibration,
                        bindings=replace(calibration.bindings, **{field: None}),
                    )
                    with self.assertRaises(EvidenceCalibrationError):
                        decide_evidence(invalid, self.observation([0.7]))

    def test_loader_rejects_missing_unknown_duplicate_and_incompatible_fields(self) -> None:
        malformed_payloads: list[object] = []

        missing = json.loads(json.dumps(self.default_payload))
        del missing["model_revision"]
        malformed_payloads.append(missing)

        unknown = json.loads(json.dumps(self.default_payload))
        unknown["surprise"] = True
        malformed_payloads.append(unknown)

        wrong_model = json.loads(json.dumps(self.default_payload))
        wrong_model["model"] = "substitute/model"
        malformed_payloads.append(wrong_model)

        wrong_revision = json.loads(json.dumps(self.default_payload))
        wrong_revision["model_revision"] = "latest"
        malformed_payloads.append(wrong_revision)

        wrong_features = json.loads(json.dumps(self.default_payload))
        wrong_features["feature_contract"] = "top_score_only"
        malformed_payloads.append(wrong_features)

        wrong_schema = json.loads(json.dumps(self.default_payload))
        wrong_schema["schema_version"] = 2
        malformed_payloads.append(wrong_schema)

        for payload in malformed_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(EvidenceCalibrationError):
                    load_evidence_calibration(self.write_payload(payload))

        duplicate = DEFAULT_EVIDENCE_CALIBRATION_PATH.read_text(encoding="utf-8").replace(
            '"schema_version": 1,',
            '"schema_version": 1, "schema_version": 1,',
        )
        with self.assertRaises(EvidenceCalibrationError):
            load_evidence_calibration(self.write_payload({}, raw=duplicate))

    def test_loader_rejects_missing_artifact_and_non_finite_json(self) -> None:
        with TemporaryDirectory() as temporary:
            missing = Path(temporary) / "missing.json"
            with self.assertRaises(EvidenceCalibrationError):
                load_evidence_calibration(missing)

            invalid_utf8 = Path(temporary) / "invalid-utf8.json"
            invalid_utf8.write_bytes(b"{\xff}")
            with self.assertRaises(EvidenceCalibrationError):
                load_evidence_calibration(invalid_utf8)

        raw = DEFAULT_EVIDENCE_CALIBRATION_PATH.read_text(encoding="utf-8").replace(
            '"threshold": null',
            '"threshold": NaN',
        )
        with self.assertRaises(EvidenceCalibrationError):
            load_evidence_calibration(self.write_payload({}, raw=raw))

    def test_observation_rejects_non_finite_or_non_numeric_features(self) -> None:
        for scores in ([True], [math.inf], [math.nan], ["0.4"]):
            with self.subTest(scores=scores):
                with self.assertRaises(ValueError):
                    self.observation(scores)  # type: ignore[arg-type]

        with self.assertRaises(ValueError):
            observe_evidence_scores(
                [0.1],
                route_selection_reason="query text must not be serialized",
                route_semantic_score=0.2,
                route_semantic_margin=0.1,
                namespace_failure_count=0,
            )
        with self.assertRaises(ValueError):
            observe_evidence_scores(
                [0.1],
                route_selection_reason="ambiguous_semantic",
                route_semantic_score=math.inf,
                route_semantic_margin=0.1,
                namespace_failure_count=0,
            )
        with self.assertRaises(ValueError):
            observe_evidence_scores(
                [0.1],
                route_selection_reason="ambiguous_semantic",
                route_semantic_score=0.2,
                route_semantic_margin=0.1,
                namespace_failure_count=-1,
            )

    def test_certification_counts_cannot_be_partial_or_impossible(self) -> None:
        partial = self.shadow_payload()
        partial["certification"]["accepted_queries"] = 10  # type: ignore[index]
        with self.assertRaises(EvidenceCalibrationError):
            load_evidence_calibration(self.write_payload(partial))

        impossible = self.active_payload()
        impossible["certification"]["false_evidence_accepted_queries"] = 101  # type: ignore[index]
        with self.assertRaises(EvidenceCalibrationError):
            load_evidence_calibration(self.write_payload(impossible))


if __name__ == "__main__":
    unittest.main()
