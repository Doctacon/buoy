"""Import-safe schema-v3 plan document validation.

This module validates plan metadata and identity without importing acquisition,
database-relation, or local-source adapters. Full delta validation remains in
``plan_artifacts`` and reuses this exact document validator.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, unquote, urlsplit

from buoy_search.applied_state import APPLIED_STATE_SCHEMA_VERSION
from buoy_search.config import EMBEDDING_PRECISIONS
from buoy_search.source_url import validate_base_url, validate_http_url_authority

PLAN_SCHEMA_VERSION = 3
DELTA_SCHEMA_VERSION = 2
ROUTING_PROTOTYPE_STRATEGY = "diverse-content-passages-v1"
MAX_ROUTING_PROTOTYPES = 8

_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_PLAN_ID = re.compile(r"plan_[0-9a-f]{16}")
_MANAGED_JOB_ID = re.compile(r"planjob_[0-9a-f]{32}")
_SAFE_SITE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")
_SOURCE_KINDS = {
    "website",
    "github_repo",
    "local_file",
    "pdf",
    "duckdb_relation",
    "bigquery_relation",
    "snowflake_relation",
}
_DIFF_FIELDS = (
    "first_apply",
    "pages_added",
    "pages_changed",
    "pages_unchanged",
    "pages_removed",
    "chunks_unchanged",
    "chunks_to_embed",
    "rows_to_upsert",
    "stale_rows",
    "retained_stale_rows",
)
_MAX_PRIVACY_DEPTH = 16
_MAX_PRIVACY_NODES = 10_000
_MAX_PRIVACY_STRING_BYTES = 65_536
_MAX_URL_DECODE_ROUNDS = 5
_EMBEDDED_ABSOLUTE_URI = re.compile(
    r"(?i)(?<![A-Za-z0-9+.-])([a-z][a-z0-9+.-]{1,31}://[^\s<>\"'\\]+)"
)
_PUBLIC_URI_SCHEMES = frozenset({"http", "https"})
_SECRET_URI_COMPONENTS = {
    "token", "access_token", "api_key", "apikey", "key", "secret", "password",
    "passwd", "credential", "credentials", "authorization", "cookie", "profile",
    "connection", "connection_string", "connection_uri", "dsn", "account",
    "snowflake_account", "private",
}


def validate_plan_document(plan: object) -> None:
    """Validate the complete schema-v3 plan metadata contract and identity."""

    if not isinstance(plan, dict):
        raise ValueError("plan.json must be an object")
    required = {
        "schema_version", "command", "plan_id", "created_at", "artifact_hash",
        "source", "site_id", "namespace", "namespace_candidate", "crawl_options",
        "chunk_options", "embedding_model", "embedding_precision", "applied_state",
        "delta", "routing_prototypes", "diff",
    }
    allowed = required | {"originating_job_id"}
    if set(plan) != required and set(plan) != allowed:
        raise ValueError("plan.json fields do not match schema v3")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported plan schema version")
    if plan["command"] != "plan" or not _PLAN_ID.fullmatch(str(plan["plan_id"])):
        raise ValueError("invalid plan command or ID")
    if not _HEX_SHA256.fullmatch(str(plan["artifact_hash"])):
        raise ValueError("invalid artifact hash")
    for key in ("site_id", "namespace", "namespace_candidate", "created_at", "embedding_model"):
        if not isinstance(plan[key], str) or not plan[key] or plan[key] != plan[key].strip():
            raise ValueError(f"plan {key} must be a non-empty trimmed string")
    if _SAFE_SITE_ID.fullmatch(plan["site_id"]) is None:
        raise ValueError("plan site_id is unsafe")
    if any(
        re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", plan[key]) is None
        for key in ("namespace", "namespace_candidate")
    ):
        raise ValueError("plan namespace identity is unsafe")
    try:
        created = datetime.fromisoformat(plan["created_at"])
    except ValueError as exc:
        raise ValueError("plan created_at must be an ISO-8601 timestamp") from exc
    if created.tzinfo is None or created.utcoffset() != timezone.utc.utcoffset(created):
        raise ValueError("plan created_at must be a UTC timestamp")
    if plan["embedding_precision"] not in EMBEDDING_PRECISIONS:
        raise ValueError("invalid embedding precision")
    if not isinstance(plan["crawl_options"], dict) or not isinstance(plan["chunk_options"], dict):
        raise ValueError("plan options must be objects")
    _validate_private_free_json(plan["crawl_options"], label="crawl options")
    _validate_private_free_json(plan["chunk_options"], label="chunk options")
    validate_plan_source(plan["source"])
    expected_site_id, expected_namespace = _source_plan_identity(plan["source"])
    if plan["site_id"] != expected_site_id:
        raise ValueError("plan site_id does not match source identity")
    if plan["namespace_candidate"] != expected_namespace:
        raise ValueError("plan namespace_candidate does not match source identity")
    baseline = plan["applied_state"]
    if not isinstance(baseline, dict) or set(baseline) != {"present", "schema_version", "hash"}:
        raise ValueError("invalid applied-state descriptor")
    if (
        type(baseline["present"]) is not bool
        or type(baseline["schema_version"]) is not int
        or baseline["schema_version"] != APPLIED_STATE_SCHEMA_VERSION
    ):
        raise ValueError("invalid applied-state descriptor types or schema version")
    if not _HEX_SHA256.fullmatch(str(baseline["hash"])):
        raise ValueError("invalid applied-state hash")
    delta = plan["delta"]
    if not isinstance(delta, dict) or set(delta) != {
        "filename", "schema_version", "logical_hash", "upsert_count", "stale_count",
        "retained_stale_count",
    }:
        raise ValueError("invalid delta descriptor")
    if (
        delta["filename"] != "delta.duckdb"
        or type(delta["schema_version"]) is not int
        or delta["schema_version"] != DELTA_SCHEMA_VERSION
    ):
        raise ValueError("invalid delta descriptor identity")
    if not _HEX_SHA256.fullmatch(str(delta["logical_hash"])):
        raise ValueError("invalid delta logical hash")
    for key in ("upsert_count", "stale_count", "retained_stale_count"):
        if type(delta[key]) is not int or delta[key] < 0:
            raise ValueError("invalid delta count")
    routing_prototypes = plan["routing_prototypes"]
    if not isinstance(routing_prototypes, dict) or set(routing_prototypes) != {
        "strategy", "count", "logical_hash",
    }:
        raise ValueError("invalid routing prototype descriptor")
    if routing_prototypes["strategy"] != ROUTING_PROTOTYPE_STRATEGY:
        raise ValueError("invalid routing prototype strategy")
    if (
        type(routing_prototypes["count"]) is not int
        or routing_prototypes["count"] < 0
        or routing_prototypes["count"] > MAX_ROUTING_PROTOTYPES
    ):
        raise ValueError("invalid routing prototype count")
    if not _HEX_SHA256.fullmatch(str(routing_prototypes["logical_hash"])):
        raise ValueError("invalid routing prototype logical hash")
    normalize_diff(plan["diff"])
    _validate_diff_counts(plan["diff"], delta)
    if not baseline["present"] and not plan["diff"]["first_apply"]:
        raise ValueError("absent applied state requires first-apply diff semantics")
    artifact_hash = stable_hash(artifact_identity(plan))
    if artifact_hash != plan["artifact_hash"]:
        raise ValueError("plan artifact hash does not match")
    if plan["plan_id"] != f"plan_{artifact_hash[:16]}":
        raise ValueError("plan ID does not match artifact hash")
    if (
        "originating_job_id" in plan
        and _MANAGED_JOB_ID.fullmatch(str(plan["originating_job_id"])) is None
    ):
        raise ValueError("invalid originating job ID")


def validate_plan_source(source: object) -> None:
    if not isinstance(source, dict) or set(source) != {"kind", "uri", "title", "attributes"}:
        raise ValueError("invalid plan source object")
    kind = source["kind"]
    if kind not in _SOURCE_KINDS or not isinstance(source["uri"], str) or not source["uri"]:
        raise ValueError("invalid plan source identity")
    if (
        not isinstance(source["title"], str)
        or not source["title"]
        or source["title"] != source["title"].strip()
        or "\x00" in source["title"]
        or not isinstance(source["attributes"], dict)
    ):
        raise ValueError("invalid plan source presentation")
    attrs = source["attributes"]
    parsed_source = urlsplit(str(source["uri"]))
    if parsed_source.username is not None or parsed_source.password is not None:
        raise ValueError("plan source URI must not contain userinfo or credentials")
    _validate_private_string(
        str(source["uri"]),
        label="plan source URI",
        allowed_uri_schemes=_source_allowed_uri_schemes(str(kind)),
    )
    _validate_private_string(str(source["title"]), label="plan source title")
    expected = {
        "website": set(),
        "github_repo": {"repo_full_name", "repo_owner", "repo_name", "repo_ref", "commit_sha", "repo_subdir"},
        "local_file": {"filename", "extension", "sha256", "source_id"},
        "pdf": {"filename", "sha256", "source_id"},
        "duckdb_relation": {"database_backend", "database_source_id", "database_relation"},
        "bigquery_relation": {"database_backend", "database_source_id", "database_relation"},
        "snowflake_relation": {"database_backend", "database_source_id", "database_relation"},
    }[kind]
    if set(attrs) != expected:
        raise ValueError("plan source attributes do not match source kind")
    for key, value in attrs.items():
        if kind == "github_repo" and key == "repo_subdir" and value is None:
            continue
        if not isinstance(value, str) or not value:
            raise ValueError("plan source attributes must be non-empty strings")
        _validate_private_string(value, label="plan source attributes")
    _validate_private_free_json(attrs, label="source attributes")
    if parsed_source.scheme in {"http", "https"}:
        validate_http_url_authority(source["uri"])
    uri = validate_base_url(source["uri"])
    if source["uri"] != uri:
        raise ValueError("plan source URI does not equal canonical normalization")
    parsed = urlsplit(uri)
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("plan source URI must not contain credentials")
    if kind == "website":
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or source["title"] != parsed.hostname.lower()
        ):
            raise ValueError("website plan source requires consistent HTTP(S) authority")
    elif kind == "github_repo":
        parts = [part for part in parsed.path.split("/") if part]
        if (
            parsed.scheme != "https"
            or (parsed.hostname or "").lower() != "github.com"
            or parsed.netloc.lower() != "github.com"
            or parsed.query
            or parsed.fragment
            or len(parts) != 2
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(attrs["repo_owner"])) is None
            or re.fullmatch(r"[A-Za-z0-9_.-]+", str(attrs["repo_name"])) is None
            or f"{attrs['repo_owner']}/{attrs['repo_name']}" != attrs["repo_full_name"]
            or source["title"] != attrs["repo_full_name"]
            or [part.casefold() for part in parts]
            != [str(attrs["repo_owner"]).casefold(), str(attrs["repo_name"]).casefold()]
        ):
            raise ValueError("GitHub plan source identity is inconsistent")
        if attrs["repo_subdir"] is not None:
            _validate_relative_source_path(str(attrs["repo_subdir"]))
    elif kind in {"local_file", "pdf"}:
        expected_scheme = "file" if kind == "local_file" else "pdf"
        filename = str(attrs["filename"])
        _validate_safe_filename(filename)
        if kind == "local_file":
            expected_extension = Path(filename).suffix.removeprefix(".")
            if not expected_extension or str(attrs["extension"]).casefold() != expected_extension.casefold():
                raise ValueError("local-file extension contradicts its filename")
        elif Path(filename).suffix.casefold() != ".pdf":
            raise ValueError("PDF source filename must end in .pdf")
        if (
            source["title"] != filename
            or parsed.scheme != expected_scheme
            or not parsed.netloc
            or parsed.netloc != attrs["source_id"]
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("document plan source identity is inconsistent")
    else:
        backend = str(kind).removesuffix("_relation")
        source_id = str(attrs["database_source_id"])
        relation = str(attrs["database_relation"])
        relation_valid = {
            "duckdb": re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*(?:\.[A-Za-z_][A-Za-z0-9_-]*){0,2}", relation),
            "bigquery": re.fullmatch(r"[a-z][a-z0-9-]*\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*", relation),
            "snowflake": re.fullmatch(r"[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*\.[A-Z_][A-Z0-9_]*", relation),
        }[backend]
        if (
            attrs["database_backend"] != backend
            or parsed.scheme != backend
            or parsed.netloc != source_id
            or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id) is None
            or relation_valid is None
            or source["title"] != f"{source_id} ({relation})"
            or parsed.path
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("database plan source identity is inconsistent")


def _source_plan_identity(source: Mapping[str, object]) -> tuple[str, str]:
    kind = str(source["kind"])
    parsed = urlsplit(str(source["uri"]))
    attrs = source["attributes"]
    assert isinstance(attrs, dict)
    if kind == "website":
        source_id = _safe_slug(parsed.hostname or parsed.netloc, fallback="site")
    elif kind == "github_repo":
        source_id = _safe_slug(
            f"github-{attrs['repo_owner']}-{attrs['repo_name']}", fallback="github-repo"
        )
    elif kind in {"local_file", "pdf"}:
        source_id = _safe_slug(parsed.netloc, fallback="file" if kind == "local_file" else "pdf")
    else:
        source_id = f"{kind.removesuffix('_relation')}-{attrs['database_source_id']}"
    return source_id, f"{source_id}-v1" if kind != "website" else f"site-{source_id}-v1"


def _safe_slug(value: str, *, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or fallback


def normalize_diff(value: Mapping[str, object]) -> dict[str, object]:
    if set(value) != set(_DIFF_FIELDS):
        raise ValueError("diff summary fields do not match schema v3")
    result: dict[str, object] = {}
    for key in _DIFF_FIELDS:
        item = value[key]
        if key == "first_apply":
            if type(item) is not bool:
                raise ValueError("diff first_apply must be a boolean")
        elif type(item) is not int or item < 0:
            raise ValueError(f"diff {key} must be a non-negative integer")
        result[key] = item
    return result


def _validate_diff_counts(diff: Mapping[str, object], delta: Mapping[str, object]) -> None:
    if (
        diff["chunks_to_embed"] != delta["upsert_count"]
        or diff["rows_to_upsert"] != delta["upsert_count"]
        or diff["stale_rows"] != delta["stale_count"]
        or diff["retained_stale_rows"] != delta["retained_stale_count"]
    ):
        raise ValueError("plan diff counts do not match delta operations")
    if diff["first_apply"] and any(
        diff[field] != 0
        for field in (
            "pages_changed", "pages_unchanged", "pages_removed", "chunks_unchanged",
            "stale_rows", "retained_stale_rows",
        )
    ):
        raise ValueError("first-apply diff counts are inconsistent")


def artifact_identity(plan: Mapping[str, object]) -> dict[str, object]:
    return {
        "schema_version": plan["schema_version"],
        "source": plan["source"],
        "site_id": plan["site_id"],
        "namespace": plan["namespace"],
        "namespace_candidate": plan["namespace_candidate"],
        "crawl_options": plan["crawl_options"],
        "chunk_options": plan["chunk_options"],
        "embedding_model": plan["embedding_model"],
        "embedding_precision": plan["embedding_precision"],
        "applied_state": plan["applied_state"],
        "delta": plan["delta"],
        "routing_prototypes": plan["routing_prototypes"],
        "diff": plan["diff"],
    }


def stable_hash(value: Any) -> str:
    return hashlib.sha256(stable_json_dumps(value).encode("utf-8")).hexdigest()


def stable_json_dumps(value: Any) -> str:
    return json.dumps(
        _normalize_json(value), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )


def _normalize_json(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize_json(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("non-finite values are not supported")
        return value
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return str(value)


def _sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", "_", key.casefold()).strip("_")
    if normalized == "ranking_profile":
        return False
    secret_markers = (
        "password", "passwd", "credential", "secret", "authorization", "cookie",
        "api_key", "apikey", "private_key", "access_key", "session_key",
        "connection_string", "connection_uri", "connection_url", "connection_setting",
    )
    provider_settings = {
        "profile", "source_profile", "provider_profile", "connection", "source_connection",
        "provider_connection", "dsn", "account", "account_identifier", "warehouse", "role",
        "username", "user", "host", "port", "billing_project", "query_project",
        "connection_database", "connection_schema",
    }
    safe_token_fields = {"target_tokens", "max_tokens", "tokenizer_model", "tokenizer_revision"}
    token_bearing = "token" in normalized.split("_") and normalized not in safe_token_fields
    return (
        any(marker in normalized for marker in secret_markers)
        or normalized in provider_settings
        or token_bearing
    )


def _validate_private_free_json(
    value: object,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str] = _PUBLIC_URI_SCHEMES,
    _depth: int = 0,
    _budget: list[int] | None = None,
    _allow_source_relative_path: bool = False,
) -> None:
    if _budget is None:
        _budget = [0]
    if _depth > _MAX_PRIVACY_DEPTH:
        raise ValueError(f"plan {label} exceeds the privacy-validation nesting limit")
    _budget[0] += 1
    if _budget[0] > _MAX_PRIVACY_NODES:
        raise ValueError(f"plan {label} exceeds the privacy-validation value limit")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or _sensitive_key(key):
                raise ValueError(
                    f"plan {label} contains a credential-bearing or provider-connection field"
                )
            _validate_private_free_json(
                item,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                _depth=_depth + 1,
                _budget=_budget,
                _allow_source_relative_path=key in {"include_paths", "exclude_paths"},
            )
    elif isinstance(value, list):
        for item in value:
            _validate_private_free_json(
                item,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                _depth=_depth + 1,
                _budget=_budget,
                _allow_source_relative_path=_allow_source_relative_path,
            )
    elif isinstance(value, str):
        _validate_private_string(
            value,
            label=f"plan {label}",
            allowed_uri_schemes=allowed_uri_schemes,
            depth=_depth,
            allow_source_relative_path=_allow_source_relative_path,
        )
    elif value is None or type(value) in {bool, int, float}:
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f"plan {label} contains a non-finite number")
    else:
        raise ValueError(f"plan {label} contains an unsupported value")


def _normalized_component_tokens(value: str) -> set[str]:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    tokens = set(filter(None, normalized.split("_")))
    if normalized:
        tokens.add(normalized)
    return tokens


def _contains_secret_uri_component(value: str) -> bool:
    tokens = _normalized_component_tokens(value)
    if tokens & _SECRET_URI_COMPONENTS:
        return True
    return any(marker in tokens for marker in {"access_token", "api_key", "client_secret"})


def _decoded_variants(value: str) -> Iterable[str]:
    current = value
    yield current
    for _ in range(_MAX_URL_DECODE_ROUNDS):
        decoded = unquote(current)
        if decoded == current:
            return
        current = decoded
        yield current
    if unquote(current) != current:
        raise ValueError("plan privacy validation exceeded the URL decode limit")


def _is_absolute_filesystem_path(value: str) -> bool:
    return PurePosixPath(value).is_absolute() or PureWindowsPath(value).is_absolute()


def _trim_embedded_uri(value: str) -> str:
    return value.rstrip(".,;:!?)]}")


def _validate_absolute_uri(
    value: str,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str],
    depth: int,
) -> None:
    parsed = urlsplit(value)
    scheme = parsed.scheme.casefold()
    if not scheme:
        return
    if parsed.username is not None or parsed.password is not None:
        raise ValueError(f"{label} contains a credential-bearing URI")
    if scheme not in allowed_uri_schemes:
        raise ValueError(f"{label} contains an unapproved provider connection URI")
    if parsed.query:
        for name, item in parse_qsl(parsed.query, keep_blank_values=True):
            if _contains_secret_uri_component(name) or _contains_secret_uri_component(item):
                raise ValueError(f"{label} contains a secret-bearing URI query")
            _validate_private_string(
                item,
                label=label,
                allowed_uri_schemes=_PUBLIC_URI_SCHEMES,
                depth=depth + 1,
            )
    if parsed.fragment:
        fragment_items = parse_qsl(parsed.fragment, keep_blank_values=True)
        values = [parsed.fragment, *(part for pair in fragment_items for part in pair)]
        if any(_contains_secret_uri_component(item) for item in values):
            raise ValueError(f"{label} contains a secret-bearing URI fragment")
        for item in values:
            _validate_private_string(
                item,
                label=label,
                allowed_uri_schemes=_PUBLIC_URI_SCHEMES,
                depth=depth + 1,
            )


def _validate_private_string(
    value: str,
    *,
    label: str,
    allowed_uri_schemes: frozenset[str] = _PUBLIC_URI_SCHEMES,
    depth: int = 0,
    allow_source_relative_path: bool = False,
) -> None:
    if depth > _MAX_PRIVACY_DEPTH:
        raise ValueError(f"{label} exceeds the privacy-validation nesting limit")
    if len(value.encode("utf-8")) > _MAX_PRIVACY_STRING_BYTES:
        raise ValueError(f"{label} exceeds the privacy-validation string limit")
    for decoded in _decoded_variants(value):
        if "\x00" in decoded or (
            _is_absolute_filesystem_path(decoded)
            and not (allow_source_relative_path and PurePosixPath(decoded).is_absolute())
        ):
            raise ValueError(f"{label} contains a private absolute path")
        candidates: list[str] = []
        parsed = urlsplit(decoded)
        if parsed.scheme and "://" in decoded:
            candidates.append(decoded)
        candidates.extend(
            _trim_embedded_uri(match.group(1))
            for match in _EMBEDDED_ABSOLUTE_URI.finditer(decoded)
        )
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            _validate_absolute_uri(
                candidate,
                label=label,
                allowed_uri_schemes=allowed_uri_schemes,
                depth=depth,
            )


def _validate_safe_filename(value: str) -> None:
    if (
        not value
        or value != value.strip()
        or value in {".", ".."}
        or "/" in value
        or "\\" in value
        or "\x00" in value
        or PurePosixPath(value).is_absolute()
        or PureWindowsPath(value).is_absolute()
    ):
        raise ValueError("document plan source filename must be a safe basename")


def _validate_relative_source_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or value != value.strip()
        or "\\" in value
        or "\x00" in value
        or path.is_absolute()
        or any(part in {"", ".", ".."} for part in path.parts)
        or re.match(r"^[A-Za-z]:", value) is not None
    ):
        raise ValueError("source path must be a safe relative path")


def _source_allowed_uri_schemes(kind: str) -> frozenset[str]:
    return frozenset({
        "website": {"http", "https"},
        "github_repo": {"https"},
        "local_file": {"file"},
        "pdf": {"pdf"},
        "duckdb_relation": {"duckdb"},
        "bigquery_relation": {"bigquery"},
        "snowflake_relation": {"snowflake"},
    }[kind])
