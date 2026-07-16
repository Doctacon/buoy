"""Local pending catalog registration lifecycle for approved apply.

Pending artifacts are integrity-bound local control-plane state. This module never
reads credentials or imports Turbopuffer.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import json
import os
from pathlib import Path
import shlex
import stat
from typing import Any
from uuid import uuid4

from buoy_search.applied_state import (
    acquire_namespace_apply_lock,
    applied_state_paths,
    load_applied_state,
)
from buoy_search.catalog import (
    CatalogDocument,
    CatalogError,
    NamespaceCard,
    card_to_dict,
    commit_system_card,
    load_catalog,
    parse_card,
    parse_prospective_card,
    prepare_card,
)
from buoy_search.plan_artifacts import stable_hash, stable_json_dumps

PENDING_SCHEMA_VERSION = 1
PENDING_FIELDS = {
    "pending_schema_version",
    "state_root",
    "catalog_path",
    "applied_state_path",
    "site_id",
    "namespace",
    "plan_id",
    "base_url",
    "prospective_card",
    "prior_catalog_revision",
    "prior_card_revision",
    "prior_applied_plan_id",
    "prior_applied_apply_id",
    "region",
    "ranking_contract",
    "remote_apply_confirmed",
    "apply_id",
    "payload_hash",
}


class PendingCatalogError(ValueError):
    """Raised when pending registration state is unsafe or incompatible."""


class PendingCollisionError(PendingCatalogError):
    """Raised when apply must stop rather than risk duplicate remote writes."""


class CatalogCommitPartialSuccess(RuntimeError):
    """Remote/applied-state success followed by pending/catalog failure."""

    def __init__(self, message: str, summary: dict[str, Any]) -> None:
        super().__init__(message)
        self.summary = summary


@dataclass(frozen=True)
class PendingSnapshot:
    payload: dict[str, Any]
    device: int
    inode: int


def normalized_path(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def pending_path_for_plan(state_root: Path, plan_id: str) -> Path:
    if not plan_id or Path(plan_id).name != plan_id or plan_id in {".", ".."}:
        raise PendingCatalogError("plan_id is unsafe for a pending artifact path")
    return normalized_path(state_root) / "catalog-pending" / f"{plan_id}.json"


def reconcile_command(path: Path, catalog_path: Path) -> str:
    return shlex.join(["buoy", "catalog", "reconcile", "--pending", str(path), "--catalog", str(catalog_path)])


def abandon_command(path: Path, catalog_path: Path) -> str:
    return shlex.join([
        "buoy", "catalog", "abandon-pending", "--pending", str(path),
        "--catalog", str(catalog_path), "--approve",
    ])


def _payload_hash(payload: dict[str, Any]) -> str:
    compact = dict(payload)
    compact.pop("payload_hash", None)
    return stable_hash(compact)


def _open_pending_parent(path: Path) -> int:
    parent = path.parent
    try:
        mode = parent.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise PendingCatalogError(
                f"pending root must be a real directory, not a symlink or non-directory: {parent}"
            )
    except FileNotFoundError:
        try:
            parent.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            pass
        except OSError as exc:
            raise PendingCatalogError(f"could not create pending root {parent}: {exc}") from exc
        mode = parent.lstat().st_mode
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise PendingCatalogError(
                f"pending root must be a real directory, not a symlink or non-directory: {parent}"
            )
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        directory_fd = os.open(parent, flags)
    except OSError as exc:
        raise PendingCatalogError(f"could not safely open pending root {parent}: {exc}") from exc
    if not stat.S_ISDIR(os.fstat(directory_fd).st_mode):
        os.close(directory_fd)
        raise PendingCatalogError(f"pending root is not a directory: {parent}")
    return directory_fd


def _atomic_write(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    data = (stable_json_dumps(payload, indent=2) + "\n").encode("utf-8")
    temporary_name = f".{path.name}.{os.getpid()}.{uuid4().hex}.tmp"
    directory_fd = _open_pending_parent(path)
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(temporary_name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(fd, "wb", closefd=True) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if exclusive:
            try:
                os.link(
                    temporary_name,
                    path.name,
                    src_dir_fd=directory_fd,
                    dst_dir_fd=directory_fd,
                    follow_symlinks=False,
                )
            except FileExistsError as exc:
                raise PendingCollisionError(
                    f"pending catalog registration already exists: {path}"
                ) from exc
            os.unlink(temporary_name, dir_fd=directory_fd)
        else:
            os.replace(
                temporary_name,
                path.name,
                src_dir_fd=directory_fd,
                dst_dir_fd=directory_fd,
            )
        try:
            os.fsync(directory_fd)
        except OSError:
            pass
    except OSError as exc:
        raise PendingCatalogError(f"could not atomically write pending catalog registration {path}: {exc}") from exc
    finally:
        try:
            os.unlink(temporary_name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        finally:
            os.close(directory_fd)


def build_pending_payload(
    *,
    state_root: Path,
    catalog_path: Path,
    applied_state_path: Path,
    site_id: str,
    namespace: str,
    plan_id: str,
    base_url: str,
    prospective_card: NamespaceCard,
    catalog: CatalogDocument,
    existing_card: NamespaceCard | None,
    prior_applied_plan_id: str | None,
    prior_applied_apply_id: str | None,
    region: str,
    ranking_contract: dict[str, object],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pending_schema_version": PENDING_SCHEMA_VERSION,
        "state_root": str(normalized_path(state_root)),
        "catalog_path": str(normalized_path(catalog_path)),
        "applied_state_path": str(normalized_path(applied_state_path)),
        "site_id": site_id,
        "namespace": namespace,
        "plan_id": plan_id,
        "base_url": base_url,
        "prospective_card": card_to_dict(prospective_card, include_vector=True),
        "prior_catalog_revision": catalog.catalog_revision,
        "prior_card_revision": existing_card.card_revision if existing_card else None,
        "prior_applied_plan_id": prior_applied_plan_id,
        "prior_applied_apply_id": prior_applied_apply_id,
        "region": region,
        "ranking_contract": dict(ranking_contract),
        "remote_apply_confirmed": False,
        "apply_id": None,
        "payload_hash": "",
    }
    payload["payload_hash"] = _payload_hash(payload)
    return validate_pending_payload(payload)


def create_pending(path: Path, payload: dict[str, Any]) -> None:
    validate_pending_payload(payload)
    _atomic_write(path, payload, exclusive=True)


def confirm_pending(path: Path, payload: dict[str, Any], *, apply_id: str) -> dict[str, Any]:
    validated = validate_pending_payload(payload)
    if validated["remote_apply_confirmed"]:
        return validated
    if validated["apply_id"] is not None:
        raise PendingCatalogError("unconfirmed pending catalog registration already has an apply_id")
    prospective = parse_prospective_card(validated["prospective_card"])
    finalized = prepare_card(
        replace(
            _card_fields(prospective),
            last_plan_id=str(validated["plan_id"]),
            last_apply_id=apply_id,
        ),
        existing=prospective,
    )
    confirmed = dict(validated)
    confirmed["prospective_card"] = card_to_dict(finalized, include_vector=True)
    confirmed["remote_apply_confirmed"] = True
    confirmed["apply_id"] = apply_id
    confirmed["payload_hash"] = _payload_hash(confirmed)
    confirmed = validate_pending_payload(confirmed)
    _atomic_write(path, confirmed)
    return confirmed


def _card_fields(card: NamespaceCard):
    from buoy_search.catalog import CardFields

    return CardFields(
        namespace=card.namespace,
        enabled=card.enabled,
        source_kind=card.source_kind,
        source_uri=card.source_uri,
        site_id=card.site_id,
        title=card.title,
        summary=card.summary,
        aliases=list(card.aliases),
        tags=list(card.tags),
        semantic_origin=card.semantic_origin,
        region=card.region,
        embedding_model=card.embedding_model,
        embedding_precision=card.embedding_precision,
        plan_schema_version=card.plan_schema_version,
        ranking_mode=card.ranking_mode,
        ranking_profile=card.ranking_profile,
        ranking_pool=card.ranking_pool,
        ranking_aggregation=card.ranking_aggregation,
        last_plan_id=card.last_plan_id,
        last_apply_id=card.last_apply_id,
    )


def validate_pending_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PendingCatalogError("pending catalog registration must be a JSON object")
    unknown = sorted(set(payload) - PENDING_FIELDS)
    missing = sorted(PENDING_FIELDS - set(payload))
    if unknown or missing:
        detail = f"unknown fields {unknown}" if unknown else f"missing fields {missing}"
        raise PendingCatalogError(f"pending catalog registration has {detail}")
    if type(payload["pending_schema_version"]) is not int or payload["pending_schema_version"] != 1:
        raise PendingCatalogError("pending catalog registration schema_version must equal 1")
    for field in ("state_root", "catalog_path", "applied_state_path", "site_id", "namespace", "plan_id", "base_url", "region", "payload_hash"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise PendingCatalogError(f"pending catalog registration field {field} must be a non-empty string")
    for field in ("state_root", "catalog_path", "applied_state_path"):
        if str(normalized_path(Path(payload[field]))) != payload[field]:
            raise PendingCatalogError(f"pending catalog registration field {field} must be a normalized absolute path")
    if not isinstance(payload["remote_apply_confirmed"], bool):
        raise PendingCatalogError("pending catalog registration confirmation must be boolean")
    for field in ("prior_card_revision", "prior_applied_plan_id", "prior_applied_apply_id"):
        if payload[field] is not None and (
            not isinstance(payload[field], str) or not payload[field].strip()
        ):
            raise PendingCatalogError(f"pending catalog registration {field} is invalid")
    if (payload["prior_applied_plan_id"] is None) != (payload["prior_applied_apply_id"] is None):
        raise PendingCatalogError("pending prior applied-state identity must have both IDs null or non-empty")
    if not isinstance(payload["prior_catalog_revision"], str) or not isinstance(payload["ranking_contract"], dict):
        raise PendingCatalogError("pending catalog registration catalog/ranking binding is invalid")
    card = parse_card(payload["prospective_card"]) if payload["remote_apply_confirmed"] else parse_prospective_card(payload["prospective_card"])
    if (
        card.namespace != payload["namespace"]
        or card.site_id != payload["site_id"]
        or card.last_plan_id != payload["plan_id"]
        or card.region != payload["region"]
    ):
        raise PendingCatalogError("pending catalog registration card binding is mismatched")
    if payload["remote_apply_confirmed"]:
        if not isinstance(payload["apply_id"], str) or not payload["apply_id"].strip():
            raise PendingCatalogError("confirmed pending catalog registration requires apply_id")
        if card.last_apply_id != payload["apply_id"]:
            raise PendingCatalogError("pending catalog registration applied identity is mismatched")
    elif payload["apply_id"] is not None or card.last_apply_id is not None:
        raise PendingCatalogError("unconfirmed pending registration cannot contain committed apply lineage")
    expected_ranking = {
        "ranking_mode": card.ranking_mode,
        "ranking_profile": card.ranking_profile,
        "ranking_pool": card.ranking_pool,
        "ranking_aggregation": card.ranking_aggregation,
    }
    if payload["ranking_contract"] != expected_ranking:
        raise PendingCatalogError("pending catalog registration ranking binding is mismatched")
    if payload["payload_hash"] != _payload_hash(payload):
        raise PendingCatalogError("pending catalog registration payload_hash is stale or invalid")
    return dict(payload)


def load_pending_snapshot(path: Path) -> PendingSnapshot:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
        try:
            metadata = os.fstat(fd)
            if not stat.S_ISREG(metadata.st_mode):
                raise PendingCatalogError(f"pending path must be a regular non-symlink file: {path}")
            with os.fdopen(fd, "r", encoding="utf-8", closefd=False) as handle:
                payload = validate_pending_payload(json.load(handle))
        finally:
            os.close(fd)
        current = path.lstat()
        if (
            stat.S_ISLNK(current.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (current.st_dev, current.st_ino) != (metadata.st_dev, metadata.st_ino)
        ):
            raise PendingCatalogError(f"pending path was replaced while being validated: {path}")
        return PendingSnapshot(payload=payload, device=metadata.st_dev, inode=metadata.st_ino)
    except PendingCatalogError:
        raise
    except OSError as exc:
        if path.is_symlink():
            raise PendingCatalogError(
                f"pending path must be a regular non-symlink file: {path}"
            ) from exc
        raise PendingCatalogError(f"invalid pending catalog registration {path}: {exc}") from exc
    except (UnicodeError, json.JSONDecodeError, ValueError, CatalogError) as exc:
        raise PendingCatalogError(f"invalid pending catalog registration {path}: {exc}") from exc


def load_pending(path: Path) -> dict[str, Any]:
    return load_pending_snapshot(path).payload


def _require_same_pending(
    path: Path,
    expected: PendingSnapshot,
    supplied_catalog: Path,
) -> PendingSnapshot:
    current = load_pending_snapshot(path)
    validate_pending_path(path, current.payload, supplied_catalog)
    if (
        (current.device, current.inode) != (expected.device, expected.inode)
        or current.payload["payload_hash"] != expected.payload["payload_hash"]
        or current.payload != expected.payload
    ):
        raise PendingCatalogError(
            f"pending catalog registration was replaced after validation: {path}"
        )
    return current


def remove_expected_pending(
    path: Path,
    expected_payload: dict[str, Any],
    *,
    expected_device: int | None = None,
    expected_inode: int | None = None,
) -> None:
    current = load_pending_snapshot(path)
    if (
        current.payload != expected_payload
        or current.payload["payload_hash"] != expected_payload["payload_hash"]
        or (expected_device is not None and current.device != expected_device)
        or (expected_inode is not None and current.inode != expected_inode)
    ):
        raise PendingCatalogError(
            f"pending catalog registration was replaced before cleanup: {path}"
        )
    directory_fd = _open_pending_parent(path)
    try:
        metadata = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
        if not stat.S_ISREG(metadata.st_mode) or (metadata.st_dev, metadata.st_ino) != (
            current.device,
            current.inode,
        ):
            raise PendingCatalogError(
                f"pending catalog registration was replaced before cleanup: {path}"
            )
        os.unlink(path.name, dir_fd=directory_fd)
    finally:
        os.close(directory_fd)


def validate_pending_path(path: Path, payload: dict[str, Any], supplied_catalog: Path) -> tuple[Path, Path]:
    absolute_pending = path.expanduser().absolute()
    state_root = normalized_path(Path(payload["state_root"]))
    expected_root = state_root / "catalog-pending"
    expected_path = expected_root / f"{payload['plan_id']}.json"
    if absolute_pending != expected_path or path.resolve(strict=True) != expected_path:
        raise PendingCatalogError(f"pending path must be the bound regular file directly under {expected_root}")
    catalog = normalized_path(supplied_catalog)
    if supplied_catalog.expanduser().is_symlink():
        raise PendingCatalogError("supplied catalog path must not be a symlink")
    if catalog != normalized_path(Path(payload["catalog_path"])):
        raise PendingCatalogError("supplied catalog path does not match the pending catalog binding")
    expected_database = normalized_path(
        applied_state_paths(
            site_id=str(payload["site_id"]),
            namespace=str(payload["namespace"]),
            state_root=state_root,
        ).database_path
    )
    if expected_database != normalized_path(Path(payload["applied_state_path"])):
        raise PendingCatalogError("pending applied-state database binding is mismatched")
    return state_root, catalog


def inspect_apply_collision(path: Path, *, expected: dict[str, str]) -> None:
    if not path.exists() and not path.is_symlink():
        return
    payload = load_pending(path)
    for field, value in expected.items():
        if str(payload.get(field)) != value:
            raise PendingCollisionError(f"pending catalog registration binding is mismatched or tampered: {path}")
    catalog = Path(payload["catalog_path"])
    if payload["remote_apply_confirmed"]:
        command = reconcile_command(path, catalog)
        raise PendingCollisionError(
            f"confirmed pending catalog registration blocks apply rerun; reconcile locally with: {command}"
        )
    state = load_applied_state(
        site_id=str(payload["site_id"]),
        namespace=str(payload["namespace"]),
        base_url=str(payload["base_url"]),
        state_root=Path(payload["state_root"]),
    )
    if _unconfirmed_state_proves_success(payload, state):
        command = reconcile_command(path, catalog)
        raise PendingCollisionError(
            "applied state proves remote apply success despite an interrupted pending confirmation; "
            f"reconcile locally with: {command}"
        )
    command = abandon_command(path, catalog)
    raise PendingCollisionError(
        "unconfirmed pending catalog registration blocks apply rerun because remote state is indeterminate; "
        f"only explicit local abandonment can permit a later idempotent repeat-upsert: {command}"
    )


def _unconfirmed_state_proves_success(payload: dict[str, Any], state: Any) -> bool:
    return (
        not payload["remote_apply_confirmed"]
        and state.last_plan_id == payload["plan_id"]
        and bool(state.last_apply_id)
        and (state.last_plan_id, state.last_apply_id)
        != (payload["prior_applied_plan_id"], payload["prior_applied_apply_id"])
    )


def reconcile_pending(path: Path, catalog_path: Path) -> tuple[CatalogDocument, NamespaceCard, bool]:
    initial = load_pending_snapshot(path)
    payload = initial.payload
    state_root, catalog = validate_pending_path(path, payload, catalog_path)
    with acquire_namespace_apply_lock(
        site_id=str(payload["site_id"]), namespace=str(payload["namespace"]), state_root=state_root
    ):
        locked = _require_same_pending(path, initial, catalog_path)
        payload = locked.payload
        state = load_applied_state(
            site_id=str(payload["site_id"]),
            namespace=str(payload["namespace"]),
            base_url=str(payload["base_url"]),
            state_root=state_root,
        )
        if payload["remote_apply_confirmed"]:
            if state.last_plan_id != payload["plan_id"] or state.last_apply_id != payload["apply_id"]:
                raise PendingCatalogError("current applied state does not match the pending plan/apply identity")
            card = parse_card(payload["prospective_card"])
        elif _unconfirmed_state_proves_success(payload, state):
            prospective = parse_prospective_card(payload["prospective_card"])
            card = prepare_card(
                replace(
                    _card_fields(prospective),
                    last_plan_id=str(payload["plan_id"]),
                    last_apply_id=state.last_apply_id,
                ),
                existing=prospective,
            )
        else:
            raise PendingCatalogError(
                "unconfirmed pending catalog registration is not backed by a new matching applied-state success"
            )
        document, card, changed = commit_system_card(catalog, card)
        remove_expected_pending(
            path,
            payload,
            expected_device=locked.device,
            expected_inode=locked.inode,
        )
        return document, card, changed


def abandon_pending(path: Path, catalog_path: Path, *, approve: bool) -> dict[str, Any]:
    initial = load_pending_snapshot(path)
    payload = initial.payload
    state_root, catalog = validate_pending_path(path, payload, catalog_path)
    with acquire_namespace_apply_lock(
        site_id=str(payload["site_id"]), namespace=str(payload["namespace"]), state_root=state_root
    ):
        locked = _require_same_pending(path, initial, catalog_path)
        payload = locked.payload
        if payload["remote_apply_confirmed"]:
            raise PendingCatalogError("confirmed pending catalog registration must be reconciled, not abandoned")
        state = load_applied_state(
            site_id=str(payload["site_id"]),
            namespace=str(payload["namespace"]),
            base_url=str(payload["base_url"]),
            state_root=state_root,
        )
        if _unconfirmed_state_proves_success(payload, state):
            raise PendingCatalogError("applied state proves this pending apply succeeded; abandonment is unsafe")
        result = {
            "command": "catalog abandon-pending",
            "catalog_path": str(catalog),
            "catalog_revision": load_catalog(catalog).catalog_revision,
            "namespace": payload["namespace"],
            "pending_path": str(path),
            "approved": approve,
            "mutation_status": "abandoned" if approve else "preview",
            "remote_state_indeterminate": True,
            "warning": "A later approved apply may repeat idempotent remote upserts after an indeterminate crash.",
        }
        if approve:
            remove_expected_pending(
                path,
                payload,
                expected_device=locked.device,
                expected_inode=locked.inode,
            )
        return result
