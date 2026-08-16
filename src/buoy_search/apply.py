"""Apply helpers for focused source-index plans.

Preflight verification is local-only: it reads plan artifacts and local state,
but does not read credentials, load embedding models, or call turbopuffer.
Approved apply is explicit and writes only fully verified rows from the exact
baseline-bound compact delta.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shlex
import stat
import tempfile
import time
from typing import Any, Callable
import unicodedata

from buoy_search.applied_state import (
    ROW_STATUS_ACTIVE,
    ROW_STATUS_RETAINED_STALE,
    APPLIED_STATE_SCHEMA_VERSION,
    ApplyRunSummary,
    AppliedState,
    AppliedStateError,
    AppliedStateRow,
    acquire_namespace_apply_lock,
    applied_state_paths,
    build_applied_state,
    load_applied_state,
    save_applied_state,
)
from buoy_search.config import DEFAULT_REGION, RuntimeConfig
from buoy_search.chunker import (
    VECTOR_DIMENSIONS,
    SentenceTransformerEmbedder,
    TurbopufferWriter,
    batched,
)
from buoy_search.catalog import (
    MAX_ROUTING_EVIDENCE,
    CardFields,
    CatalogError,
    GeneratedSemantics,
    NamespaceCard,
    bounded_routing_passages,
    generated_semantics,
    prepare_card,
)
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V3,
    CompatibilityContract,
    RemoteCatalogError,
    create_client,
    create_remote_cards,
    read_remote_catalog,
    remote_catalog_resource,
    update_remote_card,
)
from buoy_search.plan_artifacts import (
    GENERIC_SITE_TURBOPUFFER_SCHEMA,
    MAX_PLAN_JSON_BYTES,
    PLAN_SCHEMA_VERSION,
    ChunkManifestRecord,
    ManifestDocument,
    VerifiedDeltaPlan,
    applied_state_descriptor,
    build_generic_site_row,
    state_path_for_site,
    validate_plan_document,
    verify_plan_artifacts,
)
from buoy_search.plan_diff import (
    DesiredChunkDiffRecord,
    IncrementalPlanDiff,
    StateRowDiffRecord,
)
from buoy_search.retriever import ranking_defaults_for_namespace

JsonObject = dict[str, Any]
DEFAULT_APPLY_PLAN_SEARCH_ROOT = Path("artifacts/site-crawls")
REMOTE_CATALOG_CLIENT_FACTORY = create_client


class ApplyPlanError(ValueError):
    """Raised when a saved plan cannot be safely applied."""


class CatalogRegistrationPartialSuccess(RuntimeError):
    """Content/local state committed, but the routing card did not."""

    def __init__(self, message: str, summary: JsonObject) -> None:
        super().__init__(message)
        self.summary = summary


class _CatalogRegistrationAttemptError(RuntimeError):
    """Internal registration failure plus whether a provider call was attempted."""

    def __init__(
        self,
        message: str,
        *,
        api_calls_occurred: bool,
        repair_command: str,
        card_write_attempted: bool = False,
    ) -> None:
        super().__init__(message)
        self.api_calls_occurred = api_calls_occurred
        self.repair_command = repair_command
        self.card_write_attempted = card_write_attempted


@dataclass(frozen=True)
class VerifiedApplyPlan:
    """Fully verified schema-v3 delta plus its exact current baseline."""

    plan_path: Path
    plan: JsonObject
    manifest: ManifestDocument
    chunks_by_row_id: dict[str, ChunkManifestRecord]
    state: AppliedState
    diff: IncrementalPlanDiff
    state_root: Path
    upsert_rows: tuple[JsonObject, ...]
    stale_rows: tuple[JsonObject, ...]
    routing_prototypes: tuple[JsonObject, ...]
    plan_directory_device: int
    plan_directory_inode: int


@dataclass(frozen=True)
class ApplyCleanupBinding:
    """Internal exact directory binding captured by successful under-lock apply."""

    plan_path: Path
    plan_id: str
    artifact_hash: str
    namespace: str
    directory_device: int
    directory_inode: int


@dataclass(frozen=True)
class ApplyResult:
    """Result from preflight or approved apply."""

    summary: JsonObject


def _state_changed() -> ApplyPlanError:
    return ApplyPlanError("Applied state changed after this plan was created; run buoy plan again.")


def _directory_observation(descriptor: int) -> tuple[int, int, int, int]:
    observed = os.fstat(descriptor)
    if not stat.S_ISDIR(observed.st_mode):
        raise _state_changed()
    return observed.st_dev, observed.st_ino, observed.st_mtime_ns, observed.st_ctime_ns


def _file_observation(descriptor: int) -> tuple[int, int, int, int, int]:
    observed = os.fstat(descriptor)
    if not stat.S_ISREG(observed.st_mode):
        raise _state_changed()
    return (
        observed.st_dev,
        observed.st_ino,
        observed.st_size,
        observed.st_mtime_ns,
        observed.st_ctime_ns,
    )


def _empty_applied_state(*, site_id: str, namespace: str, base_url: str) -> AppliedState:
    return AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=site_id,
        namespace=namespace,
        base_url=base_url,
        updated_at="",
        last_plan_id="",
        last_apply_id="",
        rows=[],
        first_apply=True,
    )


def _load_inode_bound_applied_state(
    *,
    database_path: Path,
    parent_fd: int,
    site_id: str,
    namespace: str,
    base_url: str,
) -> AppliedState:
    """Load an exact private snapshot copied from one no-follow file descriptor."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        database_fd = os.open(database_path.name, flags, dir_fd=parent_fd)
    except OSError as exc:
        raise _state_changed() from exc
    try:
        directory_before = _directory_observation(parent_fd)
        file_before = _file_observation(database_fd)
        with tempfile.TemporaryDirectory(prefix="buoy-state-snapshot-") as tmp:
            snapshot_root = Path(tmp)
            snapshot_path = applied_state_paths(
                site_id=site_id, namespace=namespace, state_root=snapshot_root
            ).database_path
            snapshot_path.parent.mkdir(parents=True)
            with snapshot_path.open("xb") as target:
                while True:
                    block = os.read(database_fd, 1024 * 1024)
                    if not block:
                        break
                    target.write(block)
                target.flush()
                os.fsync(target.fileno())
            state = load_applied_state(
                site_id=site_id,
                namespace=namespace,
                base_url=base_url,
                state_root=snapshot_root,
            )
        file_after = _file_observation(database_fd)
        try:
            path_after = os.stat(database_path.name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise _state_changed() from exc
        if (
            file_before != file_after
            or not stat.S_ISREG(path_after.st_mode)
            or (path_after.st_dev, path_after.st_ino) != file_before[:2]
            or _directory_observation(parent_fd) != directory_before
        ):
            raise _state_changed()
        return state
    finally:
        os.close(database_fd)


def _load_stable_applied_state(
    *, site_id: str, namespace: str, base_url: str, state_root: Path
) -> tuple[AppliedState, bool]:
    """Load state from an inode-bound snapshot and detect path ABA replacement."""

    database_path = applied_state_paths(
        site_id=site_id, namespace=namespace, state_root=state_root
    ).database_path
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        parent_fd = os.open(database_path.parent, flags)
    except FileNotFoundError:
        return _empty_applied_state(
            site_id=site_id, namespace=namespace, base_url=base_url
        ), False
    except OSError as exc:
        raise _state_changed() from exc
    try:
        directory_before = _directory_observation(parent_fd)
        try:
            observed = os.stat(database_path.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            state = _empty_applied_state(
                site_id=site_id, namespace=namespace, base_url=base_url
            )
            try:
                os.stat(database_path.name, dir_fd=parent_fd, follow_symlinks=False)
            except FileNotFoundError:
                if _directory_observation(parent_fd) != directory_before:
                    raise _state_changed()
                return state, False
            except OSError as exc:
                raise _state_changed() from exc
            raise _state_changed()
        except OSError as exc:
            raise _state_changed() from exc
        if not stat.S_ISREG(observed.st_mode):
            raise _state_changed()
        state = _load_inode_bound_applied_state(
            database_path=database_path,
            parent_fd=parent_fd,
            site_id=site_id,
            namespace=namespace,
            base_url=base_url,
        )
        return state, True
    finally:
        os.close(parent_fd)


def discover_latest_plan_path(search_root: Path = DEFAULT_APPLY_PLAN_SEARCH_ROOT) -> Path:
    """Return the newest summary-qualified schema-v3 plan without opening deltas."""

    if not search_root.exists():
        raise ApplyPlanError(f"No plan search root found: {search_root}; pass --plan explicitly.")
    candidates: list[Path] = []
    for path in search_root.rglob("plan.json"):
        try:
            if path.is_symlink() or not path.is_file():
                continue
            if path.stat().st_size > MAX_PLAN_JSON_BYTES:
                continue
            plan = json.loads(path.read_text(encoding="utf-8"))
            validate_plan_document(plan)
            delta = path.with_name("delta.duckdb")
            if delta.is_symlink() or not delta.is_file():
                continue
            candidates.append(path)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
            continue
    if not candidates:
        raise ApplyPlanError(
            f"No supported schema-v3 plan.json files found under {search_root}; "
            "run `buoy plan <source>` or pass --plan."
        )
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path)))


