"""Hardened local OpenAI-compatible Chat Completions adapter.

The adapter talks directly to an exact loopback endpoint. It never consults
proxy environment variables, follows redirects, sends credentials/cookies, or
logs request and response bodies.
"""

from __future__ import annotations

from dataclasses import dataclass
import http.client
import ipaddress
import json
import math
import os
import platform
import re
import socket
import ssl
import time
from typing import Callable, Mapping, Protocol, Sequence
from urllib.parse import urlsplit, urlunsplit

from buoy_search.semantics_models import (
    DETERMINISM_BEST_EFFORT,
    LOCAL_CHAT_PROTOCOL,
    MODEL_CONTRACT_VERSION,
    STRUCTURED_OUTPUT_MODES,
    LocalModelError,
    ModelContract,
    StructuredOutputError,
    StructuredResult,
    canonical_json,
    validate_json_schema,
)

DEFAULT_MODEL_ENDPOINT = "http://127.0.0.1:11434/v1"
DEFAULT_MODEL_TIMEOUT_SECONDS = 120.0
DEFAULT_MAX_REQUEST_BYTES = 256 * 1024
DEFAULT_MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_MAX_OUTPUT_TOKENS = 1_024
DOCTOR_PROMPT_CONTRACT_VERSION = "semantics-doctor-v1"
_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}
_OLLAMA_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
_SAFE_REVISION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:+@-]{0,511}$")
_SAFE_QUANTIZATION = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._+-]{0,127}$")
_WINDOWS_DRIVE_PATH = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class Endpoint:
    scheme: str
    host: str
    port: int
    base_path: str
    resolved_addresses: tuple[str, ...]

    @property
    def origin(self) -> str:
        authority = f"[{self.host}]" if ":" in self.host else self.host
        default = (self.scheme == "http" and self.port == 80) or (
            self.scheme == "https" and self.port == 443
        )
        return f"{self.scheme}://{authority}{'' if default else f':{self.port}'}"

    def url(self, path: str) -> str:
        prefix = self.base_path.rstrip("/")
        return f"{self.origin}{prefix}/{path.lstrip('/')}"


@dataclass(frozen=True)
class TransportResponse:
    status: int
    body: bytes
    headers: Mapping[str, str]


