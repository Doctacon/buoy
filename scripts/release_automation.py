#!/usr/bin/env python3
"""Read-only validation while Buoy release publication is paused."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tarfile
import tomllib
from typing import Any, Sequence
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
PAUSED_MESSAGE = (
    "Automated Buoy release publication remains paused; v0.5.1 is published "
    "and its one-time manual release authority is consumed."
)
READ_ONLY_WORKFLOWS = (
    ".github/workflows/ci.yml",
    ".github/workflows/release-readiness.yml",
    ".github/workflows/release.yml",
)
BUOY_CONSOLE_TARGET = "buoy_search.entrypoint:main"
BUOY_CONSOLE_SCRIPTS = {"buoy": BUOY_CONSOLE_TARGET}
BUOY_CONSOLE_ENTRY_POINTS = (
    "[console_scripts]\n"
    f"buoy = {BUOY_CONSOLE_TARGET}"
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
)
REMOVED_ARCHIVE_MEMBERS = (
    "docs/command-center.md",
    "docs/evidence-snapshots.md",
    "scripts/benchmark_command_center_bounded_review.py",
    "scripts/benchmark_command_center_inventory.py",
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
    "buoy_search/catalog.py",
    "buoy_search/catalog_cli.py",
    "buoy_search/cli.py",
    "buoy_search/cross_encoder.py",
    "buoy_search/data/automatic_multi_corpus_retrieval_evals.json",
    "buoy_search/data/automatic_retrieval_evidence_calibration.json",
    "buoy_search/data/automatic_routing_confidence_calibration.json",
    "buoy_search/data/routing_canaries/rentptr.json",
    "buoy_search/data/routing_canaries/salesforce.json",
    "buoy_search/data/routing_canaries/whiteboxgeo.json",
    "buoy_search/evidence.py",
    "buoy_search/evidence_evals.py",
    "buoy_search/entrypoint.py",
    "buoy_search/multi_corpus_evals.py",
    "buoy_search/planning_service.py",
    "buoy_search/remote_catalog.py",
    "buoy_search/retriever.py",
    "buoy_search/routing.py",
    "buoy_search/routing_quality.py",
    "buoy_search/telemetry.py",
    "buoy_search/telemetry_cli.py",
    "buoy_search/telemetry_envelope.py",
    "buoy_search/telemetry_queue.py",
    "buoy_search/telemetry_store.py",
    "buoy_search/telemetry_writer.py",
)
ROUTING_CANARY_MEMBERS = {
    "buoy_search/data/routing_canaries/rentptr.json": (
        "5a39c38d302cbc5c6d758b1e48d4456456a4357248f559a6cf56e0234742f4f5"
    ),
    "buoy_search/data/routing_canaries/salesforce.json": (
        "32106e02d877788e676cdb3db3f7a3567f57f96fa009a7a558b82ca1d407d13d"
    ),
    "buoy_search/data/routing_canaries/whiteboxgeo.json": (
        "5558a4e8a786f0a5553ba0237ebf8248a5d576bd1937ffd69cf9af66a8ac0916"
    ),
}
ROUTING_CANARY_LEGACY_MEMBER = (
    "buoy_search/data/automatic_multi_corpus_retrieval_evals.json"
)
ROUTING_CANARY_LEGACY_DATASET_ID = "automatic-multi-corpus-retrieval-v1"
ROUTING_CANARY_LEGACY_DATASET_SHA256 = (
    "29064e773a71e2f31a4e6af45db793cdb30436dbf9fc61e818a03dd127ce1e2b"
)
ROUTING_CANARY_SUITE_SHA256 = (
    "0e648b1222298b443439aa8b85527048b54f51b7ef2518956d43cd6bee2981e5"
)
ROUTING_CONFIDENCE_ARTIFACT_MEMBER = (
    "buoy_search/data/automatic_routing_confidence_calibration.json"
)
ROUTING_COLLECT_ARTIFACT_SHA256 = (
    "23fb14c49263933a2adb2299a9c04089888fb2ec734b790d9eadda2df295cbed"
)
ACTIVE_ROUTING_RECEIPT_MODULES = {
    "evaluator_scorer_sha256": "buoy_search/routing_quality.py",
    "routing_module_sha256": "buoy_search/routing.py",
    "cli_module_sha256": "buoy_search/cli.py",
    "evidence_module_sha256": "buoy_search/evidence.py",
}
ACTIVE_ROUTING_RUNNER_RECEIPT = (
    "evaluator_runner_sha256",
    "scripts/evaluate_routing_quality.py",
)
REQUIRED_SDIST_MEMBERS = (
    "scripts/evaluate_multi_corpus_retrieval.py",
    "scripts/evaluate_routing_quality.py",
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


def _routing_canary_member(name: str) -> str | None:
    marker = "buoy_search/data/routing_canaries/"
    index = name.find(marker)
    if index < 0:
        return None
    return name[index:]


def _validate_routing_canary_inventory(
    names: Sequence[str], *, where: str
) -> None:
    actual = [
        logical
        for name in names
        if (logical := _routing_canary_member(name)) is not None
    ]
    expected = sorted(ROUTING_CANARY_MEMBERS)
    if sorted(actual) != expected:
        raise ReleaseError(
            f"{where} routing canary inventory must be exactly {expected}; "
            f"found {sorted(actual)}"
        )


def _stable_hash(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_strict_json(raw: bytes, *, where: str) -> object:
    def reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise ReleaseError(f"{where} contains duplicate fields")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ReleaseError(f"{where} contains non-finite value {value}")

    try:
        return json.loads(
            raw,
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"{where} is not valid JSON") from exc


def _validate_routing_authority_bytes(
    artifact: bytes,
    modules: dict[str, bytes],
    *,
    where: str,
) -> dict[str, object]:
    expected_modules = sorted(ACTIVE_ROUTING_RECEIPT_MODULES.values())
    if sorted(modules) != expected_modules:
        raise ReleaseError(
            f"{where} routing authority must include exact module bytes for "
            f"{expected_modules}; found {sorted(modules)}"
        )
    artifact_sha256 = hashlib.sha256(artifact).hexdigest()
    payload = _load_strict_json(artifact, where=f"{where} routing authority")
    if not isinstance(payload, dict):
        raise ReleaseError(f"{where} routing authority must be a JSON object")
    mode = payload.get("mode")
    if mode == "collect":
        if artifact_sha256 != ROUTING_COLLECT_ARTIFACT_SHA256:
            raise ReleaseError(
                f"{where} collect routing authority does not match its governed bytes"
            )
        return {
            "mode": "collect",
            "artifact_sha256": artifact_sha256,
            "active_module_receipts_validated": False,
            "module_sha256": None,
        }
    if mode != "active":
        raise ReleaseError(f"{where} routing authority mode is invalid")

    receipts = payload.get("receipts")
    if not isinstance(receipts, dict):
        raise ReleaseError(f"{where} active routing authority has no receipts")
    module_hashes = {
        member: hashlib.sha256(modules[member]).hexdigest()
        for member in expected_modules
    }
    for receipt_field, member in ACTIVE_ROUTING_RECEIPT_MODULES.items():
        receipt = receipts.get(receipt_field)
        if not isinstance(receipt, str) or re.fullmatch(r"[0-9a-f]{64}", receipt) is None:
            raise ReleaseError(
                f"{where} active routing receipt {receipt_field!r} is invalid"
            )
        if receipt != module_hashes[member]:
            raise ReleaseError(
                f"{where} active routing receipt {receipt_field!r} does not "
                f"match {member}"
            )
    return {
        "mode": "active",
        "artifact_sha256": artifact_sha256,
        "active_module_receipts_validated": True,
        "module_sha256": module_hashes,
    }


def _validate_routing_runner_receipt(
    artifact: bytes,
    runner: bytes,
    *,
    where: str,
) -> dict[str, object]:
    payload = _load_strict_json(artifact, where=f"{where} routing authority")
    if not isinstance(payload, dict):
        raise ReleaseError(f"{where} routing authority must be a JSON object")
    mode = payload.get("mode")
    if mode == "collect":
        return {
            "active_runner_receipt_validated": False,
            "evaluator_runner_sha256": None,
        }
    if mode != "active":
        raise ReleaseError(f"{where} routing authority mode is invalid")
    receipts = payload.get("receipts")
    if not isinstance(receipts, dict):
        raise ReleaseError(f"{where} active routing authority has no receipts")
    receipt_field, member = ACTIVE_ROUTING_RUNNER_RECEIPT
    receipt = receipts.get(receipt_field)
    actual = hashlib.sha256(runner).hexdigest()
    if not isinstance(receipt, str) or re.fullmatch(r"[0-9a-f]{64}", receipt) is None:
        raise ReleaseError(
            f"{where} active routing receipt {receipt_field!r} is invalid"
        )
    if receipt != actual:
        raise ReleaseError(
            f"{where} active routing receipt {receipt_field!r} does not match {member}"
        )
    return {
        "active_runner_receipt_validated": True,
        "evaluator_runner_sha256": actual,
    }


def _validate_routing_canary_bytes(
    canaries: dict[str, bytes],
    legacy_dataset: bytes,
    *,
    where: str,
) -> dict[str, object]:
    expected_members = sorted(ROUTING_CANARY_MEMBERS)
    if sorted(canaries) != expected_members:
        raise ReleaseError(
            f"{where} routing canary bytes must be provided for exactly "
            f"{expected_members}"
        )

    actual_hashes = {
        member: hashlib.sha256(canaries[member]).hexdigest()
        for member in expected_members
    }
    if actual_hashes != ROUTING_CANARY_MEMBERS:
        raise ReleaseError(
            f"{where} routing canary hashes do not match the approved bytes"
        )

    legacy_hash = hashlib.sha256(legacy_dataset).hexdigest()
    if legacy_hash != ROUTING_CANARY_LEGACY_DATASET_SHA256:
        raise ReleaseError(
            f"{where} legacy routing dataset does not match its approved bytes"
        )
    try:
        legacy_payload = json.loads(legacy_dataset)
        pack_payloads = {
            member: json.loads(canaries[member]) for member in expected_members
        }
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReleaseError(f"{where} routing quality inputs are not valid JSON") from exc
    if not isinstance(legacy_payload, dict) or (
        legacy_payload.get("dataset_id") != ROUTING_CANARY_LEGACY_DATASET_ID
    ):
        raise ReleaseError(f"{where} legacy routing dataset identity is invalid")

    packs: list[dict[str, str]] = []
    for member, payload in pack_payloads.items():
        if not isinstance(payload, dict) or not isinstance(payload.get("namespace"), str):
            raise ReleaseError(f"{where} routing canary {member} has no namespace")
        packs.append(
            {
                "namespace": payload["namespace"],
                "raw_sha256": actual_hashes[member],
            }
        )
    packs.sort(key=lambda item: item["namespace"])
    suite_sha256 = _stable_hash(
        {
            "contract": "routing-quality-suite/v1",
            "legacy_dataset_id": ROUTING_CANARY_LEGACY_DATASET_ID,
            "legacy_dataset_sha256": legacy_hash,
            "packs": packs,
        }
    )
    if suite_sha256 != ROUTING_CANARY_SUITE_SHA256:
        raise ReleaseError(
            f"{where} routing canaries do not reconstruct the approved suite"
        )
    return {
        "members": expected_members,
        "sha256": actual_hashes,
        "suite_sha256": suite_sha256,
    }


def _unique_archive_member(names: Sequence[str], member: str, *, where: str) -> str:
    matches = [name for name in names if _member_matches(name, member)]
    if len(matches) != 1:
        raise ReleaseError(
            f"{where} must contain exactly one {member}; found {matches}"
        )
    return matches[0]


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
    _validate_routing_canary_inventory(names, where=archive)


def _metadata_version(payload: bytes) -> str:
    for line in payload.decode("utf-8").splitlines():
        if line.startswith("Version: "):
            version = line.removeprefix("Version: ").strip()
            if version:
                return version
    raise ReleaseError("distribution metadata has no version")


def _validate_console_entry_points(payload: bytes, *, where: str) -> str:
    try:
        entry_points = payload.decode("utf-8").strip()
    except UnicodeDecodeError as exc:
        raise ReleaseError(f"{where} entry_points.txt must be UTF-8") from exc
    if entry_points != BUOY_CONSOLE_ENTRY_POINTS:
        raise ReleaseError(
            f"{where} must expose only buoy = {BUOY_CONSOLE_TARGET}"
        )
    return BUOY_CONSOLE_TARGET


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
        wheel_authority = _validate_routing_authority_bytes(
            archive.read(
                _unique_archive_member(
                    wheel_names,
                    ROUTING_CONFIDENCE_ARTIFACT_MEMBER,
                    where="wheel",
                )
            ),
            {
                member: archive.read(
                    _unique_archive_member(wheel_names, member, where="wheel")
                )
                for member in ACTIVE_ROUTING_RECEIPT_MODULES.values()
            },
            where="wheel",
        )
        wheel_canaries = _validate_routing_canary_bytes(
            {
                member: archive.read(
                    _unique_archive_member(wheel_names, member, where="wheel")
                )
                for member in ROUTING_CANARY_MEMBERS
            },
            archive.read(
                _unique_archive_member(
                    wheel_names,
                    ROUTING_CANARY_LEGACY_MEMBER,
                    where="wheel",
                )
            ),
            where="wheel",
        )
        metadata = [name for name in wheel_names if name.endswith(".dist-info/METADATA")]
        entries = [name for name in wheel_names if name.endswith(".dist-info/entry_points.txt")]
        if len(metadata) != 1:
            raise ReleaseError("wheel must contain exactly one METADATA file")
        if len(entries) != 1:
            raise ReleaseError("wheel must contain exactly one entry_points.txt")
        wheel_version = _metadata_version(archive.read(metadata[0]))
        _validate_console_entry_points(archive.read(entries[0]), where="wheel")

    with tarfile.open(sdist, "r:gz") as archive:
        sdist_names = archive.getnames()
        _validate_archive_members(sdist_names, archive="sdist")
        sdist_payloads: dict[str, bytes] = {}
        required_payloads = (
            *ROUTING_CANARY_MEMBERS,
            ROUTING_CANARY_LEGACY_MEMBER,
            ROUTING_CONFIDENCE_ARTIFACT_MEMBER,
            *ACTIVE_ROUTING_RECEIPT_MODULES.values(),
            ACTIVE_ROUTING_RUNNER_RECEIPT[1],
        )
        for member in required_payloads:
            archive_name = _unique_archive_member(
                sdist_names,
                member,
                where="sdist",
            )
            extracted_member = archive.extractfile(archive_name)
            if extracted_member is None:
                raise ReleaseError(f"sdist member {archive_name} could not be read")
            sdist_payloads[member] = extracted_member.read()
        sdist_authority = _validate_routing_authority_bytes(
            sdist_payloads[ROUTING_CONFIDENCE_ARTIFACT_MEMBER],
            {
                member: sdist_payloads[member]
                for member in ACTIVE_ROUTING_RECEIPT_MODULES.values()
            },
            where="sdist",
        )
        sdist_runner_receipt = _validate_routing_runner_receipt(
            sdist_payloads[ROUTING_CONFIDENCE_ARTIFACT_MEMBER],
            sdist_payloads[ACTIVE_ROUTING_RUNNER_RECEIPT[1]],
            where="sdist",
        )
        sdist_canaries = _validate_routing_canary_bytes(
            {
                member: sdist_payloads[member]
                for member in ROUTING_CANARY_MEMBERS
            },
            sdist_payloads[ROUTING_CANARY_LEGACY_MEMBER],
            where="sdist",
        )
        missing_sdist_members = [
            member
            for member in REQUIRED_SDIST_MEMBERS
            if not any(_member_matches(name, member) for name in sdist_names)
        ]
        if missing_sdist_members:
            raise ReleaseError(
                f"sdist is missing governed validation members: {missing_sdist_members}"
            )
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
    if wheel_canaries != sdist_canaries:
        raise ReleaseError("wheel and sdist routing canary receipts do not match")
    if wheel_authority != sdist_authority:
        raise ReleaseError("wheel and sdist routing authority receipts do not match")
    return {
        "version": wheel_version,
        "routing_canaries": wheel_canaries,
        "routing_authority": {
            **wheel_authority,
            **sdist_runner_receipt,
        },
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
    if project.get("scripts") != BUOY_CONSOLE_SCRIPTS:
        raise ReleaseError(
            "project.scripts must expose exactly "
            f"buoy = {BUOY_CONSOLE_TARGET}"
        )

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

    canary_directory = root / "src/buoy_search/data/routing_canaries"
    try:
        canary_entries = sorted(canary_directory.iterdir())
    except OSError as exc:
        raise ReleaseError("source routing canary directory is unavailable") from exc
    source_names = [
        f"buoy_search/data/routing_canaries/{path.name}" for path in canary_entries
    ]
    _validate_routing_canary_inventory(source_names, where="source")
    if any(not path.is_file() or path.is_symlink() for path in canary_entries):
        raise ReleaseError("source routing canaries must be regular files")
    source_canaries = _validate_routing_canary_bytes(
        {
            f"buoy_search/data/routing_canaries/{path.name}": path.read_bytes()
            for path in canary_entries
        },
        (root / f"src/{ROUTING_CANARY_LEGACY_MEMBER}").read_bytes(),
        where="source",
    )
    source_authority = _validate_routing_authority_bytes(
        (root / f"src/{ROUTING_CONFIDENCE_ARTIFACT_MEMBER}").read_bytes(),
        {
            member: (root / f"src/{member}").read_bytes()
            for member in ACTIVE_ROUTING_RECEIPT_MODULES.values()
        },
        where="source",
    )
    source_runner_receipt = _validate_routing_runner_receipt(
        (root / f"src/{ROUTING_CONFIDENCE_ARTIFACT_MEMBER}").read_bytes(),
        (root / ACTIVE_ROUTING_RUNNER_RECEIPT[1]).read_bytes(),
        where="source",
    )

    lock = _load_toml(root / "uv.lock")
    roots = [package for package in lock.get("package", []) if package.get("name") == "buoy-search"]
    if len(roots) != 1:
        raise ReleaseError("uv.lock must contain exactly one buoy-search root package")
    locked_root = roots[0]
    if "version" in locked_root or locked_root.get("source") != {"editable": "."}:
        raise ReleaseError("uv.lock root package must be editable and versionless")

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    headings = [line for line in changelog.splitlines() if line.startswith("## ")]
    if len(headings) < 4 or headings[0] != "## Unreleased":
        raise ReleaseError("CHANGELOG must begin with an Unreleased section")
    if headings[1] != "## [0.5.1] - 2026-08-13":
        raise ReleaseError(
            "CHANGELOG must retain published v0.5.1 history dated 2026-08-13"
        )
    if headings[2:4] != [
        "## [0.5.0] - 2026-08-01",
        "## [0.4.0] - 2026-07-21",
    ]:
        raise ReleaseError("published changelog history must remain frozen through v0.5.0")
    if any(" - pending" in heading for heading in headings):
        raise ReleaseError("CHANGELOG must not contain a pending release heading")

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
        "console_script": BUOY_CONSOLE_TARGET,
        "dynamic_version": True,
        "generated_version_file": "src/buoy_search/_version.py",
        "published_history_through": "0.5.1",
        "staged_release": None,
        "publication_paused": True,
        "routing_canaries": source_canaries,
        "routing_authority": {
            **source_authority,
            **source_runner_receipt,
        },
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