def _verify_plan_file(plan_path: Path) -> tuple[VerifiedDeltaPlan, os.stat_result]:
    """Verify an exact schema-v3 artifact and bind its directory identity."""

    _require_safe_diagnostic_path(plan_path.absolute(), label="Plan file")
    if not plan_path.exists():
        raise ApplyPlanError(f"Plan file not found: {plan_path}")
    if plan_path.is_symlink() or not plan_path.is_file():
        raise ApplyPlanError("Plan file must be a regular schema-v3 plan.json.")
    plan_directory = plan_path.parent
    try:
        directory_before = plan_directory.lstat()
        if not stat.S_ISDIR(directory_before.st_mode):
            raise ApplyPlanError("Plan directory must be a regular directory.")
        if plan_path.stat().st_size <= MAX_PLAN_JSON_BYTES:
            header = json.loads(plan_path.read_text(encoding="utf-8"))
            if isinstance(header, dict) and header.get("schema_version") != PLAN_SCHEMA_VERSION:
                raise ApplyPlanError(
                    f"Unsupported plan schema_version {header.get('schema_version')!r}; "
                    f"expected {PLAN_SCHEMA_VERSION}."
                )
        verified = verify_plan_artifacts(plan_path)
        directory_after = plan_directory.lstat()
        if not stat.S_ISDIR(directory_after.st_mode) or (
            directory_before.st_dev,
            directory_before.st_ino,
        ) != (
            directory_after.st_dev,
            directory_after.st_ino,
        ):
            raise ApplyPlanError("Plan directory changed during verification.")
    except ApplyPlanError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise ApplyPlanError(f"Unsupported or invalid schema-v3 plan: {exc}") from exc
    return verified, directory_before


def _require_safe_diagnostic_path(path: Path, *, label: str) -> None:
    """Keep executable repair diagnostics free of terminal-control paths."""

    unsafe_categories = {"Cc", "Cf", "Cs", "Zl", "Zp"}
    if any(unicodedata.category(character) in unsafe_categories for character in str(path)):
        raise ApplyPlanError(f"{label} path contains unsupported control characters.")


def load_verified_apply_plan(*, plan_path: Path, namespace: str | None, state_root: Path) -> VerifiedApplyPlan:
    """Fully verify one compact delta and its exact applied-state baseline."""

    _require_safe_diagnostic_path(state_root.absolute(), label="State root")
    verified, directory_before = _verify_plan_file(plan_path)
    plan = verified.plan
    resolved_namespace = str(plan["namespace"])
    if namespace is not None and resolved_namespace != namespace:
        raise ApplyPlanError(
            f"namespace mismatch: plan has {resolved_namespace!r}, argument has {namespace!r}"
        )
    source_uri = str(plan["source"]["uri"])
    site_id = str(plan["site_id"])
    state, state_present = _load_stable_applied_state(
        site_id=site_id,
        namespace=resolved_namespace,
        base_url=source_uri,
        state_root=state_root,
    )
    current_baseline = applied_state_descriptor(state, present=state_present)
    if current_baseline != plan["applied_state"]:
        raise ApplyPlanError(
            "Applied state changed after this plan was created; run buoy plan again."
        )
    _validate_delta_against_state(verified.upsert_rows, verified.stale_rows, state)
    _validate_routing_prototypes_against_state(
        verified.routing_prototypes,
        verified.upsert_rows,
        state,
    )
    chunks = tuple(_chunk_from_delta(row) for row in verified.upsert_rows)
    chunks_by_row_id = {chunk.row_id: chunk for chunk in chunks}
    diff = _diff_from_delta(plan, verified.upsert_rows, verified.stale_rows)
    manifest = ManifestDocument(
        schema_version=PLAN_SCHEMA_VERSION,
        site_id=site_id,
        base_url=source_uri,
        namespace=resolved_namespace,
        namespace_candidate=str(plan["namespace_candidate"]),
        pages=[],
        chunks=list(chunks),
    )
    return VerifiedApplyPlan(
        plan_path=plan_path,
        plan=plan,
        manifest=manifest,
        chunks_by_row_id=chunks_by_row_id,
        state=state,
        diff=diff,
        state_root=state_root,
        upsert_rows=verified.upsert_rows,
        stale_rows=verified.stale_rows,
        routing_prototypes=verified.routing_prototypes,
        plan_directory_device=directory_before.st_dev,
        plan_directory_inode=directory_before.st_ino,
    )


