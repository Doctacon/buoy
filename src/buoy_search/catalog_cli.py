"""Authenticated remote routing-catalog CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, replace
import json
import os
from pathlib import Path
import stat
import sys

from buoy_search.catalog import (
    CardFields,
    CatalogError,
    NamespaceCard,
    canonical_text,
    card_revision,
    card_to_dict,
    load_routing_embedder,
    parse_catalog,
    prepare_card,
    utc_now,
)
from buoy_search.catalog_pending import (
    CatalogCommitPartialSuccess,
    PendingCatalogError,
    abandon_pending,
    reconcile_pending,
)
from buoy_search.config import DEFAULT_REGION, load_config
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    MutationResult,
    ReadMetrics,
    RemoteCatalogError,
    RemoteCatalogSnapshot,
    classify_migration_state,
    classify_remote_catalog,
    create_client,
    create_remote_cards,
    delete_remote_card,
    read_remote_catalog,
    read_remote_migration_snapshot,
    remote_card_id,
    update_remote_card,
)


REMOTE_CATALOG_CLIENT_FACTORY = create_client


def configure_catalog_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    catalog = subparsers.add_parser(
        "catalog",
        help="manage the remote namespace routing catalog",
        description=(
            f"Manage validated routing cards in remote namespace {REMOTE_CATALOG_NAMESPACE}. "
            "Commands require TURBOPUFFER_API_KEY except API-free pending abandonment preview."
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
    parser.add_argument("--source-kind", required=True, choices=["github_repo", "website", "document"])
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
    _add_common(parser)
    parser.set_defaults(func=_run_upsert)

    for operation in ("enable", "disable"):
        parser = commands.add_parser(operation, help=f"{operation} one remote card")
        parser.add_argument("namespace")
        _add_common(parser)
        parser.set_defaults(func=_run_toggle, requested_enabled=operation == "enable")

    parser = commands.add_parser("remove", help="preview or approve remote card removal")
    parser.add_argument("namespace")
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_remove)

    parser = commands.add_parser("migrate-local", help="migrate one validated schema-v1 local catalog")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_migrate_local)

    parser = commands.add_parser("reconcile", help="reconcile one pending approved-apply card write")
    parser.add_argument("--pending", type=Path, required=True)
    choices = parser.add_mutually_exclusive_group()
    choices.add_argument("--rebase", action="store_true")
    choices.add_argument("--accept-remote", action="store_true")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--expected-remote-revision")
    _add_common(parser)
    parser.set_defaults(func=_run_reconcile)

    parser = commands.add_parser("abandon-pending", help="preview or approve removal of unconfirmed pending state")
    parser.add_argument("--pending", type=Path, required=True)
    parser.add_argument("--approve", action="store_true")
    _add_common(parser)
    parser.set_defaults(func=_run_abandon_pending)


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
    config = load_config(ignore_environment_namespace=True)
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
        "cards": [card_to_dict(card) for card in cards],
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote routing catalog {REMOTE_CATALOG_NAMESPACE} ({len(cards)} card(s))",
        *[f"  {card.namespace}: {card.title} ({'enabled' if card.enabled else 'disabled'}; {'live' if card.namespace in live else 'stale'})" for card in cards],
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
        "card": card_to_dict(card, include_vector=args.include_vector),
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote namespace card: {card.namespace}",
        f"  authority: {REMOTE_CATALOG_NAMESPACE}",
        f"  target: {payload['target_status']}; {'enabled' if card.enabled else 'disabled'}",
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
        resource = client.namespace(REMOTE_CATALOG_NAMESPACE)
        result = (
            create_remote_cards(resource, [card], region=region)
            if existing is None
            else update_remote_card(resource, card, expected_revision=existing.card_revision, region=region)
        )
        final = read_remote_catalog(client, region=region, compatibility=_compatibility(region))
        card = _find(final, args.namespace)
    except (RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
        return _remote_failure(exc)
    payload = {
        **_base_payload(
            "catalog upsert", region, final,
            reads=(snapshot.metrics, final.metrics), mutations=(result,),
        ),
        "namespace": card.namespace,
        "mutation_status": "created" if existing is None else ("updated" if result.changed else "unchanged"),
        "affected_ids": list(result.affected_ids),
        "card": card_to_dict(card),
    }
    _emit(payload, json_output=args.json, text_lines=[f"{payload['mutation_status'].title()} remote namespace card {card.namespace!r}."])
    return 0


def _run_toggle(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    try:
        client, snapshot = _read(args)
        current = _find(snapshot, args.namespace)
        mutation: MutationResult | None = None
        if current.enabled == args.requested_enabled:
            changed = False
            affected_ids: list[str] = []
        else:
            card = replace(current, enabled=args.requested_enabled, updated_at=utc_now(), card_revision="pending")
            card = replace(card, card_revision=card_revision(card))
            mutation = update_remote_card(
                client.namespace(REMOTE_CATALOG_NAMESPACE), card,
                expected_revision=current.card_revision, region=region,
            )
            changed = mutation.changed
            affected_ids = list(mutation.affected_ids)
        final = read_remote_catalog(client, region=region, compatibility=_compatibility(region))
        card = _find(final, args.namespace)
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    operation = "enable" if args.requested_enabled else "disable"
    payload = {
        **_base_payload(
            f"catalog {operation}", region, final,
            reads=(snapshot.metrics, final.metrics),
            mutations=(mutation,) if mutation else (),
        ),
        "namespace": card.namespace,
        "mutation_status": "updated" if changed else "unchanged",
        "affected_ids": affected_ids,
        "card": card_to_dict(card),
    }
    _emit(payload, json_output=args.json, text_lines=[f"Remote card {card.namespace!r} is {'enabled' if card.enabled else 'disabled'} ({payload['mutation_status']})."])
    return 0


def _run_remove(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    try:
        client, snapshot = _read(args)
        card = _find(snapshot, args.namespace)
        if args.approve:
            result = delete_remote_card(
                client.namespace(REMOTE_CATALOG_NAMESPACE), namespace=card.namespace,
                expected_revision=card.card_revision, region=region,
            )
            final = read_remote_catalog(
                client, region=region, compatibility=_compatibility(region)
            )
            if any(item.namespace == card.namespace for item in final.cards):
                raise RemoteCatalogError("final remote catalog snapshot still contains the removed card")
        else:
            result = None
            final = snapshot
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    payload = {
        **_base_payload(
            "catalog remove", region, final,
            reads=(snapshot.metrics, final.metrics) if args.approve else (snapshot.metrics,),
            mutations=(result,) if result else (),
        ),
        "namespace": card.namespace,
        "expected_revision": card.card_revision,
        "approved": args.approve,
        "mutation_status": "removed" if args.approve else "preview",
        "affected_ids": list(result.affected_ids) if result else [],
        "content_namespace_untouched": True,
        "applied_state_untouched": True,
    }
    _emit(payload, json_output=args.json, text_lines=[
        f"{'Removed' if args.approve else 'Preview: remove'} remote card {card.namespace!r}.",
        "Target content namespace, content rows, and local applied state are untouched.",
    ])
    return 0


@dataclass
class _BoundMigrationSource:
    path: Path
    fd: int
    initial_stat: os.stat_result
    data: bytes

    def revalidate(self) -> None:
        try:
            current_fd = os.fstat(self.fd)
            current_path = self.path.stat(follow_symlinks=False)
        except OSError as exc:
            raise CatalogError(f"migration source changed before remote write: {self.path}: {exc}") from exc
        identity = lambda value: (  # noqa: E731 - compact immutable identity projection.
            value.st_dev, value.st_ino, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns,
        )
        if (
            not stat.S_ISREG(current_path.st_mode)
            or identity(current_fd) != identity(self.initial_stat)
            or (current_path.st_dev, current_path.st_ino) != (current_fd.st_dev, current_fd.st_ino)
        ):
            raise CatalogError(f"migration source changed before remote write: {self.path}")
        os.lseek(self.fd, 0, os.SEEK_SET)
        if _read_all(self.fd) != self.data:
            raise CatalogError(f"migration source contents changed before remote write: {self.path}")

    def close(self) -> None:
        os.close(self.fd)


def _read_all(fd: int) -> bytes:
    chunks: list[bytes] = []
    while chunk := os.read(fd, 1024 * 1024):
        chunks.append(chunk)
    return b"".join(chunks)


def _open_migration_source(path: Path) -> _BoundMigrationSource:
    try:
        original = path.lstat()
        if stat.S_ISLNK(original.st_mode) or not stat.S_ISREG(original.st_mode):
            raise CatalogError(f"migration source must be a regular non-symlink file: {path}")
        resolved = path.resolve(strict=True)
        no_follow = getattr(os, "O_NOFOLLOW", None)
        if no_follow is None:
            raise CatalogError("migration source cannot be opened safely on this platform")
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | no_follow
        fd = os.open(resolved, flags)
    except CatalogError:
        raise
    except OSError as exc:
        raise CatalogError(f"migration source is not readable: {path}: {exc}") from exc
    try:
        bound = os.fstat(fd)
        current = resolved.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(bound.st_mode)
            or not stat.S_ISREG(current.st_mode)
            or (bound.st_dev, bound.st_ino) != (current.st_dev, current.st_ino)
            or (original.st_dev, original.st_ino) != (bound.st_dev, bound.st_ino)
        ):
            raise CatalogError(f"migration source changed while being validated: {path}")
        data = _read_all(fd)
        return _BoundMigrationSource(resolved, fd, bound, data)
    except Exception:
        os.close(fd)
        raise


def _parse_bound_catalog(source: _BoundMigrationSource):  # noqa: ANN202 - CatalogDocument is internal.
    try:
        payload = json.loads(
            source.data.decode("utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
        )
        return parse_catalog(payload)
    except (UnicodeError, json.JSONDecodeError, ValueError, CatalogError) as exc:
        raise CatalogError(
            f"catalog {source.path}: invalid local state ({exc}); repair or restore the file before retrying"
        ) from exc


def _run_migrate_local(args: argparse.Namespace) -> int:
    region = _resolved_region(args)
    source: _BoundMigrationSource | None = None
    try:
        source = _open_migration_source(args.source)
        document = _parse_bound_catalog(source)
        source.revalidate()
        if any(card.region != region for card in document.cards):
            raise CatalogError("every migration card region must equal the resolved region")
        client = REMOTE_CATALOG_CLIENT_FACTORY(api_key=_credentials(), region=region)
        compatibility = _compatibility(region)
        observed = read_remote_migration_snapshot(
            client, region=region, compatibility=compatibility
        )
        live_targets = set(observed.live_namespace_ids) - {REMOTE_CATALOG_NAMESPACE}
        missing_live = sorted(card.namespace for card in document.cards if card.namespace not in live_targets)
        if missing_live:
            raise RemoteCatalogError(f"migration targets are not live: {missing_live}")
        state = classify_migration_state(
            catalog_exists=observed.catalog_exists,
            existing_cards=observed.cards,
            intended_cards=document.cards,
        )
        if state.state == "conflict":
            raise RemoteCatalogError(state.reason or "remote migration state conflicts")
        intended_missing_targets = [card.namespace for card in state.missing_cards]
        intended_cards = [
            {
                "namespace": card.namespace,
                "remote_card_id": remote_card_id(card.namespace),
                "card_revision": card.card_revision,
            }
            for card in document.cards
        ]
        observed_classification = classify_remote_catalog(
            live_namespace_ids=observed.live_namespace_ids,
            cards=observed.cards,
            compatibility=compatibility,
            metrics=observed.metrics,
        )
        affected_ids: list[str] = []
        mutation: MutationResult | None = None
        if args.approve:
            source.revalidate()
            if state.missing_cards:
                mutation = create_remote_cards(
                    client.namespace(REMOTE_CATALOG_NAMESPACE), state.missing_cards, region=region
                )
                affected_ids = list(mutation.affected_ids)
        final = (
            read_remote_catalog(client, region=region, compatibility=compatibility)
            if args.approve
            else None
        )
        if final is not None:
            final_state = classify_migration_state(
                catalog_exists=True, existing_cards=final.cards, intended_cards=document.cards
            )
            if final_state.state != "exact":
                raise RemoteCatalogError("approved migration did not produce the exact intended remote card set")
        reads = (observed.metrics, final.metrics) if final else (observed.metrics,)
        request_summary = _request_summary(reads, (mutation,) if mutation else ())
        payload = {
            "command": "catalog migrate-local",
            "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
            "region": region,
            "source": str(source.path),
            "source_catalog_revision": document.catalog_revision,
            "approved": args.approve,
            "initial_migration_state": state.state,
            "migration_state": "exact" if final else state.state,
            "intended_cards": intended_cards,
            "intended_targets": [card.namespace for card in document.cards],
            "intended_missing_targets": intended_missing_targets,
            "affected_ids": affected_ids,
            "source_untouched": True,
            "snapshot_revision": final.snapshot_revision if final else observed.snapshot_revision,
            "counts": asdict(final.counts if final else observed_classification.counts),
            "classifications": {
                "missing_card_ids": list((final or observed_classification).missing_card_ids),
                "stale_target_ids": list((final or observed_classification).stale_target_ids),
                "disabled_ids": list((final or observed_classification).disabled_ids),
                "incompatible_ids": list((final or observed_classification).incompatible_ids),
                "eligible_ids": [card.namespace for card in (final or observed_classification).eligible_cards],
            },
            "final_cards": [
                {
                    "namespace": card.namespace,
                    "remote_card_id": remote_card_id(card.namespace),
                    "card_revision": card.card_revision,
                }
                for card in final.cards
            ] if final else [],
            "read_metrics": {
                "namespace_list_pages": sum(item.namespace_list_pages for item in reads),
                "metadata_requests": sum(item.metadata_requests for item in reads),
                "card_query_pages": sum(item.card_query_pages for item in reads),
                "billing": [bill for item in reads for bill in item.billing],
            },
            "request_summary": request_summary,
        }
    except (RemoteCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    finally:
        if source is not None:
            source.close()
    _emit(payload, json_output=args.json, text_lines=[
        f"Remote migration {payload['migration_state']}: {len(document.cards)} intended card(s).",
        f"{'Approved write complete' if args.approve else 'Preview only; zero writes'}; source remains untouched: {payload['source']}",
    ])
    return 0


def _run_reconcile(args: argparse.Namespace) -> int:
    if (args.rebase or args.accept_remote) and not args.approve:
        print("--rebase and --accept-remote require --approve", file=sys.stderr)
        return 2
    if args.accept_remote and not args.expected_remote_revision:
        print("--accept-remote requires --expected-remote-revision", file=sys.stderr)
        return 2
    if args.expected_remote_revision and not args.accept_remote:
        print("--expected-remote-revision is valid only with --accept-remote", file=sys.stderr)
        return 2
    region = _resolved_region(args)
    try:
        client = REMOTE_CATALOG_CLIENT_FACTORY(api_key=_credentials(), region=region)
        action = "accept_remote" if args.accept_remote else "rebase" if args.rebase else "ordinary"
        payload = reconcile_pending(
            args.pending,
            client=client,
            region=region,
            compatibility=_compatibility(region),
            action=action,
            expected_remote_revision=args.expected_remote_revision,
            embedder=load_routing_embedder() if args.rebase else None,
        )
    except CatalogCommitPartialSuccess as exc:
        payload = exc.summary
        _emit(payload, json_output=args.json, text_lines=[
            f"Pending remote catalog action: {payload['action']} for {payload['namespace']}.",
            f"Verified card revision: {payload['card_revision']}.",
            "Full catalog snapshot or pending cleanup is incomplete; pending state was retained.",
            f"Recovery: {payload['catalog_repair_command']}",
        ])
        if not args.json:
            print(str(exc), file=sys.stderr)
        return 2
    except (PendingCatalogError, RemoteCatalogError, CatalogError, RuntimeError, OSError) as exc:
        return _remote_failure(exc)
    _emit(payload, json_output=args.json, text_lines=[
        f"Pending remote catalog action: {payload['action']} for {payload['namespace']}.",
        f"Verified card revision: {payload['card_revision']}.",
        f"Post-operation remote snapshot: {payload['snapshot_revision']}.",
        "Pending registration cleanup complete; content was not replayed.",
    ])
    return 0


def _run_abandon_pending(args: argparse.Namespace) -> int:
    try:
        payload = abandon_pending(args.pending, approve=args.approve)
    except (PendingCatalogError, CatalogError, OSError) as exc:
        return _remote_failure(exc)
    _emit(payload, json_output=args.json, text_lines=[
        f"{'Abandoned' if args.approve else 'Preview: abandon'} unconfirmed pending registration {args.pending}.",
        str(payload["warning"]),
        "Remote state: not read; no stable snapshot is claimed.",
        "No credentials were read and no remote service was contacted.",
    ])
    return 0
