from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from buoy_search.multi_corpus_evals import (
    CATEGORY_COUNTS,
    DEFAULT_MULTI_CORPUS_EVAL_DATASET,
    EvalHit,
    RouteObservation,
    load_multi_corpus_eval_dataset,
    score_retrieval,
    score_routing,
)


class MultiCorpusEvalDatasetTests(unittest.TestCase):
    def test_approved_basket_has_fixed_governed_shape(self) -> None:
        dataset = load_multi_corpus_eval_dataset()

        self.assertEqual(len(dataset.cases), 50)
        self.assertTrue(dataset.human_approved_ground_truth)
        self.assertEqual(dataset.review_status, "approved")
        self.assertEqual(
            dataset.eligible_namespaces,
            (
                "site-dagster-io-v1",
                "site-oscilar-com-v1",
                "site-turbopuffer-com-v1",
                "site-www-thistle-co-v1",
            ),
        )
        self.assertEqual(
            dataset.disabled_duplicate_namespaces,
            ("site-dagster-io-benchmark-v1",),
        )
        self.assertEqual(
            {
                category: sum(case.category == category for case in dataset.cases)
                for category in CATEGORY_COUNTS
            },
            CATEGORY_COUNTS,
        )
        self.assertNotIn(
            "site-dagster-io-benchmark-v1",
            {
                namespace
                for case in dataset.cases
                for namespace in case.expected_namespaces
            },
        )
        self.assertNotIn(
            "site-dagster-io-benchmark-v1",
            {
                judgment.namespace
                for case in dataset.cases
                for judgment in case.judgments
            },
        )

    def test_human_approval_flag_and_review_status_must_agree(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        payload["review_status"] = "independently_reviewed_candidate"

        with self.assertRaisesRegex(ValueError, "review_status='approved'"):
            self._load_payload(payload)

    def test_disabled_duplicate_cannot_become_a_route_label(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        case = payload["cases"][0]
        case["expected_namespaces"] = ["site-dagster-io-benchmark-v1"]
        case["judgments"][0]["namespace"] = "site-dagster-io-benchmark-v1"

        with self.assertRaisesRegex(ValueError, "disabled or unknown expected namespace"):
            self._load_payload(payload)

    def test_metric_wording_is_part_of_the_executable_fixture_contract(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        payload["metric_contract"]["average_automatic_fanout"] = "an ambiguous average"

        with self.assertRaisesRegex(ValueError, "metric_contract"):
            self._load_payload(payload)

    def test_judgment_url_must_belong_to_its_labeled_corpus(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        payload["cases"][0]["judgments"][0]["url"] = "https://oscilar.com/platform"

        with self.assertRaisesRegex(ValueError, "URL host"):
            self._load_payload(payload)

    def test_explicit_equivalent_url_groups_load_without_rewriting_existing_cases(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        case = payload["cases"][0]
        original = case["judgments"][0]
        original["group"] = "product-purpose"
        case["judgments"].append(
            {
                **original,
                "url": "https://dagster.io/blog/what-is-dagster-equivalent",
                "reason": "A reviewed equivalent positive for scorer coverage.",
            }
        )

        dataset = self._load_payload(payload)

        loaded_case = dataset.cases[0]
        self.assertEqual(len(loaded_case.judgments), 2)
        self.assertEqual(
            {judgment.group_key for judgment in loaded_case.judgments},
            {"product-purpose"},
        )

    def test_equivalent_group_rejects_inconsistent_grades(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        case = payload["cases"][0]
        original = case["judgments"][0]
        original["group"] = "product-purpose"
        case["judgments"].append(
            {
                **original,
                "url": "https://dagster.io/blog/what-is-dagster-equivalent",
                "grade": 2,
            }
        )

        with self.assertRaisesRegex(ValueError, "inconsistent grades"):
            self._load_payload(payload)

    def _load_payload(self, payload: dict[str, object]):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "evals.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            return load_multi_corpus_eval_dataset(path)


class MultiCorpusRoutingScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = load_multi_corpus_eval_dataset()

    def test_perfect_routes_score_micro_recall_and_all_case_fanout(self) -> None:
        observations = {
            case.id: RouteObservation(
                namespaces=case.expected_namespaces,
                high_confidence_single=len(case.expected_namespaces) == 1,
            )
            for case in self.dataset.cases
        }

        metrics = score_routing(self.dataset, observations)

        self.assertEqual(metrics.route_recall_at_3, 1.0)
        self.assertEqual(metrics.route_required_total, 58)
        self.assertEqual(metrics.route_required_found, 58)
        self.assertTrue(metrics.complete_multi_corpus_coverage)
        self.assertEqual(metrics.complete_multi_corpus_cases, 10)
        self.assertEqual(metrics.incorrect_high_confidence_single_routes, 0)
        self.assertEqual(metrics.maximum_observed_fanout, 3)
        expected_average = sum(
            len(case.expected_namespaces) for case in self.dataset.cases
        ) / 50
        self.assertEqual(metrics.average_automatic_fanout, expected_average)
        self.assertEqual(metrics.average_automatic_fanout, 1.16)

    def test_route_recall_credit_truncates_at_three_but_fanout_uses_final_route(self) -> None:
        observations = {
            case.id: RouteObservation(case.expected_namespaces)
            for case in self.dataset.cases
        }
        case = self.dataset.cases[0]
        expected = case.expected_namespaces[0]
        first_three = tuple(
            namespace for namespace in self.dataset.eligible_namespaces if namespace != expected
        )
        observations[case.id] = RouteObservation((*first_three, expected))

        metrics = score_routing(self.dataset, observations)

        self.assertLess(metrics.route_recall_at_3, 1.0)
        self.assertEqual(metrics.maximum_observed_fanout, 4)
        self.assertGreater(metrics.average_automatic_fanout, 1.0)

    def test_wrong_high_confidence_single_is_counted(self) -> None:
        observations = {
            case.id: RouteObservation(case.expected_namespaces)
            for case in self.dataset.cases
        }
        case = self.dataset.cases[0]
        wrong = next(
            namespace
            for namespace in self.dataset.eligible_namespaces
            if namespace not in case.expected_namespaces
        )
        observations[case.id] = RouteObservation((wrong,), high_confidence_single=True)

        metrics = score_routing(self.dataset, observations)

        self.assertEqual(metrics.incorrect_high_confidence_single_routes, 1)

    def test_disabled_duplicate_is_rejected_from_observed_routes(self) -> None:
        observations = {
            case.id: RouteObservation(case.expected_namespaces)
            for case in self.dataset.cases
        }
        observations[self.dataset.cases[0].id] = RouteObservation(
            ("site-dagster-io-benchmark-v1",)
        )

        with self.assertRaisesRegex(ValueError, "disabled or unknown namespace"):
            score_routing(self.dataset, observations)


class MultiCorpusRetrievalScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = load_multi_corpus_eval_dataset()

    @staticmethod
    def _judgment_hits(case) -> tuple[EvalHit, ...]:
        return tuple(EvalHit(judgment.namespace, judgment.url) for judgment in case.judgments)

    def _perfect_runs(self):
        exhaustive = {
            case.id: self._judgment_hits(case)
            for case in self.dataset.cases
        }
        automatic = dict(exhaustive)
        pre_rerank = {}
        reranked = {}
        for case in self.dataset.cases:
            if case.category != "multi_corpus":
                continue
            relevant = self._judgment_hits(case)
            junk = (
                EvalHit(
                    self.dataset.eligible_namespaces[0],
                    f"https://example.invalid/{case.id}/noise-one",
                ),
                EvalHit(
                    self.dataset.eligible_namespaces[1],
                    f"https://example.invalid/{case.id}/noise-two",
                ),
            )
            pre_rerank[case.id] = (*junk, *relevant)
            reranked[case.id] = (*relevant, *junk)
        return exhaustive, automatic, pre_rerank, reranked

    def test_exhaustive_anchored_recall_and_macro_ndcg_are_reproducible(self) -> None:
        exhaustive, automatic, pre_rerank, reranked = self._perfect_runs()

        metrics = score_retrieval(
            self.dataset,
            exhaustive_hits=exhaustive,
            automatic_hits=automatic,
            pre_rerank_hits=pre_rerank,
            reranked_hits=reranked,
        )

        self.assertEqual(metrics.automatic_recall_at_5, 1.0)
        self.assertGreater(metrics.exhaustive_positive_targets, 0)
        self.assertEqual(
            metrics.automatic_positive_targets_found,
            metrics.exhaustive_positive_targets,
        )
        self.assertEqual(metrics.pre_rerank_recall_at_5, 1.0)
        self.assertEqual(metrics.reranked_recall_at_5, 1.0)
        self.assertFalse(metrics.recall_at_5_regressed)
        self.assertGreater(metrics.ndcg_at_5_improvement, 0.03)
        self.assertEqual(metrics.reranked_ndcg_at_5, 1.0)
        self.assertEqual(metrics.multi_corpus_case_total, 10)

    def test_rerank_recall_regression_is_explicit(self) -> None:
        exhaustive, automatic, pre_rerank, reranked = self._perfect_runs()
        case = next(case for case in self.dataset.cases if case.category == "multi_corpus")
        reranked[case.id] = reranked[case.id][1:]

        metrics = score_retrieval(
            self.dataset,
            exhaustive_hits=exhaustive,
            automatic_hits=automatic,
            pre_rerank_hits=pre_rerank,
            reranked_hits=reranked,
        )

        self.assertTrue(metrics.recall_at_5_regressed)
        self.assertLess(metrics.reranked_recall_at_5, metrics.pre_rerank_recall_at_5)

    def test_exhaustive_baseline_excludes_a_judgment_it_did_not_find(self) -> None:
        exhaustive, automatic, pre_rerank, reranked = self._perfect_runs()
        case = next(case for case in self.dataset.cases if len(case.judgments) > 1)
        original_target_count = sum(
            len({judgment.group_key for judgment in item.judgments})
            for item in self.dataset.cases
        )
        removed_group = case.judgments[0].group_key
        exhaustive[case.id] = tuple(
            hit
            for hit, judgment in zip(
                exhaustive[case.id], case.judgments, strict=True
            )
            if judgment.group_key != removed_group
        )

        metrics = score_retrieval(
            self.dataset,
            exhaustive_hits=exhaustive,
            automatic_hits=automatic,
            pre_rerank_hits=pre_rerank,
            reranked_hits=reranked,
        )

        self.assertEqual(metrics.exhaustive_positive_targets, original_target_count - 1)
        self.assertEqual(metrics.automatic_recall_at_5, 1.0)

    def test_any_equivalent_url_recalls_one_group_and_duplicate_gain_is_not_awarded(self) -> None:
        payload = json.loads(DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8"))
        raw_case = next(case for case in payload["cases"] if case["category"] == "multi_corpus")
        original = raw_case["judgments"][0]
        original["group"] = "shared-facet"
        alternative = {
            **original,
            "url": original["url"].rstrip("/") + "-equivalent",
            "reason": "A second reviewed URL satisfying the same answer facet.",
        }
        raw_case["judgments"].append(alternative)
        dataset = MultiCorpusEvalDatasetTests()._load_payload(payload)
        exhaustive = {
            case.id: tuple(EvalHit(j.namespace, j.url) for j in case.judgments)
            for case in dataset.cases
        }
        automatic = dict(exhaustive)
        pre_rerank = {}
        reranked = {}
        grouped_case = dataset.cases_by_id[raw_case["id"]]
        for case in dataset.cases:
            if case.category != "multi_corpus":
                continue
            hits = tuple(EvalHit(j.namespace, j.url) for j in case.judgments)
            pre_rerank[case.id] = hits
            reranked[case.id] = hits

        # Exhaustive sees only the alternative URL for this group, while the
        # automatic result sees only the original. Both satisfy the same facet.
        original_hit = EvalHit(
            grouped_case.judgments[0].namespace,
            grouped_case.judgments[0].url,
        )
        alternative_hit = EvalHit(
            grouped_case.judgments[-1].namespace,
            grouped_case.judgments[-1].url,
        )
        exhaustive[grouped_case.id] = tuple(
            hit
            for hit in exhaustive[grouped_case.id]
            if hit != original_hit
        )
        automatic[grouped_case.id] = tuple(
            hit
            for hit in automatic[grouped_case.id]
            if hit != alternative_hit
        )
        remaining_group_hits = tuple(
            hit
            for hit in reranked[grouped_case.id]
            if hit not in {original_hit, alternative_hit}
        )
        reranked[grouped_case.id] = (
            original_hit,
            alternative_hit,
            *remaining_group_hits,
        )

        metrics = score_retrieval(
            dataset,
            exhaustive_hits=exhaustive,
            automatic_hits=automatic,
            pre_rerank_hits=pre_rerank,
            reranked_hits=reranked,
        )

        expected_groups = sum(
            len({judgment.group_key for judgment in case.judgments})
            for case in dataset.cases
        )
        self.assertEqual(metrics.exhaustive_required_groups, expected_groups)
        self.assertEqual(metrics.automatic_recall_at_5, 1.0)
        # The duplicate equivalent occupies a ranked slot but earns no second gain.
        self.assertLess(metrics.reranked_ndcg_at_5, 1.0)


if __name__ == "__main__":
    unittest.main()
