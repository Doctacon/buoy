"""Fail-closed executor for the one ratified experimental Buoy baseline.

The live entry point accepts only durable paths. It verifies an exact Approval A
record and constructs the plan, immutable model, provider, and local effects
internally. A separately named simulation entry point accepts fakes for tests;
simulation can never enter the live construction path or claim live success.
Neither entry point is connected to the ordinary CLI or apply path.
"""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version as package_version
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any, Callable, Mapping, Protocol, Sequence

from buoy_search.applied_state import (
    ApplyRunSummary,
    AppliedState,
    AppliedStateRow,
    acquire_namespace_apply_lock,
    applied_state_paths,
    load_applied_state,
    save_applied_state,
)
from buoy_search.apply import (
    VerifiedApplyPlan,
    build_state_after_apply,
    embedding_text_for_chunk,
    load_verified_apply_plan,
    verified_source_metadata,
)
from buoy_search.catalog import (
    CardFields,
    NamespaceCard,
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    card_to_dict,
    generated_semantics,
    parse_card,
    prepare_card,
    prepare_prospective_card,
)
from buoy_search.catalog_pending import (
    applied_state_hash,
    build_pending_payload,
    confirm_pending,
    create_pending,
    inspect_apply_collision,
    load_pending_snapshot,
    pending_path_for_plan,
    remove_expected_pending,
)
from buoy_search.plan_artifacts import (
    GENERIC_SITE_TURBOPUFFER_SCHEMA,
    PLAN_SCHEMA_VERSION,
    build_generic_site_row,
    stable_hash,
)
from buoy_search.retriever import ranking_defaults_for_namespace
from buoy_search.remote_catalog import (
    DISTANCE_METRIC,
    REMOTE_CARD_ATTRIBUTES,
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_CATALOG_SCHEMA,
    STRONG_CONSISTENCY,
    card_from_remote_row,
    card_to_remote_row,
    remote_card_id,
    validate_remote_schema,
)

JsonObject = dict[str, Any]
REGION = "gcp-us-central1"
PLAN_ID = "plan_b6c5d128295f442f"
ARTIFACT_HASH = "b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce"
SOURCE_REPOSITORY = "Doctacon/buoy-search"
SOURCE_COMMIT = "fcb7abbe1652d2eab4ee23816b6d992d893603ac"
SOURCE_URI = "https://github.com/Doctacon/buoy-search"
SITE_ID = "github-doctacon-buoy-search"
TARGET_NAMESPACE = "github-doctacon-buoy-search-v1"
MODEL = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
MODEL_PRECISION = "float32"
CACHE_MANIFEST_HASH = "5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35"
README_HASH = "ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837"
CONTENT_ROWS = 903
CONTENT_BATCH_SIZES = (64,) * 14 + (7,)
MAX_ATTEMPTS = 26
MAX_WRITE_ROW_POSITIONS = 904
MAX_RETURNED_ROW_POSITIONS = 1817
SDK_VERSION = "2.4.0"
APPROVAL_A_TEXT = (
    "Approve one fail-closed experimental baseline operation in `gcp-us-central1` for retained plan "
    "`plan_b6c5d128295f442f` (artifact "
    "`b6c5d128295f442fcae21472c9bcb037ecb44101ca648115e8f666ba59a6f0ce`) from "
    "`Doctacon/buoy-search@fcb7abbe1652d2eab4ee23816b6d992d893603ac` into only "
    "`github-doctacon-buoy-search-v1`. Before writes, require the target namespace to be "
    "unambiguously absent or exact-schema/cosine-compatible and verified empty. Use 903 offline "
    "local float32 embeddings from MIT-licensed "
    "`BAAI/bge-small-en-v1.5@5c38ec7c405ec4b44b94cc5a9bb96e735b38267a` only after cache "
    "manifest `5f783ebce23b6ac957d2741399b46e19502b1751acfd3c744b8c41103b138f35` and "
    "README/license hash `ddb964361a55c6e5dfca6361615854b260c9c960205d04c7520151aaa1d75837` "
    "revalidate. Set the `turbopuffer==2.4.0` SDK to `max_retries=0`; permit at most 26 physical "
    "provider attempts: 10 bounded reads and 16 writes, comprising exactly 15 content upserts "
    "(14 × 64 rows plus 1 × 7 rows), at most one conditional catalog-card upsert, at most 904 "
    "attempted write-row positions, and at most 1,817 returned read-row positions. Capture every "
    "content/catalog attempt and response with request counts, exact or explicitly absent "
    "`rows_affected`, redacted billing or explicitly absent billing, and partial/indeterminate "
    "outcomes. Permit zero row/namespace/card deletes and no retry, pagination, schema/signature "
    "fallback, cleanup delete, other namespace/card, or reassignment of unused request slots. "
    "After writes, require two bounded strong reads to match exactly all 903 intended rows before "
    "the catalog mutation, then two exact-card reads to match the intended stable card revision "
    "before local DuckDB applied-state success commit. Abort on any "
    "source/artifact/model/license/cache/state/schema/distance/row/card/count/budget mismatch; on "
    "content mismatch make no catalog-card or local-state commit, and on catalog mismatch make no "
    "local-state or card-success commit while reporting any possible remote partial effect. "
    "Provider/account dollar pricing is unknown, so this approval binds operational exposure "
    "rather than a dollar ceiling. It does not authorize C3 retrieval, a recrawl/replan, another "
    "namespace, a default change, or promotion."
)
APPROVAL_A_TEXT_SHA256 = hashlib.sha256(APPROVAL_A_TEXT.encode("utf-8")).hexdigest()
APPROVAL_RECORD_FIELDS = {
    "schema_version", "approval", "status", "approval_text", "approval_text_sha256",
    "granted_at", "granted_by", "provenance",
}
APPROVAL_PROVENANCE_FIELDS = {"source_system", "conversation_id", "message_id"}
# Approval A is pinned only to the exact durable grant bytes and provenance.
APPROVAL_A_GRANTED_RECORD_SHA256: str | None = (
    "46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec"
)
APPROVAL_A_GRANTED_PROVENANCE: JsonObject | None = {
    "source_system": "pi",
    "conversation_id": "runtime-id-not-exposed",
    "message_id": "sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74",
}

CONTENT_SCHEMA: JsonObject = {
    **GENERIC_SITE_TURBOPUFFER_SCHEMA,
    "vector": {
        **GENERIC_SITE_TURBOPUFFER_SCHEMA["vector"],
        "ann": {"distance_metric": DISTANCE_METRIC},
    },
}
CONTENT_ATTRIBUTES = tuple(name for name in CONTENT_SCHEMA if name != "vector")


class ExperimentalBaselineError(RuntimeError):
    """Raised on any mismatch while preserving secret-free attempt evidence."""

    def __init__(self, message: str, evidence: JsonObject | None = None) -> None:
        super().__init__(message)
        self.evidence = evidence


class DefinitiveProviderError(RuntimeError):
    """Injected provider failure whose remote outcome is known to be failed."""


class NamespaceResource(Protocol):
    def metadata(self, **kwargs: object) -> object: ...
    def query(self, **kwargs: object) -> object: ...
    def write(self, **kwargs: object) -> object: ...


@dataclass(frozen=True)
class CacheAttestation:
    revision: str
    manifest_sha256: str
    readme_sha256: str
    license: str
    license_statement_present: bool
    file_count: int


