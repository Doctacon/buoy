#!/usr/bin/env python3
"""Deterministic, side-effect-free release validation and state planning."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tomllib
from datetime import date
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "Doctacon/buoy-search"
WORKFLOW = "release.yml"
SOURCE_REF = "refs/heads/main"
LEGACY_V040_TAG = "v0.4.0"
LEGACY_V040_SHA = "c49dc0582bf3f06a16eafdcca0707d1e64e1c58d"
LEGACY_V040_SOURCE_REF = "refs/tags/v0.4.0"
LEGACY_V040_ASSETS = {
    "buoy_search-0.4.0-py3-none-any.whl": "89b84c6beba2979ab6ffd0d244d1d0f5c1af938cfbec021a89094a7109e5c4c8",
    "buoy_search-0.4.0.tar.gz": "9c0469d2fc03b8e03780b06793537736391c21f0ed07c43adab9e674988ffd3a",
}
VERSION_RE = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")
RELEASE_POLICY_GLOBS = (
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "scripts/*release*.py",
    "scripts/*release*.sh",
)
FORBIDDEN_RELEASE_SERVICES = re.compile(
    rf"\b(?:{'py' + 'pi'}|{'turbo' + 'puffer'})\b", re.IGNORECASE
)
BOT = {
    "name": "github-actions[bot]",
    "email": "41898282+github-actions[bot]@users.noreply.github.com",
}


class ReleaseError(ValueError):
    """A release invariant was not satisfied."""


def _load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def versions(root: Path = ROOT) -> dict[str, str]:
    project = str(_load_toml(root / "pyproject.toml")["project"]["version"])
    module_text = (root / "src" / "buoy_search" / "__init__.py").read_text()
    match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', module_text, re.MULTILINE)
    if match is None:
        raise ReleaseError("module does not declare __version__")
    lock = _load_toml(root / "uv.lock")
    locked = [str(item["version"]) for item in lock["package"] if item["name"] == "buoy-search"]
    if len(locked) != 1:
        raise ReleaseError("uv.lock must contain exactly one buoy-search package")
    return {"project": project, "module": match.group(1), "lock": locked[0]}


def validate_versions(root: Path = ROOT) -> str:
    observed = versions(root)
    if len(set(observed.values())) != 1:
        raise ReleaseError(f"version mismatch: {observed}")
    version = observed["project"]
    if VERSION_RE.fullmatch(version) is None:
        raise ReleaseError(f"version must be stable MAJOR.MINOR.PATCH: {version!r}")
    return version


def validate_changelog(version: str, root: Path = ROOT) -> None:
    text = (root / "CHANGELOG.md").read_text()
    headings = list(re.finditer(r"^## (.+)$", text, re.MULTILINE))
    if not headings or headings[0].group(1) != "[Unreleased]":
        raise ReleaseError("CHANGELOG must begin release history with [Unreleased]")
    unreleased = text[headings[0].end() : headings[1].start() if len(headings) > 1 else len(text)]
    if unreleased.strip():
        raise ReleaseError("CHANGELOG Unreleased section must be empty")
    expected = f"[{version}] - pending"
    if sum(heading.group(1) == expected for heading in headings) != 1:
        raise ReleaseError(f"CHANGELOG must contain exactly '## {expected}'")
    dated = re.compile(r"\[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})")
    released = [heading.group(1) for heading in headings if heading.group(1).startswith("[")]
    for heading in released[2:]:
        match = dated.fullmatch(heading)
        if match is None:
            raise ReleaseError(f"older CHANGELOG release must have ISO date: {heading!r}")
        try:
            date.fromisoformat(match.group(2))
        except ValueError as exc:
            raise ReleaseError(f"older CHANGELOG release has invalid ISO date: {heading!r}") from exc


def validate_release_policy(root: Path = ROOT) -> None:
    relevant = sorted({path for pattern in RELEASE_POLICY_GLOBS for path in root.glob(pattern)})
    violations = [
        str(path.relative_to(root))
        for path in relevant
        if FORBIDDEN_RELEASE_SERVICES.search(path.read_text())
    ]
    if violations:
        raise ReleaseError(
            "release behavior references a forbidden publication service: " + ", ".join(violations)
        )


def validate_repository(root: Path = ROOT) -> str:
    version = validate_versions(root)
    validate_changelog(version, root)
    return version


def expected_asset_names(version: str) -> list[str]:
    return [f"buoy_search-{version}-py3-none-any.whl", f"buoy_search-{version}.tar.gz"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metadata_version(payload: bytes) -> str:
    match = re.search(rb"^Version: ([^\r\n]+)", payload, re.MULTILINE)
    if match is None:
        raise ReleaseError("distribution metadata has no Version")
    return match.group(1).decode()


def _forbidden_inventory(names: list[str]) -> list[str]:
    return [
        name
        for name in names
        if ".10x/" in name
        or "turbo-search" in name
        or "turbo_search" in name
        or "legacy_main" in name
    ]


def verify_artifacts(dist: Path, root: Path = ROOT) -> dict[str, Any]:
    version = validate_versions(root)
    expected = expected_asset_names(version)
    actual = (
        sorted(path.name for path in dist.iterdir() if path.is_file() and path.name != ".gitignore")
        if dist.is_dir()
        else []
    )
    if actual != expected:
        raise ReleaseError(f"asset names mismatch: expected {expected}, received {actual}")
    wheel, sdist = (dist / name for name in expected)
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        forbidden = _forbidden_inventory(wheel_names)
        if forbidden:
            raise ReleaseError(f"forbidden wheel inventory: {forbidden}")
        metadata_names = [name for name in wheel_names if name.endswith(".dist-info/METADATA")]
        entry_names = [name for name in wheel_names if name.endswith(".dist-info/entry_points.txt")]
        if len(metadata_names) != 1 or _metadata_version(archive.read(metadata_names[0])) != version:
            raise ReleaseError("wheel metadata version mismatch")
        if len(entry_names) != 1:
            raise ReleaseError("wheel must contain entry_points.txt")
        entry_points = archive.read(entry_names[0]).decode().strip()
        if entry_points != "[console_scripts]\nbuoy = buoy_search.cli:main":
            raise ReleaseError(f"wheel entry points mismatch: {entry_points!r}")
        tokenizer_suffixes = ("special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt")
        for suffix in tokenizer_suffixes:
            if not any(name.endswith("/data/bge-small-en-v1.5/5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/" + suffix) for name in wheel_names):
                raise ReleaseError(f"wheel missing bundled tokenizer file {suffix}")
    with tarfile.open(sdist, "r:gz") as archive:
        sdist_names = archive.getnames()
        forbidden = _forbidden_inventory(sdist_names)
        if forbidden:
            raise ReleaseError(f"forbidden sdist inventory: {forbidden}")
        metadata = [member for member in archive.getmembers() if member.name.endswith("/PKG-INFO")]
        if len(metadata) != 1:
            raise ReleaseError("sdist must contain one PKG-INFO")
        extracted = archive.extractfile(metadata[0])
        if extracted is None or _metadata_version(extracted.read()) != version:
            raise ReleaseError("sdist metadata version mismatch")
        for suffix in tokenizer_suffixes:
            if not any(
                name.endswith(
                    "/src/buoy_search/data/bge-small-en-v1.5/"
                    "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a/" + suffix
                )
                for name in sdist_names
            ):
                raise ReleaseError(f"sdist missing bundled tokenizer file {suffix}")
    assets = [{"name": name, "sha256": sha256_file(dist / name)} for name in expected]
    return {"version": version, "tag": f"v{version}", "assets": assets}


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n")


def _asset_map(assets: list[dict[str, Any]]) -> dict[str, str]:
    return {str(asset["name"]): str(asset["sha256"]) for asset in assets}


def _asset_pairs(assets: list[dict[str, Any]]) -> list[tuple[str, str]]:
    return sorted((str(asset["name"]), str(asset["sha256"])) for asset in assets)


def expected_provenance(
    manifest: dict[str, Any], sha: str, *, source_ref: str = SOURCE_REF
) -> list[dict[str, str]]:
    return [
        {
            "name": asset["name"],
            "sha256": asset["sha256"],
            "repository": REPOSITORY,
            "workflow": WORKFLOW,
            "source_ref": source_ref,
            "source_commit": sha,
        }
        for asset in manifest["assets"]
    ]


def _is_legacy_v040(manifest: dict[str, Any], sha: str) -> bool:
    return (
        manifest.get("version") == "0.4.0"
        and manifest.get("tag") == LEGACY_V040_TAG
        and sha == LEGACY_V040_SHA
        and _asset_pairs(manifest.get("assets", [])) == sorted(LEGACY_V040_ASSETS.items())
    )


def evaluate_state(snapshot: dict[str, Any], manifest: dict[str, Any], sha: str) -> str:
    tag = snapshot.get("tag")
    release = snapshot.get("release")
    if tag is None and release is None:
        return "create"
    if tag is None or release is None:
        raise ReleaseError("permanent failure: tag-only or Release-only state")
    expected_tag = manifest["tag"]
    if tag.get("name") != expected_tag or tag.get("object_type") != "tag":
        raise ReleaseError("permanent failure: tag is missing or lightweight")
    if tag.get("peel_sha") != sha:
        raise ReleaseError("permanent failure: annotated tag peels to another commit")
    legacy_v040 = _is_legacy_v040(manifest, sha)
    expected_release = {
        "tag_name": expected_tag,
        "name": "Buoy v0.4.0" if legacy_v040 else f"Buoy {manifest['version']}",
        "draft": False,
        "prerelease": False,
        "target": expected_tag,
    }
    for field, expected in expected_release.items():
        if release.get(field) != expected:
            raise ReleaseError(f"permanent failure: Release {field} mismatch")
    if _asset_pairs(release.get("assets", [])) != _asset_pairs(manifest["assets"]):
        raise ReleaseError("permanent failure: Release asset names or digests mismatch")
    actual_provenance = snapshot.get("provenance", [])
    source_ref = LEGACY_V040_SOURCE_REF if legacy_v040 else SOURCE_REF
    wanted_provenance = expected_provenance(manifest, sha, source_ref=source_ref)
    if any(item not in actual_provenance for item in wanted_provenance):
        raise ReleaseError("permanent failure: provenance mismatch")
    return "noop"


def make_plan(snapshot: dict[str, Any], manifest: dict[str, Any], sha: str) -> dict[str, Any]:
    if re.fullmatch(r"[0-9a-f]{40}", sha) is None:
        raise ReleaseError("source commit must be a full 40-character SHA")
    action = evaluate_state(snapshot, manifest, sha)
    legacy_v040_noop = action == "noop" and _is_legacy_v040(manifest, sha)
    plan = {
        "schema": 1,
        "action": action,
        "repository": REPOSITORY,
        "workflow": WORKFLOW,
        "source_ref": SOURCE_REF,
        "source_commit": sha,
        "version": manifest["version"],
        "tag": manifest["tag"],
        "tag_message": f"Buoy {manifest['version']}",
        "tagger": BOT,
        "release_name": "Buoy v0.4.0" if legacy_v040_noop else f"Buoy {manifest['version']}",
        "assets": manifest["assets"],
        "provenance": expected_provenance(
            manifest,
            sha,
            source_ref=LEGACY_V040_SOURCE_REF if legacy_v040_noop else SOURCE_REF,
        ),
    }
    encoded = json.dumps(plan, sort_keys=True, separators=(",", ":")).encode()
    return {"plan": plan, "sha256": hashlib.sha256(encoded).hexdigest()}


def validate_policy(
    *,
    head_repository: str,
    head_ref: str,
    base_sha: str,
    head_sha: str,
    snapshot: dict[str, Any],
    root: Path = ROOT,
) -> str:
    if (head_repository, head_ref) != (REPOSITORY, "develop"):
        raise ReleaseError("release PR head must be Doctacon/buoy-search:develop")
    parents = subprocess.run(
        ["git", "rev-list", "--parents", "-n", "1", "HEAD"],
        cwd=root,
        text=True,
        check=True,
        capture_output=True,
    ).stdout.split()
    if len(parents) != 3 or parents[1:] != [base_sha, head_sha]:
        raise ReleaseError("checkout is not GitHub's exact prospective merge commit")
    version = validate_repository(root)
    validate_release_policy(root)
    if snapshot.get("tag") is not None or snapshot.get("release") is not None:
        raise ReleaseError(f"v{version} already has a tag or GitHub Release")
    return version


def _api(path: str, token: str, *, accept: str = "application/vnd.github+json") -> Any:
    request = Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": accept,
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "buoy-release-automation",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
            return json.loads(payload) if payload else None
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise ReleaseError(f"GitHub API {path} returned HTTP {exc.code}") from exc


def _attestation_statement(item: dict[str, Any]) -> dict[str, Any] | None:
    envelope = item.get("bundle", {}).get("dsseEnvelope", {})
    payload = envelope.get("payload")
    if not payload:
        return None
    return json.loads(base64.b64decode(payload))


def _normalize_provenance(statement: dict[str, Any], asset_name: str, digest: str) -> dict[str, str] | None:
    subjects = statement.get("subject", [])
    if not any(subject.get("name") == asset_name and subject.get("digest", {}).get("sha256") == digest for subject in subjects):
        return None
    predicate = statement.get("predicate", {})
    build = predicate.get("buildDefinition", {})
    external = build.get("externalParameters", {}).get("workflow", {})
    dependencies = build.get("resolvedDependencies", [])
    commit = next((item.get("digest", {}).get("gitCommit") for item in dependencies if item.get("digest", {}).get("gitCommit")), None)
    repository = str(external.get("repository", ""))
    for prefix in ("git+https://github.com/", "https://github.com/"):
        if repository.startswith(prefix):
            repository = repository.removeprefix(prefix)
            break
    repository = repository.removesuffix(".git")
    workflow_path = str(external.get("path", ""))
    return {
        "name": asset_name,
        "sha256": digest,
        "repository": repository,
        "workflow": workflow_path.rsplit("/", 1)[-1],
        "source_ref": str(external.get("ref", "")),
        "source_commit": str(commit or ""),
    }


def github_snapshot(tag_name: str, manifest: dict[str, Any], token: str) -> dict[str, Any]:
    ref = _api(f"/repos/{REPOSITORY}/git/ref/tags/{tag_name}", token)
    tag: dict[str, Any] | None = None
    if ref is not None:
        object_type = ref["object"]["type"]
        peel_sha = ref["object"]["sha"]
        if object_type == "tag":
            tag_object = _api(f"/repos/{REPOSITORY}/git/tags/{peel_sha}", token)
            peel_sha = tag_object["object"]["sha"]
        tag = {"name": tag_name, "object_type": object_type, "peel_sha": peel_sha}
    hosted = _api(f"/repos/{REPOSITORY}/releases/tags/{tag_name}", token)
    release: dict[str, Any] | None = None
    provenance: list[dict[str, str]] = []
    if hosted is not None:
        assets: list[dict[str, str]] = []
        expected_assets = _asset_map(manifest.get("assets", []))
        for asset in hosted.get("assets", []):
            name = str(asset["name"])
            digest = str(asset.get("digest") or "")
            if digest.startswith("sha256:"):
                digest = digest.removeprefix("sha256:")
            else:
                raise ReleaseError(f"GitHub asset {name!r} has no authoritative SHA-256 digest")
            assets.append({"name": name, "sha256": digest})
            if expected_assets.get(name) == digest:
                attestations = _api(f"/repos/{REPOSITORY}/attestations/sha256:{digest}", token) or {}
                for item in attestations.get("attestations", []):
                    statement = _attestation_statement(item)
                    if statement is not None:
                        normalized = _normalize_provenance(statement, name, digest)
                        if normalized is not None:
                            provenance.append(normalized)
        release = {
            "tag_name": hosted.get("tag_name"),
            "name": hosted.get("name"),
            "draft": hosted.get("draft"),
            "prerelease": hosted.get("prerelease"),
            # An existing tag makes tag_name the immutable Release target identity;
            # target_commitish is only GitHub's mutable branch-name creation hint.
            "target": hosted.get("tag_name"),
            "assets": assets,
        }
    return {"tag": tag, "release": release, "provenance": provenance}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate")
    assets = commands.add_parser("artifacts")
    assets.add_argument("--dist", type=Path, required=True)
    assets.add_argument("--output", type=Path, required=True)
    state = commands.add_parser("state")
    state.add_argument("--snapshot", type=Path, required=True)
    state.add_argument("--manifest", type=Path, required=True)
    state.add_argument("--sha", required=True)
    state.add_argument("--output", type=Path, required=True)
    snapshot = commands.add_parser("github-snapshot")
    snapshot.add_argument("--manifest", type=Path, required=True)
    snapshot.add_argument("--output", type=Path, required=True)
    policy = commands.add_parser("policy")
    policy.add_argument("--head-repository", required=True)
    policy.add_argument("--head-ref", required=True)
    policy.add_argument("--base-sha", required=True)
    policy.add_argument("--head-sha", required=True)
    policy.add_argument("--snapshot", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            print(validate_repository())
        elif args.command == "artifacts":
            write_json(args.output, verify_artifacts(args.dist))
        elif args.command == "state":
            snapshot = json.loads(args.snapshot.read_text())
            manifest = json.loads(args.manifest.read_text())
            write_json(args.output, make_plan(snapshot, manifest, args.sha))
        elif args.command == "github-snapshot":
            token = os.environ.get("GITHUB_TOKEN", "")
            if not token:
                raise ReleaseError("GITHUB_TOKEN is required")
            manifest = json.loads(args.manifest.read_text())
            write_json(args.output, github_snapshot(manifest["tag"], manifest, token))
        else:
            snapshot = json.loads(args.snapshot.read_text())
            print(
                validate_policy(
                    head_repository=args.head_repository,
                    head_ref=args.head_ref,
                    base_sha=args.base_sha,
                    head_sha=args.head_sha,
                    snapshot=snapshot,
                )
            )
    except (OSError, ReleaseError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
