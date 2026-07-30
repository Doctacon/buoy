"""Deterministic, provider-independent semantic pipeline primitives.

This module contains no provider construction, model downloads, or network calls.
Remote I/O and lifecycle orchestration live in :mod:`semantics_remote`.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import math
import re
import unicodedata
from typing import Callable, Iterable, Mapping, Protocol, Sequence

from buoy_search.semantics_models import (
    LocalInferenceClient,
    canonical_json,
    structured_chat_with_repair,
    validate_json_schema,
)

SEMANTIC_SCHEMA_VERSION = 1
EXTRACTION_PROMPT_VERSION = "semantic-extraction-v1"
MERGE_PROMPT_VERSION = "semantic-merge-v1"
TAXONOMY_PROMPT_VERSION = "semantic-taxonomy-v1"
NORMALIZATION_VERSION = "unicode-case-whitespace-punctuation-v1"
BLOCKING_VERSION = "type-first-token-bounded-v1"
CONCEPT_ID_VERSION = "cluster-hash-v1"
CONFIDENCE_POLICY_VERSION = "semantic-confidence-v1"
TAXONOMY_POLICY_VERSION = "semantic-taxonomy-structure-v1"
SAMPLING_ALGORITHM = "namespace-proportional-stable-sha256-v1"
LEXICAL_FALLBACK = "explicit_lexical_only_v1"

CONTROLLED_TYPES = (
    "process", "capability", "metric", "problem", "technique", "technology",
    "product", "organization", "person", "place", "event", "domain_concept",
)
PREDICATES = ("broader", "related", "close_match")
STATUSES = ("accepted", "provisional", "rejected")
MAX_CANDIDATES_PER_ROW = 12
MAX_LABEL_LENGTH = 160
MAX_DEFINITION_LENGTH = 600
MAX_EXCERPT_LENGTH = 600
MAX_RATIONALE_LENGTH = 280
MAX_PAIR_NEIGHBORS = 8
MAX_ACCEPTED_PARENTS = 3
MAX_TAXONOMY_CANDIDATES_PER_CONCEPT = 10
MAX_TAXONOMY_DEPTH = 12
_GENERIC_NOUNS = frozenset({
    "system", "thing", "information", "data", "object", "item", "stuff"
})


class SemanticPipelineError(ValueError):
    """Safe semantic validation or policy failure."""


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    evidence_row_id: str
    source_namespace: str
    surface_form: str
    canonical_label: str
    normalized_surface: str
    normalized_label: str
    concept_type: str
    definition: str
    excerpt: str
    extraction_confidence: float


@dataclass(frozen=True)
class PairJudgment:
    classification: str
    confidence: float
    rationale: str = ""


@dataclass(frozen=True)
class TaxonomyProposal:
    subject_id: str
    predicate: str
    object_id: str
    basis: str = "semantic_induction"
    representative_mention_ids: tuple[str, ...] = ()
    status_ceiling: str | None = None


@dataclass(frozen=True)
class TaxonomyJudgment:
    supported: bool
    confidence: float
    alternative: str | None = None
    rationale: str = ""


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    status: str
    breakdown: Mapping[str, float]


@dataclass(frozen=True)
class CanonicalConcept:
    concept_id: str
    canonical_label: str
    normalized_label: str
    definition: str
    concept_type: str
    aliases: tuple[str, ...]
    status: str
    policy_score: float
    policy_breakdown: Mapping[str, float]
    mention_count: int
    namespace_count: int
    source_namespaces: tuple[str, ...]
    semantic_hash: str


@dataclass(frozen=True)
class CanonicalMention:
    mention_id: str
    concept_id: str
    candidate_id: str
    evidence_row_id: str
    source_namespace: str
    label: str
    excerpt: str
    extraction_score: float
    status: str
    policy_score: float


@dataclass(frozen=True)
class TaxonomyEdge:
    taxonomy_id: str
    subject_id: str
    predicate: str
    object_id: str
    status: str
    policy_score: float
    policy_breakdown: Mapping[str, float]
    basis: str
    representative_mention_ids: tuple[str, ...]
    rationale: str
    semantic_hash: str


class MergeVerifier(Protocol):
    def classify(self, left: Candidate, right: Candidate, *, lexical_similarity: float) -> PairJudgment: ...


class TaxonomyProposer(Protocol):
    def propose(self, concepts: Sequence[CanonicalConcept]) -> Iterable[TaxonomyProposal]: ...


class TaxonomyVerifier(Protocol):
    def verify(self, proposal: TaxonomyProposal, concepts: Mapping[str, CanonicalConcept]) -> TaxonomyJudgment: ...


class LocalMergeVerifier:
    """Independent local-model alias/sense classifier."""

    def __init__(
        self, client: LocalInferenceClient, *, guard: Callable[[], None] | None = None
    ) -> None:
        self.client = client
        self.guard = guard or (lambda: None)

    def classify(
        self, left: Candidate, right: Candidate, *, lexical_similarity: float
    ) -> PairJudgment:
        self.guard()
        context = {
            "left": _candidate_context(left),
            "right": _candidate_context(right),
            "lexical_similarity": round(lexical_similarity, 6),
        }
        result = structured_chat_with_repair(
            self.client,
            messages=(
                {"role": "system", "content": (
                    "Classify two evidence-backed concept candidates. Return only the strict "
                    "schema. Do not provide chain-of-thought; rationale is one concise sentence."
                )},
                {"role": "user", "content": canonical_json(context)},
            ),
            schema=PAIR_VERIFICATION_SCHEMA,
            max_output_tokens=256,
        ).result.value
        self.guard()
        return PairJudgment(
            str(result["classification"]),
            float(result["confidence"]),
            str(result["rationale"])[:MAX_RATIONALE_LENGTH],
        )


class LocalTaxonomyProposer:
    """Bounded local-model proposer for the controlled taxonomy grammar."""

    def __init__(
        self, client: LocalInferenceClient, *, concepts_per_call: int = 40,
        guard: Callable[[], None] | None = None,
    ) -> None:
        self.client = client
        self.concepts_per_call = concepts_per_call
        self.call_count = 0
        self.guard = guard or (lambda: None)

    def propose(self, concepts: Sequence[CanonicalConcept]) -> Iterable[TaxonomyProposal]:
        output: list[TaxonomyProposal] = []
        ordered = sorted(concepts, key=lambda item: item.concept_id)
        for start in range(0, len(ordered), self.concepts_per_call):
            self.guard()
            block = ordered[start:start + self.concepts_per_call]
            payload = [{
                "id": item.concept_id,
                "label": item.canonical_label[:MAX_LABEL_LENGTH],
                "definition": item.definition[:MAX_DEFINITION_LENGTH],
                "type": item.concept_type,
                "mention_count": item.mention_count,
                "namespace_count": item.namespace_count,
            } for item in block]
            result = structured_chat_with_repair(
                self.client,
                messages=(
                    {"role": "system", "content": (
                        "Propose only broader (child to parent), related, or close_match edges "
                        "supported by these concepts. It is valid to return no proposals. Return "
                        "only strict JSON and no chain-of-thought."
                    )},
                    {"role": "user", "content": canonical_json(payload)},
                ),
                schema=TAXONOMY_PROPOSAL_SCHEMA,
                max_output_tokens=2_048,
            ).result.value
            self.call_count += 1
            self.guard()
            for raw in result["proposals"]:
                output.append(TaxonomyProposal(
                    str(raw["subject_id"]), str(raw["predicate"]),
                    str(raw["object_id"]), str(raw["basis"]),
                    tuple(str(value) for value in raw["representative_mention_ids"]),
                ))
        return output


class LocalTaxonomyVerifier:
    """Independent local-model verifier for each proposed taxonomy edge."""

    def __init__(
        self, client: LocalInferenceClient, *, guard: Callable[[], None] | None = None
    ) -> None:
        self.client = client
        self.guard = guard or (lambda: None)

    def verify(
        self, proposal: TaxonomyProposal,
        concepts: Mapping[str, CanonicalConcept],
    ) -> TaxonomyJudgment:
        self.guard()
        left, right = concepts[proposal.subject_id], concepts[proposal.object_id]
        payload = {
            "subject": _concept_context(left),
            "predicate": proposal.predicate,
            "predicate_semantics": {
                "broader": "subject is narrower than object",
                "related": "symmetric non-hierarchical association",
                "close_match": "distinct concepts that are highly similar",
            }[proposal.predicate],
            "object": _concept_context(right),
            "basis": proposal.basis,
        }
        result = structured_chat_with_repair(
            self.client,
            messages=(
                {"role": "system", "content": (
                    "Independently verify this controlled taxonomy relation. Return only strict "
                    "JSON. Do not provide chain-of-thought; rationale is one concise sentence."
                )},
                {"role": "user", "content": canonical_json(payload)},
            ),
            schema=TAXONOMY_VERIFICATION_SCHEMA,
            max_output_tokens=256,
        ).result.value
        self.guard()
        alternative = str(result["alternative"])
        return TaxonomyJudgment(
            bool(result["supported"]), float(result["confidence"]),
            None if alternative == "none" else alternative,
            str(result["rationale"])[:MAX_RATIONALE_LENGTH],
        )


def _candidate_context(value: Candidate) -> dict[str, object]:
    return {
        "label": value.canonical_label[:MAX_LABEL_LENGTH],
        "surface_form": value.surface_form[:MAX_LABEL_LENGTH],
        "definition": value.definition[:MAX_DEFINITION_LENGTH],
        "type": value.concept_type,
        "representative_excerpt": value.excerpt[:MAX_EXCERPT_LENGTH],
        "source_namespace": value.source_namespace[:128],
    }


def _concept_context(value: CanonicalConcept) -> dict[str, object]:
    return {
        "id": value.concept_id,
        "label": value.canonical_label[:MAX_LABEL_LENGTH],
        "definition": value.definition[:MAX_DEFINITION_LENGTH],
        "type": value.concept_type,
        "aliases": list(value.aliases[:20]),
        "mention_count": value.mention_count,
        "namespace_count": value.namespace_count,
    }


_CANDIDATE_ITEM_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "surface_form": {"type": "string", "minLength": 1, "maxLength": MAX_LABEL_LENGTH},
        "canonical_label": {"type": "string", "minLength": 1, "maxLength": MAX_LABEL_LENGTH},
        "concept_type": {"type": "string", "enum": list(CONTROLLED_TYPES)},
        "definition": {"type": "string", "minLength": 1, "maxLength": MAX_DEFINITION_LENGTH},
        "supporting_excerpt": {"type": "string", "minLength": 1, "maxLength": MAX_EXCERPT_LENGTH},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["surface_form", "canonical_label", "concept_type", "definition", "supporting_excerpt", "confidence"],
    "additionalProperties": False,
}
EXTRACTION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"candidates": {"type": "array", "items": _CANDIDATE_ITEM_SCHEMA, "maxItems": MAX_CANDIDATES_PER_ROW}},
    "required": ["candidates"],
    "additionalProperties": False,
}
TAXONOMY_PROPOSAL_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "maxItems": 256,
            "items": {
                "type": "object",
                "properties": {
                    "subject_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "predicate": {"type": "string", "enum": list(PREDICATES)},
                    "object_id": {"type": "string", "minLength": 1, "maxLength": 80},
                    "basis": {"type": "string", "enum": ["evidence_supported", "semantic_induction"]},
                    "representative_mention_ids": {"type": "array", "items": {"type": "string", "maxLength": 80}, "maxItems": 8},
                },
                "required": ["subject_id", "predicate", "object_id", "basis", "representative_mention_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["proposals"],
    "additionalProperties": False,
}
PAIR_VERIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "classification": {"type": "string", "enum": ["same_concept", "close_match", "related", "distinct"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "maxLength": MAX_RATIONALE_LENGTH},
    },
    "required": ["classification", "confidence", "rationale"],
    "additionalProperties": False,
}
TAXONOMY_VERIFICATION_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "supported": {"type": "boolean"},
        "alternative": {"type": "string", "enum": ["broader", "related", "close_match", "none"]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "rationale": {"type": "string", "maxLength": MAX_RATIONALE_LENGTH},
    },
    "required": ["supported", "alternative", "confidence", "rationale"],
    "additionalProperties": False,
}


def stable_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def normalize_label(value: str) -> str:
    """Normalize without collapsing semantically meaningful interior punctuation."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = " ".join(normalized.split())
    normalized = re.sub(r"^[\s\W_]+|[\s\W_]+$", "", normalized, flags=re.UNICODE)
    return normalized


