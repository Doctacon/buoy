from __future__ import annotations

import json
import tempfile
from pathlib import Path
import unittest

from buoy_search.evals import EvalCase, RepoEvalScore, aggregate_repo_scores, hit_summary, load_eval_cases, score_hits, score_repo_hits
from buoy_search.retriever import SearchHit


BUOY_REPO_EVAL_DATASET = Path("src/buoy_search/data/buoy_search_repo_search_seed_evals.json")
VALIDATION_BASKET_EVAL_DATASETS = (
    Path("src/buoy_search/data/pytest_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/typer_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/ruff_site_search_seed_evals.json"),
    Path("src/buoy_search/data/typer_site_search_seed_evals.json"),
)
EXPANDED_REPO_EVAL_DATASETS = (
    Path("src/buoy_search/data/black_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/ruff_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/flask_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/django_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/pydantic_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/httpx_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/mkdocs_repo_search_seed_evals.json"),
    Path("src/buoy_search/data/rich_repo_search_seed_evals.json"),
)
EXPECTED_BUOY_COVERAGE_AREAS = {
    "github_repository_ingestion_flow",
    "plan_apply_safety_local_only_behavior",
    "retrieval_command_behavior",
    "chunking_artifact_generation",
    "eval_autoresearch_behavior",
}