def load_verified_catalog_repair_plan(
    *,
    plan_path: Path,
    namespace: str,
    state_root: Path,
    apply_id: str,
) -> VerifiedApplyPlan:
    """Verify a retained plan against the state committed by its partial apply."""

    _require_safe_diagnostic_path(state_root.absolute(), label="State root")
    verified, directory_before = _verify_plan_file(plan_path)
    plan = verified.plan
    resolved_namespace = str(plan["namespace"])
    if resolved_namespace != namespace:
        raise ApplyPlanError(
            f"namespace mismatch: plan has {resolved_namespace!r}, argument has {namespace!r}"
        )
    source_uri = str(plan["source"]["uri"])
    site_id = str(plan["site_id"])
    state, state_present = _load_stable_applied_state(
        site_id=site_id,
        namespace=resolved_namespace,
        base_url=source_uri,
        state_root=state_root,
    )
    if not state_present:
        raise ApplyPlanError("Catalog repair requires the committed applied state.")
    if state.last_plan_id != str(plan["plan_id"]) or state.last_apply_id != apply_id:
        raise ApplyPlanError(
            "Applied state no longer matches this plan/apply repair authority."
        )
    current_rows = {row.row_id: row for row in state.rows}
    for prototype in verified.routing_prototypes:
        row = current_rows.get(str(prototype["row_id"]))
        if (
            row is None
            or row.status != ROW_STATUS_ACTIVE
            or row.canonical_url != str(prototype["canonical_url"])
            or row.chunk_hash != str(prototype["chunk_hash"])
        ):
            raise ApplyPlanError(
                "Retained routing prototype no longer matches committed applied state."
            )
    chunks = tuple(_chunk_from_delta(row) for row in verified.upsert_rows)
    manifest = ManifestDocument(
        schema_version=PLAN_SCHEMA_VERSION,
        site_id=site_id,
        base_url=source_uri,
        namespace=resolved_namespace,
        namespace_candidate=str(plan["namespace_candidate"]),
        pages=[],
        chunks=list(chunks),
    )
    return VerifiedApplyPlan(
        plan_path=plan_path,
        plan=plan,
        manifest=manifest,
        chunks_by_row_id={chunk.row_id: chunk for chunk in chunks},
        state=state,
        diff=_diff_from_delta(plan, verified.upsert_rows, verified.stale_rows),
        state_root=state_root,
        upsert_rows=verified.upsert_rows,
        stale_rows=verified.stale_rows,
        routing_prototypes=verified.routing_prototypes,
        plan_directory_device=directory_before.st_dev,
        plan_directory_inode=directory_before.st_ino,
    )


def _validate_delta_against_state(
    upserts: tuple[JsonObject, ...], stale_rows: tuple[JsonObject, ...], state: AppliedState
) -> None:
    baseline = {row.row_id: row for row in state.rows}
    for raw in stale_rows:
        row = baseline.get(str(raw["row_id"]))
        expected = None if row is None else {
            "canonical_url": row.canonical_url,
            "page_hash": row.page_hash,
            "chunk_hash": row.chunk_hash,
            "embedding_text_hash": row.embedding_text_hash,
            "prior_plan_id": row.plan_id,
            "prior_applied_at": row.applied_at,
            "prior_status": row.status,
        }
        actual = {key: raw[key] for key in (
            "canonical_url", "page_hash", "chunk_hash", "embedding_text_hash",
            "prior_plan_id", "prior_applied_at", "prior_status",
        )}
        if expected != actual:
            raise ApplyPlanError("Verified stale delta does not match applied-state baseline.")
    active_rows = tuple(row for row in state.rows if row.status == ROW_STATUS_ACTIVE)
    for raw in upserts:
        row = baseline.get(str(raw["row_id"]))
        action = raw["action"]
        if action == "reactivate_retained_stale":
            if row is None or row.status != ROW_STATUS_RETAINED_STALE:
                raise ApplyPlanError("Verified reactivation does not match applied-state baseline.")
        elif action == "changed":
            same_active_row_changed = (
                row is not None
                and row.status == ROW_STATUS_ACTIVE
                and row.embedding_text_hash != str(raw["embedding_text_hash"])
            )
            same_active_url = row is None and any(
                candidate.canonical_url == str(raw["canonical_url"])
                for candidate in active_rows
            )
            if not same_active_row_changed and not same_active_url:
                raise ApplyPlanError("Verified changed row has no active applied-state lineage.")
        elif action == "new":
            if row is not None and row.status in {ROW_STATUS_ACTIVE, ROW_STATUS_RETAINED_STALE}:
                raise ApplyPlanError("Verified new row already exists in applied-state baseline.")
            if any(
                candidate.canonical_url == str(raw["canonical_url"])
                for candidate in active_rows
            ):
                raise ApplyPlanError("Verified new row has active canonical-URL lineage.")


def _validate_routing_prototypes_against_state(
    routing_prototypes: tuple[JsonObject, ...],
    upserts: tuple[JsonObject, ...],
    state: AppliedState,
) -> None:
    """Bind unchanged prototype provenance to the exact applied-state baseline."""

    upsert_ids = {str(row["row_id"]) for row in upserts}
    baseline = {row.row_id: row for row in state.rows}
    for prototype in routing_prototypes:
        row_id = str(prototype["row_id"])
        if row_id in upsert_ids:
            continue
        row = baseline.get(row_id)
        if (
            row is None
            or row.status != ROW_STATUS_ACTIVE
            or row.canonical_url != str(prototype["canonical_url"])
            or row.chunk_hash != str(prototype["chunk_hash"])
        ):
            raise ApplyPlanError(
                "Verified routing prototype does not match applied-state baseline."
            )


def _chunk_from_delta(row: JsonObject) -> ChunkManifestRecord:
    return ChunkManifestRecord(
        row_id=str(row["row_id"]),
        row_id_candidate=str(row["row_id_candidate"]),
        site_id=str(row["site_id"]),
        duplicate_ordinal=int(row["duplicate_ordinal"]),
        canonical_url=str(row["canonical_url"]),
        page_content_path=str(row["source_path"]),
        page_hash=str(row["page_hash"]),
        chunk_hash=str(row["chunk_hash"]),
        embedding_text_hash=str(row["embedding_text_hash"]),
        title=str(row["title"]),
        section_path=str(row["section_path"]),
        chunk_index=int(row["chunk_index"]),
        content=str(row["content"]),
        content_preview=str(row["content"])[:240].replace("\n", " "),
        doc_kind=str(row["doc_kind"]),
        tags=[str(value) for value in row["tags_json"]],
        source_metadata={str(key): str(value) for key, value in row["source_metadata_json"].items()},
    )


