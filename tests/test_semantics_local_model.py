from __future__ import annotations

import json
import os
import socket
import unittest
from unittest.mock import Mock, patch

from buoy_search.semantics_local_model import (
    DirectLoopbackTransport,
    OpenAICompatibleLocalClient,
    TransportResponse,
    validate_local_endpoint,
)
from buoy_search.semantics_models import LocalModelError, StructuredOutputError


DIGEST = "sha256:" + "a" * 64
OTHER_DIGEST = "sha256:" + "b" * 64


def loopback_resolver(host: str, port: int, **_kwargs: object):
    address = "::1" if host == "::1" else "127.0.0.1"
    family = socket.AF_INET6 if address == "::1" else socket.AF_INET
    sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
    return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]


class FakeTransport:
    def __init__(self, responses: list[TransportResponse | BaseException]) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, object]] = []

    def request(self, **kwargs: object) -> TransportResponse:
        self.requests.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def response(value: object, status: int = 200) -> TransportResponse:
    return TransportResponse(status, json.dumps(value).encode(), {})


def chat(content: object) -> TransportResponse:
    return response({"choices": [{"message": {"role": "assistant", "content": json.dumps(content)}}]})


def client(transport: FakeTransport, **overrides: object) -> OpenAICompatibleLocalClient:
    values = {
        "endpoint": "http://127.0.0.1:11434/v1",
        "model_id": "local-model",
        "model_revision": DIGEST,
        "model_context_window": 8192,
        "transport": transport,
        "resolver": loopback_resolver,
    }
    values.update(overrides)
    return OpenAICompatibleLocalClient(**values)


class EndpointPolicyTests(unittest.TestCase):
    def test_accepts_exact_ipv4_localhost_and_ipv6_loopback(self) -> None:
        for endpoint in (
            "http://127.0.0.1:11434/v1",
            "https://localhost:8443/v1",
            "http://[::1]:8080/v1",
        ):
            with self.subTest(endpoint=endpoint):
                self.assertTrue(validate_local_endpoint(endpoint, resolver=loopback_resolver).host)

    def test_rejects_public_lan_dns_credentials_and_non_http(self) -> None:
        for endpoint in (
            "https://api.openai.com/v1",
            "http://192.168.1.10:11434/v1",
            "http://model.internal:11434/v1",
            "http://user:secret@localhost:11434/v1",
            "ftp://localhost:11434/v1",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(LocalModelError):
                validate_local_endpoint(endpoint, resolver=loopback_resolver)

    def test_rejects_localhost_when_any_resolution_is_non_loopback(self) -> None:
        def poisoned(_host: str, port: int, **_kwargs: object):
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port)),
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.2", port)),
            ]

        with self.assertRaises(LocalModelError) as caught:
            validate_local_endpoint("http://localhost:11434/v1", resolver=poisoned)
        self.assertEqual(caught.exception.code, "endpoint_resolution_not_loopback")


