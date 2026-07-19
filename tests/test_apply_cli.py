from __future__ import annotations

from contextlib import contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import shlex
import tempfile
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import patch

import buoy_search.cli as cli_module
from buoy_search.apply import build_retrieval_commands, load_verified_apply_plan, run_approved_apply
from buoy_search.applied_state import (
    ROW_STATUS_ACTIVE,
    ROW_STATUS_RETAINED_STALE,
    ApplyRunSummary,
    AppliedStateError,
    AppliedStateRow,
    acquire_namespace_apply_lock,
    applied_state_paths,
    build_applied_state,
    load_applied_state,
    load_apply_run_summaries,
    save_applied_state,
)
from buoy_search.cli import build_parser, main
from buoy_search.catalog import ROUTING_DIMENSIONS, catalog_revision
from buoy_search.remote_catalog import (
    CatalogCounts,
    MutationResult,
    ReadMetrics,
    RemoteCatalogSnapshot,
    remote_card_id,
)
from buoy_search.chunker import process_corpus
from buoy_search.config import RuntimeConfig
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts


class TtyStringIO(StringIO):
    def isatty(self) -> bool:
        return True


class FailingTtyStringIO(TtyStringIO):
    def write(self, value: str) -> int:
        raise OSError("simulated stderr failure")


class FailingPromptInput(TtyStringIO):
    def readline(self, *args, **kwargs) -> str:
        del args, kwargs
        raise OSError("simulated prompt read failure")


class EventPromptInput(TtyStringIO):
    def __init__(self, value: str, events: list[str]) -> None:
        super().__init__(value)
        self.events = events

    def readline(self, *args, **kwargs) -> str:
        self.events.append("prompt-read")
        return super().readline(*args, **kwargs)


class FakeEmbedder:
    texts: list[str] = []
    batch_sizes: list[int] = []
    precisions: list[str] = []

    def __init__(self, model_name: str, *, precision: str = "float32") -> None:
        self.model_name = model_name
        self.precision = precision
        FakeEmbedder.precisions.append(precision)

    def encode(self, texts, *, batch_size: int = 32):
        FakeEmbedder.texts.extend(list(texts))
        FakeEmbedder.batch_sizes.append(batch_size)
        return [[float(index), 0.0, 1.0] for index, _ in enumerate(texts, start=1)]


class FixedRoutingEmbedder:
    def encode(self, texts):
        return [[1.0] + [0.0] * (ROUTING_DIMENSIONS - 1) for _ in texts]


class FakeRemoteCatalog:
    def __init__(self) -> None:
        self.cards = []
        self.client = SimpleNamespace(namespace=lambda _name: object())

    def snapshot(self, _client, *, region, compatibility):  # noqa: ANN001
        del compatibility
        live = tuple(sorted({card.namespace for card in self.cards}))
        counts = CatalogCounts(
            listed_total=1 + len(live), control_plane_count=1,
            content_live_count=len(live), card_count=len(self.cards),
            stale_target_count=0, missing_card_count=0, disabled_count=0,
            incompatible_count=0, eligible_count=len(self.cards),
        )
        return RemoteCatalogSnapshot(
            cards=tuple(self.cards), eligible_cards=tuple(self.cards),
            live_namespace_ids=live, missing_card_ids=(), stale_target_ids=(),
            disabled_ids=(), incompatible_ids=(),
            snapshot_revision=catalog_revision(self.cards), counts=counts,
            metrics=ReadMetrics(2, 1, 2, ()),
        )

    def create(self, _resource, cards, *, region):  # noqa: ANN001
        del region
        self.cards.extend(cards)
        card = cards[0]
        return MutationResult(True, card, 1, (remote_card_id(card.namespace),))

    def update(self, _resource, card, *, expected_revision, region):  # noqa: ANN001
        del expected_revision, region
        self.cards = [item for item in self.cards if item.namespace != card.namespace] + [card]
        return MutationResult(True, card, 1, (remote_card_id(card.namespace),))


class FakeWriter:
    rows: list[dict[str, object]] = []
    deletes: list[str] = []
    should_fail = False
    should_delete_fail = False

    def __init__(self, *, config, api_key: str, schema=None) -> None:
        self.config = config
        self.api_key = api_key
        self.schema = schema

    def upsert_rows(self, rows):
        if FakeWriter.should_fail:
            raise RuntimeError("fake upsert failure")
        FakeWriter.rows.extend(list(rows))

    def delete_rows(self, row_ids):
        if FakeWriter.should_delete_fail:
            raise RuntimeError("fake delete failure")
        FakeWriter.deletes.extend(list(row_ids))


def file_snapshot(path: Path) -> tuple[int, int, int, int, bytes]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, path.read_bytes()


def reset_fakes() -> None:
    FakeEmbedder.texts = []
    FakeEmbedder.batch_sizes = []
    FakeEmbedder.precisions = []
    FakeWriter.rows = []
    FakeWriter.deletes = []
    FakeWriter.should_fail = False
    FakeWriter.should_delete_fail = False