def lexical_tokens(value: str) -> tuple[str, ...]:
    return tuple(sorted(set(re.findall(r"[^\W_]+", normalize_label(value), re.UNICODE))))


def lexical_similarity(left: str, right: str) -> float:
    a, b = set(lexical_tokens(left)), set(lexical_tokens(right))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def candidate_id(evidence_row_id: str, value: Mapping[str, object]) -> str:
    return "sc_" + stable_hash([evidence_row_id, value])[:61]


def validate_extraction(
    value: object,
    *,
    content: str,
    evidence_row_id: str,
    source_namespace: str,
) -> tuple[Candidate, ...]:
    validate_json_schema(value, EXTRACTION_SCHEMA)
    assert isinstance(value, dict)
    output: list[Candidate] = []
    seen: set[tuple[str, str, str, str]] = set()
    for raw in value["candidates"]:
        assert isinstance(raw, dict)
        surface = str(raw["surface_form"])
        excerpt = str(raw["supporting_excerpt"])
        if surface not in content:
            raise SemanticPipelineError("candidate surface form is not an exact content substring")
        if excerpt not in content or surface not in excerpt:
            raise SemanticPipelineError("candidate excerpt is not exact support for its surface form")
        normalized_surface = normalize_label(surface)
        normalized_canonical = normalize_label(str(raw["canonical_label"]))
        if not normalized_surface or not normalized_canonical:
            raise SemanticPipelineError("candidate normalized labels must not be empty")
        if normalized_surface in _GENERIC_NOUNS and normalized_canonical in _GENERIC_NOUNS:
            # Generic filler has no reusable semantic identity by default.
            continue
        confidence = float(raw["confidence"])
        if not math.isfinite(confidence):
            raise SemanticPipelineError("candidate confidence must be finite")
        duplicate_key = (normalized_surface, normalized_canonical, str(raw["concept_type"]), excerpt)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)
        raw_identity = {
            "surface_form": surface,
            "canonical_label": str(raw["canonical_label"]),
            "concept_type": str(raw["concept_type"]),
            "definition": str(raw["definition"]),
            "supporting_excerpt": excerpt,
            "confidence": confidence,
        }
        output.append(Candidate(
            candidate_id(evidence_row_id, raw_identity), evidence_row_id, source_namespace,
            surface, str(raw["canonical_label"]), normalized_surface, normalized_canonical,
            str(raw["concept_type"]), str(raw["definition"]), excerpt, confidence,
        ))
    return tuple(sorted(output, key=lambda item: item.candidate_id))


