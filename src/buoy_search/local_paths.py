"""Canonical user-global paths for Buoy-owned local assets."""

from __future__ import annotations

import os
from pathlib import Path
import stat

from buoy_search.config import RuntimeConfigError


BUOY_HOME_NAME = ".buoy"
ARTIFACTS_RELATIVE_ROOT = Path("artifacts") / "site-crawls"


class LocalPathError(RuntimeConfigError):
    """Raised when the canonical Buoy home cannot be used safely."""


def normalized_absolute(path: Path) -> Path:
    """Return an absolute, dot-normalized path without resolving symlinks."""

    return Path(os.path.abspath(os.fspath(path)))


def default_buoy_home() -> Path:
    """Return the absolute user-global Buoy application home."""

    try:
        home = normalized_absolute(Path.home())
    except (OSError, RuntimeError) as exc:
        raise LocalPathError("could not resolve an absolute user home for Buoy") from exc
    if not home.is_absolute():  # defensive; ``abspath`` normally guarantees this.
        raise LocalPathError("could not resolve an absolute user home for Buoy")
    return home / BUOY_HOME_NAME


def default_state_root() -> Path:
    """Return the implicit applied-state root."""

    return default_buoy_home()


def default_artifact_root() -> Path:
    """Return the implicit crawl/plan root and apply discovery root."""

    return default_buoy_home() / ARTIFACTS_RELATIVE_ROOT


def is_within(path: Path, root: Path, *, strict: bool = False) -> bool:
    """Return whether ``path`` is lexically contained by ``root`` after dot normalization."""

    normalized_path = normalized_absolute(path)
    normalized_root = normalized_absolute(root)
    try:
        relative = normalized_path.relative_to(normalized_root)
    except ValueError:
        return False
    return not strict or relative != Path(".")


def prepare_default_buoy_home(path: Path, *, require_resolved_home: bool = False) -> None:
    """Create/validate the canonical home before a managed output writes below it.

    Explicit outputs outside the canonical home are caller-owned and unchanged.
    The function creates only the home boundary; command-specific code creates
    descendants using its existing lifecycle.
    """

    try:
        home = default_buoy_home()
    except LocalPathError:
        # Callers with an explicit output/state root must not acquire a hidden
        # dependency on the user's home directory. Implicit-root callers
        # resolve the home first and opt into the fail-closed path.
        if require_resolved_home:
            raise
        return
    if not is_within(path, home):
        return
    try:
        observed = home.lstat()
    except FileNotFoundError:
        try:
            home.mkdir(mode=0o700)
        except FileExistsError:
            observed = home.lstat()
        except OSError as exc:
            raise LocalPathError(f"could not create canonical Buoy home {home}: {exc}") from exc
        else:
            return
    except OSError as exc:
        raise LocalPathError(f"could not inspect canonical Buoy home {home}: {exc}") from exc

    if not stat.S_ISDIR(observed.st_mode) or home.is_symlink():
        raise LocalPathError(
            f"canonical Buoy home must be a real directory, not a symlink or other file: {home}"
        )