def _diff_from_delta(
    plan: JsonObject,
    upserts: tuple[JsonObject, ...],
    stale_rows: tuple[JsonObject, ...],
) -> IncrementalPlanDiff:
    summary = plan["diff"]
    desired = [
        DesiredChunkDiffRecord(
            row_id=str(row["row_id"]),
            canonical_url=str(row["canonical_url"]),
            page_hash=str(row["page_hash"]),
            chunk_hash=str(row["chunk_hash"]),
            embedding_text_hash=str(row["embedding_text_hash"]),
            section_path=str(row["section_path"]),
            chunk_index=int(row["chunk_index"]),
            action=str(row["action"]),  # type: ignore[arg-type]
        )
        for row in upserts
    ]
    stale = [
        StateRowDiffRecord(
            row_id=str(row["row_id"]),
            canonical_url=str(row["canonical_url"]),
            page_hash=str(row["page_hash"]),
            chunk_hash=str(row["chunk_hash"]),
            embedding_text_hash=str(row["embedding_text_hash"]),
            plan_id=str(row["prior_plan_id"]),
            applied_at=str(row["prior_applied_at"]),
            status=str(row["prior_status"]),
            reason=str(row["reason"]),
        )
        for row in stale_rows
    ]
    return IncrementalPlanDiff(
        first_apply=bool(summary["first_apply"]),
        pages_added=int(summary["pages_added"]),
        pages_changed=int(summary["pages_changed"]),
        pages_unchanged=int(summary["pages_unchanged"]),
        pages_removed=int(summary["pages_removed"]),
        chunks_unchanged=int(summary["chunks_unchanged"]),
        chunks_to_embed=int(summary["chunks_to_embed"]),
        rows_to_upsert=int(summary["rows_to_upsert"]),
        stale_rows=int(summary["stale_rows"]),
        retained_stale_rows=int(summary["retained_stale_rows"]),
        unchanged_chunks=[],
        chunks_to_embed_records=desired,
        rows_to_upsert_records=desired,
        stale_row_records=[
            record for record, raw in zip(stale, stale_rows, strict=True)
            if raw["category"] == "stale"
        ],
        retained_stale_row_records=[
            record for record, raw in zip(stale, stale_rows, strict=True)
            if raw["category"] == "retained_stale"
        ],
    )


def verified_source_metadata(verified: VerifiedApplyPlan) -> list[dict[str, str]]:
    """Project catalog metadata solely from the verified plan-level source."""

    source = verified.plan["source"]
    kind = str(source["kind"])
    attrs = source["attributes"]
    if kind == "website":
        return []
    if kind == "github_repo":
        return [
            {
                "source_kind": kind,
                **{
                    key: str(attrs[key])
                    for key in (
                        "repo_full_name",
                        "repo_owner",
                        "repo_name",
                        "repo_ref",
                        "commit_sha",
                    )
                },
            }
        ]
    if kind == "local_file":
        return [
            {
                "source_kind": kind,
                "file_filename": str(attrs["filename"]),
                "file_extension": str(attrs["extension"]),
                "file_sha256": str(attrs["sha256"]),
                "file_source_id": str(attrs["source_id"]),
            }
        ]
    if kind == "pdf":
        return [
            {
                "source_kind": kind,
                "pdf_filename": str(attrs["filename"]),
                "pdf_sha256": str(attrs["sha256"]),
                "pdf_source_id": str(attrs["source_id"]),
            }
        ]
    return [
        {
            "source_kind": kind,
            "database_backend": str(attrs["database_backend"]),
            "database_source_id": str(attrs["database_source_id"]),
            "database_relation": str(attrs["database_relation"]),
        }
    ]


def _generated_card_inputs(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str,
) -> tuple[GeneratedSemantics, dict[str, object]]:
    semantics = generated_semantics(
        base_url=str(verified.plan["source"]["uri"]),
        site_id=str(verified.plan["site_id"]),
        plan_schema_version=int(verified.plan["schema_version"]),
        source_metadata=verified_source_metadata(verified),
    )
    ranking = ranking_defaults_for_namespace(namespace, source_kind=semantics.source_kind)
    return semantics, ranking


def catalog_registration_preview(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str,
) -> JsonObject:
    """Build a credential-, API-, and model-free registration preview."""

    semantics, ranking = _generated_card_inputs(
        verified,
        namespace=namespace,
        region=region,
    )
    return {
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "namespace": namespace,
        "action": "create_or_update_after_content_and_state_commit",
        "remote_catalog_state": "unknown_until_approved",
        "required_catalog_schema_version": REMOTE_SCHEMA_V3,
        "routing_catalog_prerequisite": "exact_schema_v3_reader_first_setup",
        "manual_semantics_preserved": True,
        "enabled_state_preserved": True,
        "routing_prototype_strategy": verified.plan["routing_prototypes"]["strategy"],
        "reviewed_routing_passages": len(verified.routing_prototypes),
        "routing_passage_budget": MAX_ROUTING_EVIDENCE,
        "routing_model_work": "at_most_one_bounded_local_batch_after_approval",
        "generative_model_used": False,
        "source_kind": semantics.source_kind,
        "region": region,
        "vector_dimensions": VECTOR_DIMENSIONS,
        **ranking,
    }


def generated_card_for_apply(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str,
    apply_id: str,
    existing: NamespaceCard | None,
) -> NamespaceCard:
    """Build the persisted post-apply card while preserving operator fields."""

    semantics, ranking = _generated_card_inputs(
        verified,
        namespace=namespace,
        region=region,
    )
    manual = existing is not None and existing.semantic_origin == "manual"
    routing_examples = list(
        existing.routing_examples if existing is not None else []
    )
    routing_passages = bounded_routing_passages(
        routing_examples=routing_examples,
        routing_passages=[
            str(prototype["passage_text"])
            for prototype in verified.routing_prototypes
        ],
    )
    fields = CardFields(
        namespace=namespace,
        enabled=existing.enabled if existing is not None else True,
        source_kind=semantics.source_kind,
        source_uri=semantics.source_uri,
        site_id=str(verified.plan["site_id"]),
        title=existing.title if manual else semantics.title,
        summary=existing.summary if manual else semantics.summary,
        aliases=list(existing.aliases if manual else semantics.aliases),
        tags=list(existing.tags if manual else semantics.tags),
        # Reviewed routing questions are operator-owned prototype authority.
        # Generated refreshes may neither invent them for a new card nor clear
        # them from any existing manual or generated card.
        routing_examples=routing_examples,
        routing_passages=routing_passages,
        semantic_origin="manual" if manual else "generated",
        region=region,
        embedding_model=str(verified.plan["embedding_model"]),
        embedding_precision=str(verified.plan.get("embedding_precision", "float32")),
        plan_schema_version=int(verified.plan["schema_version"]),
        ranking_mode=str(ranking["ranking_mode"]),
        ranking_profile=str(ranking["ranking_profile"]),
        ranking_pool=int(ranking["ranking_pool"]),
        ranking_aggregation=str(ranking["ranking_aggregation"]),
        last_plan_id=str(verified.plan["plan_id"]),
        last_apply_id=apply_id,
    )
    return prepare_card(
        fields,
        existing=existing,
        now=None,
    )