def confidence_policy(
    components: Mapping[str, float | None], *, accepted_threshold: float = 0.85,
    provisional_threshold: float = 0.65,
) -> ConfidenceResult:
    if not (0 <= provisional_threshold < accepted_threshold <= 1):
        raise SemanticPipelineError("confidence thresholds must satisfy 0 <= provisional < accepted <= 1")
    weights = {
        "schema_validity": 0.10, "exact_substring": 0.15, "extraction_confidence": 0.15,
        "mention_support": 0.10, "namespace_support": 0.05, "lexical_consistency": 0.10,
        "local_similarity": 0.10, "verifier_judgment": 0.10, "type_consistency": 0.075,
        "structural_validity": 0.075,
    }
    if set(components) - set(weights):
        raise SemanticPipelineError("confidence policy received an unknown component")
    applicable: dict[str, float] = {}
    for name, raw in components.items():
        if raw is None:
            continue
        value = float(raw)
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise SemanticPipelineError("confidence components must be finite values in [0,1]")
        applicable[name] = value
    if not applicable:
        raise SemanticPipelineError("confidence policy requires an applicable component")
    denominator = sum(weights[name] for name in applicable)
    score = round(sum(weights[name] * value for name, value in applicable.items()) / denominator, 6)
    deterministic = {"schema_validity", "structural_validity"}
    if "extraction_confidence" in applicable:
        deterministic.update({"exact_substring", "type_consistency"})
    mandatory_valid = all(applicable.get(name) == 1.0 for name in deterministic)
    independently_verified = applicable.get("verifier_judgment", 0.0) >= provisional_threshold
    if not mandatory_valid:
        score = min(score, max(0.0, provisional_threshold - 0.000001))
    elif not independently_verified:
        score = min(score, max(0.0, accepted_threshold - 0.000001))
    status = "accepted" if score >= accepted_threshold else "provisional" if score >= provisional_threshold else "rejected"
    return ConfidenceResult(score, status, dict(sorted(applicable.items())))


