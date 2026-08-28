from __future__ import annotations

from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

from buoy_search.retrieval import embedding_worker as worker


class _FakeReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def score(self, query: str, passages: list[str]) -> list[float]:
        self.calls.append((query, list(passages)))
        return [float(index) / 10.0 for index in range(len(passages))]


class _FakeModel:
    def __init__(self, marker: float = 1.0) -> None:
        self.marker = marker
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        vectors: list[list[float]] = []
        for index, _text in enumerate(texts):
            vector = [0.0] * worker.DIMENSIONS
            vector[index % worker.DIMENSIONS] = self.marker
            vectors.append(vector)
        return vectors


class EmbeddingWorkerProtocolTests(unittest.TestCase):
    def test_frame_round_trip_is_canonical_and_length_prefixed(self) -> None:
        left, right = socket.socketpair()
        self.addCleanup(left.close)
        self.addCleanup(right.close)

        worker._send_frame(left, {"z": 1, "a": "value"})
        payload = worker._recv_frame(right)

        self.assertEqual(payload, b'{"a":"value","z":1}')

    def test_frame_rejects_zero_oversized_and_truncated_payloads(self) -> None:
        for payload in (
            struct.pack("!I", 0),
            struct.pack("!I", worker.MAX_FRAME_BYTES + 1),
            struct.pack("!I", 4) + b"x",
        ):
            with self.subTest(payload=payload[:4]):
                left, right = socket.socketpair()
                with left, right:
                    left.sendall(payload)
                    left.shutdown(socket.SHUT_WR)
                    with self.assertRaises(worker._ProtocolError):
                        worker._recv_frame(right)

    def test_request_rejects_unknown_duplicate_identity_and_text_bounds(self) -> None:
        valid = worker._request_value(["query"])
        invalid_payloads = [
            worker._canonical_json(valid | {"extra": True}),
            b'{"schema_version":2,"schema_version":2,"operation":"encode",'
            b'"model":"BAAI/bge-small-en-v1.5",'
            b'"revision":"5c38ec7c405ec4b44b94cc5a9bb96e735b38267a",'
            b'"precision":"float32","texts":["query"]}',
            worker._canonical_json(valid | {"schema_version": True}),
            worker._canonical_json(valid | {"model": "other"}),
            worker._canonical_json(valid | {"texts": []}),
            worker._canonical_json(valid | {"texts": [""]}),
            worker._canonical_json(valid | {"texts": ["x" * (worker.MAX_TEXT_BYTES + 1)]}),
        ]

        for payload in invalid_payloads:
            with self.subTest(payload_bytes=len(payload)):
                with self.assertRaises(worker._ProtocolError):
                    worker._parse_request(payload)

    def test_score_request_is_strict_and_bounded_to_108_passages(self) -> None:
        self.assertEqual(worker.MAX_SCORE_PASSAGES, 108)
        self.assertEqual(worker.MAX_FRAME_BYTES, 8_388_608)
        valid = worker._score_request_value("query", ["one"])
        parsed = worker._parse_request(worker._canonical_json(valid))
        self.assertIsInstance(parsed, worker._ScoreRequest)
        self.assertEqual(parsed.query, "query")
        self.assertEqual(parsed.passages, ["one"])
        boundary = worker._parse_request(
            worker._canonical_json(
                worker._score_request_value(
                    "query", ["passage"] * worker.MAX_SCORE_PASSAGES
                )
            )
        )
        self.assertEqual(len(boundary.passages), 108)

        invalid_payloads = [
            worker._canonical_json(valid | {"extra": True}),
            worker._canonical_json(valid | {"schema_version": True}),
            worker._canonical_json(valid | {"model": "other"}),
            worker._canonical_json(valid | {"revision": "other"}),
            worker._canonical_json(valid | {"query": ""}),
            worker._canonical_json(valid | {"query": "x" * (worker.MAX_TEXT_BYTES + 1)}),
            worker._canonical_json(valid | {"passages": []}),
            worker._canonical_json(valid | {"passages": [""]}),
            worker._canonical_json(
                valid | {"passages": ["p"] * (worker.MAX_SCORE_PASSAGES + 1)}
            ),
            worker._canonical_json(
                valid | {"passages": ["x" * (worker.MAX_TEXT_BYTES + 1)]}
            ),
        ]
        for payload in invalid_payloads:
            with self.subTest(payload_bytes=len(payload)):
                with self.assertRaises(worker._ProtocolError):
                    worker._parse_request(payload)

        oversized = worker._score_request_value(
            "query", ["passage"] * (worker.MAX_SCORE_PASSAGES + 1)
        )
        with self.assertRaises(worker._ProtocolError):
            worker._parse_request(worker._canonical_json(oversized))

        duplicate = (
            b'{"model":"cross-encoder/ms-marco-MiniLM-L-6-v2",'
            b'"operation":"score","passages":["one"],"query":"query",'
            b'"query":"other","revision":'
            b'"c5ee24cb16019beea0893ab7796b1df96625c6b8",'
            b'"schema_version":2}'
        )
        with self.assertRaises(worker._ProtocolError):
            worker._parse_request(duplicate)

    def test_score_client_enforces_inclusive_canonical_frame_limit(self) -> None:
        query = "bounded query"
        passages = ["bounded passage"] * worker.MAX_SCORE_PASSAGES
        request_size = len(
            worker._canonical_json(worker._score_request_value(query, passages))
        )
        with patch.object(worker, "MAX_FRAME_BYTES", request_size):
            self.assertEqual(
                worker._validate_score_input(query, passages),
                (query, passages),
            )
        with patch.object(worker, "MAX_FRAME_BYTES", request_size - 1):
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker._validate_score_input(query, passages)
        self.assertEqual(raised.exception.error_type, "protocol_error")

    def test_score_response_requires_exact_identity_count_and_finite_values(self) -> None:
        valid = {
            "schema_version": worker.SCHEMA_VERSION,
            "outcome": "success",
            "model": worker.RERANKER_MODEL,
            "revision": worker.RERANKER_REVISION,
            "scores": [0.25, -1.5],
        }
        self.assertEqual(
            worker._parse_score_response(worker._canonical_json(valid), 2),
            [0.25, -1.5],
        )
        invalid_values = [
            valid | {"extra": 1},
            valid | {"schema_version": True},
            valid | {"model": "other"},
            valid | {"revision": "other"},
            valid | {"scores": [0.25]},
            valid | {"scores": [True, 0.5]},
            valid | {"scores": [float("nan"), 0.5]},
        ]
        for value in invalid_values:
            with self.subTest(keys=sorted(value)):
                with self.assertRaises((worker._ProtocolError, ValueError)):
                    worker._parse_score_response(worker._canonical_json(value), 2)

    def test_score_client_validates_before_creating_worker_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as temporary:
            home = Path(temporary) / ".buoy"
            for query, passages in (
                ("", ["one"]),
                ("query", []),
                ("query", ["p"] * 109),
                ("query", [""]),
            ):
                with self.subTest(query=query, count=len(passages)):
                    with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                        worker.score(query, passages, buoy_home=home)
                    self.assertEqual(raised.exception.error_type, "protocol_error")
                    self.assertFalse(home.exists())

    def test_response_validates_exact_fields_dimensions_finiteness_and_normalization(self) -> None:
        vector = [0.0] * worker.DIMENSIONS
        vector[0] = 1.0
        valid = {
            "schema_version": worker.SCHEMA_VERSION,
            "outcome": "success",
            "dimensions": worker.DIMENSIONS,
            "vectors": [vector],
        }
        self.assertEqual(worker._parse_response(worker._canonical_json(valid), 1), [vector])

        invalid_values = [
            valid | {"extra": 1},
            valid | {"dimensions": True},
            valid | {"vectors": [[]]},
            valid | {"vectors": [[float("nan")] + vector[1:]]},
            valid | {"vectors": [[0.5] + vector[1:]]},
            valid | {"vectors": [[True] + vector[1:]]},
        ]
        for value in invalid_values:
            with self.subTest(keys=sorted(value)):
                with self.assertRaises((worker._ProtocolError, ValueError)):
                    worker._parse_response(worker._canonical_json(value), 1)

    def test_error_response_allows_only_bounded_categories(self) -> None:
        for category in worker._ERROR_TYPES:
            payload = worker._canonical_json(worker._error_response(category))
            with self.subTest(category=category):
                with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                    worker._parse_response(payload, 1)
                self.assertEqual(raised.exception.error_type, category)
        with self.assertRaises(worker._ProtocolError):
            worker._parse_response(
                worker._canonical_json(
                    {
                        "schema_version": worker.SCHEMA_VERSION,
                        "outcome": "error",
                        "error_type": "raw detail",
                    }
                ),
                1,
            )

    def test_ready_identity_binds_protocol_v2_and_exact_reranker(self) -> None:
        ready = worker._ready_response()
        worker._validate_ready(dict(ready))
        self.assertEqual(worker.SCHEMA_VERSION, 2)
        self.assertEqual(ready["reranker_model"], worker.RERANKER_MODEL)
        self.assertEqual(ready["reranker_revision"], worker.RERANKER_REVISION)
        self.assertEqual(ready["reranker_device"], "cpu")
        self.assertEqual(ready["reranker_max_length"], 512)
        self.assertEqual(ready["reranker_batch_size"], 8)
        self.assertTrue(ready["reranker_local_files_only"])
        self.assertTrue(ready["reranker_use_safetensors"])
        self.assertFalse(ready["reranker_trust_remote_code"])
        self.assertTrue(
            worker.worker_paths(Path.home()).identity_directory.name.startswith("v2-")
        )

        for invalid in (
            ready | {"schema_version": 1},
            ready | {"reranker_revision": "old"},
            {key: value for key, value in ready.items() if key != "reranker_model"},
        ):
            with self.assertRaises(worker._Incompatible):
                worker._validate_ready(invalid)

    def test_peer_credentials_reject_another_user_and_allow_unavailable_api(self) -> None:
        connection = Mock()
        with patch.object(worker, "_peer_uid", return_value=os.geteuid() + 1):
            with self.assertRaises(worker._ProtocolError):
                worker._verify_peer(connection)
        with patch.object(worker, "_peer_uid", return_value=None):
            worker._verify_peer(connection)

    def test_client_validates_before_creating_paths_or_spawning(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as temporary:
            home = Path(temporary) / ".buoy"
            for texts in ([], [""], ["x" * (worker.MAX_TEXT_BYTES + 1)]):
                with self.subTest(count=len(texts)):
                    with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                        worker.encode(texts, buoy_home=home)
                    self.assertEqual(raised.exception.error_type, "protocol_error")
                    self.assertFalse(home.exists())


@unittest.skipUnless(os.name == "posix", "POSIX worker prototype")
class EmbeddingWorkerLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(
            prefix="buoy-embedding-worker-", dir=Path.home()
        )
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name) / ".buoy"
        self.paths = worker.worker_paths(self.home)
        self.threads: list[threading.Thread] = []

    def tearDown(self) -> None:
        for thread in self.threads:
            thread.join(timeout=3)

    def start_fake_worker(
        self,
        *,
        model: _FakeModel | None = None,
        idle: float = 0.15,
        loader: object | None = None,
        reranker: _FakeReranker | None = None,
        reranker_loader: object | None = None,
    ) -> threading.Thread:
        selected_model = model or _FakeModel()
        selected_reranker = reranker or _FakeReranker()
        model_loader = loader if loader is not None else (lambda: selected_model)
        selected_reranker_loader = (
            reranker_loader
            if reranker_loader is not None
            else (lambda: selected_reranker)
        )
        thread = threading.Thread(
            target=worker.run_worker,
            args=(self.paths,),
            kwargs={
                "model_loader": model_loader,
                "reranker_loader": selected_reranker_loader,
                "idle_seconds": idle,
            },
            daemon=True,
        )
        thread.start()
        self.threads.append(thread)
        return thread

    def wait_for_socket(self) -> None:
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            if self.paths.socket_path.exists():
                return
            time.sleep(0.005)
        self.fail("worker socket did not become ready")

    def test_explicit_encode_spawns_once_reuses_worker_and_returns_vectors(self) -> None:
        model = _FakeModel()
        spawn_count = 0

        def spawn(_paths: worker.WorkerPaths) -> None:
            nonlocal spawn_count
            spawn_count += 1
            self.start_fake_worker(model=model)

        with patch.object(worker, "_spawn_worker", side_effect=spawn):
            first = worker.encode(["first"], buoy_home=self.home)
            second = worker.encode(["second"], buoy_home=self.home)

        self.assertEqual(spawn_count, 1)
        self.assertEqual(first[0][0], 1.0)
        self.assertEqual(second[0][0], 1.0)
        self.assertEqual(model.calls, [["first"], ["second"]])
        state = worker.read_worker_state(buoy_home=self.home)
        self.assertEqual(state["phase"], "ready")
        self.assertEqual(state["model"], worker.MODEL)

    def test_score_lazily_loads_once_and_reuses_resident_reranker(self) -> None:
        reranker = _FakeReranker()
        loads = 0

        def load_reranker() -> _FakeReranker:
            nonlocal loads
            loads += 1
            return reranker

        def spawn(_paths: worker.WorkerPaths) -> None:
            self.start_fake_worker(reranker_loader=load_reranker, idle=0.3)

        with patch.object(worker, "_spawn_worker", side_effect=spawn):
            worker.encode(["embedding only"], buoy_home=self.home)
            self.assertEqual(loads, 0)
            first = worker.score("query", ["one", "two"], buoy_home=self.home)
            second = worker.score("query two", ["three"], buoy_home=self.home)

        self.assertEqual(loads, 1)
        self.assertEqual(first, [0.0, 0.1])
        self.assertEqual(second, [0.0])
        self.assertEqual(
            reranker.calls,
            [("query", ["one", "two"]), ("query two", ["three"])],
        )
        state = worker.read_worker_state(buoy_home=self.home)
        self.assertEqual(state["reranker_model"], worker.RERANKER_MODEL)
        self.assertNotIn("query", state)
        self.assertNotIn("passages", state)
        self.assertNotIn("scores", state)

    def test_lazy_reranker_load_and_scoring_failures_are_bounded(self) -> None:
        def failed_loader() -> object:
            raise RuntimeError("private reranker path")

        with patch.object(
            worker,
            "_spawn_worker",
            side_effect=lambda _paths: self.start_fake_worker(
                reranker_loader=failed_loader,
                idle=0.3,
            ),
        ):
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.score("private query", ["private passage"], buoy_home=self.home)
        self.assertEqual(raised.exception.error_type, "model_unavailable")
        self.assertNotIn("private", str(raised.exception))
        self.threads[-1].join(timeout=1)

        class FailingReranker:
            def score(self, _query: str, _passages: list[str]) -> list[float]:
                raise RuntimeError("private score detail")

        self.start_fake_worker(
            reranker_loader=lambda: FailingReranker(),
            idle=0.3,
        )
        self.wait_for_socket()
        with self.assertRaises(worker.EmbeddingWorkerError) as score_failure:
            worker.score("query", ["passage"], buoy_home=self.home)
        self.assertEqual(score_failure.exception.error_type, "scoring_failure")
        self.assertNotIn("private", str(score_failure.exception))

    def test_concurrent_first_clients_coalesce_on_one_worker(self) -> None:
        model = _FakeModel()
        spawn_count = 0
        spawn_guard = threading.Lock()
        barrier = threading.Barrier(5)
        results: list[list[list[float]]] = []
        failures: list[Exception] = []

        def spawn(_paths: worker.WorkerPaths) -> None:
            nonlocal spawn_count
            with spawn_guard:
                spawn_count += 1
            self.start_fake_worker(model=model, idle=0.3)

        def call(index: int) -> None:
            try:
                barrier.wait()
                results.append(worker.encode([f"query-{index}"], buoy_home=self.home))
            except Exception as exc:  # pragma: no cover - assertion reports failures.
                failures.append(exc)

        with patch.object(worker, "_spawn_worker", side_effect=spawn):
            clients = [threading.Thread(target=call, args=(index,)) for index in range(5)]
            for client in clients:
                client.start()
            for client in clients:
                client.join(timeout=3)

        self.assertEqual(failures, [])
        self.assertEqual(len(results), 5)
        self.assertEqual(spawn_count, 1)
        self.assertEqual(len(model.calls), 5)

    def test_stale_owned_socket_is_removed_only_under_lifetime_authority(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(os.fspath(self.paths.socket_path))
        self.paths.socket_path.chmod(0o600)
        stale.close()
        os.close(directory_fd)

        with patch.object(
            worker,
            "_spawn_worker",
            side_effect=lambda _paths: self.start_fake_worker(),
        ):
            values = worker.encode(["query"], buoy_home=self.home)

        self.assertEqual(values[0][0], 1.0)

    def test_hardlinked_socket_cleanup_fails_without_deleting_either_link(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(os.fspath(self.paths.socket_path))
        self.paths.socket_path.chmod(0o600)
        sibling = self.paths.identity_directory / "linked.sock"
        os.link(self.paths.socket_path, sibling)
        try:
            with worker._lock(
                directory_fd, "lifetime.lock", timeout_seconds=0.0
            ):
                with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                    worker._clear_stale_runtime(directory_fd)
            self.assertEqual(
                raised.exception.error_type, "internal_worker_failure"
            )
            self.assertTrue(self.paths.socket_path.exists())
            self.assertTrue(sibling.exists())
            self.assertEqual(self.paths.socket_path.stat().st_nlink, 2)
            self.assertEqual(sibling.stat().st_nlink, 2)
        finally:
            stale.close()
            if self.paths.socket_path.exists():
                self.paths.socket_path.unlink()
            if sibling.exists():
                sibling.unlink()
            os.close(directory_fd)

    def test_hostile_socket_regular_file_fails_without_spawn_or_deletion(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        os.close(directory_fd)
        self.paths.socket_path.write_text("not a socket", encoding="utf-8")
        self.paths.socket_path.chmod(0o600)

        with patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError):
                worker.encode(["private query"], buoy_home=self.home)

        spawn.assert_not_called()
        self.assertEqual(self.paths.socket_path.read_text(encoding="utf-8"), "not a socket")

    def test_symlink_and_wrong_mode_boundaries_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as other:
            target = Path(other) / "target"
            target.mkdir(mode=0o700)
            self.home.symlink_to(target, target_is_directory=True)
            with patch.object(worker, "_spawn_worker") as spawn:
                with self.assertRaises(worker.EmbeddingWorkerError):
                    worker.encode(["query"], buoy_home=self.home)
                spawn.assert_not_called()

        if self.home.exists() or self.home.is_symlink():
            self.home.unlink()
        self.home.mkdir(mode=0o755)
        with self.assertRaises(worker.EmbeddingWorkerError):
            worker.encode(["query"], buoy_home=self.home)

    def test_interrupted_state_publication_is_recovered_under_lifetime_lock(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        payload = worker._canonical_json(
            worker._state_value(
                phase="error", pid=os.getpid(), error_type="model_unavailable"
            )
        )
        descriptor = os.open(
            "ready.tmp",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
            dir_fd=directory_fd,
        )
        os.write(descriptor, payload)
        os.close(descriptor)
        os.link(
            "ready.tmp",
            "ready.json",
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
        )

        with worker._lock(directory_fd, "lifetime.lock", timeout_seconds=0.0):
            worker._clear_stale_runtime(directory_fd)

        self.assertFalse((self.paths.identity_directory / "ready.tmp").exists())
        self.assertFalse(self.paths.ready_path.exists())
        os.close(directory_fd)

    def test_overlong_socket_path_fails_before_filesystem_or_spawn(self) -> None:
        long_home = Path(self.temporary.name) / ("x" * 110) / ".buoy"
        with patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError):
                worker.encode(["query"], buoy_home=long_home)
        spawn.assert_not_called()
        self.assertFalse(long_home.exists())

    def test_hardlinked_lock_fails_closed(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        os.close(directory_fd)
        self.paths.start_lock_path.write_bytes(b"")
        self.paths.start_lock_path.chmod(0o600)
        sibling = self.paths.identity_directory / "linked.lock"
        os.link(self.paths.start_lock_path, sibling)

        with patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError):
                worker.encode(["query"], buoy_home=self.home)
        spawn.assert_not_called()

    def test_incompatible_ready_worker_fails_without_sending_query_or_spawning(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        os.close(directory_fd)
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(os.fspath(self.paths.socket_path))
        self.paths.socket_path.chmod(0o600)
        server.listen(1)
        received: list[bytes] = []

        def serve_incompatible() -> None:
            connection, _address = server.accept()
            with connection:
                worker._send_frame(
                    connection,
                    worker._ready_response() | {"implementation_id": "other"},
                )
                connection.settimeout(0.2)
                try:
                    received.append(connection.recv(1))
                except socket.timeout:
                    received.append(b"")
            server.close()

        thread = threading.Thread(target=serve_incompatible, daemon=True)
        thread.start()
        self.threads.append(thread)
        with patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.encode(["must-not-send"], buoy_home=self.home)

        self.assertEqual(raised.exception.error_type, "incompatible_worker")
        spawn.assert_not_called()
        thread.join(timeout=1)
        self.assertEqual(received, [b""])

    def test_model_failure_is_visible_and_never_falls_back(self) -> None:
        def failed_loader() -> object:
            raise RuntimeError("sensitive raw model error")

        with patch.object(
            worker,
            "_spawn_worker",
            side_effect=lambda _paths: self.start_fake_worker(loader=failed_loader),
        ):
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.encode(["private query"], buoy_home=self.home)

        self.assertEqual(raised.exception.error_type, "model_unavailable")
        self.assertNotIn("sensitive", str(raised.exception))

    def test_transport_races_are_bounded_before_and_after_request(self) -> None:
        cases = (
            ("greeting_reset", worker._Unavailable, None),
            ("response_timeout", worker.EmbeddingWorkerError, "busy_timeout"),
            ("response_truncated", worker.EmbeddingWorkerError, "protocol_error"),
        )
        for name, exception_type, category in cases:
            with self.subTest(name=name):
                paths = worker.worker_paths(self.home)
                directory_fd = worker._prepare_identity_directory(paths)
                os.close(directory_fd)
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(os.fspath(paths.socket_path))
                paths.socket_path.chmod(0o600)
                server.listen(1)
                failures: list[Exception] = []

                def serve() -> None:
                    try:
                        connection, _address = server.accept()
                        with connection:
                            if name == "greeting_reset":
                                return
                            worker._send_frame(connection, worker._ready_response())
                            worker._recv_frame(connection)
                            if name == "response_timeout":
                                time.sleep(0.05)
                            else:
                                connection.sendall(struct.pack("!I", 10) + b"{}")
                    except Exception as exc:  # pragma: no cover - assertion reports it.
                        failures.append(exc)
                    finally:
                        server.close()

                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                with self.assertRaises(exception_type) as raised:
                    worker._connect_and_encode(
                        paths,
                        ["must-not-replay"],
                        timeout_seconds=0.01,
                    )
                if category is not None:
                    self.assertEqual(raised.exception.error_type, category)
                thread.join(timeout=1)
                self.assertEqual(failures, [])
                if paths.socket_path.exists():
                    paths.socket_path.unlink()

    def test_score_response_timeout_and_truncation_are_bounded(self) -> None:
        for behavior, category in (
            ("timeout", "busy_timeout"),
            ("truncated", "protocol_error"),
        ):
            with self.subTest(behavior=behavior):
                paths = worker.worker_paths(self.home)
                directory_fd = worker._prepare_identity_directory(paths)
                os.close(directory_fd)
                server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                server.bind(os.fspath(paths.socket_path))
                paths.socket_path.chmod(0o600)
                server.listen(1)
                received: list[worker._Request] = []

                def serve() -> None:
                    connection, _address = server.accept()
                    try:
                        with connection:
                            worker._send_frame(connection, worker._ready_response())
                            received.append(
                                worker._parse_request(worker._recv_frame(connection))
                            )
                            if behavior == "timeout":
                                time.sleep(0.05)
                            else:
                                connection.sendall(struct.pack("!I", 10) + b"{}")
                    finally:
                        server.close()

                thread = threading.Thread(target=serve, daemon=True)
                thread.start()
                with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                    worker._connect_and_score(
                        paths,
                        "must-not-replay",
                        ["passage"],
                        timeout_seconds=0.01,
                    )
                self.assertEqual(raised.exception.error_type, category)
                thread.join(timeout=1)
                self.assertEqual(len(received), 1)
                self.assertIsInstance(received[0], worker._ScoreRequest)
                if paths.socket_path.exists():
                    paths.socket_path.unlink()

    def test_post_request_score_transport_failure_is_not_replayed(self) -> None:
        with patch.object(
            worker,
            "_connect_and_score",
            side_effect=worker.EmbeddingWorkerError("busy_timeout"),
        ) as connect, patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.score("query", ["passage"], buoy_home=self.home)
        self.assertEqual(raised.exception.error_type, "busy_timeout")
        self.assertEqual(connect.call_count, 1)
        spawn.assert_not_called()

    def test_post_request_transport_failure_is_visible_without_fallback(self) -> None:
        with patch.object(
            worker,
            "_connect_and_encode",
            side_effect=worker.EmbeddingWorkerError("busy_timeout"),
        ), patch.object(worker, "_spawn_worker") as spawn:
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.encode(["must-not-replay"], buoy_home=self.home)
        self.assertEqual(raised.exception.error_type, "busy_timeout")
        spawn.assert_not_called()

    def test_shutdown_closes_and_cleans_before_releasing_lifetime_authority(self) -> None:
        real_bind = worker._bind_server
        real_unlink = worker._safe_unlink_socket
        closed = False
        cleanup_observed = False

        class ObservedServer:
            def __init__(self, wrapped: socket.socket) -> None:
                self.wrapped = wrapped

            def settimeout(self, value: float) -> None:
                self.wrapped.settimeout(value)

            def accept(self):
                return self.wrapped.accept()

            def close(self) -> None:
                nonlocal closed
                self.wrapped.close()
                closed = True

        def bind(paths: worker.WorkerPaths, directory_fd: int):
            server, observed = real_bind(paths, directory_fd)
            return ObservedServer(server), observed

        def unlink(directory_fd: int, *, expected: tuple[int, int] | None) -> None:
            nonlocal cleanup_observed
            self.assertTrue(closed)
            probe_fd = worker._prepare_identity_directory(self.paths)
            try:
                with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                    with worker._lock(
                        probe_fd, "lifetime.lock", timeout_seconds=0.0
                    ):
                        pass
                self.assertEqual(raised.exception.error_type, "busy_timeout")
            finally:
                os.close(probe_fd)
            cleanup_observed = True
            real_unlink(directory_fd, expected=expected)

        clock = iter((0.0, 301.0))
        with patch.object(worker, "_bind_server", side_effect=bind), patch.object(
            worker, "_safe_unlink_socket", side_effect=unlink
        ):
            result = worker.run_worker(
                self.paths,
                model_loader=_FakeModel,
                idle_seconds=worker.IDLE_EXIT_SECONDS,
                monotonic=lambda: next(clock),
            )

        self.assertEqual(result, 0)
        self.assertTrue(cleanup_observed)
        directory_fd = worker._prepare_identity_directory(self.paths)
        try:
            with worker._lock(directory_fd, "lifetime.lock", timeout_seconds=0.0):
                pass
        finally:
            os.close(directory_fd)

    def test_disconnect_does_not_stop_or_replay_worker(self) -> None:
        model = _FakeModel()
        self.start_fake_worker(model=model, idle=0.3)
        self.wait_for_socket()
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.connect(os.fspath(self.paths.socket_path))
        worker._recv_frame(connection)
        connection.close()

        values = worker._connect_and_encode(self.paths, ["next"], timeout_seconds=1)

        self.assertEqual(values[0][0], 1.0)
        self.assertEqual(model.calls, [["next"]])

    def test_invalid_connections_do_not_reset_idle_clock(self) -> None:
        for behavior in ("handshake_only", "malformed", "disconnected"):
            with self.subTest(behavior=behavior):
                failures: list[Exception] = []

                def connect() -> None:
                    try:
                        deadline = time.monotonic() + 2
                        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        while True:
                            try:
                                connection.connect(os.fspath(self.paths.socket_path))
                                break
                            except (FileNotFoundError, ConnectionRefusedError):
                                if time.monotonic() >= deadline:
                                    raise
                                time.sleep(0.005)
                        with connection:
                            if behavior == "disconnected":
                                return
                            worker._recv_frame(connection)
                            if behavior == "malformed":
                                worker._send_frame(connection, {"invalid": True})
                                worker._recv_frame(connection)
                    except Exception as exc:  # pragma: no cover - assertion reports it.
                        failures.append(exc)

                client = threading.Thread(target=connect, daemon=True)
                client.start()
                model = _FakeModel()
                clock = iter((0.0, 1.0, 301.0))
                result = worker.run_worker(
                    self.paths,
                    model_loader=lambda: model,
                    idle_seconds=worker.IDLE_EXIT_SECONDS,
                    monotonic=lambda: next(clock),
                )
                client.join(timeout=2)

                self.assertEqual(result, 0)
                self.assertEqual(failures, [])
                self.assertEqual(model.calls, [])
                self.assertFalse(self.paths.socket_path.exists())
                self.assertFalse(self.paths.ready_path.exists())

    def test_valid_score_request_resets_idle_clock(self) -> None:
        reranker = _FakeReranker()
        result_values: list[list[float]] = []
        failures: list[Exception] = []

        def connect() -> None:
            try:
                deadline = time.monotonic() + 2
                while True:
                    try:
                        values = worker._connect_and_score(
                            self.paths,
                            "query",
                            ["one", "two"],
                            timeout_seconds=1,
                        )
                        result_values.append(values)
                        return
                    except worker._Unavailable:
                        if time.monotonic() >= deadline:
                            raise
                        time.sleep(0.005)
            except Exception as exc:  # pragma: no cover - assertion reports it.
                failures.append(exc)

        client = threading.Thread(target=connect, daemon=True)
        client.start()
        clock = iter((0.0, 1.0, 2.0, 303.0))
        result = worker.run_worker(
            self.paths,
            model_loader=_FakeModel,
            reranker_loader=lambda: reranker,
            idle_seconds=worker.IDLE_EXIT_SECONDS,
            monotonic=lambda: next(clock),
        )
        client.join(timeout=2)

        self.assertEqual(result, 0)
        self.assertEqual(failures, [])
        self.assertEqual(result_values, [[0.0, 0.1]])
        self.assertEqual(reranker.calls, [("query", ["one", "two"])])
        self.assertFalse(self.paths.socket_path.exists())
        self.assertFalse(self.paths.ready_path.exists())

    def test_idle_exit_uses_300_second_contract_with_fake_clock(self) -> None:
        values = iter((0.0, 301.0))
        result = worker.run_worker(
            self.paths,
            model_loader=_FakeModel,
            idle_seconds=worker.IDLE_EXIT_SECONDS,
            monotonic=lambda: next(values),
        )

        self.assertEqual(result, 0)
        self.assertFalse(self.paths.socket_path.exists())
        self.assertFalse(self.paths.ready_path.exists())
        self.assertEqual(worker.IDLE_EXIT_SECONDS, 300.0)

    def test_worker_serves_serialized_requests(self) -> None:
        active = 0
        maximum = 0
        lock = threading.Lock()

        class ObservedModel(_FakeModel):
            def encode(self, texts: list[str]) -> list[list[float]]:
                nonlocal active, maximum
                with lock:
                    active += 1
                    maximum = max(maximum, active)
                time.sleep(0.02)
                try:
                    return super().encode(texts)
                finally:
                    with lock:
                        active -= 1

        self.start_fake_worker(model=ObservedModel(), idle=0.3)
        self.wait_for_socket()
        calls = [
            threading.Thread(
                target=worker._connect_and_encode,
                args=(self.paths, [f"q-{index}"]),
                kwargs={"timeout_seconds": 1},
            )
            for index in range(3)
        ]
        for call in calls:
            call.start()
        for call in calls:
            call.join(timeout=2)
        self.assertEqual(maximum, 1)

    def test_spawn_is_detached_offline_and_has_no_credentials(self) -> None:
        directory_fd = worker._prepare_identity_directory(self.paths)
        os.close(directory_fd)
        process = Mock()
        with patch.object(worker.subprocess, "Popen", return_value=process) as popen:
            worker._spawn_worker(self.paths)

        args, kwargs = popen.call_args
        self.assertEqual(
            args[0],
            [
                os.path.abspath(sys.executable),
                "-I",
                "-X",
                "utf8",
                "-m",
                "buoy_search.retrieval.embedding_worker",
            ],
        )
        self.assertEqual(kwargs["cwd"], os.fspath(self.paths.identity_directory))
        self.assertEqual(kwargs["env"], worker._minimal_worker_environment())
        self.assertNotIn("TURBOPUFFER_API_KEY", kwargs["env"])
        self.assertEqual(kwargs["env"]["HF_HUB_OFFLINE"], "1")
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.DEVNULL)
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)
        self.assertTrue(kwargs["close_fds"])
        self.assertTrue(kwargs["start_new_session"])
        self.assertFalse(kwargs["shell"])

    def test_spawn_oserror_is_bounded_without_query_or_fallback(self) -> None:
        raw_message = "sensitive executable failure"
        with patch.object(
            worker, "_connect_and_encode", side_effect=worker._Unavailable
        ) as connect, patch.object(
            worker.subprocess, "Popen", side_effect=OSError(raw_message)
        ), patch.object(worker, "_LocalModel") as fallback:
            with self.assertRaises(worker.EmbeddingWorkerError) as raised:
                worker.encode(["private query"], buoy_home=self.home)

        self.assertEqual(raised.exception.error_type, "internal_worker_failure")
        self.assertNotIn(raw_message, str(raised.exception))
        self.assertEqual(connect.call_count, 2)
        fallback.assert_not_called()
        self.assertFalse(self.paths.socket_path.exists())
        self.assertFalse(self.paths.ready_path.exists())
        for path in self.paths.identity_directory.iterdir():
            if path.is_file():
                self.assertNotIn(b"private query", path.read_bytes())

    def test_local_model_is_exact_revision_local_only_and_normalized(self) -> None:
        encoded = Mock()
        encoded.tolist.return_value = [1.0] + [0.0] * (worker.DIMENSIONS - 1)
        model = Mock()
        model.encode.return_value = [encoded]
        constructor = Mock(return_value=model)
        fake_module = Mock(SentenceTransformer=constructor)

        with patch.dict(sys.modules, {"sentence_transformers": fake_module}):
            selected = worker._LocalModel()
            values = selected.encode(["query"])

        constructor.assert_called_once_with(
            worker.MODEL,
            revision=worker.REVISION,
            local_files_only=True,
        )
        model.encode.assert_called_once_with(
            ["query"],
            batch_size=32,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        self.assertEqual(values[0][0], 1.0)

    def test_private_runtime_contains_no_score_request_or_response_payload(self) -> None:
        query = "private-score-query-sentinel"
        passage = "private-score-passage-sentinel"
        score_sentinel = "0.1"
        with patch.object(
            worker,
            "_spawn_worker",
            side_effect=lambda _paths: self.start_fake_worker(idle=0.3),
        ):
            worker.score(query, [passage, "other"], buoy_home=self.home)

        for path in self.paths.identity_directory.iterdir():
            if path.is_file():
                payload = path.read_bytes()
                self.assertNotIn(query.encode(), payload)
                self.assertNotIn(passage.encode(), payload)
                self.assertNotIn(score_sentinel.encode(), payload)
        state = worker.read_worker_state(buoy_home=self.home)
        self.assertNotIn("query", state)
        self.assertNotIn("passages", state)
        self.assertNotIn("scores", state)

    def test_private_runtime_contains_no_query_or_vector_payload(self) -> None:
        query = "private-query-sentinel"
        vector_sentinel = "0.123456789"
        with patch.object(
            worker,
            "_spawn_worker",
            side_effect=lambda _paths: self.start_fake_worker(),
        ):
            worker.encode([query], buoy_home=self.home)

        for path in self.paths.identity_directory.iterdir():
            if path.is_file():
                payload = path.read_bytes()
                self.assertNotIn(query.encode(), payload)
                self.assertNotIn(vector_sentinel.encode(), payload)
        state = worker.read_worker_state(buoy_home=self.home)
        self.assertNotIn("texts", state)
        self.assertNotIn("vectors", state)


class ExperimentalRetrieveWorkerHarnessTests(unittest.TestCase):
    def test_historical_live_harness_is_retired_before_subprocess_work(self) -> None:
        from tests.fixtures import experimental_retrieve_worker_ab as harness

        with patch.dict(
            os.environ, {"TURBOPUFFER_API_KEY": "must-not-be-read"}, clear=True
        ), patch.object(
            harness.subprocess,
            "run",
            side_effect=AssertionError("live command attempted"),
        ), self.assertRaisesRegex(RuntimeError, "zero live commands authorized"):
            harness.main()

    def test_run_retains_only_redacted_comparison_values(self) -> None:
        from tests.fixtures import experimental_retrieve_worker_ab as harness

        secret = "private-provider-result-sentinel"
        payload = {
            "routing": {"selected_cards": [{"namespace": secret}]},
            "namespaces": [secret],
            "hits": [{"content": secret}],
        }

        def run_command(_command: object, **kwargs: object) -> Mock:
            kwargs["stdout"].write(json.dumps(payload).encode("utf-8"))
            return Mock(returncode=0)

        with tempfile.TemporaryDirectory() as temporary, patch.object(
            harness.subprocess, "run", side_effect=run_command
        ):
            root = Path(temporary)
            retained = harness._run_one(
                "baseline",
                (),
                root=root,
                environment={},
            )

            self.assertNotIn(secret, json.dumps(retained, sort_keys=True))
            self.assertNotIn("payload", retained)
            self.assertNotIn("route", retained)
            self.assertIn("payload_sha256", retained)
            self.assertIn("route_sha256", retained)
            self.assertFalse((root / "baseline.stdout").exists())
            self.assertFalse((root / "baseline.stderr").exists())


class CrossEncoderWorkerLiveABHarnessTests(unittest.TestCase):
    def test_successor_contract_has_exact_query_order_and_three_commands(self) -> None:
        from tests.fixtures import cross_encoder_worker_live_ab as harness

        self.assertEqual(
            harness.QUERY,
            "How is approximate vector recall evaluated?",
        )
        self.assertEqual(
            harness.COMMANDS,
            (
                ("baseline", ("--no-embedding-worker",)),
                ("cold_worker", ()),
                ("warm_worker", ()),
            ),
        )

    def test_provider_free_self_test_redacts_and_cleans_synthetic_content(self) -> None:
        from tests.fixtures import cross_encoder_worker_live_ab as harness

        result = harness._provider_free_self_test()

        self.assertTrue(result["passed"])
        self.assertTrue(result["redaction_passed"])
        self.assertTrue(result["raw_cleanup_passed"])
        self.assertEqual(result["exact_command_count"], 3)
        self.assertNotIn("provider-derived-self-test-sentinel", json.dumps(result))

    def test_consumed_live_authority_stops_before_credential_or_subprocess_work(self) -> None:
        from tests.fixtures import cross_encoder_worker_live_ab as harness

        with patch.dict(
            os.environ, {"TURBOPUFFER_API_KEY": "must-not-be-read"}, clear=True
        ), patch.object(
            harness,
            "_run_and_reduce",
            side_effect=AssertionError("live or synthetic subprocess attempted"),
        ), self.assertRaisesRegex(RuntimeError, "authority is consumed"):
            harness.main(["--execute-live"])


class EmbeddingWorkerDormancyTests(unittest.TestCase):
    def test_cli_module_import_does_not_import_worker_backend(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                "import sys; import buoy_search.cli.main; "
                "assert 'buoy_search.retrieval.embedding_worker' not in sys.modules",
            ],
            env={"PYTHONDONTWRITEBYTECODE": "1"},
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())

    def test_cli_import_under_isolated_home_creates_no_worker_state(self) -> None:
        with tempfile.TemporaryDirectory(dir=Path.home()) as temporary:
            isolated_home = Path(temporary)
            environment = {
                "HOME": os.fspath(isolated_home),
                "HF_HUB_OFFLINE": "1",
                "OTEL_SDK_DISABLED": "true",
                "PYTHONDONTWRITEBYTECODE": "1",
                "TRANSFORMERS_OFFLINE": "1",
            }
            completed = subprocess.run(
                [sys.executable, "-I", "-c", "import buoy_search.cli.main"],
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr.decode())
            self.assertFalse((isolated_home / ".buoy").exists())


if __name__ == "__main__":
    unittest.main()
