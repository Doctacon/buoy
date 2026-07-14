from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
import json
import tempfile
from pathlib import Path
import unittest

from buoy_search.autoresearch import AutoresearchExperimentError, load_experiment, main, run_experiment


SAMPLE_EXPERIMENT = Path("autoresearch/experiments/repo-search-fixture-baseline.json")
LIVE_EXPERIMENT = Path("autoresearch/experiments/repo-search-live-baseline.json")


class AutoresearchRunnerTests(unittest.TestCase):
    def test_load_experiment_validates_required_config_only_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = write_experiment(root, fixture_hits={"case-a": [{"path": "README.md"}]})

            experiment = load_experiment(experiment_path)

        self.assertEqual(experiment.experiment_id, "fixture-baseline")
        self.assertEqual(experiment.mode, "fixture")
        self.assertEqual(experiment.config.namespace, "github-owner-buoy-search-v1")
        self.assertEqual(experiment.retrieval_options.top_k, 5)
        self.assertEqual(experiment.retrieval_options.ranking_mode, "file")
        self.assertEqual(experiment.retrieval_options.ranking_profile, "repo_code")
        self.assertEqual(experiment.retrieval_options.ranking_pool, 100)
        self.assertEqual(experiment.retrieval_options.ranking_aggregation, "adaptive_sum_3")
        self.assertEqual(experiment.fixture_hits["case-a"][0]["path"], "README.md")

    def test_load_experiment_uses_website_defaults_for_site_namespace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = write_experiment(
                root,
                extra={
                    "config": {
                        "namespace": "site-example-com-v1",
                        "region": "gcp-us-central1",
                        "embedding_model": "BAAI/bge-small-en-v1.5",
                    }
                },
                fixture_hits={"case-a": [{"url": "https://example.com/docs"}]},
            )

            experiment = load_experiment(experiment_path)

        self.assertEqual(experiment.retrieval_options.ranking_mode, "page")
        self.assertEqual(experiment.retrieval_options.ranking_profile, "none")
        self.assertEqual(experiment.retrieval_options.ranking_pool, 20)
        self.assertEqual(experiment.retrieval_options.ranking_aggregation, "max")

    def test_load_experiment_rejects_source_mutation_and_live_write_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = write_experiment(
                root,
                extra={"code_changes": ["change src/buoy_search/retriever.py"]},
                fixture_hits={"case-a": [{"path": "README.md"}]},
            )

            with self.assertRaisesRegex(AutoresearchExperimentError, "forbidden"):
                load_experiment(experiment_path)

    def test_load_experiment_rejects_command_text_that_implies_apply_or_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = write_experiment(
                root,
                extra={"command": "buoy apply --approve"},
                fixture_hits={"case-a": [{"path": "README.md"}]},
            )

            with self.assertRaisesRegex(AutoresearchExperimentError, "forbidden command token"):
                load_experiment(experiment_path)

    def test_run_fixture_experiment_writes_plan_result_and_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_path = write_dataset(root)
            experiment_path = write_experiment(
                root,
                dataset_path=dataset_path,
                fixture_hits={
                    "case-a": [
                        {
                            "path": "src/buoy_search/autoresearch.py",
                            "title": "autoresearch.py",
                            "url": "https://github.com/owner/buoy-search/blob/main/src/buoy_search/autoresearch.py",
                        },
                        {"path": "tests/test_autoresearch.py", "title": "test_autoresearch.py"},
                    ],
                    "case-b": [{"path": "src/buoy_search/evals.py", "title": "evals.py"}],
                },
            )
            experiment = load_experiment(experiment_path)
            out_dir = root / "out"

            result = run_experiment(experiment, out_dir=out_dir)

            self.assertTrue((out_dir / "plan.json").exists())
            self.assertTrue((out_dir / "result.json").exists())
            self.assertTrue((out_dir / "report.md").exists())
            self.assertEqual(result["mode"], "fixture")
            self.assertEqual(result["status"], "passed")
            self.assertFalse(result["safety"]["turbopuffer_api_calls"])
            self.assertEqual(result["eval"]["passed"], 2)
            self.assertAlmostEqual(result["repo_metrics"]["repo_search_score"], 100.0)
            report = (out_dir / "report.md").read_text(encoding="utf-8")
            self.assertIn("Composite repo search score", report)
            self.assertIn("case-a", report)
            self.assertIn("src/buoy_search/autoresearch.py", report)
            self.assertNotIn("no locator", report)

    def test_module_main_runs_one_fixture_experiment_and_prints_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_path = write_dataset(root)
            experiment_path = write_experiment(
                root,
                dataset_path=dataset_path,
                fixture_hits={
                    "case-a": [{"path": "src/buoy_search/autoresearch.py"}],
                    "case-b": [{"path": "src/buoy_search/evals.py"}],
                },
            )
            out_dir = root / "out"

            stdout = StringIO()
            with redirect_stdout(stdout):
                result_code = main(["--experiment", str(experiment_path), "--out", str(out_dir), "--json"])

            self.assertEqual(result_code, 0)
            self.assertIn('"command": "autoresearch"', stdout.getvalue())
            self.assertTrue((out_dir / "result.json").exists())
            payload = json.loads((out_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["experiment_id"], "fixture-baseline")
            self.assertTrue(payload["safety"]["config_only"])

    def test_live_mode_rejects_fixture_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            experiment_path = write_experiment(
                root,
                extra={"mode": "live"},
                fixture_hits={"case-a": [{"path": "README.md"}]},
            )

            with self.assertRaisesRegex(AutoresearchExperimentError, "live mode must not include fixture_hits"):
                load_experiment(experiment_path)

    def test_sample_fixture_experiment_runs_without_live_calls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            experiment = load_experiment(SAMPLE_EXPERIMENT)
            result = run_experiment(experiment, out_dir=Path(tmp) / "out")

        self.assertEqual(result["experiment_id"], "repo-search-fixture-baseline")
        self.assertEqual(result["mode"], "fixture")
        self.assertEqual(result["status"], "passed")
        self.assertFalse(result["safety"]["turbopuffer_api_calls"])
        self.assertAlmostEqual(result["score"], 100.0)
        self.assertEqual(result["eval"]["passed"], 10)

    def test_live_sample_preserves_pre_rebrand_remote_namespace(self) -> None:
        experiment = load_experiment(LIVE_EXPERIMENT)

        self.assertEqual(experiment.mode, "live")
        self.assertEqual(experiment.config.namespace, "github-doctacon-turbo-search-v1")
        self.assertIn("preserved pre-rebrand", experiment.question)
        self.assertIn("does not rename or recreate it", experiment.notes)


def write_dataset(root: Path) -> Path:
    dataset_path = root / "dataset.json"
    dataset_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "id": "case-a",
                        "question": "Where is the autoresearch runner implemented?",
                        "judgments": [
                            {"repo_path": "src/buoy_search/autoresearch.py", "grade": 3, "reason": "runner implementation"},
                            {"repo_path": "tests/test_autoresearch.py", "grade": 2, "reason": "runner tests"},
                        ],
                    },
                    {
                        "id": "case-b",
                        "question": "Where are repo eval metrics implemented?",
                        "judgments": [
                            {"repo_path": "src/buoy_search/evals.py", "grade": 3, "reason": "metric implementation"}
                        ],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    return dataset_path


def write_experiment(
    root: Path,
    *,
    dataset_path: Path | None = None,
    fixture_hits: dict[str, list[dict[str, object]]] | None = None,
    extra: dict[str, object] | None = None,
) -> Path:
    payload: dict[str, object] = {
        "experiment_id": "fixture-baseline",
        "question": "Does fixture retrieval score the expected repo files?",
        "hypothesis": "Expected repo paths should score highly when present in fixture hits.",
        "mode": "fixture",
        "dataset_path": str(dataset_path or write_dataset(root)),
        "config": {
            "namespace": "github-owner-buoy-search-v1",
            "region": "gcp-us-central1",
            "embedding_model": "BAAI/bge-small-en-v1.5",
        },
        "retrieval_options": {"top_k": 5, "candidates": 50, "doc_kind": None},
        "fixture_hits": fixture_hits or {},
        "notes": "baseline fixture run",
    }
    if extra:
        payload.update(extra)
    path = root / "experiment.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
