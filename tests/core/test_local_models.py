from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

from buoy_search.local_models import (
    BGE_MODEL,
    BGE_REVISION,
    LocalModelError,
    configure_local_runtime,
    load_sentence_transformer,
    model_thread_count,
    resolved_device,
)


class LocalModelRuntimeTests(unittest.TestCase):
    def test_module_import_does_not_import_model_frameworks(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-c",
                (
                    "import sys; import buoy_search.local_models; "
                    "assert 'torch' not in sys.modules; "
                    "assert 'sentence_transformers' not in sys.modules"
                ),
            ],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            check=False,
            timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr.decode())

    def test_configuration_forces_offline_non_telemetric_environment(self) -> None:
        with patch.dict(
            os.environ,
            {
                "HF_HUB_OFFLINE": "0",
                "TRANSFORMERS_OFFLINE": "0",
                "HF_HUB_DISABLE_TELEMETRY": "0",
                "DO_NOT_TRACK": "0",
                "TOKENIZERS_PARALLELISM": "true",
            },
            clear=True,
        ):
            configure_local_runtime()
            self.assertEqual(os.environ["HF_HUB_OFFLINE"], "1")
            self.assertEqual(os.environ["TRANSFORMERS_OFFLINE"], "1")
            self.assertEqual(os.environ["HF_HUB_DISABLE_TELEMETRY"], "1")
            self.assertEqual(os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"], "1")
            self.assertEqual(os.environ["DO_NOT_TRACK"], "1")
            self.assertEqual(os.environ["TOKENIZERS_PARALLELISM"], "false")

    def test_device_defaults_to_cpu_and_allows_explicit_override(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(resolved_device(), "cpu")
        with patch.dict(os.environ, {"BUOY_DEVICE": "cuda:0"}, clear=True):
            self.assertEqual(resolved_device(), "cuda:0")
        with (
            patch.dict(os.environ, {"BUOY_DEVICE": "  "}, clear=True),
            self.assertRaisesRegex(LocalModelError, "BUOY_DEVICE"),
        ):
            resolved_device()

    def test_thread_count_defaults_to_four_and_rejects_invalid_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(model_thread_count(), 4)
        with patch.dict(os.environ, {"BUOY_MODEL_THREADS": "7"}, clear=True):
            self.assertEqual(model_thread_count(), 7)
        for value in ("0", "-1", "1.5", "four", "04", ""):
            with (
                self.subTest(value=value),
                patch.dict(os.environ, {"BUOY_MODEL_THREADS": value}, clear=True),
                self.assertRaisesRegex(LocalModelError, "positive integer"),
            ):
                model_thread_count()

    def test_loader_is_exact_local_only_and_applies_device_and_threads(self) -> None:
        constructor_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
        thread_calls: list[int] = []

        torch = ModuleType("torch")
        torch.set_num_threads = thread_calls.append  # type: ignore[attr-defined]
        sentence_transformers = ModuleType("sentence_transformers")

        class FakeSentenceTransformer:
            def __init__(self, *args: object, **kwargs: object) -> None:
                constructor_calls.append((args, kwargs))

        sentence_transformers.SentenceTransformer = FakeSentenceTransformer  # type: ignore[attr-defined]
        with (
            patch.dict(
                os.environ,
                {"BUOY_DEVICE": "cuda:0", "BUOY_MODEL_THREADS": "3"},
                clear=True,
            ),
            patch.dict(
                sys.modules,
                {"torch": torch, "sentence_transformers": sentence_transformers},
            ),
        ):
            model = load_sentence_transformer(BGE_MODEL)

        self.assertIsInstance(model, FakeSentenceTransformer)
        self.assertEqual(thread_calls, [3])
        self.assertEqual(
            constructor_calls,
            [
                (
                    (BGE_MODEL,),
                    {
                        "revision": BGE_REVISION,
                        "local_files_only": True,
                        "trust_remote_code": False,
                        "device": "cuda:0",
                        "model_kwargs": {"use_safetensors": True},
                    },
                )
            ],
        )

    def test_loader_never_falls_back_when_cache_is_missing(self) -> None:
        torch = ModuleType("torch")
        torch.set_num_threads = lambda _threads: None  # type: ignore[attr-defined]
        sentence_transformers = ModuleType("sentence_transformers")

        class MissingModel:
            def __init__(self, *_args: object, **kwargs: object) -> None:
                self.assertion = kwargs
                raise OSError("cache miss")

        sentence_transformers.SentenceTransformer = MissingModel  # type: ignore[attr-defined]
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.dict(
                sys.modules,
                {"torch": torch, "sentence_transformers": sentence_transformers},
            ),
            self.assertRaisesRegex(
                LocalModelError,
                "buoy setup --download-models.*automatic downloads",
            ),
        ):
            load_sentence_transformer(BGE_MODEL, BGE_REVISION)

    def test_bge_revision_cannot_be_substituted(self) -> None:
        with self.assertRaisesRegex(LocalModelError, BGE_REVISION):
            load_sentence_transformer(BGE_MODEL, "main")


class ProvisioningCommandTests(unittest.TestCase):
    def test_exact_snapshots_are_downloaded_only_after_acknowledgment(self) -> None:
        from buoy_search.cli import setup as prepare
        from buoy_search.cli.entrypoint import main

        stderr = StringIO()
        with redirect_stderr(stderr), self.assertRaises(SystemExit) as raised:
            main(["setup"])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("network use was not authorized", stderr.getvalue())

        calls: list[dict[str, object]] = []
        hub = ModuleType("huggingface_hub")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def fake_snapshot_download(**kwargs: object) -> str:
                calls.append(kwargs)
                snapshot = prepare.MODEL_SNAPSHOTS[len(calls) - 1]
                path = root / f"snapshot-{len(calls)}"
                for name in snapshot.files:
                    target = path / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(b"fixture")
                return os.fspath(path)

            hub.snapshot_download = fake_snapshot_download  # type: ignore[attr-defined]
            with (
                patch.dict(
                    os.environ,
                    {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"},
                    clear=True,
                ),
                patch.dict(sys.modules, {"huggingface_hub": hub}),
            ):
                self.assertEqual(
                    main(
                        ["setup", "--download-models", "--cache-dir", os.fspath(root / "cache")]
                    ),
                    0,
                )
                self.assertNotIn("HF_HUB_OFFLINE", os.environ)
                self.assertNotIn("TRANSFORMERS_OFFLINE", os.environ)

        expected = [
            (BGE_MODEL, BGE_REVISION),
            (
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
                "c5ee24cb16019beea0893ab7796b1df96625c6b8",
            ),
        ]
        self.assertEqual(
            [(call["repo_id"], call["revision"]) for call in calls], expected
        )
        for call, snapshot in zip(calls, prepare.MODEL_SNAPSHOTS, strict=True):
            self.assertFalse(call["local_files_only"])
            self.assertFalse(call["token"])
            self.assertEqual(call["allow_patterns"], list(snapshot.files))
            self.assertEqual(
                call["cache_dir"], os.fspath((root / "cache" / "hub").resolve())
            )

    def test_setup_help_is_lightweight_and_does_not_load_model_frameworks(self) -> None:
        completed = subprocess.run(
            [sys.executable, "-I", "-c", (
                "import sys; from buoy_search.cli.entrypoint import main; "
                "\ntry: main(['setup', '--help'])"
                "\nexcept SystemExit as exc: assert exc.code == 0"
                "\nassert 'torch' not in sys.modules"
                "\nassert 'sentence_transformers' not in sys.modules"
                "\nassert 'huggingface_hub' not in sys.modules"
                "\nassert 'buoy_search.cli.main' not in sys.modules"
            )],
            capture_output=True, text=True, check=False, timeout=20,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--download-models", completed.stdout)

    def test_legacy_script_delegates_to_installed_command(self) -> None:
        from buoy_search.cli import setup
        from scripts import prepare_local_models

        self.assertIs(prepare_local_models.main, setup.main)
        self.assertTrue(setup._parser().parse_args(["--download"]).download)

    def test_setup_rejects_incomplete_downloads(self) -> None:
        from buoy_search.cli.entrypoint import main

        hub = ModuleType("huggingface_hub")
        with tempfile.TemporaryDirectory() as temporary:
            hub.snapshot_download = lambda **_kwargs: temporary
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.dict(sys.modules, {"huggingface_hub": hub}),
                redirect_stdout(StringIO()),
                self.assertRaisesRegex(RuntimeError, "missing required files"),
            ):
                main(["setup", "--download-models"])


if __name__ == "__main__":
    unittest.main()