def _catalog_repair_command(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str,
    apply_id: str,
    existing_revision: str | None = None,
) -> str:
    """Return an opaque retained-plan-backed catalog repair command."""

    command = [
        "buoy",
        "catalog",
        "repair-apply",
        "--plan",
        str(verified.plan_path.absolute()),
        "--namespace",
        namespace,
        "--state-root",
        str(verified.state_root.absolute()),
        "--apply-id",
        apply_id,
        "--region",
        region,
    ]
    if existing_revision is None:
        command.append("--expect-absent")
    else:
        command.extend(("--expected-card-revision", existing_revision))
    command.append("--approve")
    return shlex.join(command)


def _catalog_repair_inspect_command(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str,
    apply_id: str,
) -> str:
    """Return a read-only command that can establish a safe repair binding."""

    return shlex.join(
        (
            "buoy",
            "catalog",
            "repair-apply",
            "--plan",
            str(verified.plan_path.absolute()),
            "--namespace",
            namespace,
            "--state-root",
            str(verified.state_root.absolute()),
            "--apply-id",
            apply_id,
            "--region",
            region,
            "--inspect-current",
        )
    )


def _safe_catalog_registration_error(exc: Exception) -> str:
    if isinstance(exc, CatalogError):
        return str(exc)
    return f"catalog registration failed ({exc.__class__.__name__})"


def inspect_apply_catalog_repair(
    verified: VerifiedApplyPlan,
    *,
    config: RuntimeConfig,
    namespace: str,
    apply_id: str,
    api_key: str,
) -> JsonObject:
    """Strong-read exact v3 and return an opaque, revision-bound repair command."""

    try:
        client = REMOTE_CATALOG_CLIENT_FACTORY(
            api_key=api_key,
            region=config.region,
        )
        compatibility = CompatibilityContract(
            region=config.region,
            embedding_model=config.embedding_model,
            embedding_precision=config.embedding_precision,
        )
        snapshot = read_remote_catalog(
            client,
            region=config.region,
            compatibility=compatibility,
        )
        if snapshot.catalog_schema_version != REMOTE_SCHEMA_V3:
            raise RemoteCatalogError(
                "catalog repair inspection requires the separately approved "
                "reader-first routing catalog schema-v3 migration"
            )
        if namespace not in snapshot.live_namespace_ids:
            raise RemoteCatalogError(
                f"applied content namespace {namespace!r} is not live in "
                f"region {config.region!r}"
            )
        existing = next(
            (card for card in snapshot.cards if card.namespace == namespace),
            None,
        )
    except (CatalogError, RemoteCatalogError):
        raise
    except Exception as exc:
        raise RemoteCatalogError(
            "catalog repair inspection failed "
            f"({exc.__class__.__name__})"
        ) from None
    return {
        "catalog_schema_version": snapshot.catalog_schema_version,
        "catalog_snapshot_revision": snapshot.snapshot_revision,
        "catalog_card_revision": (
            existing.card_revision if existing is not None else None
        ),
        "catalog_repair_command": _catalog_repair_command(
            verified,
            namespace=namespace,
            region=config.region,
            apply_id=apply_id,
            existing_revision=(
                existing.card_revision if existing is not None else None
            ),
        ),
    }


def register_apply_catalog_card(
    verified: VerifiedApplyPlan,
    *,
    config: RuntimeConfig,
    namespace: str,
    apply_id: str,
    api_key: str,
    expected_card_revision: str | None = None,
    expect_absent: bool = False,
) -> JsonObject:
    """Conditionally create/update and exactly verify one post-apply card."""

    if expected_card_revision is not None and expect_absent:
        raise ValueError("catalog repair preconditions are mutually exclusive")

    api_calls_occurred = False
    card_write_attempted = False
    # Until an exact-v3 card snapshot has been read, only suggest the retained-
    # plan inspection path. It establishes a revision/absence precondition
    # without assuming anything about unreadable or not-yet-migrated state.
    repair_command = _catalog_repair_inspect_command(
        verified,
        namespace=namespace,
        region=config.region,
        apply_id=apply_id,
    )
    try:
        # Projection can load the pinned local route model, but happens only
        # after content and local state are durably committed by the caller.
        client = REMOTE_CATALOG_CLIENT_FACTORY(api_key=api_key, region=config.region)
        api_calls_occurred = True
        compatibility = CompatibilityContract(
            region=config.region,
            embedding_model=config.embedding_model,
            embedding_precision=config.embedding_precision,
        )
        snapshot = read_remote_catalog(
            client,
            region=config.region,
            compatibility=compatibility,
        )
        if snapshot.catalog_schema_version != REMOTE_SCHEMA_V3:
            raise RemoteCatalogError(
                "schema-v3 plan registration requires the separately approved "
                "reader-first routing catalog schema-v3 migration"
            )
        if namespace not in snapshot.live_namespace_ids:
            raise RemoteCatalogError(
                f"applied content namespace {namespace!r} is not live in region {config.region!r}"
            )
        existing = next(
            (card for card in snapshot.cards if card.namespace == namespace),
            None,
        )
        repair_command = _catalog_repair_command(
            verified,
            namespace=namespace,
            region=config.region,
            apply_id=apply_id,
            existing_revision=(
                existing.card_revision if existing is not None else None
            ),
        )
        precondition_matches = (
            (expect_absent and existing is None)
            or (
                expected_card_revision is not None
                and existing is not None
                and existing.card_revision == expected_card_revision
            )
            or (not expect_absent and expected_card_revision is None)
        )
        # A matching precondition means this invocation will need the fixed
        # catalog namespace for its create/update. Acquire that provider
        # resource before loading the pinned local routing model so an
        # unavailable catalog fails quickly and through the redacted remote
        # boundary. Drift/idempotence checks deliberately skip acquisition:
        # they may prove that no write is needed and must not add a provider
        # call.
        resource = (
            remote_catalog_resource(client) if precondition_matches else None
        )
        card = generated_card_for_apply(
            verified,
            namespace=namespace,
            region=config.region,
            apply_id=apply_id,
            existing=existing,
        )
        routing_projection_reused = bool(
            existing is not None
            and existing.routing_prototype_hash == card.routing_prototype_hash
            and existing.routing_model == card.routing_model
            and existing.routing_model_revision == card.routing_model_revision
            and existing.routing_evidence_vectors == card.routing_evidence_vectors
            and existing.routing_evidence_vectors_hash
            == card.routing_evidence_vectors_hash
        )
        if not precondition_matches:
            # A conditional create/update may have committed before its response
            # was lost. Treat the strongly-read card as success only when every
            # plan/apply-controlled field (including lineage and passage bank)
            # is already exactly what this retained authority would produce.
            if (
                existing is not None
                and existing.last_plan_id == str(verified.plan["plan_id"])
                and existing.last_apply_id == apply_id
                and existing.card_revision == card.card_revision
            ):
                mutation = None
            elif expect_absent:
                raise RemoteCatalogError(
                    "routing card appeared after the failed apply and does not "
                    "match its retained plan/apply authority"
                )
            else:
                raise RemoteCatalogError(
                    "routing card drifted from the failed apply and does not "
                    "match its retained plan/apply authority"
                )
        else:
            assert resource is not None
            card_write_attempted = True
            mutation = (
                create_remote_cards(
                    resource,
                    [card],
                    region=config.region,
                    schema_version=snapshot.catalog_schema_version,
                )
                if existing is None
                else update_remote_card(
                    resource,
                    card,
                    expected_revision=existing.card_revision,
                    region=config.region,
                    schema_version=snapshot.catalog_schema_version,
                )
            )
    except Exception as exc:
        raise _CatalogRegistrationAttemptError(
            _safe_catalog_registration_error(exc),
            api_calls_occurred=api_calls_occurred,
            repair_command=repair_command,
            card_write_attempted=card_write_attempted,
        ) from None

    if mutation is None:
        status = "unchanged"
    elif existing is None:
        status = "created" if mutation.changed else "unchanged"
    else:
        status = "updated" if mutation.changed else "unchanged"
    verified_card = existing if mutation is None else mutation.card or card
    assert verified_card is not None
    return {
        "catalog_registered": True,
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "catalog_mutation_status": status,
        "catalog_card_revision": verified_card.card_revision,
        "catalog_schema_version": snapshot.catalog_schema_version,
        "catalog_bootstrapped": False,
        "catalog_manual_semantics_preserved": bool(
            existing is not None and existing.semantic_origin == "manual"
        ),
        "catalog_enabled_state": verified_card.enabled,
        "routing_passage_count": len(verified_card.routing_passages),
        "routing_projection_reused": routing_projection_reused,
        "routing_embeddings_generated": (
            0
            if routing_projection_reused
            else 1
            + len(verified_card.routing_examples)
            + len(verified_card.routing_passages)
        ),
        "automatic_retrieval_ready": bool(verified_card.enabled),
        "automatic_routing_status": (
            "provisional_ready" if verified_card.enabled else "disabled"
        ),
        "calibrated_singletons_enabled": False,
        "catalog_repair_command": None,
    }


