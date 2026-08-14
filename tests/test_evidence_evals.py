from __future__ import annotations

import json
import math
import unittest

from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.evidence import EVIDENCE_FEATURE_CONTRACT
from buoy_search.evidence_evals import (
    EvidenceEvalLabel,
    EvidenceEvalObservation,
    EvidenceEvaluationError,
    calibrate_and_certify_evidence,
    evaluate_evidence_threshold,
    observations_from_collected_cases,
    select_evidence_threshold,
)


def collected_evidence(*, top_score: float | None) -> dict[str, object]:
    candidates_scored = 0 if top_score is None else 1
    return {
        "mode": "collect",
        "status": "unassessed",
        "reason": "threshold_not_calibrated",
        "model": CROSS_ENCODER_MODEL,
        "model_revision": CROSS_ENCODER_REVISION,
        "calibration_id": "automatic-retrieval-evidence-v1",
        "calibration_revision": "collect-unassessed-v1",
        "feature_contract": EVIDENCE_FEATURE_CONTRACT,
        "threshold": None,
        "widening_triggered_by_weak_evidence": False,
        "top_score": top_score,
        "second_score": None,
        "score_gap": None,
        "candidates_scored": candidates_scored,
        "route_selection_reason": "ambiguous_semantic",
        "route_semantic_score": 0.5,
        "route_semantic_margin": 0.01,
        "namespace_failure_count": 0,
    }


def observation(
    question_id: str,
    *,
    split: str = "calibration",
    source_kind: str = "website",
    answer_expected: bool = True,
    useful: bool = True,
    score: float | None = 1.0,
    fanout: int = 1,
) -> EvidenceEvalObservation:
    return EvidenceEvalObservation(
        question_id=question_id,
        split=split,  # type: ignore[arg-type]
        source_kind=source_kind,
        answer_expected=answer_expected,
        useful_evidence_present=useful,
        top_score=score,
        fanout=fanout,
    )


