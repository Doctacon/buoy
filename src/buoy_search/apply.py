"""Apply helpers for generic site RAG plans.

Preflight verification is local-only: it reads plan artifacts and local state,
but does not read credentials, load embedding models, or call turbopuffer.
Approved apply is explicit and writes only rows selected by a freshly recomputed
local diff.
"""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Sequence

from buoy_search.applied_state import (
    ROW_STATUS_ACTIVE,
    ROW_STATUS_RETAINED_STALE,
    ApplyRunSummary,
    AppliedState,
    AppliedStateError,
    AppliedStateRow,
    acquire_namespace_apply_lock,
    build_applied_state,
    load_applied_state,
    save_applied_state,
)
from buoy_search.config import EMBEDDING_PRECISIONS, RuntimeConfig
from buoy_search.chunker import SentenceTransformerEmbedder, TurbopufferWriter, batched
from buoy_search.plan_artifacts import (
    GENERIC_SITE_TURBOPUFFER_SCHEMA,
    PLAN_SCHEMA_VERSION,
    ChunkManifestRecord,
    ManifestDocument,
    build_generic_site_row,
    chunk_jsonl_records,
    dataclass_to_json_object,
    embedding_hash,
    stable_hash,
    state_path_for_site,
)
from buoy_search.plan_diff import IncrementalPlanDiff, PlanDiffError, diff_manifest_against_state

JsonObject = dict[str, Any]
DEFAULT_APPLY_PLAN_SEARCH_ROOT = Path("artifacts/site-crawls")


class ApplyPlanError(ValueError):
    """Raised when a saved plan cannot be safely applied."""


@dataclass(frozen=True)
class VerifiedApplyPlan:
    """Verified local apply inputs before any live work."""

    plan_path: Path
    plan: JsonObject
    manifest: ManifestDocument
    chunks_by_row_id: dict[str, ChunkManifestRecord]
    state: AppliedState
    diff: IncrementalPlanDiff
    state_root: Path


@dataclass(frozen=True)
class ApplyResult:
    """Result from preflight or approved apply."""

    summary: JsonObject


def discover_latest_plan_path(search_root: Path = DEFAULT_APPLY_PLAN_SEARCH_ROOT) -> Path:
    """Return the newest local plan.json under the default artifacts tree."""

    if not search_root.exists():
        raise ApplyPlanError(f"No plan search root found: {search_root}; pass --plan explicitly.")
    candidates = [path for path in search_root.rglob("plan.json") if path.is_file()]
    if not candidates:
        raise ApplyPlanError(f"No plan.json files found under {search_root}; run `buoy plan <url>` or pass --plan.")
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, str(path)))


