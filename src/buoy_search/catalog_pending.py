"""Integrity-bound pending lifecycle for approved remote catalog registration."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
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
    CatalogError,
    NamespaceCard,
    RoutingEmbedder,
    card_to_dict,
    parse_card,
    parse_prospective_card,
    prepare_card,
)
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    MutationResult,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    RemoteClient,
    create_remote_cards,
    read_remote_card_twice,
    read_remote_catalog,
    rebase_remote_card,
    update_remote_card,
    validate_accept_remote,
)
from buoy_search.plan_artifacts import stable_hash, stable_json_dumps

PENDING_SCHEMA_VERSION = 2
PENDING_FIELDS = {
    "pending_schema_version",
    "state_root",
    "catalog_namespace",
    "applied_state_path",
    "site_id",
    "namespace",
    "plan_id",
    "base_url",
    "prospective_card",
    "base_card",
    "expected_card_revision",
    "prior_applied_plan_id",
    "prior_applied_apply_id",
    "intended_state_hash",
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


def reconcile_command(path: Path) -> str:
    return shlex.join(["buoy", "catalog", "reconcile", "--pending", str(path)])


def abandon_command(path: Path) -> str:
    return shlex.join([
        "buoy", "catalog", "abandon-pending", "--pending", str(path), "--approve",
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
    applied_state_path: Path,
    site_id: str,
    namespace: str,
    plan_id: str,
    base_url: str,
    prospective_card: NamespaceCard,
    existing_card: NamespaceCard | None,
    prior_applied_plan_id: str | None,
    prior_applied_apply_id: str | None,
    intended_state_hash: str,
    region: str,
    ranking_contract: dict[str, object],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "pending_schema_version": PENDING_SCHEMA_VERSION,
        "state_root": str(normalized_path(state_root)),
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "applied_state_path": str(normalized_path(applied_state_path)),
        "site_id": site_id,
        "namespace": namespace,
        "plan_id": plan_id,
        "base_url": base_url,
        "prospective_card": card_to_dict(prospective_card, include_vector=True),
        "base_card": card_to_dict(existing_card, include_vector=True) if existing_card else None,
        "expected_card_revision": existing_card.card_revision if existing_card else None,
        "prior_applied_plan_id": prior_applied_plan_id,
        "prior_applied_apply_id": prior_applied_apply_id,
        "intended_state_hash": intended_state_hash,
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
    if type(payload["pending_schema_version"]) is not int or payload["pending_schema_version"] != PENDING_SCHEMA_VERSION:
        raise PendingCatalogError(
            f"pending catalog registration schema_version must equal {PENDING_SCHEMA_VERSION}"
        )
    for field in (
        "state_root", "catalog_namespace", "applied_state_path", "site_id", "namespace",
        "plan_id", "base_url", "intended_state_hash", "region", "payload_hash",
    ):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise PendingCatalogError(f"pending catalog registration field {field} must be a non-empty string")
    if payload["catalog_namespace"] != REMOTE_CATALOG_NAMESPACE:
        raise PendingCatalogError("pending catalog namespace binding is invalid")
    for field in ("state_root", "applied_state_path"):
        if str(normalized_path(Path(payload[field]))) != payload[field]:
            raise PendingCatalogError(f"pending catalog registration field {field} must be a normalized absolute path")
    if not isinstance(payload["remote_apply_confirmed"], bool):
        raise PendingCatalogError("pending catalog registration confirmation must be boolean")
    for field in ("expected_card_revision", "prior_applied_plan_id", "prior_applied_apply_id"):
        if payload[field] is not None and (
            not isinstance(payload[field], str) or not payload[field].strip()
        ):
            raise PendingCatalogError(f"pending catalog registration {field} is invalid")
    if payload["base_card"] is None:
        if payload["expected_card_revision"] is not None:
            raise PendingCatalogError("absence-bound pending cannot have an expected card revision")
    else:
        base_card = parse_card(payload["base_card"])
        if base_card.namespace != payload["namespace"] or base_card.region != payload["region"]:
            raise PendingCatalogError("pending base card binding is mismatched")
        if payload["expected_card_revision"] != base_card.card_revision:
            raise PendingCatalogError("pending expected card revision does not match its base card")
    if (payload["prior_applied_plan_id"] is None) != (payload["prior_applied_apply_id"] is None):
        raise PendingCatalogError("pending prior applied-state identity must have both IDs null or non-empty")
    if not isinstance(payload["ranking_contract"], dict):
        raise PendingCatalogError("pending catalog registration ranking binding is invalid")
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
) -> PendingSnapshot:
    current = load_pending_snapshot(path)
    validate_pending_path(path, current.payload)
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


def validate_pending_path(path: Path, payload: dict[str, Any]) -> Path:
    absolute_pending = path.expanduser().absolute()
    state_root = normalized_path(Path(payload["state_root"]))
    expected_root = state_root / "catalog-pending"
    expected_path = expected_root / f"{payload['plan_id']}.json"
    if absolute_pending != expected_path or path.resolve(strict=True) != expected_path:
        raise PendingCatalogError(f"pending path must be the bound regular file directly under {expected_root}")
    expected_database = normalized_path(
        applied_state_paths(
            site_id=str(payload["site_id"]),
            namespace=str(payload["namespace"]),
            state_root=state_root,
        ).database_path
    )
    if expected_database != normalized_path(Path(payload["applied_state_path"])):
        raise PendingCatalogError("pending applied-state database binding is mismatched")
    return state_root


def applied_state_hash(state: Any) -> str:
    """Return the pending ledger proof over all durable applied-state fields."""

    return stable_hash({
        "schema_version": state.schema_version,
        "site_id": state.site_id,
        "namespace": state.namespace,
        "base_url": state.base_url,
        "updated_at": state.updated_at,
        "last_plan_id": state.last_plan_id,
        "last_apply_id": state.last_apply_id,
        "rows": [vars(row) for row in sorted(state.rows, key=lambda row: row.row_id)],
    })


def inspect_apply_collision(path: Path, *, expected: dict[str, str]) -> None:
    if not path.exists() and not path.is_symlink():
        return
    payload = load_pending(path)
    for field, value in expected.items():
        if str(payload.get(field)) != value:
            raise PendingCollisionError(f"pending catalog registration binding is mismatched or tampered: {path}")
    command = reconcile_command(path)
    if payload["remote_apply_confirmed"]:
        raise PendingCollisionError(
            f"confirmed pending catalog registration blocks apply rerun; reconcile with: {command}"
        )
    state = load_applied_state(
        site_id=str(payload["site_id"]), namespace=str(payload["namespace"]),
        base_url=str(payload["base_url"]), state_root=Path(payload["state_root"]),
    )
    if _unconfirmed_state_proves_success(payload, state):
        raise PendingCollisionError(
            "applied state exactly proves content apply success despite interrupted confirmation; "
            f"reconcile without replaying content: {command}"
        )
    raise PendingCollisionError(
        "unconfirmed pending catalog registration blocks apply rerun because content state is indeterminate; "
        f"only explicit abandonment permits a later idempotent repeat-upsert: {abandon_command(path)}"
    )


def _unconfirmed_state_proves_success(payload: dict[str, Any], state: Any) -> bool:
    return (
        not payload["remote_apply_confirmed"]
        and state.last_plan_id == payload["plan_id"]
        and bool(state.last_apply_id)
        and applied_state_hash(state) == payload["intended_state_hash"]
        and (state.last_plan_id, state.last_apply_id)
        != (payload["prior_applied_plan_id"], payload["prior_applied_apply_id"])
    )


def _confirmed_card(payload: dict[str, Any], state: Any) -> NamespaceCard:
    if payload["remote_apply_confirmed"]:
        if (
            state.last_plan_id != payload["plan_id"]
            or state.last_apply_id != payload["apply_id"]
            or applied_state_hash(state) != payload["intended_state_hash"]
        ):
            raise PendingCatalogError("current applied state does not exactly match pending plan/apply ledger proof")
        return parse_card(payload["prospective_card"])
    if not _unconfirmed_state_proves_success(payload, state):
        raise PendingCatalogError(
            "unconfirmed pending registration is not backed by exact matching applied-state success"
        )
    prospective = parse_prospective_card(payload["prospective_card"])
    return prepare_card(
        replace(
            _card_fields(prospective),
            last_plan_id=str(payload["plan_id"]),
            last_apply_id=state.last_apply_id,
        ),
        existing=prospective,
    )


def _reconcile_output(
    *,
    path: Path,
    region: str,
    desired: NamespaceCard,
    accepted: NamespaceCard,
    action: str,
    affected_ids: list[str],
    mutation: MutationResult | None,
    snapshot: RemoteCatalogSnapshot | None,
    expected_remote_revision: str | None,
) -> dict[str, Any]:
    read = snapshot.metrics if snapshot else None
    mutation_metrics = mutation.metrics if mutation else None
    namespace_pages = read.namespace_list_pages if read else 0
    metadata_requests = read.metadata_requests if read else 0
    card_pages = read.card_query_pages if read else 0
    verification_requests = mutation_metrics.verification_query_requests if mutation_metrics else 0
    write_requests = mutation_metrics.write_requests if mutation_metrics else 0
    billing = list(read.billing if read else ())
    billing.extend(mutation_metrics.billing if mutation_metrics else ())
    return {
        "command": "catalog reconcile",
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "region": region,
        "snapshot_revision": snapshot.snapshot_revision if snapshot else None,
        "catalog_snapshot_complete": snapshot is not None,
        "counts": asdict(snapshot.counts) if snapshot else None,
        "read_metrics": {
            "namespace_list_pages": namespace_pages,
            "metadata_requests": metadata_requests,
            "card_query_pages": card_pages,
            "billing": list(read.billing if read else ()),
        },
        "request_summary": {
            "namespace_list_requests": namespace_pages,
            "metadata_requests": metadata_requests,
            "catalog_page_query_requests": card_pages,
            "precondition_verification_query_requests": 2,
            "mutation_verification_query_requests": verification_requests,
            "write_requests": write_requests,
            "total_requests": (
                namespace_pages + metadata_requests + card_pages
                + 2 + verification_requests + write_requests
            ),
            "billing": billing,
            "billing_complete": False,
        },
        "namespace": desired.namespace,
        "pending_path": str(path),
        "pending_cleanup": False,
        "action": action,
        "catalog_updated": action != "accepted_remote",
        "affected_ids": affected_ids,
        "card_revision": accepted.card_revision,
        "pending_plan_id": desired.last_plan_id,
        "pending_apply_id": desired.last_apply_id,
        "remote_plan_id": accepted.last_plan_id,
        "remote_apply_id": accepted.last_apply_id,
        "remote_revision": accepted.card_revision,
        "operator_accepted_exact_revision": expected_remote_revision if action == "accepted_remote" else None,
        "content_replayed": False,
        "catalog_repair_command": reconcile_command(path),
    }


def reconcile_pending(
    path: Path,
    *,
    client: RemoteClient,
    region: str,
    compatibility: CompatibilityContract,
    action: str = "ordinary",
    expected_remote_revision: str | None = None,
    embedder: RoutingEmbedder | None = None,
) -> dict[str, Any]:
    if action not in {"ordinary", "rebase", "accept_remote"}:
        raise PendingCatalogError(f"unsupported reconcile action {action!r}")
    initial = load_pending_snapshot(path)
    payload = initial.payload
    state_root = validate_pending_path(path, payload)
    if payload["region"] != region:
        raise PendingCatalogError("pending region does not match resolved remote region")
    with acquire_namespace_apply_lock(
        site_id=str(payload["site_id"]), namespace=str(payload["namespace"]), state_root=state_root
    ):
        locked = _require_same_pending(path, initial)
        payload = locked.payload
        state = load_applied_state(
            site_id=str(payload["site_id"]), namespace=str(payload["namespace"]),
            base_url=str(payload["base_url"]), state_root=state_root,
        )
        desired = _confirmed_card(payload, state)
        if not payload["remote_apply_confirmed"]:
            payload = confirm_pending(path, payload, apply_id=state.last_apply_id)
            locked = load_pending_snapshot(path)
            desired = parse_card(payload["prospective_card"])
        resource = client.namespace(REMOTE_CATALOG_NAMESPACE)
        current_values = read_remote_card_twice(
            resource, namespace=desired.namespace, region=region,
            preserve_reads=action == "accept_remote",
        )
        current = current_values[0] if current_values else None
        affected_ids: list[str] = []
        accepted: NamespaceCard | None = None
        mutation: MutationResult | None = None
        if action == "accept_remote":
            if not expected_remote_revision:
                raise PendingCatalogError("accept-remote requires an exact expected remote revision")
            if current is None:
                raise RemoteCatalogError("accept-remote requires an existing stable remote card")
            accepted = validate_accept_remote(
                current_reads=current_values, pending=desired,
                expected_remote_revision=expected_remote_revision,
            )
            result_action = "accepted_remote"
        elif action == "rebase":
            if current is None:
                raise RemoteCatalogError("safe rebase requires a current remote card")
            base = parse_card(payload["base_card"]) if payload["base_card"] else None
            rebased = rebase_remote_card(base=base, current=current, pending=desired, embedder=embedder)
            mutation = update_remote_card(
                resource, rebased, expected_revision=current.card_revision, region=region
            )
            affected_ids = list(mutation.affected_ids)
            accepted = mutation.card
            result_action = "rebased"
        else:
            if current is not None and card_to_dict(current, include_vector=True) == card_to_dict(desired, include_vector=True):
                accepted = current
                result_action = "already_committed"
            elif payload["expected_card_revision"] is None:
                if current is not None:
                    raise RemoteCatalogError("conditional card create conflicted with current remote state")
                mutation = create_remote_cards(resource, [desired], region=region)
                affected_ids = list(mutation.affected_ids)
                accepted = mutation.card
                result_action = "committed"
            else:
                if current is None or current.card_revision != payload["expected_card_revision"]:
                    raise RemoteCatalogError("conditional card update conflicted with current remote revision")
                mutation = update_remote_card(
                    resource, desired,
                    expected_revision=str(payload["expected_card_revision"]), region=region,
                )
                affected_ids = list(mutation.affected_ids)
                accepted = mutation.card
                result_action = "committed"
        if accepted is None:
            raise RemoteCatalogError("verified reconcile action returned no remote card")
        try:
            snapshot = read_remote_catalog(client, region=region, compatibility=compatibility)
            snapshot_card = next(
                (card for card in snapshot.cards if card.namespace == accepted.namespace), None
            )
            if snapshot_card is None or snapshot_card.card_revision != accepted.card_revision:
                raise RemoteCatalogError("post-reconcile remote catalog snapshot does not contain verified card")
        except (RemoteCatalogError, CatalogError, OSError, ValueError) as exc:
            partial = _reconcile_output(
                path=path, region=region, desired=desired, accepted=accepted,
                action=result_action, affected_ids=affected_ids, mutation=mutation,
                snapshot=None, expected_remote_revision=expected_remote_revision,
            )
            raise CatalogCommitPartialSuccess(str(exc), partial) from exc
        output = _reconcile_output(
            path=path, region=region, desired=desired, accepted=accepted,
            action=result_action, affected_ids=affected_ids, mutation=mutation,
            snapshot=snapshot, expected_remote_revision=expected_remote_revision,
        )
        try:
            remove_expected_pending(
                path, payload, expected_device=locked.device, expected_inode=locked.inode
            )
        except (OSError, ValueError) as exc:
            raise CatalogCommitPartialSuccess(str(exc), output) from exc
        output["pending_cleanup"] = True
        return output


def abandon_pending(path: Path, *, approve: bool) -> dict[str, Any]:
    initial = load_pending_snapshot(path)
    payload = initial.payload
    state_root = validate_pending_path(path, payload)
    with acquire_namespace_apply_lock(
        site_id=str(payload["site_id"]), namespace=str(payload["namespace"]), state_root=state_root
    ):
        locked = _require_same_pending(path, initial)
        payload = locked.payload
        if payload["remote_apply_confirmed"]:
            raise PendingCatalogError("confirmed pending catalog registration must be reconciled, not abandoned")
        state = load_applied_state(
            site_id=str(payload["site_id"]), namespace=str(payload["namespace"]),
            base_url=str(payload["base_url"]), state_root=state_root,
        )
        if _unconfirmed_state_proves_success(payload, state):
            raise PendingCatalogError("applied state exactly proves this pending apply succeeded; abandonment is unsafe")
        result = {
            "command": "catalog abandon-pending",
            "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
            "region": payload["region"],
            "snapshot_revision": None,
            "counts": None,
            "read_metrics": {
                "namespace_list_pages": 0,
                "metadata_requests": 0,
                "card_query_pages": 0,
                "billing": [],
            },
            "request_summary": {
                "namespace_list_requests": 0,
                "metadata_requests": 0,
                "catalog_page_query_requests": 0,
                "precondition_verification_query_requests": 0,
                "mutation_verification_query_requests": 0,
                "write_requests": 0,
                "total_requests": 0,
                "billing": [],
                "billing_complete": True,
            },
            "remote_state": "not_read",
            "namespace": payload["namespace"],
            "pending_path": str(path),
            "approved": approve,
            "mutation_status": "abandoned" if approve else "preview",
            "remote_state_indeterminate": True,
            "warning": "A later approved apply may repeat idempotent content upserts after an indeterminate crash.",
        }
        if approve:
            remove_expected_pending(
                path, payload, expected_device=locked.device, expected_inode=locked.inode
            )
        return result
