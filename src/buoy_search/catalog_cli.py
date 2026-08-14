"""Authenticated remote routing-catalog CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import os
import sys

from buoy_search.catalog import (
    CardFields,
    CatalogError,
    NamespaceCard,
    canonical_text,
    card_revision,
    card_to_dict,
    prepare_card,
    utc_now,
)
from buoy_search.config import DEFAULT_REGION, load_config
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    MutationResult,
    ReadMetrics,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    create_client,
    create_remote_cards,
    read_remote_catalog,
    remote_catalog_resource,
    update_remote_card,
)


REMOTE_CATALOG_CLIENT_FACTORY = create_client


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


def _emit(payload: dict[str, object], *, json_output: bool, text_lines: list[str]) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in text_lines:
            print(line)


def _remote_failure(exc: Exception) -> int:
    print(str(exc), file=sys.stderr)
    return 2


def _matches(card: NamespaceCard, needle: str) -> bool:
    return any(
        needle in canonical_text(value)
        for value in (card.namespace, card.title, card.summary, *card.aliases, *card.tags)
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
        **card_to_dict(card),
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
        "card": card_to_dict(card, include_vector=args.include_vector),
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
        )
        card = prepare_card(fields, existing=existing)
        if args.approve:
            resource = remote_catalog_resource(client)
            result = (
                create_remote_cards(resource, [card], region=region)
                if existing is None
                else update_remote_card(resource, card, expected_revision=existing.card_revision, region=region)
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
        "card": card_to_dict(card),
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"{payload['mutation_status'].title()} remote namespace card {card.namespace!r}.",
        "No write occurred; pass --approve to commit this exact card." if not args.approve else "Approved catalog-only write completed.",
    ])
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
                expected_revision=current.card_revision, region=region,
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
        "card": card_to_dict(card),
    }
    desired = "enabled" if args.requested_enabled else "disabled"
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote card {card.namespace!r}: {payload['mutation_status']} {desired}.",
        "No write occurred; pass --approve to commit." if not args.approve else "Approved catalog-only write completed.",
    ])
    return 0