class EvidenceThresholdSelectionTests(unittest.TestCase):
    def test_reviewed_labels_join_content_free_collector_observations(self) -> None:
        labels = [
            EvidenceEvalLabel(
                question_id="positive",
                split="calibration",
                source_kind="website",
                answer_expected=True,
                useful_evidence_present=True,
            ),
            EvidenceEvalLabel(
                question_id="negative",
                split="certification",
                source_kind="website",
                answer_expected=False,
                useful_evidence_present=False,
            ),
        ]
        cases = [
            {
                "id": "positive",
                "route": {"namespaces": ["one"]},
                "failures": {"automatic_namespaces": []},
                "automatic_hits": [
                    {"namespace": "one", "url": "https://example.com/positive"}
                ],
                "evidence": collected_evidence(top_score=1.5),
            },
            {
                "id": "negative",
                "route": {"namespaces": ["one", "two", "three"]},
                "failures": {"automatic_namespaces": []},
                "automatic_hits": [
                    {"namespace": "one", "url": "https://example.com/negative"}
                ],
                "evidence": collected_evidence(top_score=-2.0),
            },
        ]

        observations = observations_from_collected_cases(labels, cases)

        self.assertEqual(
            [(item.question_id, item.top_score, item.fanout) for item in observations],
            [("positive", 1.5, 1), ("negative", -2.0, 3)],
        )

        cases[1]["evidence"] = {
            "mode": "collect",
            "status": "assessment_failed",
            "reason": "evidence_assessment_failed",
            "widening_triggered_by_weak_evidence": False,
        }
        with self.assertRaises(EvidenceEvaluationError):
            observations_from_collected_cases(labels, cases)

    def test_join_rejects_untrusted_or_incompatible_evidence_contracts(self) -> None:
        labels = [
            EvidenceEvalLabel(
                question_id="case",
                split="calibration",
                source_kind="website",
                answer_expected=True,
                useful_evidence_present=True,
            )
        ]
        base_case: dict[str, object] = {
            "id": "case",
            "route": {"namespaces": ["one"]},
            "failures": {"automatic_namespaces": []},
            "automatic_hits": [
                {"namespace": "one", "url": "https://example.com/case"}
            ],
            "evidence": collected_evidence(top_score=1.5),
        }
        mutations = (
            {"mode": "active", "status": "supported", "threshold": 0.0,
             "reason": "top_score_at_or_above_threshold"},
            {"model": "substitute/model"},
            {"model_revision": "substitute-revision"},
            {"feature_contract": "substitute-feature"},
            {"calibration_revision": "substitute-calibration"},
            {"widening_triggered_by_weak_evidence": True},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                candidate = dict(base_case)
                evidence = collected_evidence(top_score=1.5)
                evidence.update(mutation)
                candidate["evidence"] = evidence
                with self.assertRaises(EvidenceEvaluationError):
                    observations_from_collected_cases(labels, [candidate])

        missing_contract = dict(base_case)
        missing_contract["evidence"] = {"top_score": 1.5}
        with self.assertRaises(EvidenceEvaluationError):
            observations_from_collected_cases(labels, [missing_contract])

    def test_join_binds_scores_to_attempted_successful_hit_identities(self) -> None:
        labels = [
            EvidenceEvalLabel(
                question_id="case",
                split="calibration",
                source_kind="website",
                answer_expected=True,
                useful_evidence_present=True,
            )
        ]
        base_case: dict[str, object] = {
            "id": "case",
            "route": {"namespaces": ["one"]},
            "failures": {"automatic_namespaces": []},
            "automatic_hits": [
                {"namespace": "one", "url": "https://example.com/case"}
            ],
            "evidence": collected_evidence(top_score=1.5),
        }

        impossible_failure = dict(base_case)
        impossible_failure["failures"] = {
            "automatic_namespaces": ["two"]
        }
        with self.assertRaises(EvidenceEvaluationError):
            observations_from_collected_cases(labels, [impossible_failure])

        missing_hits = dict(base_case)
        missing_hits.pop("automatic_hits")
        with self.assertRaises(EvidenceEvaluationError):
            observations_from_collected_cases(labels, [missing_hits])

        empty_hits_with_score = dict(base_case)
        empty_hits_with_score["automatic_hits"] = []
        with self.assertRaises(EvidenceEvaluationError):
            observations_from_collected_cases(labels, [empty_hits_with_score])

    def test_selects_maximum_coverage_subject_to_exact_risk_gate(self) -> None:
        reviewed = [
            *[
                observation(f"positive-{index}", score=float(100 - index))
                for index in range(19)
            ],
            # At threshold 82 all 19 positives and this one negative are
            # accepted: exactly 1/20 = 5%. Lowering to 81 accepts another
            # negative and fails at 2/21.
            observation(
                "negative-pass-boundary",
                answer_expected=False,
                useful=False,
                score=82.0,
            ),
            observation(
                "negative-fail-boundary",
                answer_expected=False,
                useful=False,
                score=81.0,
            ),
        ]

        selection = select_evidence_threshold(reviewed)

        self.assertEqual(selection.threshold, 82.0)
        self.assertEqual(selection.calibration_metrics.confusion.true_positive, 19)
        self.assertEqual(selection.calibration_metrics.confusion.false_positive, 1)
        self.assertAlmostEqual(
            selection.calibration_metrics.false_evidence_risk or 0.0,
            1 / 20,
        )
        self.assertEqual(
            selection.calibration_metrics.retained_useful_evidence_recall,
            1.0,
        )
        self.assertEqual(
            [point.threshold for point in selection.risk_coverage_points],
            sorted(
                {item.top_score for item in reviewed if item.top_score is not None},
                reverse=True,
            ),
        )

    def test_conservative_tie_break_chooses_highest_equivalent_threshold(self) -> None:
        reviewed = [
            observation("positive-high", score=10.0),
            observation("positive-low", score=None),
            observation(
                "negative-low",
                answer_expected=False,
                useful=False,
                score=1.0,
            ),
        ]

        selection = select_evidence_threshold(reviewed)

        self.assertEqual(selection.threshold, 10.0)
        self.assertEqual(
            selection.tie_break,
            "minimize_false_evidence_risk_then_highest_threshold",
        )
        self.assertEqual(
            selection.calibration_metrics.retained_useful_evidence_recall,
            0.5,
        )

    def test_fails_when_no_nonempty_accepted_set_can_meet_risk_gate(self) -> None:
        reviewed = [
            observation("positive", score=1.0),
            observation(
                "negative-higher",
                answer_expected=False,
                useful=False,
                score=2.0,
            ),
        ]

        with self.assertRaisesRegex(
            EvidenceEvaluationError,
            "no finite calibration threshold",
        ):
            select_evidence_threshold(reviewed)

    def test_missing_scores_are_always_rejected_and_limit_coverage(self) -> None:
        reviewed = [
            observation("positive-scored", score=1.0),
            observation("positive-missing", score=None),
            observation(
                "negative",
                answer_expected=False,
                useful=False,
                score=0.0,
            ),
        ]

        selection = select_evidence_threshold(reviewed)

        self.assertEqual(selection.threshold, 1.0)
        self.assertEqual(selection.calibration_metrics.confusion.false_negative, 1)
        self.assertEqual(
            selection.calibration_metrics.retained_useful_evidence_recall,
            0.5,
        )


class EvidenceCertificationMetricsTests(unittest.TestCase):
    def certification_observations(self) -> list[EvidenceEvalObservation]:
        return [
            observation(
                "web-useful-accepted",
                split="certification",
                source_kind="website",
                score=0.9,
            ),
            observation(
                "web-useful-rejected",
                split="certification",
                source_kind="website",
                score=0.2,
                fanout=3,
            ),
            observation(
                "web-no-answer-rejected",
                split="certification",
                source_kind="website",
                answer_expected=False,
                useful=False,
                score=0.1,
            ),
            observation(
                "repo-useful-accepted",
                split="certification",
                source_kind="repository",
                score=0.8,
                fanout=2,
            ),
            observation(
                "repo-answer-missed-but-accepted",
                split="certification",
                source_kind="repository",
                answer_expected=True,
                useful=False,
                score=0.7,
            ),
            observation(
                "repo-no-answer-accepted",
                split="certification",
                source_kind="repository",
                answer_expected=False,
                useful=False,
                score=0.6,
            ),
        ]

    def test_computes_confusion_rates_source_deltas_and_max_fanout(self) -> None:
        metrics = evaluate_evidence_threshold(
            self.certification_observations(),
            threshold=0.5,
        )

        self.assertEqual(metrics.confusion.true_positive, 2)
        self.assertEqual(metrics.confusion.false_positive, 2)
        self.assertEqual(metrics.confusion.true_negative, 1)
        self.assertEqual(metrics.confusion.false_negative, 1)
        self.assertEqual(metrics.false_evidence_risk, 0.5)
        self.assertAlmostEqual(metrics.retained_useful_evidence_recall, 2 / 3)
        self.assertEqual(metrics.rejected_no_answer_queries, 1)
        self.assertEqual(metrics.no_answer_queries, 2)
        self.assertEqual(metrics.no_answer_rejection_rate, 0.5)
        self.assertEqual(metrics.max_fanout, 3)

        by_kind = {item.source_kind: item for item in metrics.source_kinds}
        self.assertEqual(list(by_kind), ["repository", "website"])
        self.assertAlmostEqual(
            by_kind["repository"].false_evidence_risk or 0.0,
            2 / 3,
        )
        self.assertAlmostEqual(
            by_kind["repository"].false_evidence_risk_excess or 0.0,
            1 / 6,
        )
        self.assertEqual(by_kind["website"].false_evidence_risk, 0.0)
        self.assertAlmostEqual(
            by_kind["website"].retained_recall_shortfall or 0.0,
            1 / 6,
        )
        self.assertAlmostEqual(
            metrics.max_source_false_evidence_risk_delta or 0.0,
            1 / 6,
        )
        self.assertAlmostEqual(
            metrics.max_source_retained_recall_regression,
            1 / 6,
        )

    def test_reports_undefined_false_risk_instead_of_hiding_empty_denominator(self) -> None:
        reviewed = [
            observation(
                "positive",
                split="certification",
                score=0.1,
            ),
            observation(
                "negative",
                split="certification",
                answer_expected=False,
                useful=False,
                score=None,
            ),
        ]

        metrics = evaluate_evidence_threshold(reviewed, threshold=1.0)

        self.assertEqual(metrics.confusion.accepted_queries, 0)
        self.assertIsNone(metrics.false_evidence_risk)
        self.assertIsNone(metrics.max_source_false_evidence_risk_delta)
        self.assertEqual(metrics.retained_useful_evidence_recall, 0.0)

    def test_full_report_selects_only_calibration_then_certifies_once(self) -> None:
        calibration = [
            observation("cal-positive", score=0.8),
            observation(
                "cal-negative",
                answer_expected=False,
                useful=False,
                score=0.2,
            ),
        ]
        certification = [
            observation(
                "cert-positive",
                split="certification",
                score=0.8,
            ),
            observation(
                "cert-negative-high",
                split="certification",
                answer_expected=False,
                useful=False,
                score=100.0,
            ),
        ]

        report = calibrate_and_certify_evidence([*calibration, *certification])

        self.assertEqual(report.selection.threshold, 0.8)
        self.assertEqual(report.certification.threshold, 0.8)
        self.assertEqual(report.certification.confusion.false_positive, 1)
        payload = report.to_dict()
        self.assertNotIn("questions", payload)
        self.assertNotIn("question_id", json.dumps(payload))


class EvidenceEvaluationValidationTests(unittest.TestCase):
    def test_requires_nonempty_positive_and_negative_denominators(self) -> None:
        only_positive = [observation("positive")]
        only_negative = [
            observation(
                "negative",
                answer_expected=False,
                useful=False,
            )
        ]
        for reviewed in (only_positive, only_negative):
            with self.subTest(reviewed=reviewed):
                with self.assertRaises(EvidenceEvaluationError):
                    select_evidence_threshold(reviewed)

        no_no_answer = [
            observation(
                "positive",
                split="certification",
                score=1.0,
            ),
            observation(
                "answer-expected-miss",
                split="certification",
                answer_expected=True,
                useful=False,
                score=0.0,
            ),
        ]
        metrics = evaluate_evidence_threshold(no_no_answer, threshold=0.5)
        self.assertEqual(metrics.no_answer_queries, 0)
        self.assertIsNone(metrics.no_answer_rejection_rate)

    def test_requires_disjoint_question_level_splits(self) -> None:
        duplicate = [
            observation("same-question", score=1.0),
            observation(
                "same-question",
                split="certification",
                answer_expected=False,
                useful=False,
                score=0.0,
            ),
        ]
        with self.assertRaisesRegex(EvidenceEvaluationError, "must be unique"):
            calibrate_and_certify_evidence(duplicate)

        with self.assertRaisesRegex(EvidenceEvaluationError, "both calibration"):
            calibrate_and_certify_evidence([observation("cal-only")])

    def test_rejects_invalid_observation_and_threshold_values(self) -> None:
        invalid_factories = [
            lambda: observation("", score=1.0),
            lambda: observation("edge ", score=1.0),
            lambda: observation("bad-split", split="training", score=1.0),
            lambda: observation("bad-source", source_kind=" ", score=1.0),
            lambda: observation(
                "contradiction",
                answer_expected=False,
                useful=True,
                score=1.0,
            ),
            lambda: observation("infinite", score=math.inf),
            lambda: observation("zero-fanout", fanout=0),
        ]
        for factory in invalid_factories:
            with self.subTest(factory=factory):
                with self.assertRaises(EvidenceEvaluationError):
                    factory()

        reviewed = [
            observation(
                "positive",
                split="certification",
                score=1.0,
            ),
            observation(
                "negative",
                split="certification",
                answer_expected=False,
                useful=False,
                score=0.0,
            ),
        ]
        for threshold in (math.inf, math.nan, True, "0.5"):
            with self.subTest(threshold=threshold):
                with self.assertRaises(EvidenceEvaluationError):
                    evaluate_evidence_threshold(
                        reviewed,
                        threshold=threshold,  # type: ignore[arg-type]
                    )

    def test_rejects_mixed_split_input_to_individual_operations(self) -> None:
        mixed = [
            observation("cal", score=1.0),
            observation(
                "cert",
                split="certification",
                answer_expected=False,
                useful=False,
                score=0.0,
            ),
        ]
        with self.assertRaisesRegex(EvidenceEvaluationError, "expected only"):
            select_evidence_threshold(mixed)
        with self.assertRaisesRegex(EvidenceEvaluationError, "expected only"):
            evaluate_evidence_threshold(mixed, threshold=0.5)


if __name__ == "__main__":
    unittest.main()