def apply_preflight_summary(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    region: str = DEFAULT_REGION,
    approved: bool = False,
    delete_stale: bool = False,
) -> JsonObject:
    """Return a clear no-write apply summary."""

    return {
        **build_apply_summary(
            verified=verified,
            namespace=namespace,
            region=region,
            approved=approved,
            delete_stale=delete_stale,
            rows_upserted=0,
            embeddings_generated=0,
            rows_deleted=0,
            state_updated=False,
            api_calls_occurred=False,
        ),
        "cancelled": False,
        "confirmation": "not_requested",
        "catalog_registered": False,
        "automatic_retrieval_ready": False,
        "automatic_routing_status": "pending_approved_catalog_registration",
        "calibrated_singletons_enabled": False,
        "catalog_registration": catalog_registration_preview(
            verified,
            namespace=namespace,
            region=region,
        ),
    }


def run_approved_apply(
    verified: VerifiedApplyPlan,
    *,
    config: RuntimeConfig,
    namespace: str,
    batch_size: int,
    embedding_batch_size: int = 32,
    delete_stale: bool = False,
    progress_callback: Callable[[str], None] | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    cleanup_binding_callback: Callable[[ApplyCleanupBinding], None] | None = None,
) -> JsonObject:
    """Reverify under lock, then apply one exact delta to one namespace."""

    def emit_progress(message: str) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(message)
        except Exception:
            return

    def observe_monotonic() -> float | None:
        try:
            return monotonic()
        except Exception:
            return None

    def elapsed_since(started_at: float | None) -> float:
        finished_at = observe_monotonic()
        if started_at is None or finished_at is None:
            return 0.0
        return finished_at - started_at

    apply_started_at = observe_monotonic()
    embedding_seconds = 0.0
    write_seconds = 0.0
    stale_row_ids = stale_row_ids_for_delete(verified)
    if delete_stale and not stale_row_ids:
        raise ApplyPlanError("Cannot run --delete-stale because the recomputed diff has no stale rows.")

    emit_progress("apply: acquiring namespace lock")
    with acquire_namespace_apply_lock(
        site_id=str(verified.plan["site_id"]),
        namespace=namespace,
        state_root=verified.state_root,
    ):
        # Re-read state and recompute the diff under the lock so a process that
        # verified concurrently cannot repeat writes after another apply wins.
        verified = load_verified_apply_plan(
            plan_path=verified.plan_path,
            namespace=namespace,
            state_root=verified.state_root,
        )
        stale_row_ids = stale_row_ids_for_delete(verified)
        if delete_stale and not stale_row_ids:
            raise ApplyPlanError("Cannot run --delete-stale because the recomputed diff has no stale rows.")
        plan_id = str(verified.plan["plan_id"])
        api_key = os.environ.get("TURBOPUFFER_API_KEY")
        if not api_key:
            raise RuntimeError("TURBOPUFFER_API_KEY must be set in the environment for approved apply.")
        applied_at = datetime.now(timezone.utc).isoformat()
        next_state = build_state_after_apply(
            verified, applied_at=applied_at, delete_stale=delete_stale
        )

        rows_to_upsert = [verified.chunks_by_row_id[record.row_id] for record in verified.diff.rows_to_upsert_records]
        rows_written = 0
        rows_deleted = 0
        embeddings_generated = 0
        writer: TurbopufferWriter | None = None
        total_rows = len(rows_to_upsert)
        total_batches = (total_rows + batch_size - 1) // batch_size
        emit_progress(
            "apply: preparing; "
            f"rows={total_rows}; batches={total_batches}; "
            f"embedding_batch={embedding_batch_size}; write_batch={batch_size}"
        )
        if rows_to_upsert or (delete_stale and stale_row_ids):
            writer = TurbopufferWriter(
                config=config,
                api_key=api_key,
                schema=GENERIC_SITE_TURBOPUFFER_SCHEMA,
            )

        if rows_to_upsert:
            embedder = SentenceTransformerEmbedder(
                config.embedding_model, precision=config.embedding_precision
            )
            assert writer is not None
            in_flight: Future[float] | None = None
            in_flight_batch_index = 0
            in_flight_row_count = 0

            def write_rows(rows: list[JsonObject]) -> float:
                write_started_at = observe_monotonic()
                writer.upsert_rows(rows)
                return elapsed_since(write_started_at)

            def finish_in_flight() -> None:
                nonlocal in_flight, rows_written, write_seconds
                if in_flight is None:
                    return
                write_seconds += in_flight.result()
                rows_written += in_flight_row_count
                elapsed_seconds = elapsed_since(apply_started_at)
                emit_progress(
                    "apply: embedding/upserting "
                    f"batches={in_flight_batch_index}/{total_batches}; rows={rows_written}/{total_rows}; "
                    f"elapsed={elapsed_seconds:.1f}s; embedding={embedding_seconds:.1f}s; write={write_seconds:.1f}s"
                )
                in_flight = None

            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="buoy-upsert") as executor:
                try:
                    for batch_index, batch in enumerate(batched(rows_to_upsert, batch_size), start=1):
                        embedding_started_at = observe_monotonic()
                        vectors = embedder.encode(
                            [embedding_text_for_chunk(chunk) for chunk in batch],
                            batch_size=embedding_batch_size,
                        )
                        embedding_seconds += elapsed_since(embedding_started_at)
                        embeddings_generated += len(vectors)
                        rows = [
                            build_generic_site_row(
                                chunk,
                                vector,
                                plan_id=plan_id,
                                applied_at=applied_at,
                            )
                            for chunk, vector in zip(batch, vectors, strict=True)
                        ]
                        finish_in_flight()
                        in_flight_batch_index = batch_index
                        in_flight_row_count = len(rows)
                        in_flight = executor.submit(write_rows, rows)
                    finish_in_flight()
                except BaseException:
                    if in_flight is not None:
                        try:
                            in_flight.result()
                        except BaseException:
                            pass
                    raise

        if delete_stale and stale_row_ids:
            emit_progress(f"apply: deleting stale rows={len(stale_row_ids)}")
            assert writer is not None
            delete_started_at = observe_monotonic()
            writer.delete_rows(stale_row_ids)
            write_seconds += elapsed_since(delete_started_at)
            rows_deleted = len(stale_row_ids)
            emit_progress(
                "apply: deleted stale rows="
                f"{rows_deleted}; elapsed={elapsed_since(apply_started_at):.1f}s; "
                f"embedding={embedding_seconds:.1f}s; write={write_seconds:.1f}s"
            )

        emit_progress("apply: committing local state")
        save_applied_state(
            next_state,
            state_root=verified.state_root,
            apply_run=ApplyRunSummary(
                apply_id=next_state.last_apply_id,
                plan_id=next_state.last_plan_id,
                applied_at=next_state.updated_at,
                rows_upserted=rows_written,
                rows_deleted=rows_deleted,
                retained_stale_rows=sum(row.status == ROW_STATUS_RETAINED_STALE for row in next_state.rows),
            ),
        )

        if cleanup_binding_callback is not None:
            cleanup_binding_callback(
                ApplyCleanupBinding(
                    plan_path=verified.plan_path,
                    plan_id=str(verified.plan["plan_id"]),
                    artifact_hash=str(verified.plan["artifact_hash"]),
                    namespace=str(verified.plan["namespace"]),
                    directory_device=verified.plan_directory_device,
                    directory_inode=verified.plan_directory_inode,
                )
            )

        content_api_calls_occurred = bool(rows_written or rows_deleted)
        summary = build_apply_summary(
            verified=verified,
            namespace=namespace,
            region=config.region,
            approved=True,
            delete_stale=delete_stale,
            rows_upserted=rows_written,
            embeddings_generated=embeddings_generated,
            rows_deleted=rows_deleted,
            state_updated=True,
            api_calls_occurred=content_api_calls_occurred,
            timing={
                "elapsed_seconds": elapsed_since(apply_started_at),
                "embedding_seconds": embedding_seconds,
                "write_seconds": write_seconds,
                "embedding_batch_size": embedding_batch_size,
                "write_batch_size": batch_size,
                "embedding_precision": config.embedding_precision,
                "pipeline_mode": "depth_one",
            },
        )
        receipt = {
            **summary,
            "receipt_schema_version": 1,
            "apply_id": next_state.last_apply_id,
            "source": verified.plan["source"],
            "content_applied": True,
        }
        emit_progress("apply: registering routing card")
        catalog_registration_started_at = observe_monotonic()
        try:
            registration = register_apply_catalog_card(
                verified,
                config=config,
                namespace=namespace,
                apply_id=next_state.last_apply_id,
                api_key=api_key,
            )
        except _CatalogRegistrationAttemptError as exc:
            catalog_registration_seconds = elapsed_since(
                catalog_registration_started_at
            )
            timing = dict(receipt["timing"])
            timing.update(
                {
                    "elapsed_seconds": elapsed_since(apply_started_at),
                    "catalog_registration_seconds": catalog_registration_seconds,
                }
            )
            receipt = {**receipt, "timing": timing}
            api_calls_occurred = (
                content_api_calls_occurred or exc.api_calls_occurred
            )
            partial = {
                **receipt,
                "turbopuffer_api_calls": api_calls_occurred,
                "api_calls_occurred": api_calls_occurred,
                "partial_success": True,
                "catalog_registered": False,
                "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
                "catalog_mutation_status": "failed",
                "catalog_card_write_attempted": exc.card_write_attempted,
                "automatic_retrieval_ready": False,
                "automatic_routing_status": "registration_failed",
                "calibrated_singletons_enabled": False,
                "catalog_error": str(exc),
                "catalog_repair_command": exc.repair_command,
            }
            raise CatalogRegistrationPartialSuccess(
                "Content and local applied state were committed, but routing catalog "
                f"registration failed: {exc}. Repair with: {exc.repair_command}",
                partial,
            ) from None
        catalog_registration_seconds = elapsed_since(
            catalog_registration_started_at
        )
        timing = dict(receipt["timing"])
        timing.update(
            {
                "elapsed_seconds": elapsed_since(apply_started_at),
                "catalog_registration_seconds": catalog_registration_seconds,
            }
        )
        return {
            **receipt,
            "timing": timing,
            "turbopuffer_api_calls": True,
            "api_calls_occurred": True,
            "partial_success": False,
            **registration,
        }


