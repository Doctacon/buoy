"""Argparse wiring and local-only output for ``buoy catalog``."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from buoy_search.catalog import (
    CATALOG_SCHEMA_VERSION,
    CardFields,
    CatalogDocument,
    CatalogError,
    NamespaceCard,
    canonical_text,
    card_to_dict,
    load_catalog,
    mutate_catalog,
    prepare_card,
    resolve_catalog_path,
)


def configure_catalog_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    catalog = subparsers.add_parser(
        "catalog",
        help="manage the canonical local namespace routing catalog",
        description=(
            "List and mutate local namespace cards. Catalog commands never read Turbopuffer "
            "credentials or contact Turbopuffer."
        ),
    )
    commands = catalog.add_subparsers(dest="catalog_command")

    list_parser = commands.add_parser("list", help="list enabled local cards")
    list_parser.add_argument("search", nargs="?", default=None)
    list_parser.add_argument("--all", action="store_true", help="Include disabled cards.")
    _add_common(list_parser)
    list_parser.set_defaults(func=_run_list)

    show = commands.add_parser("show", help="show one local card")
    show.add_argument("namespace")
    show.add_argument("--include-vector", action="store_true", help="Include the vector in JSON output.")
    _add_common(show)
    show.set_defaults(func=_run_show)

    upsert = commands.add_parser("upsert", help="create or update one complete manual card")
    upsert.add_argument("namespace")
    upsert.add_argument("--source-kind", required=True, choices=["github_repo", "website", "document"])
    upsert.add_argument("--source-uri", required=True)
    upsert.add_argument("--site-id", required=True)
    upsert.add_argument("--title", required=True)
    upsert.add_argument("--summary", required=True)
    upsert.add_argument("--alias", action="append", default=[])
    upsert.add_argument("--tag", action="append", default=[])
    upsert.add_argument("--region", required=True)
    upsert.add_argument("--embedding-model", required=True)
    upsert.add_argument("--embedding-precision", required=True, choices=["float32", "float16"])
    upsert.add_argument("--plan-schema-version", required=True, type=int)
    upsert.add_argument("--ranking-mode", required=True, choices=["file", "page", "chunk"])
    upsert.add_argument("--ranking-profile", required=True, choices=["repo-code", "none"])
    upsert.add_argument("--ranking-pool", required=True, type=_positive_int)
    upsert.add_argument(
        "--ranking-aggregation",
        required=True,
        choices=["max", "adaptive-sum-3", "capped-sum-3"],
    )
    upsert.add_argument("--disabled", action="store_true", help="Create disabled or disable the updated card.")
    _add_common(upsert)
    upsert.set_defaults(func=_run_upsert)

    for operation in ("enable", "disable"):
        parser = commands.add_parser(operation, help=f"{operation} one local card")
        parser.add_argument("namespace")
        _add_common(parser)
        parser.set_defaults(func=_run_toggle, requested_enabled=operation == "enable")

    remove = commands.add_parser("remove", help="preview or approve local-only card removal")
    remove.add_argument("namespace")
    remove.add_argument("--approve", action="store_true", help="Approve removal from local catalog only.")
    _add_common(remove)
    remove.set_defaults(func=_run_remove)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog", default=None, help="Override BUOY_CATALOG_PATH and the state-root catalog.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _path_for(args: argparse.Namespace) -> Path | None:
    try:
        path, warning = resolve_catalog_path(args.catalog)
    except CatalogError as exc:
        print(str(exc), file=sys.stderr)
        return None
    if warning:
        print(warning, file=sys.stderr)
    return path


def _load(path: Path) -> CatalogDocument | None:
    try:
        return load_catalog(path)
    except CatalogError as exc:
        print(str(exc), file=sys.stderr)
        return None


def _emit(payload: dict[str, object], *, json_output: bool, text_lines: list[str]) -> None:
    if json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for line in text_lines:
            print(line)


def _base_payload(command: str, path: Path, document: CatalogDocument) -> dict[str, object]:
    return {
        "command": command,
        "catalog_path": str(path),
        "catalog_revision": document.catalog_revision,
    }


def _run_list(args: argparse.Namespace) -> int:
    path = _path_for(args)
    if path is None:
        return 2
    document = _load(path)
    if document is None:
        return 2
    needle = canonical_text(args.search) if args.search is not None else ""
    cards = [
        card
        for card in document.cards
        if (args.all or card.enabled) and (not needle or _matches(card, needle))
    ]
    payload = {
        **_base_payload("catalog list", path, document),
        "search": args.search,
        "all": args.all,
        "count": len(cards),
        "cards": [card_to_dict(card) for card in cards],
    }
    lines = [f"Local namespace catalog: {path} ({len(cards)} card(s))"]
    lines.extend(
        f"  {card.namespace}: {card.title} ({'enabled' if card.enabled else 'disabled'})"
        for card in cards
    )
    _emit(payload, json_output=args.json, text_lines=lines)
    return 0


def _matches(card: NamespaceCard, needle: str) -> bool:
    values = [card.namespace, card.title, card.summary, *card.aliases, *card.tags]
    return any(needle in canonical_text(value) for value in values)


def _find(document: CatalogDocument, namespace: str, path: Path) -> NamespaceCard | None:
    card = next((item for item in document.cards if item.namespace == namespace), None)
    if card is None:
        print(f"catalog {path}: namespace {namespace!r} is not registered", file=sys.stderr)
    return card


def _run_show(args: argparse.Namespace) -> int:
    path = _path_for(args)
    if path is None:
        return 2
    document = _load(path)
    if document is None:
        return 2
    card = _find(document, args.namespace, path)
    if card is None:
        return 2
    payload = {
        **_base_payload("catalog show", path, document),
        "namespace": card.namespace,
        "card": card_to_dict(card, include_vector=bool(args.include_vector)),
    }
    lines = [
        f"Local namespace card: {card.namespace}",
        f"  catalog: {path}",
        f"  status: {'enabled' if card.enabled else 'disabled'}",
        f"  title: {card.title}",
        f"  summary: {card.summary}",
        f"  source: {card.source_kind} {card.source_uri}",
        f"  aliases: {', '.join(card.aliases) if card.aliases else 'none'}",
        f"  tags: {', '.join(card.tags) if card.tags else 'none'}",
        f"  retrieval: {card.region}; {card.embedding_model}/{card.embedding_precision}; {card.ranking_mode}/{card.ranking_profile}/{card.ranking_aggregation}",
        "  vector: hidden (use --include-vector with --json)",
    ]
    _emit(payload, json_output=args.json, text_lines=lines)
    return 0


def _run_upsert(args: argparse.Namespace) -> int:
    path = _path_for(args)
    if path is None:
        return 2
    try:
        def mutation(document: CatalogDocument):
            existing = next((item for item in document.cards if item.namespace == args.namespace), None)
            enabled = False if args.disabled else (existing.enabled if existing is not None else True)
            fields = CardFields(
                namespace=args.namespace,
                enabled=enabled,
                source_kind=args.source_kind,
                source_uri=args.source_uri,
                site_id=args.site_id,
                title=args.title,
                summary=args.summary,
                aliases=list(args.alias),
                tags=list(args.tag),
                semantic_origin="manual",
                region=args.region,
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
            cards = [item for item in document.cards if item.namespace != card.namespace] + [card]
            return cards, (card, existing is None), True

        document, result = mutate_catalog(path, mutation)
        card, created = result
    except (CatalogError, OSError) as exc:
        print(f"catalog {path}: {exc}" if not str(exc).startswith("catalog ") else str(exc), file=sys.stderr)
        return 2
    payload = {
        **_base_payload("catalog upsert", path, document),
        "namespace": card.namespace,
        "mutation_status": "created" if created else "updated",
        "card": card_to_dict(card),
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"{'Created' if created else 'Updated'} local namespace card {card.namespace!r} in {path}.",
            "No Turbopuffer credentials were read and no remote data was changed.",
        ],
    )
    return 0


def _run_toggle(args: argparse.Namespace) -> int:
    path = _path_for(args)
    if path is None:
        return 2
    try:
        def mutation(document: CatalogDocument):
            existing = next((item for item in document.cards if item.namespace == args.namespace), None)
            if existing is None:
                raise CatalogError(f"namespace {args.namespace!r} is not registered")
            if existing.enabled == args.requested_enabled:
                return document.cards, (existing, False), False
            from dataclasses import replace
            from buoy_search.catalog import card_revision, utc_now
            updated = replace(existing, enabled=args.requested_enabled, updated_at=utc_now(), card_revision="pending")
            updated = replace(updated, card_revision=card_revision(updated))
            cards = [item for item in document.cards if item.namespace != updated.namespace] + [updated]
            return cards, (updated, True), True

        document, result = mutate_catalog(path, mutation)
        card, changed = result
    except CatalogError as exc:
        print(f"catalog {path}: {exc}" if not str(exc).startswith("catalog ") else str(exc), file=sys.stderr)
        return 2
    operation = "enable" if args.requested_enabled else "disable"
    payload = {
        **_base_payload(f"catalog {operation}", path, document),
        "namespace": card.namespace,
        "mutation_status": "updated" if changed else "unchanged",
        "card": card_to_dict(card),
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Namespace {card.namespace!r} is {'enabled' if card.enabled else 'disabled'} in local catalog {path} "
            f"({'updated' if changed else 'unchanged'})."
        ],
    )
    return 0


def _run_remove(args: argparse.Namespace) -> int:
    path = _path_for(args)
    if path is None:
        return 2
    if not args.approve:
        document = _load(path)
        if document is None:
            return 2
        card = _find(document, args.namespace, path)
        if card is None:
            return 2
        payload = {
            **_base_payload("catalog remove", path, document),
            "namespace": card.namespace,
            "mutation_status": "preview",
            "approved": False,
            "card": card_to_dict(card),
            "remote_turbopuffer_untouched": True,
            "applied_state_untouched": True,
        }
        _emit(
            payload,
            json_output=args.json,
            text_lines=[
                f"Preview: remove namespace {card.namespace!r} from local catalog {path}.",
                "No mutation occurred. Re-run with --approve to remove only the local card.",
                "Remote Turbopuffer data and local applied state will remain untouched.",
            ],
        )
        return 0
    try:
        def mutation(document: CatalogDocument):
            existing = next((item for item in document.cards if item.namespace == args.namespace), None)
            if existing is None:
                raise CatalogError(f"namespace {args.namespace!r} is not registered")
            return [item for item in document.cards if item.namespace != args.namespace], existing, True

        document, card = mutate_catalog(path, mutation)
    except CatalogError as exc:
        print(f"catalog {path}: {exc}" if not str(exc).startswith("catalog ") else str(exc), file=sys.stderr)
        return 2
    payload = {
        **_base_payload("catalog remove", path, document),
        "namespace": card.namespace,
        "mutation_status": "removed",
        "approved": True,
        "card": card_to_dict(card),
        "remote_turbopuffer_untouched": True,
        "applied_state_untouched": True,
    }
    _emit(
        payload,
        json_output=args.json,
        text_lines=[
            f"Removed namespace {card.namespace!r} from local catalog {path} only.",
            "Remote Turbopuffer data and local applied state were untouched.",
        ],
    )
    return 0
