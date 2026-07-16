from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.catalog import ROUTING_DIMENSIONS, load_catalog
from buoy_search.cli import main


UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)


class CredentialReadSentinel(dict[str, str]):
    def _reject_secret(self, key: object) -> None:
        if key == "TURBOPUFFER_API_KEY":
            raise AssertionError("TURBOPUFFER_API_KEY was read")

    def __contains__(self, key: object) -> bool:
        self._reject_secret(key)
        return super().__contains__(key)

    def __getitem__(self, key: str) -> str:
        self._reject_secret(key)
        return super().__getitem__(key)

    def get(self, key: str, default: str | None = None) -> str | None:
        self._reject_secret(key)
        return super().get(key, default)


class FixedEmbedder:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def encode(self, texts):  # noqa: ANN001
        self.calls.append(list(texts))
        return [list(UNIT_VECTOR) for _ in texts]


def upsert_args(path: Path, *, namespace: str = "site-example-v1", title: str = "Example") -> list[str]:
    return [
        "catalog", "upsert", namespace,
        "--catalog", str(path),
        "--source-kind", "website",
        "--source-uri", "https://example.com/docs",
        "--site-id", "site-example",
        "--title", title,
        "--summary", "Example documentation.",
        "--alias", "example docs",
        "--tag", "docs",
        "--region", "gcp-us-central1",
        "--embedding-model", "BAAI/bge-small-en-v1.5",
        "--embedding-precision", "float32",
        "--plan-schema-version", "1",
        "--ranking-mode", "page",
        "--ranking-profile", "none",
        "--ranking-pool", "20",
        "--ranking-aggregation", "max",
        "--json",
    ]