def build_state_after_apply(
    verified: VerifiedApplyPlan,
    *,
    applied_at: str,
    delete_stale: bool = False,
) -> AppliedState:
    """Return the local state ledger after a successful approved apply."""

    upsert_ids = set(verified.chunks_by_row_id)
    stale_ids = {str(row["row_id"]) for row in verified.stale_rows}
    next_rows: dict[str, AppliedStateRow] = {}
    for row in verified.state.rows:
        if row.row_id in upsert_ids:
            continue
        if row.row_id in stale_ids:
            if not delete_stale:
                next_rows[row.row_id] = AppliedStateRow(
                    row_id=row.row_id,
                    canonical_url=row.canonical_url,
                    page_hash=row.page_hash,
                    chunk_hash=row.chunk_hash,
                    embedding_text_hash=row.embedding_text_hash,
                    plan_id=row.plan_id,
                    applied_at=row.applied_at,
                    status=ROW_STATUS_RETAINED_STALE,
                )
            continue
        if row.status in {ROW_STATUS_ACTIVE, ROW_STATUS_RETAINED_STALE}:
            next_rows[row.row_id] = row
    for chunk in verified.chunks_by_row_id.values():
        next_rows[chunk.row_id] = AppliedStateRow(
            row_id=chunk.row_id,
            canonical_url=chunk.canonical_url,
            page_hash=chunk.page_hash,
            chunk_hash=chunk.chunk_hash,
            embedding_text_hash=chunk.embedding_text_hash,
            plan_id=str(verified.plan["plan_id"]),
            applied_at=applied_at,
            status=ROW_STATUS_ACTIVE,
        )
    apply_id = make_apply_id(str(verified.plan["plan_id"]), applied_at)
    return build_applied_state(
        site_id=str(verified.plan["site_id"]),
        namespace=str(verified.plan["namespace"]),
        base_url=str(verified.plan["source"]["uri"]),
        last_plan_id=str(verified.plan["plan_id"]),
        last_apply_id=apply_id,
        rows=[next_rows[row_id] for row_id in sorted(next_rows)],
        updated_at=applied_at,
    )