@dataclass(frozen=True)
class PreparedBaseline:
    """All model-derived values validated before credential access."""

    rows: tuple[JsonObject, ...]
    card: NamespaceCard
    prospective_card: NamespaceCard
    next_state: AppliedState
    model: str
    model_revision: str
    precision: str
    dimensions: int
    normalized: bool
    pooling: str


@dataclass(frozen=True)
class ProviderResources:
    """Simulation-only provider fakes used by the fake-backed matrix."""

    target: NamespaceResource
    catalog: NamespaceResource
    sdk_version: str = "simulation"
    max_retries: int = -1


@dataclass(frozen=True)
class LocalEffects:
    """Simulation-only local effects used by the fake-backed matrix."""

    lock: Callable[[], AbstractContextManager[None]]
    validate_preconditions: Callable[[VerifiedApplyPlan], None]
    create_pending: Callable[[PreparedBaseline, NamespaceCard | None], None]
    commit_state: Callable[[PreparedBaseline], None]
    remove_pending: Callable[[], None]
    pending_exists: Callable[[], bool]
    state_matches: Callable[[PreparedBaseline], bool]


@dataclass(frozen=True)
class Slot:
    number: int
    phase: str
    resource: str
    operation_number: int
    kind: str
    requested_rows: int | None = None
    top_k: int | None = None
    returned_rows_ceiling: int = 0


@dataclass
class Attempt:
    slot: Slot
    status: str = "attempted"
    rows_affected: int | None = None
    rows_affected_present: bool = False
    returned_rows: int = 0
    billing: JsonObject | None = None
    billing_present: bool = False
    metrics: JsonObject | None = None
    metrics_present: bool = False
    request_identity: str | None = None
    request_identity_present: bool = False
    affected_ids: list[str] | None = None
    affected_ids_present: bool = False
    error: str | None = None
    cumulative_physical_attempts: int = 0
    cumulative_write_row_positions: int = 0
    cumulative_returned_row_positions: int = 0


SLOTS: tuple[Slot, ...] = (
    Slot(1, "target_preflight_metadata", TARGET_NAMESPACE, 1, "read"),
    Slot(2, "target_empty_check", TARGET_NAMESPACE, 1, "read", top_k=1, returned_rows_ceiling=1),
    Slot(3, "catalog_preflight_metadata", REMOTE_CATALOG_NAMESPACE, 1, "read"),
    Slot(4, "catalog_card_preflight", REMOTE_CATALOG_NAMESPACE, 1, "read", top_k=2, returned_rows_ceiling=2),
    Slot(5, "catalog_card_preflight", REMOTE_CATALOG_NAMESPACE, 2, "read", top_k=2, returned_rows_ceiling=2),
    *(Slot(6 + index, "content_write", TARGET_NAMESPACE, index + 1, "write", requested_rows=size)
      for index, size in enumerate(CONTENT_BATCH_SIZES)),
    Slot(21, "target_postwrite_metadata", TARGET_NAMESPACE, 1, "read"),
    Slot(22, "target_postwrite_verification", TARGET_NAMESPACE, 1, "read", top_k=904, returned_rows_ceiling=904),
    Slot(23, "target_postwrite_verification", TARGET_NAMESPACE, 2, "read", top_k=904, returned_rows_ceiling=904),
    Slot(24, "catalog_conditional_write", REMOTE_CATALOG_NAMESPACE, 1, "write", requested_rows=1),
    Slot(25, "catalog_postwrite_verification", REMOTE_CATALOG_NAMESPACE, 1, "read", top_k=2, returned_rows_ceiling=2),
    Slot(26, "catalog_postwrite_verification", REMOTE_CATALOG_NAMESPACE, 2, "read", top_k=2, returned_rows_ceiling=2),
)


@dataclass
class _Ledger:
    attempts: dict[int, Attempt] = field(default_factory=dict)
    physical_attempts: int = 0
    write_row_positions: int = 0
    returned_row_positions: int = 0
    delete_attempts: int = 0

    def invoke(
        self,
        slot_number: int,
        call: Callable[[], object],
        *,
        expected_affected_ids: Sequence[str] | None = None,
    ) -> JsonObject:
        slot = SLOTS[slot_number - 1]
        if slot.number != slot_number or slot_number in self.attempts:
            raise ExperimentalBaselineError("attempt slot reuse or reassignment is forbidden", self.evidence())
        self.physical_attempts += 1
        self.write_row_positions += slot.requested_rows or 0
        attempt = Attempt(
            slot=slot,
            cumulative_physical_attempts=self.physical_attempts,
            cumulative_write_row_positions=self.write_row_positions,
            cumulative_returned_row_positions=self.returned_row_positions,
        )
        # Accounting exists before the physical call.
        self.attempts[slot_number] = attempt
        self._check_budgets()
        try:
            response = call()
        except BaseException as exc:
            attempt.status = "failed" if isinstance(exc, DefinitiveProviderError) else "indeterminate"
            attempt.error = _safe_error(exc)
            response_errors = _capture_attached_error_accounting(attempt, exc)
            self.returned_row_positions += attempt.returned_rows
            attempt.cumulative_returned_row_positions = self.returned_row_positions
            try:
                self._check_budgets()
            except ExperimentalBaselineError as budget_error:
                response_errors.append(str(budget_error))
            detail = f"; attached accounting malformed: {'; '.join(response_errors)}" if response_errors else ""
            raise ExperimentalBaselineError(
                f"provider attempt {slot_number} did not complete ({attempt.error}){detail}", self.evidence()
            ) from None
        try:
            payload = _plain_response(response)
            response_errors = _capture_response(
                attempt, payload, require_rows_affected=slot.kind == "write"
            )
            if slot.kind == "write" and attempt.rows_affected != slot.requested_rows:
                response_errors.append("successful write rows_affected mismatch")
            if expected_affected_ids is not None and attempt.affected_ids != list(expected_affected_ids):
                response_errors.append("successful write affected IDs mismatch")
            self.returned_row_positions += attempt.returned_rows
            attempt.cumulative_returned_row_positions = self.returned_row_positions
            self._check_budgets()
            if response_errors:
                raise ExperimentalBaselineError("; ".join(response_errors))
            attempt.status = "succeeded"
            return payload
        except ExperimentalBaselineError as exc:
            attempt.status = "failed"
            attempt.error = str(exc)
            raise ExperimentalBaselineError(
                f"provider attempt {slot_number} returned a malformed response: {exc}", self.evidence()
            ) from None

    def mark_unused(self, slot_number: int) -> None:
        if slot_number in self.attempts:
            raise ExperimentalBaselineError("an attempted slot cannot become unused", self.evidence())

    def _check_budgets(self) -> None:
        if self.physical_attempts > MAX_ATTEMPTS:
            raise ExperimentalBaselineError("physical-attempt ceiling exceeded", self.evidence())
        if self.write_row_positions > MAX_WRITE_ROW_POSITIONS:
            raise ExperimentalBaselineError("write-row-position ceiling exceeded", self.evidence())
        if self.returned_row_positions > MAX_RETURNED_ROW_POSITIONS:
            raise ExperimentalBaselineError("returned-row-position ceiling exceeded", self.evidence())
        if self.delete_attempts:
            raise ExperimentalBaselineError("delete attempts are forbidden", self.evidence())

    def evidence(self, *, success: bool = False) -> JsonObject:
        mapped: list[JsonObject] = []
        for slot in SLOTS:
            attempt = self.attempts.get(slot.number)
            if attempt is None:
                mapped.append({**asdict(slot), "status": "unused"})
            else:
                value = asdict(attempt)
                value["slot"] = asdict(slot)
                mapped.append(value)
        return {
            "executor": "experimental_buoy_baseline",
            "success": success,
            "approval_a_granted_by_executor": False,
            "approval_b_granted_by_executor": False,
            "dollar_cost": "unknown",
            "required_sdk_version": SDK_VERSION,
            "required_max_retries": 0,
            "limits": {
                "physical_attempts": MAX_ATTEMPTS,
                "write_row_positions": MAX_WRITE_ROW_POSITIONS,
                "returned_row_positions": MAX_RETURNED_ROW_POSITIONS,
                "delete_attempts": 0,
            },
            "read_attempts": sum(
                attempt.slot.kind == "read" for attempt in self.attempts.values()
            ),
            "write_attempts": sum(
                attempt.slot.kind == "write" for attempt in self.attempts.values()
            ),
            "physical_attempts": self.physical_attempts,
            "write_row_positions": self.write_row_positions,
            "returned_row_positions": self.returned_row_positions,
            "delete_attempts": self.delete_attempts,
            "slots": mapped,
        }


