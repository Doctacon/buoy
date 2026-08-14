"""Governed, content-free evidence assessment for automatic retrieval.

Raw cross-encoder logits are not probabilities.  This module therefore keeps
score observation separate from the versioned calibration artifact that is
allowed to interpret those scores.  The packaged artifact starts in collect
mode and intentionally contains no threshold.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
from typing import Literal, Mapping, Sequence, cast

from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION

EVIDENCE_CALIBRATION_SCHEMA_VERSION = 1
EVIDENCE_FEATURE_CONTRACT = "cross_encoder_top_score_threshold_v1"
DEFAULT_EVIDENCE_CALIBRATION_PATH = (
    Path(__file__).with_name("data")
    / "automatic_retrieval_evidence_calibration.json"
)

MAX_FALSE_EVIDENCE_RISK = 0.05
MIN_RETAINED_ANSWER_RECALL = 0.95
MIN_NO_ANSWER_ABSTENTION_RATE = 0.90
MAX_SOURCE_KIND_GATE_DELTA = 0.05
MAX_AUTOMATIC_FANOUT = 3
NON_COLLECT_ACTIVATION_PAUSED_MESSAGE = (
    "shadow and active evidence modes remain paused until a separately reviewed "
    "calibration report and runtime binding check are implemented"
)

EvidenceMode = Literal["collect", "shadow", "active"]
EvidenceStatus = Literal[
    "unassessed",
    "would_support",
    "would_abstain",
    "would_be_inconclusive",
    "supported",
    "no_relevant_evidence",
    "inconclusive",
]

_MODES = frozenset({"collect", "shadow", "active"})
_SAFE_IDENTIFIER_RE = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
_SAFE_REVISION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+/-]{0,127}\Z")
_ROUTE_SELECTION_REASONS = frozenset(
    {
        "unique_title_or_alias",
        "multiple_named_corpora",
        "high_confidence_semantic",
        "ambiguous_semantic",
    }
)


class EvidenceCalibrationError(RuntimeError):
    """The evidence calibration artifact is absent, unsafe, or incompatible."""


@dataclass(frozen=True)
class CalibrationBindings:
    """Immutable inputs that a threshold was calibrated and certified against."""

    retrieval_revision: str | None
    dataset_revision: str | None
    evaluator_revision: str | None
    source_mix_revision: str | None

    @property
    def complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.retrieval_revision,
                self.dataset_revision,
                self.evaluator_revision,
                self.source_mix_revision,
            )
        )


@dataclass(frozen=True)
class EvidenceCertification:
    """Locked question-level certification counts and bounded gate results."""

    false_evidence_accepted_queries: int | None
    accepted_queries: int | None
    retained_answer_bearing_queries: int | None
    pre_gate_answer_bearing_queries: int | None
    abstained_no_answer_queries: int | None
    no_answer_queries: int | None
    max_source_false_evidence_risk_delta: float | None
    max_source_retained_recall_regression: float | None
    observed_max_fanout: int | None
    question_level_split_verified: bool
    locked_certification_verified: bool
    sample_sufficiency_passed: bool
    source_kind_gates_passed: bool
    multi_corpus_gates_passed: bool

    @property
    def false_evidence_risk(self) -> float | None:
        return _safe_rate(
            self.false_evidence_accepted_queries,
            self.accepted_queries,
        )

    @property
    def retained_answer_recall(self) -> float | None:
        return _safe_rate(
            self.retained_answer_bearing_queries,
            self.pre_gate_answer_bearing_queries,
        )

    @property
    def no_answer_abstention_rate(self) -> float | None:
        return _safe_rate(
            self.abstained_no_answer_queries,
            self.no_answer_queries,
        )

    @property
    def passes_bound_gates(self) -> bool:
        false_evidence_risk = self.false_evidence_risk
        retained_answer_recall = self.retained_answer_recall
        no_answer_abstention_rate = self.no_answer_abstention_rate
        source_false_evidence_delta = self.max_source_false_evidence_risk_delta
        source_recall_delta = self.max_source_retained_recall_regression
        max_fanout = self.observed_max_fanout
        return bool(
            false_evidence_risk is not None
            and false_evidence_risk <= MAX_FALSE_EVIDENCE_RISK
            and retained_answer_recall is not None
            and retained_answer_recall >= MIN_RETAINED_ANSWER_RECALL
            and no_answer_abstention_rate is not None
            and no_answer_abstention_rate >= MIN_NO_ANSWER_ABSTENTION_RATE
            and source_false_evidence_delta is not None
            and 0.0 <= source_false_evidence_delta <= MAX_SOURCE_KIND_GATE_DELTA
            and source_recall_delta is not None
            and 0.0 <= source_recall_delta <= MAX_SOURCE_KIND_GATE_DELTA
            and max_fanout is not None
            and 1 <= max_fanout <= MAX_AUTOMATIC_FANOUT
            and self.question_level_split_verified
            and self.locked_certification_verified
            and self.sample_sufficiency_passed
            and self.source_kind_gates_passed
            and self.multi_corpus_gates_passed
        )


@dataclass(frozen=True)
class EvidenceCalibration:
    """Strict, versioned authority for interpreting evidence score features."""

    schema_version: int
    calibration_id: str
    calibration_revision: str
    mode: EvidenceMode
    model: str
    model_revision: str
    feature_contract: str
    threshold: float | None
    owner_approved: bool
    bindings: CalibrationBindings
    certification: EvidenceCertification


@dataclass(frozen=True)
class EvidenceObservation:
    """Bounded numeric features from an exact final retrieval hit set."""

    top_score: float | None
    second_score: float | None
    score_gap: float | None
    candidates_scored: int
    route_selection_reason: str
    route_semantic_score: float | None
    route_semantic_margin: float | None
    namespace_failure_count: int

    def to_dict(self) -> dict[str, object]:
        """Return diagnostics that cannot contain query or candidate content."""

        return {
            "top_score": self.top_score,
            "second_score": self.second_score,
            "score_gap": self.score_gap,
            "candidates_scored": self.candidates_scored,
            "route_selection_reason": self.route_selection_reason,
            "route_semantic_score": self.route_semantic_score,
            "route_semantic_margin": self.route_semantic_margin,
            "namespace_failure_count": self.namespace_failure_count,
        }


@dataclass(frozen=True)
class EvidenceDecision:
    """One governed evidence outcome plus content-free public diagnostics."""

    calibration: EvidenceCalibration
    observation: EvidenceObservation
    status: EvidenceStatus
    reason: str
    is_weak: bool | None
    widening_triggered_by_weak_evidence: bool = False

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "mode": self.calibration.mode,
            "status": self.status,
            "reason": self.reason,
            "model": self.calibration.model,
            "model_revision": self.calibration.model_revision,
            "calibration_id": self.calibration.calibration_id,
            "calibration_revision": self.calibration.calibration_revision,
            "feature_contract": self.calibration.feature_contract,
            "threshold": self.calibration.threshold,
            "widening_triggered_by_weak_evidence": (
                self.widening_triggered_by_weak_evidence
            ),
        }
        payload.update(self.observation.to_dict())
        return payload


def load_evidence_calibration(
    path: str | Path | None = None,
) -> EvidenceCalibration:
    """Load and fully validate one calibration artifact without fallback."""

    artifact_path = (
        DEFAULT_EVIDENCE_CALIBRATION_PATH if path is None else Path(path)
    )
    try:
        raw = artifact_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        raise EvidenceCalibrationError(
            "automatic evidence calibration artifact is unavailable"
        ) from None

    try:
        payload = json.loads(
            raw,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_json_constant,
        )
    except (json.JSONDecodeError, UnicodeError, EvidenceCalibrationError):
        raise EvidenceCalibrationError(
            "automatic evidence calibration artifact is not valid strict JSON"
        ) from None

    artifact = _parse_calibration(payload)
    _validate_calibration_contract(artifact)
    if artifact.mode != "collect":
        raise EvidenceCalibrationError(NON_COLLECT_ACTIVATION_PAUSED_MESSAGE)
    return artifact


def observe_evidence_scores(
    scores: Sequence[float],
    *,
    route_selection_reason: str,
    route_semantic_score: float | None,
    route_semantic_margin: float | None,
    namespace_failure_count: int,
) -> EvidenceObservation:
    """Reduce finite candidate scores to the governed feature contract."""

    if isinstance(scores, (str, bytes, bytearray)):
        raise ValueError("evidence scores must be a numeric sequence")
    normalized = [
        _finite_runtime_number(score, field=f"scores[{index}]")
        for index, score in enumerate(scores)
    ]
    normalized.sort(reverse=True)

    if route_selection_reason not in _ROUTE_SELECTION_REASONS:
        raise ValueError("route_selection_reason is not part of the evidence contract")
    semantic_score = _optional_finite_runtime_number(
        route_semantic_score,
        field="route_semantic_score",
    )
    semantic_margin = _optional_finite_runtime_number(
        route_semantic_margin,
        field="route_semantic_margin",
    )
    if isinstance(namespace_failure_count, bool) or not isinstance(
        namespace_failure_count, int
    ):
        raise ValueError("namespace_failure_count must be an integer")
    if namespace_failure_count < 0:
        raise ValueError("namespace_failure_count must not be negative")

    top_score = normalized[0] if normalized else None
    second_score = normalized[1] if len(normalized) > 1 else None
    return EvidenceObservation(
        top_score=top_score,
        second_score=second_score,
        score_gap=(top_score - second_score if second_score is not None else None),
        candidates_scored=len(normalized),
        route_selection_reason=route_selection_reason,
        route_semantic_score=semantic_score,
        route_semantic_margin=semantic_margin,
        namespace_failure_count=namespace_failure_count,
    )


def decide_evidence(
    calibration: EvidenceCalibration,
    observation: EvidenceObservation,
    *,
    widening_triggered_by_weak_evidence: bool = False,
) -> EvidenceDecision:
    """Interpret one observation according to a validated calibration mode."""

    _validate_calibration_contract(calibration)
    if not isinstance(widening_triggered_by_weak_evidence, bool):
        raise ValueError("widening_triggered_by_weak_evidence must be a boolean")

    if calibration.mode == "collect":
        return EvidenceDecision(
            calibration=calibration,
            observation=observation,
            status="unassessed",
            reason="threshold_not_calibrated",
            is_weak=None,
            widening_triggered_by_weak_evidence=(
                widening_triggered_by_weak_evidence
            ),
        )

    threshold = calibration.threshold
    if threshold is None:  # Defensive: contract validation rejects this first.
        raise EvidenceCalibrationError(
            "threshold-bearing evidence mode has no calibrated threshold"
        )
    if observation.top_score is None:
        weak = True
        reason = "no_candidates"
    elif observation.top_score < threshold:
        weak = True
        reason = "top_score_below_threshold"
    else:
        weak = False
        reason = "top_score_at_or_above_threshold"

    if calibration.mode == "shadow":
        if not weak:
            status: EvidenceStatus = "would_support"
        elif observation.namespace_failure_count:
            status = "would_be_inconclusive"
        else:
            status = "would_abstain"
    elif not weak:
        status = "supported"
    elif observation.namespace_failure_count:
        status = "inconclusive"
    else:
        status = "no_relevant_evidence"

    return EvidenceDecision(
        calibration=calibration,
        observation=observation,
        status=status,
        reason=reason,
        is_weak=weak,
        widening_triggered_by_weak_evidence=widening_triggered_by_weak_evidence,
    )


def _parse_calibration(value: object) -> EvidenceCalibration:
    payload = _strict_object(
        value,
        field="artifact",
        keys={
            "schema_version",
            "calibration_id",
            "calibration_revision",
            "mode",
            "model",
            "model_revision",
            "feature_contract",
            "threshold",
            "owner_approved",
            "bindings",
            "certification",
        },
    )
    mode_value = _strict_string(payload["mode"], field="mode")
    if mode_value not in _MODES:
        raise EvidenceCalibrationError("mode is not supported")
    return EvidenceCalibration(
        schema_version=_strict_integer(
            payload["schema_version"],
            field="schema_version",
        ),
        calibration_id=_strict_string(
            payload["calibration_id"],
            field="calibration_id",
        ),
        calibration_revision=_strict_string(
            payload["calibration_revision"],
            field="calibration_revision",
        ),
        mode=cast(EvidenceMode, mode_value),
        model=_strict_string(payload["model"], field="model"),
        model_revision=_strict_string(
            payload["model_revision"],
            field="model_revision",
        ),
        feature_contract=_strict_string(
            payload["feature_contract"],
            field="feature_contract",
        ),
        threshold=_optional_strict_number(
            payload["threshold"],
            field="threshold",
        ),
        owner_approved=_strict_boolean(
            payload["owner_approved"],
            field="owner_approved",
        ),
        bindings=_parse_bindings(payload["bindings"]),
        certification=_parse_certification(payload["certification"]),
    )


def _parse_bindings(value: object) -> CalibrationBindings:
    payload = _strict_object(
        value,
        field="bindings",
        keys={
            "retrieval_revision",
            "dataset_revision",
            "evaluator_revision",
            "source_mix_revision",
        },
    )
    return CalibrationBindings(
        retrieval_revision=_optional_strict_string(
            payload["retrieval_revision"], field="bindings.retrieval_revision"
        ),
        dataset_revision=_optional_strict_string(
            payload["dataset_revision"], field="bindings.dataset_revision"
        ),
        evaluator_revision=_optional_strict_string(
            payload["evaluator_revision"], field="bindings.evaluator_revision"
        ),
        source_mix_revision=_optional_strict_string(
            payload["source_mix_revision"], field="bindings.source_mix_revision"
        ),
    )


def _parse_certification(value: object) -> EvidenceCertification:
    keys = {
        "false_evidence_accepted_queries",
        "accepted_queries",
        "retained_answer_bearing_queries",
        "pre_gate_answer_bearing_queries",
        "abstained_no_answer_queries",
        "no_answer_queries",
        "max_source_false_evidence_risk_delta",
        "max_source_retained_recall_regression",
        "observed_max_fanout",
        "question_level_split_verified",
        "locked_certification_verified",
        "sample_sufficiency_passed",
        "source_kind_gates_passed",
        "multi_corpus_gates_passed",
    }
    payload = _strict_object(value, field="certification", keys=keys)
    return EvidenceCertification(
        false_evidence_accepted_queries=_optional_strict_integer(
            payload["false_evidence_accepted_queries"],
            field="certification.false_evidence_accepted_queries",
        ),
        accepted_queries=_optional_strict_integer(
            payload["accepted_queries"],
            field="certification.accepted_queries",
        ),
        retained_answer_bearing_queries=_optional_strict_integer(
            payload["retained_answer_bearing_queries"],
            field="certification.retained_answer_bearing_queries",
        ),
        pre_gate_answer_bearing_queries=_optional_strict_integer(
            payload["pre_gate_answer_bearing_queries"],
            field="certification.pre_gate_answer_bearing_queries",
        ),
        abstained_no_answer_queries=_optional_strict_integer(
            payload["abstained_no_answer_queries"],
            field="certification.abstained_no_answer_queries",
        ),
        no_answer_queries=_optional_strict_integer(
            payload["no_answer_queries"],
            field="certification.no_answer_queries",
        ),
        max_source_false_evidence_risk_delta=_optional_strict_number(
            payload["max_source_false_evidence_risk_delta"],
            field="certification.max_source_false_evidence_risk_delta",
        ),
        max_source_retained_recall_regression=_optional_strict_number(
            payload["max_source_retained_recall_regression"],
            field="certification.max_source_retained_recall_regression",
        ),
        observed_max_fanout=_optional_strict_integer(
            payload["observed_max_fanout"],
            field="certification.observed_max_fanout",
        ),
        question_level_split_verified=_strict_boolean(
            payload["question_level_split_verified"],
            field="certification.question_level_split_verified",
        ),
        locked_certification_verified=_strict_boolean(
            payload["locked_certification_verified"],
            field="certification.locked_certification_verified",
        ),
        sample_sufficiency_passed=_strict_boolean(
            payload["sample_sufficiency_passed"],
            field="certification.sample_sufficiency_passed",
        ),
        source_kind_gates_passed=_strict_boolean(
            payload["source_kind_gates_passed"],
            field="certification.source_kind_gates_passed",
        ),
        multi_corpus_gates_passed=_strict_boolean(
            payload["multi_corpus_gates_passed"],
            field="certification.multi_corpus_gates_passed",
        ),
    )


def _validate_calibration_contract(calibration: EvidenceCalibration) -> None:
    if calibration.schema_version != EVIDENCE_CALIBRATION_SCHEMA_VERSION:
        raise EvidenceCalibrationError("calibration schema version is incompatible")
    if not _SAFE_IDENTIFIER_RE.fullmatch(calibration.calibration_id):
        raise EvidenceCalibrationError("calibration_id is invalid")
    if not _SAFE_IDENTIFIER_RE.fullmatch(calibration.calibration_revision):
        raise EvidenceCalibrationError("calibration_revision is invalid")
    if calibration.model != CROSS_ENCODER_MODEL:
        raise EvidenceCalibrationError("calibration model is incompatible")
    if calibration.model_revision != CROSS_ENCODER_REVISION:
        raise EvidenceCalibrationError("calibration model revision is incompatible")
    if calibration.feature_contract != EVIDENCE_FEATURE_CONTRACT:
        raise EvidenceCalibrationError("calibration feature contract is incompatible")

    for name, revision in (
        ("retrieval_revision", calibration.bindings.retrieval_revision),
        ("dataset_revision", calibration.bindings.dataset_revision),
        ("evaluator_revision", calibration.bindings.evaluator_revision),
        ("source_mix_revision", calibration.bindings.source_mix_revision),
    ):
        if revision is not None and not _SAFE_REVISION_RE.fullmatch(revision):
            raise EvidenceCalibrationError(f"bindings.{name} is invalid")

    _validate_certification_counts(calibration.certification)

    if calibration.mode == "collect":
        if calibration.threshold is not None:
            raise EvidenceCalibrationError("collect mode must not declare a threshold")
        if calibration.owner_approved:
            raise EvidenceCalibrationError("collect mode cannot be owner-approved")
        if calibration.bindings.complete:
            raise EvidenceCalibrationError("collect mode cannot declare complete bindings")
        return

    if calibration.threshold is None or not math.isfinite(calibration.threshold):
        raise EvidenceCalibrationError(
            "shadow and active modes require a finite calibrated threshold"
        )
    if not calibration.bindings.complete:
        raise EvidenceCalibrationError(
            "shadow and active modes require complete calibration bindings"
        )
    if calibration.mode == "active" and not (
        calibration.owner_approved
        and calibration.certification.passes_bound_gates
    ):
        raise EvidenceCalibrationError(
            "active evidence calibration is not owner-approved and certified"
        )


def _validate_certification_counts(certification: EvidenceCertification) -> None:
    pairs = (
        (
            certification.false_evidence_accepted_queries,
            certification.accepted_queries,
            "false evidence",
        ),
        (
            certification.retained_answer_bearing_queries,
            certification.pre_gate_answer_bearing_queries,
            "retained answer",
        ),
        (
            certification.abstained_no_answer_queries,
            certification.no_answer_queries,
            "no-answer abstention",
        ),
    )
    for numerator, denominator, label in pairs:
        if numerator is None and denominator is None:
            continue
        if numerator is None or denominator is None:
            raise EvidenceCalibrationError(
                f"certification {label} counts must be provided together"
            )
        if numerator < 0 or denominator <= 0 or numerator > denominator:
            raise EvidenceCalibrationError(
                f"certification {label} counts are invalid"
            )
    if (
        certification.observed_max_fanout is not None
        and certification.observed_max_fanout < 0
    ):
        raise EvidenceCalibrationError("certification observed_max_fanout is invalid")
    for value, label in (
        (
            certification.max_source_false_evidence_risk_delta,
            "max_source_false_evidence_risk_delta",
        ),
        (
            certification.max_source_retained_recall_regression,
            "max_source_retained_recall_regression",
        ),
    ):
        if value is not None and value < 0:
            raise EvidenceCalibrationError(f"certification {label} is invalid")


def _safe_rate(numerator: int | None, denominator: int | None) -> float | None:
    if numerator is None or denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def _strict_object(
    value: object,
    *,
    field: str,
    keys: set[str],
) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise EvidenceCalibrationError(f"{field} must be an object")
    actual = set(value)
    if actual != keys:
        raise EvidenceCalibrationError(f"{field} has missing or unknown fields")
    return value


def _strict_string(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise EvidenceCalibrationError(f"{field} must be a string")
    return value


def _optional_strict_string(value: object, *, field: str) -> str | None:
    if value is None:
        return None
    return _strict_string(value, field=field)


def _strict_boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise EvidenceCalibrationError(f"{field} must be a boolean")
    return value


def _strict_integer(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise EvidenceCalibrationError(f"{field} must be an integer")
    return value


def _optional_strict_integer(value: object, *, field: str) -> int | None:
    if value is None:
        return None
    return _strict_integer(value, field=field)


def _optional_strict_number(value: object, *, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise EvidenceCalibrationError(f"{field} must be a number or null")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise EvidenceCalibrationError(f"{field} must be finite")
    return normalized


def _finite_runtime_number(value: object, *, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"{field} must be finite")
    return normalized


def _optional_finite_runtime_number(
    value: object,
    *,
    field: str,
) -> float | None:
    if value is None:
        return None
    return _finite_runtime_number(value, field=field)


def _reject_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceCalibrationError("calibration JSON contains duplicate fields")
        result[key] = value
    return result


def _reject_non_finite_json_constant(_value: str) -> object:
    raise EvidenceCalibrationError("calibration JSON contains a non-finite number")
