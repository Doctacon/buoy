"""Deterministic offline calibration and certification for evidence abstention.

This module consumes reviewed question-level observations only.  It performs no
retrieval, model loading, provider access, or calibration-artifact mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Literal, Mapping, Sequence

from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.evidence import (
    COLLECT_EVIDENCE_CALIBRATION_REVISION,
    EVIDENCE_CALIBRATION_ID,
    EVIDENCE_FEATURE_CONTRACT,
    MAX_FALSE_EVIDENCE_RISK,
)
from buoy_search.multi_corpus_evals import normalize_collected_evidence

EvidenceEvalSplit = Literal["calibration", "certification"]
_EVAL_SPLITS = frozenset({"calibration", "certification"})


class EvidenceEvaluationError(ValueError):
    """The reviewed observations cannot support a governed evaluation."""


@dataclass(frozen=True)
class EvidenceEvalLabel:
    """One separately reviewed question-level evidence label and split."""

    question_id: str
    split: EvidenceEvalSplit
    source_kind: str
    answer_expected: bool
    useful_evidence_present: bool

    def __post_init__(self) -> None:
        # Reuse the observation's strict label validation without inventing a
        # score or fanout at review time.
        EvidenceEvalObservation(
            question_id=self.question_id,
            split=self.split,
            source_kind=self.source_kind,
            answer_expected=self.answer_expected,
            useful_evidence_present=self.useful_evidence_present,
            top_score=None,
            fanout=1,
        )


@dataclass(frozen=True)
class EvidenceEvalObservation:
    """One reviewed query and its bounded, question-level retrieval outcome."""

    question_id: str
    split: EvidenceEvalSplit
    source_kind: str
    answer_expected: bool
    useful_evidence_present: bool
    top_score: float | None
    fanout: int

    def __post_init__(self) -> None:
        if not isinstance(self.question_id, str) or not self.question_id:
            raise EvidenceEvaluationError("question_id must be a non-empty string")
        if self.question_id != self.question_id.strip():
            raise EvidenceEvaluationError("question_id must not contain edge whitespace")
        if self.split not in _EVAL_SPLITS:
            raise EvidenceEvaluationError("split must be calibration or certification")
        if not isinstance(self.source_kind, str) or not self.source_kind:
            raise EvidenceEvaluationError("source_kind must be a non-empty string")
        if self.source_kind != self.source_kind.strip():
            raise EvidenceEvaluationError("source_kind must not contain edge whitespace")
        if not isinstance(self.answer_expected, bool):
            raise EvidenceEvaluationError("answer_expected must be a boolean")
        if not isinstance(self.useful_evidence_present, bool):
            raise EvidenceEvaluationError(
                "useful_evidence_present must be a boolean"
            )
        if self.useful_evidence_present and not self.answer_expected:
            raise EvidenceEvaluationError(
                "useful evidence cannot be present for a no-answer question"
            )
        if self.top_score is not None:
            if isinstance(self.top_score, bool) or not isinstance(
                self.top_score, (int, float)
            ):
                raise EvidenceEvaluationError("top_score must be numeric or null")
            score = float(self.top_score)
            if not math.isfinite(score):
                raise EvidenceEvaluationError("top_score must be finite")
            object.__setattr__(self, "top_score", score)
        if isinstance(self.fanout, bool) or not isinstance(self.fanout, int):
            raise EvidenceEvaluationError("fanout must be an integer")
        if self.fanout <= 0:
            raise EvidenceEvaluationError("fanout must be greater than zero")


def observations_from_collected_cases(
    labels: Sequence[EvidenceEvalLabel],
    cases: Sequence[Mapping[str, object]],
) -> tuple[EvidenceEvalObservation, ...]:
    """Join labels to frozen historical collect observations by question ID.

    This offline calibration input deliberately remains bound to the original
    collect-only contract even after the packaged runtime artifact becomes
    active.  Active runs suppress weak hits and are not interchangeable with
    the pre-activation observations used to choose a threshold.
    """

    if isinstance(labels, (str, bytes, bytearray)) or isinstance(
        cases, (str, bytes, bytearray)
    ):
        raise EvidenceEvaluationError("labels and cases must be sequences")
    reviewed = tuple(labels)
    if any(not isinstance(item, EvidenceEvalLabel) for item in reviewed):
        raise EvidenceEvaluationError("every label must be an EvidenceEvalLabel")
    label_ids = [item.question_id for item in reviewed]
    if len(label_ids) != len(set(label_ids)):
        raise EvidenceEvaluationError("reviewed label question IDs must be unique")

    by_id: dict[str, Mapping[str, object]] = {}
    for raw_case in cases:
        if not isinstance(raw_case, Mapping):
            raise EvidenceEvaluationError("collected cases must be objects")
        case_id = raw_case.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise EvidenceEvaluationError("collected case ID must be a string")
        if case_id in by_id:
            raise EvidenceEvaluationError("collected case IDs must be unique")
        by_id[case_id] = raw_case
    if set(label_ids) != set(by_id):
        raise EvidenceEvaluationError(
            "reviewed labels and collected cases must contain the same question IDs"
        )

    observations: list[EvidenceEvalObservation] = []
    for label in reviewed:
        collected = by_id[label.question_id]
        route = collected.get("route")
        evidence = collected.get("evidence")
        if not isinstance(route, Mapping) or not isinstance(evidence, Mapping):
            raise EvidenceEvaluationError(
                "every collected case requires route and evidence observations"
            )
        namespaces = route.get("namespaces")
        if (
            not isinstance(namespaces, list)
            or not namespaces
            or len(namespaces) > 3
            or any(not isinstance(value, str) or not value for value in namespaces)
            or len(namespaces) != len(set(namespaces))
        ):
            raise EvidenceEvaluationError("collected route fanout is invalid")
        failures = collected.get("failures")
        if not isinstance(failures, Mapping):
            raise EvidenceEvaluationError(
                "every collected case requires attributed failure observations"
            )
        automatic_failures = failures.get("automatic_namespaces")
        if (
            not isinstance(automatic_failures, list)
            or any(
                not isinstance(value, str) or not value
                for value in automatic_failures
            )
            or len(automatic_failures) != len(set(automatic_failures))
        ):
            raise EvidenceEvaluationError(
                "collected automatic namespace failures are invalid"
            )
        attempted_namespaces = set(namespaces)
        failed_namespaces = set(automatic_failures)
        if not failed_namespaces < attempted_namespaces:
            raise EvidenceEvaluationError(
                "collected automatic failures must be a strict subset of the route"
            )
        automatic_hits = collected.get("automatic_hits")
        if not isinstance(automatic_hits, list):
            raise EvidenceEvaluationError(
                "every collected case requires automatic hit identities"
            )
        successful_namespaces = attempted_namespaces - failed_namespaces
        normalized_hit_keys: set[tuple[str, str]] = set()
        for hit in automatic_hits:
            if not isinstance(hit, Mapping) or set(hit) != {"namespace", "url"}:
                raise EvidenceEvaluationError(
                    "collected automatic hit identities are invalid"
                )
            namespace = hit.get("namespace")
            url = hit.get("url")
            if (
                not isinstance(namespace, str)
                or not namespace
                or namespace not in successful_namespaces
                or not isinstance(url, str)
                or not url
            ):
                raise EvidenceEvaluationError(
                    "collected automatic hit identities are invalid"
                )
            hit_key = namespace, url
            if hit_key in normalized_hit_keys:
                raise EvidenceEvaluationError(
                    "collected automatic hit identities must be unique"
                )
            normalized_hit_keys.add(hit_key)
        try:
            normalized_evidence = normalize_collected_evidence(
                evidence,
                where=f"collected case {label.question_id!r} evidence",
                automatic_failure_count=len(automatic_failures),
            )
        except ValueError as exc:
            raise EvidenceEvaluationError(str(exc)) from None
        expected_contract = {
            "mode": "collect",
            "status": "unassessed",
            "reason": "threshold_not_calibrated",
            "model": CROSS_ENCODER_MODEL,
            "model_revision": CROSS_ENCODER_REVISION,
            "calibration_id": EVIDENCE_CALIBRATION_ID,
            "calibration_revision": COLLECT_EVIDENCE_CALIBRATION_REVISION,
            "feature_contract": EVIDENCE_FEATURE_CONTRACT,
            "threshold": None,
            "widening_triggered_by_weak_evidence": False,
        }
        if any(
            normalized_evidence.get(field) != expected
            for field, expected in expected_contract.items()
        ):
            raise EvidenceEvaluationError(
                "collected evidence does not match the packaged collect contract"
            )
        top_score = normalized_evidence["top_score"]
        candidates_scored = int(normalized_evidence["candidates_scored"])
        if (not automatic_hits) != (candidates_scored == 0):
            raise EvidenceEvaluationError(
                "collected evidence candidate count contradicts automatic hits"
            )
        if len(automatic_hits) > candidates_scored:
            raise EvidenceEvaluationError(
                "collected evidence scored fewer candidates than returned hit identities"
            )
        observations.append(
            EvidenceEvalObservation(
                question_id=label.question_id,
                split=label.split,
                source_kind=label.source_kind,
                answer_expected=label.answer_expected,
                useful_evidence_present=label.useful_evidence_present,
                top_score=(float(top_score) if top_score is not None else None),
                fanout=len(namespaces),
            )
        )
    return tuple(observations)


@dataclass(frozen=True)
class EvidenceConfusionCounts:
    """Useful-evidence labels by threshold acceptance decision."""

    true_positive: int
    false_positive: int
    true_negative: int
    false_negative: int

    @property
    def positive_queries(self) -> int:
        return self.true_positive + self.false_negative

    @property
    def negative_queries(self) -> int:
        return self.false_positive + self.true_negative

    @property
    def accepted_queries(self) -> int:
        return self.true_positive + self.false_positive

    @property
    def rejected_queries(self) -> int:
        return self.true_negative + self.false_negative

    def to_dict(self) -> dict[str, int]:
        return {
            "true_positive": self.true_positive,
            "false_positive": self.false_positive,
            "true_negative": self.true_negative,
            "false_negative": self.false_negative,
            "positive_queries": self.positive_queries,
            "negative_queries": self.negative_queries,
            "accepted_queries": self.accepted_queries,
            "rejected_queries": self.rejected_queries,
        }


@dataclass(frozen=True)
class RiskCoveragePoint:
    """One attainable top-score threshold on the reviewed split."""

    threshold: float
    confusion: EvidenceConfusionCounts
    false_evidence_risk: float
    retained_useful_evidence_recall: float

    def to_dict(self) -> dict[str, object]:
        return {
            "threshold": self.threshold,
            "confusion": self.confusion.to_dict(),
            "false_evidence_risk": self.false_evidence_risk,
            "retained_useful_evidence_recall": (
                self.retained_useful_evidence_recall
            ),
        }


@dataclass(frozen=True)
class SourceKindEvidenceMetrics:
    """Certification metrics and one-sided aggregate deltas for a source kind."""

    source_kind: str
    confusion: EvidenceConfusionCounts
    false_evidence_risk: float | None
    retained_useful_evidence_recall: float | None
    false_evidence_risk_excess: float | None
    retained_recall_shortfall: float | None
    no_answer_queries: int
    rejected_no_answer_queries: int
    no_answer_rejection_rate: float | None

    def to_dict(self) -> dict[str, object]:
        return {
            "source_kind": self.source_kind,
            "confusion": self.confusion.to_dict(),
            "false_evidence_risk": self.false_evidence_risk,
            "retained_useful_evidence_recall": (
                self.retained_useful_evidence_recall
            ),
            "false_evidence_risk_excess": self.false_evidence_risk_excess,
            "retained_recall_shortfall": self.retained_recall_shortfall,
            "no_answer_queries": self.no_answer_queries,
            "rejected_no_answer_queries": self.rejected_no_answer_queries,
            "no_answer_rejection_rate": self.no_answer_rejection_rate,
        }


@dataclass(frozen=True)
class EvidenceThresholdMetrics:
    """Question-level metrics at one fixed threshold."""

    split: EvidenceEvalSplit
    threshold: float
    confusion: EvidenceConfusionCounts
    false_evidence_risk: float | None
    retained_useful_evidence_recall: float
    no_answer_queries: int
    rejected_no_answer_queries: int
    no_answer_rejection_rate: float | None
    max_fanout: int
    source_kinds: tuple[SourceKindEvidenceMetrics, ...]
    max_source_false_evidence_risk_delta: float | None
    max_source_retained_recall_regression: float

    def to_dict(self) -> dict[str, object]:
        return {
            "split": self.split,
            "threshold": self.threshold,
            "confusion": self.confusion.to_dict(),
            "false_evidence_risk": self.false_evidence_risk,
            "retained_useful_evidence_recall": (
                self.retained_useful_evidence_recall
            ),
            "no_answer_queries": self.no_answer_queries,
            "rejected_no_answer_queries": self.rejected_no_answer_queries,
            "no_answer_rejection_rate": self.no_answer_rejection_rate,
            "max_fanout": self.max_fanout,
            "source_kinds": [item.to_dict() for item in self.source_kinds],
            "max_source_false_evidence_risk_delta": (
                self.max_source_false_evidence_risk_delta
            ),
            "max_source_retained_recall_regression": (
                self.max_source_retained_recall_regression
            ),
        }


@dataclass(frozen=True)
class EvidenceThresholdSelection:
    """The deterministic calibration choice and its complete risk curve."""

    threshold: float
    calibration_metrics: EvidenceThresholdMetrics
    risk_coverage_points: tuple[RiskCoveragePoint, ...]
    max_false_evidence_risk: float = MAX_FALSE_EVIDENCE_RISK
    objective: str = "maximize_retained_useful_evidence_recall"
    tie_break: str = "minimize_false_evidence_risk_then_highest_threshold"

    def to_dict(self) -> dict[str, object]:
        return {
            "threshold": self.threshold,
            "max_false_evidence_risk": self.max_false_evidence_risk,
            "objective": self.objective,
            "tie_break": self.tie_break,
            "calibration_metrics": self.calibration_metrics.to_dict(),
            "risk_coverage_points": [
                point.to_dict() for point in self.risk_coverage_points
            ],
        }


@dataclass(frozen=True)
class EvidenceCalibrationReport:
    """One calibration selection followed by one locked certification result."""

    selection: EvidenceThresholdSelection
    certification: EvidenceThresholdMetrics

    def to_dict(self) -> dict[str, object]:
        return {
            "selection": self.selection.to_dict(),
            "certification": self.certification.to_dict(),
        }


def select_evidence_threshold(
    observations: Sequence[EvidenceEvalObservation],
) -> EvidenceThresholdSelection:
    """Choose the highest-coverage passing threshold from calibration only."""

    reviewed = _validated_split(observations, expected_split="calibration")
    positive_count, negative_count = _require_label_denominators(reviewed)
    points = _risk_coverage_points(
        reviewed,
        positive_count=positive_count,
        negative_count=negative_count,
    )
    feasible = [
        point
        for point in points
        if _risk_at_most(
            point.confusion.false_positive,
            point.confusion.accepted_queries,
            MAX_FALSE_EVIDENCE_RISK,
        )
    ]
    if not feasible:
        raise EvidenceEvaluationError(
            "no finite calibration threshold satisfies the false-evidence risk "
            "gate with a non-empty accepted denominator"
        )

    selected = min(
        feasible,
        key=lambda point: (
            -point.confusion.true_positive,
            Fraction(
                point.confusion.false_positive,
                point.confusion.accepted_queries,
            ),
            -point.threshold,
        ),
    )
    metrics = evaluate_evidence_threshold(
        reviewed,
        threshold=selected.threshold,
        expected_split="calibration",
    )
    return EvidenceThresholdSelection(
        threshold=selected.threshold,
        calibration_metrics=metrics,
        risk_coverage_points=points,
    )


def evaluate_evidence_threshold(
    observations: Sequence[EvidenceEvalObservation],
    *,
    threshold: float,
    expected_split: EvidenceEvalSplit = "certification",
) -> EvidenceThresholdMetrics:
    """Evaluate one already-selected finite threshold on exactly one split."""

    finite_threshold = _finite_threshold(threshold)
    reviewed = _validated_split(observations, expected_split=expected_split)
    _require_label_denominators(reviewed)
    confusion = _confusion_at_threshold(reviewed, finite_threshold)
    retained_recall = confusion.true_positive / confusion.positive_queries
    false_evidence_risk = _optional_rate(
        confusion.false_positive,
        confusion.accepted_queries,
    )
    no_answer = [item for item in reviewed if not item.answer_expected]
    rejected_no_answer = sum(
        not _is_accepted(item, finite_threshold) for item in no_answer
    )
    no_answer_rejection_rate = (
        rejected_no_answer / len(no_answer) if no_answer else None
    )

    source_kinds = _source_kind_metrics(
        reviewed,
        threshold=finite_threshold,
        aggregate_false_evidence_risk=false_evidence_risk,
        aggregate_retained_recall=retained_recall,
    )
    false_risk_deltas = [
        item.false_evidence_risk_excess
        for item in source_kinds
        if item.false_evidence_risk_excess is not None
    ]
    recall_deltas = [
        item.retained_recall_shortfall
        for item in source_kinds
        if item.retained_recall_shortfall is not None
    ]
    return EvidenceThresholdMetrics(
        split=expected_split,
        threshold=finite_threshold,
        confusion=confusion,
        false_evidence_risk=false_evidence_risk,
        retained_useful_evidence_recall=retained_recall,
        no_answer_queries=len(no_answer),
        rejected_no_answer_queries=rejected_no_answer,
        no_answer_rejection_rate=no_answer_rejection_rate,
        max_fanout=max(item.fanout for item in reviewed),
        source_kinds=source_kinds,
        max_source_false_evidence_risk_delta=(
            max(false_risk_deltas) if false_risk_deltas else None
        ),
        max_source_retained_recall_regression=max(recall_deltas, default=0.0),
    )


def calibrate_and_certify_evidence(
    observations: Sequence[EvidenceEvalObservation],
) -> EvidenceCalibrationReport:
    """Select on calibration questions, then evaluate certification exactly once."""

    reviewed = _validated_observations(observations)
    calibration = [item for item in reviewed if item.split == "calibration"]
    certification = [item for item in reviewed if item.split == "certification"]
    if not calibration or not certification:
        raise EvidenceEvaluationError(
            "both calibration and certification question splits are required"
        )
    selection = select_evidence_threshold(calibration)
    certification_metrics = evaluate_evidence_threshold(
        certification,
        threshold=selection.threshold,
        expected_split="certification",
    )
    return EvidenceCalibrationReport(
        selection=selection,
        certification=certification_metrics,
    )


def _risk_coverage_points(
    observations: Sequence[EvidenceEvalObservation],
    *,
    positive_count: int,
    negative_count: int,
) -> tuple[RiskCoveragePoint, ...]:
    if positive_count <= 0 or negative_count <= 0:  # Defensive caller contract.
        raise EvidenceEvaluationError("risk curve requires positive and negative labels")
    thresholds = sorted(
        {
            item.top_score
            for item in observations
            if item.top_score is not None
        },
        reverse=True,
    )
    if not thresholds:
        raise EvidenceEvaluationError(
            "calibration requires at least one finite top score"
        )
    points: list[RiskCoveragePoint] = []
    for threshold in thresholds:
        confusion = _confusion_at_threshold(observations, threshold)
        accepted = confusion.accepted_queries
        if accepted <= 0:  # Every observed score threshold accepts itself.
            continue
        points.append(
            RiskCoveragePoint(
                threshold=threshold,
                confusion=confusion,
                false_evidence_risk=(confusion.false_positive / accepted),
                retained_useful_evidence_recall=(
                    confusion.true_positive / positive_count
                ),
            )
        )
    return tuple(points)


def _source_kind_metrics(
    observations: Sequence[EvidenceEvalObservation],
    *,
    threshold: float,
    aggregate_false_evidence_risk: float | None,
    aggregate_retained_recall: float,
) -> tuple[SourceKindEvidenceMetrics, ...]:
    result: list[SourceKindEvidenceMetrics] = []
    for source_kind in sorted({item.source_kind for item in observations}):
        source_observations = [
            item for item in observations if item.source_kind == source_kind
        ]
        confusion = _confusion_at_threshold(source_observations, threshold)
        source_risk = _optional_rate(
            confusion.false_positive,
            confusion.accepted_queries,
        )
        source_recall = _optional_rate(
            confusion.true_positive,
            confusion.positive_queries,
        )
        no_answer = [
            item for item in source_observations if not item.answer_expected
        ]
        rejected_no_answer = sum(
            not _is_accepted(item, threshold) for item in no_answer
        )
        result.append(
            SourceKindEvidenceMetrics(
                source_kind=source_kind,
                confusion=confusion,
                false_evidence_risk=source_risk,
                retained_useful_evidence_recall=source_recall,
                false_evidence_risk_excess=(
                    max(0.0, source_risk - aggregate_false_evidence_risk)
                    if source_risk is not None
                    and aggregate_false_evidence_risk is not None
                    else None
                ),
                retained_recall_shortfall=(
                    max(0.0, aggregate_retained_recall - source_recall)
                    if source_recall is not None
                    else None
                ),
                no_answer_queries=len(no_answer),
                rejected_no_answer_queries=rejected_no_answer,
                no_answer_rejection_rate=(
                    rejected_no_answer / len(no_answer) if no_answer else None
                ),
            )
        )
    return tuple(result)


def _confusion_at_threshold(
    observations: Sequence[EvidenceEvalObservation],
    threshold: float,
) -> EvidenceConfusionCounts:
    true_positive = false_positive = true_negative = false_negative = 0
    for observation in observations:
        accepted = _is_accepted(observation, threshold)
        if observation.useful_evidence_present:
            if accepted:
                true_positive += 1
            else:
                false_negative += 1
        elif accepted:
            false_positive += 1
        else:
            true_negative += 1
    return EvidenceConfusionCounts(
        true_positive=true_positive,
        false_positive=false_positive,
        true_negative=true_negative,
        false_negative=false_negative,
    )


def _is_accepted(observation: EvidenceEvalObservation, threshold: float) -> bool:
    return observation.top_score is not None and observation.top_score >= threshold


def _validated_split(
    observations: Sequence[EvidenceEvalObservation],
    *,
    expected_split: EvidenceEvalSplit,
) -> tuple[EvidenceEvalObservation, ...]:
    reviewed = _validated_observations(observations)
    if not reviewed:
        raise EvidenceEvaluationError(f"{expected_split} split must not be empty")
    if any(item.split != expected_split for item in reviewed):
        raise EvidenceEvaluationError(
            f"expected only {expected_split} observations"
        )
    return reviewed


def _validated_observations(
    observations: Sequence[EvidenceEvalObservation],
) -> tuple[EvidenceEvalObservation, ...]:
    if isinstance(observations, (str, bytes, bytearray)):
        raise EvidenceEvaluationError("observations must be a sequence")
    reviewed = tuple(observations)
    if any(not isinstance(item, EvidenceEvalObservation) for item in reviewed):
        raise EvidenceEvaluationError(
            "every observation must be an EvidenceEvalObservation"
        )
    question_ids = [item.question_id for item in reviewed]
    if len(question_ids) != len(set(question_ids)):
        raise EvidenceEvaluationError(
            "question_id values must be unique across question-level splits"
        )
    return reviewed


def _require_label_denominators(
    observations: Sequence[EvidenceEvalObservation],
) -> tuple[int, int]:
    positive_count = sum(item.useful_evidence_present for item in observations)
    negative_count = len(observations) - positive_count
    if positive_count <= 0 or negative_count <= 0:
        raise EvidenceEvaluationError(
            "evaluation requires non-empty useful and non-useful denominators"
        )
    return positive_count, negative_count


def _risk_at_most(
    false_accepted: int,
    accepted: int,
    maximum: float,
) -> bool:
    if accepted <= 0:
        return False
    return Fraction(false_accepted, accepted) <= Fraction(str(maximum))


def _optional_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def _finite_threshold(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceEvaluationError("threshold must be numeric")
    threshold = float(value)
    if not math.isfinite(threshold):
        raise EvidenceEvaluationError("threshold must be finite")
    return threshold