def load_verified_apply_plan(*, plan_path: Path, namespace: str | None, state_root: Path) -> VerifiedApplyPlan:
    """Load and verify plan artifacts and recompute state diff locally.

    This function is intentionally safe for preflight: it does not read secrets,
    load embeddings, or contact turbopuffer.
    """

    if not plan_path.exists():
        raise ApplyPlanError(f"Plan file not found: {plan_path}")
    plan_dir = plan_path.parent
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        manifest_payload = json.loads((plan_dir / "manifest.json").read_text(encoding="utf-8"))
        chunks_jsonl = (plan_dir / "chunks.jsonl").read_text(encoding="utf-8")
    except json.JSONDecodeError as exc:
        raise ApplyPlanError(f"Could not parse plan artifacts: {exc}") from exc
    except OSError as exc:
        raise ApplyPlanError(f"Could not read plan artifacts: {exc}") from exc

    require_plan_field(plan, "schema_version")
    if int(plan["schema_version"]) != PLAN_SCHEMA_VERSION:
        raise ApplyPlanError(
            f"unsupported plan schema_version {plan['schema_version']}; expected {PLAN_SCHEMA_VERSION}"
        )
    if plan.get("command") != "plan":
        raise ApplyPlanError(f"plan command must be 'plan', found {plan.get('command')!r}")
    require_plan_field(plan, "namespace")
    resolved_namespace = str(plan["namespace"])
    if namespace is not None and resolved_namespace != namespace:
        raise ApplyPlanError(f"namespace mismatch: plan has {plan['namespace']!r}, argument has {namespace!r}")

    manifest = manifest_from_json(manifest_payload)
    if manifest.namespace != resolved_namespace:
        raise ApplyPlanError(
            f"namespace mismatch: manifest has {manifest.namespace!r}, plan has {resolved_namespace!r}"
        )
    for field in ("base_url", "site_id", "namespace_candidate"):
        require_plan_field(plan, field)
        if str(plan[field]) != str(getattr(manifest, field)):
            raise ApplyPlanError(
                f"plan {field} mismatch: plan has {plan[field]!r}, manifest has {getattr(manifest, field)!r}"
            )

    expected_state_path = state_path_for_site(manifest.site_id, resolved_namespace, state_root=state_root)
    if str(plan.get("state_path", "")) != expected_state_path:
        raise ApplyPlanError(
            "plan state_path does not match the requested state root; "
            f"expected {expected_state_path!r}, found {plan.get('state_path')!r}"
        )

    chunks = list(chunk_jsonl_records(chunks_jsonl))
    verify_chunks_match_manifest(chunks, manifest)
    embedding_precision = str(plan.get("embedding_precision", "float32"))
    if embedding_precision not in EMBEDDING_PRECISIONS:
        raise ApplyPlanError(
            f"embedding precision must be one of: {', '.join(EMBEDDING_PRECISIONS)}"
        )
    verify_manifest_embedding_hashes(manifest, embedding_precision=embedding_precision)
    verify_artifact_hash(plan, manifest)

    state = load_applied_state(
        site_id=manifest.site_id,
        namespace=resolved_namespace,
        base_url=manifest.base_url,
        state_root=state_root,
    )
    diff = diff_manifest_against_state(manifest, state)
    chunks_by_row_id = {chunk.row_id: chunk for chunk in manifest.chunks}
    return VerifiedApplyPlan(
        plan_path=plan_path,
        plan=plan,
        manifest=manifest,
        chunks_by_row_id=chunks_by_row_id,
        state=state,
        diff=diff,
        state_root=state_root,
    )