class _UnionFind:
    def __init__(self, values: Iterable[str]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        root = value
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[value] != value:
            value, self.parent[value] = self.parent[value], root
        return root

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a != b:
            self.parent[max(a, b)] = min(a, b)


def _pair_candidates(candidates: Sequence[Candidate]) -> Iterable[tuple[Candidate, Candidate, float]]:
    blocks: dict[tuple[str, str], list[Candidate]] = {}
    for item in candidates:
        ordered_tokens = tuple(re.findall(
            r"[^\W_]+", normalize_label(item.normalized_label), re.UNICODE
        ))
        keys = set(ordered_tokens)
        if len(ordered_tokens) > 1:
            keys.add("".join(token[0] for token in ordered_tokens if token))
        for key in keys:
            blocks.setdefault((item.concept_type, key), []).append(item)
    emitted: set[tuple[str, str]] = set()
    neighbor_counts: dict[str, int] = {}
    for block_key in sorted(blocks):
        ordered = sorted(blocks[block_key], key=lambda item: item.candidate_id)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1:]:
                key = (left.candidate_id, right.candidate_id)
                if key in emitted or neighbor_counts.get(left.candidate_id, 0) >= MAX_PAIR_NEIGHBORS:
                    continue
                similarity = lexical_similarity(left.normalized_label, right.normalized_label)
                # Acronym and shared-token blocks are verifier candidates, not
                # merge evidence; the independent local model decides senses.
                emitted.add(key)
                neighbor_counts[left.candidate_id] = neighbor_counts.get(left.candidate_id, 0) + 1
                yield left, right, similarity