class JsonTransport(Protocol):
    def request(
        self,
        *,
        method: str,
        url: str,
        body: bytes | None,
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> TransportResponse: ...


Resolver = Callable[..., list[tuple[object, ...]]]


def validate_local_endpoint(
    value: str,
    *,
    resolver: Resolver = socket.getaddrinfo,
    deadline: float | None = None,
) -> Endpoint:
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise LocalModelError("local model endpoint is invalid", code="endpoint_invalid") from exc
    host = parsed.hostname
    if (
        parsed.scheme not in {"http", "https"}
        or host is None
        or host.casefold() not in _LOOPBACK_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise LocalModelError(
            "local model endpoint must be credential-free HTTP(S) on 127.0.0.1, localhost, or ::1",
            code="endpoint_not_loopback",
        )
    if parsed.path and not parsed.path.startswith("/"):
        raise LocalModelError("local model endpoint is invalid", code="endpoint_invalid")
    effective_port = port or (443 if parsed.scheme == "https" else 80)
    if effective_port < 1 or effective_port > 65_535:
        raise LocalModelError("local model endpoint port is invalid", code="endpoint_invalid")
    try:
        addresses = resolver(host, effective_port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise LocalModelError("local model endpoint could not be resolved", code="endpoint_resolution") from exc
    if deadline is not None:
        # A blocking resolver cannot be cancelled portably, but an over-budget
        # lookup must never be followed by a connection or request.
        _remaining_seconds(deadline)
    if not addresses:
        raise LocalModelError("local model endpoint could not be resolved", code="endpoint_resolution")
    resolved_addresses: list[str] = []
    for address in addresses:
        sockaddr = address[4]
        if not isinstance(sockaddr, tuple) or not sockaddr:
            raise LocalModelError("local model endpoint resolution is invalid", code="endpoint_resolution")
        try:
            resolved = ipaddress.ip_address(str(sockaddr[0]))
        except ValueError as exc:
            raise LocalModelError("local model endpoint resolution is invalid", code="endpoint_resolution") from exc
        if not resolved.is_loopback:
            raise LocalModelError(
                "local model endpoint resolved outside loopback",
                code="endpoint_resolution_not_loopback",
            )
        resolved_addresses.append(str(resolved))
    return Endpoint(
        parsed.scheme,
        host.casefold(),
        effective_port,
        parsed.path.rstrip("/"),
        tuple(dict.fromkeys(resolved_addresses)),
    )


class DirectLoopbackTransport:
    """Direct stdlib HTTP transport with no redirect, proxy, or cookie machinery."""

    def __init__(self, *, resolver: Resolver = socket.getaddrinfo) -> None:
        self._resolver = resolver

    def request(
        self,
        *,
        method: str,
        url: str,
        body: bytes | None,
        timeout_seconds: float,
        maximum_response_bytes: int,
    ) -> TransportResponse:
        deadline = time.monotonic() + timeout_seconds
        endpoint = validate_local_endpoint(
            url, resolver=self._resolver, deadline=deadline
        )
        parsed = urlsplit(url)
        path = urlunsplit(("", "", parsed.path or "/", parsed.query, ""))
        headers = {
            "Accept": "application/json",
            "Connection": "close",
            "User-Agent": "buoy-local-semantics/1",
            "Host": parsed.netloc,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(body))
        connection = http.client.HTTPConnection(
            endpoint.host,
            endpoint.port,
            timeout=_remaining_seconds(deadline),
        )
        raw_socket: socket.socket | None = None
        try:
            # Connect to the already-validated numeric address. No second DNS
            # lookup can rebind the request before sensitive bytes are sent.
            raw_socket = socket.create_connection(
                (endpoint.resolved_addresses[0], endpoint.port),
                timeout=_remaining_seconds(deadline),
            )
            _require_loopback_peer(raw_socket)
            if endpoint.scheme == "https":
                raw_socket.settimeout(_remaining_seconds(deadline))
                raw_socket = ssl.create_default_context().wrap_socket(
                    raw_socket, server_hostname=endpoint.host
                )
                _require_loopback_peer(raw_socket)
            raw_socket.settimeout(_remaining_seconds(deadline))
            connection.sock = raw_socket
            connection.request(method, path, body=body, headers=headers)
            raw_socket.settimeout(_remaining_seconds(deadline))
            response = connection.getresponse()
            if 300 <= response.status < 400:
                raise LocalModelError(
                    "local model redirects are prohibited", code="redirect_prohibited"
                )
            content_length = response.getheader("Content-Length")
            if content_length is not None:
                try:
                    declared = int(content_length)
                except ValueError as exc:
                    raise LocalModelError(
                        "local model response length is invalid", code="response_length"
                    ) from exc
                if declared < 0 or declared > maximum_response_bytes:
                    raise LocalModelError(
                        "local model response exceeds the configured byte limit",
                        code="response_too_large",
                    )
            payload = _read_response_with_deadline(
                response,
                sock=raw_socket,
                maximum_response_bytes=maximum_response_bytes,
                deadline=deadline,
            )
            return TransportResponse(
                response.status,
                payload,
                {name.casefold(): value for name, value in response.getheaders()},
            )
        except LocalModelError:
            raise
        except (OSError, TimeoutError, http.client.HTTPException, ssl.SSLError) as exc:
            code = "timeout" if isinstance(exc, (TimeoutError, socket.timeout)) else "transport_failure"
            raise LocalModelError(
                f"local model request failed ({exc.__class__.__name__})", code=code
            ) from None
        finally:
            connection.close()


def _remaining_seconds(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LocalModelError("local model request exceeded its total deadline", code="timeout")
    return remaining


def _require_loopback_peer(sock: socket.socket) -> None:
    peer = sock.getpeername()[0]
    try:
        peer_ip = ipaddress.ip_address(str(peer))
    except ValueError as exc:
        raise LocalModelError("local model connection peer is invalid", code="peer_invalid") from exc
    if not peer_ip.is_loopback:
        raise LocalModelError("local model connection escaped loopback", code="peer_not_loopback")


def _read_response_with_deadline(
    response: http.client.HTTPResponse,
    *,
    sock: socket.socket,
    maximum_response_bytes: int,
    deadline: float,
) -> bytes:
    chunks: list[bytes] = []
    total = 0
    reader = getattr(response, "read1", response.read)
    while True:
        sock.settimeout(_remaining_seconds(deadline))
        # read1 performs at most one underlying socket read, allowing the
        # monotonic deadline to be recomputed even for slow-drip responses.
        chunk = reader(min(64 * 1024, maximum_response_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > maximum_response_bytes:
            raise LocalModelError(
                "local model response exceeds the configured byte limit",
                code="response_too_large",
            )
    return b"".join(chunks)


def _validate_public_model_id(model_id: str) -> None:
    segments = model_id.replace("\\", "/").split("/")
    if (
        os.path.isabs(model_id)
        or _WINDOWS_DRIVE_PATH.match(model_id)
        or "/" in model_id
        or "\\" in model_id
        or model_id.startswith(("./", "../", "file:"))
        or ".." in segments
        or any(character.isspace() and character not in {" "} for character in model_id)
    ):
        raise LocalModelError(
            "model ID must be a public alias, not a local filesystem path",
            code="model_id_path",
        )


def _ollama_digest(
    value: object, *, source: str, required: bool = False
) -> str | None:
    if value is None and not required:
        return None
    if not isinstance(value, str) or _OLLAMA_DIGEST.fullmatch(value) is None:
        raise LocalModelError(
            f"local Ollama runtime returned an invalid {source} digest",
            code="revision_invalid",
        )
    return value


def _safe_runtime_version(value: object) -> str | None:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", value) is None:
        return None
    return value


def _validate_model_revision(value: str) -> str:
    revision = value.strip()
    if (
        _SAFE_REVISION.fullmatch(revision) is None
        or revision.casefold().startswith(("file:", "path:"))
        or _WINDOWS_DRIVE_PATH.match(revision)
        or ".." in revision
    ):
        raise LocalModelError(
            "model revision must be a bounded public revision token",
            code="model_revision",
        )
    return revision


def _safe_quantization(value: object) -> str | None:
    if not isinstance(value, str) or _SAFE_QUANTIZATION.fullmatch(value) is None:
        return None
    return value


class OpenAICompatibleLocalClient:
    """One pinned local model accessed through the portable Chat API subset."""

    def __init__(
        self,
        *,
        endpoint: str,
        model_id: str,
        model_revision: str | None,
        model_context_window: int,
        timeout_seconds: float = DEFAULT_MODEL_TIMEOUT_SECONDS,
        seed: int = 0,
        structured_output_mode: str = "openai_json_schema",
        maximum_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES,
        maximum_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
        transport: JsonTransport | None = None,
        resolver: Resolver = socket.getaddrinfo,
    ) -> None:
        self.endpoint = validate_local_endpoint(endpoint, resolver=resolver)
        if not isinstance(model_id, str) or not model_id.strip() or len(model_id) > 512:
            raise LocalModelError("model ID must be a bounded non-empty string", code="model_id")
        _validate_public_model_id(model_id.strip())
        if model_revision is not None and not isinstance(model_revision, str):
            raise LocalModelError(
                "model revision must be a bounded public revision token",
                code="model_revision",
            )
        if type(model_context_window) is not int or model_context_window < 1:
            raise LocalModelError("model context window must be a positive integer", code="context_window")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(float(timeout_seconds))
            or timeout_seconds <= 0
        ):
            raise LocalModelError("model timeout must be finite and greater than zero", code="timeout_value")
        if type(seed) is not int:
            raise LocalModelError("model seed must be an integer", code="seed")
        if structured_output_mode not in STRUCTURED_OUTPUT_MODES:
            raise LocalModelError("structured output mode is unsupported", code="structured_mode")
        for name, value in (
            ("maximum request bytes", maximum_request_bytes),
            ("maximum response bytes", maximum_response_bytes),
        ):
            if type(value) is not int or value < 1:
                raise LocalModelError(f"{name} must be a positive integer", code="byte_limit")
        self.model_id = model_id.strip()
        self.configured_revision = (
            _validate_model_revision(model_revision) if model_revision is not None else None
        )
        self.model_context_window = model_context_window
        self.timeout_seconds = float(timeout_seconds)
        self.seed = seed
        self.structured_output_mode = structured_output_mode
        self.maximum_request_bytes = maximum_request_bytes
        self.maximum_response_bytes = maximum_response_bytes
        self._transport = transport or DirectLoopbackTransport(resolver=resolver)

    def structured_chat(
        self,
        *,
        messages: Sequence[Mapping[str, str]],
        schema: Mapping[str, object],
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ) -> StructuredResult:
        if type(max_output_tokens) is not int or max_output_tokens < 1:
            raise LocalModelError("maximum output tokens must be positive", code="output_tokens")
        safe_messages: list[dict[str, str]] = []
        for message in messages:
            if set(message) != {"role", "content"}:
                raise LocalModelError("local model message has invalid fields", code="message_schema")
            role, content = message.get("role"), message.get("content")
            if role not in {"system", "user", "assistant"} or not isinstance(content, str):
                raise LocalModelError("local model message is invalid", code="message_schema")
            safe_messages.append({"role": role, "content": content})
        response_format: dict[str, object]
        if self.structured_output_mode == "openai_json_schema":
            response_format = {
                "type": "json_schema",
                "json_schema": {"name": "buoy_response", "strict": True, "schema": dict(schema)},
            }
        else:
            response_format = {"type": "json_schema", "schema": dict(schema)}
        request = {
            "model": self.model_id,
            "messages": safe_messages,
            "stream": False,
            "temperature": 0,
            "seed": self.seed,
            "max_tokens": max_output_tokens,
            "response_format": response_format,
        }
        started = time.monotonic()
        response, response_bytes = self._json_request(
            method="POST", url=self.endpoint.url("chat/completions"), value=request
        )
        latency = time.monotonic() - started
        try:
            choices = response["choices"]
            if not isinstance(choices, list) or len(choices) != 1:
                raise TypeError
            message = choices[0]["message"]
            content = message["content"]
            if not isinstance(content, str):
                raise TypeError
        except (KeyError, IndexError, TypeError):
            raise StructuredOutputError(
                "local model returned an invalid Chat Completions envelope",
                code="response_envelope",
            ) from None
        if len(content.encode("utf-8")) > self.maximum_response_bytes:
            raise StructuredOutputError(
                "local model structured content exceeds the byte limit",
                code="structured_content_too_large",
            )
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            raise StructuredOutputError(
                "local model returned malformed structured JSON",
                code="malformed_json",
                invalid_output=content,
            ) from None
        if not isinstance(value, dict):
            raise StructuredOutputError(
                "local model structured output must be an object",
                code="schema_type",
                invalid_output=content,
            )
        try:
            validate_json_schema(value, schema)
        except StructuredOutputError as exc:
            raise StructuredOutputError(
                str(exc), code=exc.code, invalid_output=content
            ) from None
        return StructuredResult(value, response_bytes, latency)

    def doctor(self, *, prompt_contract_version: str = DOCTOR_PROMPT_CONTRACT_VERSION) -> dict[str, object]:
        models, _ = self._json_request(method="GET", url=self.endpoint.url("models"), value=None)
        data = models.get("data")
        if not isinstance(data, list) or not any(
            isinstance(item, dict) and item.get("id") == self.model_id for item in data
        ):
            raise LocalModelError("configured local model is unavailable", code="model_unavailable")

        metadata = self._runtime_metadata()
        observed_revision = metadata.get("model_revision")
        if observed_revision is not None and not isinstance(observed_revision, str):
            observed_revision = None
        if self.configured_revision and observed_revision and self.configured_revision != observed_revision:
            raise LocalModelError("configured model revision does not match the local runtime", code="revision_mismatch")
        revision = observed_revision or self.configured_revision
        if not revision:
            raise LocalModelError(
                "an immutable model revision is required because the runtime did not expose one",
                code="revision_required",
            )
        observed_context = metadata.get("observed_context_window")
        if type(observed_context) is int and observed_context != self.model_context_window:
            raise LocalModelError(
                "configured model context window does not match the local runtime",
                code="context_mismatch",
            )
        structured_supported = metadata.get("structured_output_supported") is True
        if not structured_supported:
            raise LocalModelError(
                "the local runtime did not explicitly confirm required structured output",
                code="structured_output_unconfirmed",
            )
        seed_supported = metadata.get("seed_supported") is True
        schema = {
            "type": "object",
            "properties": {"ok": {"type": "boolean"}, "label": {"type": "string", "maxLength": 32}},
            "required": ["ok", "label"],
            "additionalProperties": False,
        }
        result = self.structured_chat(
            messages=(
                {"role": "system", "content": "Return only JSON matching the supplied schema."},
                {"role": "user", "content": "Synthetic diagnostic only. Return ok=true and label='local'."},
            ),
            schema=schema,
            max_output_tokens=64,
        )
        if result.value != {"ok": True, "label": "local"}:
            raise StructuredOutputError(
                "local model synthetic diagnostic returned an unexpected value",
                code="doctor_value",
            )
        runtime_identity = str(metadata.get("runtime_identity") or "openai_compatible_local")[:128]
        runtime_version = _safe_runtime_version(metadata.get("runtime_version"))
        quantization = _safe_quantization(metadata.get("model_quantization"))
        contract = ModelContract(
            contract_version=MODEL_CONTRACT_VERSION,
            runtime_protocol=LOCAL_CHAT_PROTOCOL,
            runtime_identity=runtime_identity,
            runtime_version=runtime_version[:128] if runtime_version else None,
            model_id=self.model_id,
            model_revision=revision,
            revision_verification="runtime_digest" if observed_revision else "externally_asserted",
            model_quantization=quantization,
            model_context_window=self.model_context_window,
            seed=self.seed,
            seed_supported=seed_supported,
            structured_output_supported=structured_supported,
            structured_output_mode=self.structured_output_mode,
            prompt_contract_version=prompt_contract_version,
            determinism=DETERMINISM_BEST_EFFORT,
        )
        return {
            "command": "semantics doctor",
            "healthy": True,
            "model_contract": contract.to_dict(),
            "model_contract_hash": contract.contract_hash,
            "configured_context_window": self.model_context_window,
            "observed_runtime_context_window": observed_context,
            "local_model_loaded": metadata.get("model_loaded"),
            "model_size_bytes": metadata.get("model_size_bytes"),
            "observed_local_call_latency_seconds": round(result.latency_seconds, 6),
            "structured_response_bytes": result.response_bytes,
            "platform": _platform_report(),
            "evidence_transmitted": False,
            "local_model_calls_occurred": True,
            "evidence_rows_read": 0,
            "turbopuffer_api_calls_occurred": False,
            "turbopuffer_writes_occurred": False,
            "hosted_model_calls_occurred": False,
            "hosted_model_cost": 0,
        }

    def _runtime_metadata(self) -> dict[str, object]:
        origin = self.endpoint.origin
        version = self._optional_get(f"{origin}/api/version")
        if isinstance(version, dict) and isinstance(version.get("version"), str):
            tags = self._optional_get(f"{origin}/api/tags") or {}
            running = self._optional_get(f"{origin}/api/ps") or {}
            model: dict[str, object] | None = None
            for item in tags.get("models", []) if isinstance(tags, dict) else []:
                if isinstance(item, dict) and self.model_id in {item.get("name"), item.get("model")}:
                    model = item
                    break
            active: dict[str, object] | None = None
            for item in running.get("models", []) if isinstance(running, dict) else []:
                if isinstance(item, dict) and self.model_id in {item.get("name"), item.get("model")}:
                    active = item
                    break
            details = model.get("details") if isinstance(model, dict) else None
            tag_digest = _ollama_digest(
                model.get("digest") if isinstance(model, dict) else None,
                source="installed model",
                required=model is not None,
            )
            active_digest = _ollama_digest(
                active.get("digest") if isinstance(active, dict) else None,
                source="active model",
                required=active is not None,
            )
            if tag_digest and active_digest and tag_digest != active_digest:
                raise LocalModelError(
                    "local Ollama runtime returned conflicting immutable model digests",
                    code="revision_conflict",
                )
            return {
                "runtime_identity": "ollama",
                "runtime_version": _safe_runtime_version(version["version"]),
                "model_revision": tag_digest or active_digest,
                "model_quantization": details.get("quantization_level") if isinstance(details, dict) else None,
                "model_size_bytes": model.get("size") if isinstance(model, dict) and type(model.get("size")) is int else None,
                # An absent /api/ps match means the configured model is installed
                # but not currently loaded; tag digest pinning remains valid while
                # active context metadata is unavailable.
                "model_loaded": active is not None,
                "observed_context_window": active.get("context_length") if isinstance(active, dict) else None,
                "seed_supported": True,
                "structured_output_supported": self.structured_output_mode == "openai_json_schema",
            }
        props = self._optional_get(f"{origin}/props")
        if isinstance(props, dict):
            default = props.get("default_generation_settings")
            return {
                "runtime_identity": "llama.cpp",
                # llama.cpp build_info may include compiler or filesystem paths;
                # it is not model identity and is intentionally not persisted.
                "runtime_version": None,
                "model_loaded": True,
                "observed_context_window": default.get("n_ctx") if isinstance(default, dict) else None,
                "seed_supported": True,
                "structured_output_supported": self.structured_output_mode == "llama_cpp_json_schema",
            }
        return {
            "runtime_identity": "openai_compatible_local",
            "seed_supported": False,
            "structured_output_supported": False,
        }

    def _optional_get(self, url: str) -> dict[str, object] | None:
        try:
            value, _ = self._json_request(method="GET", url=url, value=None)
            return value
        except LocalModelError as exc:
            if exc.code in {"status_404", "status_405", "status_501"}:
                return None
            raise

    def _json_request(
        self, *, method: str, url: str, value: object | None
    ) -> tuple[dict[str, object], int]:
        body = None if value is None else canonical_json(value).encode("utf-8")
        if body is not None and len(body) > self.maximum_request_bytes:
            raise LocalModelError(
                "local model request exceeds the configured byte limit",
                code="request_too_large",
            )
        response = self._transport.request(
            method=method,
            url=url,
            body=body,
            timeout_seconds=self.timeout_seconds,
            maximum_response_bytes=self.maximum_response_bytes,
        )
        if response.status != 200:
            if 300 <= response.status < 400:
                raise LocalModelError(
                    "local model redirects are prohibited", code="redirect_prohibited"
                )
            raise LocalModelError(
                f"local model request failed (status {response.status})",
                code=f"status_{response.status}",
            )
        try:
            value = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise LocalModelError(
                "local model returned malformed JSON", code="malformed_response_json"
            ) from None
        if not isinstance(value, dict):
            raise LocalModelError(
                "local model returned a non-object JSON response", code="response_type"
            )
        return value, len(response.body)


def _platform_report() -> dict[str, object]:
    report: dict[str, object] = {
        "system": platform.system()[:64],
        "architecture": platform.machine()[:64],
        "python_implementation": platform.python_implementation()[:64],
        "python_version": platform.python_version()[:64],
    }
    try:
        page_size = int(__import__("os").sysconf("SC_PAGE_SIZE"))
        pages = int(__import__("os").sysconf("SC_PHYS_PAGES"))
        memory = page_size * pages
        if memory > 0:
            report["physical_memory_bytes"] = memory
    except (AttributeError, OSError, TypeError, ValueError):
        pass
    return report