def validate_model_cache(cache_root: Path) -> CacheAttestation:
    """Hash the exact immutable snapshot without importing/loading a model."""

    root = cache_root.expanduser().resolve(strict=True)
    ref = root / "refs" / "main"
    if ref.read_text(encoding="utf-8").strip() != MODEL_REVISION:
        raise ExperimentalBaselineError("model cache refs/main revision mismatch")
    snapshot = root / "snapshots" / MODEL_REVISION
    if not snapshot.is_dir():
        raise ExperimentalBaselineError("immutable model snapshot is missing")
    entries: list[JsonObject] = []
    for path in sorted((item for item in snapshot.rglob("*") if item.is_file()), key=lambda item: str(item.relative_to(snapshot))):
        data = path.read_bytes()
        entries.append({
            "path": str(path.relative_to(snapshot)),
            "size": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
    manifest_hash = stable_hash(entries)
    readme = snapshot / "README.md"
    readme_bytes = readme.read_bytes()
    readme_text = readme_bytes.decode("utf-8")
    attestation = CacheAttestation(
        revision=MODEL_REVISION,
        manifest_sha256=manifest_hash,
        readme_sha256=hashlib.sha256(readme_bytes).hexdigest(),
        license="mit" if re.search(r"(?m)^license:\s*mit\s*$", readme_text) else "unknown",
        license_statement_present="FlagEmbedding is licensed under the MIT License" in readme_text,
        file_count=len(entries),
    )
    validate_cache_attestation(attestation)
    return attestation


def validate_cache_attestation(value: CacheAttestation) -> None:
    if value.revision != MODEL_REVISION:
        raise ExperimentalBaselineError("model revision mismatch")
    if value.manifest_sha256 != CACHE_MANIFEST_HASH:
        raise ExperimentalBaselineError("full model cache manifest hash mismatch")
    if value.readme_sha256 != README_HASH:
        raise ExperimentalBaselineError("model README hash mismatch")
    if value.license != "mit" or not value.license_statement_present:
        raise ExperimentalBaselineError("immutable model README does not prove the MIT license")
    if value.file_count != 12:
        raise ExperimentalBaselineError("immutable model cache must contain exactly 12 resolved files")


def validate_immutable_plan(verified: VerifiedApplyPlan) -> None:
    """Validate every local plan/state identity before model or credential work."""

    plan = verified.plan
    manifest = verified.manifest
    exact = {
        "plan_id": PLAN_ID,
        "artifact_hash": ARTIFACT_HASH,
        "namespace": TARGET_NAMESPACE,
        "embedding_model": MODEL,
        "embedding_precision": MODEL_PRECISION,
    }
    for field_name, expected in exact.items():
        if plan.get(field_name) != expected:
            raise ExperimentalBaselineError(f"immutable plan {field_name} mismatch")
    if (
        manifest.namespace != TARGET_NAMESPACE
        or manifest.site_id != SITE_ID
        or manifest.base_url != SOURCE_URI
        or len(manifest.chunks) != CONTENT_ROWS
    ):
        raise ExperimentalBaselineError("immutable manifest source/namespace/row count mismatch")
    row_ids = [chunk.row_id for chunk in manifest.chunks]
    if len(set(row_ids)) != CONTENT_ROWS or any(not value for value in row_ids):
        raise ExperimentalBaselineError("immutable manifest must contain 903 unique non-empty row IDs")
    for record in [*manifest.pages, *manifest.chunks]:
        metadata = record.source_metadata
        if metadata.get("repo_full_name") != SOURCE_REPOSITORY:
            raise ExperimentalBaselineError("immutable source repository mismatch")
        if metadata.get("commit_sha") != SOURCE_COMMIT:
            raise ExperimentalBaselineError("immutable source commit mismatch")
    if (
        verified.state.rows
        or not verified.state.first_apply
        or verified.state.site_id != manifest.site_id
        or verified.state.namespace != TARGET_NAMESPACE
        or verified.state.base_url != manifest.base_url
    ):
        raise ExperimentalBaselineError("local applied-state ledger is not exactly empty and compatible")
    diff = verified.diff
    if (
        not diff.first_apply
        or diff.rows_to_upsert != CONTENT_ROWS
        or diff.chunks_to_embed != CONTENT_ROWS
        or diff.chunks_unchanged != 0
        or diff.stale_rows != 0
        or diff.retained_stale_rows != 0
        or diff.stale_row_records
        or diff.retained_stale_row_records
        or len(diff.rows_to_upsert_records) != CONTENT_ROWS
    ):
        raise ExperimentalBaselineError("immutable first-apply diff contains incompatible or stale intent")


def validate_prepared(verified: VerifiedApplyPlan, prepared: PreparedBaseline) -> None:
    if (
        prepared.model != MODEL
        or prepared.model_revision != MODEL_REVISION
        or prepared.precision != MODEL_PRECISION
        or prepared.dimensions != ROUTING_DIMENSIONS
        or not prepared.normalized
        or prepared.pooling != "cls"
    ):
        raise ExperimentalBaselineError("prepared model contract mismatch")
    if len(prepared.rows) != CONTENT_ROWS:
        raise ExperimentalBaselineError("prepared content row count mismatch")
    chunks = list(verified.manifest.chunks)
    expected_ids = [chunk.row_id for chunk in chunks]
    actual_ids: list[str] = []
    for index, (chunk, row) in enumerate(zip(chunks, prepared.rows, strict=True)):
        if not isinstance(row, dict):
            raise ExperimentalBaselineError(f"prepared row {index} is not an object")
        vector = _validate_vector(row.get("vector"), label=f"content row {index}")
        expected = build_generic_site_row(
            chunk, vector, plan_id=PLAN_ID, applied_at=prepared.next_state.updated_at
        )
        if row != expected:
            raise ExperimentalBaselineError(f"prepared row {index} attributes mismatch")
        actual_ids.append(str(row.get("id")))
    if actual_ids != expected_ids or len(set(actual_ids)) != CONTENT_ROWS:
        raise ExperimentalBaselineError("prepared content IDs/order mismatch")
    card = parse_card(card_to_dict(prepared.card, include_vector=True))
    prospective = prepared.prospective_card
    if (
        prospective.last_plan_id != PLAN_ID
        or prospective.last_apply_id is not None
        or card.last_plan_id != PLAN_ID
        or card.last_apply_id != prepared.next_state.last_apply_id
    ):
        raise ExperimentalBaselineError("prepared catalog card lineage mismatch")
    comparable_card = card_to_dict(card, include_vector=True)
    comparable_prospective = card_to_dict(prospective, include_vector=True)
    for volatile in ("card_revision", "last_apply_id"):
        comparable_card.pop(volatile)
        comparable_prospective.pop(volatile)
    if comparable_card != comparable_prospective:
        raise ExperimentalBaselineError("prepared prospective/final card mismatch")
    exact_card_values = {
        "namespace": TARGET_NAMESPACE,
        "enabled": True,
        "source_kind": "github_repo",
        "source_uri": SOURCE_URI,
        "site_id": SITE_ID,
        "title": SOURCE_REPOSITORY,
        "summary": f"Public GitHub repository {SOURCE_REPOSITORY} indexed from {SOURCE_URI}.",
        "aliases": ["buoy-search"],
        "tags": ["github", "repository"],
        "semantic_origin": "generated",
        "region": REGION,
        "embedding_model": MODEL,
        "embedding_precision": MODEL_PRECISION,
        "vector_dimensions": ROUTING_DIMENSIONS,
        "routing_model": ROUTING_MODEL,
        "routing_model_revision": ROUTING_MODEL_REVISION,
        "last_plan_id": PLAN_ID,
        "ranking_mode": "file",
        "ranking_profile": "repo_code",
        "ranking_pool": 100,
        "ranking_aggregation": "adaptive_sum_3",
    }
    if any(getattr(card, name) != value for name, value in exact_card_values.items()):
        raise ExperimentalBaselineError("prepared catalog card compatibility mismatch")
    if not card.last_apply_id:
        raise ExperimentalBaselineError("prepared catalog card is missing apply lineage")
    state = prepared.next_state
    expected_state_rows = [
        AppliedStateRow(
            row_id=chunk.row_id,
            canonical_url=chunk.canonical_url,
            page_hash=chunk.page_hash,
            chunk_hash=chunk.chunk_hash,
            embedding_text_hash=chunk.embedding_text_hash,
            plan_id=PLAN_ID,
            applied_at=state.updated_at,
            status="active",
        )
        for chunk in sorted(chunks, key=lambda item: item.row_id)
    ]
    if (
        state.schema_version != verified.state.schema_version
        or state.site_id != SITE_ID
        or state.namespace != TARGET_NAMESPACE
        or state.base_url != SOURCE_URI
        or not state.updated_at
        or state.last_plan_id != PLAN_ID
        or state.last_apply_id != card.last_apply_id
        or state.rows != expected_state_rows
    ):
        raise ExperimentalBaselineError("prepared local applied-state mismatch")


def create_provider_resources(*, api_key: str, region: str, max_retries: int) -> ProviderResources:
    """Construct exactly one locked Turbopuffer 2.4.0 client with no retries."""

    if region != REGION or max_retries != 0:
        raise ExperimentalBaselineError("provider construction requires exact region and max_retries=0")
    if package_version("turbopuffer") != SDK_VERSION:
        raise ExperimentalBaselineError("locked turbopuffer SDK version mismatch")
    try:
        import turbopuffer
        client = turbopuffer.Turbopuffer(api_key=api_key, region=region, max_retries=0)
    except Exception as exc:
        raise ExperimentalBaselineError(f"provider client construction failed ({_safe_error(exc)})") from None
    class DirectResource:
        def __init__(self, resource: object) -> None:
            self._resource = resource

        def metadata(self, **kwargs: object) -> object:
            try:
                return self._resource.metadata(**kwargs)  # type: ignore[attr-defined]
            except turbopuffer.NotFoundError:
                # A locked SDK 404 is the one unambiguous namespace-absent result.
                return {"namespace_absent": True}

        def query(self, **kwargs: object) -> object:
            return self._resource.query(**kwargs)  # type: ignore[attr-defined]

        def write(self, **kwargs: object) -> object:
            return self._resource.write(**kwargs)  # type: ignore[attr-defined]

    return ProviderResources(
        target=DirectResource(client.namespace(TARGET_NAMESPACE)),
        catalog=DirectResource(client.namespace(REMOTE_CATALOG_NAMESPACE)),
        sdk_version=SDK_VERSION,
        max_retries=0,
    )


def validate_approval_a_record(path: Path) -> JsonObject:
    """Verify the exact durable Approval A grant and its user-message provenance."""

    absolute = path.expanduser().absolute()
    try:
        metadata = absolute.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ExperimentalBaselineError("Approval A record must be a regular non-symlink file")
        raw = absolute.read_bytes()
        payload = json.loads(raw)
    except ExperimentalBaselineError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ExperimentalBaselineError(f"Approval A record is unreadable ({_safe_error(exc)})") from None
    if not isinstance(payload, dict) or set(payload) != APPROVAL_RECORD_FIELDS:
        raise ExperimentalBaselineError("Approval A record has missing or extra fields")
    if (
        type(payload["schema_version"]) is not int
        or payload["schema_version"] != 1
        or payload["approval"] != "experimental-buoy-baseline-approval-a"
        or payload["status"] != "granted"
        or payload["approval_text"] != APPROVAL_A_TEXT
        or payload["approval_text_sha256"] != APPROVAL_A_TEXT_SHA256
    ):
        raise ExperimentalBaselineError("Approval A record does not contain the exact granted contract")
    for name in ("granted_at", "granted_by"):
        if not isinstance(payload[name], str) or not payload[name].strip():
            raise ExperimentalBaselineError(f"Approval A record field {name} must be non-empty")
    try:
        granted_at = datetime.fromisoformat(payload["granted_at"].replace("Z", "+00:00"))
    except ValueError:
        raise ExperimentalBaselineError("Approval A granted_at must be an ISO-8601 timestamp") from None
    if granted_at.tzinfo is None:
        raise ExperimentalBaselineError("Approval A granted_at must include a timezone")
    provenance = payload["provenance"]
    if not isinstance(provenance, dict) or set(provenance) != APPROVAL_PROVENANCE_FIELDS:
        raise ExperimentalBaselineError("Approval A provenance has missing or extra fields")
    if any(not isinstance(provenance[name], str) or not provenance[name].strip() for name in APPROVAL_PROVENANCE_FIELDS):
        raise ExperimentalBaselineError("Approval A provenance fields must be non-empty")
    record_hash = hashlib.sha256(raw).hexdigest()
    if APPROVAL_A_GRANTED_RECORD_SHA256 is None or APPROVAL_A_GRANTED_PROVENANCE is None:
        raise ExperimentalBaselineError("Approval A remains ungranted in this reviewed build")
    if (
        record_hash != APPROVAL_A_GRANTED_RECORD_SHA256
        or provenance != APPROVAL_A_GRANTED_PROVENANCE
    ):
        raise ExperimentalBaselineError("Approval A record/provenance is not the source-pinned grant")
    return {
        "record_sha256": record_hash,
        "approval_text_sha256": APPROVAL_A_TEXT_SHA256,
        "granted_at": payload["granted_at"],
        "granted_by": payload["granted_by"],
        "provenance": dict(provenance),
    }


def execute_experimental_baseline(
    *, approval_record: Path, plan_path: Path, cache_root: Path, state_root: Path
) -> JsonObject:
    """Run the live operation from exact durable inputs; there is no CLI route."""

    approval = validate_approval_a_record(approval_record)
    with acquire_namespace_apply_lock(
        site_id=SITE_ID, namespace=TARGET_NAMESPACE, state_root=state_root
    ):
        verified = load_verified_apply_plan(
            plan_path=plan_path, namespace=TARGET_NAMESPACE, state_root=state_root
        )
        cache_attestation = validate_model_cache(cache_root)
        effects = _LiveLocalEffects(verified)
        result = _execute_locked(
            verified,
            cache_attestation=cache_attestation,
            prepare=lambda value: _prepare_live_baseline(value, cache_root),
            credential_reader=_read_live_credential,
            provider_factory=create_provider_resources,
            local_effects=effects,
            simulation=False,
        )
    result["approval_a"] = approval
    return result


def simulate_experimental_baseline(
    verified: VerifiedApplyPlan,
    *,
    cache_attestation: CacheAttestation,
    prepare: Callable[[VerifiedApplyPlan], PreparedBaseline],
    provider: ProviderResources,
    local_effects: LocalEffects,
) -> JsonObject:
    """Exercise the contract with fakes; this can never report a live operation."""

    if provider.sdk_version != "simulation" or provider.max_retries != -1:
        raise ExperimentalBaselineError("simulation provider must carry simulation-only identity")
    with local_effects.lock():
        return _execute_locked(
            verified,
            cache_attestation=cache_attestation,
            prepare=prepare,
            credential_reader=lambda: "simulation-no-credential",
            provider_factory=lambda **_kwargs: provider,
            local_effects=local_effects,
            simulation=True,
        )


def _execute_locked(
    verified: VerifiedApplyPlan,
    *,
    cache_attestation: CacheAttestation,
    prepare: Callable[[VerifiedApplyPlan], PreparedBaseline],
    credential_reader: Callable[[], str],
    provider_factory: Callable[..., ProviderResources],
    local_effects: LocalEffects,
    simulation: bool,
) -> JsonObject:
    ledger = _Ledger()
    pending_created = False
    state_committed = False
    card_verified = False
    provider_attested = False
    try:
        validate_immutable_plan(verified)
        local_effects.validate_preconditions(verified)
        validate_cache_attestation(cache_attestation)
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        prepared = prepare(verified)
        validate_prepared(verified, prepared)
        credential = credential_reader()
        if not isinstance(credential, str) or not credential:
            raise ExperimentalBaselineError("TURBOPUFFER_API_KEY is required for an approved operation")
        provider = provider_factory(api_key=credential, region=REGION, max_retries=0)
        if simulation:
            if provider.sdk_version != "simulation" or provider.max_retries != -1:
                raise ExperimentalBaselineError("simulation provider identity mismatch")
        elif provider.sdk_version != SDK_VERSION or provider.max_retries != 0:
            raise ExperimentalBaselineError("live provider construction did not bind max_retries=0")
        provider_attested = not simulation

        target_absent = _target_preflight(ledger, provider.target)
        if target_absent:
            ledger.mark_unused(2)
        existing_card = _catalog_preflight(ledger, provider.catalog, prepared.card)

        local_effects.create_pending(prepared, existing_card)
        pending_created = local_effects.pending_exists()
        if not pending_created:
            raise ExperimentalBaselineError("pending record was not durably created")
        for batch_number, size in enumerate(CONTENT_BATCH_SIZES, start=1):
            start = sum(CONTENT_BATCH_SIZES[: batch_number - 1])
            rows = list(prepared.rows[start : start + size])
            expected_ids = [str(row["id"]) for row in rows]
            response = ledger.invoke(
                5 + batch_number,
                lambda rows=rows: provider.target.write(
                    distance_metric=DISTANCE_METRIC,
                    schema=CONTENT_SCHEMA,
                    upsert_rows=rows,
                    return_affected_ids=True,
                ),
                expected_affected_ids=expected_ids,
            )
            _require_write_response(
                response, expected_rows=size, expected_ids=expected_ids
            )

        metadata = ledger.invoke(21, lambda: provider.target.metadata())
        _validate_content_metadata(metadata, allow_absent=False)
        first_rows = _target_verification_read(ledger, provider.target, 22)
        second_rows = _target_verification_read(ledger, provider.target, 23)
        _validate_target_rows(first_rows, prepared.rows)
        _validate_target_rows(second_rows, prepared.rows)
        if first_rows != second_rows:
            raise ExperimentalBaselineError("target verification order/content changed between strong reads")

        card_row = card_to_remote_row(prepared.card)
        condition = (
            ("id", "Eq", None)
            if existing_card is None
            else ("card_revision", "Eq", existing_card.card_revision)
        )
        response = ledger.invoke(
            24,
            lambda: provider.catalog.write(
                distance_metric=DISTANCE_METRIC,
                schema=REMOTE_CATALOG_SCHEMA,
                upsert_rows=[card_row],
                upsert_condition=condition,
                return_affected_ids=True,
            ),
            expected_affected_ids=[str(card_row["id"])],
        )
        _require_write_response(response, expected_rows=1, expected_ids=[str(card_row["id"])])
        first_card = _card_read(ledger, provider.catalog, 25, allow_missing=False)
        second_card = _card_read(ledger, provider.catalog, 26, allow_missing=False)
        expected_card = card_to_dict(prepared.card, include_vector=True)
        if first_card is None or second_card is None:
            raise ExperimentalBaselineError("catalog verification did not return the intended card")
        if card_to_dict(first_card, include_vector=True) != expected_card:
            raise ExperimentalBaselineError("first catalog verification card mismatch")
        if card_to_dict(second_card, include_vector=True) != expected_card:
            raise ExperimentalBaselineError("second catalog verification card mismatch")
        if first_card.card_revision != second_card.card_revision:
            raise ExperimentalBaselineError("catalog card revision changed between strong reads")
        card_verified = True
        if ledger.physical_attempts not in {25, 26}:
            raise ExperimentalBaselineError("successful request count is outside the fixed ledger")

        local_effects.commit_state(prepared)
        state_committed = local_effects.state_matches(prepared)
        if not state_committed:
            raise ExperimentalBaselineError("local applied-state commit could not be verified")
        local_effects.remove_pending()
        pending_created = local_effects.pending_exists()
        if pending_created:
            raise ExperimentalBaselineError("pending record still exists after verified cleanup")
        evidence = ledger.evidence(success=True)
        evidence.update({
            "provider_attested": provider_attested,
            "sdk_version": provider.sdk_version if not simulation else None,
            "max_retries": provider.max_retries if not simulation else None,
            "target_namespace": TARGET_NAMESPACE,
            "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
            "content_rows_verified": CONTENT_ROWS,
            "card_revision": prepared.card.card_revision,
            "local_state_committed": True,
            "remote_card_verified": True,
            "pending_retained": False,
            "simulation": simulation,
            "execution_mode": "simulation" if simulation else "live",
        })
        return evidence
    except ExperimentalBaselineError as exc:
        pending_created, state_committed = _observe_local_effects(
            local_effects, prepared=locals().get("prepared"),
            pending_default=pending_created, state_default=state_committed,
        )
        evidence = exc.evidence or ledger.evidence()
        evidence["provider_attested"] = provider_attested
        evidence["pending_retained"] = pending_created
        evidence["local_state_committed"] = state_committed
        evidence["remote_card_verified"] = card_verified
        evidence["card_success"] = card_verified
        evidence["simulation"] = simulation
        evidence["execution_mode"] = "simulation" if simulation else "live"
        exc.evidence = evidence
        raise
    except BaseException as exc:
        pending_created, state_committed = _observe_local_effects(
            local_effects, prepared=locals().get("prepared"),
            pending_default=pending_created, state_default=state_committed,
        )
        evidence = ledger.evidence()
        evidence.update({
            "provider_attested": provider_attested,
            "pending_retained": pending_created,
            "local_state_committed": state_committed,
            "remote_card_verified": card_verified,
            "card_success": card_verified,
            "simulation": simulation,
            "execution_mode": "simulation" if simulation else "live",
        })
        raise ExperimentalBaselineError(f"experimental baseline aborted ({_safe_error(exc)})", evidence) from None


def _read_live_credential() -> str:
    value = os.environ.get("TURBOPUFFER_API_KEY")
    if not value:
        raise ExperimentalBaselineError("TURBOPUFFER_API_KEY is required for an approved operation")
    return value


class _PinnedClsEmbedder:
    """One exact offline model instance with normalized float32 CLS pooling."""

    def __init__(self, cache_root: Path) -> None:
        snapshot = cache_root.expanduser().resolve(strict=True) / "snapshots" / MODEL_REVISION
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer

            self._torch = torch
            self._tokenizer = AutoTokenizer.from_pretrained(
                snapshot, local_files_only=True, revision=MODEL_REVISION
            )
            self._model = AutoModel.from_pretrained(
                snapshot, local_files_only=True, revision=MODEL_REVISION
            ).float().eval()
        except Exception as exc:
            raise ExperimentalBaselineError(
                f"pinned offline model construction failed ({_safe_error(exc)})"
            ) from None
        config = self._model.config
        if getattr(config, "hidden_size", None) != ROUTING_DIMENSIONS:
            raise ExperimentalBaselineError("pinned model hidden dimension mismatch")

    def encode(self, texts: Sequence[str], *, batch_size: int = 32) -> list[list[float]]:
        values: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            tokens = self._tokenizer(
                list(texts[start : start + batch_size]),
                padding=True,
                truncation=True,
                return_tensors="pt",
            )
            with self._torch.no_grad():
                output = self._model(**tokens)
                cls = output.last_hidden_state[:, 0, :].to(dtype=self._torch.float32)
                normalized = self._torch.nn.functional.normalize(cls, p=2, dim=1)
            values.extend(normalized.cpu().tolist())
        return [_validate_vector(value, label="pinned CLS output") for value in values]


def _prepare_live_baseline(verified: VerifiedApplyPlan, cache_root: Path) -> PreparedBaseline:
    # Rehash immediately at the model boundary; callers cannot substitute an
    # attestation object for the exact immutable cache bytes.
    validate_model_cache(cache_root)
    embedder = _PinnedClsEmbedder(cache_root)
    texts = [embedding_text_for_chunk(chunk) for chunk in verified.manifest.chunks]
    vectors = embedder.encode(texts, batch_size=32)
    if len(vectors) != CONTENT_ROWS:
        raise ExperimentalBaselineError("pinned model returned an incorrect embedding count")
    applied_at = datetime.now(timezone.utc).isoformat()
    next_state = build_state_after_apply(verified, applied_at=applied_at, delete_stale=False)
    rows = tuple(
        build_generic_site_row(chunk, vector, plan_id=PLAN_ID, applied_at=applied_at)
        for chunk, vector in zip(verified.manifest.chunks, vectors, strict=True)
    )
    semantics = generated_semantics(
        base_url=verified.manifest.base_url,
        site_id=verified.manifest.site_id,
        plan_schema_version=PLAN_SCHEMA_VERSION,
        source_metadata=verified_source_metadata(verified),
    )
    ranking = ranking_defaults_for_namespace(TARGET_NAMESPACE)
    common = dict(
        namespace=TARGET_NAMESPACE,
        enabled=True,
        source_kind=semantics.source_kind,
        source_uri=semantics.source_uri,
        site_id=SITE_ID,
        title=semantics.title,
        summary=semantics.summary,
        aliases=list(semantics.aliases),
        tags=list(semantics.tags),
        semantic_origin="generated",
        region=REGION,
        embedding_model=MODEL,
        embedding_precision=MODEL_PRECISION,
        plan_schema_version=PLAN_SCHEMA_VERSION,
        ranking_mode=str(ranking["ranking_mode"]),
        ranking_profile=str(ranking["ranking_profile"]),
        ranking_pool=int(ranking["ranking_pool"]),
        ranking_aggregation=str(ranking["ranking_aggregation"]),
        last_plan_id=PLAN_ID,
    )
    prospective = prepare_prospective_card(
        CardFields(**common, last_apply_id=None), embedder=embedder, now=applied_at
    )
    card = prepare_card(
        CardFields(**common, last_apply_id=next_state.last_apply_id),
        existing=prospective,
        embedder=embedder,
        now=applied_at,
    )
    return PreparedBaseline(
        rows=rows,
        card=card,
        prospective_card=prospective,
        next_state=next_state,
        model=MODEL,
        model_revision=MODEL_REVISION,
        precision=MODEL_PRECISION,
        dimensions=ROUTING_DIMENSIONS,
        normalized=True,
        pooling="cls",
    )


class _LiveLocalEffects:
    def __init__(self, verified: VerifiedApplyPlan) -> None:
        self.verified = verified
        self.pending_path = pending_path_for_plan(verified.state_root, PLAN_ID)
        self.pending_snapshot: Any = None

    def validate_preconditions(self, verified: VerifiedApplyPlan) -> None:
        if verified is not self.verified:
            raise ExperimentalBaselineError("live verified-plan identity changed under lock")
        state_path = applied_state_paths(
            site_id=SITE_ID, namespace=TARGET_NAMESPACE, state_root=verified.state_root
        ).database_path.resolve(strict=False)
        inspect_apply_collision(
            self.pending_path,
            expected={
                "state_root": str(verified.state_root.expanduser().resolve(strict=False)),
                "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
                "applied_state_path": str(state_path),
                "site_id": SITE_ID,
                "namespace": TARGET_NAMESPACE,
                "plan_id": PLAN_ID,
                "base_url": SOURCE_URI,
            },
        )

    def create_pending(
        self, prepared: PreparedBaseline, existing_card: NamespaceCard | None
    ) -> None:
        state_root = self.verified.state_root.expanduser().resolve(strict=False)
        state_path = applied_state_paths(
            site_id=SITE_ID, namespace=TARGET_NAMESPACE, state_root=state_root
        ).database_path.resolve(strict=False)
        pending = build_pending_payload(
            state_root=state_root,
            applied_state_path=state_path,
            site_id=SITE_ID,
            namespace=TARGET_NAMESPACE,
            plan_id=PLAN_ID,
            base_url=SOURCE_URI,
            prospective_card=prepared.prospective_card,
            existing_card=existing_card,
            prior_applied_plan_id=None,
            prior_applied_apply_id=None,
            intended_state_hash=applied_state_hash(prepared.next_state),
            region=REGION,
            ranking_contract=ranking_defaults_for_namespace(TARGET_NAMESPACE),
        )
        create_pending(self.pending_path, pending)
        confirm_pending(
            self.pending_path,
            pending,
            apply_id=prepared.next_state.last_apply_id,
            now=prepared.card.updated_at,
        )
        self.pending_snapshot = load_pending_snapshot(self.pending_path)
        if self.pending_snapshot.payload["prospective_card"] != card_to_dict(
            prepared.card, include_vector=True
        ):
            raise ExperimentalBaselineError("confirmed pending card does not match the intended card")

    def commit_state(self, prepared: PreparedBaseline) -> None:
        save_applied_state(
            prepared.next_state,
            state_root=self.verified.state_root,
            apply_run=ApplyRunSummary(
                apply_id=prepared.next_state.last_apply_id,
                plan_id=PLAN_ID,
                applied_at=prepared.next_state.updated_at,
                rows_upserted=CONTENT_ROWS,
                rows_deleted=0,
                retained_stale_rows=0,
            ),
        )

    def remove_pending(self) -> None:
        if self.pending_snapshot is None:
            raise ExperimentalBaselineError("pending snapshot is unavailable for exact cleanup")
        remove_expected_pending(
            self.pending_path,
            self.pending_snapshot.payload,
            expected_device=self.pending_snapshot.device,
            expected_inode=self.pending_snapshot.inode,
        )

    def pending_exists(self) -> bool:
        return self.pending_path.exists() or self.pending_path.is_symlink()

    def state_matches(self, prepared: PreparedBaseline) -> bool:
        try:
            current = load_applied_state(
                site_id=SITE_ID,
                namespace=TARGET_NAMESPACE,
                base_url=SOURCE_URI,
                state_root=self.verified.state_root,
            )
        except Exception:
            return False
        return applied_state_hash(current) == applied_state_hash(prepared.next_state)


def _observe_local_effects(
    effects: LocalEffects,
    *,
    prepared: object,
    pending_default: bool,
    state_default: bool,
) -> tuple[bool, bool]:
    try:
        pending = effects.pending_exists()
    except BaseException:
        pending = pending_default
    try:
        committed = effects.state_matches(prepared) if isinstance(prepared, PreparedBaseline) else state_default
    except BaseException:
        committed = state_default
    return pending, committed


def _target_preflight(ledger: _Ledger, resource: NamespaceResource) -> bool:
    metadata = ledger.invoke(1, lambda: resource.metadata())
    if metadata.get("namespace_absent") is True:
        if "schema" in metadata or "distance_metric" in metadata:
            raise ExperimentalBaselineError("target namespace absence result is ambiguous")
        return True
    _validate_content_metadata(metadata, allow_absent=False)
    response = ledger.invoke(
        2,
        lambda: resource.query(
            rank_by=("id", "asc"), top_k=1, include_attributes=["id"],
            consistency=dict(STRONG_CONSISTENCY),
        ),
    )
    if response["rows"]:
        raise ExperimentalBaselineError("target namespace is not empty")
    return False


def _catalog_preflight(
    ledger: _Ledger, resource: NamespaceResource, intended: NamespaceCard
) -> NamespaceCard | None:
    metadata = ledger.invoke(3, lambda: resource.metadata())
    validate_remote_schema(metadata)
    if metadata.get("distance_metric") != DISTANCE_METRIC:
        raise ExperimentalBaselineError("catalog namespace distance_metric is missing or mismatched")
    first = _card_read(ledger, resource, 4, allow_missing=True)
    second = _card_read(ledger, resource, 5, allow_missing=True)
    if (first is None) != (second is None):
        raise ExperimentalBaselineError("catalog card presence changed between strong reads")
    if first is None:
        return None
    assert second is not None
    if card_to_dict(first, include_vector=True) != card_to_dict(second, include_vector=True):
        raise ExperimentalBaselineError("catalog card changed between strong reads")
    _validate_existing_card_compatibility(first, intended)
    return first


def _validate_existing_card_compatibility(existing: NamespaceCard, intended: NamespaceCard) -> None:
    compatible_fields = (
        "namespace", "enabled", "source_kind", "source_uri", "site_id", "title", "summary",
        "aliases", "tags", "semantic_origin", "region", "embedding_model",
        "embedding_precision", "vector_dimensions", "plan_schema_version", "ranking_mode",
        "ranking_profile", "ranking_pool", "ranking_aggregation", "routing_model",
        "routing_model_revision", "semantic_hash", "vector", "vector_hash",
    )
    if any(getattr(existing, name) != getattr(intended, name) for name in compatible_fields):
        raise ExperimentalBaselineError("existing catalog card is incompatible with the intended card")


def _target_verification_read(
    ledger: _Ledger, resource: NamespaceResource, slot: int
) -> list[JsonObject]:
    response = ledger.invoke(
        slot,
        lambda: resource.query(
            rank_by=("id", "asc"), top_k=904,
            include_attributes=[*CONTENT_ATTRIBUTES, "vector"],
            vector_encoding="float", consistency=dict(STRONG_CONSISTENCY),
        ),
    )
    return response["rows"]


def _validate_target_rows(actual: Sequence[JsonObject], expected: Sequence[JsonObject]) -> None:
    if len(actual) != CONTENT_ROWS:
        raise ExperimentalBaselineError("target verification must return exactly 903 rows and no 904th row")
    ids = [row.get("id") for row in actual]
    if len(set(ids)) != CONTENT_ROWS:
        raise ExperimentalBaselineError("target verification contains duplicate IDs")
    for index, (actual_row, expected_row) in enumerate(zip(actual, expected, strict=True)):
        if set(actual_row) != set(expected_row):
            raise ExperimentalBaselineError(f"target verification row {index} fields mismatch")
        actual_attributes = {key: value for key, value in actual_row.items() if key != "vector"}
        expected_attributes = {key: value for key, value in expected_row.items() if key != "vector"}
        if actual_attributes != expected_attributes:
            raise ExperimentalBaselineError(f"target verification row {index} attributes mismatch")
        # The exact f16 namespace schema may quantize float32 inference values.
        # Compatibility therefore requires stable normalized vector shape, not
        # byte equality with the pre-write float32 values.
        _validate_vector(actual_row.get("vector"), label=f"verified content row {index}")


def _card_read(
    ledger: _Ledger,
    resource: NamespaceResource,
    slot: int,
    *,
    allow_missing: bool,
) -> NamespaceCard | None:
    row_id = remote_card_id(TARGET_NAMESPACE)
    response = ledger.invoke(
        slot,
        lambda: resource.query(
            rank_by=("id", "asc"), top_k=2, filters=("id", "Eq", row_id),
            include_attributes=list(REMOTE_CARD_ATTRIBUTES), vector_encoding="float",
            consistency=dict(STRONG_CONSISTENCY),
        ),
    )
    rows = response["rows"]
    if len(rows) > 1:
        raise ExperimentalBaselineError("exact card read returned duplicate rows")
    if not rows:
        if allow_missing:
            return None
        raise ExperimentalBaselineError("exact card read returned no row")
    return card_from_remote_row(rows[0], region=REGION)


def _validate_content_metadata(payload: Mapping[str, Any], *, allow_absent: bool) -> None:
    if payload.get("namespace_absent") is True:
        if allow_absent:
            return
        raise ExperimentalBaselineError("target namespace unexpectedly absent")
    schema = payload.get("schema")
    if _normalize_content_schema(schema) != _normalize_content_schema({
        "id": {"type": "string", "filterable": True}, **CONTENT_SCHEMA,
    }):
        raise ExperimentalBaselineError("target namespace schema mismatch")
    if payload.get("distance_metric") != DISTANCE_METRIC:
        raise ExperimentalBaselineError("target namespace distance_metric is missing or mismatched")


def _normalize_content_schema(value: object) -> JsonObject:
    if not isinstance(value, Mapping):
        raise ExperimentalBaselineError("target namespace metadata is missing schema")
    normalized: JsonObject = {}
    for raw_name, raw_config in value.items():
        name = str(raw_name)
        config = {"type": raw_config} if isinstance(raw_config, str) else raw_config
        if not isinstance(config, Mapping) or not isinstance(config.get("type"), str):
            raise ExperimentalBaselineError("target namespace schema contains an invalid attribute")
        allowed = {
            "type", "filterable", "full_text_search", "regex", "glob", "fuzzy",
            "sparse_knn", "ann", "embed",
        }
        unknown = set(config) - allowed
        if unknown:
            raise ExperimentalBaselineError(
                f"target namespace schema attribute {name!r} has unknown config keys"
            )
        type_name = str(config["type"])
        result: JsonObject = {
            "type": type_name,
            "filterable": config.get("filterable", name != "vector"),
        }
        for flag in ("full_text_search", "regex", "glob", "fuzzy", "sparse_knn"):
            if config.get(flag) not in (None, False):
                result[flag] = config[flag]
        ann = config.get("ann")
        if ann is True:
            result["ann"] = {"distance_metric": DISTANCE_METRIC}
        elif ann not in (None, False):
            if not isinstance(ann, Mapping):
                raise ExperimentalBaselineError("target namespace schema has invalid ANN config")
            result["ann"] = dict(ann)
        if config.get("embed") is not None:
            result["embed"] = config["embed"]
        normalized[name] = result
    implicit_id = normalized.pop("id", None)
    if implicit_id != {"type": "string", "filterable": True}:
        raise ExperimentalBaselineError("target namespace implicit id schema mismatch")
    return normalized


def _require_write_response(
    response: Mapping[str, Any], *, expected_rows: int, expected_ids: Sequence[str] | None = None
) -> None:
    if response.get("rows_affected") != expected_rows:
        raise ExperimentalBaselineError("successful write rows_affected mismatch")
    if expected_ids is not None:
        raw_ids = response.get("upserted_ids")
        if not isinstance(raw_ids, list) or raw_ids != list(expected_ids):
            raise ExperimentalBaselineError("successful write affected IDs mismatch")


def _capture_response(
    attempt: Attempt, payload: JsonObject, *, require_rows_affected: bool
) -> list[str]:
    errors: list[str] = []
    attempt.rows_affected_present = "rows_affected" in payload
    rows_affected = payload.get("rows_affected")
    if attempt.rows_affected_present and (type(rows_affected) is not int or rows_affected < 0):
        errors.append("rows_affected must be an exact non-negative integer")
    else:
        attempt.rows_affected = rows_affected if attempt.rows_affected_present else None
    if require_rows_affected and not attempt.rows_affected_present:
        errors.append("successful write omitted rows_affected")

    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        errors.append("response rows must be an array")
    else:
        attempt.returned_rows = len(rows)
        if len(rows) > attempt.slot.returned_rows_ceiling:
            errors.append("response exceeded the slot returned-row ceiling")

    attempt.billing_present = "billing" in payload
    billing = payload.get("billing")
    if attempt.billing_present:
        if not isinstance(billing, Mapping):
            errors.append("billing must be an object when present")
        else:
            attempt.billing = _redact_mapping(billing)

    attempt.metrics_present = "metrics" in payload
    metrics = payload.get("metrics")
    if attempt.metrics_present:
        if not isinstance(metrics, Mapping):
            errors.append("metrics must be an object when present")
        else:
            attempt.metrics = _redact_mapping(metrics)

    identity_key = (
        "request_id" if "request_id" in payload
        else "request_identity" if "request_identity" in payload
        else None
    )
    attempt.request_identity_present = identity_key is not None
    if identity_key is not None:
        identity = payload[identity_key]
        if not isinstance(identity, str) or not identity:
            errors.append("request identity must be a non-empty string")
        else:
            attempt.request_identity = "sha256:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()

    attempt.affected_ids_present = "upserted_ids" in payload
    affected_ids = payload.get("upserted_ids")
    if attempt.affected_ids_present:
        if not isinstance(affected_ids, list) or any(not isinstance(item, str) for item in affected_ids):
            errors.append("upserted_ids must be an array of strings")
        else:
            attempt.affected_ids = list(affected_ids)
    return errors


def _capture_attached_error_accounting(attempt: Attempt, exc: BaseException) -> list[str]:
    """Retain all parseable response/metrics accounting attached to an error."""

    payload: JsonObject = {}
    errors: list[str] = []
    for attribute in ("response", "body"):
        attached = getattr(exc, attribute, None)
        if attached is None:
            continue
        try:
            payload.update(_plain_response(attached))
        except ExperimentalBaselineError as parse_error:
            errors.append(f"{attribute}: {parse_error}")
    metrics = getattr(exc, "metrics", None)
    if metrics is not None:
        try:
            metrics_payload = _plain_response(metrics)
            payload.setdefault("metrics", metrics_payload)
            for key, value in metrics_payload.items():
                payload.setdefault(key, value)
        except ExperimentalBaselineError as parse_error:
            errors.append(f"metrics: {parse_error}")
    for attribute, field_name in (
        ("billing", "billing"), ("request_id", "request_id"),
        ("request_identity", "request_identity"), ("rows_affected", "rows_affected"),
    ):
        value = getattr(exc, attribute, None)
        if value is not None:
            payload.setdefault(field_name, _plain_value(value))
    if payload:
        errors.extend(_capture_response(attempt, payload, require_rows_affected=False))
    return errors


def _plain_response(value: object) -> JsonObject:
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    json_method = getattr(value, "json", None)
    if callable(json_method):
        try:
            result = json_method()
        except Exception:
            result = None
        if isinstance(result, Mapping):
            return {str(key): _plain_value(item) for key, item in result.items()}
    for method_name in ("to_dict", "model_dump"):
        method = getattr(value, method_name, None)
        if callable(method):
            result = method()
            if isinstance(result, Mapping):
                return {str(key): _plain_value(item) for key, item in result.items()}
    raise ExperimentalBaselineError("provider response must be an object")


def _plain_value(value: object) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain_value(item) for item in value]
    for method_name in ("to_dict", "model_dump"):
        method = getattr(value, method_name, None)
        if callable(method):
            return _plain_value(method())
    if hasattr(value, "__dict__"):
        return {
            key: _plain_value(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return value


def _redact_mapping(value: Mapping[object, object]) -> JsonObject:
    safe: JsonObject = {}
    for raw_key, item in value.items():
        key = str(raw_key)[:80]
        if re.search(r"secret|token|credential|api.?key|header|account", key, re.IGNORECASE):
            safe[key] = "<redacted>"
        elif item is None or isinstance(item, (bool, int)):
            safe[key] = item
        elif isinstance(item, float):
            safe[key] = item if math.isfinite(item) else "<redacted>"
        elif isinstance(item, Mapping):
            safe[key] = _redact_mapping(item)
        elif isinstance(item, (list, tuple)):
            safe[key] = [
                child if child is None or isinstance(child, (bool, int, float)) else "<redacted>"
                for child in item[:100]
            ]
        else:
            safe[key] = "<redacted>"
    return safe


def _validate_vector(value: object, *, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != ROUTING_DIMENSIONS:
        raise ExperimentalBaselineError(f"{label} vector must have exactly 384 dimensions")
    vector: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ExperimentalBaselineError(f"{label} vector must contain finite numbers")
        number = float(item)
        if not math.isfinite(number):
            raise ExperimentalBaselineError(f"{label} vector must contain finite numbers")
        vector.append(number)
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0 or abs(norm - 1.0) > 1e-4:
        raise ExperimentalBaselineError(f"{label} vector must be normalized")
    return vector


def _safe_error(exc: BaseException) -> str:
    name = re.sub(r"[^A-Za-z0-9_.-]", "_", exc.__class__.__name__)[:80]
    status = getattr(exc, "status_code", None)
    suffix = f",status={status}" if type(status) is int else ""
    if isinstance(exc, TimeoutError) or "timeout" in name.casefold():
        suffix += ",timeout"
    return name + suffix
