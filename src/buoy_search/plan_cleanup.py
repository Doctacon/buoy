"""Safe local lifecycle cleanup for verified plan artifact directories."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil


def cleanup_applied_plan_directory(plan_path: Path, *, state_root: Path) -> list[str]:
    """Remove one successfully applied, verified plan directory or return warnings."""

    plan_dir = plan_path.parent
    if _is_within_state_root(plan_dir, state_root):
        return [f"could not remove plan artifact directory under state root: {plan_dir}"]
    if _verified_plan_namespace(plan_dir) is None:
        return [f"could not remove unverified plan artifact directory: {plan_dir}"]
    return _remove_plan_directory(plan_dir)


def cleanup_superseded_plan_directories(
    new_plan_path: Path,
    *,
    namespace: str,
    state_root: Path,
) -> list[str]:
    """Remove verified sibling plans for the same namespace after a new plan succeeds."""

    new_plan_dir = new_plan_path.parent.absolute()
    if _is_within_state_root(new_plan_dir, state_root):
        return [f"could not inspect plan artifact directory under state root: {new_plan_dir}"]
    parent = new_plan_dir.parent
    if parent.is_symlink():
        return [f"could not inspect plan artifact parent symlink: {parent}"]

    try:
        candidates = list(parent.iterdir())
    except OSError as exc:
        return [f"could not inspect plan artifact parent {parent}: {exc}"]

    warnings: list[str] = []
    for candidate in candidates:
        if candidate.absolute() == new_plan_dir or candidate.is_symlink() or not candidate.is_dir():
            continue
        if _is_within_state_root(candidate, state_root):
            warnings.append(f"could not remove plan artifact directory under state root: {candidate}")
            continue
        if _verified_plan_namespace(candidate) != namespace:
            continue
        warnings.extend(_remove_plan_directory(candidate))
    return warnings


def _is_within_state_root(path: Path, state_root: Path) -> bool:
    """Return whether a path is lexically contained by the configured state root."""

    try:
        path.absolute().relative_to(state_root.absolute())
    except ValueError:
        return False
    return True


def _verified_plan_namespace(plan_dir: Path) -> str | None:
    """Return a namespace only for a regular, self-consistent plan directory."""

    if plan_dir.is_symlink() or not plan_dir.is_dir():
        return None
    plan_path = plan_dir / "plan.json"
    manifest_path = plan_dir / "manifest.json"
    if any(path.is_symlink() or not path.is_file() for path in (plan_path, manifest_path)):
        return None
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(plan, dict) or not isinstance(manifest, dict):
        return None
    namespace = plan.get("namespace")
    if plan.get("command") != "plan" or not isinstance(namespace, str) or not namespace:
        return None
    if manifest.get("namespace") != namespace:
        return None
    return namespace


def _remove_plan_directory(plan_dir: Path) -> list[str]:
    """Delete a verified plan directory without traversing any symlink."""

    if plan_dir.is_symlink() or _contains_symlink(plan_dir):
        return [f"could not remove plan artifact directory containing a symlink: {plan_dir}"]
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        return [f"could not safely remove plan artifact directory on this platform: {plan_dir}"]
    try:
        shutil.rmtree(plan_dir)
    except OSError as exc:
        return [f"could not remove plan artifact directory {plan_dir}: {exc}"]
    return []


def _contains_symlink(directory: Path) -> bool:
    for root, directories, files in os.walk(directory, followlinks=False):
        root_path = Path(root)
        if any((root_path / name).is_symlink() for name in [*directories, *files]):
            return True
    return False
