"""Race-resistant local lifecycle cleanup for fully verified schema-v3 plans."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import shutil
import stat
from uuid import uuid4

from buoy_search.local_paths import (
    LocalPathError,
    default_artifact_root,
    default_state_root,
    is_within,
    normalized_absolute,
)


@dataclass(frozen=True)
class _VerifiedPlanIdentity:
    namespace: str
    plan_id: str
    artifact_hash: str
    created_at: datetime
    directory_device: int
    directory_inode: int
    plan_file_device: int
    plan_file_inode: int
    delta_file_device: int
    delta_file_inode: int


def cleanup_applied_plan_directory(
    plan_path: Path,
    *,
    state_root: Path,
    managed_plan_root: Path | None = None,
    expected_plan_id: str,
    expected_artifact_hash: str,
    expected_namespace: str,
    expected_directory_device: int,
    expected_directory_inode: int,
) -> list[str]:
    """Remove only the exact fully verified plan that completed approved apply."""

    plan_dir = plan_path.parent.absolute()
    if _is_protected_state_root_path(
        plan_dir,
        state_root=state_root,
        managed_plan_root=managed_plan_root,
    ):
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
    return _remove_exact_plan_directory(
        plan_dir,
        identity,
        cleanup_anchor=_canonical_cleanup_anchor(
            plan_dir,
            state_root=state_root,
            managed_plan_root=managed_plan_root,
        ),
    )


def cleanup_superseded_plan_directories(
    new_plan_path: Path,
    *,
    namespace: str,
    state_root: Path,
    managed_plan_root: Path | None = None,
) -> list[str]:
    """Remove exact fully verified siblings superseded by one successful plan."""

    new_plan_dir = new_plan_path.parent.absolute()
    if _is_protected_state_root_path(
        new_plan_dir,
        state_root=state_root,
        managed_plan_root=managed_plan_root,
    ):
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
        if _is_protected_state_root_path(
            candidate,
            state_root=state_root,
            managed_plan_root=managed_plan_root,
        ):
            warnings.append(f"could not remove plan artifact directory under state root: {candidate}")
            continue
        identity = _verified_plan_identity(candidate)
        if (
            identity is None
            or identity.namespace != namespace
            or identity.created_at >= new_identity.created_at
        ):
            continue
        warnings.extend(
            _remove_exact_plan_directory(
                candidate,
                identity,
                cleanup_anchor=_canonical_cleanup_anchor(
                    candidate,
                    state_root=state_root,
                    managed_plan_root=managed_plan_root,
                ),
            )
        )
    return warnings


def _is_protected_state_root_path(
    path: Path,
    *,
    state_root: Path,
    managed_plan_root: Path | None,
) -> bool:
    """Protect the state root except for exact descendants of one managed plan root."""

    normalized_state_root = normalized_absolute(state_root)
    try:
        canonical_state_root = normalized_absolute(default_state_root())
        canonical_managed_root = normalized_absolute(default_artifact_root())
    except LocalPathError:
        return is_within(path, normalized_state_root)
    normalized_managed_root = (
        canonical_managed_root
        if managed_plan_root is None
        else normalized_absolute(managed_plan_root)
    )
    within_selected_state = is_within(path, normalized_state_root)
    within_canonical_home = is_within(path, canonical_state_root)
    if normalized_state_root != canonical_state_root and within_selected_state:
        return True
    if not within_selected_state and not within_canonical_home:
        return False
    if (
        normalized_managed_root != canonical_managed_root
        or not is_within(canonical_managed_root, canonical_state_root, strict=True)
        or not is_within(path, normalized_managed_root, strict=True)
        or not _real_directory_chain(canonical_state_root, canonical_managed_root)
        or not _real_directory_chain(normalized_managed_root, normalized_absolute(path))
    ):
        return True
    return False


def _canonical_cleanup_anchor(
    path: Path,
    *,
    state_root: Path,
    managed_plan_root: Path | None,
) -> Path | None:
    """Return the inode-bound root for the one canonical managed cleanup exception."""

    try:
        canonical_state_root = normalized_absolute(default_state_root())
        canonical_managed_root = normalized_absolute(default_artifact_root())
    except LocalPathError:
        return None
    normalized_managed_root = (
        canonical_managed_root
        if managed_plan_root is None
        else normalized_absolute(managed_plan_root)
    )
    if (
        normalized_managed_root == canonical_managed_root
        and is_within(path, canonical_managed_root, strict=True)
    ):
        return canonical_state_root
    return None


def _real_directory_chain(root: Path, target: Path) -> bool:
    """Require every existing component from ``root`` through ``target`` to be a real directory."""

    try:
        relative = target.relative_to(root)
    except ValueError:
        return False
    current = root
    for component in (Path("."), *relative.parts):
        if component != Path("."):
            current /= component
        try:
            observed = current.lstat()
        except OSError:
            return False
        if not stat.S_ISDIR(observed.st_mode) or current.is_symlink():
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
    """Fully verify a schema-v3 plan and bind it to its no-follow directory."""

    before = _directory_identity(plan_dir)
    if before is None:
        return None
    try:
        if {entry.name for entry in plan_dir.iterdir()} != {"plan.json", "delta.duckdb"}:
            return None
        plan_file_before = plan_dir.joinpath("plan.json").lstat()
        delta_file_before = plan_dir.joinpath("delta.duckdb").lstat()
        if not stat.S_ISREG(plan_file_before.st_mode) or not stat.S_ISREG(
            delta_file_before.st_mode
        ):
            return None
        from buoy_search.plan_artifacts import verify_plan_artifacts

        verified = verify_plan_artifacts(plan_dir / "plan.json")
    except (OSError, ValueError):
        return None
    after = _directory_identity(plan_dir)
    if before != after:
        return None
    try:
        plan_file_after = plan_dir.joinpath("plan.json").lstat()
        delta_file_after = plan_dir.joinpath("delta.duckdb").lstat()
    except OSError:
        return None
    if (
        (plan_file_before.st_dev, plan_file_before.st_ino)
        != (plan_file_after.st_dev, plan_file_after.st_ino)
        or (delta_file_before.st_dev, delta_file_before.st_ino)
        != (delta_file_after.st_dev, delta_file_after.st_ino)
    ):
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
        plan_file_device=plan_file_before.st_dev,
        plan_file_inode=plan_file_before.st_ino,
        delta_file_device=delta_file_before.st_dev,
        delta_file_inode=delta_file_before.st_ino,
    )


def _same_plan(left: _VerifiedPlanIdentity, right: _VerifiedPlanIdentity) -> bool:
    return (
        left.namespace,
        left.plan_id,
        left.artifact_hash,
        left.created_at,
        left.directory_device,
        left.directory_inode,
        left.plan_file_device,
        left.plan_file_inode,
        left.delta_file_device,
        left.delta_file_inode,
    ) == (
        right.namespace,
        right.plan_id,
        right.artifact_hash,
        right.created_at,
        right.directory_device,
        right.directory_inode,
        right.plan_file_device,
        right.plan_file_inode,
        right.delta_file_device,
        right.delta_file_inode,
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
    plan_dir: Path,
    expected: _VerifiedPlanIdentity,
    *,
    cleanup_anchor: Path | None,
) -> list[str]:
    """Atomically quarantine, reverify, then delete only the expected directory."""

    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        return [f"could not safely remove plan artifact directory on this platform: {plan_dir}"]

    try:
        if cleanup_anchor is None:
            flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            parent_fd = os.open(plan_dir.parent, flags)
        else:
            parent_fd = _open_directory_chain(plan_dir.parent, anchor=cleanup_anchor)
    except OSError as exc:
        return [f"could not open plan artifact parent for cleanup {plan_dir.parent}: {exc}"]

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

        quarantine_path = plan_dir.parent / quarantine_name
        after = _verified_plan_identity(quarantine_path)
        if after is None or not _same_plan(after, expected):
            warnings = _restore_quarantine(parent_fd, quarantine_name, plan_dir.name, plan_dir)
            return warnings or [f"could not remove replaced or unverified plan artifact directory: {plan_dir}"]
        return _remove_bound_quarantine(
            parent_fd,
            quarantine_name,
            expected=expected,
            display_path=plan_dir,
        )
    finally:
        os.close(parent_fd)


def _open_directory_chain(path: Path, *, anchor: Path) -> int:
    """Open a directory relative to an inode-bound anchor without following descendants."""

    normalized = normalized_absolute(path)
    normalized_anchor = normalized_absolute(anchor)
    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    if not hasattr(os, "O_NOFOLLOW"):
        raise OSError("O_NOFOLLOW is required for managed plan cleanup")
    flags |= os.O_NOFOLLOW

    if not normalized.is_absolute():
        raise OSError(f"plan artifact parent is not absolute: {normalized}")
    try:
        relative = normalized.relative_to(normalized_anchor)
    except ValueError as exc:
        raise OSError(
            f"plan artifact parent {normalized} is outside cleanup anchor {normalized_anchor}"
        ) from exc
    current_fd = os.open(normalized_anchor, flags)
    try:
        for component in relative.parts:
            next_fd = os.open(component, flags, dir_fd=current_fd)
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except BaseException:
        os.close(current_fd)
        raise


def _remove_bound_quarantine(
    parent_fd: int,
    quarantine_name: str,
    *,
    expected: _VerifiedPlanIdentity,
    display_path: Path,
) -> list[str]:
    """Bind the random quarantine contents, then use fd/symlink-safe removal."""

    flags = os.O_RDONLY | os.O_DIRECTORY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        quarantine_fd = os.open(quarantine_name, flags, dir_fd=parent_fd)
    except OSError as exc:
        return [f"could not bind quarantined plan artifact directory {display_path}: {exc}"]
    try:
        observed_dir = os.fstat(quarantine_fd)
        if (
            observed_dir.st_dev,
            observed_dir.st_ino,
        ) != (expected.directory_device, expected.directory_inode):
            return [f"could not remove replaced quarantined plan artifact directory: {display_path}"]
        expected_files = {
            "plan.json": (expected.plan_file_device, expected.plan_file_inode),
            "delta.duckdb": (expected.delta_file_device, expected.delta_file_inode),
        }
        with os.scandir(quarantine_fd) as entries:
            observed_names = {entry.name for entry in entries}
        if observed_names != set(expected_files):
            return [f"could not remove changed quarantined plan artifact directory: {display_path}"]
        for name, file_identity in expected_files.items():
            try:
                observed_file = os.stat(name, dir_fd=quarantine_fd, follow_symlinks=False)
            except OSError as exc:
                return [f"could not inspect quarantined plan artifact file {display_path / name}: {exc}"]
            if not stat.S_ISREG(observed_file.st_mode) or (
                observed_file.st_dev,
                observed_file.st_ino,
            ) != file_identity:
                return [f"could not remove replaced quarantined plan artifact file: {display_path / name}"]

    except OSError as exc:
        return [f"could not bind quarantined plan artifact files {display_path}: {exc}"]
    finally:
        os.close(quarantine_fd)

    try:
        shutil.rmtree(quarantine_name, dir_fd=parent_fd)
        os.fsync(parent_fd)
    except OSError as exc:
        return [f"could not remove quarantined plan artifact directory {display_path}: {exc}"]
    return []
