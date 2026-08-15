"""Pure, provider-free contracts for scalable namespace-routing quality.

This module deliberately does not construct models, clients, or content
retrievers.  It owns the checked-in canary shape, the route-only projection of
the approved 50-case answer-quality basket, content-free observations,
deterministic confidence calibration, and activation metrics.  A later runner
may collect observations through the production router, but collection is not
implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Mapping, Sequence

from buoy_search.catalog import (
    MAX_ROUTING_EXAMPLE_CHARACTERS,
    MAX_ROUTING_EXAMPLES,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_PROJECTION,
    ROUTING_PROTOTYPE_CONTRACT,
    card_passage_text,
    canonical_text,
)
from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.multi_corpus_evals import (
    DEFAULT_MULTI_CORPUS_EVAL_DATASET,
    MultiCorpusEvalDataset,
    load_multi_corpus_eval_dataset,
)
from buoy_search.plan_artifacts import stable_hash


DEFAULT_ROUTING_CANARY_DIR = Path(__file__).with_name("data") / "routing_canaries"
DEFAULT_ROUTING_CALIBRATION = (
    Path(__file__).with_name("data")
    / "automatic_routing_confidence_calibration.json"
)

ROUTING_CANARY_SCHEMA_VERSION = 1
ROUTING_QUALITY_RUN_SCHEMA_VERSION = 1
ROUTING_CALIBRATION_SCHEMA_VERSION = 1
ROUTING_QUALITY_EVALUATOR_VERSION = "1"
ROUTING_CALIBRATION_ID = "automatic-routing-confidence-v2"

ROUTING_SHORTLIST_LIMIT = 12
ROUTING_MAX_EXAMPLES = MAX_ROUTING_EXAMPLES
ROUTING_MAX_FANOUT = 3
ROUTING_RECALL_MINIMUM = 0.95
ROUTING_AVERAGE_INITIAL_FANOUT_MAXIMUM = 2.0
ROUTING_SCHEMA_CONTRACT = "remote-routing-card-schema-v1-v2"
ROUTING_PROJECTION_CONTRACT = ROUTING_PROJECTION
ROUTING_ROUTE_CONTRACT_REVISION = ROUTING_PROTOTYPE_CONTRACT
ROUTING_CONFIDENCE_FEATURE_CONTRACT = "max_prototype_score_and_margin_v1"
ROUTING_CONFIDENCE_SCORE_FIELD = "reranker_score"
ROUTING_CONFIDENCE_MARGIN_FIELD = "reranker_margin"

CANARY_ROLES = frozenset(
    {"named_self", "capability_self", "confusable_self", "contrast_other"}
)
CANARY_SPLITS = frozenset({"calibration", "gate"})
SELECTION_REASONS = frozenset(
    {
        "unique_title_or_alias",
        "multiple_named_corpora",
        "high_confidence_semantic",
        "ambiguous_semantic",
        "high_confidence_prototype",
        "ambiguous_prototype",
    }
)

_PACK_FIELDS = {
    "schema_version",
    "corpus_id",
    "namespace",
    "review_status",
    "human_approved",
    "route_contract_revision",
    "canaries_disjoint_from_routing_examples",
    "cases",
}
_CASE_FIELDS = {
    "id",
    "role",
    "split",
    "question",
    "expected_namespaces",
    "confusable_with",
}
_CALIBRATION_FIELDS = {
    "schema_version",
    "calibration_id",
    "calibration_revision",
    "mode",
    "owner_approved",
    "score_floor",
    "margin_floor",
    "bindings",
    "certification",
}
_CALIBRATION_BINDING_FIELDS = {
    "routing_model",
    "routing_model_revision",
    "routing_reranker_model",
    "routing_reranker_revision",
    "schema_contract",
    "projection",
    "shortlist_limit",
    "max_examples",
    "feature_contract",
    "score_field",
    "margin_field",
    "canary_suite_sha256",
    "catalog_projection_sha256",
}
_COLLECT_CERTIFICATION_FIELDS = {"passed", "case_count", "verdict_sha256"}
_SAFE_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True)
class RoutingCorpusIdentity:
    corpus_id: str
    namespace: str


@dataclass(frozen=True)
class RoutingQualityCase:
    id: str
    origin: str
    subject_namespace: str | None
    role: str
    split: str
    question: str
    expected_namespaces: tuple[str, ...]
    confusable_with: tuple[str, ...]


@dataclass(frozen=True)
class RoutingCanaryPack:
    corpus_id: str
    namespace: str
    raw_sha256: str
    review_status: str
    human_approved: bool
    route_contract_revision: str
    canaries_disjoint_from_routing_examples: bool
    cases: tuple[RoutingQualityCase, ...]


@dataclass(frozen=True)
class RoutingQualityDataset:
    suite_sha256: str
    legacy_dataset_id: str
    legacy_dataset_sha256: str
    legacy_namespaces: tuple[str, ...]
    corpora: tuple[RoutingCorpusIdentity, ...]
    packs: tuple[RoutingCanaryPack, ...]
    cases: tuple[RoutingQualityCase, ...]

    @property
    def cases_by_id(self) -> dict[str, RoutingQualityCase]:
        return {case.id: case for case in self.cases}

    @property
    def corpus_namespaces(self) -> dict[str, str]:
        return {corpus.corpus_id: corpus.namespace for corpus in self.corpora}

    @property
    def approved_covered_namespaces(self) -> tuple[str, ...]:
        covered = set(self.legacy_namespaces)
        covered.update(
            pack.namespace
            for pack in self.packs
            if pack.human_approved and pack.review_status == "approved"
        )
        return tuple(sorted(covered))

    @property
    def covered_namespaces(self) -> tuple[str, ...]:
        """Namespaces represented by legacy cases or any candidate pack."""

        covered = set(self.legacy_namespaces)
        covered.update(pack.namespace for pack in self.packs)
        return tuple(sorted(covered))


@dataclass(frozen=True)
class RoutingCorpusObservation:
    namespace: str
    shortlist_rank: int
    shortlist_cosine_score: float
    reranker_rank: int
    reranker_score: float
    exact_name_match: bool
    winning_prototype_kind: str
    winning_prototype_index: int | None
    winning_prototype_hash: str


@dataclass(frozen=True)
class RoutingCaseObservation:
    case_id: str
    corpus_scores: tuple[RoutingCorpusObservation, ...]
    reranker_margin: float | None
    fallback_namespaces: tuple[str, ...]
    initial_namespaces: tuple[str, ...]
    selection_reason: str
    high_confidence: bool
    initial_fanout: int


@dataclass(frozen=True)
class RoutingRouteObservation:
    """Strategy-neutral route shape used for a same-catalog baseline."""

    case_id: str
    shortlist_namespaces: tuple[str, ...]
    exact_name_namespaces: tuple[str, ...]
    fallback_namespaces: tuple[str, ...]
    initial_namespaces: tuple[str, ...]
    selection_reason: str
    high_confidence: bool
    initial_fanout: int


@dataclass(frozen=True)
class RoutingThresholdCalibration:
    score_floor: float
    margin_floor: float
    calibration_case_count: int
    correct_high_confidence_singletons: int
    incorrect_high_confidence_singletons: int
    average_initial_fanout: float
    calibration_case_ids_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "score_floor": self.score_floor,
            "margin_floor": self.margin_floor,
            "calibration_case_count": self.calibration_case_count,
            "correct_high_confidence_singletons": (
                self.correct_high_confidence_singletons
            ),
            "incorrect_high_confidence_singletons": (
                self.incorrect_high_confidence_singletons
            ),
            "average_initial_fanout": self.average_initial_fanout,
            "calibration_case_ids_sha256": self.calibration_case_ids_sha256,
        }


@dataclass(frozen=True)
class RoutingConfidenceBindings:
    routing_model: str
    routing_model_revision: str
    routing_reranker_model: str
    routing_reranker_revision: str
    schema_contract: str
    projection: str
    shortlist_limit: int
    max_examples: int
    feature_contract: str
    score_field: str
    margin_field: str
    canary_suite_sha256: str | None
    catalog_projection_sha256: str | None


@dataclass(frozen=True)
class RoutingConfidenceCalibration:
    schema_version: int
    calibration_id: str
    calibration_revision: str
    mode: str
    owner_approved: bool
    score_floor: float | None
    margin_floor: float | None
    bindings: RoutingConfidenceBindings
    certification_passed: bool
    certification_case_count: int
    certification_verdict_sha256: str | None


@dataclass(frozen=True)
class RoutingCaseMetrics:
    case_id: str
    subject_namespace: str | None
    expected_namespaces: tuple[str, ...]
    shortlist_found: int
    shortlist_complete: bool
    route_found: int
    route_complete: bool
    named_self_passed: bool | None
    contrast_passed: bool | None
    multi_corpus_passed: bool | None
    incorrect_high_confidence_singleton: bool
    no_answer_high_confidence_singleton: bool

    @property
    def gate_passed(self) -> bool:
        optional = (
            self.named_self_passed,
            self.contrast_passed,
            self.multi_corpus_passed,
        )
        return (
            self.shortlist_complete
            and self.route_complete
            and all(value is not False for value in optional)
            and not self.incorrect_high_confidence_singleton
            and not self.no_answer_high_confidence_singleton
        )


@dataclass(frozen=True)
class PerCorpusRoutingMetrics:
    namespace: str
    positive_case_total: int
    positive_cases_found_at_3: int
    positive_recall_at_3: float | None
    certification_shortlist_required_total: int
    certification_shortlist_required_found: int
    certification_shortlist_recall_at_12: float | None


@dataclass(frozen=True)
class RoutingQualityMetrics:
    shortlist_recall_at_12: float
    shortlist_required_total: int
    shortlist_required_found: int
    route_recall_at_3: float
    route_required_total: int
    route_required_found: int
    named_self_total: int
    named_self_passed: int
    contrast_total: int
    contrast_passed: int
    multi_corpus_total: int
    multi_corpus_passed: int
    incorrect_high_confidence_singletons: int
    no_answer_high_confidence_singletons: int
    average_initial_fanout: float
    maximum_initial_fanout: int
    maximum_fallback_fanout: int
    case_metrics: tuple[RoutingCaseMetrics, ...]
    per_corpus: tuple[PerCorpusRoutingMetrics, ...]

    @property
    def cases_by_id(self) -> dict[str, RoutingCaseMetrics]:
        return {case.case_id: case for case in self.case_metrics}

    @property
    def per_corpus_by_namespace(self) -> dict[str, PerCorpusRoutingMetrics]:
        return {corpus.namespace: corpus for corpus in self.per_corpus}

    def to_dict(self) -> dict[str, object]:
        return {
            "shortlist_recall_at_12": self.shortlist_recall_at_12,
            "shortlist_required_total": self.shortlist_required_total,
            "shortlist_required_found": self.shortlist_required_found,
            "route_recall_at_3": self.route_recall_at_3,
            "route_required_total": self.route_required_total,
            "route_required_found": self.route_required_found,
            "named_self_total": self.named_self_total,
            "named_self_passed": self.named_self_passed,
            "contrast_total": self.contrast_total,
            "contrast_passed": self.contrast_passed,
            "multi_corpus_total": self.multi_corpus_total,
            "multi_corpus_passed": self.multi_corpus_passed,
            "incorrect_high_confidence_singletons": (
                self.incorrect_high_confidence_singletons
            ),
            "no_answer_high_confidence_singletons": (
                self.no_answer_high_confidence_singletons
            ),
            "average_initial_fanout": self.average_initial_fanout,
            "maximum_initial_fanout": self.maximum_initial_fanout,
            "maximum_fallback_fanout": self.maximum_fallback_fanout,
            "per_corpus": [
                {
                    "namespace": item.namespace,
                    "positive_case_total": item.positive_case_total,
                    "positive_cases_found_at_3": item.positive_cases_found_at_3,
                    "positive_recall_at_3": item.positive_recall_at_3,
                    "certification_shortlist_required_total": (
                        item.certification_shortlist_required_total
                    ),
                    "certification_shortlist_required_found": (
                        item.certification_shortlist_required_found
                    ),
                    "certification_shortlist_recall_at_12": (
                        item.certification_shortlist_recall_at_12
                    ),
                }
                for item in self.per_corpus
            ],
        }


@dataclass(frozen=True)
class RoutingQualityVerdict:
    passed: bool
    failed_checks: tuple[str, ...]
    checks: Mapping[str, Mapping[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "failed_checks": list(self.failed_checks),
            "checks": {name: dict(value) for name, value in self.checks.items()},
        }


def load_routing_canary_pack(path: Path) -> RoutingCanaryPack:
    """Load one exact five-case per-corpus canary pack."""

    raw = path.read_bytes()
    payload = _load_strict_json(raw, where=f"routing canary pack {path}")
    item = _required_mapping(payload, where=f"routing canary pack {path}")
    _require_exact_fields(item, _PACK_FIELDS, where=f"routing canary pack {path}")
    if item.get("schema_version") != ROUTING_CANARY_SCHEMA_VERSION:
        raise ValueError(
            f"Routing canary pack schema_version must be {ROUTING_CANARY_SCHEMA_VERSION}."
        )
    corpus_id = _safe_id(item.get("corpus_id"), where="routing canary corpus_id")
    namespace = _safe_id(item.get("namespace"), where="routing canary namespace")
    review_status = _required_string(
        item, "review_status", where="routing canary pack"
    )
    if review_status not in {"candidate", "approved"}:
        raise ValueError(
            "Routing canary review_status must be 'candidate' or 'approved'."
        )
    human_approved = item.get("human_approved")
    if not isinstance(human_approved, bool):
        raise ValueError("Routing canary human_approved must be a boolean.")
    if human_approved != (review_status == "approved"):
        raise ValueError(
            "Routing canary human_approved and review_status='approved' must agree."
        )
    route_revision = _safe_id(
        item.get("route_contract_revision"),
        where="routing canary route_contract_revision",
    )
    if route_revision != ROUTING_ROUTE_CONTRACT_REVISION:
        raise ValueError(
            "Routing canary route_contract_revision must be "
            f"{ROUTING_ROUTE_CONTRACT_REVISION!r}."
        )
    disjoint = item.get("canaries_disjoint_from_routing_examples")
    if not isinstance(disjoint, bool):
        raise ValueError(
            "Routing canary disjointness assertion must be a boolean."
        )
    if human_approved and not disjoint:
        raise ValueError(
            "An approved routing canary pack must affirm routing-example disjointness."
        )
    raw_cases = item.get("cases")
    if not isinstance(raw_cases, list) or len(raw_cases) != 5:
        raise ValueError("Routing canary pack must contain exactly five cases.")
    cases = tuple(
        _parse_canary_case(
            raw_case,
            corpus_id=corpus_id,
            namespace=namespace,
        )
        for raw_case in raw_cases
    )
    _validate_five_case_roles(cases, corpus_id=corpus_id, namespace=namespace)
    _require_unique([case.id for case in cases], where="routing canary case IDs")
    _require_unique(
        [canonical_text(case.question) for case in cases],
        where="routing canary normalized questions",
    )
    return RoutingCanaryPack(
        corpus_id=corpus_id,
        namespace=namespace,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        review_status=review_status,
        human_approved=human_approved,
        route_contract_revision=route_revision,
        canaries_disjoint_from_routing_examples=disjoint,
        cases=cases,
    )


def project_approved_50_routes(
    dataset: MultiCorpusEvalDataset,
) -> tuple[RoutingQualityCase, ...]:
    """Project only route labels/questions from the immutable approved basket."""

    if (
        len(dataset.cases) != 50
        or not dataset.human_approved_ground_truth
        or dataset.review_status != "approved"
    ):
        raise ValueError(
            "Routing quality requires the exact approved 50-case legacy basket."
        )
    role_by_category = {
        "unambiguous": "legacy_named",
        "descriptor_free_confusable": "legacy_descriptor",
        "multi_corpus": "legacy_multi",
        "no_answer": "legacy_no_answer",
    }
    projected: list[RoutingQualityCase] = []
    for case in dataset.cases:
        try:
            role = role_by_category[case.category]
        except KeyError as exc:
            raise ValueError(
                f"Approved legacy route case {case.id!r} has an unknown category."
            ) from exc
        subject = case.expected_namespaces[0] if len(case.expected_namespaces) == 1 else None
        projected.append(
            RoutingQualityCase(
                id=f"approved50:{case.id}",
                origin="approved50",
                subject_namespace=subject,
                role=role,
                split="gate",
                question=case.question,
                expected_namespaces=case.expected_namespaces,
                confusable_with=(),
            )
        )
    return tuple(projected)


def load_routing_quality_dataset(
    *,
    canary_dir: Path | None = None,
    legacy_dataset_path: Path | None = None,
) -> RoutingQualityDataset:
    """Merge the approved route projection with sorted modular canary packs."""

    legacy = load_multi_corpus_eval_dataset(
        legacy_dataset_path or DEFAULT_MULTI_CORPUS_EVAL_DATASET
    )
    projected = project_approved_50_routes(legacy)
    directory = canary_dir or DEFAULT_ROUTING_CANARY_DIR
    if directory.exists() and not directory.is_dir():
        raise ValueError("Routing canary path must be a directory.")
    paths = sorted(directory.glob("*.json")) if directory.exists() else []
    packs = tuple(
        sorted(
            (load_routing_canary_pack(path) for path in paths),
            key=lambda pack: (pack.namespace, pack.corpus_id),
        )
    )

    identities: dict[str, str] = {
        corpus.id: corpus.namespace for corpus in legacy.logical_corpora
    }
    namespaces_to_corpora = {value: key for key, value in identities.items()}
    for pack in packs:
        existing_namespace = identities.get(pack.corpus_id)
        if existing_namespace is not None and existing_namespace != pack.namespace:
            raise ValueError(
                f"Corpus {pack.corpus_id!r} maps to conflicting namespaces."
            )
        existing_corpus = namespaces_to_corpora.get(pack.namespace)
        if existing_corpus is not None and existing_corpus != pack.corpus_id:
            raise ValueError(
                f"Namespace {pack.namespace!r} maps to conflicting corpus IDs."
            )
        identities[pack.corpus_id] = pack.namespace
        namespaces_to_corpora[pack.namespace] = pack.corpus_id
    _require_unique([pack.corpus_id for pack in packs], where="routing canary corpus IDs")
    _require_unique([pack.namespace for pack in packs], where="routing canary namespaces")

    cases = (*projected, *(case for pack in packs for case in pack.cases))
    _require_unique([case.id for case in cases], where="routing quality case IDs")
    _require_unique(
        [canonical_text(case.question) for case in cases],
        where="routing quality normalized questions",
    )
    known_corpora = set(identities)
    known_namespaces = set(identities.values())
    for case in cases:
        if not set(case.expected_namespaces) <= known_namespaces:
            raise ValueError(
                f"Routing quality case {case.id!r} expects an unknown namespace."
            )
        if not set(case.confusable_with) <= known_corpora:
            raise ValueError(
                f"Routing quality case {case.id!r} names an unknown confusable corpus."
            )

    suite_sha = routing_quality_suite_sha256(
        legacy_dataset_id=legacy.dataset_id,
        legacy_dataset_sha256=legacy.canonical_sha256,
        packs=packs,
    )
    return RoutingQualityDataset(
        suite_sha256=suite_sha,
        legacy_dataset_id=legacy.dataset_id,
        legacy_dataset_sha256=legacy.canonical_sha256,
        legacy_namespaces=tuple(sorted(legacy.eligible_namespaces)),
        corpora=tuple(
            RoutingCorpusIdentity(corpus_id, namespace)
            for corpus_id, namespace in sorted(identities.items())
        ),
        packs=packs,
        cases=tuple(cases),
    )


def routing_certification_dataset(
    dataset: RoutingQualityDataset,
) -> RoutingQualityDataset:
    """Project the immutable suite to certification cases only.

    Canary calibration cases remain available through ``dataset.packs`` for
    binding the threshold receipt, but they cannot contribute to certification
    metrics or regression claims.
    """

    cases = tuple(case for case in dataset.cases if case.split == "gate")
    if not cases or any(case.split != "gate" for case in cases):
        raise ValueError("Routing certification requires non-empty gate cases.")
    return replace(dataset, cases=cases)


def routing_quality_suite_sha256(
    *,
    legacy_dataset_id: str,
    legacy_dataset_sha256: str,
    packs: Sequence[RoutingCanaryPack],
) -> str:
    """Bind the legacy source and exact raw bytes of every modular pack."""

    _safe_id(legacy_dataset_id, where="legacy routing dataset_id")
    _sha256(legacy_dataset_sha256, where="legacy routing dataset sha256")
    ordered = sorted(packs, key=lambda pack: pack.namespace)
    _require_unique([pack.namespace for pack in ordered], where="routing suite namespaces")
    return stable_hash(
        {
            "contract": "routing-quality-suite/v1",
            "legacy_dataset_id": legacy_dataset_id,
            "legacy_dataset_sha256": legacy_dataset_sha256,
            "packs": [
                {"namespace": pack.namespace, "raw_sha256": pack.raw_sha256}
                for pack in ordered
            ],
        }
    )


def routing_example_passage(*, title: str, summary: str, example: str) -> str:
    """Return the exact governed passage for one routing example."""

    return f"Title: {title}\nSummary: {summary}\nRouting example: {example}"


def routing_prototype_hash(value: str) -> str:
    """Return a content-free identity for one exact prototype passage."""

    if not isinstance(value, str) or not value:
        raise ValueError("Routing prototype text must be a non-empty string.")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def routing_catalog_projection_sha256(cards: Sequence[object]) -> str:
    """Hash only semantic state capable of changing automatic routing."""

    projections: list[dict[str, object]] = []
    namespaces: list[str] = []
    for card in cards:
        namespace = _safe_id(
            _object_field(card, "namespace"), where="routing card namespace"
        )
        namespaces.append(namespace)
        enabled = _object_field(card, "enabled")
        if not isinstance(enabled, bool):
            raise ValueError(f"Routing card {namespace!r} enabled must be boolean.")
        title = _nonempty_object_string(card, "title", namespace=namespace)
        summary = _nonempty_object_string(card, "summary", namespace=namespace)
        aliases = _canonical_string_sequence(
            _object_field(card, "aliases"), where=f"routing card {namespace!r} aliases"
        )
        tags = _canonical_string_sequence(
            _object_field(card, "tags"), where=f"routing card {namespace!r} tags"
        )
        raw_examples = _object_field(card, "routing_examples", default=())
        examples = _canonical_string_sequence(
            raw_examples, where=f"routing card {namespace!r} routing_examples"
        )
        if len(examples) > ROUTING_MAX_EXAMPLES:
            raise ValueError(
                f"Routing card {namespace!r} has more than {ROUTING_MAX_EXAMPLES} examples."
            )
        if any(len(example) > MAX_ROUTING_EXAMPLE_CHARACTERS for example in examples):
            raise ValueError(
                f"Routing card {namespace!r} has an overlong routing example."
            )
        base = card_passage_text(
            title=title,
            summary=summary,
            aliases=aliases,
            tags=tags,
        )
        prototype_hashes = [routing_prototype_hash(base)]
        prototype_hashes.extend(
            routing_prototype_hash(
                routing_example_passage(title=title, summary=summary, example=example)
            )
            for example in examples
        )
        semantic_hash = _nonempty_object_string(
            card, "semantic_hash", namespace=namespace
        )
        vector_hash_value = _nonempty_object_string(
            card, "vector_hash", namespace=namespace
        )
        projections.append(
            {
                "namespace": namespace,
                "enabled": enabled,
                "title": title,
                "summary": summary,
                "aliases": list(aliases),
                "tags": list(tags),
                "routing_examples": list(examples),
                "semantic_hash": semantic_hash,
                "vector_hash": vector_hash_value,
                "routing_prototype_hash": _nonempty_object_string(
                    card,
                    "routing_prototype_hash",
                    namespace=namespace,
                    default=semantic_hash,
                ),
                "routing_prototype_vector_hash": _nonempty_object_string(
                    card,
                    "routing_prototype_vector_hash",
                    namespace=namespace,
                    default=vector_hash_value,
                ),
                "prototype_hashes": prototype_hashes,
                "routing_model": _nonempty_object_string(
                    card, "routing_model", namespace=namespace
                ),
                "routing_model_revision": _nonempty_object_string(
                    card, "routing_model_revision", namespace=namespace
                ),
            }
        )
    _require_unique(namespaces, where="routing catalog projection namespaces")
    return stable_hash(sorted(projections, key=lambda item: str(item["namespace"])))


def validate_canary_catalog_contract(
    dataset: RoutingQualityDataset,
    eligible_cards: Sequence[object],
) -> str:
    """Require collectible coverage and exact canary/example disjointness.

    Candidate packs are intentionally collectible before owner approval. The
    activation gate separately requires approved coverage, so collection can
    never confer routing authority.
    """

    card_by_namespace: dict[str, object] = {}
    all_examples: dict[str, str] = {}
    for card in eligible_cards:
        namespace = _safe_id(
            _object_field(card, "namespace"), where="eligible routing card namespace"
        )
        if namespace in card_by_namespace:
            raise ValueError(f"Eligible routing cards repeat namespace {namespace!r}.")
        enabled = _object_field(card, "enabled")
        if enabled is not True:
            raise ValueError("Canary catalog validation accepts enabled eligible cards only.")
        card_by_namespace[namespace] = card
        for example in _canonical_string_sequence(
            _object_field(card, "routing_examples", default=()),
            where=f"routing card {namespace!r} routing_examples",
        ):
            key = canonical_text(example)
            all_examples.setdefault(key, namespace)

    eligible = set(card_by_namespace)
    covered = set(dataset.covered_namespaces)
    missing_coverage = sorted(eligible - covered)
    if missing_coverage:
        raise ValueError(
            "Enabled eligible routing corpora lack collectible canary coverage: "
            f"{missing_coverage}."
        )
    for case in dataset.cases:
        if not set(case.expected_namespaces) <= eligible:
            raise ValueError(
                f"Routing quality case {case.id!r} expects a non-eligible namespace."
            )
        collision = all_examples.get(canonical_text(case.question))
        if collision is not None:
            raise ValueError(
                f"Routing quality case {case.id!r} duplicates a stored routing example "
                f"for {collision!r}."
            )
    return routing_catalog_projection_sha256(eligible_cards)


def validate_routing_observations(
    dataset: RoutingQualityDataset,
    observations: Mapping[str, RoutingCaseObservation],
) -> dict[str, RoutingCaseObservation]:
    """Validate a complete content-free observation mapping."""

    expected_ids = set(dataset.cases_by_id)
    actual_ids = set(observations)
    if expected_ids != actual_ids:
        raise ValueError(
            "Routing observations do not match the quality suite "
            f"(missing={sorted(expected_ids - actual_ids)}, "
            f"unknown={sorted(actual_ids - expected_ids)})."
        )
    normalized: dict[str, RoutingCaseObservation] = {}
    for case in dataset.cases:
        observation = observations[case.id]
        if not isinstance(observation, RoutingCaseObservation):
            raise ValueError(
                f"Routing observation {case.id!r} must be RoutingCaseObservation."
            )
        _validate_case_observation(case, observation)
        normalized[case.id] = observation
    return normalized


def validate_route_observations(
    dataset: RoutingQualityDataset,
    observations: Mapping[str, RoutingRouteObservation],
) -> dict[str, RoutingRouteObservation]:
    """Validate complete strategy-neutral route observations."""

    expected_ids = set(dataset.cases_by_id)
    actual_ids = set(observations)
    if expected_ids != actual_ids:
        raise ValueError(
            "Routing baseline observations do not match the quality suite "
            f"(missing={sorted(expected_ids - actual_ids)}, "
            f"unknown={sorted(actual_ids - expected_ids)})."
        )
    normalized: dict[str, RoutingRouteObservation] = {}
    for case in dataset.cases:
        observation = observations[case.id]
        if not isinstance(observation, RoutingRouteObservation):
            raise ValueError(
                f"Routing baseline observation {case.id!r} must be "
                "RoutingRouteObservation."
            )
        if observation.case_id != case.id:
            raise ValueError(
                f"Routing baseline observation key does not match case {case.id!r}."
            )
        shortlist = observation.shortlist_namespaces
        exact_names = observation.exact_name_namespaces
        fallback = observation.fallback_namespaces
        initial = observation.initial_namespaces
        if not 1 <= len(shortlist) <= ROUTING_SHORTLIST_LIMIT:
            raise ValueError(
                "Routing baseline shortlist must contain one through "
                f"{ROUTING_SHORTLIST_LIMIT} namespaces."
            )
        for label, values in (
            ("shortlist", shortlist),
            ("exact names", exact_names),
            ("fallback", fallback),
            ("initial", initial),
        ):
            for namespace in values:
                _safe_id(
                    namespace,
                    where=f"routing baseline {case.id!r} {label} namespace",
                )
            _require_unique(
                values, where=f"routing baseline {case.id!r} {label} namespaces"
            )
        if not set(exact_names) <= set(shortlist):
            raise ValueError("Routing baseline exact names must be in its shortlist.")
        if not 1 <= len(fallback) <= ROUTING_MAX_FANOUT:
            raise ValueError("Routing baseline fallback fanout must be one through three.")
        if not 1 <= len(initial) <= ROUTING_MAX_FANOUT:
            raise ValueError("Routing baseline initial fanout must be one through three.")
        if not set(fallback) <= set(shortlist) or not set(initial) <= set(fallback):
            raise ValueError("Routing baseline routes must come from its shortlist.")
        if initial != fallback[: len(initial)]:
            raise ValueError("Routing baseline initial route must prefix fallback order.")
        if observation.initial_fanout != len(initial):
            raise ValueError("Routing baseline initial_fanout does not match its route.")
        if observation.selection_reason not in SELECTION_REASONS:
            raise ValueError("Routing baseline selection_reason is invalid.")
        if not isinstance(observation.high_confidence, bool):
            raise ValueError("Routing baseline high_confidence must be boolean.")
        if observation.selection_reason in {
            "unique_title_or_alias",
            "high_confidence_semantic",
            "high_confidence_prototype",
        } and observation.initial_fanout != 1:
            raise ValueError("Confident singleton selection must begin with fanout one.")
        if observation.selection_reason in {
            "ambiguous_semantic",
            "ambiguous_prototype",
        } and initial != fallback:
            raise ValueError("Ambiguous selection must begin with its full fallback.")
        normalized[case.id] = observation
    return normalized


def calibrate_routing_thresholds(
    dataset: RoutingQualityDataset,
    observations: Mapping[str, RoutingCaseObservation],
) -> RoutingThresholdCalibration:
    """Select deterministic score/margin floors from calibration cases only."""

    parsed = validate_routing_observations(dataset, observations)
    cases = tuple(
        case
        for case in dataset.cases
        if case.split == "calibration" and case.role != "named_self"
    )
    if not cases:
        raise ValueError("Routing threshold calibration requires calibration cases.")
    if any(len(case.expected_namespaces) != 1 for case in cases):
        raise ValueError(
            "Routing threshold calibration cases must expect exactly one namespace."
        )

    for case in cases:
        if case.role != "contrast_other":
            continue
        observation = parsed[case.id]
        if (
            not set(case.expected_namespaces)
            <= set(observation.fallback_namespaces)
            or case.subject_namespace is None
            or observation.fallback_namespaces[0] == case.subject_namespace
        ):
            raise ValueError(
                f"Routing contrast calibration case {case.id!r} fails its route contract."
            )

    top_scores: list[float] = []
    margins: list[float] = []
    for case in cases:
        observation = parsed[case.id]
        ranked = sorted(observation.corpus_scores, key=lambda item: item.reranker_rank)
        top_scores.append(ranked[0].reranker_score)
        if observation.reranker_margin is not None:
            margins.append(observation.reranker_margin)
    score_candidates = _threshold_breakpoints(top_scores)
    margin_candidates = _threshold_breakpoints(margins or [0.0])

    feasible: list[RoutingThresholdCalibration] = []
    case_id_digest = stable_hash([case.id for case in cases])
    for score_floor in score_candidates:
        for margin_floor in margin_candidates:
            correct = 0
            incorrect = 0
            fanout = 0
            for case in cases:
                observation = parsed[case.id]
                ranked = sorted(
                    observation.corpus_scores,
                    key=lambda item: item.reranker_rank,
                )
                top = ranked[0]
                confident = (
                    top.reranker_score >= score_floor
                    and observation.reranker_margin is not None
                    and observation.reranker_margin >= margin_floor
                )
                if confident:
                    if (top.namespace,) == case.expected_namespaces:
                        correct += 1
                    else:
                        incorrect += 1
                    fanout += 1
                else:
                    fanout += min(ROUTING_MAX_FANOUT, len(ranked))
            if incorrect:
                continue
            feasible.append(
                RoutingThresholdCalibration(
                    score_floor=score_floor,
                    margin_floor=margin_floor,
                    calibration_case_count=len(cases),
                    correct_high_confidence_singletons=correct,
                    incorrect_high_confidence_singletons=incorrect,
                    average_initial_fanout=fanout / len(cases),
                    calibration_case_ids_sha256=case_id_digest,
                )
            )
    if not feasible:  # The disable-singletons sentinel should make this unreachable.
        raise ValueError("Routing threshold calibration found no safe threshold pair.")
    return max(
        feasible,
        key=lambda result: (
            result.correct_high_confidence_singletons,
            -result.average_initial_fanout,
            result.score_floor,
            result.margin_floor,
        ),
    )


def score_routing_quality(
    dataset: RoutingQualityDataset,
    observations: Mapping[str, RoutingCaseObservation],
) -> RoutingQualityMetrics:
    """Score fully diagnosed prototype-routing observations."""

    parsed = validate_routing_observations(dataset, observations)
    routes = {
        case.id: RoutingRouteObservation(
            case_id=case.id,
            shortlist_namespaces=tuple(
                item.namespace
                for item in sorted(
                    parsed[case.id].corpus_scores,
                    key=lambda item: item.shortlist_rank,
                )
            ),
            exact_name_namespaces=tuple(
                item.namespace
                for item in parsed[case.id].corpus_scores
                if item.exact_name_match
            ),
            fallback_namespaces=parsed[case.id].fallback_namespaces,
            initial_namespaces=parsed[case.id].initial_namespaces,
            selection_reason=parsed[case.id].selection_reason,
            high_confidence=parsed[case.id].high_confidence,
            initial_fanout=parsed[case.id].initial_fanout,
        )
        for case in dataset.cases
    }
    return _score_route_selection_quality(dataset, routes)


def score_route_selection_quality(
    dataset: RoutingQualityDataset,
    observations: Mapping[str, RoutingRouteObservation],
) -> RoutingQualityMetrics:
    """Score a strategy-neutral same-catalog route baseline.

    This boundary avoids pretending legacy cosine ranks are MiniLM prototype
    scores. It intentionally accepts no numeric score or passage fields.
    """

    parsed = validate_route_observations(dataset, observations)
    return _score_route_selection_quality(dataset, parsed)


def _score_route_selection_quality(
    dataset: RoutingQualityDataset,
    parsed: Mapping[str, RoutingRouteObservation],
) -> RoutingQualityMetrics:
    shortlist_total = 0
    shortlist_found = 0
    route_total = 0
    route_found = 0
    named_total = 0
    named_passed = 0
    contrast_total = 0
    contrast_passed = 0
    multi_total = 0
    multi_passed = 0
    incorrect_confident = 0
    no_answer_confident = 0
    total_initial_fanout = 0
    maximum_initial_fanout = 0
    maximum_fallback_fanout = 0
    case_metrics: list[RoutingCaseMetrics] = []

    corpus_positive: dict[str, list[int]] = {
        corpus.namespace: [0, 0] for corpus in dataset.corpora
    }
    corpus_shortlist: dict[str, list[int]] = {
        corpus.namespace: [0, 0] for corpus in dataset.corpora
    }

    for case in dataset.cases:
        observation = parsed[case.id]
        expected = set(case.expected_namespaces)
        shortlist = set(observation.shortlist_namespaces)
        fallback = set(observation.fallback_namespaces[:ROUTING_MAX_FANOUT])
        current_shortlist_found = len(expected & shortlist)
        current_route_found = len(expected & fallback)
        certification_case = case.split == "gate"
        if certification_case:
            shortlist_total += len(expected)
            shortlist_found += current_shortlist_found
            for namespace in expected:
                corpus_shortlist[namespace][0] += 1
                corpus_shortlist[namespace][1] += int(namespace in shortlist)
        route_total += len(expected)
        route_found += current_route_found

        positive_single = (
            len(case.expected_namespaces) == 1
            and case.role
            not in {"contrast_other", "legacy_no_answer", "legacy_multi"}
        )
        if positive_single:
            namespace = case.expected_namespaces[0]
            corpus_positive[namespace][0] += 1
            corpus_positive[namespace][1] += int(namespace in fallback)

        named_result: bool | None = None
        if case.role in {"named_self", "legacy_named"}:
            named_total += 1
            expected_first = case.expected_namespaces[0]
            named_result = bool(
                observation.fallback_namespaces[0] == expected_first
                and observation.selection_reason == "unique_title_or_alias"
                and expected_first in observation.exact_name_namespaces
            )
            named_passed += int(named_result)

        contrast_result: bool | None = None
        if case.role == "contrast_other":
            contrast_total += 1
            contrast_result = bool(
                expected <= fallback
                and case.subject_namespace is not None
                and observation.fallback_namespaces[0] != case.subject_namespace
            )
            contrast_passed += int(contrast_result)

        multi_result: bool | None = None
        if len(expected) > 1:
            multi_total += 1
            multi_result = expected <= fallback
            multi_passed += int(multi_result)

        confident_singleton = observation.high_confidence and observation.initial_fanout == 1
        incorrect = bool(
            confident_singleton
            and set(observation.initial_namespaces) != expected
        )
        no_answer = bool(confident_singleton and not expected)
        incorrect_confident += int(incorrect)
        no_answer_confident += int(no_answer)
        total_initial_fanout += observation.initial_fanout
        maximum_initial_fanout = max(
            maximum_initial_fanout, observation.initial_fanout
        )
        maximum_fallback_fanout = max(
            maximum_fallback_fanout, len(observation.fallback_namespaces)
        )
        case_metrics.append(
            RoutingCaseMetrics(
                case_id=case.id,
                subject_namespace=case.subject_namespace,
                expected_namespaces=case.expected_namespaces,
                shortlist_found=current_shortlist_found,
                shortlist_complete=expected <= shortlist,
                route_found=current_route_found,
                route_complete=expected <= fallback,
                named_self_passed=named_result,
                contrast_passed=contrast_result,
                multi_corpus_passed=multi_result,
                incorrect_high_confidence_singleton=incorrect,
                no_answer_high_confidence_singleton=no_answer,
            )
        )

    per_corpus: list[PerCorpusRoutingMetrics] = []
    for corpus in sorted(dataset.corpora, key=lambda item: item.namespace):
        positive_total, positive_found = corpus_positive[corpus.namespace]
        corpus_shortlist_total, corpus_shortlist_found = corpus_shortlist[
            corpus.namespace
        ]
        per_corpus.append(
            PerCorpusRoutingMetrics(
                namespace=corpus.namespace,
                positive_case_total=positive_total,
                positive_cases_found_at_3=positive_found,
                positive_recall_at_3=(
                    positive_found / positive_total if positive_total else None
                ),
                certification_shortlist_required_total=corpus_shortlist_total,
                certification_shortlist_required_found=corpus_shortlist_found,
                certification_shortlist_recall_at_12=(
                    corpus_shortlist_found / corpus_shortlist_total
                    if corpus_shortlist_total
                    else None
                ),
            )
        )
    return RoutingQualityMetrics(
        shortlist_recall_at_12=(
            shortlist_found / shortlist_total if shortlist_total else 0.0
        ),
        shortlist_required_total=shortlist_total,
        shortlist_required_found=shortlist_found,
        route_recall_at_3=route_found / route_total if route_total else 0.0,
        route_required_total=route_total,
        route_required_found=route_found,
        named_self_total=named_total,
        named_self_passed=named_passed,
        contrast_total=contrast_total,
        contrast_passed=contrast_passed,
        multi_corpus_total=multi_total,
        multi_corpus_passed=multi_passed,
        incorrect_high_confidence_singletons=incorrect_confident,
        no_answer_high_confidence_singletons=no_answer_confident,
        average_initial_fanout=total_initial_fanout / len(dataset.cases),
        maximum_initial_fanout=maximum_initial_fanout,
        maximum_fallback_fanout=maximum_fallback_fanout,
        case_metrics=tuple(case_metrics),
        per_corpus=tuple(per_corpus),
    )


def gate_routing_quality(
    dataset: RoutingQualityDataset,
    metrics: RoutingQualityMetrics,
    *,
    calibration: RoutingThresholdCalibration,
    eligible_namespaces: Sequence[str] | None = None,
    baseline: RoutingQualityMetrics | None = None,
) -> RoutingQualityVerdict:
    """Apply exact activation gates to already-scored observations."""

    if any(case.split != "gate" for case in dataset.cases):
        raise ValueError(
            "Routing activation gates require the certification-only dataset."
        )
    expected_case_ids = {case.id for case in dataset.cases}
    if set(metrics.cases_by_id) != expected_case_ids:
        raise ValueError(
            "Routing activation metrics do not match the certification cases."
        )
    if baseline is not None and set(baseline.cases_by_id) != expected_case_ids:
        raise ValueError(
            "Routing baseline metrics do not match the certification cases."
        )
    calibration_cases = tuple(
        case
        for pack in dataset.packs
        for case in pack.cases
        if case.split == "calibration"
    )
    expected_calibration_ids_sha256 = stable_hash(
        [case.id for case in calibration_cases]
    )
    calibration_contract_passed = bool(
        calibration_cases
        and calibration.calibration_case_count == len(calibration_cases)
        and calibration.calibration_case_ids_sha256
        == expected_calibration_ids_sha256
        and calibration.incorrect_high_confidence_singletons == 0
        and math.isfinite(calibration.score_floor)
        and math.isfinite(calibration.margin_floor)
        and math.isfinite(calibration.average_initial_fanout)
    )

    eligible = set(
        eligible_namespaces
        if eligible_namespaces is not None
        else (corpus.namespace for corpus in dataset.corpora)
    )
    covered = set(dataset.approved_covered_namespaces)
    per_corpus_positive_passed = all(
        item.positive_case_total > 0 and item.positive_recall_at_3 == 1.0
        for item in metrics.per_corpus
        if item.namespace in eligible
    )
    per_corpus_shortlist_passed = all(
        item.certification_shortlist_required_total > 0
        and item.certification_shortlist_recall_at_12 == 1.0
        for item in metrics.per_corpus
        if item.namespace in eligible
    )

    regressed_cases: list[str] = []
    regressed_corpora: list[str] = []
    if baseline is not None:
        current_cases = metrics.cases_by_id
        for case_id, baseline_case in baseline.cases_by_id.items():
            current = current_cases.get(case_id)
            if baseline_case.gate_passed and (
                current is None or not current.gate_passed
            ):
                regressed_cases.append(case_id)
        current_corpora = metrics.per_corpus_by_namespace
        for namespace, baseline_corpus in baseline.per_corpus_by_namespace.items():
            current = current_corpora.get(namespace)
            before = baseline_corpus.positive_recall_at_3
            after = current.positive_recall_at_3 if current is not None else None
            if before is not None and (after is None or after < before):
                regressed_corpora.append(namespace)

    checks: dict[str, dict[str, object]] = {
        "calibration_contract": {
            "passed": calibration_contract_passed,
            "observed": {
                "case_count": calibration.calibration_case_count,
                "case_ids_sha256": calibration.calibration_case_ids_sha256,
                "incorrect_high_confidence_singletons": (
                    calibration.incorrect_high_confidence_singletons
                ),
            },
            "required": {
                "case_count": len(calibration_cases),
                "case_ids_sha256": expected_calibration_ids_sha256,
                "incorrect_high_confidence_singletons": 0,
            },
        },
        "approved_corpus_coverage": {
            "passed": eligible <= covered,
            "observed": sorted(eligible & covered),
            "required": sorted(eligible),
        },
        "shortlist_recall_at_12": {
            "passed": metrics.shortlist_recall_at_12 == 1.0,
            "observed": metrics.shortlist_recall_at_12,
            "required": "1.0",
        },
        "per_corpus_shortlist_recall_at_12": {
            "passed": per_corpus_shortlist_passed,
            "observed": {
                item.namespace: item.certification_shortlist_recall_at_12
                for item in metrics.per_corpus
                if item.namespace in eligible
            },
            "required": "every eligible corpus exactly 1.0 with non-empty denominator",
        },
        "per_corpus_positive_recall_at_3": {
            "passed": per_corpus_positive_passed,
            "observed": {
                item.namespace: item.positive_recall_at_3
                for item in metrics.per_corpus
                if item.namespace in eligible
            },
            "required": "every eligible corpus exactly 1.0 with non-empty denominator",
        },
        "aggregate_route_recall_at_3": {
            "passed": metrics.route_recall_at_3 >= ROUTING_RECALL_MINIMUM,
            "observed": metrics.route_recall_at_3,
            "required": f">={ROUTING_RECALL_MINIMUM}",
        },
        "named_self_routes": {
            "passed": metrics.named_self_passed == metrics.named_self_total,
            "observed": metrics.named_self_passed,
            "required": metrics.named_self_total,
        },
        "contrast_routes": {
            "passed": metrics.contrast_passed == metrics.contrast_total,
            "observed": metrics.contrast_passed,
            "required": metrics.contrast_total,
        },
        "complete_multi_corpus_coverage": {
            "passed": metrics.multi_corpus_passed == metrics.multi_corpus_total,
            "observed": metrics.multi_corpus_passed,
            "required": metrics.multi_corpus_total,
        },
        "incorrect_high_confidence_singletons": {
            "passed": metrics.incorrect_high_confidence_singletons == 0,
            "observed": metrics.incorrect_high_confidence_singletons,
            "required": 0,
        },
        "no_answer_high_confidence_singletons": {
            "passed": metrics.no_answer_high_confidence_singletons == 0,
            "observed": metrics.no_answer_high_confidence_singletons,
            "required": 0,
        },
        "average_initial_fanout": {
            "passed": metrics.average_initial_fanout
            <= ROUTING_AVERAGE_INITIAL_FANOUT_MAXIMUM,
            "observed": metrics.average_initial_fanout,
            "required": f"<={ROUTING_AVERAGE_INITIAL_FANOUT_MAXIMUM}",
        },
        "maximum_fanout": {
            "passed": metrics.maximum_initial_fanout <= ROUTING_MAX_FANOUT
            and metrics.maximum_fallback_fanout <= ROUTING_MAX_FANOUT,
            "observed": {
                "initial": metrics.maximum_initial_fanout,
                "fallback": metrics.maximum_fallback_fanout,
            },
            "required": f"<={ROUTING_MAX_FANOUT}",
        },
        "baseline_bound": {
            "passed": baseline is not None,
            "observed": baseline is not None,
            "required": True,
        },
        "no_previously_passing_case_regression": {
            "passed": baseline is not None and not regressed_cases,
            "observed": sorted(regressed_cases),
            "required": [],
        },
        "no_per_corpus_recall_regression": {
            "passed": baseline is not None and not regressed_corpora,
            "observed": sorted(regressed_corpora),
            "required": [],
        },
    }
    failed = tuple(name for name, result in checks.items() if not result["passed"])
    return RoutingQualityVerdict(not failed, failed, checks)


def load_routing_confidence_calibration(
    path: Path | None = None,
) -> RoutingConfidenceCalibration:
    """Load the initial collect-only artifact; arbitrary activation fails closed."""

    selected = path or DEFAULT_ROUTING_CALIBRATION
    raw = selected.read_bytes()
    payload = _required_mapping(
        _load_strict_json(raw, where="routing confidence calibration"),
        where="routing confidence calibration",
    )
    _require_exact_fields(
        payload, _CALIBRATION_FIELDS, where="routing confidence calibration"
    )
    if payload.get("schema_version") != ROUTING_CALIBRATION_SCHEMA_VERSION:
        raise ValueError("Routing confidence calibration schema is incompatible.")
    calibration_id = _required_string(
        payload, "calibration_id", where="routing confidence calibration"
    )
    if calibration_id != ROUTING_CALIBRATION_ID:
        raise ValueError("Routing confidence calibration ID is incompatible.")
    revision = _safe_id(
        payload.get("calibration_revision"),
        where="routing confidence calibration revision",
    )
    if payload.get("mode") != "collect":
        raise ValueError("Only collect-mode routing confidence calibration is authorized.")
    if payload.get("owner_approved") is not False:
        raise ValueError("Collect-mode routing confidence calibration cannot be approved.")
    if payload.get("score_floor") is not None or payload.get("margin_floor") is not None:
        raise ValueError("Collect-mode routing confidence calibration has no thresholds.")

    bindings_payload = _required_mapping(
        payload.get("bindings"), where="routing confidence calibration bindings"
    )
    _require_exact_fields(
        bindings_payload,
        _CALIBRATION_BINDING_FIELDS,
        where="routing confidence calibration bindings",
    )
    expected_constants: dict[str, object] = {
        "routing_model": ROUTING_MODEL,
        "routing_model_revision": ROUTING_MODEL_REVISION,
        "routing_reranker_model": CROSS_ENCODER_MODEL,
        "routing_reranker_revision": CROSS_ENCODER_REVISION,
        "schema_contract": ROUTING_SCHEMA_CONTRACT,
        "projection": ROUTING_PROJECTION_CONTRACT,
        "shortlist_limit": ROUTING_SHORTLIST_LIMIT,
        "max_examples": ROUTING_MAX_EXAMPLES,
        "feature_contract": ROUTING_CONFIDENCE_FEATURE_CONTRACT,
        "score_field": ROUTING_CONFIDENCE_SCORE_FIELD,
        "margin_field": ROUTING_CONFIDENCE_MARGIN_FIELD,
    }
    for field, expected in expected_constants.items():
        if bindings_payload.get(field) != expected:
            raise ValueError(
                f"Routing confidence calibration binding {field!r} is incompatible."
            )
    for field in ("canary_suite_sha256", "catalog_projection_sha256"):
        if bindings_payload.get(field) is not None:
            _sha256(
                bindings_payload.get(field),
                where=f"routing confidence calibration {field}",
            )

    certification = _required_mapping(
        payload.get("certification"), where="routing confidence certification"
    )
    _require_exact_fields(
        certification,
        _COLLECT_CERTIFICATION_FIELDS,
        where="routing confidence certification",
    )
    if certification.get("passed") is not False:
        raise ValueError("Collect-mode routing confidence certification cannot pass.")
    if (
        type(certification.get("case_count")) is not int
        or certification.get("case_count") != 0
    ):
        raise ValueError("Collect-mode routing confidence certification has zero cases.")
    if certification.get("verdict_sha256") is not None:
        raise ValueError("Collect-mode routing confidence certification has no verdict.")

    bindings = RoutingConfidenceBindings(
        routing_model=str(bindings_payload["routing_model"]),
        routing_model_revision=str(bindings_payload["routing_model_revision"]),
        routing_reranker_model=str(bindings_payload["routing_reranker_model"]),
        routing_reranker_revision=str(
            bindings_payload["routing_reranker_revision"]
        ),
        schema_contract=str(bindings_payload["schema_contract"]),
        projection=str(bindings_payload["projection"]),
        shortlist_limit=int(bindings_payload["shortlist_limit"]),
        max_examples=int(bindings_payload["max_examples"]),
        feature_contract=str(bindings_payload["feature_contract"]),
        score_field=str(bindings_payload["score_field"]),
        margin_field=str(bindings_payload["margin_field"]),
        canary_suite_sha256=bindings_payload["canary_suite_sha256"],  # type: ignore[arg-type]
        catalog_projection_sha256=bindings_payload[
            "catalog_projection_sha256"
        ],  # type: ignore[arg-type]
    )
    return RoutingConfidenceCalibration(
        schema_version=ROUTING_CALIBRATION_SCHEMA_VERSION,
        calibration_id=calibration_id,
        calibration_revision=revision,
        mode="collect",
        owner_approved=False,
        score_floor=None,
        margin_floor=None,
        bindings=bindings,
        certification_passed=False,
        certification_case_count=0,
        certification_verdict_sha256=None,
    )


def _parse_canary_case(
    payload: object,
    *,
    corpus_id: str,
    namespace: str,
) -> RoutingQualityCase:
    item = _required_mapping(payload, where=f"routing canary case for {corpus_id!r}")
    _require_exact_fields(
        item, _CASE_FIELDS, where=f"routing canary case for {corpus_id!r}"
    )
    case_id = _safe_id(item.get("id"), where="routing canary case id")
    role = _required_string(item, "role", where=f"routing canary case {case_id!r}")
    split = _required_string(item, "split", where=f"routing canary case {case_id!r}")
    if role not in CANARY_ROLES:
        raise ValueError(f"Routing canary case {case_id!r} has an invalid role.")
    if split not in CANARY_SPLITS:
        raise ValueError(f"Routing canary case {case_id!r} has an invalid split.")
    question = _required_string(
        item, "question", where=f"routing canary case {case_id!r}"
    )
    if not canonical_text(question):
        raise ValueError(f"Routing canary case {case_id!r} question is empty after normalization.")
    expected = _unique_safe_id_sequence(
        item.get("expected_namespaces"),
        where=f"routing canary case {case_id!r} expected_namespaces",
    )
    confusable = _unique_safe_id_sequence(
        item.get("confusable_with"),
        where=f"routing canary case {case_id!r} confusable_with",
    )
    return RoutingQualityCase(
        id=case_id,
        origin=corpus_id,
        subject_namespace=namespace,
        role=role,
        split=split,
        question=question,
        expected_namespaces=expected,
        confusable_with=confusable,
    )


def _validate_five_case_roles(
    cases: Sequence[RoutingQualityCase],
    *,
    corpus_id: str,
    namespace: str,
) -> None:
    expected_roles = {
        ("named_self", "gate"): 1,
        ("capability_self", "calibration"): 1,
        ("capability_self", "gate"): 1,
        ("confusable_self", "gate"): 1,
        ("contrast_other", "calibration"): 1,
    }
    actual = {
        key: sum((case.role, case.split) == key for case in cases)
        for key in expected_roles
    }
    if actual != expected_roles:
        raise ValueError(
            f"Routing canary pack {corpus_id!r} must contain the exact five role/split cases."
        )
    for case in cases:
        if case.role in {"named_self", "capability_self", "confusable_self"}:
            if case.expected_namespaces != (namespace,):
                raise ValueError(
                    f"Routing canary self case {case.id!r} must expect its pack namespace."
                )
        if case.role == "named_self" and case.confusable_with:
            raise ValueError("named_self canary cannot declare confusable corpora.")
        if case.role == "capability_self" and case.confusable_with:
            raise ValueError("capability_self canary cannot declare confusable corpora.")
        if case.role == "confusable_self":
            if not case.confusable_with or corpus_id in case.confusable_with:
                raise ValueError(
                    "confusable_self must name at least one other confusable corpus."
                )
        if case.role == "contrast_other":
            if len(case.expected_namespaces) != 1 or case.expected_namespaces == (
                namespace,
            ):
                raise ValueError(
                    "contrast_other must expect exactly one other namespace."
                )
            if corpus_id not in case.confusable_with:
                raise ValueError(
                    "contrast_other confusable_with must include its corpus under test."
                )


def _validate_case_observation(
    case: RoutingQualityCase,
    observation: RoutingCaseObservation,
) -> None:
    if observation.case_id != case.id:
        raise ValueError(f"Routing observation key does not match case {case.id!r}.")
    scores = observation.corpus_scores
    if not 1 <= len(scores) <= ROUTING_SHORTLIST_LIMIT:
        raise ValueError(
            f"Routing observation {case.id!r} must contain one to {ROUTING_SHORTLIST_LIMIT} corpus scores."
        )
    namespaces = [score.namespace for score in scores]
    _require_unique(namespaces, where=f"routing observation {case.id!r} namespaces")
    for score in scores:
        _safe_id(score.namespace, where=f"routing observation {case.id!r} namespace")
        _positive_int(
            score.shortlist_rank,
            where=f"routing observation {case.id!r} shortlist_rank",
        )
        _positive_int(
            score.reranker_rank,
            where=f"routing observation {case.id!r} reranker_rank",
        )
        _finite(
            score.shortlist_cosine_score,
            where=f"routing observation {case.id!r} shortlist score",
        )
        _finite(
            score.reranker_score,
            where=f"routing observation {case.id!r} reranker score",
        )
        if not isinstance(score.exact_name_match, bool):
            raise ValueError("Routing observation exact_name_match must be boolean.")
        if score.winning_prototype_kind == "card":
            if score.winning_prototype_index is not None:
                raise ValueError("A card prototype has no example index.")
        elif score.winning_prototype_kind == "example":
            index = score.winning_prototype_index
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < ROUTING_MAX_EXAMPLES
            ):
                raise ValueError("A routing example prototype index is invalid.")
        else:
            raise ValueError("Winning routing prototype kind must be card or example.")
        _sha256(
            score.winning_prototype_hash,
            where="routing observation winning_prototype_hash",
        )
    count = len(scores)
    if {score.shortlist_rank for score in scores} != set(range(1, count + 1)):
        raise ValueError("Routing observation shortlist ranks must be contiguous.")
    if {score.reranker_rank for score in scores} != set(range(1, count + 1)):
        raise ValueError("Routing observation reranker ranks must be contiguous.")
    by_reranker = sorted(scores, key=lambda score: score.reranker_rank)
    expected_order = sorted(
        scores,
        key=lambda score: (
            -score.reranker_score,
            score.shortlist_rank,
            score.namespace,
        ),
    )
    if [score.namespace for score in by_reranker] != [
        score.namespace for score in expected_order
    ]:
        raise ValueError("Routing observation reranker order is not deterministic.")
    expected_margin = (
        by_reranker[0].reranker_score - by_reranker[1].reranker_score
        if count > 1
        else None
    )
    if expected_margin is None:
        if observation.reranker_margin is not None:
            raise ValueError("One-card routing observation has no reranker margin.")
    else:
        margin = _finite(
            observation.reranker_margin,
            where=f"routing observation {case.id!r} reranker_margin",
        )
        if margin < 0 or not math.isclose(
            margin, expected_margin, rel_tol=0.0, abs_tol=1e-12
        ):
            raise ValueError("Routing observation reranker margin is inconsistent.")

    fallback = observation.fallback_namespaces
    initial = observation.initial_namespaces
    if not 1 <= len(fallback) <= ROUTING_MAX_FANOUT:
        raise ValueError("Routing observation fallback fanout must be one through three.")
    if not 1 <= len(initial) <= ROUTING_MAX_FANOUT:
        raise ValueError("Routing observation initial fanout must be one through three.")
    _require_unique(fallback, where=f"routing observation {case.id!r} fallback")
    _require_unique(initial, where=f"routing observation {case.id!r} initial")
    if not set(fallback) <= set(namespaces) or not set(initial) <= set(fallback):
        raise ValueError("Routing observation routes must come from scored corpora.")
    if observation.initial_fanout != len(initial):
        raise ValueError("Routing observation initial_fanout does not match its route.")
    if initial != fallback[: len(initial)]:
        raise ValueError("Routing observation initial route must prefix fallback order.")
    if observation.selection_reason not in SELECTION_REASONS:
        raise ValueError("Routing observation selection_reason is invalid.")
    if not isinstance(observation.high_confidence, bool):
        raise ValueError("Routing observation high_confidence must be boolean.")
    if observation.selection_reason in {
        "unique_title_or_alias",
        "high_confidence_semantic",
        "high_confidence_prototype",
    } and observation.initial_fanout != 1:
        raise ValueError("Confident singleton selection must begin with fanout one.")
    if observation.selection_reason in {
        "ambiguous_semantic",
        "ambiguous_prototype",
    } and initial != fallback:
        raise ValueError("Ambiguous semantic selection must begin with its full fallback.")


def _threshold_breakpoints(values: Sequence[float]) -> tuple[float, ...]:
    finite = sorted({_finite(value, where="routing calibration breakpoint") for value in values})
    if not finite:
        raise ValueError("Routing calibration needs at least one finite breakpoint.")
    candidates = set(finite)
    for value in finite:
        next_value = math.nextafter(value, math.inf)
        if not math.isfinite(next_value):
            raise ValueError("Routing calibration could not create a finite sentinel.")
        candidates.add(next_value)
    return tuple(sorted(candidates))


def _load_strict_json(raw: bytes, *, where: str) -> object:
    def object_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{where} contains duplicate fields.")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"{where} contains non-finite number {value!r}.")

    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=object_pairs,
            parse_constant=reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ValueError(f"{where} is not UTF-8 JSON.") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{where} is not valid JSON.") from exc


def _required_mapping(value: object, *, where: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{where} must be an object.")
    return value


def _require_exact_fields(
    value: Mapping[str, object], expected: set[str], *, where: str
) -> None:
    missing = expected - set(value)
    unknown = set(value) - expected
    if missing or unknown:
        raise ValueError(
            f"{where} fields are invalid "
            f"(missing={sorted(missing)}, unknown={sorted(unknown)})."
        )


def _required_string(
    value: Mapping[str, object], field: str, *, where: str
) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"{where} {field} must be a non-empty string.")
    return item.strip()


def _safe_id(value: object, *, where: str) -> str:
    if not isinstance(value, str) or _SAFE_ID_RE.fullmatch(value) is None:
        raise ValueError(f"{where} must match {_SAFE_ID_RE.pattern!r}.")
    return value


def _sha256(value: object, *, where: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{where} must be a lowercase SHA-256 digest.")
    return value


def _positive_int(value: object, *, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{where} must be a positive integer.")
    return value


def _finite(value: object, *, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{where} must be a finite number.")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{where} must be a finite number.")
    return number


def _unique_safe_id_sequence(value: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where} must be a list.")
    items = tuple(_safe_id(item, where=where) for item in value)
    _require_unique(items, where=where)
    return items


def _canonical_string_sequence(value: object, *, where: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ValueError(f"{where} must be a sequence of strings.")
    cleaned: list[str] = []
    keys: set[str] = set()
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{where} entries must be non-empty strings.")
        text = item.strip()
        key = canonical_text(text)
        if not key or key in keys:
            raise ValueError(f"{where} contains duplicate normalized values.")
        keys.add(key)
        cleaned.append(text)
    return tuple(sorted(cleaned))


def _require_unique(values: Sequence[object], *, where: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f"{where} must be unique.")


_MISSING = object()


def _object_field(value: object, field: str, *, default: object = _MISSING) -> object:
    if isinstance(value, Mapping):
        if field in value:
            return value[field]
    elif hasattr(value, field):
        return getattr(value, field)
    if default is not _MISSING:
        return default
    raise ValueError(f"Routing card is missing field {field!r}.")


def _nonempty_object_string(
    value: object,
    field: str,
    *,
    namespace: str,
    default: str | None = None,
) -> str:
    item = (
        _object_field(value, field)
        if default is None
        else _object_field(value, field, default=default)
    )
    if not isinstance(item, str) or not item.strip():
        raise ValueError(f"Routing card {namespace!r} field {field!r} is invalid.")
    return item.strip()
