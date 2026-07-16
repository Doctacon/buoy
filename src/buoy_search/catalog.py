"""Canonical local namespace catalog and pinned routing-card projection.

This module is local-only: it never reads credentials or imports turbopuffer.
Model construction is isolated behind ``load_routing_embedder`` and always uses
an exact cached revision with downloads disabled.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import ipaddress
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Protocol, Sequence
import unicodedata
from urllib.parse import urlsplit

import portalocker

from buoy_search.applied_state import AppliedStateError, resolve_state_root
from buoy_search.plan_artifacts import PLAN_SCHEMA_VERSION, stable_hash, stable_json_dumps
from buoy_search.retriever import RANKING_AGGREGATIONS, RANKING_MODES, RANKING_PROFILES

CATALOG_SCHEMA_VERSION = 1
CATALOG_ENV = "BUOY_CATALOG_PATH"
ROUTING_MODEL = "BAAI/bge-small-en-v1.5"
ROUTING_MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
ROUTING_PRECISION = "float32"
ROUTING_DIMENSIONS = 384
ROUTING_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
ROUTING_CONTRACT: dict[str, object] = {
    "dimensions": ROUTING_DIMENSIONS,
    "model": ROUTING_MODEL,
    "normalized": True,
    "precision": ROUTING_PRECISION,
    "revision": ROUTING_MODEL_REVISION,
}
SOURCE_KINDS = {"github_repo", "website", "document"}
SEMANTIC_ORIGINS = {"generated", "manual"}
EMBEDDING_PRECISIONS = {"float32", "float16"}
CARD_FIELDS = {
    "namespace", "enabled", "created_at", "updated_at", "card_revision",
    "last_plan_id", "last_apply_id", "source_kind", "source_uri", "site_id",
    "title", "summary", "aliases", "tags", "semantic_origin", "region",
    "embedding_model", "embedding_precision", "vector_dimensions",
    "plan_schema_version", "ranking_mode", "ranking_profile", "ranking_pool",
    "ranking_aggregation", "routing_model", "routing_model_revision",
    "semantic_hash", "vector", "vector_hash",
}
DOCUMENT_FIELDS = {"schema_version", "catalog_revision", "updated_at", "cards"}


class CatalogError(ValueError):
    """Raised when local catalog state or a requested mutation is invalid."""


class RoutingEmbedder(Protocol):
    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        """Return normalized routing vectors for passage texts."""


@dataclass(frozen=True)
class NamespaceCard:
    namespace: str
    enabled: bool
    created_at: str
    updated_at: str
    card_revision: str
    last_plan_id: str | None
    last_apply_id: str | None
    source_kind: str
    source_uri: str
    site_id: str
    title: str
    summary: str
    aliases: list[str]
    tags: list[str]
    semantic_origin: str
    region: str
    embedding_model: str
    embedding_precision: str
    vector_dimensions: int
    plan_schema_version: int
    ranking_mode: str
    ranking_profile: str
    ranking_pool: int
    ranking_aggregation: str
    routing_model: str
    routing_model_revision: str
    semantic_hash: str
    vector: list[float]
    vector_hash: str


@dataclass(frozen=True)
class CatalogDocument:
    schema_version: int
    catalog_revision: str
    updated_at: str
    cards: list[NamespaceCard]


@dataclass(frozen=True)
class GeneratedSemantics:
    source_kind: str
    source_uri: str
    title: str
    summary: str
    aliases: list[str]
    tags: list[str]


@dataclass(frozen=True)
class CardFields:
    """Validated non-projection inputs shared by manual upsert and later apply."""

    namespace: str
    enabled: bool
    source_kind: str
    source_uri: str
    site_id: str
    title: str
    summary: str
    aliases: list[str]
    tags: list[str]
    semantic_origin: str
    region: str
    embedding_model: str
    embedding_precision: str
    plan_schema_version: int
    ranking_mode: str
    ranking_profile: str
    ranking_pool: int
    ranking_aggregation: str
    last_plan_id: str | None = None
    last_apply_id: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE)
    return " ".join(normalized.split())


def normalize_semantic_values(values: Iterable[str], *, field: str) -> list[str]:
    cleaned: list[str] = []
    seen: dict[str, str] = {}
    for value in values:
        if not isinstance(value, str) or not value.strip():
            raise CatalogError(f"{field} entries must be non-empty strings")
        item = value.strip()
        key = canonical_text(item)
        if not key:
            raise CatalogError(f"{field} entry {value!r} has no alphanumeric content")
        if key in seen:
            raise CatalogError(f"{field} contains duplicate normalized values {seen[key]!r} and {item!r}")
        seen[key] = item
        cleaned.append(item)
    return sorted(cleaned)


def card_passage_text(*, title: str, summary: str, aliases: Sequence[str], tags: Sequence[str]) -> str:
    return (
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Aliases: {'; '.join(sorted(aliases)) if aliases else 'none'}\n"
        f"Tags: {'; '.join(sorted(tags)) if tags else 'none'}"
    )


def semantic_hash_for_fields(*, title: str, summary: str, aliases: Sequence[str], tags: Sequence[str]) -> str:
    return stable_hash(
        {
            "passage_text": card_passage_text(
                title=title, summary=summary, aliases=aliases, tags=tags
            ),
            "routing_contract": ROUTING_CONTRACT,
        }
    )


def vector_hash(vector: Sequence[float]) -> str:
    return stable_hash(list(vector))


def catalog_revision(cards: Sequence[NamespaceCard]) -> str:
    return stable_hash([card_to_dict(card, include_vector=True) for card in sorted(cards, key=lambda item: item.namespace)])


def card_revision(card: NamespaceCard) -> str:
    payload = card_to_dict(card, include_vector=True)
    for key in ("created_at", "updated_at", "card_revision"):
        payload.pop(key)
    return stable_hash(payload)


def card_to_dict(card: NamespaceCard, *, include_vector: bool = False) -> dict[str, object]:
    payload = asdict(card)
    if not include_vector:
        payload.pop("vector")
    return payload


def document_to_dict(document: CatalogDocument) -> dict[str, object]:
    return {
        "schema_version": document.schema_version,
        "catalog_revision": document.catalog_revision,
        "updated_at": document.updated_at,
        "cards": [card_to_dict(card, include_vector=True) for card in document.cards],
    }


def empty_catalog(*, now: str | None = None) -> CatalogDocument:
    return CatalogDocument(
        schema_version=CATALOG_SCHEMA_VERSION,
        catalog_revision=stable_hash([]),
        updated_at=now or utc_now(),
        cards=[],
    )


def resolve_catalog_path(
    explicit_catalog: str | Path | None,
    *,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path, str | None]:
    """Resolve CLI, environment, then implicit state-root catalog precedence."""

    if explicit_catalog is not None:
        value = str(explicit_catalog)
        if not value.strip():
            raise CatalogError("--catalog must contain a non-whitespace path")
        return Path(value).expanduser(), None
    environment = os.environ if environ is None else environ
    if CATALOG_ENV in environment:
        value = environment[CATALOG_ENV]
        if not value.strip():
            raise CatalogError(f"{CATALOG_ENV} must contain a non-whitespace path")
        return Path(value).expanduser(), None
    try:
        state_root, warning = resolve_state_root(None)
    except AppliedStateError as exc:
        message = str(exc)
        if "both implicit state roots exist" in message:
            raise CatalogError(
                "both implicit state roots exist: .buoy and .turbo-search; "
                "pass --catalog PATH to choose the local catalog"
            ) from exc
        raise CatalogError(message) from exc
    return state_root / "catalog.json", warning


def _require_exact_fields(payload: Mapping[str, object], expected: set[str], *, label: str) -> None:
    unknown = sorted(set(payload) - expected)
    missing = sorted(expected - set(payload))
    if unknown:
        raise CatalogError(f"{label} has unknown field(s): {', '.join(unknown)}")
    if missing:
        raise CatalogError(f"{label} is missing field(s): {', '.join(missing)}")


def _require_string(value: object, *, field: str, namespace: str | None = None) -> str:
    if not isinstance(value, str) or not value.strip():
        prefix = f"namespace {namespace!r} " if namespace else ""
        raise CatalogError(f"{prefix}field {field} must be a non-empty string")
    return value


def _require_optional_id(value: object, *, field: str, namespace: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field=field, namespace=namespace)


def _require_exact_int(
    value: object,
    *,
    field: str,
    namespace: str | None = None,
    expected: int | None = None,
    positive: bool = False,
) -> int:
    prefix = f"namespace {namespace!r} " if namespace else "catalog "
    if type(value) is not int:
        raise CatalogError(f"{prefix}field {field} must be a JSON integer")
    if expected is not None and value != expected:
        raise CatalogError(f"{prefix}field {field} must equal {expected}")
    if positive and value <= 0:
        raise CatalogError(f"{prefix}field {field} must be a positive integer")
    return value


def _validate_lineage(
    *,
    semantic_origin: str,
    last_plan_id: object,
    last_apply_id: object,
    namespace: str,
    persisted: bool,
) -> tuple[str | None, str | None]:
    plan_id = _require_optional_id(last_plan_id, field="last_plan_id", namespace=namespace)
    apply_id = _require_optional_id(last_apply_id, field="last_apply_id", namespace=namespace)
    if apply_id is not None and plan_id is None:
        raise CatalogError(
            f"namespace {namespace!r} field last_apply_id requires non-empty last_plan_id"
        )
    if not persisted:
        if plan_id is None or apply_id is not None:
            raise CatalogError(
                f"namespace {namespace!r} prospective card requires last_plan_id and no last_apply_id"
            )
        return plan_id, apply_id
    if semantic_origin == "generated" and (plan_id is None or apply_id is None):
        raise CatalogError(
            f"namespace {namespace!r} generated card requires non-empty last_plan_id and last_apply_id"
        )
    if semantic_origin == "manual" and ((plan_id is None) != (apply_id is None)):
        raise CatalogError(
            f"namespace {namespace!r} manual card lineage must have both IDs null or both non-empty"
        )
    return plan_id, apply_id


def _validate_utc(value: object, *, field: str, namespace: str | None = None) -> str:
    text = _require_string(value, field=field, namespace=namespace)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CatalogError(f"field {field} must be a UTC ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CatalogError(f"field {field} must be a UTC ISO-8601 timestamp")
    return text


def _validate_http_hostname(hostname: str, *, namespace: str) -> None:
    try:
        ipaddress.ip_address(hostname)
        return
    except ValueError:
        pass
    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CatalogError(f"namespace {namespace!r} field source_uri has a malformed hostname") from exc
    labels = ascii_hostname.split(".")
    if any(
        not label
        or len(label) > 63
        or label.startswith("-")
        or label.endswith("-")
        or re.fullmatch(r"[A-Za-z0-9-]+", label) is None
        for label in labels
    ):
        raise CatalogError(f"namespace {namespace!r} field source_uri has a malformed hostname")


def _validate_source_uri(
    value: object,
    *,
    namespace: str,
    source_kind: str | None = None,
) -> str:
    uri = _require_string(value, field="source_uri", namespace=namespace)
    if uri != uri.strip() or any(character.isspace() for character in uri):
        raise CatalogError(f"namespace {namespace!r} field source_uri must not contain whitespace")
    try:
        parsed = urlsplit(uri)
        port = parsed.port
    except ValueError as exc:
        raise CatalogError(f"namespace {namespace!r} field source_uri is malformed: {exc}") from exc
    if parsed.scheme in {"http", "https"}:
        if not parsed.hostname or not parsed.netloc or parsed.username is not None or parsed.password is not None:
            raise CatalogError(f"namespace {namespace!r} field source_uri must contain a valid HTTP(S) host")
        if port is not None and port == 0:
            raise CatalogError(f"namespace {namespace!r} field source_uri has an invalid port")
        _validate_http_hostname(parsed.hostname, namespace=namespace)
        return uri
    if parsed.scheme == "file" and source_kind in {None, "document"}:
        if (
            not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or re.fullmatch(r"[A-Za-z0-9._~-]+", parsed.netloc) is None
        ):
            raise CatalogError(
                f"namespace {namespace!r} field source_uri must be a supported file://<source-id> URI"
            )
        return uri
    allowed = "HTTP(S)" if source_kind in {"website", "github_repo"} else "HTTP(S) or file"
    raise CatalogError(
        f"namespace {namespace!r} field source_uri uses unsupported scheme {parsed.scheme!r}; "
        f"{source_kind or 'generated source'} requires {allowed}"
    )


def validate_vector(value: object, *, namespace: str) -> list[float]:
    if not isinstance(value, list) or len(value) != ROUTING_DIMENSIONS:
        raise CatalogError(
            f"namespace {namespace!r} field vector must contain exactly {ROUTING_DIMENSIONS} numbers"
        )
    vector: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise CatalogError(f"namespace {namespace!r} field vector[{index}] must be a finite JSON number")
        number = float(item)
        if not math.isfinite(number):
            raise CatalogError(f"namespace {namespace!r} field vector[{index}] must be a finite JSON number")
        vector.append(item)
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0.0 or abs(norm - 1.0) > 1e-4:
        raise CatalogError(f"namespace {namespace!r} field vector must be normalized and non-zero")
    return vector


def parse_card(payload: object) -> NamespaceCard:
    return _parse_card(payload, persisted=True)


def _parse_card(payload: object, *, persisted: bool) -> NamespaceCard:
    if not isinstance(payload, dict):
        raise CatalogError("catalog cards entries must be JSON objects")
    _require_exact_fields(payload, CARD_FIELDS, label="catalog card")
    namespace = _require_string(payload["namespace"], field="namespace")
    aliases_raw = payload["aliases"]
    tags_raw = payload["tags"]
    if not isinstance(aliases_raw, list) or not isinstance(tags_raw, list):
        raise CatalogError(f"namespace {namespace!r} aliases and tags must be arrays")
    aliases = normalize_semantic_values(aliases_raw, field="aliases")
    tags = normalize_semantic_values(tags_raw, field="tags")
    if aliases != aliases_raw:
        raise CatalogError(f"namespace {namespace!r} field aliases must be sorted and canonical")
    if tags != tags_raw:
        raise CatalogError(f"namespace {namespace!r} field tags must be sorted and canonical")
    title = _require_string(payload["title"], field="title", namespace=namespace)
    if canonical_text(title) in {canonical_text(alias) for alias in aliases}:
        raise CatalogError(f"namespace {namespace!r} field aliases must not contain the normalized title")
    source_kind = _require_string(payload["source_kind"], field="source_kind", namespace=namespace)
    semantic_origin = _require_string(payload["semantic_origin"], field="semantic_origin", namespace=namespace)
    embedding_precision = str(payload["embedding_precision"])
    ranking_mode = str(payload["ranking_mode"])
    ranking_profile = str(payload["ranking_profile"])
    ranking_aggregation = str(payload["ranking_aggregation"])
    if source_kind not in SOURCE_KINDS:
        raise CatalogError(f"namespace {namespace!r} field source_kind is unsupported: {source_kind!r}")
    if semantic_origin not in SEMANTIC_ORIGINS:
        raise CatalogError(f"namespace {namespace!r} field semantic_origin is unsupported: {semantic_origin!r}")
    if embedding_precision not in EMBEDDING_PRECISIONS:
        raise CatalogError(f"namespace {namespace!r} field embedding_precision is unsupported")
    if ranking_mode not in RANKING_MODES or ranking_profile not in RANKING_PROFILES or ranking_aggregation not in RANKING_AGGREGATIONS:
        raise CatalogError(f"namespace {namespace!r} has an unsupported ranking contract")
    enabled = payload["enabled"]
    if not isinstance(enabled, bool):
        raise CatalogError(f"namespace {namespace!r} field enabled must be a boolean")
    dimensions = _require_exact_int(
        payload["vector_dimensions"],
        field="vector_dimensions",
        namespace=namespace,
        expected=ROUTING_DIMENSIONS,
    )
    plan_schema = _require_exact_int(
        payload["plan_schema_version"],
        field="plan_schema_version",
        namespace=namespace,
        expected=PLAN_SCHEMA_VERSION,
    )
    ranking_pool = _require_exact_int(
        payload["ranking_pool"], field="ranking_pool", namespace=namespace, positive=True
    )
    if payload["routing_model"] != ROUTING_MODEL or payload["routing_model_revision"] != ROUTING_MODEL_REVISION:
        raise CatalogError(f"namespace {namespace!r} has an incompatible routing model contract")
    vector = validate_vector(payload["vector"], namespace=namespace)
    expected_semantic_hash = semantic_hash_for_fields(
        title=title,
        summary=_require_string(payload["summary"], field="summary", namespace=namespace),
        aliases=aliases,
        tags=tags,
    )
    if payload["semantic_hash"] != expected_semantic_hash:
        raise CatalogError(f"namespace {namespace!r} field semantic_hash is stale or invalid")
    if payload["vector_hash"] != vector_hash(vector):
        raise CatalogError(f"namespace {namespace!r} field vector_hash is stale or invalid")
    last_plan_id, last_apply_id = _validate_lineage(
        semantic_origin=semantic_origin,
        last_plan_id=payload["last_plan_id"],
        last_apply_id=payload["last_apply_id"],
        namespace=namespace,
        persisted=persisted,
    )
    card = NamespaceCard(
        namespace=namespace,
        enabled=enabled,
        created_at=_validate_utc(payload["created_at"], field="created_at", namespace=namespace),
        updated_at=_validate_utc(payload["updated_at"], field="updated_at", namespace=namespace),
        card_revision=_require_string(payload["card_revision"], field="card_revision", namespace=namespace),
        last_plan_id=last_plan_id,
        last_apply_id=last_apply_id,
        source_kind=source_kind,
        source_uri=_validate_source_uri(
            payload["source_uri"], namespace=namespace, source_kind=source_kind
        ),
        site_id=_require_string(payload["site_id"], field="site_id", namespace=namespace),
        title=title,
        summary=str(payload["summary"]),
        aliases=aliases,
        tags=tags,
        semantic_origin=semantic_origin,
        region=_require_string(payload["region"], field="region", namespace=namespace),
        embedding_model=_require_string(payload["embedding_model"], field="embedding_model", namespace=namespace),
        embedding_precision=embedding_precision,
        vector_dimensions=dimensions,
        plan_schema_version=plan_schema,
        ranking_mode=ranking_mode,
        ranking_profile=ranking_profile,
        ranking_pool=ranking_pool,
        ranking_aggregation=ranking_aggregation,
        routing_model=ROUTING_MODEL,
        routing_model_revision=ROUTING_MODEL_REVISION,
        semantic_hash=str(payload["semantic_hash"]),
        vector=vector,
        vector_hash=str(payload["vector_hash"]),
    )
    if card.card_revision != card_revision(card):
        raise CatalogError(f"namespace {namespace!r} field card_revision is stale or invalid")
    return card


def parse_catalog(payload: object) -> CatalogDocument:
    if not isinstance(payload, dict):
        raise CatalogError("catalog document must be a JSON object")
    _require_exact_fields(payload, DOCUMENT_FIELDS, label="catalog document")
    _require_exact_int(
        payload["schema_version"], field="schema_version", expected=CATALOG_SCHEMA_VERSION
    )
    cards_raw = payload["cards"]
    if not isinstance(cards_raw, list):
        raise CatalogError("catalog field cards must be an array")
    cards = [parse_card(item) for item in cards_raw]
    namespaces = [card.namespace for card in cards]
    if namespaces != sorted(namespaces):
        raise CatalogError("catalog cards must be sorted by namespace")
    if len(namespaces) != len(set(namespaces)):
        raise CatalogError("catalog contains a duplicate namespace")
    revision = _require_string(payload["catalog_revision"], field="catalog_revision")
    if revision != catalog_revision(cards):
        raise CatalogError("catalog field catalog_revision is stale or invalid")
    return CatalogDocument(
        schema_version=CATALOG_SCHEMA_VERSION,
        catalog_revision=revision,
        updated_at=_validate_utc(payload["updated_at"], field="updated_at"),
        cards=cards,
    )


def load_catalog(path: Path) -> CatalogDocument:
    if not path.exists():
        return empty_catalog()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        return parse_catalog(payload)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError, CatalogError) as exc:
        raise CatalogError(
            f"catalog {path}: invalid local state ({exc}); repair or restore the file before retrying"
        ) from exc


@contextmanager
def catalog_lock(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(f"{path.name}.lock")
    try:
        with portalocker.Lock(str(lock_path), mode="a+", timeout=0, fail_when_locked=True):
            yield
    except portalocker.exceptions.LockException as exc:
        raise CatalogError(f"catalog {path}: another catalog mutation is in progress; retry after it finishes") from exc


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError:
            pass
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def save_catalog(path: Path, cards: Sequence[NamespaceCard], *, now: str | None = None) -> CatalogDocument:
    ordered = sorted(cards, key=lambda item: item.namespace)
    namespaces = [card.namespace for card in ordered]
    if len(namespaces) != len(set(namespaces)):
        raise CatalogError(f"catalog {path}: cannot save duplicate namespaces")
    for card in ordered:
        parse_card(card_to_dict(card, include_vector=True))
    document = CatalogDocument(
        schema_version=CATALOG_SCHEMA_VERSION,
        catalog_revision=catalog_revision(ordered),
        updated_at=now or utc_now(),
        cards=list(ordered),
    )
    data = (stable_json_dumps(document_to_dict(document), indent=2) + "\n").encode("utf-8")
    try:
        _atomic_write(path, data)
    except OSError as exc:
        raise CatalogError(f"catalog {path}: atomic save failed: {exc}") from exc
    return document


class _SentenceTransformerRoutingEmbedder:
    def __init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover
            raise CatalogError("sentence-transformers is required for catalog vectors; run `uv sync` first") from exc
        try:
            self._model = SentenceTransformer(
                ROUTING_MODEL,
                revision=ROUTING_MODEL_REVISION,
                local_files_only=True,
            )
        except Exception as exc:
            raise CatalogError(
                f"pinned routing model {ROUTING_MODEL}@{ROUTING_MODEL_REVISION} is not cached locally; "
                "cache that exact revision explicitly and retry (downloads and substitutions are disabled)"
            ) from exc

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        values = self._model.encode(
            list(texts), normalize_embeddings=True, show_progress_bar=False
        )
        return [value.tolist() if hasattr(value, "tolist") else list(value) for value in values]


def load_routing_embedder() -> RoutingEmbedder:
    return _SentenceTransformerRoutingEmbedder()


def validate_card_fields(fields: CardFields, *, persisted: bool = True) -> CardFields:
    namespace = _require_string(fields.namespace, field="namespace")
    if not isinstance(fields.enabled, bool):
        raise CatalogError(f"namespace {namespace!r} field enabled must be a boolean")
    if fields.source_kind not in SOURCE_KINDS:
        raise CatalogError(f"namespace {namespace!r} field source_kind is unsupported")
    _validate_source_uri(fields.source_uri, namespace=namespace, source_kind=fields.source_kind)
    _require_string(fields.site_id, field="site_id", namespace=namespace)
    title = _require_string(fields.title, field="title", namespace=namespace).strip()
    summary = _require_string(fields.summary, field="summary", namespace=namespace).strip()
    aliases = normalize_semantic_values(fields.aliases, field="aliases")
    tags = normalize_semantic_values(fields.tags, field="tags")
    if canonical_text(title) in {canonical_text(alias) for alias in aliases}:
        raise CatalogError(f"namespace {namespace!r} field aliases must not contain the normalized title")
    if fields.semantic_origin not in SEMANTIC_ORIGINS:
        raise CatalogError(f"namespace {namespace!r} field semantic_origin is unsupported")
    _require_string(fields.region, field="region", namespace=namespace)
    _require_string(fields.embedding_model, field="embedding_model", namespace=namespace)
    if fields.embedding_precision not in EMBEDDING_PRECISIONS:
        raise CatalogError(f"namespace {namespace!r} field embedding_precision is unsupported")
    _require_exact_int(
        fields.plan_schema_version,
        field="plan_schema_version",
        namespace=namespace,
        expected=PLAN_SCHEMA_VERSION,
    )
    if fields.ranking_mode not in RANKING_MODES or fields.ranking_profile not in RANKING_PROFILES or fields.ranking_aggregation not in RANKING_AGGREGATIONS:
        raise CatalogError(f"namespace {namespace!r} has an unsupported ranking contract")
    _require_exact_int(
        fields.ranking_pool, field="ranking_pool", namespace=namespace, positive=True
    )
    _validate_lineage(
        semantic_origin=fields.semantic_origin,
        last_plan_id=fields.last_plan_id,
        last_apply_id=fields.last_apply_id,
        namespace=namespace,
        persisted=persisted,
    )
    return replace(fields, namespace=namespace, title=title, summary=summary, aliases=aliases, tags=tags)


def prepare_card(
    fields: CardFields,
    *,
    existing: NamespaceCard | None = None,
    embedder: RoutingEmbedder | None = None,
    now: str | None = None,
) -> NamespaceCard:
    """Build a persisted card, reusing a compatible unchanged projection."""

    return _prepare_card(
        fields, existing=existing, embedder=embedder, now=now, persisted=True
    )


def prepare_prospective_card(
    fields: CardFields,
    *,
    existing: NamespaceCard | None = None,
    embedder: RoutingEmbedder | None = None,
    now: str | None = None,
) -> NamespaceCard:
    """Build non-persistable apply-precompute data with plan but no apply ID."""

    return _prepare_card(
        fields, existing=existing, embedder=embedder, now=now, persisted=False
    )


def _prepare_card(
    fields: CardFields,
    *,
    existing: NamespaceCard | None,
    embedder: RoutingEmbedder | None,
    now: str | None,
    persisted: bool,
) -> NamespaceCard:
    fields = validate_card_fields(fields, persisted=persisted)
    timestamp = now or utc_now()
    semantic_hash = semantic_hash_for_fields(
        title=fields.title, summary=fields.summary, aliases=fields.aliases, tags=fields.tags
    )
    if (
        existing is not None
        and existing.semantic_hash == semantic_hash
        and existing.routing_model == ROUTING_MODEL
        and existing.routing_model_revision == ROUTING_MODEL_REVISION
    ):
        vector = list(existing.vector)
    else:
        passage = card_passage_text(
            title=fields.title, summary=fields.summary, aliases=fields.aliases, tags=fields.tags
        )
        try:
            encoder = embedder or load_routing_embedder()
            encoded = encoder.encode([passage])
        except CatalogError:
            raise
        except Exception as exc:
            raise CatalogError(f"namespace {fields.namespace!r}: routing model failed: {exc}") from exc
        if len(encoded) != 1:
            raise CatalogError(f"namespace {fields.namespace!r}: routing model must return exactly one vector")
        vector = validate_vector(encoded[0], namespace=fields.namespace)
    provisional = NamespaceCard(
        namespace=fields.namespace,
        enabled=fields.enabled,
        created_at=existing.created_at if existing else timestamp,
        updated_at=timestamp,
        card_revision="pending",
        last_plan_id=fields.last_plan_id,
        last_apply_id=fields.last_apply_id,
        source_kind=fields.source_kind,
        source_uri=fields.source_uri,
        site_id=fields.site_id,
        title=fields.title,
        summary=fields.summary,
        aliases=list(fields.aliases),
        tags=list(fields.tags),
        semantic_origin=fields.semantic_origin,
        region=fields.region,
        embedding_model=fields.embedding_model,
        embedding_precision=fields.embedding_precision,
        vector_dimensions=ROUTING_DIMENSIONS,
        plan_schema_version=PLAN_SCHEMA_VERSION,
        ranking_mode=fields.ranking_mode,
        ranking_profile=fields.ranking_profile,
        ranking_pool=fields.ranking_pool,
        ranking_aggregation=fields.ranking_aggregation,
        routing_model=ROUTING_MODEL,
        routing_model_revision=ROUTING_MODEL_REVISION,
        semantic_hash=semantic_hash,
        vector=vector,
        vector_hash=vector_hash(vector),
    )
    card = replace(provisional, card_revision=card_revision(provisional))
    return _parse_card(card_to_dict(card, include_vector=True), persisted=persisted)


def merge_system_card(existing: NamespaceCard | None, incoming: NamespaceCard) -> NamespaceCard:
    """Merge one apply-prepared card while preserving manual semantics/enabled state."""

    incoming = parse_card(card_to_dict(incoming, include_vector=True))
    if existing is None:
        return incoming
    if existing.namespace != incoming.namespace:
        raise CatalogError("cannot merge cards with different namespaces")
    if existing.semantic_origin != "manual":
        merged = replace(incoming, created_at=existing.created_at)
    else:
        merged = replace(
            incoming,
            enabled=existing.enabled,
            created_at=existing.created_at,
            title=existing.title,
            summary=existing.summary,
            aliases=list(existing.aliases),
            tags=list(existing.tags),
            semantic_origin="manual",
            semantic_hash=existing.semantic_hash,
            vector=list(existing.vector),
            vector_hash=existing.vector_hash,
        )
    merged = replace(merged, card_revision="pending")
    merged = replace(merged, card_revision=card_revision(merged))
    return parse_card(card_to_dict(merged, include_vector=True))


def commit_system_card(
    path: Path,
    incoming: NamespaceCard,
) -> tuple[CatalogDocument, NamespaceCard, bool]:
    """Lock, revalidate, merge, and atomically commit one later-apply card."""

    with catalog_lock(path):
        document = load_catalog(path)
        existing = next((card for card in document.cards if card.namespace == incoming.namespace), None)
        merged = merge_system_card(existing, incoming)
        if existing is not None and existing.card_revision == merged.card_revision:
            return document, existing, False
        cards = [card for card in document.cards if card.namespace != merged.namespace] + [merged]
        return save_catalog(path, cards), merged, True


def mutate_catalog(path: Path, mutation: Any) -> tuple[CatalogDocument, Any]:
    """Apply one callback under the catalog lock and atomically save its card list."""

    with catalog_lock(path):
        current = load_catalog(path)
        cards, result, changed = mutation(current)
        if not changed:
            return current, result
        return save_catalog(path, cards), result


def _consistent_metadata(metadata: Sequence[Mapping[str, object]], key: str) -> str | None:
    values = {
        str(item[key]).strip()
        for item in metadata
        if key in item and isinstance(item[key], str) and str(item[key]).strip()
    }
    if len(values) > 1:
        raise CatalogError(f"verified source metadata has contradictory {key} values: {sorted(values)}")
    return next(iter(values), None)


def _github_identity(uri: str) -> tuple[str, str, str] | None:
    parsed = urlsplit(uri)
    parts = [part for part in parsed.path.split("/") if part]
    if (
        parsed.scheme != "https"
        or (parsed.hostname or "").lower() != "github.com"
        or parsed.netloc.lower() != "github.com"
        or parsed.query
        or parsed.fragment
        or len(parts) != 2
    ):
        return None
    return parts[0], parts[1], f"{parts[0]}/{parts[1]}"


def generated_semantics(
    *,
    base_url: str,
    site_id: str,
    plan_schema_version: int,
    source_metadata: Iterable[Mapping[str, object]],
) -> GeneratedSemantics:
    """Derive deterministic generated semantics from verified plan/source metadata."""

    _require_exact_int(
        plan_schema_version,
        field="plan_schema_version",
        namespace="generated-card",
        expected=PLAN_SCHEMA_VERSION,
    )
    uri = _validate_source_uri(base_url, namespace="generated-card")
    site = _require_string(site_id, field="site_id")
    metadata = list(source_metadata)
    for item in metadata:
        if "source_kind" in item and not isinstance(item["source_kind"], str):
            raise CatalogError("verified source metadata field source_kind must be a string")
    kinds = {
        str(item["source_kind"]).strip()
        for item in metadata
        if isinstance(item.get("source_kind"), str) and str(item["source_kind"]).strip()
    }
    if len(kinds) > 1:
        raise CatalogError(f"verified source metadata has contradictory source_kind values: {sorted(kinds)}")
    raw_kind = next(iter(kinds), None)
    if raw_kind not in {None, "github_repo", "pdf", "local_file"}:
        raise CatalogError(f"unsupported verified source_kind {raw_kind!r}")
    parsed = urlsplit(uri)
    github = _github_identity(uri)
    if raw_kind == "github_repo":
        if github is None:
            raise CatalogError("github_repo metadata contradicts the verified repository-root base_url")
        source_kind = "github_repo"
    elif raw_kind in {"pdf", "local_file"}:
        if parsed.scheme != "file":
            raise CatalogError(f"{raw_kind} metadata contradicts the verified non-file base_url")
        source_kind = "document"
    elif github is not None:
        source_kind = "github_repo"
    elif parsed.scheme in {"http", "https"} and parsed.hostname:
        source_kind = "website"
    elif parsed.scheme == "file" and (parsed.netloc or parsed.path.startswith("/")):
        source_kind = "document"
    else:
        raise CatalogError(f"unsupported verified source URI {uri!r}")

    if source_kind == "github_repo":
        assert github is not None
        metadata_name = _consistent_metadata(metadata, "repo_full_name")
        derived_name = github[2]
        if metadata_name is not None and metadata_name.casefold() != derived_name.casefold():
            raise CatalogError("repo_full_name metadata contradicts the verified repository-root base_url")
        full_name = metadata_name or derived_name
        title = full_name
        summary = f"Public GitHub repository {full_name} indexed from {uri}."
        aliases = normalize_semantic_values([full_name.split("/", 1)[1], full_name], field="aliases")
        aliases = [alias for alias in aliases if canonical_text(alias) != canonical_text(title)]
        tags = ["github", "repository"]
    elif source_kind == "website":
        hostname = (parsed.hostname or "").lower()
        title = hostname
        summary = f"Indexed knowledge source at {uri}."
        aliases = []
        tags = ["website"]
    else:
        filename: str | None = None
        if raw_kind == "pdf":
            filename = _consistent_metadata(metadata, "pdf_filename")
            if filename is None:
                raise CatalogError("pdf source metadata requires one consistent non-empty pdf_filename")
        elif raw_kind == "local_file":
            filename = _consistent_metadata(metadata, "file_filename")
            if filename is None:
                raise CatalogError("local_file source metadata requires one consistent non-empty file_filename")
        title = filename or site
        summary = f"Indexed document {title} from {uri}."
        aliases = []
        if filename:
            stem = Path(filename).stem.strip()
            if stem and canonical_text(stem) != canonical_text(title):
                aliases = [stem]
        tags = ["document"]
    return GeneratedSemantics(
        source_kind=source_kind,
        source_uri=uri,
        title=title,
        summary=summary,
        aliases=sorted(aliases),
        tags=sorted(tags),
    )
