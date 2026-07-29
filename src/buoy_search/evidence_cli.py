"""CLI wiring for explicit remote evidence estimate, snapshot, and verify."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from buoy_search.applied_state import AppliedStateError, resolve_state_root
from buoy_search.config import (
    DEFAULT_EMBEDDING_PRECISION,
    DEFAULT_REGION,
    EMBEDDING_PRECISIONS,
    load_config,
)
from buoy_search.evidence_snapshot import (
    DEFAULT_EVIDENCE_OUT_ROOT,
    DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES,
    DEFAULT_MAXIMUM_ROWS,
    EvidenceSnapshotError,
)
from buoy_search.remote_catalog import create_client

EVIDENCE_CLIENT_FACTORY = create_client


def configure_evidence_parser(subparsers: object) -> None:
    evidence = subparsers.add_parser(  # type: ignore[attr-defined]
        "evidence",
        help="estimate, create, or verify remote-first immutable evidence snapshots",
        description=(
            "Evidence snapshots retain full content and vectors in turbopuffer branches. "
            "Only a compact remote membership ledger and bounded local snapshot.json are created."
        ),
    )
    commands = evidence.add_subparsers(dest="evidence_command")
    estimate = commands.add_parser(
        "estimate",
        help="estimate branch logical storage without remote writes or local artifacts",
    )
    _add_selection_arguments(estimate)
    estimate.set_defaults(func=_run_estimate)

    snapshot = commands.add_parser(
        "snapshot",
        help="create or reuse branch-backed evidence and a compact remote ledger",
    )
    _add_selection_arguments(snapshot)
    snapshot.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_EVIDENCE_OUT_ROOT,
        help="Bounded manifest root (default: artifacts/evidence-snapshots).",
    )
    snapshot.set_defaults(func=_run_snapshot)

    verify = commands.add_parser(
        "verify",
        help="remotely verify a completed evidence snapshot without local applied state",
    )
    verify.add_argument("--snapshot-id", required=True)
    verify.add_argument("--region", default=None)
    verify.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Optional local snapshot.json to compare with the remote snapshot.",
    )
    verify.add_argument(
        "--out-root",
        type=Path,
        default=DEFAULT_EVIDENCE_OUT_ROOT,
        help="Look for a default local manifest under this root when present.",
    )
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=_run_verify)


def _add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--namespace",
        action="append",
        required=True,
        help="Explicit applied source namespace; repeat for multiple namespaces (maximum 64).",
    )
    parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Applied-state root (default .buoy with legacy in-place fallback).",
    )
    parser.add_argument("--region", default=None)
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument(
        "--embedding-precision",
        choices=EMBEDDING_PRECISIONS,
        default=None,
    )
    parser.add_argument(
        "--maximum-rows",
        type=_positive_int,
        default=DEFAULT_MAXIMUM_ROWS,
        help=f"Fail-closed exact ledger row limit (default {DEFAULT_MAXIMUM_ROWS}).",
    )
    parser.add_argument(
        "--maximum-remote-logical-bytes",
        type=_positive_int,
        default=DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES,
        help=(
            "Fail-closed approximate branch logical-byte limit "
            f"(default {DEFAULT_MAXIMUM_REMOTE_LOGICAL_BYTES})."
        ),
    )
    parser.add_argument("--json", action="store_true")


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _runtime(args: argparse.Namespace) -> tuple[str, str, str]:
    config = load_config(ignore_environment_namespace=True)
    return (
        args.region or config.region or DEFAULT_REGION,
        args.embedding_model or config.embedding_model,
        args.embedding_precision or config.embedding_precision or DEFAULT_EMBEDDING_PRECISION,
    )


def _state_root(args: argparse.Namespace) -> Path:
    root, warning = resolve_state_root(args.state_root)
    if warning:
        print(warning, file=sys.stderr)
    return root


def _client(*, region: str):  # noqa: ANN202 - injected protocol result.
    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        raise EvidenceSnapshotError(
            "TURBOPUFFER_API_KEY must be set for remote evidence operations"
        )
    return EVIDENCE_CLIENT_FACTORY(api_key=api_key, region=region)


def _run_estimate(args: argparse.Namespace) -> int:
    try:
        from buoy_search.evidence_remote import estimate_evidence_snapshot

        region, model, precision = _runtime(args)
        result = estimate_evidence_snapshot(
            _client(region=region),
            namespaces=args.namespace,
            state_root=_state_root(args),
            region=region,
            embedding_model=model,
            embedding_precision=precision,
            maximum_rows=args.maximum_rows,
            maximum_remote_logical_bytes=args.maximum_remote_logical_bytes,
        )
    except (EvidenceSnapshotError, AppliedStateError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print(result, json_output=args.json)
    return 0 if bool(result.get("would_pass_limits")) else 2


def _run_snapshot(args: argparse.Namespace) -> int:
    try:
        from buoy_search.evidence_remote import create_evidence_snapshot

        region, model, precision = _runtime(args)
        result = create_evidence_snapshot(
            _client(region=region),
            namespaces=args.namespace,
            state_root=_state_root(args),
            region=region,
            embedding_model=model,
            embedding_precision=precision,
            out_root=args.out_root,
            maximum_rows=args.maximum_rows,
            maximum_remote_logical_bytes=args.maximum_remote_logical_bytes,
        )
    except (EvidenceSnapshotError, AppliedStateError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print(result, json_output=args.json)
    return 0


def _run_verify(args: argparse.Namespace) -> int:
    try:
        from buoy_search.evidence_remote import verify_evidence_snapshot

        region = args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)
        manifest = args.manifest
        if manifest is None:
            candidate = args.out_root / args.snapshot_id / "snapshot.json"
            manifest = candidate if candidate.exists() else None
        result = verify_evidence_snapshot(
            _client(region=region),
            snapshot_id=args.snapshot_id,
            manifest_path=manifest,
        )
    except (EvidenceSnapshotError, AppliedStateError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    _print(result, json_output=args.json)
    return 0


def _print(payload: dict[str, object], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    command = str(payload.get("command", "evidence"))
    print(f"{command}:")
    for key in sorted(payload):
        if key == "command":
            continue
        value = payload[key]
        if isinstance(value, (dict, list)):
            print(f"  {key}: {json.dumps(value, sort_keys=True)}")
        else:
            print(f"  {key}: {value}")