def resolve_concepts(
    candidates: Sequence[Candidate], *, merge_verifier: MergeVerifier | None,
    accepted_threshold: float = 0.85, provisional_threshold: float = 0.65,
    maximum_verifier_calls: int | None = None,
) -> tuple[tuple[CanonicalConcept, ...], tuple[CanonicalMention, ...], tuple[TaxonomyProposal, ...], int]:
    """Resolve aliases/senses with bounded comparisons and deterministic union-find.

    With ``merge_verifier=None`` the explicitly reported lexical-only fallback
    merges only exact normalized canonical labels of the same controlled type.
    """

    ordered = sorted(candidates, key=lambda item: item.candidate_id)
    union = _UnionFind(item.candidate_id for item in ordered)
    if merge_verifier is None:
        by_exact: dict[tuple[str, str, str], str] = {}
        for item in ordered:
            # The explicitly reported lexical-only fallback is conservative.
            # Normal builds always use the independent local verifier below.
            key = (
                item.concept_type, item.normalized_label,
                normalize_label(item.definition),
            )
            prior = by_exact.setdefault(key, item.candidate_id)
            union.union(prior, item.candidate_id)
    induced: list[TaxonomyProposal] = []
    merge_scores: list[tuple[str, str, float]] = []
    verification_calls = 0
    if merge_verifier is not None:
        for left, right, similarity in _pair_candidates(ordered):
            if maximum_verifier_calls is not None and verification_calls >= maximum_verifier_calls:
                raise SemanticPipelineError("merge verifier call budget would be exceeded")
            judgment = merge_verifier.classify(left, right, lexical_similarity=similarity)
            verification_calls += 1
            if judgment.classification not in {"same_concept", "close_match", "related", "distinct"}:
                raise SemanticPipelineError("merge verifier returned an invalid classification")
            if not math.isfinite(judgment.confidence) or not 0 <= judgment.confidence <= 1:
                raise SemanticPipelineError("merge verifier confidence is invalid")
            if len(judgment.rationale) > MAX_RATIONALE_LENGTH:
                raise SemanticPipelineError("merge verifier rationale is too long")
            if judgment.classification == "same_concept":
                if left.concept_type != right.concept_type:
                    continue
                if judgment.confidence >= accepted_threshold:
                    union.union(left.candidate_id, right.candidate_id)
                    merge_scores.append((
                        left.candidate_id, right.candidate_id, judgment.confidence
                    ))
                elif judgment.confidence >= provisional_threshold:
                    # A medium verifier judgment is inspectable but cannot make
                    # the irreversible canonical merge. Preserve both senses and
                    # publish only a provisional close-match disposition.
                    induced.append(TaxonomyProposal(
                        left.candidate_id, "close_match", right.candidate_id,
                        "semantic_induction", (), "provisional",
                    ))
            elif judgment.classification in {"close_match", "related"} and judgment.confidence >= provisional_threshold:
                induced.append(TaxonomyProposal(left.candidate_id, judgment.classification, right.candidate_id, "semantic_induction"))
    groups: dict[str, list[Candidate]] = {}
    for item in ordered:
        groups.setdefault(union.find(item.candidate_id), []).append(item)
    concepts: list[CanonicalConcept] = []
    mentions: list[CanonicalMention] = []
    candidate_to_concept: dict[str, str] = {}
    for group in sorted(groups.values(), key=lambda values: min(item.candidate_id for item in values)):
        types = {item.concept_type for item in group}
        if len(types) != 1:
            raise SemanticPipelineError("one canonical cluster contains incompatible senses")
        labels = sorted({item.canonical_label for item in group}, key=lambda value: (normalize_label(value), value))
        canonical = min(labels, key=lambda value: (-sum(1 for item in group if item.canonical_label == value), normalize_label(value), value))
        aliases = tuple(value for value in sorted({item.surface_form for item in group}, key=lambda value: (normalize_label(value), value)) if normalize_label(value) != normalize_label(canonical))
        cluster_basis = sorted(item.candidate_id for item in group)
        concept_id = "concept_" + stable_hash([CONCEPT_ID_VERSION, cluster_basis])[:56]
        namespaces = tuple(sorted({item.source_namespace for item in group}))
        consistency = sum(lexical_similarity(item.canonical_label, canonical) for item in group) / len(group)
        member_ids = {item.candidate_id for item in group}
        verified_scores = [
            score for left, right, score in merge_scores
            if left in member_ids and right in member_ids
        ]
        policy = confidence_policy({
            "schema_validity": 1.0, "exact_substring": 1.0,
            "extraction_confidence": sum(item.extraction_confidence for item in group) / len(group),
            "mention_support": min(1.0, 0.75 + 0.05 * len(group)),
            "namespace_support": min(1.0, 0.8 + 0.1 * len(namespaces)),
            "lexical_consistency": consistency, "local_similarity": consistency,
            "verifier_judgment": (
                sum(verified_scores) / len(verified_scores)
                if verified_scores else None
            ),
            "type_consistency": 1.0, "structural_validity": 1.0,
        }, accepted_threshold=accepted_threshold, provisional_threshold=provisional_threshold)
        semantic = stable_hash({"label": canonical, "definition": group[0].definition, "type": next(iter(types)), "aliases": aliases, "members": cluster_basis})
        concept = CanonicalConcept(concept_id, canonical, normalize_label(canonical), group[0].definition, next(iter(types)), aliases, policy.status, policy.score, policy.breakdown, len(group), len(namespaces), namespaces, semantic)
        if concept.status == "rejected":
            continue
        concepts.append(concept)
        for item in group:
            candidate_to_concept[item.candidate_id] = concept_id
            mention_id = "mention_" + stable_hash([concept_id, item.candidate_id])[:56]
            mentions.append(CanonicalMention(mention_id, concept_id, item.candidate_id, item.evidence_row_id, item.source_namespace, item.surface_form, item.excerpt, item.extraction_confidence, policy.status, policy.score))
    # An alias cannot collide with another published alias or canonical label.
    # Distinct colliding canonical labels remain distinct senses and receive a
    # close-match conflict proposal instead of a silent merge.
    alias_owners: dict[str, set[str]] = {}
    canonical_owners: dict[str, set[str]] = {}
    for concept in concepts:
        canonical_owners.setdefault(concept.normalized_label, set()).add(concept.concept_id)
        for alias in concept.aliases:
            alias_owners.setdefault(normalize_label(alias), set()).add(concept.concept_id)
    ambiguous_aliases = {
        alias for alias, owners in alias_owners.items()
        if len(owners | canonical_owners.get(alias, set())) > 1
    }
    conflict_pairs: set[tuple[str, str]] = set()
    for normalized, owners in {**canonical_owners, **{
        key: alias_owners.get(key, set()) | canonical_owners.get(key, set())
        for key in ambiguous_aliases
    }}.items():
        ordered_owners = sorted(owners)
        if len(ordered_owners) > 1:
            conflict_pairs.update(
                (left, right)
                for index, left in enumerate(ordered_owners)
                for right in ordered_owners[index + 1:]
            )
    if ambiguous_aliases:
        filtered: list[CanonicalConcept] = []
        for concept in concepts:
            aliases = tuple(
                alias for alias in concept.aliases
                if normalize_label(alias) not in ambiguous_aliases
            )
            filtered.append(replace(
                concept,
                aliases=aliases,
                semantic_hash=stable_hash({
                    "prior_cluster_hash": concept.semantic_hash,
                    "unambiguous_aliases": aliases,
                }),
            ))
        concepts = filtered

    proposals: set[tuple[str, str, str, str]] = set()
    remapped: list[TaxonomyProposal] = []
    for left, right in sorted(conflict_pairs):
        induced.append(TaxonomyProposal(
            left, "close_match", right, "semantic_induction"
        ))
    for proposal in induced:
        concept_ids = {item.concept_id for item in concepts}
        left = candidate_to_concept.get(proposal.subject_id)
        right = candidate_to_concept.get(proposal.object_id)
        if proposal.subject_id in concept_ids:
            left = proposal.subject_id
        if proposal.object_id in concept_ids:
            right = proposal.object_id
        if left is None or right is None or left == right:
            continue
        key = (left, proposal.predicate, right, proposal.basis)
        if proposal.predicate in {"related", "close_match"} and right < left:
            key = (right, proposal.predicate, left, proposal.basis)
        if key not in proposals:
            proposals.add(key)
            remapped.append(TaxonomyProposal(
                *key,
                representative_mention_ids=proposal.representative_mention_ids,
                status_ceiling=proposal.status_ceiling,
            ))
    return tuple(sorted(concepts, key=lambda item: item.concept_id)), tuple(sorted(mentions, key=lambda item: item.mention_id)), tuple(sorted(remapped, key=lambda item: (item.subject_id, item.predicate, item.object_id))), verification_calls


