"""Remote lifecycle for autonomous semantic builds.

All model and remote provider objects are injected. Importing this module does
not construct a client, read credentials, download a model, or perform I/O.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import heapq
import json
import math
import os
from pathlib import Path
import resource
import tempfile
import time
from typing import Callable, Iterator, Mapping, Sequence

import portalocker

from buoy_search.evidence_remote import (
    LEDGER_ATTRIBUTES,
    STRONG_CONSISTENCY,
    RemoteClient,
    _capture_billing,
    _metadata,
    _new_metrics,
    _plain,
    _query_rows,
    _read_catalog_row,
    _resource_exists,
    _safe_call,
    _validate_exact_schema,
    verify_evidence_snapshot,
)
from buoy_search.semantics_models import (
    LocalInferenceClient,
    ModelContract,
    StructuredOutputError,
    canonical_json,
)
from buoy_search.semantics_pipeline import (
    BLOCKING_VERSION,
    CONCEPT_ID_VERSION,
    CONFIDENCE_POLICY_VERSION,
    CONTROLLED_TYPES,
    EXTRACTION_PROMPT_VERSION,
    EXTRACTION_SCHEMA,
    MAX_CANDIDATES_PER_ROW,
    LocalMergeVerifier,
    LocalTaxonomyProposer,
    LocalTaxonomyVerifier,
    MERGE_PROMPT_VERSION,
    NORMALIZATION_VERSION,
    SAMPLING_ALGORITHM,
    SEMANTIC_SCHEMA_VERSION,
    TAXONOMY_POLICY_VERSION,
    TAXONOMY_PROMPT_VERSION,
    Candidate,
    MergeVerifier,
    SemanticPipelineError,
    TaxonomyProposer,
    TaxonomyVerifier,
    allocate_sample,
    build_taxonomy,
    resolve_concepts,
    stable_hash,
    validate_extraction,
)

SEMANTICS_CATALOG_NAMESPACE = "buoy-semantics-catalog-v1"
DEFAULT_OUT_ROOT = Path("artifacts/semantic-builds")
MAX_MANIFEST_BYTES = 256 * 1024
REMOTE_PAGE_SIZE = 10_000
WRITE_BATCH_SIZE = 500
EXTRACTION_WRITE_BATCH_SIZE = 100
WRITE_MAX_BYTES = 16 * 1024 * 1024
MAX_MODEL_EVIDENCE_CHARS = 32_000
EVIDENCE_CONTENT_ATTRIBUTES = (
    "content", "title", "section_path", "canonical_url", "chunk_hash",
    "page_hash", "doc_kind", "tags",
)


class SemanticBuildError(ValueError):
    """Sanitized semantic build, resume, budget, or remote-state failure."""

    def __init__(
        self, message: str, *, incomplete_namespaces: Sequence[str] = ()
    ) -> None:
        self.incomplete_namespaces = tuple(sorted(set(incomplete_namespaces)))
        suffix = (
            f"; incomplete_internal_namespaces={canonical_json(self.incomplete_namespaces)}"
            if self.incomplete_namespaces else ""
        )
        super().__init__(message + suffix)


@dataclass(frozen=True)
class BuildLimits:
    maximum_rows: int = 500
    maximum_evidence_bytes: int = 4_000_000
    maximum_model_calls: int = 2_000
    maximum_wall_seconds: int = 21_600
    maximum_candidates: int = 10_000
    maximum_concepts: int = 5_000
    maximum_taxonomy_rows: int = 20_000
    maximum_derived_bytes: int = 268_435_456
    model_concurrency: int = 1

    def validate(self) -> None:
        values = asdict(self)
        if any(type(value) is not int or value < 1 for value in values.values()):
            raise SemanticBuildError("all semantic build limits must be positive integers")
        if self.model_concurrency != 1:
            raise SemanticBuildError("semantic model concurrency must be exactly 1")


@dataclass(frozen=True)
class BuildNames:
    build_id: str
    extraction_namespace: str
    concepts_namespace: str
    mentions_namespace: str
    taxonomy_namespace: str


class _BudgetedInferenceClient:
    """Count every real/reused inference call and fail before the hard cap."""

    def __init__(self, client: LocalInferenceClient, maximum_calls: int) -> None:
        self.client = client
        self.maximum_calls = maximum_calls
        self.calls = 0

    @property
    def remaining(self) -> int:
        return self.maximum_calls - self.calls

    def add_historical(self, count: int) -> None:
        if type(count) is not int or count < 0 or count > self.remaining:
            raise SemanticBuildError("semantic build exceeded model-call budget")
        self.calls += count

    def structured_chat(self, **kwargs: object):  # noqa: ANN201
        if self.remaining <= 0:
            raise SemanticBuildError("semantic build exceeded model-call budget")
        self.calls += 1
        return self.client.structured_chat(**kwargs)


EXTRACTION_SCHEMA_REMOTE = {
    "build_id": {"type": "string", "filterable": True},
    "evidence_snapshot_id": {"type": "string", "filterable": True},
    "evidence_row_id": {"type": "string", "filterable": True},
    "evidence_branch": {"type": "string", "filterable": False},
    "source_namespace": {"type": "string", "filterable": True},
    "source_row_id": {"type": "string", "filterable": False},
    "chunk_hash": {"type": "string", "filterable": False},
    "evidence_input_hash": {"type": "string", "filterable": False},
    "content_hash": {"type": "string", "filterable": False},
    "content_utf8_bytes": {"type": "uint", "filterable": False},
    "model_contract_hash": {"type": "string", "filterable": False},
    "prompt_contract_version": {"type": "string", "filterable": False},
    "normalization_version": {"type": "string", "filterable": False},
    "state": {"type": "string", "filterable": True},
    "candidate_count": {"type": "uint", "filterable": False},
    "candidates_json": {"type": "string", "filterable": False},
    "retry_count": {"type": "uint", "filterable": False},
    "output_hash": {"type": "string", "filterable": False},
}
EXTRACTION_ATTRIBUTES = tuple(EXTRACTION_SCHEMA_REMOTE)

CONCEPT_SCHEMA = {
    "build_id": {"type": "string", "filterable": True},
    "evidence_snapshot_id": {"type": "string", "filterable": True},
    "canonical_label": {"type": "string", "filterable": False},
    "normalized_label": {"type": "string", "filterable": True},
    "definition": {"type": "string", "filterable": False},
    "concept_type": {"type": "string", "filterable": True},
    "aliases": {"type": "[]string", "filterable": False},
    "status": {"type": "string", "filterable": True},
    "policy_version": {"type": "string", "filterable": False},
    "policy_score": {"type": "float", "filterable": False},
    "policy_breakdown_json": {"type": "string", "filterable": False},
    "mention_count": {"type": "uint", "filterable": False},
    "namespace_count": {"type": "uint", "filterable": False},
    "source_namespaces": {"type": "[]string", "filterable": False},
    "created_at": {"type": "string", "filterable": False},
    "semantic_hash": {"type": "string", "filterable": False},
}
MENTION_SCHEMA = {
    "build_id": {"type": "string", "filterable": True},
    "evidence_snapshot_id": {"type": "string", "filterable": True},
    "concept_id": {"type": "string", "filterable": True},
    "status": {"type": "string", "filterable": True},
    "evidence_row_id": {"type": "string", "filterable": True},
    "branch_namespace": {"type": "string", "filterable": False},
    "source_namespace": {"type": "string", "filterable": True},
    "source_row_id": {"type": "string", "filterable": False},
    "chunk_hash": {"type": "string", "filterable": False},
    "page_hash": {"type": "string", "filterable": False},
    "canonical_url": {"type": "string", "filterable": False},
    "title": {"type": "string", "filterable": False},
    "section_path": {"type": "string", "filterable": False},
    "label": {"type": "string", "filterable": False},
    "excerpt": {"type": "string", "filterable": False},
    "extraction_score": {"type": "float", "filterable": False},
    "policy_score": {"type": "float", "filterable": False},
    "model_contract_hash": {"type": "string", "filterable": False},
    "prompt_contract_version": {"type": "string", "filterable": False},
    "semantic_hash": {"type": "string", "filterable": False},
}
TAXONOMY_SCHEMA = {
    "build_id": {"type": "string", "filterable": True},
    "evidence_snapshot_id": {"type": "string", "filterable": True},
    "subject_id": {"type": "string", "filterable": True},
    "predicate": {"type": "string", "filterable": True},
    "object_id": {"type": "string", "filterable": True},
    "status": {"type": "string", "filterable": True},
    "policy_version": {"type": "string", "filterable": False},
    "policy_score": {"type": "float", "filterable": False},
    "policy_breakdown_json": {"type": "string", "filterable": False},
    "basis": {"type": "string", "filterable": True},
    "representative_mention_ids": {"type": "[]string", "filterable": False},
    "rationale": {"type": "string", "filterable": False},
    "created_at": {"type": "string", "filterable": False},
    "semantic_hash": {"type": "string", "filterable": False},
}
CATALOG_SCHEMA = {
    "build_id": {"type": "string", "filterable": True},
    "semantic_schema_version": {"type": "uint", "filterable": True},
    "state": {"type": "string", "filterable": True},
    "created_at": {"type": "string", "filterable": False},
    "evidence_snapshot_id": {"type": "string", "filterable": True},
    "coverage": {"type": "string", "filterable": True},
    "sampling_contract_json": {"type": "string", "filterable": False},
    "model_contract_json": {"type": "string", "filterable": False},
    "embedding_contract_json": {"type": "string", "filterable": False},
    "pipeline_contract_json": {"type": "string", "filterable": False},
    "thresholds_json": {"type": "string", "filterable": False},
    "limits_json": {"type": "string", "filterable": False},
    "extraction_namespace": {"type": "string", "filterable": False},
    "concepts_namespace": {"type": "string", "filterable": False},
    "mentions_namespace": {"type": "string", "filterable": False},
    "taxonomy_namespace": {"type": "string", "filterable": False},
    "selected_row_count": {"type": "uint", "filterable": False},
    "candidate_count": {"type": "uint", "filterable": False},
    "concept_count": {"type": "uint", "filterable": False},
    "accepted_concept_count": {"type": "uint", "filterable": False},
    "provisional_concept_count": {"type": "uint", "filterable": False},
    "mention_count": {"type": "uint", "filterable": False},
    "taxonomy_count": {"type": "uint", "filterable": False},
    "model_call_count": {"type": "uint", "filterable": False},
    "evidence_utf8_bytes": {"type": "uint", "filterable": False},
    "approximate_input_tokens": {"type": "uint", "filterable": False},
    "token_estimate_method": {"type": "string", "filterable": False},
    "derived_bytes": {"type": "uint", "filterable": False},
    "activity_json": {"type": "string", "filterable": False},
    "quality_json": {"type": "string", "filterable": False},
    "semantic_logical_hash": {"type": "string", "filterable": False},
    "manifest_hash": {"type": "string", "filterable": False},
}
CATALOG_ATTRIBUTES = tuple(CATALOG_SCHEMA)


def _identity_payload(*, snapshot_id: str, coverage: str, sample_size: int | None, sample_seed: int, model_contract: ModelContract, embedding_contract: object, accepted_threshold: float, provisional_threshold: float, limits: BuildLimits) -> dict[str, object]:
    return {
        "semantic_schema_version": SEMANTIC_SCHEMA_VERSION,
        "evidence_snapshot_id": snapshot_id,
        "coverage": coverage,
        "sampling": {"algorithm": SAMPLING_ALGORITHM, "sample_size": sample_size, "sample_seed": sample_seed},
        "model_contract": model_contract.to_dict(),
        "embedding_contract": embedding_contract,
        "pipeline": {
            "extraction_prompt": EXTRACTION_PROMPT_VERSION, "merge_prompt": MERGE_PROMPT_VERSION,
            "taxonomy_prompt": TAXONOMY_PROMPT_VERSION, "normalization": NORMALIZATION_VERSION,
            "blocking": BLOCKING_VERSION, "concept_id": CONCEPT_ID_VERSION,
            "confidence": CONFIDENCE_POLICY_VERSION, "taxonomy": TAXONOMY_POLICY_VERSION,
        },
        "thresholds": {"accepted": accepted_threshold, "provisional": provisional_threshold},
        "limits": asdict(limits),
    }


def derive_build_names(identity: Mapping[str, object]) -> BuildNames:
    digest = stable_hash(identity)
    build_id = "semantics_" + digest[:16]
    short = digest[:16]
    return BuildNames(build_id, f"buoy-semantics-extractions-{short}", f"buoy-semantics-concepts-{short}", f"buoy-semantics-mentions-{short}", f"buoy-semantics-taxonomy-{short}")


def _manifest_hash(value: Mapping[str, object]) -> str:
    payload = dict(value); payload.pop("manifest_hash", None)
    return stable_hash(payload)


def _write_manifest(out_root: Path, build_id: str, manifest: Mapping[str, object]) -> tuple[Path, int]:
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise SemanticBuildError(f"local semantic manifest exceeds {MAX_MANIFEST_BYTES} bytes")
    directory = Path(out_root) / build_id
    directory.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".build.", suffix=".tmp", dir=directory)
    target = directory / "build.json"
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        try: os.unlink(temporary)
        except OSError: pass
        raise
    return target, len(encoded)


@contextmanager
def _build_lock(out_root: Path, build_id: str) -> Iterator[None]:
    root = Path(out_root)
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / f".{build_id}.lock"
    try:
        with portalocker.Lock(str(lock_path), mode="a", timeout=0):
            yield
    except portalocker.exceptions.LockException as exc:
        raise SemanticBuildError(f"semantic build {build_id!r} is already running on this host") from exc


def _read_semantic_catalog(client: RemoteClient, build_id: str, metrics: dict[str, int]) -> dict[str, object] | None:
    resource = client.namespace(SEMANTICS_CATALOG_NAMESPACE)
    if not _resource_exists(resource, metrics=metrics):
        return None
    metadata = _metadata(resource, metrics=metrics)
    _validate_exact_schema(metadata, CATALOG_SCHEMA)
    response = _safe_call("semantic catalog query", resource.query, rank_by=("id", "asc"), limit=2, filters=("id", "Eq", build_id), include_attributes=list(CATALOG_ATTRIBUTES), consistency=dict(STRONG_CONSISTENCY))
    metrics["remote_queries"] += 1
    plain = _plain(response)
    rows = list(plain.get("rows", [])) if isinstance(plain, dict) else []
    if len(rows) > 1:
        raise SemanticBuildError("semantic catalog contains duplicate build rows")
    if not rows:
        return None
    row = _plain(rows[0])
    if not isinstance(row, dict) or set(row) != {"id", *CATALOG_ATTRIBUTES} or row.get("state") != "complete":
        raise SemanticBuildError("semantic catalog row is invalid or incomplete")
    return row


def _embedding_contract(evidence_row: Mapping[str, object]) -> object:
    try:
        identity = json.loads(str(evidence_row["source_identity_json"]))
        sources = identity["sources"]
        return [{"namespace": value["namespace"], "embedding_model": value["embedding_model"], "embedding_precision": value["embedding_precision"], "vector_dimensions": value["vector_dimensions"]} for value in sources]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise SemanticBuildError("completed evidence snapshot has an invalid embedding contract") from exc


def _active_ledger_rows(client: RemoteClient, ledger_namespace: str, metrics: dict[str, int]) -> Iterator[dict[str, object]]:
    for row in _query_rows(client.namespace(ledger_namespace), include_attributes=LEDGER_ATTRIBUTES, metrics=metrics, filters=("status", "Eq", "active")):
        if set(row) != {"id", *LEDGER_ATTRIBUTES} or row.get("status") != "active":
            raise SemanticBuildError("active evidence ledger returned an invalid row")
        yield row


def _select_rows(client: RemoteClient, *, snapshot_id: str, ledger_namespace: str, maximum_rows: int, sample_size: int | None, sample_seed: int, metrics: dict[str, int]) -> tuple[list[dict[str, object]], Mapping[str, int], Mapping[str, int]]:
    counts: dict[str, int] = {}
    if sample_size is None:
        selected = []
        for row in _active_ledger_rows(client, ledger_namespace, metrics):
            namespace = str(row["source_namespace"]); counts[namespace] = counts.get(namespace, 0) + 1
            if len(selected) == maximum_rows:
                raise SemanticBuildError(f"full active evidence exceeds maximum rows {maximum_rows}")
            selected.append(row)
        return selected, counts, counts
    for row in _active_ledger_rows(client, ledger_namespace, metrics):
        namespace = str(row["source_namespace"]); counts[namespace] = counts.get(namespace, 0) + 1
    allocation = allocate_sample(counts, sample_size)
    buckets: dict[str, list[tuple[int, str, dict[str, object]]]] = {key: [] for key in allocation}
    for row in _active_ledger_rows(client, ledger_namespace, metrics):
        namespace = str(row["source_namespace"]); quota = allocation.get(namespace, 0)
        if quota == 0: continue
        score = int(hashlib.sha256(
            f"{snapshot_id}:{namespace}:{row['source_row_id']}:{sample_seed}".encode()
        ).hexdigest(), 16)
        heap = buckets[namespace]
        entry = (-score, str(row["id"]), row)
        if len(heap) < quota: heapq.heappush(heap, entry)
        elif entry > heap[0]: heapq.heapreplace(heap, entry)
    selected = [entry[2] for heap in buckets.values() for entry in heap]
    selected.sort(key=lambda row: str(row["id"]))
    if len(selected) != sample_size:
        raise SemanticBuildError("deterministic sampling did not select the requested rows")
    return selected, counts, allocation


def _content_for_row(
    client: RemoteClient,
    ledger: Mapping[str, object],
    metrics: dict[str, int],
) -> dict[str, object]:
    branch = client.namespace(str(ledger["branch_namespace"]))
    response = _safe_call(
        "semantic evidence content query",
        branch.query,
        rank_by=("id", "asc"),
        limit=2,
        filters=("id", "Eq", ledger["source_row_id"]),
        include_attributes=list(EVIDENCE_CONTENT_ATTRIBUTES),
        consistency=dict(STRONG_CONSISTENCY),
    )
    metrics["remote_queries"] += 1
    plain = _plain(response)
    rows = list(plain.get("rows", [])) if isinstance(plain, dict) else []
    if len(rows) != 1:
        raise SemanticBuildError("active evidence content could not be retrieved by exact ID")
    row = _plain(rows[0])
    if (
        not isinstance(row, dict)
        or set(row) != {"id", *EVIDENCE_CONTENT_ATTRIBUTES}
        or row.get("id") != ledger["source_row_id"]
        or row.get("chunk_hash") != ledger["chunk_hash"]
        or row.get("page_hash") != ledger["page_hash"]
        or row.get("canonical_url") != ledger["canonical_url"]
        or not isinstance(row.get("content"), str)
        or any(not isinstance(row.get(field), str) for field in ("title", "section_path", "doc_kind"))
        or not isinstance(row.get("tags"), list)
        or any(not isinstance(value, str) for value in row["tags"])
    ):
        raise SemanticBuildError("active evidence provenance or content is invalid")
    return row


def _bounded_evidence_input(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "title": str(row["title"])[:1_000],
        "section_path": str(row["section_path"])[:1_000],
        "content": str(row["content"])[:MAX_MODEL_EVIDENCE_CHARS],
        "source_kind": str(row["doc_kind"])[:128],
        "tags": [str(value)[:256] for value in list(row["tags"])[:100]],
    }


def _model_extract(
    client: LocalInferenceClient,
    *,
    content: str,
    evidence_context: Mapping[str, object] | None = None,
    evidence_row_id: str,
    source_namespace: str,
    maximum_attempts: int = 3,
    guard: Callable[[], None] | None = None,
) -> tuple[tuple[Candidate, ...], int]:
    context = dict(evidence_context or {"content": content})
    original = (
        {"role": "system", "content": (
            "Extract reusable domain concepts only. Exact excerpts and controlled types are "
            "mandatory. Reject generic filler nouns. Return strict JSON and no chain-of-thought."
        )},
        {"role": "user", "content": canonical_json(context)},
    )
    if type(maximum_attempts) is not int or not 1 <= maximum_attempts <= 3:
        raise SemanticBuildError("semantic extraction has no remaining model-call budget")
    check = guard or (lambda: None)
    invalid_output: str | None = None
    validation_code = ""
    for attempt in range(maximum_attempts):
        check()
        messages: Sequence[Mapping[str, str]] = original
        if attempt:
            prior = invalid_output or "<unavailable>"
            messages = (*original, {
                "role": "user",
                "content": (
                    "Repair the prior structured response below. Return only JSON matching "
                    f"the supplied schema. Validation code: {validation_code[:64]}.\n"
                    f"<invalid-structured-output>{prior}</invalid-structured-output>"
                ),
            })
        try:
            result = client.structured_chat(
                messages=messages, schema=EXTRACTION_SCHEMA,
                max_output_tokens=2_048,
            )
            check()
            values = validate_extraction(
                result.value, content=content,
                evidence_row_id=evidence_row_id,
                source_namespace=source_namespace,
            )
            return values, attempt
        except StructuredOutputError as exc:
            validation_code = exc.code
            invalid_output = exc._invalid_output
        except SemanticPipelineError:
            validation_code = "semantic_exact_support"
            invalid_output = canonical_json(result.value)[:16_384]
    raise SemanticBuildError(
        "semantic extraction remained invalid after bounded repair attempts"
    )


def _candidate_json(candidates: Sequence[Candidate]) -> str:
    return canonical_json([asdict(item) for item in candidates])


def _resume_candidates(
    row: Mapping[str, object], *, build_id: str, snapshot_id: str,
    ledger: Mapping[str, object], evidence: Mapping[str, object], model_hash: str,
) -> tuple[Candidate, ...]:
    bounded_input = _bounded_evidence_input(evidence)
    expected = {
        "build_id": build_id,
        "evidence_snapshot_id": snapshot_id,
        "evidence_row_id": ledger["id"],
        "evidence_branch": ledger["branch_namespace"],
        "source_namespace": ledger["source_namespace"],
        "source_row_id": ledger["source_row_id"],
        "chunk_hash": ledger["chunk_hash"],
        "evidence_input_hash": stable_hash(bounded_input),
        "content_hash": hashlib.sha256(str(evidence["content"]).encode()).hexdigest(),
        "content_utf8_bytes": len(str(evidence["content"]).encode("utf-8")),
        "model_contract_hash": model_hash,
        "prompt_contract_version": EXTRACTION_PROMPT_VERSION,
        "normalization_version": NORMALIZATION_VERSION,
        "state": "valid",
    }
    if any(row.get(key) != value for key, value in expected.items()):
        raise SemanticBuildError("resumable extraction record conflicts with deterministic build inputs")
    encoded = row.get("candidates_json")
    if not isinstance(encoded, str) or stable_hash(encoded) != row.get("output_hash"):
        raise SemanticBuildError("resumable extraction output hash conflicts")
    try: raw = json.loads(encoded)
    except json.JSONDecodeError as exc: raise SemanticBuildError("resumable extraction candidates are invalid") from exc
    if not isinstance(raw, list) or len(raw) != row.get("candidate_count"):
        raise SemanticBuildError("resumable extraction candidate count conflicts")
    try: candidates = tuple(Candidate(**value) for value in raw)
    except (TypeError, ValueError) as exc: raise SemanticBuildError("resumable extraction candidates are invalid") from exc
    if _candidate_json(candidates) != encoded:
        raise SemanticBuildError("resumable extraction candidates are not canonical")
    raw_candidates = [{
        "surface_form": value.surface_form,
        "canonical_label": value.canonical_label,
        "concept_type": value.concept_type,
        "definition": value.definition,
        "supporting_excerpt": value.excerpt,
        "confidence": value.extraction_confidence,
    } for value in candidates]
    try:
        validated = validate_extraction(
            {"candidates": raw_candidates},
            content=str(evidence["content"]),
            evidence_row_id=str(ledger["id"]),
            source_namespace=str(ledger["source_namespace"]),
        )
    except (StructuredOutputError, SemanticPipelineError) as exc:
        raise SemanticBuildError(
            "resumable extraction candidates conflict with exact evidence"
        ) from exc
    if validated != candidates:
        raise SemanticBuildError(
            "resumable extraction candidates conflict with deterministic validation"
        )
    return candidates


def _existing_extractions(
    client: RemoteClient, namespace: str, metrics: dict[str, int], *,
    selected_ids: Sequence[str], maximum_candidates: int, maximum_bytes: int,
) -> dict[str, dict[str, object]] | None:
    """Read only deterministic selected staging rows under hard row/byte caps.

    The ID-only pass detects extras without fetching hostile scalar payloads.
    Each selected full row is then fetched by exact ID with a two-row response
    bound and charged in full canonical bytes before it enters resume state.
    """

    resource = client.namespace(namespace)
    if not _resource_exists(resource, metrics=metrics):
        return None
    _validate_exact_schema(_metadata(resource, metrics=metrics), EXTRACTION_SCHEMA_REMOTE)
    expected = set(selected_ids)
    observed_ids: list[str] = []
    for row in _query_rows(resource, include_attributes=(), metrics=metrics):
        if set(row) != {"id"} or not isinstance(row["id"], str):
            raise SemanticBuildError("extraction staging namespace contains invalid IDs")
        if len(observed_ids) >= len(expected):
            raise SemanticBuildError("extraction staging contains rows outside deterministic selection")
        observed_ids.append(row["id"])
    observed = set(observed_ids)
    if len(observed) != len(observed_ids) or not observed.issubset(expected):
        raise SemanticBuildError("extraction staging contains rows outside deterministic selection")

    rows: dict[str, dict[str, object]] = {}
    candidate_count = 0
    byte_count = 0
    for row_id in sorted(observed):
        response = _safe_call(
            "exact extraction staging query",
            resource.query,
            rank_by=("id", "asc"),
            limit=2,
            filters=("id", "Eq", row_id),
            include_attributes=list(EXTRACTION_ATTRIBUTES),
            consistency=dict(STRONG_CONSISTENCY),
        )
        metrics["remote_queries"] += 1
        _capture_billing(response, metrics)
        plain = _plain(response)
        values = list(plain.get("rows", [])) if isinstance(plain, dict) else []
        if len(values) != 1:
            raise SemanticBuildError("extraction staging exact-ID response is invalid")
        row = _plain(values[0])
        if (
            not isinstance(row, dict)
            or set(row) != {"id", *EXTRACTION_ATTRIBUTES}
            or row.get("id") != row_id
        ):
            raise SemanticBuildError("extraction staging namespace contains invalid rows")
        count = row.get("candidate_count")
        encoded = row.get("candidates_json")
        if type(count) is not int or count < 0 or not isinstance(encoded, str):
            raise SemanticBuildError("extraction staging accounting is invalid")
        row_bytes = len(canonical_json(row).encode("utf-8"))
        candidate_count += count
        byte_count += row_bytes
        if (
            row_bytes > maximum_bytes
            or candidate_count > maximum_candidates
            or byte_count > maximum_bytes
        ):
            raise SemanticBuildError("extraction staging exceeds candidate or byte bound")
        rows[row_id] = row
    return rows


def _write_batches(client: RemoteClient, namespace: str, schema: Mapping[str, Mapping[str, object]], rows: Sequence[dict[str, object]], metrics: dict[str, int], *, conditional: bool = False) -> tuple[int, int]:
    resource = client.namespace(namespace); calls = 0; byte_count = 0
    if not rows:
        response = _safe_call("semantic empty namespace write", resource.write, schema=schema)
        calls += 1
        plain = _plain(response)
        if not isinstance(plain, dict) or plain.get("rows_affected") != 0: raise SemanticBuildError("semantic empty namespace write count mismatch")
    for start in range(0, len(rows), WRITE_BATCH_SIZE):
        batch = list(rows[start:start + WRITE_BATCH_SIZE]); kwargs: dict[str, object] = {"upsert_rows": batch}
        if start == 0: kwargs["schema"] = schema
        if conditional:
            kwargs.update(
                upsert_condition=("id", "Eq", None), return_affected_ids=True
            )
        size = len(canonical_json(kwargs).encode()); byte_count += size
        if size > WRITE_MAX_BYTES: raise SemanticBuildError("semantic remote write payload exceeds bounded size")
        response = _safe_call("semantic namespace write", resource.write, **kwargs); calls += 1
        plain = _plain(response); affected = plain.get("rows_affected") if isinstance(plain, dict) else None
        if affected != len(batch): raise SemanticBuildError("semantic remote write count mismatch")
        if conditional and plain.get("upserted_ids") != [row["id"] for row in batch]:
            raise SemanticBuildError("semantic conditional write did not prove row ownership")
    _validate_exact_schema(_metadata(resource, metrics=metrics), schema)
    return calls, byte_count


def _persisted_row_hash(row: Mapping[str, object]) -> str:
    payload = dict(row)
    payload.pop("semantic_hash", None)
    return stable_hash(payload)


def _stamp_persisted_row_hash(row: dict[str, object]) -> dict[str, object]:
    row["semantic_hash"] = _persisted_row_hash(row)
    return row


def _semantic_logical_hash(
    concepts: Sequence[Mapping[str, object]],
    mentions: Sequence[Mapping[str, object]],
    taxonomy: Sequence[Mapping[str, object]],
) -> str:
    return stable_hash({
        "concepts": [
            _persisted_row_hash(row)
            for row in sorted(concepts, key=lambda value: str(value["id"]))
        ],
        "mentions": [
            _persisted_row_hash(row)
            for row in sorted(mentions, key=lambda value: str(value["id"]))
        ],
        "taxonomy": [
            _persisted_row_hash(row)
            for row in sorted(taxonomy, key=lambda value: str(value["id"]))
        ],
    })


def _read_final_namespace(
    client: RemoteClient, namespace: str,
    schema: Mapping[str, Mapping[str, object]], metrics: dict[str, int],
    *, maximum_rows: int,
) -> list[dict[str, object]]:
    resource = client.namespace(namespace)
    if not _resource_exists(resource, metrics=metrics):
        raise SemanticBuildError("final semantic namespace is missing")
    _validate_exact_schema(_metadata(resource, metrics=metrics), schema)
    output: list[dict[str, object]] = []
    for row in _query_rows(resource, include_attributes=tuple(schema), metrics=metrics):
        if set(row) != {"id", *schema} or len(output) >= maximum_rows:
            raise SemanticBuildError("final semantic namespace row or count is invalid")
        if row.get("semantic_hash") != _persisted_row_hash(row):
            raise SemanticBuildError("final semantic row hash conflicts with persisted contents")
        output.append(row)
    return output


def _verify_completed_catalog(
    client: RemoteClient, row: Mapping[str, object], metrics: dict[str, int],
    limits: BuildLimits,
) -> None:
    concepts = _read_final_namespace(
        client, str(row["concepts_namespace"]), CONCEPT_SCHEMA, metrics,
        maximum_rows=limits.maximum_concepts,
    )
    mentions = _read_final_namespace(
        client, str(row["mentions_namespace"]), MENTION_SCHEMA, metrics,
        maximum_rows=limits.maximum_candidates,
    )
    taxonomy = _read_final_namespace(
        client, str(row["taxonomy_namespace"]), TAXONOMY_SCHEMA, metrics,
        maximum_rows=limits.maximum_taxonomy_rows,
    )
    if (
        len(concepts) != row.get("concept_count")
        or len(mentions) != row.get("mention_count")
        or len(taxonomy) != row.get("taxonomy_count")
    ):
        raise SemanticBuildError("completed semantic namespace counts conflict")
    logical = _semantic_logical_hash(concepts, mentions, taxonomy)
    if logical != row.get("semantic_logical_hash"):
        raise SemanticBuildError("completed semantic logical hash conflicts")


def _verify_final_namespace(
    client: RemoteClient, namespace: str,
    schema: Mapping[str, Mapping[str, object]],
    rows: Sequence[Mapping[str, object]], metrics: dict[str, int],
) -> None:
    resource = client.namespace(namespace)
    _validate_exact_schema(_metadata(resource, metrics=metrics), schema)
    expected: dict[str, str] = {}
    for row in rows:
        if row.get("semantic_hash") != _persisted_row_hash(row):
            raise SemanticBuildError("intended semantic row hash is invalid")
        expected[str(row["id"])] = stable_hash(row)
    observed: dict[str, str] = {}
    for row in _query_rows(
        resource, include_attributes=tuple(schema), metrics=metrics
    ):
        if set(row) != {"id", *schema}:
            raise SemanticBuildError("final semantic namespace row has invalid fields")
        row_id = str(row["id"])
        if row_id in observed:
            raise SemanticBuildError("final semantic namespace has duplicate rows")
        if row.get("semantic_hash") != _persisted_row_hash(row):
            raise SemanticBuildError("final semantic row hash conflicts with persisted contents")
        observed[row_id] = stable_hash(row)
    if observed != expected:
        raise SemanticBuildError("final semantic namespace hash or count mismatch")


def _check_deadline(started: float, maximum_seconds: int, phase: str) -> None:
    if time.monotonic() - started >= maximum_seconds:
        raise SemanticBuildError(f"semantic build exceeded wall-time budget during {phase}")


def _probe_model_contract(
    model_client: LocalInferenceClient, expected: ModelContract
) -> ModelContract:
    doctor = getattr(model_client, "doctor", None)
    if not callable(doctor):
        raise SemanticBuildError(
            "local model client cannot re-probe its pinned contract before publication"
        )
    payload = doctor()
    value = payload.get("model_contract") if isinstance(payload, Mapping) else None
    if not isinstance(value, Mapping):
        raise SemanticBuildError("local model contract re-probe returned an invalid contract")
    try:
        observed = ModelContract(**dict(value))
    except TypeError as exc:
        raise SemanticBuildError("local model contract re-probe returned an invalid contract") from exc
    if observed != expected or observed.contract_hash != expected.contract_hash:
        raise SemanticBuildError("local model contract drifted during semantic inference")
    return observed


@contextmanager
def _report_incomplete_on_error(
    client: RemoteClient, names: BuildNames, metrics: dict[str, int]
) -> Iterator[None]:
    try:
        yield
    except Exception as exc:
        detected: list[str] = []
        for namespace in (
            names.extraction_namespace,
            names.concepts_namespace,
            names.mentions_namespace,
            names.taxonomy_namespace,
        ):
            try:
                if _resource_exists(client.namespace(namespace), metrics=metrics):
                    detected.append(namespace)
            except Exception:
                continue
        if isinstance(exc, SemanticBuildError):
            detected.extend(exc.incomplete_namespaces)
        raise SemanticBuildError(
            str(exc).split("; incomplete_internal_namespaces=", 1)[0],
            incomplete_namespaces=detected,
        ) from exc


def _catalog_manifest(row: Mapping[str, object]) -> dict[str, object]:
    manifest = {key: row[key] for key in (
        "build_id", "semantic_schema_version", "created_at", "evidence_snapshot_id", "coverage",
        "sampling_contract_json", "model_contract_json", "embedding_contract_json",
        "pipeline_contract_json", "thresholds_json", "limits_json",
        "extraction_namespace", "concepts_namespace", "mentions_namespace", "taxonomy_namespace",
        "selected_row_count", "candidate_count", "concept_count", "accepted_concept_count",
        "provisional_concept_count", "mention_count", "taxonomy_count", "model_call_count",
        "evidence_utf8_bytes", "approximate_input_tokens", "token_estimate_method",
        "derived_bytes", "activity_json", "quality_json", "semantic_logical_hash",
    )}
    manifest["semantics_catalog_namespace"] = SEMANTICS_CATALOG_NAMESPACE
    manifest["manifest_hash"] = _manifest_hash(manifest)
    return manifest


def create_semantic_build(
    client: RemoteClient, *, evidence_snapshot_id: str, model_client: LocalInferenceClient,
    model_contract: ModelContract, out_root: Path = DEFAULT_OUT_ROOT,
    merge_verifier: MergeVerifier | None = None, taxonomy_proposer: TaxonomyProposer | None = None,
    taxonomy_verifier: TaxonomyVerifier | None = None, sample_size: int | None = None,
    sample_seed: int = 0, accepted_threshold: float = 0.85,
    provisional_threshold: float = 0.65, limits: BuildLimits = BuildLimits(), resume: bool = False,
    initial_model_calls: int = 0,
) -> dict[str, object]:
    limits.validate()
    if sample_size is not None and (type(sample_size) is not int or sample_size < 1 or sample_size > limits.maximum_rows):
        raise SemanticBuildError("sample size must be within the configured row budget")
    if not (0 <= provisional_threshold < accepted_threshold <= 1):
        raise SemanticBuildError("confidence thresholds must satisfy 0 <= provisional < accepted <= 1")
    metrics = _new_metrics()
    try:
        verification = verify_evidence_snapshot(client, snapshot_id=evidence_snapshot_id, _metrics=metrics)
        evidence = _read_catalog_row(client, snapshot_id=evidence_snapshot_id, metrics=metrics)
    except Exception as exc:
        raise SemanticBuildError(f"completed evidence snapshot validation failed: {exc}") from exc
    if evidence is None or evidence.get("state") != "complete": raise SemanticBuildError("completed evidence snapshot was not found")
    embedding = _embedding_contract(evidence)
    coverage = "sampled" if sample_size is not None else "full"
    identity = _identity_payload(snapshot_id=evidence_snapshot_id, coverage=coverage, sample_size=sample_size, sample_seed=sample_seed, model_contract=model_contract, embedding_contract=embedding, accepted_threshold=accepted_threshold, provisional_threshold=provisional_threshold, limits=limits)
    names = derive_build_names(identity)
    started = time.monotonic()
    # Local inference stages are mandatory. Callers may inject deterministic
    # fakes, but omission never skips merge/taxonomy inference.
    model_guard = lambda: _check_deadline(
        started, limits.maximum_wall_seconds, "local inference"
    )
    budgeted_model = _BudgetedInferenceClient(
        model_client, limits.maximum_model_calls
    )
    budgeted_model.add_historical(initial_model_calls)
    effective_merge = merge_verifier or LocalMergeVerifier(
        budgeted_model, guard=model_guard
    )
    effective_proposer = taxonomy_proposer or LocalTaxonomyProposer(
        budgeted_model, guard=model_guard
    )
    effective_taxonomy = taxonomy_verifier or LocalTaxonomyVerifier(
        budgeted_model, guard=model_guard
    )
    with _report_incomplete_on_error(client, names, metrics), _build_lock(out_root, names.build_id):
        completed = _read_semantic_catalog(client, names.build_id, metrics)
        if completed is not None:
            completed_limits, _completed_model, completed_identity = _completed_contract(
                completed
            )
            if completed_identity != identity:
                raise SemanticBuildError(
                    "completed semantic catalog conflicts with the requested build identity"
                )
            _verify_completed_catalog(
                client, completed, metrics, completed_limits
            )
            manifest = _catalog_manifest(completed)
            if manifest["manifest_hash"] != completed.get("manifest_hash"): raise SemanticBuildError("completed semantic manifest hash conflicts")
            path, local_bytes = _write_manifest(out_root, names.build_id, manifest)
            return {
                "build_id": names.build_id,
                "reused_build": True,
                "local_manifest_path": str(path),
                "local_bytes_written": local_bytes,
                "model_calls": initial_model_calls,
                "incomplete_internal_namespaces": [],
                "local_model_calls_occurred": initial_model_calls > 0,
                "turbopuffer_internal_writes_occurred": False,
                "source_namespace_writes_occurred": False,
                "evidence_branch_writes_occurred": False,
                "local_full_corpus_written": False,
                "local_manifest_written": True,
                "hosted_model_calls_occurred": False,
                "hosted_model_cost": 0,
                **metrics,
            }
        selected, active_counts, sampled_counts = _select_rows(client, snapshot_id=evidence_snapshot_id, ledger_namespace=str(evidence["ledger_namespace"]), maximum_rows=limits.maximum_rows, sample_size=sample_size, sample_seed=sample_seed, metrics=metrics)
        selected_ids = tuple(str(row["id"]) for row in selected)
        existing = _existing_extractions(
            client, names.extraction_namespace, metrics,
            selected_ids=selected_ids,
            maximum_candidates=limits.maximum_candidates,
            maximum_bytes=limits.maximum_derived_bytes,
        )
        if existing is not None and not resume:
            raise SemanticBuildError("matching incomplete extraction staging exists; --resume is required")
        selected_id_set = set(selected_ids)
        if existing is not None and set(existing) - selected_id_set:
            raise SemanticBuildError("extraction staging contains rows outside deterministic selection")
        all_candidates: list[Candidate] = []; staging_pending: list[dict[str, object]] = []; staging_all: list[dict[str, object]] = []
        evidence_metadata: dict[str, tuple[str, str]] = {}
        evidence_bytes = 0; model_calls = 0; retries = 0; new_staging_count = 0; stage_calls = 0; stage_write_bytes = 0
        for ledger in selected:
            _check_deadline(started, limits.maximum_wall_seconds, "evidence retrieval")
            evidence_row = _content_for_row(client, ledger, metrics)
            content = str(evidence_row["content"])
            evidence_metadata[str(ledger["id"])] = (
                str(evidence_row["title"])[:1_000],
                str(evidence_row["section_path"])[:1_000],
            )
            row_bytes = len(content.encode("utf-8"))
            # Fail before transmitting the first over-budget row to the model.
            if evidence_bytes + row_bytes > limits.maximum_evidence_bytes:
                raise SemanticBuildError("semantic build exceeded evidence byte budget")
            evidence_bytes += row_bytes
            staged = None if existing is None else existing.get(str(ledger["id"]))
            if staged is not None:
                candidates = _resume_candidates(
                    staged, build_id=names.build_id,
                    snapshot_id=evidence_snapshot_id, ledger=ledger,
                    evidence=evidence_row, model_hash=model_contract.contract_hash,
                )
                retry_count = staged.get("retry_count")
                if type(retry_count) is not int or retry_count < 0 or retry_count > 2:
                    raise SemanticBuildError("resumable extraction accounting is invalid")
                budgeted_model.add_historical(retry_count + 1)
                model_calls = budgeted_model.calls
                retries += retry_count
                staging_all.append(dict(staged))
            else:
                remaining_calls = budgeted_model.remaining
                candidates, retry_count = _model_extract(
                    budgeted_model, content=content,
                    evidence_context=_bounded_evidence_input(evidence_row),
                    evidence_row_id=str(ledger["id"]),
                    source_namespace=str(ledger["source_namespace"]),
                    maximum_attempts=min(3, remaining_calls),
                    guard=model_guard,
                )
                model_calls = budgeted_model.calls
                retries += retry_count
                _check_deadline(started, limits.maximum_wall_seconds, "extraction")
                encoded = _candidate_json(candidates)
                staged_row = {
                    "id": ledger["id"], "build_id": names.build_id,
                    "evidence_snapshot_id": evidence_snapshot_id,
                    "evidence_row_id": ledger["id"],
                    "evidence_branch": ledger["branch_namespace"],
                    "source_namespace": ledger["source_namespace"],
                    "source_row_id": ledger["source_row_id"],
                    "chunk_hash": ledger["chunk_hash"],
                    "evidence_input_hash": stable_hash(_bounded_evidence_input(evidence_row)),
                    "content_hash": hashlib.sha256(content.encode()).hexdigest(),
                    "content_utf8_bytes": row_bytes,
                    "model_contract_hash": model_contract.contract_hash,
                    "prompt_contract_version": EXTRACTION_PROMPT_VERSION,
                    "normalization_version": NORMALIZATION_VERSION,
                    "state": "valid", "candidate_count": len(candidates),
                    "candidates_json": encoded, "retry_count": retry_count,
                    "output_hash": stable_hash(encoded),
                }
                staging_pending.append(staged_row); staging_all.append(staged_row); new_staging_count += 1
            if model_calls > limits.maximum_model_calls: raise SemanticBuildError("semantic build exceeded model-call budget")
            all_candidates.extend(candidates)
            if len(all_candidates) > limits.maximum_candidates: raise SemanticBuildError("semantic build exceeded candidate budget")
            if len(staging_pending) == EXTRACTION_WRITE_BATCH_SIZE:
                _check_deadline(started, limits.maximum_wall_seconds, "extraction publication")
                calls, written = _write_batches(client, names.extraction_namespace, EXTRACTION_SCHEMA_REMOTE, staging_pending, metrics, conditional=True)
                stage_calls += calls; stage_write_bytes += written; staging_pending = []
        if existing is not None and len(existing) + new_staging_count != len(selected): raise SemanticBuildError("selected evidence rows are not fully accounted for")
        if staging_pending or (existing is None and not selected):
            _check_deadline(started, limits.maximum_wall_seconds, "extraction publication")
            calls, written = _write_batches(client, names.extraction_namespace, EXTRACTION_SCHEMA_REMOTE, staging_pending, metrics, conditional=True)
            stage_calls += calls; stage_write_bytes += written
        try:
            concepts, mentions, induced, merge_calls = resolve_concepts(
                all_candidates,
                merge_verifier=effective_merge,
                accepted_threshold=accepted_threshold,
                provisional_threshold=provisional_threshold,
                maximum_verifier_calls=limits.maximum_model_calls - model_calls,
            )
        except SemanticPipelineError as exc:
            raise SemanticBuildError(str(exc)) from exc
        if merge_verifier is not None:
            budgeted_model.add_historical(merge_calls)
        model_calls = budgeted_model.calls
        _check_deadline(started, limits.maximum_wall_seconds, "merge verification")
        if len(concepts) > limits.maximum_concepts or model_calls > limits.maximum_model_calls: raise SemanticBuildError("semantic build exceeded concept or model-call budget")
        proposed = list(induced)
        if concepts and model_calls >= limits.maximum_model_calls:
            raise SemanticBuildError("taxonomy proposal model-call budget would be exceeded")
        expected_proposal_calls = (
            math.ceil(len(concepts) / effective_proposer.concepts_per_call)
            if isinstance(effective_proposer, LocalTaxonomyProposer) else (1 if concepts else 0)
        )
        if expected_proposal_calls > budgeted_model.remaining:
            raise SemanticBuildError("taxonomy proposal model-call budget would be exceeded")
        proposer_start_calls = getattr(effective_proposer, "call_count", 0)
        proposed.extend(effective_proposer.propose(concepts))
        proposal_calls = getattr(effective_proposer, "call_count", proposer_start_calls + (1 if concepts else 0)) - proposer_start_calls
        if taxonomy_proposer is not None:
            budgeted_model.add_historical(proposal_calls)
        model_calls = budgeted_model.calls
        _check_deadline(started, limits.maximum_wall_seconds, "taxonomy proposal")
        if len(proposed) > limits.maximum_taxonomy_rows: raise SemanticBuildError("semantic build exceeded taxonomy candidate budget")
        try:
            taxonomy, structural, taxonomy_calls = build_taxonomy(
                concepts,
                proposed,
                verifier=effective_taxonomy,
                accepted_threshold=accepted_threshold,
                provisional_threshold=provisional_threshold,
                maximum_verifier_calls=limits.maximum_model_calls - model_calls,
            )
        except SemanticPipelineError as exc:
            raise SemanticBuildError(str(exc)) from exc
        if taxonomy_verifier is not None:
            budgeted_model.add_historical(taxonomy_calls)
        model_calls = budgeted_model.calls
        _check_deadline(started, limits.maximum_wall_seconds, "taxonomy verification")
        if model_calls > limits.maximum_model_calls or len(taxonomy) > limits.maximum_taxonomy_rows: raise SemanticBuildError("semantic build exceeded final model-call or taxonomy budget")
        ledger_by_id = {str(row["id"]): row for row in selected}
        created_at = datetime.now(timezone.utc).isoformat()
        concept_rows: list[dict[str, object]] = []
        for value in concepts:
            concept_rows.append(_stamp_persisted_row_hash({
                "id": value.concept_id, "build_id": names.build_id,
                "evidence_snapshot_id": evidence_snapshot_id,
                "canonical_label": value.canonical_label,
                "normalized_label": value.normalized_label,
                "definition": value.definition,
                "concept_type": value.concept_type,
                "aliases": list(value.aliases), "status": value.status,
                "policy_version": CONFIDENCE_POLICY_VERSION,
                "policy_score": value.policy_score,
                "policy_breakdown_json": canonical_json(value.policy_breakdown),
                "mention_count": value.mention_count,
                "namespace_count": value.namespace_count,
                "source_namespaces": list(value.source_namespaces),
                "created_at": created_at,
            }))
        mention_rows: list[dict[str, object]] = []
        for value in mentions:
            ledger = ledger_by_id[value.evidence_row_id]
            title, section_path = evidence_metadata[value.evidence_row_id]
            mention_rows.append(_stamp_persisted_row_hash({
                "id": value.mention_id, "build_id": names.build_id,
                "evidence_snapshot_id": evidence_snapshot_id,
                "concept_id": value.concept_id, "status": value.status,
                "evidence_row_id": value.evidence_row_id,
                "branch_namespace": ledger["branch_namespace"],
                "source_namespace": ledger["source_namespace"],
                "source_row_id": ledger["source_row_id"],
                "chunk_hash": ledger["chunk_hash"],
                "page_hash": ledger["page_hash"],
                "canonical_url": ledger["canonical_url"],
                "title": title, "section_path": section_path,
                "label": value.label, "excerpt": value.excerpt,
                "extraction_score": value.extraction_score,
                "policy_score": value.policy_score,
                "model_contract_hash": model_contract.contract_hash,
                "prompt_contract_version": EXTRACTION_PROMPT_VERSION,
            }))
        mention_concepts = {
            value.mention_id: value.concept_id for value in mentions
        }
        for value in taxonomy:
            endpoints = {value.subject_id, value.object_id}
            for mention_id in value.representative_mention_ids:
                concept_id = mention_concepts.get(mention_id)
                if concept_id is None:
                    raise SemanticBuildError(
                        "taxonomy representative mention does not exist in the current build"
                    )
                if concept_id not in endpoints:
                    raise SemanticBuildError(
                        "taxonomy representative mention is unrelated to both endpoints"
                    )
        taxonomy_rows: list[dict[str, object]] = []
        for value in taxonomy:
            taxonomy_rows.append(_stamp_persisted_row_hash({
                "id": value.taxonomy_id, "build_id": names.build_id,
                "evidence_snapshot_id": evidence_snapshot_id,
                "subject_id": value.subject_id,
                "predicate": value.predicate,
                "object_id": value.object_id, "status": value.status,
                "policy_version": TAXONOMY_POLICY_VERSION,
                "policy_score": value.policy_score,
                "policy_breakdown_json": canonical_json(value.policy_breakdown),
                "basis": value.basis,
                "representative_mention_ids": list(value.representative_mention_ids),
                "rationale": value.rationale, "created_at": created_at,
            }))
        for namespace in (names.concepts_namespace, names.mentions_namespace, names.taxonomy_namespace):
            if _resource_exists(client.namespace(namespace), metrics=metrics): raise SemanticBuildError("deterministic final semantic namespace already exists without a completed catalog row")
        derived_bytes = sum(
            len(canonical_json(row).encode("utf-8"))
            for rows in (staging_all, concept_rows, mention_rows, taxonomy_rows)
            for row in rows
        )
        if derived_bytes > limits.maximum_derived_bytes: raise SemanticBuildError("semantic build exceeded derived-byte budget")
        _check_deadline(started, limits.maximum_wall_seconds, "final publication")
        concept_calls, concept_write_bytes = _write_batches(
            client, names.concepts_namespace, CONCEPT_SCHEMA, concept_rows, metrics,
            conditional=True,
        )
        _check_deadline(started, limits.maximum_wall_seconds, "concept publication")
        mention_calls, mention_write_bytes = _write_batches(
            client, names.mentions_namespace, MENTION_SCHEMA, mention_rows, metrics,
            conditional=True,
        )
        _check_deadline(started, limits.maximum_wall_seconds, "mention publication")
        taxonomy_write_calls, taxonomy_write_bytes = _write_batches(
            client, names.taxonomy_namespace, TAXONOMY_SCHEMA, taxonomy_rows, metrics,
            conditional=True,
        )
        _check_deadline(started, limits.maximum_wall_seconds, "taxonomy publication")
        semantic_hash = _semantic_logical_hash(
            concept_rows, mention_rows, taxonomy_rows
        )
        sampling_contract = {"coverage": coverage, "algorithm": SAMPLING_ALGORITHM, "sample_size": sample_size, "sample_seed": sample_seed, "active_counts": active_counts, "selected_counts": sampled_counts}
        published_candidate_ids = {mention.candidate_id for mention in mentions}
        connected = {
            endpoint for edge in taxonomy
            for endpoint in (edge.subject_id, edge.object_id)
        }
        broader_subjects = {
            edge.subject_id for edge in taxonomy if edge.predicate == "broader"
        }
        quality = {
            "lexical_mode": "local_verifier_with_lexical_blocking",
            "extraction_retries": retries, "extraction_failures": 0,
            "selected_evidence_rows": len(selected),
            "processed_evidence_rows": len(selected),
            "raw_candidates": len(all_candidates),
            "rejected_candidates": len(all_candidates) - len(mentions),
            "accepted_concepts": sum(value.status == "accepted" for value in concepts),
            "provisional_concepts": sum(value.status == "provisional" for value in concepts),
            "aliases_merged": sum(len(value.aliases) for value in concepts),
            "close_match_pairs": sum(value.predicate == "close_match" for value in taxonomy),
            "accepted_mentions": sum(value.status == "accepted" for value in mentions),
            "provisional_mentions": sum(value.status == "provisional" for value in mentions),
            "accepted_broader_relations": sum(value.status == "accepted" and value.predicate == "broader" for value in taxonomy),
            "provisional_broader_relations": sum(value.status == "provisional" and value.predicate == "broader" for value in taxonomy),
            "accepted_related_relations": sum(value.status == "accepted" and value.predicate == "related" for value in taxonomy),
            "provisional_related_relations": sum(value.status == "provisional" and value.predicate == "related" for value in taxonomy),
            "orphan_concepts": sum(value.concept_id not in connected for value in concepts),
            "top_level_concepts": sum(value.concept_id not in broader_subjects for value in concepts),
            "evidence_coverage": (len(selected) / sum(active_counts.values())) if active_counts else 0.0,
            "concepts_per_1000_evidence_rows": (len(concepts) * 1000 / len(selected)) if selected else 0.0,
            "quality_sample": {
                "accepted_concept_ids": [value.concept_id for value in concepts if value.status == "accepted"][:25],
                "provisional_concept_ids": [value.concept_id for value in concepts if value.status == "provisional"][:10],
                "alias_concept_ids": [value.concept_id for value in concepts if value.aliases][:10],
                "rejected_candidate_ids": [value.candidate_id for value in all_candidates if value.candidate_id not in published_candidate_ids][:10],
                "taxonomy_ids": [value.taxonomy_id for value in taxonomy][:10],
            },
            **structural,
        }
        approximate_tokens = math.ceil(evidence_bytes / 3)
        token_method = "conservative_utf8_bytes_divided_by_3"
        activity = {
            "local_model_calls_occurred": True,
            "turbopuffer_api_calls_occurred": True,
            "turbopuffer_internal_writes_occurred": True,
            "source_namespace_writes_occurred": False,
            "evidence_branch_writes_occurred": False,
            "hosted_model_calls_occurred": False,
            "hosted_model_cost": 0,
            "local_full_corpus_written": False,
            "local_manifest_written": True,
        }
        # Reserve and count the final synthetic-only model pin probe before any
        # completion publication. It transmits no evidence.
        budgeted_model.add_historical(1)
        _probe_model_contract(model_client, model_contract)
        model_calls = budgeted_model.calls
        quality.update({
            "model_calls": model_calls,
            "evidence_utf8_bytes": evidence_bytes,
            "approximate_input_tokens": approximate_tokens,
            "elapsed_inference_seconds": round(time.monotonic() - started, 6),
            "peak_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        })
        catalog_row = {
            "id": names.build_id, "build_id": names.build_id,
            "semantic_schema_version": SEMANTIC_SCHEMA_VERSION, "state": "complete",
            "created_at": created_at, "evidence_snapshot_id": evidence_snapshot_id,
            "coverage": coverage,
            "sampling_contract_json": canonical_json(sampling_contract),
            "model_contract_json": canonical_json(model_contract.to_dict()),
            "embedding_contract_json": canonical_json(embedding),
            "pipeline_contract_json": canonical_json(identity["pipeline"]),
            "thresholds_json": canonical_json(identity["thresholds"]),
            "limits_json": canonical_json(asdict(limits)),
            "extraction_namespace": names.extraction_namespace,
            "concepts_namespace": names.concepts_namespace,
            "mentions_namespace": names.mentions_namespace,
            "taxonomy_namespace": names.taxonomy_namespace,
            "selected_row_count": len(selected), "candidate_count": len(all_candidates),
            "concept_count": len(concepts),
            "accepted_concept_count": quality["accepted_concepts"],
            "provisional_concept_count": quality["provisional_concepts"],
            "mention_count": len(mentions), "taxonomy_count": len(taxonomy),
            "model_call_count": model_calls, "evidence_utf8_bytes": evidence_bytes,
            "approximate_input_tokens": approximate_tokens,
            "token_estimate_method": token_method,
            "derived_bytes": derived_bytes, "activity_json": canonical_json(activity),
            "quality_json": canonical_json(quality),
            "semantic_logical_hash": semantic_hash, "manifest_hash": "pending",
        }
        manifest_preview = _catalog_manifest(catalog_row)
        catalog_row["manifest_hash"] = manifest_preview["manifest_hash"]
        catalog_resource = client.namespace(SEMANTICS_CATALOG_NAMESPACE)
        # Revalidate immutable evidence first, then make the exact final
        # namespace scans immediately adjacent to catalog completion. Only the
        # hard deadline check may occur between the last scan and conditional
        # catalog write.
        _check_deadline(started, limits.maximum_wall_seconds, "catalog finalization")
        try:
            verify_evidence_snapshot(
                client, snapshot_id=evidence_snapshot_id, _metrics=metrics
            )
        except Exception as exc:
            raise SemanticBuildError(
                f"evidence snapshot changed during semantic build: {exc}"
            ) from exc
        _verify_final_namespace(
            client, names.concepts_namespace, CONCEPT_SCHEMA, concept_rows, metrics
        )
        _verify_final_namespace(
            client, names.mentions_namespace, MENTION_SCHEMA, mention_rows, metrics
        )
        _verify_final_namespace(
            client, names.taxonomy_namespace, TAXONOMY_SCHEMA, taxonomy_rows, metrics
        )
        _check_deadline(started, limits.maximum_wall_seconds, "catalog finalization")
        catalog_write_payload = {
            "schema": CATALOG_SCHEMA, "upsert_rows": [catalog_row],
            "upsert_condition": ("id", "Eq", None), "return_affected_ids": True,
        }
        catalog_write_bytes = len(canonical_json(catalog_write_payload).encode("utf-8"))
        response = _safe_call("semantic catalog finalization", catalog_resource.write, **catalog_write_payload)
        plain = _plain(response)
        if not isinstance(plain, dict) or plain.get("rows_affected") != 1 or plain.get("upserted_ids") != [names.build_id]: raise SemanticBuildError("semantic catalog-last finalization conflicted")
        metrics["catalog_write_calls"] += 1
        metrics["catalog_rows_written"] += 1
        _validate_exact_schema(_metadata(catalog_resource, metrics=metrics), CATALOG_SCHEMA)
        path, local_bytes = _write_manifest(out_root, names.build_id, manifest_preview)
        elapsed = time.monotonic() - started
        semantic_write_calls = stage_calls + concept_calls + mention_calls + taxonomy_write_calls + 1
        semantic_rows_written = new_staging_count + len(concept_rows) + len(mention_rows) + len(taxonomy_rows) + 1
        semantic_write_bytes = (
            stage_write_bytes + concept_write_bytes + mention_write_bytes
            + taxonomy_write_bytes + catalog_write_bytes
        )
        return {
            "build_id": names.build_id, "reused_build": False,
            "local_manifest_path": str(path), "local_bytes_written": local_bytes,
            "selected_rows": len(selected), "candidates": len(all_candidates),
            "concepts": len(concepts), "mentions": len(mentions),
            "taxonomy_rows": len(taxonomy), "model_calls": model_calls,
            "repair_count": retries, "evidence_utf8_bytes": evidence_bytes,
            "approximate_input_tokens": approximate_tokens,
            "token_estimate_method": token_method,
            "derived_bytes": derived_bytes, "remote_write_calls": semantic_write_calls,
            "remote_semantic_rows_written": semantic_rows_written,
            "approximate_remote_semantic_write_bytes": semantic_write_bytes,
            "approximate_remote_bytes_definition": "canonical JSON request bytes including schemas and catalog completion",
            "incomplete_internal_namespaces": [],
            "maximum_model_concurrency": 1, "elapsed_seconds": round(elapsed, 6),
            "observed_max_rss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "semantic_logical_hash": semantic_hash, "quality": quality,
            **activity, **metrics,
        }


def _json_catalog_field(row: Mapping[str, object], field: str) -> object:
    value = row.get(field)
    if not isinstance(value, str):
        raise SemanticBuildError(f"semantic catalog field {field} is invalid")
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise SemanticBuildError(f"semantic catalog field {field} is invalid") from exc


def _completed_contract(row: Mapping[str, object]) -> tuple[BuildLimits, ModelContract, dict[str, object]]:
    if row.get("semantic_schema_version") != SEMANTIC_SCHEMA_VERSION:
        raise SemanticBuildError("semantic catalog schema version conflicts")
    limits_raw = _json_catalog_field(row, "limits_json")
    model_raw = _json_catalog_field(row, "model_contract_json")
    thresholds = _json_catalog_field(row, "thresholds_json")
    sampling = _json_catalog_field(row, "sampling_contract_json")
    embedding = _json_catalog_field(row, "embedding_contract_json")
    pipeline = _json_catalog_field(row, "pipeline_contract_json")
    activity = _json_catalog_field(row, "activity_json")
    quality = _json_catalog_field(row, "quality_json")
    if not all(isinstance(value, dict) for value in (limits_raw, model_raw, thresholds, sampling, pipeline, activity, quality)):
        raise SemanticBuildError("semantic catalog contract fields are invalid")
    try:
        limits = BuildLimits(**limits_raw)
        model = ModelContract(**model_raw)
    except TypeError as exc:
        raise SemanticBuildError("semantic catalog model or limits contract is invalid") from exc
    limits.validate()
    accepted = thresholds.get("accepted")
    provisional = thresholds.get("provisional")
    if not isinstance(accepted, (int, float)) or not isinstance(provisional, (int, float)):
        raise SemanticBuildError("semantic catalog thresholds are invalid")
    identity = _identity_payload(
        snapshot_id=str(row.get("evidence_snapshot_id")),
        coverage=str(row.get("coverage")),
        sample_size=sampling.get("sample_size"),
        sample_seed=sampling.get("sample_seed", 0),
        model_contract=model,
        embedding_contract=embedding,
        accepted_threshold=float(accepted),
        provisional_threshold=float(provisional),
        limits=limits,
    )
    if pipeline != identity["pipeline"]:
        raise SemanticBuildError("semantic catalog pipeline contract conflicts")
    if sampling.get("coverage") != row.get("coverage") or sampling.get("algorithm") != SAMPLING_ALGORITHM:
        raise SemanticBuildError("semantic catalog coverage contract conflicts")
    if row.get("token_estimate_method") != "conservative_utf8_bytes_divided_by_3":
        raise SemanticBuildError("semantic catalog token estimate contract conflicts")
    evidence_bytes = row.get("evidence_utf8_bytes")
    if type(evidence_bytes) is not int or row.get("approximate_input_tokens") != math.ceil(evidence_bytes / 3):
        raise SemanticBuildError("semantic catalog approximate token count conflicts")
    required_activity = {
        "local_model_calls_occurred": True,
        "turbopuffer_api_calls_occurred": True,
        "turbopuffer_internal_writes_occurred": True,
        "source_namespace_writes_occurred": False,
        "evidence_branch_writes_occurred": False,
        "hosted_model_calls_occurred": False,
        "hosted_model_cost": 0,
        "local_full_corpus_written": False,
        "local_manifest_written": True,
    }
    if activity != required_activity:
        raise SemanticBuildError("semantic catalog activity contract conflicts")
    names = derive_build_names(identity)
    if (
        row.get("id") != names.build_id
        or row.get("build_id") != names.build_id
        or row.get("extraction_namespace") != names.extraction_namespace
        or row.get("concepts_namespace") != names.concepts_namespace
        or row.get("mentions_namespace") != names.mentions_namespace
        or row.get("taxonomy_namespace") != names.taxonomy_namespace
    ):
        raise SemanticBuildError("semantic catalog build identity conflicts")
    return limits, model, identity


def verify_semantic_build(
    client: RemoteClient, *, build_id: str, manifest_path: Path | None = None
) -> dict[str, object]:
    """Read-only full remote verification; never constructs or calls a model."""

    if not isinstance(build_id, str) or not build_id.startswith("semantics_"):
        raise SemanticBuildError("semantic build ID is invalid")
    metrics = _new_metrics()
    row = _read_semantic_catalog(client, build_id, metrics)
    if row is None:
        raise SemanticBuildError(f"completed semantic build {build_id!r} was not found")
    limits, model, _identity = _completed_contract(row)
    try:
        verify_evidence_snapshot(
            client, snapshot_id=str(row["evidence_snapshot_id"]), _metrics=metrics
        )
    except Exception as exc:
        raise SemanticBuildError(f"semantic evidence snapshot verification failed: {exc}") from exc
    concepts = _read_final_namespace(
        client, str(row["concepts_namespace"]), CONCEPT_SCHEMA, metrics,
        maximum_rows=limits.maximum_concepts,
    )
    mentions = _read_final_namespace(
        client, str(row["mentions_namespace"]), MENTION_SCHEMA, metrics,
        maximum_rows=limits.maximum_candidates,
    )
    taxonomy = _read_final_namespace(
        client, str(row["taxonomy_namespace"]), TAXONOMY_SCHEMA, metrics,
        maximum_rows=limits.maximum_taxonomy_rows,
    )
    expected_counts = (
        row.get("concept_count"), row.get("mention_count"), row.get("taxonomy_count")
    )
    if expected_counts != (len(concepts), len(mentions), len(taxonomy)):
        raise SemanticBuildError("semantic catalog counts conflict with final namespaces")
    if sum(value.get("status") == "accepted" for value in concepts) != row.get("accepted_concept_count"):
        raise SemanticBuildError("accepted concept count conflicts")
    if sum(value.get("status") == "provisional" for value in concepts) != row.get("provisional_concept_count"):
        raise SemanticBuildError("provisional concept count conflicts")
    logical = _semantic_logical_hash(concepts, mentions, taxonomy)
    if logical != row.get("semantic_logical_hash"):
        raise SemanticBuildError("semantic logical hash conflicts")

    concept_by_id = {str(value["id"]): value for value in concepts}
    if len(concept_by_id) != len(concepts):
        raise SemanticBuildError("semantic concepts contain duplicate IDs")
    mention_by_id = {str(value["id"]): value for value in mentions}
    active: dict[str, dict[str, object]] = {}
    evidence_catalog = _read_catalog_row(
        client, snapshot_id=str(row["evidence_snapshot_id"]), metrics=metrics
    )
    if evidence_catalog is None:
        raise SemanticBuildError("semantic evidence catalog row is missing")
    for ledger in _active_ledger_rows(
        client, str(evidence_catalog["ledger_namespace"]), metrics
    ):
        active[str(ledger["id"])] = ledger
    mention_counts = {key: 0 for key in concept_by_id}
    for mention in mentions:
        if (
            mention.get("build_id") != build_id
            or mention.get("evidence_snapshot_id") != row.get("evidence_snapshot_id")
        ):
            raise SemanticBuildError("semantic mention build identity conflicts")
        concept = concept_by_id.get(str(mention.get("concept_id")))
        ledger = active.get(str(mention.get("evidence_row_id")))
        if concept is None or ledger is None:
            raise SemanticBuildError("semantic mention references a missing concept or active evidence row")
        if mention.get("status") != concept.get("status"):
            raise SemanticBuildError("semantic mention status conflicts with its concept")
        if any(mention.get(field) != ledger.get(source) for field, source in (
            ("branch_namespace", "branch_namespace"),
            ("source_namespace", "source_namespace"),
            ("source_row_id", "source_row_id"),
            ("chunk_hash", "chunk_hash"),
            ("page_hash", "page_hash"),
            ("canonical_url", "canonical_url"),
        )):
            raise SemanticBuildError("semantic mention evidence provenance conflicts")
        if (
            mention.get("model_contract_hash") != model.contract_hash
            or mention.get("prompt_contract_version") != EXTRACTION_PROMPT_VERSION
        ):
            raise SemanticBuildError("semantic mention model or prompt contract conflicts")
        mention_counts[str(concept["id"])] += 1
    mention_namespaces: dict[str, set[str]] = {key: set() for key in concept_by_id}
    for mention in mentions:
        mention_namespaces[str(mention["concept_id"])].add(str(mention["source_namespace"]))
    for concept_id, concept in concept_by_id.items():
        if (
            concept.get("build_id") != build_id
            or concept.get("evidence_snapshot_id") != row.get("evidence_snapshot_id")
        ):
            raise SemanticBuildError("semantic concept build identity conflicts")
        if concept.get("status") not in {"accepted", "provisional"}:
            raise SemanticBuildError("published concept has invalid status")
        if concept.get("concept_type") not in CONTROLLED_TYPES:
            raise SemanticBuildError("published concept has invalid type")
        if concept.get("policy_version") != CONFIDENCE_POLICY_VERSION:
            raise SemanticBuildError("published concept policy contract conflicts")
        if mention_counts[concept_id] != concept.get("mention_count") or mention_counts[concept_id] < 1:
            raise SemanticBuildError("concept mention count conflicts")
        expected_namespaces = sorted(mention_namespaces[concept_id])
        if concept.get("namespace_count") != len(expected_namespaces) or concept.get("source_namespaces") != expected_namespaces:
            raise SemanticBuildError("concept namespace support conflicts")

    accepted_graph: dict[str, set[str]] = {key: set() for key in concept_by_id}
    seen_edges: set[tuple[str, str, str]] = set()
    for edge in taxonomy:
        if (
            edge.get("build_id") != build_id
            or edge.get("evidence_snapshot_id") != row.get("evidence_snapshot_id")
        ):
            raise SemanticBuildError("semantic taxonomy build identity conflicts")
        if edge.get("basis") not in {"evidence_supported", "semantic_induction"}:
            raise SemanticBuildError("taxonomy basis is invalid")
        subject = str(edge.get("subject_id")); object_id = str(edge.get("object_id")); predicate = str(edge.get("predicate"))
        if subject == object_id or subject not in concept_by_id or object_id not in concept_by_id:
            raise SemanticBuildError("taxonomy endpoint is invalid")
        if predicate not in {"broader", "related", "close_match"}:
            raise SemanticBuildError("taxonomy predicate is invalid")
        key = (subject, predicate, object_id)
        if predicate in {"related", "close_match"} and object_id < subject:
            raise SemanticBuildError("symmetric taxonomy pair is not canonical")
        if key in seen_edges:
            raise SemanticBuildError("taxonomy contains a duplicate relation")
        seen_edges.add(key)
        if edge.get("policy_version") != TAXONOMY_POLICY_VERSION:
            raise SemanticBuildError("taxonomy policy contract conflicts")
        status = edge.get("status")
        if status == "accepted":
            if concept_by_id[subject].get("status") != "accepted" or concept_by_id[object_id].get("status") != "accepted":
                raise SemanticBuildError("accepted taxonomy references a non-accepted concept")
            if predicate == "broader":
                accepted_graph[subject].add(object_id)
                if len(accepted_graph[subject]) > 3:
                    raise SemanticBuildError("accepted broader taxonomy exceeds maximum parents")
        elif status != "provisional":
            raise SemanticBuildError("published taxonomy has invalid status")
        representative = edge.get("representative_mention_ids")
        if not isinstance(representative, list):
            raise SemanticBuildError("taxonomy representative mention is invalid")
        for mention_id in representative:
            mention = mention_by_id.get(str(mention_id))
            if mention is None:
                raise SemanticBuildError("taxonomy representative mention is invalid")
            if mention.get("concept_id") not in {subject, object_id}:
                raise SemanticBuildError(
                    "taxonomy representative mention is unrelated to both endpoints"
                )
    def visit(node: str, visiting: set[str], visited: set[str]) -> None:
        if node in visiting:
            raise SemanticBuildError("accepted broader taxonomy contains a cycle")
        if node in visited:
            return
        visiting.add(node)
        for parent in accepted_graph[node]:
            visit(parent, visiting, visited)
        visiting.remove(node); visited.add(node)
    visited: set[str] = set()
    for concept_id in accepted_graph:
        visit(concept_id, set(), visited)
    def hierarchy_depth(node: str) -> int:
        parents = accepted_graph[node]
        return 0 if not parents else 1 + max(hierarchy_depth(parent) for parent in parents)
    if any(hierarchy_depth(concept_id) > 12 for concept_id in accepted_graph):
        raise SemanticBuildError("accepted broader taxonomy exceeds maximum depth")

    catalog_manifest = _catalog_manifest(row)
    if catalog_manifest.get("manifest_hash") != row.get("manifest_hash"):
        raise SemanticBuildError("semantic catalog manifest hash conflicts")
    if manifest_path is not None:
        if not Path(manifest_path).exists():
            raise SemanticBuildError("supplied semantic manifest does not exist")
        try:
            local = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SemanticBuildError("local semantic manifest is invalid") from exc
        if not isinstance(local, dict) or local != catalog_manifest or _manifest_hash(local) != local.get("manifest_hash"):
            raise SemanticBuildError("local semantic manifest conflicts with remote build")
    return {
        "command": "semantics verify", "build_id": build_id,
        "evidence_snapshot_id": row["evidence_snapshot_id"], "verified": True,
        "concept_count": len(concepts), "mention_count": len(mentions),
        "taxonomy_count": len(taxonomy), "semantic_logical_hash": logical,
        "local_model_calls_occurred": False, "turbopuffer_api_calls_occurred": True,
        "turbopuffer_writes_occurred": False, "hosted_model_calls_occurred": False,
        "hosted_model_cost": 0, **metrics,
    }


def inspect_semantic_build(
    client: RemoteClient, *, build_id: str, kind: str, status: str | None = None,
    limit: int = 25,
) -> dict[str, object]:
    if kind not in {"summary", "concepts", "mentions", "taxonomy"}:
        raise SemanticBuildError("semantic inspect kind is invalid")
    if status not in {None, "accepted", "provisional"}:
        raise SemanticBuildError("semantic inspect status is invalid")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise SemanticBuildError("semantic inspect limit must be between 1 and 100")
    metrics = _new_metrics()
    row = _read_semantic_catalog(client, build_id, metrics)
    if row is None:
        raise SemanticBuildError(f"completed semantic build {build_id!r} was not found")
    if kind == "summary":
        items: object = {
            key: row[key] for key in (
                "build_id", "evidence_snapshot_id", "coverage", "selected_row_count",
                "candidate_count", "accepted_concept_count", "provisional_concept_count",
                "mention_count", "taxonomy_count", "model_call_count", "evidence_utf8_bytes",
                "derived_bytes", "semantic_logical_hash",
            )
        }
        items["quality"] = _json_catalog_field(row, "quality_json")
    else:
        namespace, schema = {
            "concepts": (str(row["concepts_namespace"]), CONCEPT_SCHEMA),
            "mentions": (str(row["mentions_namespace"]), MENTION_SCHEMA),
            "taxonomy": (str(row["taxonomy_namespace"]), TAXONOMY_SCHEMA),
        }[kind]
        resource = client.namespace(namespace)
        if not _resource_exists(resource, metrics=metrics):
            raise SemanticBuildError("semantic inspect namespace is missing")
        _validate_exact_schema(_metadata(resource, metrics=metrics), schema)
        response = _safe_call(
            "semantic inspect query", resource.query, rank_by=("id", "asc"), limit=limit,
            filters=("status", "Eq", status) if status else None,
            include_attributes=list(schema), consistency=dict(STRONG_CONSISTENCY),
        )
        metrics["remote_queries"] += 1
        plain = _plain(response); raw = list(plain.get("rows", [])) if isinstance(plain, dict) else []
        if len(raw) > limit:
            raise SemanticBuildError("semantic inspect returned more rows than requested")
        allowed = {
            "concepts": {"id", "canonical_label", "definition", "concept_type", "aliases", "status", "policy_score", "policy_breakdown_json", "mention_count", "source_namespaces"},
            "mentions": {"id", "concept_id", "status", "evidence_row_id", "branch_namespace", "source_namespace", "source_row_id", "chunk_hash", "canonical_url", "title", "section_path", "label", "excerpt", "policy_score"},
            "taxonomy": {"id", "subject_id", "predicate", "object_id", "status", "policy_score", "policy_breakdown_json", "basis", "representative_mention_ids", "rationale"},
        }[kind]
        items = [{key: value for key, value in value.items() if key in allowed} for value in raw if isinstance(value, dict)]
    return {
        "command": "semantics inspect", "build_id": build_id, "kind": kind,
        "status": status, "limit": limit, "items": items,
        "local_model_calls_occurred": False, "turbopuffer_api_calls_occurred": True,
        "turbopuffer_writes_occurred": False, "hosted_model_calls_occurred": False,
        "hosted_model_cost": 0, **metrics,
    }


def estimate_semantic_build(
    client: RemoteClient, *, evidence_snapshot_id: str, model_client: LocalInferenceClient,
    limits: BuildLimits = BuildLimits(), sample_rows: int = 20, sample_seed: int = 0,
    prior_model_calls: int = 0,
) -> dict[str, object]:
    """Bounded no-write/no-artifact estimate using active immutable evidence."""
    limits.validate()
    if type(prior_model_calls) is not int or prior_model_calls < 0:
        raise SemanticBuildError("prior model calls must be a non-negative integer")
    if type(sample_rows) is not int or sample_rows < 1 or sample_rows > 20:
        raise SemanticBuildError("semantic estimate sample rows must be between 1 and 20")
    metrics = _new_metrics()
    try:
        verify_evidence_snapshot(client, snapshot_id=evidence_snapshot_id, _metrics=metrics)
        evidence = _read_catalog_row(client, snapshot_id=evidence_snapshot_id, metrics=metrics)
    except Exception as exc:
        raise SemanticBuildError(f"completed evidence snapshot validation failed: {exc}") from exc
    if evidence is None:
        raise SemanticBuildError("completed evidence snapshot was not found")
    total = sum(
        1 for _row in _active_ledger_rows(
            client, str(evidence["ledger_namespace"]), metrics
        )
    )
    if total < 1:
        raise SemanticBuildError("completed evidence snapshot has no active rows")
    selected_count = min(sample_rows, total)
    selected, _counts, _allocation = _select_rows(
        client, snapshot_id=evidence_snapshot_id,
        ledger_namespace=str(evidence["ledger_namespace"]),
        maximum_rows=max(total, 1), sample_size=selected_count, sample_seed=sample_seed,
        metrics=metrics,
    )
    started = time.monotonic(); evidence_bytes = 0; candidates = 0; calls = 0; retries = 0
    sampled_with_model = 0
    for ledger in selected:
        evidence_row = _content_for_row(client, ledger, metrics)
        content = str(evidence_row["content"])
        evidence_bytes += len(content.encode("utf-8"))
        remaining_calls = limits.maximum_model_calls - prior_model_calls - calls
        if remaining_calls < 1:
            continue
        values, retry_count = _model_extract(
            model_client, content=content, evidence_row_id=str(ledger["id"]),
            source_namespace=str(ledger["source_namespace"]),
            maximum_attempts=min(3, remaining_calls),
        )
        candidates += len(values); retries += retry_count; calls += retry_count + 1
        sampled_with_model += 1
    latency = (
        (time.monotonic() - started) / calls if calls else 0.0
    )
    candidate_scale = total / sampled_with_model if sampled_with_model else 0.0
    evidence_scale = total / selected_count
    estimated_candidates = (
        math.ceil(candidates * candidate_scale)
        if sampled_with_model
        else total * MAX_CANDIDATES_PER_ROW
    )
    estimated_calls = prior_model_calls + math.ceil(
        total + estimated_candidates * 0.25
    )
    estimated_evidence_bytes = math.ceil(evidence_bytes * evidence_scale)
    approximate_tokens = math.ceil(estimated_evidence_bytes / 3)
    concept_low = max(0, math.floor(estimated_candidates * 0.45))
    concept_high = estimated_candidates
    mention_low, mention_high = concept_low, estimated_candidates
    taxonomy_low, taxonomy_high = 0, estimated_candidates * 3
    estimated_derived_bytes = (
        estimated_candidates * 2_048
        + concept_high * 1_024
        + mention_high * 1_536
        + taxonomy_high * 1_024
    )
    estimated_seconds = estimated_calls * latency
    limit_results = {
        "evidence_rows": {"estimated": total, "maximum": limits.maximum_rows, "passes": total <= limits.maximum_rows},
        "evidence_utf8_bytes": {"estimated": estimated_evidence_bytes, "maximum": limits.maximum_evidence_bytes, "passes": estimated_evidence_bytes <= limits.maximum_evidence_bytes},
        "model_calls": {"estimated": estimated_calls, "maximum": limits.maximum_model_calls, "passes": estimated_calls <= limits.maximum_model_calls},
        "wall_seconds": {"estimated": math.ceil(estimated_seconds), "maximum": limits.maximum_wall_seconds, "passes": estimated_seconds <= limits.maximum_wall_seconds},
        "candidates": {"estimated": estimated_candidates, "maximum": limits.maximum_candidates, "passes": estimated_candidates <= limits.maximum_candidates},
        "concepts": {"estimated": concept_high, "maximum": limits.maximum_concepts, "passes": concept_high <= limits.maximum_concepts},
        "mentions": {"estimated": mention_high, "maximum": limits.maximum_candidates, "passes": mention_high <= limits.maximum_candidates},
        "taxonomy_relations": {"estimated": taxonomy_high, "maximum": limits.maximum_taxonomy_rows, "passes": taxonomy_high <= limits.maximum_taxonomy_rows},
        "derived_utf8_bytes": {"estimated": estimated_derived_bytes, "maximum": limits.maximum_derived_bytes, "passes": estimated_derived_bytes <= limits.maximum_derived_bytes},
    }
    would_pass = all(bool(value["passes"]) for value in limit_results.values())
    return {
        "command": "semantics estimate", "snapshot_id": evidence_snapshot_id,
        "total_active_rows": total, "sampled_rows": selected_count,
        "approximate_input_tokens": approximate_tokens,
        "token_estimate_method": "conservative_utf8_bytes_divided_by_3",
        "evidence_utf8_bytes": estimated_evidence_bytes,
        "sample_evidence_utf8_bytes": evidence_bytes,
        "estimated_model_calls": estimated_calls,
        "observed_local_call_latency_seconds": round(latency, 6),
        "estimated_wall_time_range_seconds": [round(estimated_seconds * 0.75, 3), round(estimated_seconds * 1.5, 3)],
        "estimated_candidate_count": estimated_candidates,
        "estimated_concept_count_range": [concept_low, concept_high],
        "estimated_mention_count_range": [mention_low, mention_high],
        "estimated_taxonomy_relation_count_range": [taxonomy_low, taxonomy_high],
        "estimated_derived_utf8_bytes": estimated_derived_bytes,
        "limit_results": limit_results,
        "maximum_limits": asdict(limits), "would_pass_limits": would_pass,
        "local_model_calls_occurred": prior_model_calls + calls > 0, "turbopuffer_api_calls_occurred": True,
        "turbopuffer_writes_occurred": False, "remote_writes_occurred": False,
        "hosted_model_calls_occurred": False, "hosted_model_cost": 0,
        "local_full_corpus_written": False, "local_artifacts_written": False,
        "local_manifest_written": False, "sample_model_calls": calls,
        "prior_model_calls": prior_model_calls,
        "model_call_count": prior_model_calls + calls,
        "sample_retries": retries, **metrics,
    }