class StructuredClientTests(unittest.TestCase):
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }

    def test_strict_request_uses_temperature_zero_seed_and_bounded_nonstreaming_output(self) -> None:
        transport = FakeTransport([chat({"ok": True})])
        result = client(transport).structured_chat(
            messages=({"role": "user", "content": "synthetic"},),
            schema=self.schema,
            max_output_tokens=50,
        )
        self.assertEqual(result.value, {"ok": True})
        request = json.loads(transport.requests[0]["body"])
        self.assertEqual(request["temperature"], 0)
        self.assertEqual(request["seed"], 0)
        self.assertFalse(request["stream"])
        self.assertEqual(request["max_tokens"], 50)
        self.assertEqual(request["response_format"]["type"], "json_schema")
        self.assertNotIn("api_key", request)

    def test_llama_cpp_schema_envelope_is_explicit(self) -> None:
        transport = FakeTransport([chat({"ok": True})])
        client(transport, structured_output_mode="llama_cpp_json_schema").structured_chat(
            messages=({"role": "user", "content": "synthetic"},), schema=self.schema
        )
        request = json.loads(transport.requests[0]["body"])
        self.assertIn("schema", request["response_format"])
        self.assertNotIn("json_schema", request["response_format"])

    def test_malformed_json_envelope_and_schema_fail_with_sanitized_codes(self) -> None:
        secret = "PRIVATE_EVIDENCE_SENTENCE"
        cases = [
            (response({"choices": [{"message": {"content": "not-json"}}]}), "malformed_json"),
            (chat({"ok": True, "evidence": secret}), "schema_unknown_fields"),
            (response({"choices": []}), "response_envelope"),
        ]
        for raw, code in cases:
            with self.subTest(code=code):
                transport = FakeTransport([raw])
                with self.assertRaises(StructuredOutputError) as caught:
                    client(transport).structured_chat(
                        messages=({"role": "user", "content": secret},), schema=self.schema
                    )
                self.assertEqual(caught.exception.code, code)
                self.assertNotIn(secret, str(caught.exception))
                if code in {"malformed_json", "schema_unknown_fields"}:
                    self.assertIsNotNone(caught.exception._invalid_output)
                    self.assertLessEqual(len(caught.exception._invalid_output or ""), 16_384)

    def test_request_cap_fails_before_transport(self) -> None:
        transport = FakeTransport([])
        with self.assertRaises(LocalModelError) as caught:
            client(transport, maximum_request_bytes=100).structured_chat(
                messages=({"role": "user", "content": "x" * 1_000},), schema=self.schema
            )
        self.assertEqual(caught.exception.code, "request_too_large")
        self.assertEqual(transport.requests, [])

    def test_redirect_is_rejected_without_second_request(self) -> None:
        transport = FakeTransport([TransportResponse(302, b"", {"location": "https://example.com"})])
        with self.assertRaises(LocalModelError) as caught:
            client(transport).structured_chat(
                messages=({"role": "user", "content": "synthetic"},), schema=self.schema
            )
        self.assertEqual(caught.exception.code, "redirect_prohibited")
        self.assertEqual(len(transport.requests), 1)