def build_taxonomy(
    concepts: Sequence[CanonicalConcept], proposals: Iterable[TaxonomyProposal], *,
    verifier: TaxonomyVerifier, accepted_threshold: float = 0.85,
    provisional_threshold: float = 0.65, maximum_verifier_calls: int | None = None,
) -> tuple[tuple[TaxonomyEdge, ...], Mapping[str, int], int]:
    by_id = {item.concept_id: item for item in concepts}
    if len(by_id) != len(concepts):
        raise SemanticPipelineError("concept IDs must be unique")
    accepted_graph: dict[str, set[str]] = {key: set() for key in by_id}
    accepted_parents: dict[str, int] = {key: 0 for key in by_id}
    proposed_seen: set[tuple[str, str, str]] = set()
    published_seen: set[tuple[str, str, str]] = set()
    output: list[TaxonomyEdge] = []
    diagnostics = {"prevented_cycles": 0, "prevented_depth": 0, "prevented_parent_limit": 0, "invalid_edges": 0}
    candidate_counts: dict[str, int] = {key: 0 for key in by_id}
    calls = 0

    def depth(node: str, trail: frozenset[str] = frozenset()) -> int:
        if node in trail:
            return MAX_TAXONOMY_DEPTH + 1
        parents = accepted_graph[node]
        return 0 if not parents else 1 + max(depth(parent, trail | {node}) for parent in parents)

    def reaches(start: str, target: str) -> bool:
        pending = [start]
        visited: set[str] = set()
        while pending:
            value = pending.pop()
            if value == target:
                return True
            if value not in visited:
                visited.add(value)
                pending.extend(accepted_graph[value])
        return False

    for proposal in sorted(proposals, key=lambda item: (item.subject_id, item.predicate, item.object_id, item.basis)):
        if (
            proposal.predicate not in PREDICATES
            or proposal.basis not in {"evidence_supported", "semantic_induction"}
            or proposal.status_ceiling not in {None, "provisional"}
            or len(proposal.representative_mention_ids) > 8
        ):
            diagnostics["invalid_edges"] += 1
            continue
        left, right = proposal.subject_id, proposal.object_id
        if left not in by_id or right not in by_id or left == right:
            diagnostics["invalid_edges"] += 1
            continue
        if proposal.predicate in {"related", "close_match"} and right < left:
            left, right = right, left
        if any(
            candidate_counts[value] >= MAX_TAXONOMY_CANDIDATES_PER_CONCEPT
            for value in (left, right)
        ):
            diagnostics["invalid_edges"] += 1
            continue
        candidate_counts[left] += 1
        candidate_counts[right] += 1
        key = (left, proposal.predicate, right)
        if key in proposed_seen:
            diagnostics["invalid_edges"] += 1
            continue
        proposed_seen.add(key)
        if maximum_verifier_calls is not None and calls >= maximum_verifier_calls:
            raise SemanticPipelineError("taxonomy verifier call budget would be exceeded")
        judgment = verifier.verify(TaxonomyProposal(
            left, proposal.predicate, right, proposal.basis,
            proposal.representative_mention_ids, proposal.status_ceiling,
        ), by_id)
        calls += 1
        if not math.isfinite(judgment.confidence) or not 0 <= judgment.confidence <= 1 or len(judgment.rationale) > MAX_RATIONALE_LENGTH:
            raise SemanticPipelineError("taxonomy verifier output is invalid")
        predicate = proposal.predicate
        if not judgment.supported and judgment.alternative in PREDICATES:
            predicate = str(judgment.alternative)
            if predicate in {"related", "close_match"} and right < left:
                left, right = right, left
        elif not judgment.supported:
            continue
        final_key = (left, predicate, right)
        if final_key in published_seen:
            diagnostics["invalid_edges"] += 1
            continue
        # Independent verification is a publication gate, not merely one
        # weighted signal. Low confidence is rejected and medium confidence can
        # never be promoted to accepted by deterministic components.
        if judgment.confidence < provisional_threshold:
            continue
        policy = confidence_policy({"schema_validity": 1.0, "verifier_judgment": judgment.confidence, "structural_validity": 1.0}, accepted_threshold=accepted_threshold, provisional_threshold=provisional_threshold)
        status = policy.status
        if judgment.confidence < accepted_threshold:
            status = "provisional"
        if proposal.status_ceiling == "provisional":
            status = "provisional"
        if by_id[left].status != "accepted" or by_id[right].status != "accepted":
            status = "provisional"
        if predicate == "broader" and status == "accepted":
            if accepted_parents[left] >= MAX_ACCEPTED_PARENTS:
                diagnostics["prevented_parent_limit"] += 1
                status = "provisional"
            elif reaches(right, left):
                diagnostics["prevented_cycles"] += 1
                status = "provisional"
            else:
                accepted_graph[left].add(right)
                accepted_parents[left] += 1
                # Adding a parent can deepen every descendant of `left`, not
                # only `left`; validate the whole accepted hierarchy.
                if max((depth(node) for node in accepted_graph), default=0) > MAX_TAXONOMY_DEPTH:
                    accepted_graph[left].remove(right)
                    accepted_parents[left] -= 1
                    diagnostics["prevented_depth"] += 1
                    status = "provisional"
        identity = [left, predicate, right, proposal.basis]
        semantic = stable_hash(identity)
        output.append(TaxonomyEdge("taxonomy_" + semantic[:55], left, predicate, right, status, policy.score, policy.breakdown, proposal.basis, tuple(proposal.representative_mention_ids), judgment.rationale[:MAX_RATIONALE_LENGTH], semantic))
        # Add only after an edge survives all confidence and structural gates;
        # a rejected alternative must not suppress a later publishable edge.
        published_seen.add(final_key)
    return tuple(output), diagnostics, calls


def allocate_sample(counts: Mapping[str, int], sample_size: int) -> Mapping[str, int]:
    if type(sample_size) is not int or sample_size < 1:
        raise SemanticPipelineError("sample size must be a positive integer")
    positive = {key: value for key, value in sorted(counts.items()) if value > 0}
    total = sum(positive.values())
    if sample_size > total:
        raise SemanticPipelineError("sample size exceeds active evidence rows")
    if sample_size < len(positive):
        selected = sorted(positive, key=lambda key: (stable_hash(key), key))[:sample_size]
        return {key: int(key in selected) for key in positive}
    allocation = {key: 1 for key in positive}
    remaining = sample_size - len(positive)
    capacity_total = sum(value - 1 for value in positive.values())
    if remaining and capacity_total:
        raw = {key: remaining * (value - 1) / capacity_total for key, value in positive.items()}
        for key in positive:
            allocation[key] += min(positive[key] - 1, int(raw[key]))
        left = sample_size - sum(allocation.values())
        for key in sorted(positive, key=lambda name: (-(raw[name] - int(raw[name])), stable_hash(name), name)):
            if left and allocation[key] < positive[key]:
                allocation[key] += 1; left -= 1
    return allocation
