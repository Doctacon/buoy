"""Authenticated remote routing-catalog CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import re
import sys

from buoy_search.applied_state import (
    AppliedStateError,
    acquire_namespace_apply_lock,
    resolve_state_root,
)
from buoy_search.catalog import (
    CardFields,
    CatalogError,
    MAX_ROUTING_EXAMPLES,
    NamespaceCard,
    ROUTING_PASSAGE_FIELDS,
    ROUTING_PROTOTYPE_FIELD_ORDER,
    canonical_text,
    card_revision,
    card_to_dict,
    bounded_routing_passages,
    normalize_routing_examples,
    prepare_card,
    utc_now,
)
from buoy_search.config import DEFAULT_REGION, RuntimeConfig, RuntimeConfigError, load_config
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_CATALOG_SCHEMA_V2_ADDITIONS,
    REMOTE_CATALOG_SCHEMA_V3_ADDITIONS,
    REMOTE_SCHEMA_V1,
    REMOTE_SCHEMA_V2,
    REMOTE_SCHEMA_V3,
    CompatibilityContract,
    MutationMetrics,
    MutationResult,
    ReadMetrics,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    create_client,
    create_remote_cards,
    migrate_remote_catalog_schema_v2,
    migrate_remote_catalog_schema_v3,
    read_remote_catalog,
    remote_card_id,
    remote_catalog_projection_sha256,
    remote_catalog_resource,
    remote_catalog_schema_fingerprint,
    update_remote_card,
)


REMOTE_CATALOG_CLIENT_FACTORY = create_client
_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class _CatalogOperatorError(RemoteCatalogError):
    """Safe, bounded diagnostics authored by the catalog operator itself."""


def configure_catalog_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    catalog = subparsers.add_parser(
        "catalog",
        help="manage the remote namespace routing catalog",
        description=(
            f"Manage validated routing cards in remote namespace {REMOTE_CATALOG_NAMESPACE}. "
            "Commands require TURBOPUFFER_API_KEY. Mutations preview unless --approve is supplied."
        ),
    )
    commands = catalog.add_subparsers(dest="catalog_command")

    parser = commands.add_parser("list", help="list remote live routing cards")
    parser.add_argument("search", nargs="?", default=None)
    parser.add_argument("--all", action="store_true", help="Include disabled and stale cards.")
    _add_common(parser)
    parser.set_defaults(func=_run_list)

    parser = commands.add_parser("show", help="show one remote routing card")
    parser.add_argument("namespace")
    parser.add_argument("--include-vector", action="store_true", help="Include vector in JSON output only.")
    _add_common(parser)
    parser.set_defaults(func=_run_show)

    parser = commands.add_parser("upsert", help="create or update one complete remote manual card")
    parser.add_argument("namespace")
    parser.add_argument(
        "--source-kind",
        required=True,
        choices=["github_repo", "website", "document", "database"],
    )
    parser.add_argument("--source-uri", required=True)
    parser.add_argument("--site-id", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--alias", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument(
        "--routing-example",
        action="append",
        default=[],
        help="Add a descriptor-free example question (repeatable, maximum eight).",
    )
    parser.add_argument("--embedding-model", required=True)
    parser.add_argument("--embedding-precision", required=True, choices=["float32", "float16"])
    parser.add_argument("--plan-schema-version", required=True, type=int)
    parser.add_argument("--ranking-mode", required=True, choices=["file", "page", "chunk"])
    parser.add_argument("--ranking-profile", required=True, choices=["repo-code", "none"])
    parser.add_argument("--ranking-pool", required=True, type=_positive_int)
    parser.add_argument("--ranking-aggregation", required=True, choices=["max", "adaptive-sum-3", "capped-sum-3"])
    parser.add_argument("--disabled", action="store_true")
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_upsert)

    parser = commands.add_parser(
        "repair-apply",
        help="repair one failed post-apply card from its retained verified plan",
    )
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--namespace", required=True)
    parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Local applied-state root. Defaults to the absolute user-global ~/.buoy directory.",
    )
    parser.add_argument("--apply-id", required=True)
    repair_precondition = parser.add_mutually_exclusive_group(required=True)
    repair_precondition.add_argument("--expected-card-revision", default=None)
    repair_precondition.add_argument("--expect-absent", action="store_true")
    repair_precondition.add_argument(
        "--inspect-current",
        action="store_true",
        help=(
            "strong-read exact-v3 state and emit a revision/absence-bound "
            "follow-up without writing"
        ),
    )
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_repair_apply)

    parser = commands.add_parser(
        "migrate-routing-v2",
        help="preview or approve the reader-first routing schema migration",
    )
    parser.add_argument("--expected-snapshot-revision", default=None)
    parser.add_argument("--expected-projection-sha256", default=None)
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_migrate_routing_v2)

    parser = commands.add_parser(
        "migrate-routing-v3",
        help="preview or approve the reader-first routing-passage schema migration",
    )
    parser.add_argument("--expected-snapshot-revision", default=None)
    parser.add_argument("--expected-projection-sha256", default=None)
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_migrate_routing_v3)

    parser = commands.add_parser(
        "set-routing-examples",
        help="preview or conditionally replace one card's reviewed routing examples",
    )
    parser.add_argument("namespace")
    parser.add_argument(
        "--routing-example",
        action="append",
        required=True,
        help="Set a reviewed example question (repeatable, one through eight).",
    )
    parser.add_argument("--expected-card-revision", default=None)
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_set_routing_examples)

    for operation in ("enable", "disable"):
        parser = commands.add_parser(operation, help=f"{operation} one remote card")
        parser.add_argument("namespace")
        parser.add_argument("--approve", action="store_true")
        _add_common(parser)
        parser.set_defaults(func=_run_toggle, requested_enabled=operation == "enable")


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--region", default=None, help="Override TURBOPUFFER_REGION.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _approval_sha256(value: object, *, option: str) -> str:
    if not isinstance(value, str) or _SHA256_PATTERN.fullmatch(value) is None:
        raise _CatalogOperatorError(
            f"{option} must be supplied as exactly 64 lowercase hexadecimal characters with --approve"
        )
    return value


def _operator_namespace(value: object) -> str:
    if (
        not isinstance(value, str)
        or re.fullmatch(r"[A-Za-z0-9-_.]{1,128}", value) is None
    ):
        raise _CatalogOperatorError(
            "target namespace must match [A-Za-z0-9-_.]{1,128}"
        )
    if value == REMOTE_CATALOG_NAMESPACE or value.startswith("buoy-evidence-"):
        raise _CatalogOperatorError("target namespace is reserved")
    return value


def _normalized_reviewed_examples(values: object) -> list[str]:
    try:
        raw = list(values) if isinstance(values, list) else []
        examples = normalize_routing_examples(raw)
        if not examples or len(examples) > MAX_ROUTING_EXAMPLES:
            raise CatalogError("invalid routing example count")
        return examples
    except CatalogError:
        raise _CatalogOperatorError(
            "routing examples must contain one through eight unique non-empty "
            "questions of at most 512 characters"
        ) from None


def _resolved_region(args: argparse.Namespace) -> str:
    return args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)


def _credentials() -> str:
    value = os.environ.get("TURBOPUFFER_API_KEY")
    if not value:
        raise RemoteCatalogError("TURBOPUFFER_API_KEY must be set for remote catalog access")
    return value


def _compatibility(region: str) -> CompatibilityContract:
    config = load_config()
    return CompatibilityContract(
        region=region,
        embedding_model=config.embedding_model,
        embedding_precision=config.embedding_precision,
    )


def _read(args: argparse.Namespace) -> tuple[object, RemoteCatalogSnapshot]:
    region = _resolved_region(args)
    client = REMOTE_CATALOG_CLIENT_FACTORY(api_key=_credentials(), region=region)
    return client, read_remote_catalog(client, region=region, compatibility=_compatibility(region))


def _request_summary(
    reads: tuple[ReadMetrics, ...],
    mutations: tuple[MutationResult, ...] = (),
) -> dict[str, object]:
    namespace_pages = sum(item.namespace_list_pages for item in reads)
    metadata_requests = sum(item.metadata_requests for item in reads)
    card_pages = sum(item.card_query_pages for item in reads)
    verification_queries = sum(item.metrics.verification_query_requests for item in mutations)
    write_requests = sum(item.metrics.write_requests for item in mutations)
    billing = [bill for item in reads for bill in item.billing]
    billing.extend(bill for item in mutations for bill in item.metrics.billing)
    return {
        "namespace_list_requests": namespace_pages,
        "metadata_requests": metadata_requests,
        "catalog_page_query_requests": card_pages,
        "mutation_verification_query_requests": verification_queries,
        "write_requests": write_requests,
        "total_requests": (
            namespace_pages + metadata_requests + card_pages
            + verification_queries + write_requests
        ),
        "billing": billing,
    }


def _base_payload(
    command: str,
    region: str,
    snapshot: RemoteCatalogSnapshot,
    *,
    reads: tuple[ReadMetrics, ...] | None = None,
    mutations: tuple[MutationResult, ...] = (),
) -> dict[str, object]:
    accounted_reads = reads or (snapshot.metrics,)
    return {
        "command": command,
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "region": region,
        "snapshot_revision": snapshot.snapshot_revision,
        "counts": asdict(snapshot.counts),
        "coverage": {
            "eligible_ids": [card.namespace for card in snapshot.eligible_cards],
            "missing_card_ids": list(snapshot.missing_card_ids),
            "stale_target_ids": list(snapshot.stale_target_ids),
            "disabled_ids": list(snapshot.disabled_ids),
            "incompatible_ids": list(snapshot.incompatible_ids),
        },
        "read_metrics": {
            "namespace_list_pages": sum(item.namespace_list_pages for item in accounted_reads),
            "metadata_requests": sum(item.metadata_requests for item in accounted_reads),
            "card_query_pages": sum(item.card_query_pages for item in accounted_reads),
            "billing": [bill for item in accounted_reads for bill in item.billing],
        },
        "request_summary": _request_summary(accounted_reads, mutations),
    }


def _operation_accounting(
    *,
    strong_read_calls: int | None,
    model_inferences: int | None = 0,
    schema_writes: int = 0,
    card_writes: int = 0,
) -> dict[str, int | None]:
    return {
        "strong_read_calls": strong_read_calls,
        "model_inferences": model_inferences,
        "schema_writes": schema_writes,
        "card_writes": card_writes,
        "content_writes": 0,
        "content_operations": 0,
        "deletes": 0,
    }


def _full_card_payload(card: NamespaceCard) -> dict[str, object]:
    return card_to_dict(
        card,
        include_vector=True,
        include_routing_examples=True,
        include_routing_passages=True,
    )


def _card_identities(snapshot: RemoteCatalogSnapshot) -> list[dict[str, str]]:
    return [
        {
            "namespace": card.namespace,
            "row_id": remote_card_id(card.namespace),
            "card_revision": card.card_revision,
        }
        for card in snapshot.cards
    ]


def _require_exact_migration_result(
    before: RemoteCatalogSnapshot,
    after: RemoteCatalogSnapshot,
    *,
    expected_schema_version: int = REMOTE_SCHEMA_V2,
) -> None:
    if after.catalog_schema_version != expected_schema_version:
        raise _CatalogOperatorError(
            "schema migration verification did not observe exact schema "
            f"v{expected_schema_version}"
        )
    if before.live_namespace_ids != after.live_namespace_ids:
        raise _CatalogOperatorError("schema migration verification observed inventory drift")
    if before.counts != after.counts:
        raise _CatalogOperatorError("schema migration verification observed catalog-count drift")
    if [_full_card_payload(card) for card in before.cards] != [
        _full_card_payload(card) for card in after.cards
    ]:
        raise _CatalogOperatorError("schema migration verification observed card projection drift")
    if before.snapshot_revision != after.snapshot_revision:
        raise _CatalogOperatorError("schema migration verification observed revision drift")
    if remote_catalog_projection_sha256(before) != remote_catalog_projection_sha256(after):
        raise _CatalogOperatorError("schema migration verification observed projection drift")


def _card_fields_with_examples(
    card: NamespaceCard,
    examples: list[str],
) -> CardFields:
    routing_passages = bounded_routing_passages(
        routing_examples=examples,
        routing_passages=card.routing_passages,
    )
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
        routing_examples=list(examples),
        routing_passages=routing_passages,
    )


def _require_bounded_example_candidate(
    current: NamespaceCard,
    intended: NamespaceCard,
    examples: list[str],
) -> None:
    current_payload = _full_card_payload(current)
    intended_payload = _full_card_payload(intended)
    allowed = {
        "updated_at",
        "card_revision",
        *ROUTING_PASSAGE_FIELDS,
        *ROUTING_PROTOTYPE_FIELD_ORDER,
    }
    if any(
        current_payload[key] != intended_payload[key]
        for key in current_payload
        if key not in allowed
    ):
        raise _CatalogOperatorError("routing-example projection changed a protected card field")
    if intended.routing_examples != examples:
        raise _CatalogOperatorError("routing-example projection did not preserve canonical questions")
    if (
        intended.semantic_hash != current.semantic_hash
        or intended.vector != current.vector
        or intended.vector_hash != current.vector_hash
    ):
        raise _CatalogOperatorError("routing-example projection changed the legacy base projection")


def _require_exact_schema_mutation(mutation: MutationResult) -> None:
    if not (
        mutation.changed is True
        and mutation.card is None
        and mutation.rows_affected == 0
        and mutation.affected_ids == ()
        and mutation.metrics.write_requests == 1
    ):
        raise _CatalogOperatorError(
            "schema migration did not report exactly one schema-only write"
        )


def _require_exact_example_mutation(
    mutation: MutationResult,
    intended: NamespaceCard,
) -> None:
    expected_id = remote_card_id(intended.namespace)
    if not (
        mutation.changed is True
        and mutation.rows_affected == 1
        and mutation.affected_ids == (expected_id,)
        and mutation.metrics.write_requests == 1
        and mutation.card is not None
        and _full_card_payload(mutation.card) == _full_card_payload(intended)
    ):
        raise _CatalogOperatorError(
            "conditional routing-example update did not affect and verify exactly the intended row"
        )


def _require_exact_example_result(
    before: RemoteCatalogSnapshot,
    after: RemoteCatalogSnapshot,
    intended: NamespaceCard,
) -> NamespaceCard:
    if after.catalog_schema_version != before.catalog_schema_version:
        raise _CatalogOperatorError(
            "routing-example verification observed catalog schema drift"
        )
    if before.live_namespace_ids != after.live_namespace_ids:
        raise _CatalogOperatorError("routing-example verification observed inventory drift")
    if before.counts != after.counts:
        raise _CatalogOperatorError("routing-example verification observed catalog-count drift")
    before_by_namespace = {card.namespace: card for card in before.cards}
    after_by_namespace = {card.namespace: card for card in after.cards}
    if set(before_by_namespace) != set(after_by_namespace):
        raise _CatalogOperatorError("routing-example verification observed card inventory drift")
    for namespace, card in before_by_namespace.items():
        if namespace == intended.namespace:
            continue
        if _full_card_payload(card) != _full_card_payload(after_by_namespace[namespace]):
            raise _CatalogOperatorError("routing-example verification observed unrelated card drift")
    verified = after_by_namespace[intended.namespace]
    if _full_card_payload(verified) != _full_card_payload(intended):
        raise _CatalogOperatorError("routing-example verification did not reproduce the intended card")
    return verified


def _emit(payload: dict[str, object], *, json_output: bool, text_lines: list[str]) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in text_lines:
            print(line)


def _remote_failure(exc: Exception) -> int:
    print(str(exc), file=sys.stderr)
    return 2


def _operator_failure(
    exc: Exception,
    *,
    args: argparse.Namespace,
    command: str,
    operation: str,
    region: str,
    snapshot: RemoteCatalogSnapshot | None,
    strong_read_calls: int | None,
    model_inferences: int | None,
) -> int:
    if isinstance(exc, _CatalogOperatorError):
        message = str(exc)
    else:
        class_name = re.sub(r"[^A-Za-z0-9_.-]", "_", type(exc).__name__)[:80]
        message = f"{operation} failed ({class_name})"
    operations = _operation_accounting(
        strong_read_calls=strong_read_calls,
        model_inferences=model_inferences,
    )
    if snapshot is not None:
        payload = {
            **_base_payload(
                command,
                region,
                snapshot,
                reads=(snapshot.metrics,),
            ),
            "request_accounting_mode": "exact",
        }
        payload["request_summary"]["accounting_complete"] = True
    else:
        request_complete = strong_read_calls == 0
        payload = {
            "command": command,
            "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
            "region": region,
            "snapshot_revision": None,
            "counts": None,
            "coverage": None,
            "read_metrics": None,
            "request_summary": (
                {
                    "namespace_list_requests": 0,
                    "metadata_requests": 0,
                    "catalog_page_query_requests": 0,
                    "mutation_verification_query_requests": 0,
                    "write_requests": 0,
                    "total_requests": 0,
                    "billing": [],
                    "accounting_complete": True,
                }
                if request_complete
                else {
                    "namespace_list_requests": None,
                    "metadata_requests": None,
                    "catalog_page_query_requests": None,
                    "mutation_verification_query_requests": 0,
                    "write_requests": 0,
                    "total_requests": None,
                    "billing": [],
                    "accounting_complete": False,
                }
            ),
            "request_accounting_mode": (
                "exact" if request_complete else "unknown_partial_read"
            ),
        }
    payload.update(
        {
            "approved": bool(args.approve),
            "mutation_status": "precondition_failed",
            "write_attempted": False,
            "verification_complete": False,
            "failure": message,
            "operations_performed": operations,
            "operation_accounting_complete": (
                strong_read_calls is not None and model_inferences is not None
            ),
        }
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        strong_text = (
            str(strong_read_calls)
            if strong_read_calls is not None
            else "unknown"
        )
        model_text = (
            str(model_inferences) if model_inferences is not None else "unknown"
        )
        print(message, file=sys.stderr)
        print("No mutation was attempted.", file=sys.stderr)
        print(
            "operations: strong_reads="
            f"{strong_text}; model_inferences={model_text}; "
            "schema_writes=0; card_writes=0; content=0; deletes=0",
            file=sys.stderr,
        )
    return 2


def _attempted_mutation_failure(
    *,
    args: argparse.Namespace,
    command: str,
    operation: str,
    region: str,
    snapshot: RemoteCatalogSnapshot,
    reads: tuple[ReadMetrics, ...],
    mutation: MutationResult | None,
    write_kind: str,
    strong_read_calls: int,
    model_inferences: int,
    failure: str,
    details: dict[str, object] | None = None,
) -> int:
    accounted_mutation = mutation or MutationResult(
        changed=False,
        card=None,
        rows_affected=0,
        affected_ids=(),
        metrics=MutationMetrics(write_requests=1),
    )
    schema_writes = 1 if write_kind == "schema" else 0
    card_writes = 1 if write_kind == "card" else 0
    payload = {
        **_base_payload(
            command,
            region,
            snapshot,
            reads=reads,
            mutations=(accounted_mutation,),
        ),
        "approved": True,
        "mutation_status": "verification_failed",
        "write_attempted": True,
        "write_kind": write_kind,
        "verification_complete": False,
        "retry_requires_fresh_preview": True,
        "failure": failure,
        "rows_affected": mutation.rows_affected if mutation is not None else None,
        "affected_ids": (
            list(mutation.affected_ids) if mutation is not None else None
        ),
        "operations_performed": _operation_accounting(
            strong_read_calls=strong_read_calls,
            model_inferences=model_inferences,
            schema_writes=schema_writes,
            card_writes=card_writes,
        ),
        **(details or {}),
    }
    accounting_complete = mutation is not None and len(reads) == strong_read_calls
    completed_request_summary = dict(payload["request_summary"])
    if accounting_complete:
        payload["request_summary"]["accounting_complete"] = True
        payload["request_accounting_mode"] = "exact"
    else:
        payload["known_lower_bound_request_summary"] = completed_request_summary
        payload["request_summary"] = {
            "namespace_list_requests": None,
            "metadata_requests": None,
            "catalog_page_query_requests": None,
            "mutation_verification_query_requests": None,
            "write_requests": 1,
            "total_requests": None,
            "billing": completed_request_summary["billing"],
            "accounting_complete": False,
        }
        payload["request_accounting_mode"] = "known_lower_bound"
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"{operation} failed after one {write_kind} write attempt.", file=sys.stderr)
        print(f"{failure} Perform a fresh preview before any retry.", file=sys.stderr)
        print(
            "operations: strong_reads="
            f"{strong_read_calls}; model_inferences={model_inferences}; "
            f"schema_writes={schema_writes}; card_writes={card_writes}; "
            "content=0; deletes=0",
            file=sys.stderr,
        )
        print(
            "request accounting: "
            f"{'exact' if accounting_complete else 'known lower bound'}",
            file=sys.stderr,
        )
    return 2


def _matches(card: NamespaceCard, needle: str) -> bool:
    return any(
        needle in canonical_text(value)
        for value in (
            card.namespace,
            card.title,
            card.summary,
            *card.aliases,
            *card.tags,
            *card.routing_examples,
        )
    )


def _find(snapshot: RemoteCatalogSnapshot, namespace: str) -> NamespaceCard:
    card = next((item for item in snapshot.cards if item.namespace == namespace), None)
    if card is None:
        raise RemoteCatalogError(f"remote catalog has no card for namespace {namespace!r}")
    return card


def _card_status(snapshot: RemoteCatalogSnapshot, card: NamespaceCard) -> str:
    if card.namespace in snapshot.stale_target_ids:
        return "stale"
    if card.namespace in snapshot.disabled_ids:
        return "disabled"
    if card.namespace in snapshot.incompatible_ids:
        return "incompatible"
    if any(item.namespace == card.namespace for item in snapshot.eligible_cards):
        return "eligible"
    return "unknown"


def _listed_card(snapshot: RemoteCatalogSnapshot, card: NamespaceCard) -> dict[str, object]:
    return {
        **card_to_dict(card, include_routing_passages=False),
        "catalog_status": _card_status(snapshot, card),
        "target_status": (
            "live" if card.namespace in snapshot.live_namespace_ids else "stale"
        ),
    }


def _run_list(args: argparse.Namespace) -> int:
    try:
        _client, snapshot = _read(args)
        needle = canonical_text(args.search) if args.search is not None else ""
        live = set(snapshot.live_namespace_ids)
        cards = [
            card for card in snapshot.cards
            if (args.all or (card.enabled and card.namespace in live))
            and (not needle or _matches(card, needle))
        ]
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    payload = {
        **_base_payload("catalog list", _resolved_region(args), snapshot),
        "search": args.search,
        "all": args.all,
        "count": len(cards),
        "cards": [_listed_card(snapshot, card) for card in cards],
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote routing catalog {REMOTE_CATALOG_NAMESPACE} ({len(cards)} card(s))",
        *[
            f"  {card.namespace}: {card.title} ({_card_status(snapshot, card)})"
            for card in cards
        ],
        *(
            ["  missing cards: " + ", ".join(snapshot.missing_card_ids)]
            if snapshot.missing_card_ids else []
        ),
    ])
    return 0


def _run_show(args: argparse.Namespace) -> int:
    if args.include_vector and not args.json:
        print("--include-vector requires --json", file=sys.stderr)
        return 2
    try:
        _client, snapshot = _read(args)
        card = _find(snapshot, args.namespace)
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    payload = {
        **_base_payload("catalog show", _resolved_region(args), snapshot),
        "namespace": card.namespace,
        "target_status": "live" if card.namespace in snapshot.live_namespace_ids else "stale",
        "catalog_status": _card_status(snapshot, card),
        "card": card_to_dict(
            card,
            include_vector=args.include_vector,
            include_routing_passages=False,
        ),
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote namespace card: {card.namespace}",
        f"  authority: {REMOTE_CATALOG_NAMESPACE}",
        f"  target: {payload['target_status']}; {_card_status(snapshot, card)}",
        f"  title: {card.title}",
        f"  summary: {card.summary}",
        "  vector: hidden (use --include-vector with --json)",
    ])
    return 0


def _run_upsert(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    try:
        client, snapshot = _read(args)
        if args.namespace not in snapshot.live_namespace_ids:
            raise RemoteCatalogError(f"target namespace {args.namespace!r} is not live in region {region!r}")
        existing = next((item for item in snapshot.cards if item.namespace == args.namespace), None)
        # Source-derived passages are apply-owned. A generic manual upsert may
        # rebuild their projection when editable card metadata changes, but it
        # must preserve the exact passage bank (and fail rather than evicting a
        # passage when reviewed examples exhaust the shared evidence budget).
        routing_passages = list(existing.routing_passages) if existing else []
        fields = CardFields(
            namespace=args.namespace,
            enabled=False if args.disabled else (existing.enabled if existing else True),
            source_kind=args.source_kind,
            source_uri=args.source_uri,
            site_id=args.site_id,
            title=args.title,
            summary=args.summary,
            aliases=list(args.alias),
            tags=list(args.tag),
            semantic_origin="manual",
            region=region,
            embedding_model=args.embedding_model,
            embedding_precision=args.embedding_precision,
            plan_schema_version=args.plan_schema_version,
            ranking_mode=args.ranking_mode,
            ranking_profile=args.ranking_profile.replace("-", "_"),
            ranking_pool=args.ranking_pool,
            ranking_aggregation=args.ranking_aggregation.replace("-", "_"),
            last_plan_id=existing.last_plan_id if existing else None,
            last_apply_id=existing.last_apply_id if existing else None,
            routing_examples=list(args.routing_example),
            routing_passages=routing_passages,
        )
        if (
            args.approve
            and fields.routing_examples
            and snapshot.catalog_schema_version == 1
        ):
            raise RemoteCatalogError(
                "routing_examples approval requires the explicit reader-first "
                "remote catalog schema-v2 migration; no schema-v1 write occurred"
            )
        if (
            args.approve
            and fields.routing_passages
            and snapshot.catalog_schema_version != REMOTE_SCHEMA_V3
        ):
            raise RemoteCatalogError(
                "routing_passages approval requires the explicit reader-first "
                "remote catalog schema-v3 migration; no schema-v1/v2 write occurred"
            )
        card = prepare_card(fields, existing=existing)
        if args.approve:
            resource = remote_catalog_resource(client)
            result = (
                create_remote_cards(
                    resource,
                    [card],
                    region=region,
                    schema_version=snapshot.catalog_schema_version,
                )
                if existing is None
                else update_remote_card(
                    resource,
                    card,
                    expected_revision=existing.card_revision,
                    region=region,
                    schema_version=snapshot.catalog_schema_version,
                )
            )
            final = read_remote_catalog(client, region=region, compatibility=_compatibility(region))
            card = _find(final, args.namespace)
        else:
            result = None
            final = snapshot
    except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
        return _remote_failure(exc)
    payload = {
        **_base_payload(
            "catalog upsert", region, final,
            reads=(snapshot.metrics, final.metrics) if args.approve else (snapshot.metrics,),
            mutations=(result,) if result else (),
        ),
        "namespace": card.namespace,
        "approved": args.approve,
        "mutation_status": (
            "preview"
            if not args.approve
            else "unchanged"
            if result is not None and not result.changed
            else "created"
            if existing is None
            else "updated"
        ),
        "affected_ids": list(result.affected_ids) if result else [],
        "card": card_to_dict(card, include_routing_passages=False),
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"{payload['mutation_status'].title()} remote namespace card {card.namespace!r}.",
        "No write occurred; pass --approve to commit this exact card." if not args.approve else "Approved catalog-only write completed.",
    ])
    return 0


def _run_repair_apply(args: argparse.Namespace) -> int:
    """Rebuild one card from retained, state-bound plan authority."""

    from buoy_search.apply import (
        ApplyPlanError,
        _CatalogRegistrationAttemptError,
        inspect_apply_catalog_repair,
        load_verified_catalog_repair_plan,
        register_apply_catalog_card,
    )
    from buoy_search.plan_cleanup import cleanup_applied_plan_directory

    region = _resolved_region(args)
    try:
        args.state_root, _ = resolve_state_root(args.state_root)
        namespace = _operator_namespace(args.namespace)
        expected_revision = (
            _approval_sha256(
                args.expected_card_revision,
                option="--expected-card-revision",
            )
            if args.expected_card_revision is not None
            else None
        )
        if args.inspect_current and args.approve:
            raise ValueError("--inspect-current cannot be combined with --approve")

        # This local-only pass supplies the lock identity. The plan and its
        # committed state are both revalidated after the lock is held.
        preliminary = load_verified_catalog_repair_plan(
            plan_path=args.plan,
            namespace=namespace,
            state_root=args.state_root,
            apply_id=args.apply_id,
        )
        with acquire_namespace_apply_lock(
            site_id=str(preliminary.plan["site_id"]),
            namespace=namespace,
            state_root=preliminary.state_root,
        ):
            verified = load_verified_catalog_repair_plan(
                plan_path=args.plan,
                namespace=namespace,
                state_root=args.state_root,
                apply_id=args.apply_id,
            )
            if (
                verified.plan["site_id"] != preliminary.plan["site_id"]
                or verified.plan["plan_id"] != preliminary.plan["plan_id"]
                or verified.plan["artifact_hash"]
                != preliminary.plan["artifact_hash"]
                or verified.plan_directory_device
                != preliminary.plan_directory_device
                or verified.plan_directory_inode
                != preliminary.plan_directory_inode
            ):
                raise ApplyPlanError(
                    "Retained plan changed before catalog repair acquired its lock."
                )
            config = RuntimeConfig(
                namespace=namespace,
                region=region,
                embedding_model=str(verified.plan["embedding_model"]),
                embedding_precision=str(
                    verified.plan.get("embedding_precision", "float32")
                ),
            )

            if args.inspect_current:
                inspection = inspect_apply_catalog_repair(
                    verified,
                    config=config,
                    namespace=namespace,
                    apply_id=args.apply_id,
                    api_key=_credentials(),
                )
                payload = {
                    "command": "catalog repair-apply",
                    "approved": False,
                    "inspection": True,
                    "namespace": namespace,
                    "region": region,
                    "plan_id": verified.plan["plan_id"],
                    "apply_id": args.apply_id,
                    "routing_passage_count": len(verified.routing_prototypes),
                    "turbopuffer_api_calls": True,
                    "routing_model_loaded": False,
                    "catalog_card_write_attempted": False,
                    "mutation_status": "inspection",
                    "plan_retained": True,
                    **inspection,
                }
                _emit(
                    payload,
                    json_output=args.json,
                    text_lines=[
                        f"Inspected current routing state for {namespace!r}.",
                        "No model or write occurred; the verified plan was retained.",
                        f"Run: {inspection['catalog_repair_command']}",
                    ],
                )
                return 0

            if not args.approve:
                payload = {
                    "command": "catalog repair-apply",
                    "approved": False,
                    "inspection": False,
                    "namespace": namespace,
                    "region": region,
                    "plan_id": verified.plan["plan_id"],
                    "apply_id": args.apply_id,
                    "routing_passage_count": len(verified.routing_prototypes),
                    "precondition": (
                        {"card_revision": expected_revision}
                        if expected_revision is not None
                        else {"card_absent": True}
                    ),
                    "turbopuffer_api_calls": False,
                    "routing_model_loaded": False,
                    "mutation_status": "preview",
                }
                _emit(
                    payload,
                    json_output=args.json,
                    text_lines=[
                        f"Verified retained repair authority for {namespace!r}.",
                        "No provider or model call occurred; rerun with --approve.",
                    ],
                )
                return 0

            try:
                registration = register_apply_catalog_card(
                    verified,
                    config=config,
                    namespace=namespace,
                    apply_id=args.apply_id,
                    api_key=_credentials(),
                    expected_card_revision=expected_revision,
                    expect_absent=bool(args.expect_absent),
                )
            except _CatalogRegistrationAttemptError as exc:
                payload = {
                    "command": "catalog repair-apply",
                    "approved": True,
                    "namespace": namespace,
                    "region": region,
                    "plan_id": verified.plan["plan_id"],
                    "apply_id": args.apply_id,
                    "mutation_status": "failed",
                    "catalog_registered": False,
                    "automatic_retrieval_ready": False,
                    "catalog_card_write_attempted": exc.card_write_attempted,
                    "turbopuffer_api_calls": exc.api_calls_occurred,
                    "plan_retained_for_catalog_repair": True,
                    "catalog_error": str(exc),
                    "catalog_repair_command": exc.repair_command,
                }
                if args.json:
                    print(json.dumps(payload, indent=2, sort_keys=True))
                else:
                    print(str(exc), file=sys.stderr)
                    print(
                        "The verified plan remains available for repair.",
                        file=sys.stderr,
                    )
                    print(
                        f"Repair with: {exc.repair_command}",
                        file=sys.stderr,
                    )
                return 2

            cleanup_warnings = cleanup_applied_plan_directory(
                verified.plan_path,
                state_root=verified.state_root,
                expected_plan_id=str(verified.plan["plan_id"]),
                expected_artifact_hash=str(verified.plan["artifact_hash"]),
                expected_namespace=namespace,
                expected_directory_device=verified.plan_directory_device,
                expected_directory_inode=verified.plan_directory_inode,
            )
    except (
        ApplyPlanError,
        AppliedStateError,
        RemoteCatalogError,
        CatalogError,
        RuntimeConfigError,
        RuntimeError,
        OSError,
        ValueError,
    ) as exc:
        return _remote_failure(exc)

    payload = {
        "command": "catalog repair-apply",
        "approved": True,
        "namespace": namespace,
        "region": region,
        "plan_id": verified.plan["plan_id"],
        "apply_id": args.apply_id,
        "mutation_status": registration["catalog_mutation_status"],
        "plan_retained": verified.plan_path.exists(),
        "cleanup_warnings": cleanup_warnings,
        **registration,
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Repaired routing card for {namespace!r} from the retained plan.",
            *[f"Warning: {warning}" for warning in cleanup_warnings],
        ],
    )
    return 0


def _run_migrate_routing_v2(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    snapshot: RemoteCatalogSnapshot | None = None
    strong_read_calls: int | None = 0
    model_inferences: int | None = 0
    try:
        expected_snapshot: str | None = None
        expected_projection: str | None = None
        if args.approve:
            expected_snapshot = _approval_sha256(
                args.expected_snapshot_revision,
                option="--expected-snapshot-revision",
            )
            expected_projection = _approval_sha256(
                args.expected_projection_sha256,
                option="--expected-projection-sha256",
            )

        compatibility = _compatibility(region)
        client = REMOTE_CATALOG_CLIENT_FACTORY(
            api_key=_credentials(),
            region=region,
        )
        strong_read_calls = None
        snapshot = read_remote_catalog(
            client,
            region=region,
            compatibility=compatibility,
        )
        strong_read_calls = 1
        observed_projection = remote_catalog_projection_sha256(snapshot)
        observed_schema_fingerprint = remote_catalog_schema_fingerprint(
            snapshot.catalog_schema_version
        )
        mutation: MutationResult | None = None
        final = snapshot
        mutation_status = "preview"
        strong_read_calls = 1

        if args.approve:
            if snapshot.snapshot_revision != expected_snapshot:
                raise _CatalogOperatorError(
                    "catalog snapshot drifted from --expected-snapshot-revision; regenerate the preview"
                )
            if observed_projection != expected_projection:
                raise _CatalogOperatorError(
                    "catalog projection drifted from --expected-projection-sha256; regenerate the preview"
                )
            if snapshot.catalog_schema_version == REMOTE_SCHEMA_V2:
                mutation_status = "already_v2"
            elif snapshot.catalog_schema_version == REMOTE_SCHEMA_V1:
                resource = remote_catalog_resource(client)
                try:
                    mutation = migrate_remote_catalog_schema_v2(resource)
                    _require_exact_schema_mutation(mutation)
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog migrate-routing-v2",
                        operation="Routing catalog schema migration",
                        region=region,
                        snapshot=snapshot,
                        reads=(snapshot.metrics,),
                        mutation=mutation,
                        write_kind="schema",
                        strong_read_calls=1,
                        model_inferences=0,
                        failure=(
                            "The schema write did not return a valid, verified response."
                        ),
                        details={
                            "observed_snapshot_revision": snapshot.snapshot_revision,
                            "observed_projection_sha256": observed_projection,
                        },
                    )
                verification_reads = (snapshot.metrics,)
                try:
                    final = read_remote_catalog(
                        client,
                        region=region,
                        compatibility=compatibility,
                    )
                    strong_read_calls += 1
                    verification_reads = (snapshot.metrics, final.metrics)
                    _require_exact_migration_result(snapshot, final)
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog migrate-routing-v2",
                        operation="Routing catalog schema migration",
                        region=region,
                        snapshot=snapshot,
                        reads=verification_reads,
                        mutation=mutation,
                        write_kind="schema",
                        strong_read_calls=2,
                        model_inferences=0,
                        failure=(
                            "The post-write catalog could not be proven as the exact "
                            "unchanged v2 projection."
                        ),
                        details={
                            "observed_snapshot_revision": snapshot.snapshot_revision,
                            "observed_projection_sha256": observed_projection,
                        },
                    )
                mutation_status = "migrated"
            else:  # Defensive: the exact reader currently admits only v1 or v2.
                raise _CatalogOperatorError("catalog schema is not an exact supported version")

        final_projection = remote_catalog_projection_sha256(final)
        performed_schema_writes = (
            mutation.metrics.write_requests if mutation is not None else 0
        )
        reads = (
            (snapshot.metrics, final.metrics)
            if strong_read_calls == 2
            else (snapshot.metrics,)
        )
    except (
        RemoteCatalogError,
        CatalogError,
        RuntimeConfigError,
        RuntimeError,
        OSError,
    ) as exc:
        return _operator_failure(
            exc,
            args=args,
            command="catalog migrate-routing-v2",
            operation="routing schema migration",
            region=region,
            snapshot=snapshot,
            strong_read_calls=strong_read_calls,
            model_inferences=model_inferences,
        )

    payload = {
        **_base_payload(
            "catalog migrate-routing-v2",
            region,
            final,
            reads=reads,
            mutations=(mutation,) if mutation is not None else (),
        ),
        "approved": args.approve,
        "mutation_status": mutation_status,
        "verification_complete": args.approve,
        "observed_snapshot_revision": snapshot.snapshot_revision,
        "expected_snapshot_revision": snapshot.snapshot_revision,
        "observed_projection_sha256": observed_projection,
        "expected_projection_sha256": observed_projection,
        "final_projection_sha256": final_projection,
        "schema": {
            "observed_version": snapshot.catalog_schema_version,
            "target_version": REMOTE_SCHEMA_V2,
            "final_version": final.catalog_schema_version,
            "observed_fingerprint_sha256": observed_schema_fingerprint,
            "final_fingerprint_sha256": remote_catalog_schema_fingerprint(
                final.catalog_schema_version
            ),
            "additions": REMOTE_CATALOG_SCHEMA_V2_ADDITIONS,
        },
        "card_identities": _card_identities(snapshot),
        "old_reader_warning": (
            "Exact schema-v1 readers fail closed after this additive migration; "
            "deploy the v1/v2-compatible reader first."
        ),
        "operation_budget": _operation_accounting(
            strong_read_calls=2,
            schema_writes=1,
        ),
        "operations_performed": _operation_accounting(
            strong_read_calls=strong_read_calls,
            schema_writes=performed_schema_writes,
        ),
        "affected_ids": list(mutation.affected_ids) if mutation else [],
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Routing catalog schema v2: {mutation_status}.",
            f"  catalog: {REMOTE_CATALOG_NAMESPACE} ({region})",
            f"  observed schema: v{snapshot.catalog_schema_version}; target: v{REMOTE_SCHEMA_V2}",
            f"  schema fingerprint: {observed_schema_fingerprint}",
            f"  snapshot revision: {snapshot.snapshot_revision}",
            f"  projection sha256: {observed_projection}",
            "  exact schema additions:",
            *[
                f"    {name}: "
                + json.dumps(config, sort_keys=True, separators=(",", ":"))
                for name, config in REMOTE_CATALOG_SCHEMA_V2_ADDITIONS.items()
            ],
            f"  card bindings ({len(snapshot.cards)}):",
            *[
                "    "
                f"{identity['namespace']} | {identity['row_id']} | "
                f"{identity['card_revision']}"
                for identity in _card_identities(snapshot)
            ],
            "  operations: strong_reads="
            f"{strong_read_calls}; model_inferences=0",
            "  writes: schema="
            f"{performed_schema_writes}; cards=0; content=0; deletes=0",
            "  approval budget: strong_reads<=2; model_inferences=0; "
            "schema_writes<=1; card_writes=0; content=0; deletes=0",
            payload["old_reader_warning"],
            *(
                [
                    "No write occurred. Review the bindings, then rerun with "
                    "--expected-snapshot-revision and --expected-projection-sha256 --approve."
                ]
                if not args.approve
                else [
                    "No write occurred; the catalog was already exact schema v2."
                    if mutation_status == "already_v2"
                    else "Approved catalog-only schema write completed and verified."
                ]
            ),
        ],
    )
    return 0


def _run_migrate_routing_v3(args: argparse.Namespace) -> int:
    """Preview or approve the exact schema-v2 to schema-v3 migration."""

    region = _resolved_region(args)
    snapshot: RemoteCatalogSnapshot | None = None
    strong_read_calls: int | None = 0
    model_inferences: int | None = 0
    try:
        expected_snapshot: str | None = None
        expected_projection: str | None = None
        if args.approve:
            expected_snapshot = _approval_sha256(
                args.expected_snapshot_revision,
                option="--expected-snapshot-revision",
            )
            expected_projection = _approval_sha256(
                args.expected_projection_sha256,
                option="--expected-projection-sha256",
            )

        compatibility = _compatibility(region)
        client = REMOTE_CATALOG_CLIENT_FACTORY(
            api_key=_credentials(),
            region=region,
        )
        strong_read_calls = None
        snapshot = read_remote_catalog(
            client,
            region=region,
            compatibility=compatibility,
        )
        strong_read_calls = 1
        if snapshot.catalog_schema_version == REMOTE_SCHEMA_V1:
            raise _CatalogOperatorError(
                "migrate-routing-v3 requires exact schema v2 first; preview and "
                "approve migrate-routing-v2 before this migration"
            )
        observed_projection = remote_catalog_projection_sha256(snapshot)
        observed_schema_fingerprint = remote_catalog_schema_fingerprint(
            snapshot.catalog_schema_version
        )
        mutation: MutationResult | None = None
        final = snapshot
        mutation_status = "preview"

        if args.approve:
            if snapshot.snapshot_revision != expected_snapshot:
                raise _CatalogOperatorError(
                    "catalog snapshot drifted from --expected-snapshot-revision; regenerate the preview"
                )
            if observed_projection != expected_projection:
                raise _CatalogOperatorError(
                    "catalog projection drifted from --expected-projection-sha256; regenerate the preview"
                )
            if snapshot.catalog_schema_version == REMOTE_SCHEMA_V3:
                mutation_status = "already_v3"
            elif snapshot.catalog_schema_version == REMOTE_SCHEMA_V2:
                resource = remote_catalog_resource(client)
                try:
                    mutation = migrate_remote_catalog_schema_v3(resource)
                    _require_exact_schema_mutation(mutation)
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog migrate-routing-v3",
                        operation="Routing passage catalog schema migration",
                        region=region,
                        snapshot=snapshot,
                        reads=(snapshot.metrics,),
                        mutation=mutation,
                        write_kind="schema",
                        strong_read_calls=1,
                        model_inferences=0,
                        failure=(
                            "The schema-v3 write did not return a valid, verified response."
                        ),
                        details={
                            "observed_snapshot_revision": snapshot.snapshot_revision,
                            "observed_projection_sha256": observed_projection,
                        },
                    )
                verification_reads = (snapshot.metrics,)
                try:
                    final = read_remote_catalog(
                        client,
                        region=region,
                        compatibility=compatibility,
                    )
                    strong_read_calls += 1
                    verification_reads = (snapshot.metrics, final.metrics)
                    _require_exact_migration_result(
                        snapshot,
                        final,
                        expected_schema_version=REMOTE_SCHEMA_V3,
                    )
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog migrate-routing-v3",
                        operation="Routing passage catalog schema migration",
                        region=region,
                        snapshot=snapshot,
                        reads=verification_reads,
                        mutation=mutation,
                        write_kind="schema",
                        strong_read_calls=2,
                        model_inferences=0,
                        failure=(
                            "The post-write catalog could not be proven as the exact "
                            "unchanged v3 projection."
                        ),
                        details={
                            "observed_snapshot_revision": snapshot.snapshot_revision,
                            "observed_projection_sha256": observed_projection,
                        },
                    )
                mutation_status = "migrated"
            else:
                raise _CatalogOperatorError(
                    "catalog schema is not an exact supported version"
                )

        final_projection = remote_catalog_projection_sha256(final)
        performed_schema_writes = (
            mutation.metrics.write_requests if mutation is not None else 0
        )
        reads = (
            (snapshot.metrics, final.metrics)
            if strong_read_calls == 2
            else (snapshot.metrics,)
        )
    except (
        RemoteCatalogError,
        CatalogError,
        RuntimeConfigError,
        RuntimeError,
        OSError,
    ) as exc:
        return _operator_failure(
            exc,
            args=args,
            command="catalog migrate-routing-v3",
            operation="routing-passage schema migration",
            region=region,
            snapshot=snapshot,
            strong_read_calls=strong_read_calls,
            model_inferences=model_inferences,
        )

    payload = {
        **_base_payload(
            "catalog migrate-routing-v3",
            region,
            final,
            reads=reads,
            mutations=(mutation,) if mutation is not None else (),
        ),
        "approved": args.approve,
        "mutation_status": mutation_status,
        "verification_complete": args.approve,
        "observed_snapshot_revision": snapshot.snapshot_revision,
        "expected_snapshot_revision": snapshot.snapshot_revision,
        "observed_projection_sha256": observed_projection,
        "expected_projection_sha256": observed_projection,
        "final_projection_sha256": final_projection,
        "schema": {
            "observed_version": snapshot.catalog_schema_version,
            "target_version": REMOTE_SCHEMA_V3,
            "final_version": final.catalog_schema_version,
            "observed_fingerprint_sha256": observed_schema_fingerprint,
            "final_fingerprint_sha256": remote_catalog_schema_fingerprint(
                final.catalog_schema_version
            ),
            "additions": REMOTE_CATALOG_SCHEMA_V3_ADDITIONS,
        },
        "card_identities": _card_identities(snapshot),
        "old_reader_warning": (
            "Exact schema-v1/v2 readers fail closed after this additive migration; "
            "deploy the v1/v2/v3-compatible reader first."
        ),
        "operation_budget": _operation_accounting(
            strong_read_calls=2,
            schema_writes=1,
        ),
        "operations_performed": _operation_accounting(
            strong_read_calls=strong_read_calls,
            schema_writes=performed_schema_writes,
        ),
        "affected_ids": list(mutation.affected_ids) if mutation else [],
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Routing catalog schema v3: {mutation_status}.",
            f"  catalog: {REMOTE_CATALOG_NAMESPACE} ({region})",
            f"  observed schema: v{snapshot.catalog_schema_version}; target: v{REMOTE_SCHEMA_V3}",
            f"  schema fingerprint: {observed_schema_fingerprint}",
            f"  snapshot revision: {snapshot.snapshot_revision}",
            f"  projection sha256: {observed_projection}",
            "  exact schema additions:",
            *[
                f"    {name}: "
                + json.dumps(config, sort_keys=True, separators=(",", ":"))
                for name, config in REMOTE_CATALOG_SCHEMA_V3_ADDITIONS.items()
            ],
            "  operations: strong_reads="
            f"{strong_read_calls}; model_inferences=0",
            "  writes: schema="
            f"{performed_schema_writes}; cards=0; content=0; deletes=0",
            payload["old_reader_warning"],
            *(
                [
                    "No write occurred. Review the bindings, then rerun with "
                    "--expected-snapshot-revision and --expected-projection-sha256 --approve."
                ]
                if not args.approve
                else [
                    "No write occurred; the catalog was already exact schema v3."
                    if mutation_status == "already_v3"
                    else "Approved catalog-only schema-v3 write completed and verified."
                ]
            ),
        ],
    )
    return 0


def _run_set_routing_examples(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    snapshot: RemoteCatalogSnapshot | None = None
    strong_read_calls: int | None = 0
    model_inferences: int | None = 0
    try:
        namespace = _operator_namespace(args.namespace)
        examples = _normalized_reviewed_examples(args.routing_example)
        expected_revision: str | None = None
        if args.approve:
            expected_revision = _approval_sha256(
                args.expected_card_revision,
                option="--expected-card-revision",
            )

        compatibility = _compatibility(region)
        client = REMOTE_CATALOG_CLIENT_FACTORY(
            api_key=_credentials(),
            region=region,
        )
        strong_read_calls = None
        snapshot = read_remote_catalog(
            client,
            region=region,
            compatibility=compatibility,
        )
        strong_read_calls = 1
        if snapshot.catalog_schema_version not in {
            REMOTE_SCHEMA_V2,
            REMOTE_SCHEMA_V3,
        }:
            raise _CatalogOperatorError(
                "set-routing-examples requires an exact schema-v2 or schema-v3 catalog; "
                "preview and approve migrate-routing-v2 first"
            )
        current = next(
            (card for card in snapshot.cards if card.namespace == namespace),
            None,
        )
        if current is None:
            raise _CatalogOperatorError(
                "remote catalog has no card for the requested namespace"
            )
        status = _card_status(snapshot, current)
        if status not in {"eligible", "disabled"}:
            raise _CatalogOperatorError(
                "routing examples may only be set on an eligible or disabled non-stale card"
            )
        if args.approve and current.card_revision != expected_revision:
            raise _CatalogOperatorError(
                "card revision drifted from --expected-card-revision; regenerate the preview"
            )

        examples_changed = current.routing_examples != examples
        if examples_changed:
            model_inferences = None
            intended = prepare_card(
                _card_fields_with_examples(current, examples),
                existing=current,
                now=utc_now(),
            )
            _require_bounded_example_candidate(current, intended, examples)
            model_inferences = 1
        else:
            intended = current
            model_inferences = 0

        mutation: MutationResult | None = None
        final = snapshot
        verified: NamespaceCard | None = None
        strong_read_calls = 1
        mutation_status = "preview"
        if args.approve:
            if examples_changed:
                resource = remote_catalog_resource(client)
                try:
                    mutation = update_remote_card(
                        resource,
                        intended,
                        expected_revision=current.card_revision,
                        region=region,
                        schema_version=snapshot.catalog_schema_version,
                    )
                    _require_exact_example_mutation(mutation, intended)
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog set-routing-examples",
                        operation="Routing example update",
                        region=region,
                        snapshot=snapshot,
                        reads=(snapshot.metrics,),
                        mutation=mutation,
                        write_kind="card",
                        strong_read_calls=1,
                        model_inferences=model_inferences,
                        failure=(
                            "The conditional card write did not return a valid, "
                            "verified result."
                        ),
                        details={
                            "namespace": current.namespace,
                            "current_card_revision": current.card_revision,
                            "intended_card_revision": intended.card_revision,
                        },
                    )
                verification_reads = (snapshot.metrics,)
                try:
                    final = read_remote_catalog(
                        client,
                        region=region,
                        compatibility=compatibility,
                    )
                    strong_read_calls += 1
                    verification_reads = (snapshot.metrics, final.metrics)
                    verified = _require_exact_example_result(
                        snapshot,
                        final,
                        intended,
                    )
                except Exception:
                    return _attempted_mutation_failure(
                        args=args,
                        command="catalog set-routing-examples",
                        operation="Routing example update",
                        region=region,
                        snapshot=snapshot,
                        reads=verification_reads,
                        mutation=mutation,
                        write_kind="card",
                        strong_read_calls=2,
                        model_inferences=model_inferences,
                        failure=(
                            "The post-write catalog could not be proven as the exact "
                            "one-card update with unchanged catalog invariants."
                        ),
                        details={
                            "namespace": current.namespace,
                            "current_card_revision": current.card_revision,
                            "intended_card_revision": intended.card_revision,
                        },
                    )
                mutation_status = "updated" if mutation.changed else "unchanged"
            else:
                verified = current
                mutation_status = "unchanged"

        performed_card_writes = (
            mutation.metrics.write_requests if mutation is not None else 0
        )
        reads = (
            (snapshot.metrics, final.metrics)
            if strong_read_calls == 2
            else (snapshot.metrics,)
        )
    except (
        RemoteCatalogError,
        CatalogError,
        RuntimeConfigError,
        RuntimeError,
        OSError,
    ) as exc:
        return _operator_failure(
            exc,
            args=args,
            command="catalog set-routing-examples",
            operation="routing example update",
            region=region,
            snapshot=snapshot,
            strong_read_calls=strong_read_calls,
            model_inferences=model_inferences,
        )

    payload = {
        **_base_payload(
            "catalog set-routing-examples",
            region,
            final,
            reads=reads,
            mutations=(mutation,) if mutation is not None else (),
        ),
        "namespace": current.namespace,
        "catalog_status": status,
        "approved": args.approve,
        "mutation_status": mutation_status,
        "routing_examples": examples,
        "current_card_revision": current.card_revision,
        "expected_card_revision": current.card_revision,
        "intended_card_revision": intended.card_revision,
        "verified_card_revision": (
            verified.card_revision if verified is not None else None
        ),
        "verification_complete": args.approve,
        "current_routing_prototype_hash": current.routing_prototype_hash,
        "intended_routing_prototype_hash": intended.routing_prototype_hash,
        "current_routing_prototype_vector_hash": (
            current.routing_prototype_vector_hash
        ),
        "intended_routing_prototype_vector_hash": (
            intended.routing_prototype_vector_hash
        ),
        "legacy_projection_preserved": True,
        "card": card_to_dict(
            verified if verified is not None else intended,
            include_routing_passages=False,
        ),
        "operation_budget": _operation_accounting(
            strong_read_calls=2,
            model_inferences=1,
            card_writes=1,
        ),
        "operations_performed": _operation_accounting(
            strong_read_calls=strong_read_calls,
            model_inferences=model_inferences,
            card_writes=performed_card_writes,
        ),
        "affected_ids": list(mutation.affected_ids) if mutation else [],
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Routing examples for {current.namespace!r}: {mutation_status}.",
            f"  normalized questions ({len(examples)}):",
            *[
                "    " + json.dumps(question, ensure_ascii=False)
                for question in examples
            ],
            f"  current revision: {current.card_revision}",
            f"  intended revision: {intended.card_revision}",
            f"  prototype hash: {intended.routing_prototype_hash}",
            "  prototype vector hash: "
            f"{intended.routing_prototype_vector_hash}",
            "  operations: strong_reads="
            f"{strong_read_calls}; model_inferences={model_inferences}",
            "  writes: schema=0; cards="
            f"{performed_card_writes}; content=0; deletes=0",
            "  approval budget: strong_reads<=2; model_inferences<=1; "
            "schema_writes=0; card_writes<=1; affected_cards<=1; "
            "content=0; deletes=0",
            *(
                [
                    "No write occurred. Review the questions and projection, then rerun "
                    "with --expected-card-revision and --approve."
                ]
                if not args.approve
                else [
                    "No write occurred; the canonical routing examples were already present."
                    if mutation_status == "unchanged"
                    else "Approved conditional catalog-card write completed and verified."
                ]
            ),
        ],
    )
    return 0


def _run_toggle(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    try:
        client, snapshot = _read(args)
        current = _find(snapshot, args.namespace)
        mutation: MutationResult | None = None
        intended = current
        if current.enabled != args.requested_enabled:
            intended = replace(
                current,
                enabled=args.requested_enabled,
                updated_at=utc_now(),
                card_revision="pending",
            )
            intended = replace(intended, card_revision=card_revision(intended))
        if current.enabled == args.requested_enabled or not args.approve:
            changed = False
            affected_ids: list[str] = []
        else:
            mutation = update_remote_card(
                remote_catalog_resource(client), intended,
                expected_revision=current.card_revision,
                region=region,
                schema_version=snapshot.catalog_schema_version,
            )
            changed = mutation.changed
            affected_ids = list(mutation.affected_ids)
        final = (
            read_remote_catalog(client, region=region, compatibility=_compatibility(region))
            if args.approve else snapshot
        )
        card = _find(final, args.namespace) if args.approve else intended
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    operation = "enable" if args.requested_enabled else "disable"
    payload = {
        **_base_payload(
            f"catalog {operation}", region, final,
            reads=(snapshot.metrics, final.metrics) if args.approve else (snapshot.metrics,),
            mutations=(mutation,) if mutation else (),
        ),
        "namespace": card.namespace,
        "approved": args.approve,
        "mutation_status": ("updated" if changed else "unchanged") if args.approve else "preview",
        "affected_ids": affected_ids,
        "card": card_to_dict(card, include_routing_passages=False),
    }
    desired = "enabled" if args.requested_enabled else "disabled"
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote card {card.namespace!r}: {payload['mutation_status']} {desired}.",
        "No write occurred; pass --approve to commit." if not args.approve else "Approved catalog-only write completed.",
    ])
    return 0
