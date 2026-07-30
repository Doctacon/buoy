"""Lazy CLI wiring for autonomous local-model semantic builds."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import sys

from buoy_search.config import DEFAULT_REGION
from buoy_search.semantics_local_model import DEFAULT_MODEL_ENDPOINT, DEFAULT_MODEL_TIMEOUT_SECONDS
from buoy_search.semantics_models import LocalModelError, ModelContract, STRUCTURED_OUTPUT_MODES
from buoy_search.semantics_remote import BuildLimits, DEFAULT_OUT_ROOT, SemanticBuildError


def configure_semantics_parser(subparsers: object) -> None:
    semantics = subparsers.add_parser(  # type: ignore[attr-defined]
        "semantics",
        help="build and inspect local-model-only concepts, mentions, and taxonomy",
        description=("Semantic inference uses only an explicitly configured loopback local model. "
                     "Hosted inference endpoints and fallbacks are not supported."),
    )
    commands = semantics.add_subparsers(dest="semantics_command")
    doctor = commands.add_parser("doctor", help="test the synthetic local model contract without evidence or turbopuffer")
    _add_model_arguments(doctor)
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(func=_run_doctor)

    estimate = commands.add_parser("estimate", help="estimate one semantic build without remote writes or local artifacts")
    estimate.add_argument("--snapshot-id", required=True)
    estimate.add_argument("--region", default=None)
    _add_model_arguments(estimate)
    _add_limit_arguments(estimate)
    estimate.add_argument("--estimate-sample-rows", type=_bounded_estimate_sample, default=20)
    estimate.add_argument("--sample-seed", type=int, default=0)
    estimate.add_argument("--json", action="store_true")
    estimate.set_defaults(func=_run_estimate)

    build = commands.add_parser("build", help="create or resume one immutable autonomous semantic build")
    build.add_argument("--snapshot-id", required=True)
    build.add_argument("--region", default=None)
    build.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    _add_model_arguments(build)
    _add_limit_arguments(build)
    build.add_argument("--accepted-threshold", type=_unit_float, default=0.85)
    build.add_argument("--provisional-threshold", type=_unit_float, default=0.65)
    build.add_argument("--sample-size", type=_positive_int, default=None)
    build.add_argument("--sample-seed", type=int, default=0)
    build.add_argument("--resume", action="store_true")
    build.add_argument("--json", action="store_true")
    build.set_defaults(func=_run_build)

    verify = commands.add_parser("verify", help="remotely verify a completed semantic build without a local model")
    verify.add_argument("--build-id", required=True)
    verify.add_argument("--region", default=None)
    verify.add_argument("--manifest", type=Path, default=None)
    verify.add_argument("--out-root", type=Path, default=DEFAULT_OUT_ROOT)
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=_run_verify)

    inspect = commands.add_parser("inspect", help="read a bounded remote semantic quality view without a local model")
    inspect.add_argument("--build-id", required=True)
    inspect.add_argument("--region", default=None)
    inspect.add_argument("--kind", choices=("concepts", "mentions", "taxonomy", "summary"), required=True)
    inspect.add_argument("--status", choices=("accepted", "provisional"), default=None)
    inspect.add_argument("--limit", type=_inspect_limit, default=25)
    inspect.add_argument("--json", action="store_true")
    inspect.set_defaults(func=_run_inspect)


def _add_model_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--model-endpoint", default=os.environ.get("BUOY_SEMANTICS_MODEL_ENDPOINT", DEFAULT_MODEL_ENDPOINT))
    parser.add_argument("--model-id", default=os.environ.get("BUOY_SEMANTICS_MODEL_ID"), required="BUOY_SEMANTICS_MODEL_ID" not in os.environ)
    parser.add_argument("--model-revision", default=os.environ.get("BUOY_SEMANTICS_MODEL_REVISION"))
    parser.add_argument("--model-context-window", type=_positive_int, default=_environment_int("BUOY_SEMANTICS_MODEL_CONTEXT_WINDOW"), required="BUOY_SEMANTICS_MODEL_CONTEXT_WINDOW" not in os.environ)
    parser.add_argument("--model-timeout-seconds", type=_positive_float, default=_environment_float("BUOY_SEMANTICS_MODEL_TIMEOUT_SECONDS", DEFAULT_MODEL_TIMEOUT_SECONDS))
    parser.add_argument("--model-seed", type=int, default=_environment_int("BUOY_SEMANTICS_MODEL_SEED", 0))
    parser.add_argument("--structured-output-mode", choices=STRUCTURED_OUTPUT_MODES, default=os.environ.get("BUOY_SEMANTICS_STRUCTURED_OUTPUT_MODE", "openai_json_schema"))


def _add_limit_arguments(parser: argparse.ArgumentParser) -> None:
    defaults = BuildLimits()
    parser.add_argument("--maximum-evidence-rows", type=_positive_int, default=defaults.maximum_rows)
    parser.add_argument("--maximum-evidence-utf8-bytes", type=_positive_int, default=defaults.maximum_evidence_bytes)
    parser.add_argument("--maximum-model-calls", type=_positive_int, default=defaults.maximum_model_calls)
    parser.add_argument("--maximum-wall-seconds", type=_positive_int, default=defaults.maximum_wall_seconds)
    parser.add_argument("--maximum-candidates", type=_positive_int, default=defaults.maximum_candidates)
    parser.add_argument("--maximum-concepts", type=_positive_int, default=defaults.maximum_concepts)
    parser.add_argument("--maximum-taxonomy-relations", type=_positive_int, default=defaults.maximum_taxonomy_rows)
    parser.add_argument("--maximum-derived-utf8-bytes", type=_positive_int, default=defaults.maximum_derived_bytes)
    parser.add_argument("--model-concurrency", type=_positive_int, choices=(1,), default=1)


def _limits(args: argparse.Namespace) -> BuildLimits:
    return BuildLimits(
        maximum_rows=args.maximum_evidence_rows,
        maximum_evidence_bytes=args.maximum_evidence_utf8_bytes,
        maximum_model_calls=args.maximum_model_calls,
        maximum_wall_seconds=args.maximum_wall_seconds,
        maximum_candidates=args.maximum_candidates,
        maximum_concepts=args.maximum_concepts,
        maximum_taxonomy_rows=args.maximum_taxonomy_relations,
        maximum_derived_bytes=args.maximum_derived_utf8_bytes,
        model_concurrency=args.model_concurrency,
    )


def _environment_int(name: str, default: int | None = None) -> int | None:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _environment_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _positive_int(value: str) -> int:
    try: parsed = int(value)
    except ValueError as exc: raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed < 1: raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def _positive_float(value: str) -> float:
    try: parsed = float(value)
    except ValueError as exc: raise argparse.ArgumentTypeError("must be a finite number greater than zero") from exc
    if not math.isfinite(parsed) or parsed <= 0: raise argparse.ArgumentTypeError("must be a finite number greater than zero")
    return parsed


def _unit_float(value: str) -> float:
    try: parsed = float(value)
    except ValueError as exc: raise argparse.ArgumentTypeError("must be between zero and one") from exc
    if not math.isfinite(parsed) or not 0 <= parsed <= 1: raise argparse.ArgumentTypeError("must be between zero and one")
    return parsed


def _inspect_limit(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 100: raise argparse.ArgumentTypeError("must be no greater than 100")
    return parsed


def _bounded_estimate_sample(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 20: raise argparse.ArgumentTypeError("must be no greater than 20")
    return parsed


def _model(args: argparse.Namespace):  # noqa: ANN202
    from buoy_search.semantics_local_model import OpenAICompatibleLocalClient
    return OpenAICompatibleLocalClient(
        endpoint=args.model_endpoint, model_id=args.model_id,
        model_revision=args.model_revision, model_context_window=args.model_context_window,
        timeout_seconds=args.model_timeout_seconds, seed=args.model_seed,
        structured_output_mode=args.structured_output_mode,
    )


def _remote_client(region: str):  # noqa: ANN202
    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        raise SemanticBuildError("TURBOPUFFER_API_KEY must be set for semantic remote operations")
    from buoy_search.remote_catalog import create_client
    return create_client(api_key=api_key, region=region)


def _model_contract(client) -> ModelContract:  # noqa: ANN001
    payload = client.doctor()
    value = payload.get("model_contract")
    if not isinstance(value, dict):
        raise SemanticBuildError("local model doctor returned an invalid contract")
    try: return ModelContract(**value)
    except TypeError as exc: raise SemanticBuildError("local model doctor returned an invalid contract") from exc


def _run_doctor(args: argparse.Namespace) -> int:
    try: result = _model(args).doctor()
    except (LocalModelError, OSError, ValueError) as exc: return _error(exc)
    _print(result, args.json); return 0


def _run_estimate(args: argparse.Namespace) -> int:
    try:
        from buoy_search.semantics_remote import estimate_semantic_build
        model = _model(args)
        contract = _model_contract(model)
        result = estimate_semantic_build(
            _remote_client(args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)),
            evidence_snapshot_id=args.snapshot_id, model_client=model, limits=_limits(args),
            sample_rows=args.estimate_sample_rows, sample_seed=args.sample_seed,
            prior_model_calls=1,
        )
        result["model_contract"] = contract.to_dict()
        result["model_contract_hash"] = contract.contract_hash
        result["contract_probe_model_calls"] = 1
    except (LocalModelError, SemanticBuildError, OSError, ValueError) as exc: return _error(exc)
    _print(result, args.json); return 0 if result["would_pass_limits"] else 2


def _run_build(args: argparse.Namespace) -> int:
    try:
        if not (args.provisional_threshold < args.accepted_threshold):
            raise SemanticBuildError("thresholds must satisfy 0 <= provisional < accepted <= 1")
        from buoy_search.semantics_remote import create_semantic_build
        model = _model(args)
        result = create_semantic_build(
            _remote_client(args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)),
            evidence_snapshot_id=args.snapshot_id, model_client=model,
            model_contract=_model_contract(model), out_root=args.out_root,
            sample_size=args.sample_size, sample_seed=args.sample_seed,
            accepted_threshold=args.accepted_threshold,
            provisional_threshold=args.provisional_threshold, limits=_limits(args), resume=args.resume,
            initial_model_calls=1,
        )
        result["contract_probe_model_calls"] = 1 + int(not result.get("reused_build", False))
        result.setdefault("local_model_calls_occurred", True)
        result.setdefault("turbopuffer_api_calls_occurred", True)
        result.setdefault("turbopuffer_internal_writes_occurred", not bool(result.get("reused_build")))
        result.setdefault("source_namespace_writes_occurred", False)
        result.setdefault("evidence_branch_writes_occurred", False)
        result.setdefault("hosted_model_calls_occurred", False)
        result.setdefault("hosted_model_cost", 0)
        result.setdefault("local_full_corpus_written", False)
        result.setdefault("local_manifest_written", True)
    except (LocalModelError, SemanticBuildError, OSError, ValueError) as exc:
        if args.json and isinstance(exc, SemanticBuildError):
            print(json.dumps({
                "error": str(exc).split("; incomplete_internal_namespaces=", 1)[0],
                "incomplete_internal_namespaces": list(exc.incomplete_namespaces),
            }, sort_keys=True), file=sys.stderr)
            return 2
        return _error(exc)
    _print(result, args.json); return 0


def _run_verify(args: argparse.Namespace) -> int:
    try:
        from buoy_search.semantics_remote import verify_semantic_build
        manifest = args.manifest
        if manifest is None:
            candidate = args.out_root / args.build_id / "build.json"
            manifest = candidate if candidate.exists() else None
        result = verify_semantic_build(
            _remote_client(args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)),
            build_id=args.build_id, manifest_path=manifest,
        )
    except (SemanticBuildError, OSError, ValueError) as exc: return _error(exc)
    _print(result, args.json); return 0


def _run_inspect(args: argparse.Namespace) -> int:
    try:
        from buoy_search.semantics_remote import inspect_semantic_build
        result = inspect_semantic_build(
            _remote_client(args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)),
            build_id=args.build_id, kind=args.kind, status=args.status, limit=args.limit,
        )
    except (SemanticBuildError, OSError, ValueError) as exc: return _error(exc)
    _print(result, args.json); return 0


def _error(exc: BaseException) -> int:
    print(str(exc), file=sys.stderr); return 2


def _print(payload: dict[str, object], json_output: bool) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True)); return
    print(f"{payload.get('command', 'semantics')}:")
    for key in sorted(payload):
        if key == "command": continue
        value = payload[key]
        print(f"  {key}: {json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else value}")