def write_page(corpus: Path, name: str, url: str, title: str, body: str) -> None:
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / name).write_text(
        "\n".join(
            [
                "---",
                f'url: "{url}"',
                f'title: "{title}"',
                'status: "200"',
                'content_type: "text/html"',
                'source_hash: "source-hash"',
                'crawl_timestamp: "2026-06-20T00:00:00+00:00"',
                'fetcher: "test"',
                "---",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )


def build_saved_plan(
    root: Path,
    *,
    state_root: Path | None = None,
    page_b_body: str = "# Intro\n\nBeta useful docs.",
    embedding_precision: str = "float32",
    namespace: str | None = None,
    embedding_model: str = "BAAI/bge-small-en-v1.5",
):
    corpus = root / "pages"
    write_page(corpus, "a.md", "https://example.com/docs/a", "Page A", "# Intro\n\nAlpha useful docs.")
    write_page(corpus, "b.md", "https://example.com/docs/b", "Page B", page_b_body)
    out_dir = root / "plan"
    artifacts = build_plan_artifacts(
        indexing_plan=process_corpus(corpus),
        base_url="https://example.com/docs/",
        out_dir=out_dir,
        state_root=state_root or root / "state",
        embedding_precision=embedding_precision,
        namespace=namespace,
        embedding_model=embedding_model,
    )
    write_plan_artifacts(artifacts, out_dir)
    return artifacts, out_dir / "plan.json"


def build_three_row_plan(root: Path, *, state_root: Path):
    corpus = root / "pages"
    for index in range(3):
        write_page(
            corpus,
            f"{index}.md",
            f"https://example.com/docs/{index}",
            f"Page {index}",
            f"# Intro\n\nUseful docs {index}.",
        )
    out_dir = root / "plan"
    artifacts = build_plan_artifacts(
        indexing_plan=process_corpus(corpus),
        base_url="https://example.com/docs/",
        out_dir=out_dir,
        state_root=state_root,
    )
    write_plan_artifacts(artifacts, out_dir)
    return artifacts, out_dir / "plan.json"


def build_one_page_plan_with_stale_state(root: Path, state_root: Path):
    previous_artifacts, _ = build_saved_plan(root / "previous", state_root=state_root)
    desired = previous_artifacts.manifest.chunks[0]
    stale = previous_artifacts.manifest.chunks[1]

    one_page_root = root / "one-page"
    corpus = one_page_root / "pages"
    write_page(corpus, "a.md", "https://example.com/docs/a", "Page A", "# Intro\n\nAlpha useful docs.")
    one_page_artifacts = build_plan_artifacts(
        indexing_plan=process_corpus(corpus),
        base_url="https://example.com/docs/",
        out_dir=one_page_root / "plan",
        state_root=state_root,
    )
    write_plan_artifacts(one_page_artifacts, one_page_root / "plan")
    save_applied_state(
        build_applied_state(
            site_id=previous_artifacts.manifest.site_id,
            namespace=previous_artifacts.manifest.namespace,
            base_url=previous_artifacts.manifest.base_url,
            last_plan_id="plan_previous",
            last_apply_id="apply_previous",
            rows=[
                AppliedStateRow(
                    row_id=desired.row_id,
                    canonical_url=desired.canonical_url,
                    page_hash=desired.page_hash,
                    chunk_hash=desired.chunk_hash,
                    embedding_text_hash=desired.embedding_text_hash,
                    plan_id="plan_previous",
                    applied_at="2026-06-20T12:00:00+00:00",
                ),
                AppliedStateRow(
                    row_id=stale.row_id,
                    canonical_url=stale.canonical_url,
                    page_hash=stale.page_hash,
                    chunk_hash=stale.chunk_hash,
                    embedding_text_hash=stale.embedding_text_hash,
                    plan_id="plan_previous",
                    applied_at="2026-06-20T12:00:00+00:00",
                ),
            ],
            updated_at="2026-06-20T12:00:00+00:00",
        ),
        state_root=state_root,
    )
    return previous_artifacts, one_page_artifacts, one_page_root / "plan" / "plan.json", stale


class ApplyCliTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_fakes()
        self.remote_catalog = FakeRemoteCatalog()
        patchers = [
            patch("buoy_search.catalog.load_routing_embedder", return_value=FixedRoutingEmbedder()),
            patch("buoy_search.apply.REMOTE_CATALOG_CLIENT_FACTORY", return_value=self.remote_catalog.client),
            patch("buoy_search.apply.read_remote_catalog", side_effect=self.remote_catalog.snapshot),
            patch("buoy_search.apply.create_remote_cards", side_effect=self.remote_catalog.create),
            patch("buoy_search.apply.update_remote_card", side_effect=self.remote_catalog.update),
            patch("buoy_search.remote_catalog.create_client", side_effect=AssertionError("real SDK factory used")),
        ]
        for patcher in patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_apply_batch_size_defaults_and_embedding_batch_validation(self) -> None:
        parser = build_parser()
        plan_defaults = parser.parse_args(["plan", "https://example.com"])
        self.assertEqual(plan_defaults.embedding_precision, "float32")
        float16_plan = parser.parse_args(["plan", "https://example.com", "--embedding-precision", "float16"])
        self.assertEqual(float16_plan.embedding_precision, "float16")
        defaults = parser.parse_args(["apply"])
        self.assertEqual(defaults.batch_size, 64)
        self.assertEqual(defaults.embedding_batch_size, 32)
        self.assertIsNone(defaults.state_root)
        with redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            parser.parse_args(["apply", "--embedding-batch-size", "0"])

    def test_approved_apply_uses_precision_recorded_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts, plan_path = build_saved_plan(
                root, state_root=root / "state", embedding_precision="float16"
            )
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch("buoy_search.cli._confirm_apply", side_effect=AssertionError("prompted")):
                result, _stdout, _stderr = self.run_main(
                    ["apply", "--approve", "--plan", str(plan_path), "--state-root", str(root / "state"), "--json"],
                    env={"TURBOPUFFER_API_KEY": "test-key", "BUOY_EMBEDDING_PRECISION": "float32"},
                )
            self.assertEqual(result, 0)
            self.assertEqual(FakeEmbedder.precisions, ["float16"])
            self.assertEqual(artifacts.plan.embedding_precision, "float16")

    def test_approved_apply_handoff_preserves_pre_rebrand_namespace_and_verified_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            namespace = "github-doctacon-turbo-search-v1"
            model = "legacy model; untouched"
            _, plan_path = build_saved_plan(
                root,
                state_root=state_root,
                namespace=namespace,
                embedding_model=model,
                embedding_precision="float16",
            )
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    ["apply", "--approve", "--plan", str(plan_path), "--state-root", str(state_root), "--json"],
                    env={"TURBOPUFFER_API_KEY": "test-key", "TURBOPUFFER_REGION": "gcp-us-east4"},
                )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["namespace"], namespace)
        self.assertEqual(payload["region"], "gcp-us-east4")
        self.assertEqual(payload["embedding_model"], model)
        self.assertEqual(payload["embedding_precision"], "float16")
        live = shlex.split(payload["retrieval_commands"]["live"])
        self.assertEqual(
            live,
            [
                "buoy",
                "retrieve",
                "<query>",
                "--namespace",
                namespace,
                "--region",
                "gcp-us-east4",
                "--embedding-model",
                model,
                "--embedding-precision",
                "float16",
            ],
        )
        self.assertEqual(shlex.split(payload["retrieval_commands"]["preview"]), [*live, "--dry-run"])

    def run_main(
        self,
        args: list[str],
        *,
        env: dict[str, str] | None = None,
        stdin: StringIO | None = None,
        stderr: StringIO | None = None,
    ):
        stdout = StringIO()
        stdin = stdin or StringIO()
        stderr = stderr or StringIO()
        env_patch = {} if env is None else env
        with patch.dict("os.environ", env_patch, clear=True), patch("sys.stdin", stdin):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                result = main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_apply_mode_gate_and_non_tty_rejection_precede_plan_work(self) -> None:
        with patch("buoy_search.cli.resolve_cli_state_root", side_effect=AssertionError("state root")), patch(
            "buoy_search.cli.discover_latest_plan_path", side_effect=AssertionError("plan selection")
        ):
            conflict, conflict_stdout, conflict_stderr = self.run_main(
                ["apply", "--dry-run", "--approve", "--json"]
            )
            piped, piped_stdout, piped_stderr = self.run_main(
                ["apply", "--json"], stdin=StringIO("yes\n")
            )

        self.assertEqual((conflict, conflict_stdout), (2, ""))
        self.assertIn("either --dry-run or --approve", conflict_stderr)
        self.assertEqual((piped, piped_stdout), (2, ""))
        self.assertIn("interactive stdin", piped_stderr)
        self.assertIn("--dry-run", piped_stderr)
        self.assertIn("--approve", piped_stderr)

    def test_interactive_declines_eof_and_prompt_failures_cancel_without_side_effects(self) -> None:
        responses = {
            "enter": "\n",
            "lower-no": "no\n",
            "upper-no": " NO \n",
            "arbitrary": "apply it\n",
            "eof": "",
        }
        for label, response in responses.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                reset_fakes()
                self.remote_catalog.cards = []
                root = Path(tmp)
                state_root = root / "state"
                artifacts, plan_path = build_saved_plan(root, state_root=state_root)
                paths = applied_state_paths(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    state_root=state_root,
                )
                obsolete = paths.state_dir / "last-applied.json"
                obsolete.parent.mkdir(parents=True, exist_ok=True)
                obsolete.write_bytes(b"obsolete cancellation sentinel\x00")
                before = file_snapshot(obsolete)
                with patch("buoy_search.cli.load_config", side_effect=AssertionError("credentials/config")), patch(
                    "buoy_search.cli.run_approved_apply", side_effect=AssertionError("approved pipeline")
                ), patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("model")), patch(
                    "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer")
                ):
                    result, stdout, stderr = self.run_main(
                        [
                            "apply", "--plan", str(plan_path), "--state-root", str(state_root), "--json",
                        ],
                        stdin=TtyStringIO(response),
                    )
                payload = json.loads(stdout)
                self.assertEqual(result, 0, stderr)
                self.assertFalse(payload["approved"])
                self.assertFalse(payload["dry_run"])
                self.assertTrue(payload["cancelled"])
                self.assertEqual(payload["confirmation"], "declined_or_unavailable")
                self.assertFalse(payload["turbopuffer_api_calls"])
                self.assertFalse(payload["state_updated"])
                self.assertFalse(payload["catalog_updated"])
                self.assertIn("Website RAG apply preflight", stderr)
                self.assertTrue(stderr.endswith("Apply this plan? [y/N] "))
                self.assertTrue(plan_path.exists())
                self.assertFalse(paths.database_path.exists())
                self.assertFalse((state_root / "catalog-pending").exists())
                self.assertEqual(file_snapshot(obsolete), before)
                self.assertEqual(FakeEmbedder.texts, [])
                self.assertEqual(FakeWriter.rows, [])
                self.assertEqual(self.remote_catalog.cards, [])

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)
            result, stdout, stderr = self.run_main(
                ["apply", "--plan", str(plan_path), "--state-root", str(state_root)],
                stdin=FailingPromptInput(),
            )
        self.assertEqual(result, 0, stderr)
        self.assertIn("Website RAG apply preflight", stdout)
        self.assertTrue(stdout.endswith("Apply cancelled; nothing was written.\n"))
        self.assertTrue(stderr.endswith("Apply this plan? [y/N] "))

    def test_interactive_preflight_failure_never_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            missing_plan = Path(tmp) / "missing" / "plan.json"
            with patch("buoy_search.cli._confirm_apply", side_effect=AssertionError("prompted")):
                result, stdout, stderr = self.run_main(
                    ["apply", "--plan", str(missing_plan), "--json"],
                    stdin=TtyStringIO("yes\n"),
                )
        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("Plan file not found", stderr)
        self.assertNotIn("Apply this plan?", stderr)

    def test_prompt_output_failure_is_safe_json_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)
            result, stdout, _stderr = self.run_main(
                ["apply", "--plan", str(plan_path), "--state-root", str(state_root), "--json"],
                stdin=TtyStringIO("yes\n"),
                stderr=FailingTtyStringIO(),
            )
            plan_retained = plan_path.exists()
        payload = json.loads(stdout)
        self.assertEqual(result, 0)
        self.assertTrue(payload["cancelled"])
        self.assertFalse(payload["state_updated"])
        self.assertTrue(plan_retained)

    def test_interactive_confirmation_accepts_only_exact_yes_forms(self) -> None:
        for response in ("y\n", "yes\n", " Y \n", " YeS\t\n"):
            with self.subTest(response=response), tempfile.TemporaryDirectory() as tmp:
                reset_fakes()
                self.remote_catalog.cards = []
                root = Path(tmp)
                state_root = root / "state"
                artifacts, plan_path = build_saved_plan(root, state_root=state_root)
                paths = applied_state_paths(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    state_root=state_root,
                )
                obsolete = paths.state_dir / "legacy-json" / "last-applied.json"
                obsolete.parent.mkdir(parents=True, exist_ok=True)
                obsolete.write_bytes(b"obsolete confirmed interactive sentinel\x00")
                obsolete_before = file_snapshot(obsolete)
                with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                    "buoy_search.apply.TurbopufferWriter", FakeWriter
                ), patch("buoy_search.cli._confirm_apply", wraps=cli_module._confirm_apply) as confirm:
                    result, stdout, stderr = self.run_main(
                        ["apply", "--plan", str(plan_path), "--state-root", str(state_root), "--json"],
                        env={"TURBOPUFFER_API_KEY": "test-key"},
                        stdin=TtyStringIO(response),
                    )
                payload = json.loads(stdout)
                self.assertEqual(result, 0, stderr)
                self.assertTrue(payload["approved"])
                self.assertFalse(payload["dry_run"])
                self.assertTrue(payload["state_updated"])
                self.assertTrue(payload["catalog_updated"])
                self.assertEqual(confirm.call_count, 1)
                self.assertIn("Website RAG apply preflight", stderr)
                self.assertIn("Apply this plan? [y/N] ", stderr)
                self.assertFalse(plan_path.exists())
                self.assertEqual(file_snapshot(obsolete), obsolete_before)
                self.assertEqual(len(FakeWriter.rows), len(artifacts.manifest.chunks))

    def test_interactive_preflight_prompt_and_approved_revalidation_order(self) -> None:
        events: list[str] = []
        real_print_apply_text = cli_module.print_apply_text
        real_load_config = cli_module.load_config
        real_lock = acquire_namespace_apply_lock

        def ordered_print(payload, *, stream=None):  # noqa: ANN001
            events.append("preflight-visible")
            return real_print_apply_text(payload, stream=stream)

        def ordered_config():
            events.append("load-config")
            return real_load_config()

        @contextmanager
        def ordered_lock(**kwargs):
            events.append("lock")
            with real_lock(**kwargs):
                yield

        class OrderedEmbedder(FakeEmbedder):
            def __init__(self, model_name: str, *, precision: str = "float32") -> None:
                events.append("model")
                super().__init__(model_name, precision=precision)

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.cli.print_apply_text", side_effect=ordered_print), patch(
                "buoy_search.cli.load_config", side_effect=ordered_config
            ), patch("buoy_search.apply.acquire_namespace_apply_lock", ordered_lock), patch(
                "buoy_search.apply.load_verified_apply_plan", wraps=load_verified_apply_plan
            ) as revalidate, patch("buoy_search.apply.SentenceTransformerEmbedder", OrderedEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    ["apply", "--plan", str(plan_path), "--state-root", str(state_root)],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stdin=EventPromptInput("yes\n", events),
                )
        self.assertEqual(result, 0, stderr)
        self.assertIn("artifact_hash:", stdout)
        self.assertIn("state_path:", stdout)
        self.assertIn("Apply this plan? [y/N] ", stderr)
        self.assertEqual(revalidate.call_count, 1)
        self.assertLess(events.index("preflight-visible"), events.index("prompt-read"))
        self.assertLess(events.index("prompt-read"), events.index("load-config"))
        self.assertLess(events.index("load-config"), events.index("lock"))
        self.assertLess(events.index("lock"), events.index("model"))

    def test_apply_preflight_verifies_plan_without_credentials_or_live_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        "site-example-com-v1",
                        "--state-root",
                        str(state_root),
                        "--json",
                    ]
                )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["command"], "apply")
        self.assertFalse(payload["approved"])
        self.assertTrue(payload["dry_run"])
        self.assertFalse(payload["cancelled"])
        self.assertEqual(payload["confirmation"], "not_requested")
        self.assertFalse(payload["credentials_required"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertFalse(payload["api_calls_occurred"])
        self.assertNotIn("timing", payload)
        self.assertTrue(payload["artifact_verified"])
        self.assertEqual(payload["rows_to_upsert"], 2)
        self.assertEqual(payload["rows_upserted"], 0)
        self.assertEqual(payload["region"], "gcp-us-central1")
        live = shlex.split(payload["retrieval_commands"]["live"])
        self.assertEqual(
            live,
            [
                "buoy",
                "retrieve",
                "<query>",
                "--namespace",
                "site-example-com-v1",
                "--region",
                "gcp-us-central1",
                "--embedding-model",
                "BAAI/bge-small-en-v1.5",
                "--embedding-precision",
                "float32",
            ],
        )
        self.assertEqual(
            shlex.split(payload["retrieval_commands"]["preview"]),
            [*live, "--dry-run"],
        )
        self.assertEqual(stderr, "")

    def test_apply_preflight_is_byte_equivalent_with_obsolete_json_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)
            args = [
                "apply", "--dry-run", "--plan", str(plan_path), "--namespace", "site-example-com-v1",
                "--state-root", str(state_root), "--json",
            ]

            absent_result = self.run_main(args)
            paths = applied_state_paths(
                site_id="example-com", namespace="site-example-com-v1", state_root=state_root
            )
            obsolete_paths = (
                paths.state_dir / "last-applied.json",
                paths.state_dir / "legacy-json" / "last-applied.json",
            )
            for index, obsolete_path in enumerate(obsolete_paths):
                obsolete_path.parent.mkdir(parents=True, exist_ok=True)
                obsolete_path.write_bytes(f"unparseable applied state {index}\x00".encode())
            before = {path: file_snapshot(path) for path in obsolete_paths}

            present_result = self.run_main(args)

            self.assertEqual(present_result, absent_result)
            self.assertEqual({path: file_snapshot(path) for path in obsolete_paths}, before)
            self.assertTrue(json.loads(present_result[1])["state_first_apply"])
            self.assertFalse(paths.database_path.exists())

    def test_retrieval_handoff_commands_quote_every_dynamic_value(self) -> None:
        commands = build_retrieval_commands(
            namespace="legacy namespace; echo unsafe",
            region="region with spaces",
            embedding_model="model/$(touch nope)",
            embedding_precision="precision; false",
        )
        live = [
            "buoy",
            "retrieve",
            "<query>",
            "--namespace",
            "legacy namespace; echo unsafe",
            "--region",
            "region with spaces",
            "--embedding-model",
            "model/$(touch nope)",
            "--embedding-precision",
            "precision; false",
        ]
        self.assertEqual(shlex.split(commands["live"]), live)
        self.assertEqual(shlex.split(commands["preview"]), [*live, "--dry-run"])

    def test_automatic_plan_preflight_text_is_decision_complete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.cli.discover_latest_plan_path", return_value=plan_path) as discover:
                result, stdout, stderr = self.run_main(
                    ["apply", "--dry-run", "--state-root", str(state_root)],
                    env={"TURBOPUFFER_REGION": "aws-us-west-2"},
                )

        self.assertEqual(result, 0, stderr)
        discover.assert_called_once_with()
        self.assertIn(f"source: {artifacts.manifest.base_url}", stdout)
        self.assertIn(f"plan_path: {plan_path}", stdout)
        self.assertIn(f"artifact_hash: {artifacts.plan.artifact_hash}", stdout)
        self.assertIn("namespace: site-example-com-v1 (aws-us-west-2)", stdout)
        self.assertIn("embedding_model: BAAI/bge-small-en-v1.5", stdout)
        self.assertIn("embedding_precision: float32", stdout)
        self.assertIn("first_apply: True", stdout)
        self.assertIn("rows: to_upsert=2; upserted=0; unchanged=0", stdout)
        self.assertIn("embeddings: to_generate=2; generated=0", stdout)
        self.assertIn("stale_intent: retain 0 stale rows", stdout)
        self.assertIn("retrieval after successful apply (preview):", stdout)
        self.assertIn("retrieval after successful apply (live):", stdout)
        self.assertIn("no credentials, embeddings, or turbopuffer API calls", stdout)

    def test_apply_defaults_to_latest_old_plan_and_uses_legacy_state_in_place(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                legacy_root = Path(".turbo-search")
                legacy_root.mkdir()
                marker = legacy_root / "marker"
                marker.write_text("preserve", encoding="utf-8")
                _, old_plan_path = build_saved_plan(
                    root / "artifacts/site-crawls/old-site-plan",
                    state_root=legacy_root,
                )
                _, latest_plan_path = build_saved_plan(
                    root / "artifacts/site-crawls/latest-site-plan",
                    state_root=legacy_root,
                )
                old_artifact_hash = json.loads(latest_plan_path.read_text(encoding="utf-8"))["artifact_hash"]
                os.utime(old_plan_path, (1, 1))
                os.utime(latest_plan_path, (2, 2))

                with patch(
                    "buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")
                ), patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")):
                    result, stdout, stderr = self.run_main(["apply", "--dry-run", "--json"])

                self.assertFalse(Path(".buoy").exists())
                self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
                self.assertEqual(json.loads(latest_plan_path.read_text(encoding="utf-8"))["artifact_hash"], old_artifact_hash)
            finally:
                os.chdir(old_cwd)

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["plan_path"], str(latest_plan_path.relative_to(root)))
        self.assertEqual(payload["namespace"], "site-example-com-v1")
        self.assertEqual(payload["state_path"], ".turbo-search/state/example-com/site-example-com-v1/state.duckdb")
        self.assertFalse(payload["approved"])
        self.assertFalse(payload["turbopuffer_api_calls"])
        self.assertIn("using legacy state root .turbo-search in place", stderr)
        self.assertNotIn("Warning", stdout)

    def test_dual_implicit_state_roots_fail_before_apply_plan_or_remote_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            current = root / ".buoy"
            legacy = root / ".turbo-search"
            current.mkdir()
            legacy.mkdir()
            with patch("buoy_search.applied_state.DEFAULT_STATE_ROOT", current), patch(
                "buoy_search.applied_state.LEGACY_STATE_ROOT", legacy
            ), patch("buoy_search.cli.discover_latest_plan_path") as discover_mock, patch(
                "buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")
            ), patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")):
                result, stdout, stderr = self.run_main(
                    ["apply", "--approve", "--json"], env={"TURBOPUFFER_API_KEY": "not-used"}
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("both implicit state roots exist", stderr)
        discover_mock.assert_not_called()

    def test_apply_without_plan_fails_clearly_when_no_local_plan_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                result, stdout, stderr = self.run_main(["apply", "--dry-run", "--json"])
            finally:
                os.chdir(old_cwd)

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("No plan search root found", stderr)
        self.assertIn("pass --plan explicitly", stderr)

    def test_approved_apply_requires_api_key_before_embedding_or_writing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        "site-example-com-v1",
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("TURBOPUFFER_API_KEY must be set", stderr)

    def test_confirmed_apply_matches_first_apply_behavior_with_obsolete_json_present(self) -> None:
        def run_case(root: Path, *, obsolete: bool) -> tuple[dict[str, object], dict[Path, tuple[int, int, int, int, bytes]]]:
            reset_fakes()
            self.remote_catalog.cards = []
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            paths = applied_state_paths(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            obsolete_paths = (
                paths.state_dir / "last-applied.json",
                paths.state_dir / "legacy-json" / "last-applied.json",
            )
            before: dict[Path, tuple[int, int, int, int, bytes]] = {}
            if obsolete:
                for index, obsolete_path in enumerate(obsolete_paths):
                    obsolete_path.parent.mkdir(parents=True, exist_ok=True)
                    obsolete_path.write_bytes(f"obsolete confirmed apply {index}\n".encode())
                before = {path: file_snapshot(path) for path in obsolete_paths}

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply", "--plan", str(plan_path), "--namespace", artifacts.manifest.namespace,
                        "--state-root", str(state_root), "--approve", "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            self.assertEqual(result, 0, stderr)
            payload = json.loads(stdout)
            loaded = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            summaries = load_apply_run_summaries(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            after = {path: file_snapshot(path) for path in obsolete_paths} if obsolete else {}
            projection = {
                key: payload[key]
                for key in (
                    "approved", "dry_run", "state_first_apply", "rows_to_upsert", "rows_upserted",
                    "embeddings_to_generate", "embeddings_generated", "stale_rows",
                    "retained_stale_rows", "state_updated", "catalog_updated",
                )
            }
            projection["written_row_ids"] = sorted(str(row["id"]) for row in FakeWriter.rows)
            projection["state_rows"] = sorted((row.row_id, row.status) for row in loaded.rows)
            projection["apply_summary_counts"] = [
                (summary.rows_upserted, summary.rows_deleted, summary.retained_stale_rows)
                for summary in summaries
            ]
            projection["plan_removed"] = not plan_path.parent.exists()
            self.assertEqual(after, before)
            return projection, after

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            absent_projection, absent_files = run_case(root / "absent", obsolete=False)
            present_projection, present_files = run_case(root / "present", obsolete=True)

        self.assertEqual(present_projection, absent_projection)
        self.assertEqual(absent_files, {})
        self.assertEqual(len(present_files), 2)
        self.assertTrue(present_projection["state_first_apply"])

    def test_approved_apply_upserts_only_diff_rows_and_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            unchanged, needs_upsert = artifacts.manifest.chunks
            save_applied_state(
                build_applied_state(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    base_url=artifacts.manifest.base_url,
                    last_plan_id="plan_previous",
                    last_apply_id="apply_previous",
                    rows=[
                        AppliedStateRow(
                            row_id=unchanged.row_id,
                            canonical_url=unchanged.canonical_url,
                            page_hash=unchanged.page_hash,
                            chunk_hash=unchanged.chunk_hash,
                            embedding_text_hash=unchanged.embedding_text_hash,
                            plan_id="plan_previous",
                            applied_at="2026-06-20T12:00:00+00:00",
                        )
                    ],
                    updated_at="2026-06-20T12:00:00+00:00",
                ),
                state_root=state_root,
            )

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )

            plan_removed = not plan_path.parent.exists()
            payload = json.loads(stdout)
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            summaries = load_apply_run_summaries(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )

        self.assertEqual(result, 0, stderr)
        self.assertTrue(payload["approved"])
        self.assertEqual(payload["timing"]["embedding_batch_size"], 32)
        self.assertEqual(payload["timing"]["write_batch_size"], 64)
        self.assertEqual(payload["rows_to_upsert"], 1)
        self.assertEqual(payload["rows_upserted"], 1)
        self.assertEqual(payload["embeddings_generated"], 1)
        self.assertEqual(len(FakeEmbedder.texts), 1)
        self.assertIn("Beta useful docs", FakeEmbedder.texts[0])
        self.assertEqual([row["id"] for row in FakeWriter.rows], [needs_upsert.row_id])
        self.assertTrue(payload["state_updated"])
        self.assertTrue(plan_removed)
        self.assertFalse(loaded_state.first_apply)
        self.assertEqual({row.row_id for row in loaded_state.rows if row.status == ROW_STATUS_ACTIVE}, {unchanged.row_id, needs_upsert.row_id})
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].apply_id, loaded_state.last_apply_id)
        self.assertEqual(summaries[0].rows_upserted, 1)
        self.assertEqual(summaries[0].rows_deleted, 0)

    def test_successful_apply_reports_cleanup_warning_without_losing_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ), patch(
                "buoy_search.cli.cleanup_applied_plan_directory",
                return_value=[f"could not remove plan artifact directory {plan_path.parent}: denied"],
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            plan_retained = plan_path.parent.exists()

        self.assertEqual(result, 0, stderr)
        self.assertTrue(json.loads(stdout)["approved"])
        self.assertIn("Warning: could not remove plan artifact directory", stderr)
        self.assertTrue(plan_retained)

    def test_failed_apply_preserves_existing_state_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            unchanged, _needs_upsert = artifacts.manifest.chunks
            previous_state = build_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                last_plan_id="plan_previous",
                last_apply_id="apply_previous",
                rows=[
                    AppliedStateRow(
                        row_id=unchanged.row_id,
                        canonical_url=unchanged.canonical_url,
                        page_hash=unchanged.page_hash,
                        chunk_hash=unchanged.chunk_hash,
                        embedding_text_hash=unchanged.embedding_text_hash,
                        plan_id="plan_previous",
                        applied_at="2026-06-20T12:00:00+00:00",
                    )
                ],
                updated_at="2026-06-20T12:00:00+00:00",
            )
            previous_summary = ApplyRunSummary(
                apply_id="apply_previous",
                plan_id="plan_previous",
                applied_at="2026-06-20T12:00:00+00:00",
                rows_upserted=1,
                rows_deleted=0,
                retained_stale_rows=0,
            )
            save_applied_state(previous_state, state_root=state_root, apply_run=previous_summary)
            FakeWriter.should_fail = True

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            plan_retained = plan_path.parent.exists()
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            summaries = load_apply_run_summaries(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("fake upsert failure", stderr)
        self.assertTrue(plan_retained)
        self.assertEqual(loaded_state, previous_state)
        self.assertEqual(summaries, [previous_summary])

    def test_approved_apply_does_not_update_state_when_upsert_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            paths = applied_state_paths(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            obsolete_path = paths.state_dir / "last-applied.json"
            obsolete_path.parent.mkdir(parents=True, exist_ok=True)
            obsolete_path.write_bytes(b"failed apply must not touch this\n")
            obsolete_before = file_snapshot(obsolete_path)
            FakeWriter.should_fail = True

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            obsolete_after = file_snapshot(obsolete_path)

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("fake upsert failure", stderr)
        self.assertTrue(loaded_state.first_apply)
        self.assertEqual(obsolete_after, obsolete_before)

    def test_approved_apply_with_delete_stale_fails_when_no_stale_rows_before_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--delete-stale",
                        "--json",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("no stale rows", stderr)
        self.assertEqual(FakeEmbedder.texts, [])
        self.assertEqual(FakeWriter.rows, [])
        self.assertEqual(FakeWriter.deletes, [])

    def test_apply_fails_on_artifact_hash_mismatch_before_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)
            manifest_path = plan_path.parent / "manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["chunks"][0]["content"] = "tampered content"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        "site-example-com-v1",
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertTrue("chunks.jsonl does not match" in stderr or "artifact hash mismatch" in stderr)

    def test_apply_fails_on_namespace_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _, plan_path = build_saved_plan(root, state_root=state_root)

            result, stdout, stderr = self.run_main(
                [
                    "apply",
                    "--dry-run",
                    "--plan",
                    str(plan_path),
                    "--namespace",
                    "site-other-v1",
                    "--state-root",
                    str(state_root),
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("namespace mismatch", stderr)

    def test_apply_fails_on_incompatible_local_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            save_applied_state(
                build_applied_state(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    base_url="https://example.com/other/",
                    last_plan_id="plan_previous",
                    last_apply_id="apply_previous",
                    rows=[],
                    updated_at="2026-06-20T12:00:00+00:00",
                ),
                state_root=state_root,
            )

            result, stdout, stderr = self.run_main(
                [
                    "apply",
                    "--dry-run",
                    "--plan",
                    str(plan_path),
                    "--namespace",
                    artifacts.manifest.namespace,
                    "--state-root",
                    str(state_root),
                    "--json",
                ]
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("base_url mismatch", stderr)

    def test_successful_apply_marks_stale_rows_as_retained_without_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            desired = artifacts.manifest.chunks[0]
            stale = artifacts.manifest.chunks[1]
            # Rebuild a one-page desired plan so the saved state's second row is stale.
            one_page_root = root / "one-page"
            corpus = one_page_root / "pages"
            write_page(corpus, "a.md", "https://example.com/docs/a", "Page A", "# Intro\n\nAlpha useful docs.")
            one_page_artifacts = build_plan_artifacts(
                indexing_plan=process_corpus(corpus),
                base_url="https://example.com/docs/",
                out_dir=one_page_root / "plan",
                state_root=state_root,
            )
            write_plan_artifacts(one_page_artifacts, one_page_root / "plan")
            plan_path = one_page_root / "plan" / "plan.json"
            save_applied_state(
                build_applied_state(
                    site_id=artifacts.manifest.site_id,
                    namespace=artifacts.manifest.namespace,
                    base_url=artifacts.manifest.base_url,
                    last_plan_id="plan_previous",
                    last_apply_id="apply_previous",
                    rows=[
                        AppliedStateRow(
                            row_id=desired.row_id,
                            canonical_url=desired.canonical_url,
                            page_hash=desired.page_hash,
                            chunk_hash=desired.chunk_hash,
                            embedding_text_hash=desired.embedding_text_hash,
                            plan_id="plan_previous",
                            applied_at="2026-06-20T12:00:00+00:00",
                        ),
                        AppliedStateRow(
                            row_id=stale.row_id,
                            canonical_url=stale.canonical_url,
                            page_hash=stale.page_hash,
                            chunk_hash=stale.chunk_hash,
                            embedding_text_hash=stale.embedding_text_hash,
                            plan_id="plan_previous",
                            applied_at="2026-06-20T12:00:00+00:00",
                        ),
                    ],
                    updated_at="2026-06-20T12:00:00+00:00",
                ),
                state_root=state_root,
            )

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(payload["rows_to_upsert"], 0)
        self.assertEqual(payload["stale_rows"], 1)
        self.assertFalse(payload["delete_stale"])
        self.assertEqual(payload["stale_rows_to_delete"], 0)
        self.assertEqual(payload["rows_deleted"], 0)
        self.assertEqual(FakeWriter.deletes, [])
        retained = [row for row in loaded_state.rows if row.status == ROW_STATUS_RETAINED_STALE]
        self.assertEqual([row.row_id for row in retained], [stale.row_id])

    def test_apply_preflight_reports_stale_retention_without_delete_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _, plan_path, _stale = build_one_page_plan_with_stale_state(root, state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--json",
                    ]
                )
                text_result, text_stdout, text_stderr = self.run_main(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                    ]
                )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(text_result, 0, text_stderr)
        self.assertIn("stale_intent: retain 1 stale rows", text_stdout)
        self.assertFalse(payload["approved"])
        self.assertFalse(payload["delete_stale"])
        self.assertFalse(payload["delete_would_run"])
        self.assertEqual(payload["stale_rows"], 1)
        self.assertEqual(payload["stale_rows_to_delete"], 0)
        self.assertEqual(payload["stale_row_ids_to_delete"], [])
        self.assertEqual(payload["stale_rows_retained"], 1)
        self.assertEqual(payload["rows_deleted"], 0)
        self.assertEqual(stderr, "")

    def test_apply_preflight_reports_delete_stale_without_deleting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _, plan_path, stale = build_one_page_plan_with_stale_state(root, state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--delete-stale",
                        "--json",
                    ]
                )
                text_result, text_stdout, text_stderr = self.run_main(
                    [
                        "apply",
                        "--dry-run",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--delete-stale",
                    ]
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertEqual(text_result, 0, text_stderr)
        self.assertIn("stale_intent: delete 1 stale rows", text_stdout)
        self.assertFalse(payload["approved"])
        self.assertTrue(payload["delete_stale"])
        self.assertTrue(payload["delete_would_run"])
        self.assertEqual(payload["stale_rows"], 1)
        self.assertEqual(payload["stale_rows_to_delete"], 1)
        self.assertEqual(payload["stale_row_ids_to_delete"], [stale.row_id])
        self.assertEqual(payload["rows_deleted"], 0)
        self.assertEqual(stderr, "")
        self.assertEqual([row.row_id for row in loaded_state.rows], [artifacts.manifest.chunks[0].row_id, stale.row_id])

    def test_approved_apply_with_delete_stale_deletes_exact_stale_ids_and_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _, plan_path, stale = build_one_page_plan_with_stale_state(root, state_root)

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--delete-stale",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        payload = json.loads(stdout)
        self.assertEqual(result, 0, stderr)
        self.assertTrue(payload["approved"])
        self.assertTrue(payload["delete_stale"])
        self.assertEqual(payload["stale_rows_to_delete"], 1)
        self.assertEqual(payload["rows_deleted"], 1)
        self.assertEqual(payload["stale_rows_retained"], 0)
        self.assertEqual(FakeWriter.deletes, [stale.row_id])
        self.assertEqual([row.row_id for row in loaded_state.rows], [artifacts.manifest.chunks[0].row_id])
        self.assertFalse([row for row in loaded_state.rows if row.status == ROW_STATUS_RETAINED_STALE])

    def test_approved_apply_does_not_update_state_when_delete_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _, plan_path, stale = build_one_page_plan_with_stale_state(root, state_root)
            FakeWriter.should_delete_fail = True

            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--delete-stale",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )
            summaries = load_apply_run_summaries(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("fake delete failure", stderr)
        self.assertEqual(FakeWriter.deletes, [])
        self.assertEqual([row.row_id for row in loaded_state.rows], [artifacts.manifest.chunks[0].row_id, stale.row_id])
        self.assertTrue(all(row.status == ROW_STATUS_ACTIVE for row in loaded_state.rows))
        self.assertEqual(summaries, [])

    def test_same_namespace_lock_fails_before_writer_construction(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)

            @contextmanager
            def contended_lock(**_kwargs):
                raise AppliedStateError("approved apply is already in progress for namespace 'site-example-com-v1'")
                yield

            with patch("buoy_search.apply.acquire_namespace_apply_lock", contended_lock), patch(
                "buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("already in progress", stderr)
        self.assertEqual(FakeWriter.rows, [])

    def test_different_namespaces_have_independent_apply_locks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_root = Path(tmp) / "state"
            with acquire_namespace_apply_lock(site_id="example-com", namespace="site-one-v1", state_root=state_root):
                with acquire_namespace_apply_lock(site_id="example-com", namespace="site-two-v1", state_root=state_root):
                    pass

    def test_depth_one_pipeline_overlaps_main_thread_embedding_with_one_ordered_writer(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_three_row_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            main_thread = threading.get_ident()
            write_started = threading.Event()
            release_first_write = threading.Event()

            class OverlapEmbedder:
                calls = 0
                thread_ids: list[int] = []

                def __init__(self, _model_name: str, *, precision: str = "float32") -> None:
                    self.precision = precision

                def encode(self, texts, *, batch_size: int = 32):
                    del batch_size
                    OverlapEmbedder.calls += 1
                    OverlapEmbedder.thread_ids.append(threading.get_ident())
                    if OverlapEmbedder.calls == 2:
                        self.assert_event(write_started)
                        release_first_write.set()
                    return [[float(index), 0.0, 1.0] for index, _ in enumerate(texts, start=1)]

                @staticmethod
                def assert_event(event: threading.Event) -> None:
                    if not event.wait(2):
                        raise AssertionError("first write did not overlap second embedding batch")

            class OrderedWriter:
                calls: list[list[str]] = []
                thread_ids: list[int] = []
                active = 0
                max_active = 0
                lock = threading.Lock()

                def __init__(self, *, config, api_key: str, schema=None) -> None:
                    del config, api_key, schema

                def upsert_rows(self, rows):
                    row_ids = [str(row["id"]) for row in rows]
                    with OrderedWriter.lock:
                        OrderedWriter.active += 1
                        OrderedWriter.max_active = max(OrderedWriter.max_active, OrderedWriter.active)
                    try:
                        OrderedWriter.thread_ids.append(threading.get_ident())
                        if not OrderedWriter.calls:
                            write_started.set()
                            if not release_first_write.wait(2):
                                raise AssertionError("second embedding batch did not run during first write")
                        OrderedWriter.calls.append(row_ids)
                    finally:
                        with OrderedWriter.lock:
                            OrderedWriter.active -= 1

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", OverlapEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", OrderedWriter):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=1,
                )

        expected_ids = [record.row_id for record in verified.diff.rows_to_upsert_records]
        self.assertEqual([row_id for call in OrderedWriter.calls for row_id in call], expected_ids)
        self.assertEqual(OverlapEmbedder.thread_ids, [main_thread, main_thread, main_thread])
        self.assertTrue(all(thread_id != main_thread for thread_id in OrderedWriter.thread_ids))
        self.assertEqual(OrderedWriter.max_active, 1)
        self.assertEqual(summary["rows_upserted"], 3)
        self.assertEqual(summary["timing"]["pipeline_mode"], "depth_one")

    def test_depth_one_pipeline_discards_prepared_batch_after_prior_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_three_row_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            write_started = threading.Event()
            second_encoded = threading.Event()
            progress: list[str] = []

            class TwoBatchEmbedder:
                calls = 0

                def __init__(self, _model_name: str, *, precision: str = "float32") -> None:
                    self.precision = precision

                def encode(self, texts, *, batch_size: int = 32):
                    del batch_size
                    TwoBatchEmbedder.calls += 1
                    if TwoBatchEmbedder.calls == 2:
                        if not write_started.wait(2):
                            raise AssertionError("first write did not start")
                        second_encoded.set()
                    return [[1.0, 0.0, 1.0] for _ in texts]

            class FailingFirstWriter:
                calls = 0

                def __init__(self, *, config, api_key: str, schema=None) -> None:
                    del config, api_key, schema

                def upsert_rows(self, rows):
                    del rows
                    FailingFirstWriter.calls += 1
                    write_started.set()
                    if not second_encoded.wait(2):
                        raise AssertionError("second batch was not prepared during first write")
                    raise RuntimeError("late first write failure")

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", TwoBatchEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FailingFirstWriter):
                with self.assertRaisesRegex(RuntimeError, "late first write failure"):
                    run_approved_apply(
                        verified,
                        config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                        namespace=artifacts.manifest.namespace,
                        batch_size=1,
                        progress_callback=progress.append,
                    )
            state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertEqual(TwoBatchEmbedder.calls, 2)
        self.assertEqual(FailingFirstWriter.calls, 1)
        self.assertFalse(any("embedding/upserting" in message for message in progress))
        self.assertTrue(state.first_apply)

    def test_depth_one_pipeline_awaits_prior_write_when_embedding_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_three_row_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            write_started = threading.Event()
            release_write = threading.Event()
            write_finished = threading.Event()

            class FailingSecondEmbedder:
                calls = 0

                def __init__(self, _model_name: str, *, precision: str = "float32") -> None:
                    self.precision = precision

                def encode(self, texts, *, batch_size: int = 32):
                    del batch_size
                    FailingSecondEmbedder.calls += 1
                    if FailingSecondEmbedder.calls == 2:
                        if not write_started.wait(2):
                            raise AssertionError("first write did not start")
                        release_write.set()
                        raise RuntimeError("second embedding failure")
                    return [[1.0, 0.0, 1.0] for _ in texts]

            class WaitingWriter:
                calls = 0

                def __init__(self, *, config, api_key: str, schema=None) -> None:
                    del config, api_key, schema

                def upsert_rows(self, rows):
                    del rows
                    WaitingWriter.calls += 1
                    write_started.set()
                    if not release_write.wait(2):
                        raise AssertionError("embedding failure did not release prior write")
                    write_finished.set()

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FailingSecondEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", WaitingWriter):
                with self.assertRaisesRegex(RuntimeError, "second embedding failure"):
                    run_approved_apply(
                        verified,
                        config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                        namespace=artifacts.manifest.namespace,
                        batch_size=1,
                    )
            state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertTrue(write_finished.is_set())
        self.assertEqual(FailingSecondEmbedder.calls, 2)
        self.assertEqual(WaitingWriter.calls, 1)
        self.assertTrue(state.first_apply)

    def test_depth_one_pipeline_executor_failure_occurs_before_embedding_or_writes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FakeWriter), patch(
                "buoy_search.apply.ThreadPoolExecutor", side_effect=RuntimeError("executor unavailable")
            ):
                with self.assertRaisesRegex(RuntimeError, "executor unavailable"):
                    run_approved_apply(
                        verified,
                        config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                        namespace=artifacts.manifest.namespace,
                        batch_size=1,
                    )
            state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertEqual(FakeEmbedder.texts, [])
        self.assertEqual(FakeWriter.rows, [])
        self.assertTrue(state.first_apply)

    def test_depth_one_pipeline_preserves_zero_and_one_batch_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            main_thread = threading.get_ident()

            class ThreadRecordingWriter(FakeWriter):
                thread_ids: list[int] = []
                call_count = 0

                def upsert_rows(self, rows):
                    ThreadRecordingWriter.thread_ids.append(threading.get_ident())
                    ThreadRecordingWriter.call_count += 1
                    super().upsert_rows(rows)

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", ThreadRecordingWriter):
                one_batch = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=64,
                )

            verified_zero = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", side_effect=AssertionError("embedder called")
            ), patch("buoy_search.apply.TurbopufferWriter", side_effect=AssertionError("writer called")):
                zero_batch = run_approved_apply(
                    verified_zero,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=64,
                )

        self.assertEqual(ThreadRecordingWriter.call_count, 1)
        self.assertTrue(all(thread_id != main_thread for thread_id in ThreadRecordingWriter.thread_ids))
        self.assertEqual(one_batch["rows_upserted"], 2)
        self.assertEqual(one_batch["timing"]["pipeline_mode"], "depth_one")
        self.assertEqual(zero_batch["rows_to_upsert"], 0)
        self.assertEqual(zero_batch["rows_upserted"], 0)
        self.assertEqual(zero_batch["embeddings_generated"], 0)
        self.assertEqual(zero_batch["timing"]["pipeline_mode"], "depth_one")

    def test_approved_apply_reports_controlled_stage_timings_and_batch_sizes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            main_clock = iter([0.0, 1.0, 3.0, 4.0, 6.0, 7.0, 8.0, 17.0])
            write_clock = iter([10.0, 13.0, 20.0, 26.0])

            def clock() -> float:
                if threading.current_thread().name.startswith("buoy-upsert"):
                    return next(write_clock)
                return next(main_clock)

            progress: list[str] = []
            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FakeWriter):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=1,
                    embedding_batch_size=7,
                    progress_callback=progress.append,
                    monotonic=clock,
                )

        self.assertEqual(FakeEmbedder.batch_sizes, [7, 7])
        self.assertEqual(
            summary["timing"],
            {
                "elapsed_seconds": 17.0,
                "embedding_seconds": 4.0,
                "write_seconds": 9.0,
                "embedding_batch_size": 7,
                "write_batch_size": 1,
                "embedding_precision": "float32",
                "pipeline_mode": "depth_one",
            },
        )
        self.assertIn(
            "apply: embedding/upserting batches=2/2; rows=2/2; elapsed=8.0s; embedding=4.0s; write=9.0s",
            progress,
        )

    def test_timing_failure_after_successful_upsert_does_not_prevent_state_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            clock = iter([0.0, 1.0, 2.0, 3.0])

            def failing_after_upsert_clock() -> float:
                if FakeWriter.rows:
                    raise OSError("simulated timing failure")
                return next(clock)

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FakeWriter):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=2,
                    monotonic=failing_after_upsert_clock,
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertEqual(len(FakeWriter.rows), 2)
        self.assertEqual(len(loaded_state.rows), 2)
        self.assertTrue(summary["state_updated"])
        self.assertEqual(summary["timing"]["write_seconds"], 0.0)

    def test_delete_only_apply_times_delete_and_reports_post_success_diagnostics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            _previous, artifacts, plan_path, stale = build_one_page_plan_with_stale_state(root, state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            clock = iter([0.0, 1.0, 4.0, 5.0, 6.0])
            progress: list[str] = []
            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=64,
                    delete_stale=True,
                    progress_callback=progress.append,
                    monotonic=lambda: next(clock),
                )

        self.assertEqual(FakeWriter.rows, [])
        self.assertEqual(FakeWriter.deletes, [stale.row_id])
        self.assertEqual(summary["rows_deleted"], 1)
        self.assertEqual(summary["timing"]["embedding_seconds"], 0.0)
        self.assertEqual(summary["timing"]["write_seconds"], 3.0)
        self.assertEqual(summary["timing"]["elapsed_seconds"], 6.0)
        self.assertIn(
            "apply: deleted stale rows=1; elapsed=5.0s; embedding=0.0s; write=3.0s",
            progress,
        )

    def test_approved_apply_tty_progress_reports_phases_and_each_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, stdout, stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--batch-size",
                        "1",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stderr=TtyStringIO(),
                )

        self.assertEqual(result, 0, stderr)
        self.assertIn("timing: elapsed=", stdout)
        self.assertIn("embedding_batch_size=32; write_batch_size=1", stdout)
        self.assertIn("pipeline=depth_one", stdout)
        rendered = stderr.replace("\x1b[K", "")
        self.assertIn("\rapply: verifying plan", rendered)
        self.assertIn("\rapply: acquiring namespace lock", rendered)
        self.assertIn(
            "\rapply: preparing; rows=2; batches=2; embedding_batch=32; write_batch=1",
            rendered,
        )
        self.assertIn("\rapply: embedding/upserting batches=1/2; rows=1/2; elapsed=", rendered)
        self.assertIn("\rapply: embedding/upserting batches=2/2; rows=2/2", rendered)
        self.assertIn("\rapply: committing local state", rendered)
        self.assertIn("\rapply: cleaning up successful plan", rendered)
        self.assertNotIn("\n", rendered)

    def test_apply_preflight_tty_shows_verification_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            result, _stdout, stderr = self.run_main(
                [
                    "apply",
                    "--dry-run",
                    "--plan",
                    str(plan_path),
                    "--namespace",
                    artifacts.manifest.namespace,
                    "--state-root",
                    str(state_root),
                ],
                stderr=TtyStringIO(),
            )

        self.assertEqual(result, 0, stderr)
        rendered = stderr.replace("\x1b[K", "")
        self.assertIn("\rapply: verifying plan", rendered)
        self.assertNotIn("embedding/upsert", rendered)
        self.assertNotIn("committing local state", rendered)
        self.assertNotIn("\n", rendered)

    def test_apply_progress_is_suppressed_for_json_and_no_progress(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                json_result, json_stdout, json_stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                        "--json",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stderr=TtyStringIO(),
                )
            artifacts, plan_path = build_saved_plan(root / "no-progress", state_root=root / "state-no-progress")
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                quiet_result, _quiet_stdout, quiet_stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(root / "state-no-progress"),
                        "--approve",
                        "--no-progress",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stderr=TtyStringIO(),
                )

        self.assertEqual(json_result, 0, json_stderr)
        self.assertTrue(json.loads(json_stdout)["approved"])
        self.assertEqual(json_stderr, "")
        self.assertEqual(quiet_result, 0, quiet_stderr)
        self.assertEqual(quiet_stderr, "")

    def test_progress_callback_failure_after_upsert_does_not_prevent_state_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )

            def failing_progress(_message: str) -> None:
                raise OSError("simulated progress failure")

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FakeWriter):
                summary = run_approved_apply(
                    verified,
                    config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                    namespace=artifacts.manifest.namespace,
                    batch_size=1,
                    progress_callback=failing_progress,
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertEqual(summary["rows_upserted"], 2)
        self.assertEqual(len(FakeWriter.rows), 2)
        self.assertFalse(loaded_state.first_apply)
        self.assertEqual(
            {row.row_id for row in loaded_state.rows if row.status == ROW_STATUS_ACTIVE},
            {chunk.row_id for chunk in artifacts.manifest.chunks},
        )

    def test_progress_callback_failure_does_not_mask_apply_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            verified = load_verified_apply_plan(
                plan_path=plan_path,
                namespace=artifacts.manifest.namespace,
                state_root=state_root,
            )
            FakeWriter.should_fail = True

            def failing_progress(_message: str) -> None:
                raise OSError("simulated progress failure")

            with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "test-key"}, clear=True), patch(
                "buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder
            ), patch("buoy_search.apply.TurbopufferWriter", FakeWriter):
                with self.assertRaisesRegex(RuntimeError, "fake upsert failure"):
                    run_approved_apply(
                        verified,
                        config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                        namespace=artifacts.manifest.namespace,
                        batch_size=1,
                        progress_callback=failing_progress,
                    )

    def test_apply_tty_progress_stream_failure_does_not_prevent_state_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, _stdout, _stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stderr=FailingTtyStringIO(),
                )
            loaded_state = load_applied_state(
                site_id=artifacts.manifest.site_id,
                namespace=artifacts.manifest.namespace,
                base_url=artifacts.manifest.base_url,
                state_root=state_root,
            )

        self.assertEqual(result, 0)
        self.assertFalse(loaded_state.first_apply)
        self.assertEqual(len(FakeWriter.rows), 2)

    def test_apply_tty_progress_stream_failure_does_not_mask_upsert_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            FakeWriter.should_fail = True
            with patch("buoy_search.apply.SentenceTransformerEmbedder", FakeEmbedder), patch(
                "buoy_search.apply.TurbopufferWriter", FakeWriter
            ):
                result, _stdout, _stderr = self.run_main(
                    [
                        "apply",
                        "--plan",
                        str(plan_path),
                        "--namespace",
                        artifacts.manifest.namespace,
                        "--state-root",
                        str(state_root),
                        "--approve",
                    ],
                    env={"TURBOPUFFER_API_KEY": "test-key"},
                    stderr=FailingTtyStringIO(),
                )

        self.assertEqual(result, 2)
        self.assertEqual(FakeWriter.rows, [])

    def test_apply_text_output_suppresses_progress_when_stderr_is_not_a_tty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, plan_path = build_saved_plan(root, state_root=state_root)
            result, _stdout, stderr = self.run_main(
                [
                    "apply",
                    "--dry-run",
                    "--plan",
                    str(plan_path),
                    "--namespace",
                    artifacts.manifest.namespace,
                    "--state-root",
                    str(state_root),
                ]
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(stderr, "")


if __name__ == "__main__":
    unittest.main()