class DoctorContractTests(unittest.TestCase):
    def test_ollama_doctor_discovers_digest_and_reports_synthetic_only_activity(self) -> None:
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}),
            response({"version": "0.9.0"}),
            response({"models": [{"name": "local-model", "digest": DIGEST, "size": 1234, "details": {"quantization_level": "Q4_K_M"}}]}),
            response({"models": [{"name": "local-model", "digest": DIGEST, "context_length": 8192}]}),
            chat({"ok": True, "label": "local"}),
        ])
        result = client(transport, model_revision=None).doctor()
        contract = result["model_contract"]
        self.assertEqual(contract["runtime_identity"], "ollama")
        self.assertEqual(contract["model_revision"], DIGEST)
        self.assertEqual(contract["revision_verification"], "runtime_digest")
        self.assertEqual(contract["model_quantization"], "Q4_K_M")
        self.assertEqual(result["model_size_bytes"], 1234)
        self.assertTrue(result["local_model_calls_occurred"])
        self.assertFalse(result["evidence_transmitted"])
        self.assertEqual(result["evidence_rows_read"], 0)
        self.assertFalse(result["turbopuffer_api_calls_occurred"])
        self.assertFalse(result["hosted_model_calls_occurred"])
        bodies = [request["body"] for request in transport.requests if request["body"]]
        self.assertFalse(any(b"evidence_snapshot" in body for body in bodies))

    def test_ollama_raw_digest_is_canonicalized_and_matches_prefixed_pin(self) -> None:
        raw_digest = "a" * 64
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}),
            response({"version": "0.11.10"}),
            response({"models": [{"name": "local-model", "digest": raw_digest}]}),
            response({"models": [{"name": "local-model", "digest": raw_digest, "context_length": 8192}]}),
            chat({"ok": True, "label": "local"}),
        ])
        result = client(transport, model_revision=DIGEST).doctor()
        self.assertEqual(result["model_contract"]["model_revision"], DIGEST)
        self.assertEqual(result["model_contract"]["revision_verification"], "runtime_digest")

    def test_unavailable_model_revision_mismatch_context_mismatch_and_missing_revision_fail(self) -> None:
        unavailable = FakeTransport([response({"data": [{"id": "other"}]})])
        with self.assertRaises(LocalModelError) as caught:
            client(unavailable).doctor()
        self.assertEqual(caught.exception.code, "model_unavailable")

        mismatch = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({"version": "1"}),
            response({"models": [{"name": "local-model", "digest": OTHER_DIGEST}]}), response({"models": []}),
        ])
        with self.assertRaises(LocalModelError) as caught:
            client(mismatch).doctor()
        self.assertEqual(caught.exception.code, "revision_mismatch")

        context = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({"version": "1"}),
            response({"models": [{"name": "local-model", "digest": DIGEST}]}),
            response({"models": [{"name": "local-model", "digest": DIGEST, "context_length": 4096}]}),
        ])
        with self.assertRaises(LocalModelError) as caught:
            client(context).doctor()
        self.assertEqual(caught.exception.code, "context_mismatch")

        no_revision = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({}, 404), response({}, 404),
        ])
        with self.assertRaises(LocalModelError) as caught:
            client(no_revision, model_revision=None).doctor()
        self.assertEqual(caught.exception.code, "revision_required")

    def test_invalid_or_conflicting_ollama_digests_fail_closed(self) -> None:
        cases = (
            (
                [{"name": "local-model", "digest": "sha256:abc"}],
                [],
                "revision_invalid",
            ),
            (
                [{"name": "local-model", "digest": DIGEST}],
                [{"name": "local-model", "digest": "sha256:abc", "context_length": 8192}],
                "revision_invalid",
            ),
            (
                [{"name": "local-model", "digest": DIGEST}],
                [{"name": "local-model", "digest": OTHER_DIGEST, "context_length": 8192}],
                "revision_conflict",
            ),
            (
                [{"name": "local-model", "digest": DIGEST}],
                [{"name": "local-model", "context_length": 8192}],
                "revision_invalid",
            ),
        )
        for tags, active, code in cases:
            with self.subTest(code=code, active=active):
                transport = FakeTransport([
                    response({"data": [{"id": "local-model"}]}),
                    response({"version": "1"}),
                    response({"models": tags}),
                    response({"models": active}),
                ])
                with self.assertRaises(LocalModelError) as caught:
                    client(transport, model_revision=None).doctor()
                self.assertEqual(caught.exception.code, code)

    def test_unloaded_ollama_model_uses_installed_digest_without_claiming_context(self) -> None:
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}),
            response({"version": "1"}),
            response({"models": [{"name": "local-model", "digest": DIGEST}]}),
            response({"models": []}),
            chat({"ok": True, "label": "local"}),
        ])
        result = client(transport, model_revision=None).doctor()
        self.assertFalse(result["local_model_loaded"])
        self.assertIsNone(result["observed_runtime_context_window"])
        self.assertEqual(result["model_contract"]["model_revision"], DIGEST)

    def test_generic_runtime_cannot_claim_structured_or_seed_capability(self) -> None:
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({}, 404), response({}, 404),
        ])
        with self.assertRaises(LocalModelError) as caught:
            client(transport).doctor()
        self.assertEqual(caught.exception.code, "structured_output_unconfirmed")
        self.assertEqual(len(transport.requests), 3)

    def test_structured_capability_failure_does_not_claim_support(self) -> None:
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({"version": "1"}),
            response({"models": [{"name": "local-model", "digest": DIGEST}]}),
            response({"models": []}), response({"error": "schema unsupported"}, 400),
        ])
        with self.assertRaises(LocalModelError) as caught:
            client(transport).doctor()
        self.assertEqual(caught.exception.code, "status_400")

    def test_platform_report_contains_no_hostname_or_path(self) -> None:
        private = "/Users/alice/private/llama.cpp/build"
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}), response({}, 404),
            response({
                "build_info": private,
                "model_path": "/Users/alice/private/model.gguf",
                "default_generation_settings": {"n_ctx": 8192},
            }),
            chat({"ok": True, "label": "local"}),
        ])
        result = client(transport, structured_output_mode="llama_cpp_json_schema").doctor()
        serialized = json.dumps(result)
        platform_report = result["platform"]
        self.assertNotIn("hostname", platform_report)
        self.assertNotIn("cwd", platform_report)
        self.assertNotIn("model_path", serialized)
        self.assertNotIn("/Users/alice", serialized)
        self.assertNotIn("private", serialized)
        self.assertIsNone(result["model_contract"]["runtime_version"])
        self.assertTrue(result["model_contract"]["seed_supported"])

    def test_private_revision_and_quantization_values_never_reach_doctor_output(self) -> None:
        normal_revision = "gguf-sha256_abc123"
        self.assertEqual(
            client(FakeTransport([]), model_revision=normal_revision).configured_revision,
            normal_revision,
        )
        for revision in (
            "/Users/alice/private/revision.txt",
            "../private/revision.txt",
            r"relative\\private\\revision.txt",
            "C:private-revision.txt",
            "file:private-revision.txt",
            "revision\nprivate",
        ):
            with self.subTest(revision=revision), self.assertRaises(LocalModelError) as caught:
                client(FakeTransport([]), model_revision=revision)
            self.assertEqual(caught.exception.code, "model_revision")
            self.assertNotIn("private", str(caught.exception))
            self.assertNotIn("alice", str(caught.exception))

        private = "/Users/alice/private/quantization.txt"
        transport = FakeTransport([
            response({"data": [{"id": "local-model"}]}),
            response({"version": "1"}),
            response({
                "models": [{
                    "name": "local-model",
                    "digest": DIGEST,
                    "details": {"quantization_level": private},
                }]
            }),
            response({"models": []}),
            chat({"ok": True, "label": "local"}),
        ])
        result = client(transport, model_revision=None).doctor()
        serialized = json.dumps(result)
        self.assertIsNone(result["model_contract"]["model_quantization"])
        self.assertNotIn("/Users/alice", serialized)
        self.assertNotIn("private", serialized)
        self.assertNotIn("quantization.txt", serialized)

    def test_private_path_model_ids_and_nonfinite_timeouts_are_rejected(self) -> None:
        for model_id in (
            "/Users/alice/private/model.gguf",
            r"C:\\private\\model.gguf",
            "C:private-model.gguf",
            "../model.gguf",
            "relative/model.gguf",
            r"relative\\model.gguf",
        ):
            with self.subTest(model_id=model_id), self.assertRaises(LocalModelError) as caught:
                client(FakeTransport([]), model_id=model_id)
            self.assertEqual(caught.exception.code, "model_id_path")
            self.assertNotIn("private", str(caught.exception))
        for timeout in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(timeout=timeout), self.assertRaises(LocalModelError) as caught:
                client(FakeTransport([]), timeout_seconds=timeout)
            self.assertEqual(caught.exception.code, "timeout_value")


