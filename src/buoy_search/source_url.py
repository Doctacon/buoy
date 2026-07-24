"""Lightweight source URL normalization without loading source adapters."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import SplitResult, urlparse, urlsplit, urlunparse

_DATABASE_SCHEMES = frozenset({"duckdb", "bigquery", "snowflake"})
_SAFE_DATABASE_SOURCE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
_SAFE_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?")


def validate_http_url_authority(url: str) -> SplitResult:
    """Return a strictly validated HTTP(S) URL split without imposing network policy."""

    if not isinstance(url, str) or not url or url != url.strip() or any(
        character.isspace() for character in url
    ):
        raise ValueError("HTTP(S) URL must not contain whitespace.")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError as exc:
        raise ValueError("HTTP(S) URL has an invalid authority or port.") from exc
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL must use http or https.")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("HTTP(S) URL must not contain userinfo or credentials.")
    if not parsed.netloc or not hostname:
        raise ValueError("HTTP(S) URL must include a hostname.")

    authority = parsed.netloc
    bracketed_authority = authority.startswith("[")
    if bracketed_authority:
        closing_bracket = authority.find("]")
        suffix = authority[closing_bracket + 1 :] if closing_bracket >= 0 else ""
        if closing_bracket < 0 or (suffix and not suffix.startswith(":")) or suffix == ":":
            raise ValueError("HTTP(S) URL has an invalid port.")
    elif authority.endswith(":"):
        raise ValueError("HTTP(S) URL has an invalid port.")
    if port is not None and not 1 <= port <= 65_535:
        raise ValueError("HTTP(S) URL port must be between 1 and 65535.")

    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if bracketed_authority:
            raise ValueError("HTTP(S) URL IP address is invalid.")
        dotted_candidate = hostname[:-1] if hostname.endswith(".") else hostname
        dotted_labels = dotted_candidate.split(".")
        if len(dotted_labels) == 4 and all(
            label.isascii() and label.isdigit() for label in dotted_labels
        ):
            raise ValueError("HTTP(S) URL IP address is invalid.")
        try:
            ascii_hostname = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as exc:
            raise ValueError("HTTP(S) URL hostname is invalid.") from exc
        dns_name = ascii_hostname[:-1] if ascii_hostname.endswith(".") else ascii_hostname
        labels = dns_name.split(".")
        if (
            not dns_name
            or len(dns_name) > 253
            or any(_SAFE_DNS_LABEL.fullmatch(label) is None for label in labels)
        ):
            raise ValueError("HTTP(S) URL hostname is invalid.")
    return parsed


def validate_base_url(url: str) -> str:
    """Return the normalized source base URL or raise ``ValueError``."""

    parsed = urlparse(url)
    if parsed.scheme in _DATABASE_SCHEMES:
        try:
            port = parsed.port
        except ValueError as exc:
            raise ValueError("Database base URL has an invalid port.") from exc
        if (
            not parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or parsed.path != ""
            or parsed.params
            or parsed.query
            or parsed.fragment
            or _SAFE_DATABASE_SOURCE_ID.fullmatch(parsed.netloc) is None
        ):
            raise ValueError(
                "Database base URL must be duckdb://, bigquery://, or snowflake://<source-id> "
                "with no path, credentials, port, query, or fragment."
            )
        return f"{parsed.scheme}://{parsed.netloc}"
    if parsed.scheme == "pdf":
        if (
            not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
        ):
            raise ValueError("PDF base URL must be an internal pdf://<source-id> URI")
        return urlunparse(parsed._replace(path="", params="", query="", fragment=""))
    if parsed.scheme == "file":
        if (
            not parsed.netloc
            or parsed.path not in {"", "/"}
            or parsed.params
            or parsed.query
        ):
            raise ValueError(
                "local file base URL must be an internal file://<source-id> URI"
            )
        return urlunparse(parsed._replace(path="", params="", query="", fragment=""))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("base URL must be an absolute http(s) URL")
    return urlunparse(parsed._replace(fragment=""))