class EvalHarnessTests(unittest.TestCase):
    def test_loads_builtin_smoke_eval_dataset(self) -> None:
        cases = load_eval_cases()

        self.assertGreaterEqual(len(cases), 4)
        questions = {case.question for case in cases}
        self.assertIn("How should I choose between Scrapling fetchers?", questions)
        self.assertIn("How does Scrapling LinkExtractor filter links by allow and deny patterns?", questions)
        for case in cases:
            self.assertTrue(case.expected_urls or case.expected_topics)

    def test_loads_scrapling_smoke_eval_dataset(self) -> None:
        cases = load_eval_cases(Path("src/buoy_search/data/scrapling_retrieval_smoke_evals.json"))

        self.assertGreaterEqual(len(cases), 4)
        questions = {case.question for case in cases}
        self.assertIn("How does Scrapling LinkExtractor filter links by allow and deny patterns?", questions)
        self.assertTrue(any("scrapling.readthedocs.io" in url for case in cases for url in case.expected_urls))
        for case in cases:
            self.assertTrue(case.expected_urls or case.expected_topics)

    def test_loads_expanded_validation_basket_eval_datasets(self) -> None:
        for dataset in VALIDATION_BASKET_EVAL_DATASETS:
            with self.subTest(dataset=str(dataset)):
                cases = load_eval_cases(dataset)

                self.assertGreaterEqual(len(cases), 8)
                for case in cases:
                    self.assertTrue(case.judgments)
                    self.assertTrue(all(judgment.grade > 0 for judgment in case.judgments))

    def test_loads_expanded_repo_eval_datasets(self) -> None:
        for dataset in EXPANDED_REPO_EVAL_DATASETS:
            with self.subTest(dataset=str(dataset)):
                cases = load_eval_cases(dataset)

                self.assertGreaterEqual(len(cases), 5)
                for case in cases:
                    self.assertTrue(case.judgments)
                    self.assertTrue(all(judgment.repo_path for judgment in case.judgments))
                    self.assertTrue(all(judgment.grade > 0 for judgment in case.judgments))

    def test_score_hits_passes_on_expected_url_in_top_k(self) -> None:
        case = EvalCase(
            id="fetchers",
            question="How should I choose a fetcher?",
            expected_urls=("https://scrapling.readthedocs.io/en/latest/fetching/choosing.html",),
            expected_topics=("Fetchers basics",),
        )

        score = score_hits(
            case,
            [
                SearchHit(
                    id="1",
                    title="Fetchers basics",
                    url="https://scrapling.readthedocs.io/en/latest/fetching/choosing.html",
                    section_path="Fetchers basics",
                )
            ],
        )

        self.assertTrue(score.passed)
        self.assertEqual(score.matched_rank, 1)
        self.assertEqual(score.matched_url, "https://scrapling.readthedocs.io/en/latest/fetching/choosing.html")

    def test_score_hits_passes_on_expected_topic_in_title_or_content(self) -> None:
        case = EvalCase(
            id="link-extractor",
            question="How does LinkExtractor filter links?",
            expected_urls=(),
            expected_topics=("allow_domains",),
        )

        score = score_hits(
            case,
            [
                {
                    "title": "Generic templates",
                    "url": "https://scrapling.readthedocs.io/en/latest/spiders/generic-templates.html",
                    "content": "LinkExtractor supports allow, deny, and allow_domains filters.",
                }
            ],
        )

        self.assertTrue(score.passed)
        self.assertEqual(score.matched_rank, 1)
        self.assertEqual(score.matched_topic, "allow_domains")

    def test_load_eval_cases_accepts_graded_repo_judgments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "repo-evals.json"
            dataset.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "id": "github-routing",
                                "question": "Where is GitHub repo URL routing implemented?",
                                "judgments": [
                                    {
                                        "repo_path": "src/buoy_search/crawler.py",
                                        "grade": 3,
                                        "reason": "Source detection lives here.",
                                    },
                                    {
                                        "repo_path": "tests/test_crawler.py",
                                        "grade": 2,
                                        "reason": "Tests document expected routing behavior.",
                                    },
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            cases = load_eval_cases(dataset)

        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].judgments[0].repo_path, "src/buoy_search/crawler.py")
        self.assertEqual(cases[0].judgments[0].grade, 3)

    def test_score_repo_hits_perfect_ranking_gets_full_composite_score(self) -> None:
        case = graded_case()

        score = score_repo_hits(
            case,
            [
                {"path": "src/buoy_search/crawler.py", "url": "https://github.com/owner/repo/blob/main/src/buoy_search/crawler.py"},
                {"source_metadata": {"repo_path": "tests/test_crawler.py"}},
                {"url": "https://github.com/owner/repo/blob/main/README.md"},
            ],
        )

        self.assertAlmostEqual(score.ndcg_at_10, 1.0)
        self.assertAlmostEqual(score.recall_at_10, 1.0)
        self.assertAlmostEqual(score.mrr_at_10, 1.0)
        self.assertAlmostEqual(score.precision_at_5, 1.0)
        self.assertEqual(score.repo_search_score, 100.0)
        self.assertEqual(score.matched_rank, 1)

    def test_aggregate_repo_score_is_clamped_to_documented_range(self) -> None:
        metrics = aggregate_repo_scores(
            [
                RepoEvalScore(
                    ndcg_at_10=1.0,
                    recall_at_10=1.0,
                    mrr_at_10=1.0,
                    precision_at_5=1.0,
                    repo_search_score=100.00000000000001,
                    matched_rank=1,
                    matched_judgments=(),
                )
            ]
        )

        self.assertEqual(metrics["repo_search_score"], 100.0)

    def test_hit_summary_includes_path_and_repo_path_locators(self) -> None:
        summary = hit_summary(
            {
                "title": "repo file",
                "path": "generated-page.md",
                "source_metadata": {"repo_path": "src/buoy_search/evals.py"},
            },
            1,
        )

        self.assertEqual(summary["path"], "generated-page.md")
        self.assertEqual(summary["repo_path"], "src/buoy_search/evals.py")

    def test_score_repo_hits_partial_ranking_uses_grades_and_ranks(self) -> None:
        case = graded_case()

        score = score_repo_hits(
            case,
            [
                {"path": "docs/unrelated.md"},
                {"source_metadata": {"repo_path": "tests/test_crawler.py"}},
                {"source_metadata": {"repo_path": "tests/test_crawler.py"}},
                {"path": "src/buoy_search/crawler.py"},
            ],
        )

        ideal_dcg = 7.0 + (3.0 / 1.584962500721156) + (1.0 / 2.0)
        observed_dcg = (3.0 / 1.584962500721156) + (7.0 / 2.321928094887362)
        expected_ndcg = observed_dcg / ideal_dcg
        expected_score = 100.0 * (
            0.55 * expected_ndcg
            + 0.20 * (2.0 / 3.0)
            + 0.15 * 0.5
            + 0.10 * 0.5
        )
        self.assertAlmostEqual(score.ndcg_at_10, expected_ndcg)
        self.assertAlmostEqual(score.recall_at_10, 2.0 / 3.0)
        self.assertAlmostEqual(score.mrr_at_10, 0.5)
        self.assertAlmostEqual(score.precision_at_5, 0.5)
        self.assertAlmostEqual(score.repo_search_score, expected_score)
        self.assertEqual(score.matched_rank, 2)

    def test_score_repo_hits_no_match_scores_zero(self) -> None:
        score = score_repo_hits(graded_case(), [{"path": "src/buoy_search/apply.py"}])

        self.assertFalse(score.passed)
        self.assertEqual(score.matched_rank, None)
        self.assertEqual(score.ndcg_at_10, 0.0)
        self.assertEqual(score.recall_at_10, 0.0)
        self.assertEqual(score.mrr_at_10, 0.0)
        self.assertEqual(score.precision_at_5, 0.0)
        self.assertEqual(score.repo_search_score, 0.0)

    def test_score_repo_hits_does_not_credit_duplicate_hits_twice(self) -> None:
        case = EvalCase.from_mapping(
            {
                "id": "duplicate",
                "question": "Where is source routing implemented?",
                "judgments": [
                    {
                        "repo_path": "src/buoy_search/crawler.py",
                        "grade": 3,
                    }
                ],
            }
        )

        score = score_repo_hits(
            case,
            [
                {"path": "src/buoy_search/crawler.py"},
                {"path": "src/buoy_search/crawler.py"},
            ],
        )

        self.assertAlmostEqual(score.ndcg_at_10, 1.0)
        self.assertAlmostEqual(score.recall_at_10, 1.0)
        self.assertAlmostEqual(score.mrr_at_10, 1.0)
        self.assertAlmostEqual(score.precision_at_5, 0.5)

    def test_score_repo_hits_honors_section_path_when_provided(self) -> None:
        case = EvalCase.from_mapping(
            {
                "id": "section",
                "question": "Where is the composite score specified?",
                "judgments": [
                    {
                        "repo_path": ".10x/specs/repo-search-eval-autoresearch.md",
                        "section_path": "Composite score",
                        "grade": 3,
                    }
                ],
            }
        )

        wrong_section = score_repo_hits(
            case,
            [
                {
                    "path": ".10x/specs/repo-search-eval-autoresearch.md",
                    "section_path": "Safety",
                }
            ],
        )
        right_section = score_repo_hits(
            case,
            [
                {
                    "path": ".10x/specs/repo-search-eval-autoresearch.md",
                    "section_path": "Behavior > Composite score",
                }
            ],
        )

        self.assertFalse(wrong_section.passed)
        self.assertTrue(right_section.passed)

    def test_loads_buoy_search_seed_repo_eval_dataset(self) -> None:
        cases = load_eval_cases(BUOY_REPO_EVAL_DATASET)
        raw = json.loads(BUOY_REPO_EVAL_DATASET.read_text(encoding="utf-8"))

        self.assertGreaterEqual(len(cases), 8)
        self.assertEqual(raw["metadata"]["status"], "seed-draft")
        self.assertFalse(raw["metadata"]["human_approved_ground_truth"])
        coverage_areas = {case["coverage_area"] for case in raw["cases"]}
        self.assertTrue(EXPECTED_BUOY_COVERAGE_AREAS.issubset(coverage_areas))
        case_ids = {case.id for case in cases}
        self.assertIn("github-url-routing", case_ids)
        self.assertIn("plan-command-local-only", case_ids)
        self.assertIn("retrieval-hybrid-command", case_ids)
        self.assertIn("evals-composite-metrics", case_ids)

    def test_buoy_search_seed_repo_eval_judgments_are_graded_and_draft(self) -> None:
        cases = load_eval_cases(BUOY_REPO_EVAL_DATASET)

        for case in cases:
            with self.subTest(case=case.id):
                self.assertGreaterEqual(len(case.judgments), 2)
                self.assertTrue(any(judgment.grade == 3 for judgment in case.judgments))
                self.assertTrue(any(judgment.grade in {1, 2} for judgment in case.judgments))
                for judgment in case.judgments:
                    self.assertIsNotNone(judgment.repo_path)
                    self.assertIsNotNone(judgment.reason)
                    self.assertIn(judgment.grade, {0, 1, 2, 3})
                    assert judgment.repo_path is not None
                    self.assertTrue(Path(judgment.repo_path).exists(), judgment.repo_path)

    def test_load_eval_cases_rejects_missing_expected_hints(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "evals.json"
            dataset.write_text(json.dumps([{"id": "bad", "question": "Missing hints?"}]), encoding="utf-8")

            with self.assertRaises(ValueError):
                load_eval_cases(dataset)

    def test_load_eval_cases_rejects_invalid_graded_judgments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = Path(tmp) / "evals.json"
            dataset.write_text(
                json.dumps(
                    [
                        {
                            "id": "bad-grade",
                            "question": "Invalid grade?",
                            "judgments": [{"repo_path": "README.md", "grade": 4}],
                        }
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "invalid grade"):
                load_eval_cases(dataset)


def graded_case() -> EvalCase:
    return EvalCase.from_mapping(
        {
            "id": "repo-routing",
            "question": "Where is GitHub repo URL routing implemented?",
            "judgments": [
                {"repo_path": "src/buoy_search/crawler.py", "grade": 3},
                {"repo_path": "tests/test_crawler.py", "grade": 2},
                {"url": "https://github.com/owner/repo/blob/main/README.md", "grade": 1},
                {"repo_path": "docs/unrelated.md", "grade": 0},
            ],
        }
    )


if __name__ == "__main__":
    unittest.main()