def apply_preflight_summary(
    verified: VerifiedApplyPlan,
    *,
    namespace: str,
    approved: bool = False,
    delete_stale: bool = False,
) -> JsonObject:
    """Return a clear no-write apply summary."""

    return build_apply_summary(
        verified=verified,
        namespace=namespace,
        approved=approved,
        delete_stale=delete_stale,
        rows_upserted=0,
        embeddings_generated=0,
        rows_deleted=0,
        state_updated=False,
        api_calls_occurred=False,
    )


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
) -> JsonObject:
    """Embed/upsert only diff rows, optionally delete stale rows, then update state."""

    def emit_progress(message: str) -> None:
        if progress_callback is None:
            return
        try:
            progress_callback(message)
        except Exception:
            # Progress is advisory; it must not interrupt a live apply.
            return

    def observe_monotonic() -> float | None:
        try:
            return monotonic()
        except Exception:
            # Timing is diagnostic; it must not interrupt a live apply.
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

    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        raise RuntimeError("TURBOPUFFER_API_KEY must be set in the environment for approved apply.")

    emit_progress("apply: acquiring namespace lock")
    with acquire_namespace_apply_lock(
        site_id=verified.manifest.site_id,
        namespace=namespace,
        state_root=verified.state_root,
    ):
        applied_at = datetime.now(timezone.utc).isoformat()
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
                                plan_id=str(verified.plan["plan_id"]),
                                applied_at=applied_at,
                            )
                            for chunk, vector in zip(batch, vectors, strict=True)
                        ]
                        # The current batch was prepared while the previous upsert ran.
                        # Confirm that write before submitting another one; failed writes
                        # therefore discard these vectors without starting later work.
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
            elapsed_seconds = elapsed_since(apply_started_at)
            emit_progress(
                "apply: deleted stale rows="
                f"{rows_deleted}; elapsed={elapsed_seconds:.1f}s; "
                f"embedding={embedding_seconds:.1f}s; write={write_seconds:.1f}s"
            )

        emit_progress("apply: committing local state")
        next_state = build_state_after_apply(verified, applied_at=applied_at, delete_stale=delete_stale)
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
    return build_apply_summary(
        verified=verified,
        namespace=namespace,
        approved=True,
        delete_stale=delete_stale,
        rows_upserted=rows_written,
        embeddings_generated=embeddings_generated,
        rows_deleted=rows_deleted,
        state_updated=True,
        api_calls_occurred=rows_written > 0 or rows_deleted > 0,
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


def build_state_after_apply(
    verified: VerifiedApplyPlan,
    *,
    applied_at: str,
    delete_stale: bool = False,
) -> AppliedState:
    """Return the local state ledger after a successful approved apply."""

    active_rows = [
        AppliedStateRow(
            row_id=chunk.row_id,
            canonical_url=chunk.canonical_url,
            page_hash=chunk.page_hash,
            chunk_hash=chunk.chunk_hash,
            embedding_text_hash=chunk.embedding_text_hash,
            plan_id=str(verified.plan["plan_id"]),
            applied_at=applied_at,
            status=ROW_STATUS_ACTIVE,
        )
        for chunk in sorted(verified.manifest.chunks, key=lambda item: item.row_id)
    ]
    retained_rows: list[AppliedStateRow] = []
    if not delete_stale:
        retained_seen: set[str] = set()
        for record in [*verified.diff.stale_row_records, *verified.diff.retained_stale_row_records]:
            if record.row_id in retained_seen:
                continue
            retained_seen.add(record.row_id)
            retained_rows.append(
                AppliedStateRow(
                    row_id=record.row_id,
                    canonical_url=record.canonical_url,
                    page_hash=record.page_hash,
                    chunk_hash=record.chunk_hash,
                    embedding_text_hash=record.embedding_text_hash,
                    plan_id=record.plan_id,
                    applied_at=record.applied_at,
                    status=ROW_STATUS_RETAINED_STALE,
                )
            )
    apply_id = make_apply_id(str(verified.plan["plan_id"]), applied_at)
    return build_applied_state(
        site_id=verified.manifest.site_id,
        namespace=verified.manifest.namespace,
        base_url=verified.manifest.base_url,
        last_plan_id=str(verified.plan["plan_id"]),
        last_apply_id=apply_id,
        rows=[*active_rows, *sorted(retained_rows, key=lambda row: row.row_id)],
        updated_at=applied_at,
    )


def build_apply_summary(
    *,
    verified: VerifiedApplyPlan,
    namespace: str,
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
        "base_url": verified.manifest.base_url,
        "site_id": verified.manifest.site_id,
        "plan_id": verified.plan["plan_id"],
        "plan_path": str(verified.plan_path),
        "state_backend": "local",
        "state_path": state_path_for_site(verified.manifest.site_id, namespace, state_root=verified.state_root),
        "state_first_apply": verified.state.first_apply,
        "state_updated": state_updated,
        "artifact_hash": verified.plan["artifact_hash"],
        "artifact_verified": True,
        "embedding_model": verified.plan["embedding_model"],
        "embedding_precision": verified.plan.get("embedding_precision", "float32"),
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
        "diff": diff_summary,
    }
    if timing is not None:
        summary["timing"] = timing
    return summary


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


def verify_artifact_hash(plan: JsonObject, manifest: ManifestDocument) -> None:
    require_plan_field(plan, "artifact_hash")
    require_plan_field(plan, "crawl_options")
    require_plan_field(plan, "chunk_options")
    require_plan_field(plan, "embedding_model")
    artifact_payload = {
        "schema_version": PLAN_SCHEMA_VERSION,
        "base_url": manifest.base_url,
        "site_id": manifest.site_id,
        "namespace": manifest.namespace,
        "namespace_candidate": manifest.namespace_candidate,
        "crawl_options": plan["crawl_options"],
        "chunk_options": plan["chunk_options"],
        "embedding_model": plan["embedding_model"],
        "manifest": dataclass_to_json_object(manifest),
    }
    if "embedding_precision" in plan:
        artifact_payload["embedding_precision"] = plan["embedding_precision"]
    expected = stable_hash(artifact_payload)
    if str(plan["artifact_hash"]) != expected:
        raise ApplyPlanError(
            f"artifact hash mismatch: plan has {plan['artifact_hash']!r}, recomputed {expected!r}"
        )


def verify_chunks_match_manifest(chunks_jsonl_records_payload: Sequence[JsonObject], manifest: ManifestDocument) -> None:
    manifest_chunks = [dataclass_to_json_object(chunk) for chunk in manifest.chunks]
    if list(chunks_jsonl_records_payload) != manifest_chunks:
        raise ApplyPlanError("chunks.jsonl does not match manifest.json chunks")


def verify_manifest_embedding_hashes(
    manifest: ManifestDocument, *, embedding_precision: str = "float32"
) -> None:
    for chunk in manifest.chunks:
        expected = embedding_hash(embedding_text_for_chunk(chunk), embedding_precision)
        if chunk.embedding_text_hash != expected:
            raise ApplyPlanError(
                f"embedding_text_hash mismatch for row {chunk.row_id}: "
                f"manifest has {chunk.embedding_text_hash!r}, recomputed {expected!r}"
            )


def embedding_text_for_chunk(chunk: ChunkManifestRecord) -> str:
    context: list[str] = []
    if chunk.title:
        context.append(f"Title: {chunk.title}")
    if chunk.section_path:
        context.append(f"Section: {chunk.section_path}")
    context.append(chunk.content)
    return "\n\n".join(part for part in context if str(part).strip())


def manifest_from_json(payload: JsonObject) -> ManifestDocument:
    if not isinstance(payload, dict):
        raise ApplyPlanError("manifest must be a JSON object")
    try:
        schema_version = int(payload["schema_version"])
        if schema_version != PLAN_SCHEMA_VERSION:
            raise ApplyPlanError(
                f"unsupported manifest schema_version {schema_version}; expected {PLAN_SCHEMA_VERSION}"
            )
        pages_payload = payload.get("pages", [])
        chunks_payload = payload.get("chunks", [])
        if not isinstance(pages_payload, list):
            raise ApplyPlanError("manifest pages must be a list")
        if not isinstance(chunks_payload, list):
            raise ApplyPlanError("manifest chunks must be a list")
        return ManifestDocument(
            schema_version=schema_version,
            site_id=str(payload["site_id"]),
            base_url=str(payload["base_url"]),
            namespace=str(payload["namespace"]),
            namespace_candidate=str(payload["namespace_candidate"]),
            pages=[page_from_json(page, index=index) for index, page in enumerate(pages_payload)],
            chunks=[chunk_from_json(chunk, index=index) for index, chunk in enumerate(chunks_payload)],
        )
    except KeyError as exc:
        raise ApplyPlanError(f"manifest missing required field: {exc.args[0]}") from exc


def page_from_json(payload: Any, *, index: int):
    from buoy_search.plan_artifacts import PageManifestRecord

    if not isinstance(payload, dict):
        raise ApplyPlanError(f"manifest page {index} must be a JSON object")
    try:
        status = payload.get("status")
        return PageManifestRecord(
            canonical_url=str(payload["canonical_url"]),
            title=str(payload["title"]),
            content_path=str(payload["content_path"]),
            page_hash=str(payload["page_hash"]),
            status=None if status is None else int(status),
            content_type=str(payload.get("content_type", "")),
            source_metadata={str(key): str(value) for key, value in dict(payload.get("source_metadata", {})).items()},
        )
    except KeyError as exc:
        raise ApplyPlanError(f"manifest page {index} missing required field: {exc.args[0]}") from exc


def chunk_from_json(payload: Any, *, index: int) -> ChunkManifestRecord:
    if not isinstance(payload, dict):
        raise ApplyPlanError(f"manifest chunk {index} must be a JSON object")
    try:
        return ChunkManifestRecord(
            row_id=str(payload["row_id"]),
            row_id_candidate=str(payload.get("row_id_candidate", payload["row_id"])),
            site_id=str(payload["site_id"]),
            duplicate_ordinal=int(payload.get("duplicate_ordinal", 0)),
            canonical_url=str(payload["canonical_url"]),
            page_content_path=str(payload["page_content_path"]),
            page_hash=str(payload["page_hash"]),
            chunk_hash=str(payload["chunk_hash"]),
            embedding_text_hash=str(payload["embedding_text_hash"]),
            title=str(payload["title"]),
            section_path=str(payload["section_path"]),
            chunk_index=int(payload["chunk_index"]),
            content=str(payload["content"]),
            content_preview=str(payload.get("content_preview", "")),
            doc_kind=str(payload.get("doc_kind", "page")),
            tags=[str(tag) for tag in payload.get("tags", [])],
            source_metadata={str(key): str(value) for key, value in dict(payload.get("source_metadata", {})).items()},
        )
    except KeyError as exc:
        raise ApplyPlanError(f"manifest chunk {index} missing required field: {exc.args[0]}") from exc


def require_plan_field(plan: JsonObject, field: str) -> None:
    if field not in plan:
        raise ApplyPlanError(f"plan missing required field: {field}")


def make_apply_id(plan_id: str, applied_at: str) -> str:
    timestamp = applied_at.replace(":", "").replace("+", "Z").replace("-", "")
    return f"apply_{timestamp}_{plan_id[:24]}"
