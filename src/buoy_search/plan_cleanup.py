"""Race-safe local lifecycle cleanup for fully verified schema-v2 plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import stat
from uuid import uuid4


@dataclass(frozen=True)
class _VerifiedPlanIdentity:
    namespace: str
    plan_id: str
    artifact_hash: str
    created_at: datetime
    directory_device: int
    directory_inode: int


def cleanup_applied_plan_directory(
    plan_path: Path,
    *,
    state_root: Path,
    expected_plan_id: str,
    expected_artifact_hash: str,
    expected_namespace: str,
    expected_directory_device: int,
    expected_directory_inode: int,
) -> list[str]:
    """Remove only the exact fully verified plan that completed approved apply."""

    plan_dir = plan_path.parent.absolute()
    if _is_within_state_root(plan_dir, state_root):
        return [f"could not remove plan artifact directory under state root: {plan_dir}"]
    identity = _verified_plan_identity(plan_dir)
    if identity is None or (
        identity.plan_id,
        identity.artifact_hash,
        identity.namespace,
        identity.directory_device,
        identity.directory_inode,
    ) != (
        expected_plan_id,
        expected_artifact_hash,
        expected_namespace,
        expected_directory_device,
        expected_directory_inode,
    ):
        return [f"could not remove replaced or unverified plan artifact directory: {plan_dir}"]
    return _remove_exact_plan_directory(plan_dir, identity)


def cleanup_superseded_plan_directories(
    new_plan_path: Path,
    *,
    namespace: str,
    state_root: Path,
) -> list[str]:
    """Remove exact fully verified siblings superseded by one successful plan."""

    new_plan_dir = new_plan_path.parent.absolute()
    if _is_within_state_root(new_plan_dir, state_root):
        return [f"could not inspect plan artifact directory under state root: {new_plan_dir}"]
    new_identity = _verified_plan_identity(new_plan_dir)
    if new_identity is None or new_identity.namespace != namespace:
        return [f"could not verify newly written plan artifact directory: {new_plan_dir}"]
    parent = new_plan_dir.parent
    if parent.is_symlink():
        return [f"could not inspect plan artifact parent symlink: {parent}"]

    try:
        candidates = list(parent.iterdir())
    except OSError as exc:
        return [f"could not inspect plan artifact parent {parent}: {exc}"]

    warnings: list[str] = []
    for candidate in candidates:
        candidate = candidate.absolute()
        if candidate == new_plan_dir or candidate.is_symlink() or not candidate.is_dir():
            continue
        if _is_within_state_root(candidate, state_root):
            warnings.append(f"could not remove plan artifact directory under state root: {candidate}")
            continue
        identity = _verified_plan_identity(candidate)
        if (
            identity is None
            or identity.namespace != namespace
            or identity.created_at >= new_identity.created_at
        ):
            continue
        warnings.extend(_remove_exact_plan_directory(candidate, identity))
    return warnings


def _is_within_state_root(path: Path, state_root: Path) -> bool:
    """Return whether a path is lexically contained by the configured state root."""

    try:
        path.absolute().relative_to(state_root.absolute())
    except ValueError:
        return False
    return True


def _directory_identity(path: Path) -> tuple[int, int] | None:
    try:
        observed = path.lstat()
    except OSError:
        return None
    if not stat.S_ISDIR(observed.st_mode):
        return None
    return observed.st_dev, observed.st_ino


def _verified_plan_identity(plan_dir: Path) -> _VerifiedPlanIdentity | None:
    """Fully verify a schema-v2 plan and bind it to its no-follow directory."""

    before = _directory_identity(plan_dir)
    if before is None:
        return None
    try:
        if {entry.name for entry in plan_dir.iterdir()} != {"plan.json", "delta.duckdb"}:
            return None
        from buoy_search.plan_artifacts import verify_plan_artifacts

        verified = verify_plan_artifacts(plan_dir / "plan.json")
    except (OSError, ValueError):
        return None
    after = _directory_identity(plan_dir)
    if before != after:
        return None
    plan = verified.plan
    namespace = plan.get("namespace")
    plan_id = plan.get("plan_id")
    artifact_hash = plan.get("artifact_hash")
    created_at = plan.get("created_at")
    if not all(
        isinstance(value, str) and value
        for value in (namespace, plan_id, artifact_hash, created_at)
    ):
        return None
    try:
        created = datetime.fromisoformat(created_at)
    except ValueError:
        return None
    if created.tzinfo is None:
        return None
    return _VerifiedPlanIdentity(
        namespace=namespace,
        plan_id=plan_id,
        artifact_hash=artifact_hash,
        created_at=created,
        directory_device=before[0],
        directory_inode=before[1],
    )


def _same_plan(left: _VerifiedPlanIdentity, right: _VerifiedPlanIdentity) -> bool:
    return (
        left.namespace,
        left.plan_id,
        left.artifact_hash,
        left.created_at,
        left.directory_device,
        left.directory_inode,
    ) == (
        right.namespace,
        right.plan_id,
        right.artifact_hash,
        right.created_at,
        right.directory_device,
        right.directory_inode,
    )


def _restore_quarantine(
    parent_fd: int, quarantine_name: str, original_name: str, display_path: Path
) -> list[str]:
    try:
        os.stat(original_name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        try:
            os.rename(
                quarantine_name,
                original_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
            return []
        except OSError as exc:
            return [f"could not restore retained plan artifact directory {display_path}: {exc}"]
    except OSError as exc:
        return [f"could not restore retained plan artifact directory {display_path}: {exc}"]
    return [f"retained raced plan artifact in quarantine beside: {display_path}"]


def _remove_exact_plan_directory(
    plan_dir: Path, expected: _VerifiedPlanIdentity
) -> list[str]:
    """Atomically quarantine, reverify, then delete only the expected directory."""

    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        return [f"could not safely remove plan artifact directory on this platform: {plan_dir}"]
    parent = plan_dir.parent
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        parent_fd = os.open(parent, flags)
    except OSError as exc:
        return [f"could not open plan artifact parent for cleanup {parent}: {exc}"]

    quarantine_name = f".buoy-plan-delete-{uuid4().hex}"
    try:
        try:
            observed = os.stat(plan_dir.name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            return [f"could not inspect plan artifact directory {plan_dir}: {exc}"]
        if not stat.S_ISDIR(observed.st_mode) or (
            observed.st_dev,
            observed.st_ino,
        ) != (expected.directory_device, expected.directory_inode):
            return [f"could not remove replaced plan artifact directory: {plan_dir}"]
        try:
            os.rename(
                plan_dir.name,
                quarantine_name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
        except OSError as exc:
            return [f"could not quarantine plan artifact directory {plan_dir}: {exc}"]

        quarantine_path = parent / quarantine_name
        after = _verified_plan_identity(quarantine_path)
        if after is None or not _same_plan(after, expected):
            warnings = _restore_quarantine(parent_fd, quarantine_name, plan_dir.name, plan_dir)
            return warnings or [f"could not remove replaced or unverified plan artifact directory: {plan_dir}"]
        try:
            shutil.rmtree(quarantine_name, dir_fd=parent_fd)
            os.fsync(parent_fd)
        except OSError as exc:
            return [f"could not remove quarantined plan artifact directory {plan_dir}: {exc}"]
        return []
    finally:
        os.close(parent_fd)
