#!/usr/bin/env python3
"""Read-only validation while Buoy release publication is paused."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tomllib
from typing import Any, Sequence
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
PAUSED_MESSAGE = (
    "Buoy release publication is paused while tag-derived versioning and "
    "publication policy are reconciled; no tag or GitHub Release was planned."
)
READ_ONLY_WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/release-readiness.yml",
    ".github/workflows/release.yml",
)
FORBIDDEN_WORKFLOW_MARKERS = (
    "contents: write",
    "id-token: write",
    "packages: write",
    "pull-requests: write",
    "write-all",
    "gh release",
    "git tag",
    "actions/attest",
    "actions/upload-artifact",
    "/releases",
    "/git/refs",
)
REMOVED_PACKAGE_MEMBERS = (
    "buoy_search/catalog.py",
    "buoy_search/catalog_cli.py",
    "buoy_search/catalog_pending.py",
    "buoy_search/command_center_api.py",
    "buoy_search/command_center_jobs.py",
    "buoy_search/command_center_local.py",
    "buoy_search/command_center_remote.py",
    "buoy_search/command_center_server.py",
    "buoy_search/evidence_cli.py",
    "buoy_search/evidence_remote.py",
    "buoy_search/evidence_snapshot.py",
    "buoy_search/experimental_baseline.py",
    "buoy_search/namespaces.py",
    "buoy_search/remote_catalog.py",
    "buoy_search/routing.py",
)
REMOVED_ARCHIVE_MEMBERS = (
    "docs/catalog.md",
    "docs/command-center.md",
    "docs/evidence-snapshots.md",
    "scripts/benchmark_command_center_bounded_review.py",
    "scripts/benchmark_command_center_inventory.py",
    "tests/test_automatic_routing.py",
    "tests/test_catalog.py",
    "tests/test_catalog_cli.py",
    "tests/test_catalog_pending.py",
    "tests/test_command_center_api.py",
    "tests/test_command_center_bounded_review_benchmark.py",
    "tests/test_command_center_cli.py",
    "tests/test_command_center_inventory_benchmark.py",
    "tests/test_command_center_jobs.py",
    "tests/test_command_center_local.py",
    "tests/test_command_center_remote.py",
    "tests/test_cutover_isolation.py",
    "tests/test_evidence_cli.py",
    "tests/test_evidence_remote.py",
    "tests/test_evidence_snapshot.py",
    "tests/test_experimental_baseline.py",
    "tests/test_multi_namespace_retrieval.py",
    "tests/test_namespaces.py",
    "tests/test_remote_catalog.py",
    "tests/test_semantic_routing_representative.py",
)
REMOVED_ARCHIVE_PREFIXES = (
    "autoresearch/runs/semantic-routing-representative-20260715/",
)
REQUIRED_PACKAGE_MEMBERS = (
    "buoy_search/__init__.py",
    "buoy_search/__main__.py",
    "buoy_search/_version.py",
    "buoy_search/applied_state.py",
    "buoy_search/apply.py",
    "buoy_search/cli.py",
    "buoy_search/planning_service.py",
    "buoy_search/retriever.py",
)
TOKENIZER_MEMBER_SUFFIXES = (
    "data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/special_tokens_map.json",
    "data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/tokenizer.json",
    "data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/tokenizer_config.json",
    "data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/vocab.txt",
)


class ReleaseError(ValueError):
    """A source or read-only release invariant was not satisfied."""


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_read_only_workflow(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ReleaseError(f"{path} is not valid workflow YAML") from exc
    if not isinstance(payload, dict):
        raise ReleaseError(f"{path} must contain a workflow object")
    if payload.get("permissions") != {"contents": "read"}:
        raise ReleaseError(f"{path} must declare read-only contents: read")
    jobs = payload.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        raise ReleaseError(f"{path} must contain a non-empty jobs object")
    for job_name, job in jobs.items():
        if not isinstance(job_name, str) or not isinstance(job, dict):
            raise ReleaseError(f"{path} contains an invalid job")
        if "permissions" in job and job["permissions"] != {"contents": "read"}:
            raise ReleaseError(
                f"{path} job {job_name!r} may not escalate workflow permissions"
            )
    return payload


def _member_matches(name: str, member: str) -> bool:
    return name == member or name.endswith(f"/{member}")


def _validate_archive_members(names: list[str], *, archive: str) -> None:
    forbidden = [
        name
        for name in names
        if "/.10x/" in f"/{name}"
        or "/web/" in f"/{name}"
        or "/node_modules/" in f"/{name}"
        or "/command_center_static/" in f"/{name}"
        or any(_member_matches(name, member) for member in REMOVED_PACKAGE_MEMBERS)
        or any(_member_matches(name, member) for member in REMOVED_ARCHIVE_MEMBERS)
        or any(
            f"/{prefix}" in f"/{name}" for prefix in REMOVED_ARCHIVE_PREFIXES
        )
    ]
    if forbidden:
        raise ReleaseError(f"{archive} contains removed product surfaces: {forbidden}")
    missing = [
        member
        for member in REQUIRED_PACKAGE_MEMBERS
        if not any(_member_matches(name, member) for name in names)
    ]
    if missing:
        raise ReleaseError(f"{archive} is missing focused package members: {missing}")
    missing_tokenizer = [
        suffix
        for suffix in TOKENIZER_MEMBER_SUFFIXES
        if not any(name.endswith(suffix) for name in names)
    ]
    if missing_tokenizer:
        raise ReleaseError(f"{archive} is missing bundled tokenizer files: {missing_tokenizer}")


def _metadata_version(payload: bytes) -> str:
    for line in payload.decode("utf-8").splitlines():
        if line.startswith("Version: "):
            version = line.removeprefix("Version: ").strip()
            if version:
                return version
    raise ReleaseError("distribution metadata has no version")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_distribution(dist: Path) -> dict[str, object]:
    """Inspect one diagnostic wheel/sdist pair without publishing it."""

    dist = Path(dist)
    files = sorted(
        path for path in dist.iterdir() if path.is_file() and path.name != ".gitignore"
    )
    wheels = [path for path in files if path.suffix == ".whl"]
    sdists = [path for path in files if path.name.endswith(".tar.gz")]
    if len(wheels) != 1 or len(sdists) != 1 or len(files) != 2:
        raise ReleaseError("distribution directory must contain exactly one wheel and one sdist")
    wheel = wheels[0]
    sdist = sdists[0]

    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        _validate_archive_members(wheel_names, archive="wheel")
        metadata = [name for name in wheel_names if name.endswith(".dist-info/METADATA")]
        entries = [name for name in wheel_names if name.endswith(".dist-info/entry_points.txt")]
        if len(metadata) != 1:
            raise ReleaseError("wheel must contain exactly one METADATA file")
        if len(entries) != 1:
            raise ReleaseError("wheel must contain exactly one entry_points.txt")
        wheel_version = _metadata_version(archive.read(metadata[0]))
        entry_points = archive.read(entries[0]).decode("utf-8").strip()
        if entry_points != "[console_scripts]\nbuoy = buoy_search.cli:main":
            raise ReleaseError("wheel must expose only the buoy console entry point")

    with tarfile.open(sdist, "r:gz") as archive:
        sdist_names = archive.getnames()
        _validate_archive_members(sdist_names, archive="sdist")
        metadata = [
            member for member in archive.getmembers() if member.name.endswith("/PKG-INFO")
        ]
        if len(metadata) != 1:
            raise ReleaseError("sdist must contain exactly one PKG-INFO")
        extracted = archive.extractfile(metadata[0])
        if extracted is None:
            raise ReleaseError("sdist PKG-INFO could not be read")
        sdist_version = _metadata_version(extracted.read())
        if not any(name.endswith("/images/buoy.svg") for name in sdist_names):
            raise ReleaseError("sdist must contain images/buoy.svg")

    if wheel_version != sdist_version:
        raise ReleaseError("wheel and sdist metadata versions do not match")
    return {
        "version": wheel_version,
        "wheel": {
            "name": wheel.name,
            "files": len(wheel_names),
            "sha256": _sha256(wheel),
        },
        "sdist": {
            "name": sdist.name,
            "files": len(sdist_names),
            "sha256": _sha256(sdist),
        },
        "publication_occurred": False,
    }


def validate_source(root: Path = ROOT) -> dict[str, object]:
    """Validate dynamic source metadata without deriving or publishing a version."""

    pyproject = _load_toml(root / "pyproject.toml")
    project = pyproject.get("project", {})
    if "version" in project:
        raise ReleaseError("project.version must remain absent under Hatch VCS")
    if project.get("dynamic") != ["version"]:
        raise ReleaseError("project.dynamic must be exactly ['version']")

    build = pyproject.get("build-system", {})
    if build.get("build-backend") != "hatchling.build":
        raise ReleaseError("build backend must remain hatchling.build")
    if build.get("requires") != ["hatchling==1.31.0", "hatch-vcs==0.5.0"]:
        raise ReleaseError("Hatch and Hatch-VCS build requirements must remain exactly pinned")
    if pyproject.get("tool", {}).get("hatch", {}).get("version") != {"source": "vcs"}:
        raise ReleaseError("Hatch version authority must remain VCS")
    hook = (
        pyproject.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("hooks", {})
        .get("vcs")
    )
    if hook != {"version-file": "src/buoy_search/_version.py"}:
        raise ReleaseError("Hatch VCS must generate src/buoy_search/_version.py")

    module = (root / "src/buoy_search/__init__.py").read_text(encoding="utf-8")
    if "from ._version import __version__" not in module:
        raise ReleaseError("buoy_search.__version__ must come from generated _version.py")
    ignored = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    if "src/buoy_search/_version.py" not in ignored:
        raise ReleaseError("generated _version.py must remain ignored")

    lock = _load_toml(root / "uv.lock")
    roots = [package for package in lock.get("package", []) if package.get("name") == "buoy-search"]
    if len(roots) != 1:
        raise ReleaseError("uv.lock must contain exactly one buoy-search root package")
    locked_root = roots[0]
    if "version" in locked_root or locked_root.get("source") != {"editable": "."}:
        raise ReleaseError("uv.lock root package must be editable and versionless")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = [line for line in changelog.splitlines() if line.startswith("## ")]
    if len(headings) < 2 or headings[0] != "## Unreleased":
        raise ReleaseError("CHANGELOG must begin with an Unreleased section")
    if headings[1] != "## [0.4.0] - 2026-07-21":
        raise ReleaseError("published changelog history must remain frozen through v0.4.0")
    if any(" - pending" in heading for heading in headings):
        raise ReleaseError("paused publication must not stage a pending release heading")

    for relative in READ_ONLY_WORKFLOWS:
        path = root / relative
        _load_read_only_workflow(path)
        text = path.read_text(encoding="utf-8")
        marker = next(
            (item for item in FORBIDDEN_WORKFLOW_MARKERS if item.casefold() in text.casefold()),
            None,
        )
        if marker is not None:
            raise ReleaseError(f"{relative} contains forbidden publication marker {marker!r}")

    return {
        "dynamic_version": True,
        "generated_version_file": "src/buoy_search/_version.py",
        "published_history_through": "0.4.0",
        "publication_paused": True,
        "workflows_read_only": list(READ_ONLY_WORKFLOWS),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "validate-source",
        help="validate dynamic source metadata and read-only workflows",
    )
    distribution = commands.add_parser(
        "validate-distribution",
        help="inspect a diagnostic wheel/sdist pair without publication",
    )
    distribution.add_argument("dist", type=Path)
    for legacy in ("validate", "artifacts", "state", "github-snapshot", "policy"):
        commands.add_parser(
            legacy,
            help="disabled while release publication is paused",
            add_help=False,
        )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if values and values[0] in {"validate", "artifacts", "state", "github-snapshot", "policy"}:
        print(PAUSED_MESSAGE, file=sys.stderr)
        return 2
    args = build_parser().parse_args(values)
    try:
        result = (
            validate_source()
            if args.command == "validate-source"
            else validate_distribution(args.dist)
        )
    except (OSError, ReleaseError, tarfile.TarError, tomllib.TOMLDecodeError, zipfile.BadZipFile) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.command in {"validate-source", "validate-distribution"}:
        print(json.dumps(result, sort_keys=True))
        return 0
    print(PAUSED_MESSAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
