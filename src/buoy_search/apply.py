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
from buoy_search.plan_artifacts import (
    GENERIC_SITE_TURBOPUFFER_SCHEMA,
    MAX_PLAN_JSON_BYTES,
    PLAN_SCHEMA_VERSION,
    ChunkManifestRecord,
    ManifestDocument,
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


class ApplyPlanError(ValueError):
    """Raised when a saved plan cannot be safely applied."""


@dataclass(frozen=True)
class VerifiedApplyPlan:
    """Fully verified schema-v2 delta plus its exact current baseline."""

    plan_path: Path
    plan: JsonObject
    manifest: ManifestDocument
    chunks_by_row_id: dict[str, ChunkManifestRecord]
    state: AppliedState
    diff: IncrementalPlanDiff
    state_root: Path
    upsert_rows: tuple[JsonObject, ...]
    stale_rows: tuple[JsonObject, ...]
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
    """Return the newest summary-qualified schema-v2 plan without opening deltas."""

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
            f"No supported schema-v2 plan.json files found under {search_root}; "
            "run `buoy plan <source>` or pass --plan."
        )
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path)))


def load_verified_apply_plan(*, plan_path: Path, namespace: str | None, state_root: Path) -> VerifiedApplyPlan:
    """Fully verify one compact delta and its exact applied-state baseline."""

    if not plan_path.exists():
        raise ApplyPlanError(f"Plan file not found: {plan_path}")
    if plan_path.is_symlink() or not plan_path.is_file():
        raise ApplyPlanError("Plan file must be a regular schema-v2 plan.json.")
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
        raise ApplyPlanError(f"Unsupported or invalid schema-v2 plan: {exc}") from exc
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
            api_calls_occurred=bool(rows_written or rows_deleted),
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
        return {
            **summary,
            "receipt_schema_version": 1,
            "apply_id": next_state.last_apply_id,
            "source": verified.plan["source"],
            "content_applied": True,
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