class DirectTransportTests(unittest.TestCase):
    class Sock:
        def __init__(self, peer: str = "127.0.0.1") -> None:
            self.peer = peer
            self.timeouts: list[float] = []
        def getpeername(self):
            return (self.peer, 11434)
        def settimeout(self, value: float):
            self.timeouts.append(value)
        def close(self):
            return None

    class Response:
        status = 200
        def __init__(self, body: bytes = b"{}", length: str | None = None) -> None:
            self._body = body
            self._length = length
            self._offset = 0
        def getheader(self, name: str):
            return self._length if name == "Content-Length" else None
        def read(self, limit: int):
            value = self._body[self._offset:self._offset + limit]
            self._offset += len(value)
            return value
        def read1(self, limit: int):
            return self.read(limit)
        def getheaders(self):
            return []

    class Connection:
        last_headers: dict[str, str] = {}
        last_body: bytes | None = None
        request_count = 0
        response = None
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            self.sock = None
        def request(self, _method: str, _path: str, body=None, headers=None):
            DirectTransportTests.Connection.last_headers = headers
            DirectTransportTests.Connection.last_body = body
            DirectTransportTests.Connection.request_count += 1
        def getresponse(self):
            return self.response or DirectTransportTests.Response()
        def close(self):
            return None

    def setUp(self) -> None:
        self.Connection.last_headers = {}
        self.Connection.last_body = None
        self.Connection.request_count = 0
        self.Connection.response = None

    def request(self, *, sock=None, **kwargs):
        connected = sock or self.Sock()
        with patch(
            "buoy_search.semantics_local_model.socket.create_connection",
            return_value=connected,
        ) as create, patch(
            "buoy_search.semantics_local_model.http.client.HTTPConnection",
            self.Connection,
        ):
            result = DirectLoopbackTransport(resolver=loopback_resolver).request(**kwargs)
        return result, create

    def test_pins_validated_numeric_address_and_ignores_proxy_credentials(self) -> None:
        self.Connection.response = self.Response()
        with patch.dict(os.environ, {"HTTP_PROXY": "http://proxy.invalid", "HTTPS_PROXY": "http://proxy.invalid"}):
            result, create = self.request(
                method="POST", url="http://localhost:11434/v1/chat/completions",
                body=b"{}", timeout_seconds=1, maximum_response_bytes=100,
            )
        self.assertEqual(result.body, b"{}")
        self.assertEqual(create.call_args.args[0], ("127.0.0.1", 11434))
        self.assertEqual(self.Connection.last_headers["Host"], "localhost:11434")
        self.assertNotIn("Authorization", self.Connection.last_headers)
        self.assertNotIn("Cookie", self.Connection.last_headers)

    def test_completed_content_length_response_does_not_touch_closed_socket(self) -> None:
        sock = self.Sock()

        class ClosingSocketResponse(self.Response):
            def read1(inner_self, limit: int):
                value = inner_self.read(limit)
                if inner_self._offset == len(inner_self._body):
                    sock.closed = True
                return value

            def isclosed(inner_self):
                return getattr(sock, "closed", False)

        original_settimeout = sock.settimeout

        def fail_if_closed(value: float) -> None:
            if getattr(sock, "closed", False):
                raise OSError(9, "closed socket")
            original_settimeout(value)

        sock.settimeout = fail_if_closed  # type: ignore[method-assign]
        self.Connection.response = ClosingSocketResponse(body=b"{}", length="2")
        result, _ = self.request(
            sock=sock,
            method="GET", url="http://127.0.0.1:11434/v1/models",
            body=None, timeout_seconds=1, maximum_response_bytes=100,
        )
        self.assertEqual(result.body, b"{}")

    def test_https_preserves_loopback_hostname_for_tls_sni(self) -> None:
        self.Connection.response = self.Response()
        context = Mock()
        sock = self.Sock("::1")
        context.wrap_socket.return_value = sock
        with patch(
            "buoy_search.semantics_local_model.socket.create_connection",
            return_value=sock,
        ), patch(
            "buoy_search.semantics_local_model.ssl.create_default_context",
            return_value=context,
        ), patch(
            "buoy_search.semantics_local_model.http.client.HTTPConnection",
            self.Connection,
        ):
            DirectLoopbackTransport(resolver=loopback_resolver).request(
                method="GET", url="https://localhost:8443/v1/models", body=None,
                timeout_seconds=1, maximum_response_bytes=100,
            )
        context.wrap_socket.assert_called_once_with(sock, server_hostname="localhost")
        self.assertEqual(self.Connection.last_headers["Host"], "localhost:8443")

    def test_nonloopback_connected_peer_fails_before_body_transmission(self) -> None:
        secret = b"PRIVATE EVIDENCE PROMPT"
        with patch(
            "buoy_search.semantics_local_model.socket.create_connection",
            return_value=self.Sock("10.0.0.2"),
        ), patch(
            "buoy_search.semantics_local_model.http.client.HTTPConnection",
            self.Connection,
        ):
            with self.assertRaises(LocalModelError) as caught:
                DirectLoopbackTransport(resolver=loopback_resolver).request(
                    method="POST", url="http://localhost:11434/v1/chat/completions",
                    body=secret, timeout_seconds=1, maximum_response_bytes=100,
                )
        self.assertEqual(caught.exception.code, "peer_not_loopback")
        self.assertEqual(self.Connection.request_count, 0)
        self.assertIsNone(self.Connection.last_body)

    def test_response_size_redirect_and_total_deadline_fail_closed(self) -> None:
        self.Connection.response = self.Response(length="101")
        with self.assertRaises(LocalModelError) as caught:
            self.request(
                method="GET", url="http://127.0.0.1:11434/v1/models", body=None,
                timeout_seconds=1, maximum_response_bytes=100,
            )
        self.assertEqual(caught.exception.code, "response_too_large")

        self.Connection.response = self.Response(body=b"x" * 101)
        with self.assertRaises(LocalModelError) as caught:
            self.request(
                method="GET", url="http://127.0.0.1:11434/v1/models", body=None,
                timeout_seconds=1, maximum_response_bytes=100,
            )
        self.assertEqual(caught.exception.code, "response_too_large")

        self.Connection.response = self.Response()
        self.Connection.response.status = 302
        with self.assertRaises(LocalModelError) as caught:
            self.request(
                method="GET", url="http://127.0.0.1:11434/v1/models", body=None,
                timeout_seconds=1, maximum_response_bytes=100,
            )
        self.assertEqual(caught.exception.code, "redirect_prohibited")

        clock = [0.0]

        class SlowBodyResponse(self.Response):
            def read1(inner_self, limit: int):
                value = inner_self.read(1 if inner_self._offset == 0 else limit)
                clock[0] = 2.0
                return value

        self.Connection.response = SlowBodyResponse(body=b"xx")
        with patch(
            "buoy_search.semantics_local_model.time.monotonic",
            side_effect=lambda: clock[0],
        ):
            with self.assertRaises(LocalModelError) as caught:
                self.request(
                    method="GET", url="http://127.0.0.1:11434/v1/models", body=None,
                    timeout_seconds=1, maximum_response_bytes=100,
                )
        self.assertEqual(caught.exception.code, "timeout")

    def test_over_budget_resolution_fails_before_connection_or_send(self) -> None:
        clock = [0.0]

        def slow_resolver(host: str, port: int, **kwargs: object):
            clock[0] = 2.0
            return loopback_resolver(host, port, **kwargs)

        with patch(
            "buoy_search.semantics_local_model.time.monotonic",
            side_effect=lambda: clock[0],
        ), patch(
            "buoy_search.semantics_local_model.socket.create_connection",
        ) as create, patch(
            "buoy_search.semantics_local_model.http.client.HTTPConnection",
            self.Connection,
        ):
            with self.assertRaises(LocalModelError) as caught:
                DirectLoopbackTransport(resolver=slow_resolver).request(
                    method="POST",
                    url="http://localhost:11434/v1/chat/completions",
                    body=b"PRIVATE EVIDENCE PROMPT",
                    timeout_seconds=1,
                    maximum_response_bytes=100,
                )
        self.assertEqual(caught.exception.code, "timeout")
        create.assert_not_called()
        self.assertEqual(self.Connection.request_count, 0)
        self.assertIsNone(self.Connection.last_body)

    def test_over_budget_request_fails_before_response_headers(self) -> None:
        clock = [0.0]
        base = self.Connection

        class SlowRequestConnection(base):
            response_count = 0

            def request(inner_self, method, path, body=None, headers=None):
                super().request(method, path, body=body, headers=headers)
                clock[0] = 2.0

            def getresponse(inner_self):
                type(inner_self).response_count += 1
                return super().getresponse()

        with patch(
            "buoy_search.semantics_local_model.time.monotonic",
            side_effect=lambda: clock[0],
        ), patch(
            "buoy_search.semantics_local_model.socket.create_connection",
            return_value=self.Sock(),
        ), patch(
            "buoy_search.semantics_local_model.http.client.HTTPConnection",
            SlowRequestConnection,
        ):
            with self.assertRaises(LocalModelError) as caught:
                DirectLoopbackTransport(resolver=loopback_resolver).request(
                    method="POST",
                    url="http://localhost:11434/v1/chat/completions",
                    body=b"{}",
                    timeout_seconds=1,
                    maximum_response_bytes=100,
                )
        self.assertEqual(caught.exception.code, "timeout")
        self.assertEqual(SlowRequestConnection.request_count, 1)
        self.assertEqual(SlowRequestConnection.response_count, 0)


if __name__ == "__main__":
    unittest.main()