def run_cli(args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
    stdout = StringIO()
    stderr = StringIO()
    context = patch.dict(os.environ, env, clear=True) if env is not None else patch.dict(os.environ, {}, clear=True)
    with context, redirect_stdout(stdout), redirect_stderr(stderr):
        result = main(args)
    return result, stdout.getvalue(), stderr.getvalue()


class CatalogCliTests(unittest.TestCase):
    def test_complete_catalog_lifecycle_json_and_vector_visibility(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            embedder = FixedEmbedder()
            with patch("buoy_search.catalog.load_routing_embedder", return_value=embedder):
                result, stdout, stderr = run_cli(upsert_args(path))
            self.assertEqual((result, stderr), (0, ""))
            created = json.loads(stdout)
            self.assertEqual(created["command"], "catalog upsert")
            self.assertEqual(created["catalog_path"], str(path))
            self.assertEqual(created["namespace"], "site-example-v1")
            self.assertEqual(created["mutation_status"], "created")
            self.assertNotIn("vector", created["card"])
            self.assertEqual(len(embedder.calls), 1)

            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("read loaded model")):
                result, stdout, stderr = run_cli(["catalog", "list", "example docs", "--catalog", str(path), "--json"])
                self.assertEqual((result, stderr), (0, ""))
                listed = json.loads(stdout)
                self.assertEqual(listed["count"], 1)
                self.assertNotIn("vector", listed["cards"][0])

                result, stdout, stderr = run_cli(["catalog", "show", "site-example-v1", "--catalog", str(path), "--json"])
                self.assertEqual((result, stderr), (0, ""))
                self.assertNotIn("vector", json.loads(stdout)["card"])

                result, stdout, stderr = run_cli([
                    "catalog", "show", "site-example-v1", "--catalog", str(path), "--include-vector", "--json"
                ])
                self.assertEqual((result, stderr), (0, ""))
                self.assertEqual(len(json.loads(stdout)["card"]["vector"]), 384)

            original = load_catalog(path).cards[0]
            result, stdout, stderr = run_cli(["catalog", "disable", "site-example-v1", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            disabled_payload = json.loads(stdout)
            self.assertEqual(disabled_payload["mutation_status"], "updated")
            disabled = load_catalog(path).cards[0]
            self.assertFalse(disabled.enabled)
            self.assertEqual(disabled.vector, original.vector)
            self.assertEqual(disabled.semantic_hash, original.semantic_hash)

            result, stdout, stderr = run_cli(["catalog", "list", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(json.loads(stdout)["count"], 0)
            result, stdout, stderr = run_cli(["catalog", "list", "--all", "--catalog", str(path), "--json"])
            self.assertEqual(json.loads(stdout)["count"], 1)

            result, stdout, stderr = run_cli(["catalog", "disable", "site-example-v1", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(json.loads(stdout)["mutation_status"], "unchanged")

            result, stdout, stderr = run_cli(["catalog", "enable", "site-example-v1", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            self.assertTrue(json.loads(stdout)["card"]["enabled"])

            before_preview = path.read_bytes()
            result, stdout, stderr = run_cli(["catalog", "remove", "site-example-v1", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            preview = json.loads(stdout)
            self.assertEqual(preview["mutation_status"], "preview")
            self.assertTrue(preview["remote_turbopuffer_untouched"])
            self.assertTrue(preview["applied_state_untouched"])
            self.assertEqual(path.read_bytes(), before_preview)

            result, stdout, stderr = run_cli([
                "catalog", "remove", "site-example-v1", "--catalog", str(path), "--approve", "--json"
            ])
            self.assertEqual((result, stderr), (0, ""))
            removed = json.loads(stdout)
            self.assertEqual(removed["mutation_status"], "removed")
            self.assertEqual(load_catalog(path).cards, [])

    def test_upsert_preserves_enabled_created_apply_lineage_and_reuses_vector(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            embedder = FixedEmbedder()
            with patch("buoy_search.catalog.load_routing_embedder", return_value=embedder):
                self.assertEqual(run_cli(upsert_args(path))[0], 0)
            self.assertEqual(run_cli(["catalog", "disable", "site-example-v1", "--catalog", str(path), "--json"])[0], 0)
            before = load_catalog(path).cards[0]
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("unchanged semantics embedded")):
                result, stdout, stderr = run_cli(upsert_args(path))
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(payload["mutation_status"], "updated")
            after = load_catalog(path).cards[0]
            self.assertFalse(after.enabled)
            self.assertEqual(after.created_at, before.created_at)
            self.assertEqual(after.vector, before.vector)
            self.assertEqual((after.last_plan_id, after.last_apply_id), (before.last_plan_id, before.last_apply_id))

    def test_disabled_upsert_and_search_normalization_and_namespace_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            with patch("buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()):
                args = upsert_args(path, namespace="z", title="Data_Vault")
                args.insert(-1, "--disabled")
                self.assertEqual(run_cli(args)[0], 0)
                self.assertEqual(run_cli(upsert_args(path, namespace="a", title="Alpha"))[0], 0)
            result, stdout, stderr = run_cli(["catalog", "list", "data vault", "--all", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual([card["namespace"] for card in json.loads(stdout)["cards"]], ["z"])
            result, stdout, stderr = run_cli(["catalog", "list", "--all", "--catalog", str(path), "--json"])
            self.assertEqual([card["namespace"] for card in json.loads(stdout)["cards"]], ["a", "z"])

    def test_text_show_never_prints_vector_even_when_include_flag_is_given(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            with patch("buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()):
                self.assertEqual(run_cli(upsert_args(path))[0], 0)
            result, stdout, stderr = run_cli([
                "catalog", "show", "site-example-v1", "--catalog", str(path), "--include-vector"
            ])
            self.assertEqual((result, stderr), (0, ""))
            self.assertIn("vector: hidden", stdout)
            self.assertNotIn("1.0, 0.0", stdout)

    def test_invalid_or_failed_upsert_preserves_existing_bytes_and_keeps_json_stdout_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            with patch("buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()):
                self.assertEqual(run_cli(upsert_args(path))[0], 0)
            before = path.read_bytes()
            bad = upsert_args(path)
            index = bad.index("example docs")
            bad[index:index + 1] = ["Example", "--alias", "Ｅｘａｍｐｌｅ"]
            result, stdout, stderr = run_cli(bad)
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn(str(path), stderr)
            self.assertIn("duplicate normalized", stderr)
            self.assertEqual(path.read_bytes(), before)

            changed = upsert_args(path, title="Changed")
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=RuntimeError("model unavailable")):
                result, stdout, stderr = run_cli(changed)
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("model unavailable", stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_malformed_source_uri_fails_before_model_and_preserves_json_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            for source_uri in (
                " https://example.com",
                "https://example.com:not-a-port",
                "https://bad_host.example",
                "urn:example",
            ):
                args = upsert_args(path)
                args[args.index("https://example.com/docs")] = source_uri
                with self.subTest(source_uri=source_uri), patch(
                    "buoy_search.catalog.load_routing_embedder",
                    side_effect=AssertionError("model loaded for malformed URI"),
                ):
                    result, stdout, stderr = run_cli(args)
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn("source_uri", stderr)
                self.assertFalse(path.exists())

    def test_corruption_fails_before_model_and_reports_path_on_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            path.write_text("{", encoding="utf-8")
            with patch("buoy_search.catalog.load_routing_embedder", side_effect=AssertionError("model loaded")):
                result, stdout, stderr = run_cli(upsert_args(path))
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn(str(path), stderr)
            self.assertIn("repair or restore", stderr)

    def test_path_precedence_environment_and_explicit_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "env.json"
            cli_path = Path(tmp) / "cli.json"
            with patch("buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()):
                args = upsert_args(cli_path)
                result, stdout, stderr = run_cli(args, env={"BUOY_CATALOG_PATH": str(env_path)})
            self.assertEqual((result, stderr), (0, ""))
            self.assertTrue(cli_path.exists())
            self.assertFalse(env_path.exists())

            result, stdout, stderr = run_cli(["catalog", "list", "--json"], env={"BUOY_CATALOG_PATH": str(cli_path)})
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(json.loads(stdout)["catalog_path"], str(cli_path))

            result, stdout, stderr = run_cli(["catalog", "list", "--catalog", "", "--json"])
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("non-whitespace", stderr)

    def test_legacy_state_root_warning_uses_stderr_and_keeps_json_stdout_clean(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / ".buoy"
            legacy = root / ".turbo-search"
            legacy.mkdir()
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                result, stdout, stderr = run_cli(["catalog", "list", "--json"])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads(stdout)["catalog_path"], str(legacy / "catalog.json"))
            self.assertIn("legacy state root", stderr)

            current.mkdir()
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ):
                result, stdout, stderr = run_cli(["catalog", "list", "--json"])
            self.assertEqual(result, 2)
            self.assertEqual(stdout, "")
            self.assertIn("--catalog", stderr)
            self.assertNotIn("--state-root", stderr)

    def test_absent_namespace_errors_and_missing_catalog_list_is_nonmutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "catalog.json"
            result, stdout, stderr = run_cli(["catalog", "list", "--catalog", str(path), "--json"])
            self.assertEqual((result, stderr), (0, ""))
            self.assertEqual(json.loads(stdout)["count"], 0)
            self.assertFalse(path.parent.exists())
            for command in ("show", "enable", "disable", "remove"):
                result, stdout, stderr = run_cli(["catalog", command, "missing", "--catalog", str(path), "--json"])
                self.assertEqual(result, 2)
                self.assertEqual(stdout, "")
                self.assertIn("namespace 'missing'", stderr)

    def test_commands_do_not_read_credentials_or_contact_turbopuffer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "catalog.json"
            environment = CredentialReadSentinel(
                {"TURBOPUFFER_API_KEY": "must-not-be-read", "BUOY_CATALOG_PATH": str(path)}
            )
            stdout = StringIO()
            stderr = StringIO()
            args = upsert_args(path)
            with patch("buoy_search.catalog.os.environ", environment), patch(
                "buoy_search.catalog.load_routing_embedder", return_value=FixedEmbedder()
            ), patch(
                "buoy_search.namespaces.list_namespace_ids", side_effect=AssertionError("remote catalog call")
            ), patch(
                "buoy_search.retriever.build_namespace", side_effect=AssertionError("Turbopuffer client")
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(args)
            self.assertEqual((result, stderr.getvalue()), (0, ""))
            self.assertFalse(json.loads(stdout.getvalue())["card"].get("vector"))

    def test_explicit_retrieval_is_unchanged_when_catalog_environment_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "corrupt-catalog.json"
            catalog_path.write_text("{", encoding="utf-8")
            result, stdout, stderr = run_cli(
                ["retrieve", "query", "--namespace", "explicit-one", "--namespace", "explicit-two", "--json"],
                env={"BUOY_CATALOG_PATH": str(catalog_path)},
            )
            self.assertEqual((result, stderr), (0, ""))
            payload = json.loads(stdout)
            self.assertEqual(payload["namespaces"], ["explicit-one", "explicit-two"])
            self.assertTrue(payload["dry_run"])
            self.assertFalse(payload["credentials_required"])
            self.assertFalse(payload["turbopuffer_api_calls"])


if __name__ == "__main__":
    unittest.main()