def build_apply_summary(
    *,
    verified: VerifiedApplyPlan,
    namespace: str,
    region: str,
    approved: bool,
    delete_stale: bool,
    rows_upserted: int,
    embeddings_generated: int,
    rows_deleted: int,
    state_updated: bool,
    api_calls_occurred: bool,
    timing: JsonObject | None = None,
) -> JsonObject:
    diff_summary = verified.diff.summary_dict()
    row_ids_to_delete = stale_row_ids_for_delete(verified) if delete_stale else []
    stale_rows_retained = 0 if delete_stale else verified.diff.stale_rows + verified.diff.retained_stale_rows
    source_kind = {
        "website": "website",
        "github_repo": "github_repo",
        "local_file": "document",
        "pdf": "document",
        "duckdb_relation": "database",
        "bigquery_relation": "database",
        "snowflake_relation": "database",
    }[str(verified.plan["source"]["kind"])]
    ranking = ranking_defaults_for_namespace(namespace, source_kind=source_kind)
    retrieval_commands = build_retrieval_commands(
        namespace=namespace,
        region=region,
        embedding_model=str(verified.plan["embedding_model"]),
        embedding_precision=str(verified.plan.get("embedding_precision", "float32")),
        ranking=ranking,
    )
    summary: JsonObject = {
        "command": "apply",
        "approved": approved,
        "delete_stale": delete_stale,
        "dry_run": not approved,
        "credentials_required": approved,
        "credentials_required_for_approved_apply": True,
        "turbopuffer_api_calls": api_calls_occurred,
        "api_calls_occurred": api_calls_occurred,
        "namespace": namespace,
        "region": region,
        "base_url": str(verified.plan["source"]["uri"]),
        "source": verified.plan["source"],
        "source_kind": source_kind,
        "site_id": str(verified.plan["site_id"]),
        "plan_id": verified.plan["plan_id"],
        "plan_path": str(verified.plan_path),
        "state_backend": "local",
        "state_path": state_path_for_site(str(verified.plan["site_id"]), namespace, state_root=verified.state_root),
        "state_first_apply": verified.state.first_apply,
        "state_updated": state_updated,
        "artifact_hash": verified.plan["artifact_hash"],
        "artifact_verified": True,
        "embedding_model": verified.plan["embedding_model"],
        "embedding_precision": verified.plan.get("embedding_precision", "float32"),
        "vector_dimensions": VECTOR_DIMENSIONS,
        "rows_to_upsert": verified.diff.rows_to_upsert,
        "rows_upserted": rows_upserted,
        "embeddings_to_generate": verified.diff.chunks_to_embed,
        "embeddings_generated": embeddings_generated,
        "routing_prototypes_reviewed": len(verified.routing_prototypes),
        "routing_prototype_strategy": verified.plan["routing_prototypes"]["strategy"],
        "stale_rows": verified.diff.stale_rows,
        "retained_stale_rows": verified.diff.retained_stale_rows,
        "stale_rows_to_delete": len(row_ids_to_delete),
        "stale_row_ids_to_delete": row_ids_to_delete,
        "rows_deleted": rows_deleted,
        "stale_rows_retained": stale_rows_retained,
        "delete_would_run": bool(delete_stale and row_ids_to_delete),
        "ranking": ranking,
        "retrieval_commands": retrieval_commands,
        "diff": diff_summary,
    }
    if timing is not None:
        summary["timing"] = timing
    return summary


def build_retrieval_commands(
    *,
    namespace: str,
    region: str,
    embedding_model: str,
    embedding_precision: str,
    ranking: JsonObject,
) -> JsonObject:
    """Return shell-safe preview/live commands for the applied retrieval contract."""

    live_args = [
        "buoy",
        "retrieve",
        "<query>",
        "--namespace",
        namespace,
        "--region",
        region,
        "--embedding-model",
        embedding_model,
        "--embedding-precision",
        embedding_precision,
        "--ranking-mode",
        str(ranking["ranking_mode"]),
        "--ranking-profile",
        str(ranking["ranking_profile"]).replace("_", "-"),
        "--ranking-pool",
        str(ranking["ranking_pool"]),
        "--ranking-aggregation",
        str(ranking["ranking_aggregation"]).replace("_", "-"),
    ]
    return {
        "preview": shlex.join([*live_args, "--dry-run"]),
        "live": shlex.join(live_args),
    }


def stale_row_ids_for_delete(verified: VerifiedApplyPlan) -> list[str]:
    """Return exact stale row IDs eligible for explicit deletion."""

    row_ids: list[str] = []
    seen: set[str] = set()
    for record in [*verified.diff.stale_row_records, *verified.diff.retained_stale_row_records]:
        if record.row_id in seen:
            continue
        seen.add(record.row_id)
        row_ids.append(record.row_id)
    return row_ids


def embedding_text_for_chunk(chunk: ChunkManifestRecord) -> str:
    context: list[str] = []
    if chunk.title:
        context.append(f"Title: {chunk.title}")
    if chunk.section_path:
        context.append(f"Section: {chunk.section_path}")
    context.append(chunk.content)
    return "\n\n".join(part for part in context if str(part).strip())


def make_apply_id(plan_id: str, applied_at: str) -> str:
    timestamp = applied_at.replace(":", "").replace("+", "Z").replace("-", "")
    return f"apply_{timestamp}_{plan_id[:24]}"
