from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPT = Path("autoresearch/runs/semantic-routing-representative-20260715/evaluate.py").resolve()
SPEC = importlib.util.spec_from_file_location("semantic_routing_representative", SCRIPT)
assert SPEC and SPEC.loader
routing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(routing)


class RepresentativeSemanticRoutingTests(unittest.TestCase):
    def test_tracked_inputs_and_cards_validate_exact_13_by_90_contract(self) -> None:
        cards = routing.load_cards()
        routing.validate_cards(cards)
        questions = routing.load_questions()

        self.assertEqual([card["repo_key"] for card in cards], sorted(routing.DATASETS))
        self.assertEqual(len(cards), 13)
        self.assertEqual(len(questions), 90)
        self.assertEqual(len({question["identity"] for question in questions}), 90)
        self.assertTrue(all(question["identity"] == f"{question['repo_key']}:{question['case_id']}" for question in questions))

    def test_card_validation_fails_closed_for_bijection_public_and_contract_errors(self) -> None:
        cards = routing.load_cards()
        variants = []
        variants.append(cards[:-1])
        duplicate_key = [dict(card) for card in cards]
        duplicate_key[-1]["repo_key"] = duplicate_key[0]["repo_key"]
        variants.append(duplicate_key)
        duplicate_namespace = [dict(card) for card in cards]
        duplicate_namespace[-1]["namespace"] = duplicate_namespace[0]["namespace"]
        variants.append(duplicate_namespace)
        private = [dict(card) for card in cards]
        private[0]["public"] = False
        variants.append(private)
        incompatible = [dict(card) for card in cards]
        incompatible[0]["embedding_contract"] = {**routing.EXPECTED_CONTRACT, "revision": "mutable"}
        variants.append(incompatible)
        missing = [dict(card) for card in cards]
        del missing[0]["summary"]
        variants.append(missing)

        for variant in variants:
            with self.subTest(variant=variants.index(variant)):
                with self.assertRaises(routing.ExperimentError):
                    routing.validate_cards(variant)

    def test_card_descriptions_do_not_copy_questions_case_ids_or_file_judgments(self) -> None:
        cards = routing.load_cards()
        questions = routing.load_questions()
        descriptions = "\n".join(
            " ".join(
                [str(card["title"]), str(card["summary"]), *card["aliases"], *card["tags"]]
            ).casefold()
            for card in cards
        )
        datasets = [
            json.loads((routing.REPO_ROOT / details[1]).read_text(encoding="utf-8"))
            for details in routing.DATASETS.values()
        ]

        self.assertTrue(all(question["question"].casefold() not in descriptions for question in questions))
        self.assertTrue(all(question["case_id"].casefold() not in descriptions for question in questions))
        for dataset in datasets:
            for case in dataset["cases"]:
                for judgment in case.get("judgments", []):
                    for field in ("repo_path", "url", "section_path"):
                        locator = judgment.get(field)
                        if locator:
                            self.assertNotIn(str(locator).casefold(), descriptions)

    def test_normalization_and_complete_phrase_matching_are_canonical(self) -> None:
        self.assertEqual(routing.normalize("  ＣＬＩ___Café—TOOLS  "), "cli café tools")
        self.assertTrue(routing.contains_phrase("a click cli framework", "click cli"))
        self.assertFalse(routing.contains_phrase("a clicker cli framework", "click"))
        self.assertFalse(routing.contains_phrase("click advanced cli", "click cli"))

    def test_lexical_descriptors_are_deduplicated_and_frequency_does_not_inflate_score(self) -> None:
        cards = [
            {
                "repo_key": "alpha",
                "namespace": "n-alpha",
                "title": "Alpha",
                "aliases": ["ALPHA", "alpha tool"],
                "tags": ["tool", "tool"],
            },
            {
                "repo_key": "beta",
                "namespace": "n-beta",
                "title": "Beta",
                "aliases": [],
                "tags": [],
            },
        ]
        once = routing.lexical_rank("alpha tool", cards)
        repeated = routing.lexical_rank("alpha alpha tool alpha tool", cards)

        self.assertEqual(once[0]["raw_score"], repeated[0]["raw_score"])
        self.assertEqual(once[0]["raw_score"]["distinct_matched_descriptors"], 3)
        self.assertEqual(once[0]["raw_score"]["total_matched_token_count"], 4)
        self.assertEqual(len(once), 1)

    def test_lexical_ranking_uses_repo_key_as_final_tie_breaker(self) -> None:
        cards = [
            {"repo_key": "zeta", "namespace": "n-zeta", "title": "tool", "aliases": [], "tags": []},
            {"repo_key": "alpha", "namespace": "n-alpha", "title": "tool", "aliases": [], "tags": []},
        ]
        ranking = routing.lexical_rank("Which tool?", cards)
        self.assertEqual([item["repo_key"] for item in ranking], ["alpha", "zeta"])

    def test_semantic_ranking_with_injected_vectors_uses_cosine_and_tie_breaker(self) -> None:
        cards = [
            {"repo_key": "zeta", "namespace": "n-zeta"},
            {"repo_key": "alpha", "namespace": "n-alpha"},
            {"repo_key": "beta", "namespace": "n-beta"},
        ]
        ranking = routing.semantic_rank(
            [1.0, 0.0], cards, {"zeta": [1.0, 0.0], "alpha": [1.0, 0.0], "beta": [0.0, 1.0]}
        )
        self.assertEqual([item["repo_key"] for item in ranking], ["alpha", "zeta", "beta"])
        self.assertEqual(ranking[0]["raw_score"], 1.0)

    def test_fixed_route_fan_out_truncates_recorded_ranking_before_home_rank(self) -> None:
        ranking = [
            {"rank": rank, "repo_key": f"repo-{rank}", "namespace": f"namespace-{rank}"}
            for rank in range(1, 8)
        ]

        routed = routing.routed_top_five(ranking)

        self.assertEqual(len(routed), 5)
        self.assertEqual([item["rank"] for item in routed], [1, 2, 3, 4, 5])
        self.assertEqual(routing.home_rank(routed, "namespace-5"), 5)
        self.assertIsNone(routing.home_rank(routed, "namespace-6"))

    def test_evaluate_scores_semantic_and_hybrid_homes_outside_fan_out_as_unranked(self) -> None:
        cards = [
            {
                "repo_key": f"repo-{index}",
                "namespace": f"namespace-{index}",
                "title": f"Project {index}",
                "aliases": [],
                "tags": [],
                "summary": "project",
            }
            for index in range(1, 7)
        ]
        questions = [
            {
                "identity": "repo-6:case",
                "repo_key": "repo-6",
                "case_id": "case",
                "question": "descriptor free question",
                "home_namespace": "namespace-6",
            }
        ]
        card_vectors = [
            [1.0, 0.0],
            [0.9, 0.435889894],
            [0.8, 0.6],
            [0.7, 0.714142843],
            [0.6, 0.8],
            [0.0, 1.0],
        ]
        with patch.object(routing, "encode_float32", side_effect=[card_vectors, [[1.0, 0.0]]]):
            result = routing.evaluate(cards, questions, object())

        for strategy in ("semantic", "hybrid_rrf"):
            case = result[strategy]["cases"][0]
            self.assertEqual(len(case["rankings"]), 5)
            self.assertIsNone(case["home_namespace_rank"])
            self.assertEqual(result[strategy]["metrics"]["aggregate"]["unranked_count"], 1)

    def test_hybrid_uses_equal_weight_production_rrf_and_deterministic_ties(self) -> None:
        lexical = [
            {"rank": 1, "repo_key": "alpha", "namespace": "n-alpha"},
            {"rank": 2, "repo_key": "beta", "namespace": "n-beta"},
        ]
        semantic = [
            {"rank": 1, "repo_key": "beta", "namespace": "n-beta"},
            {"rank": 2, "repo_key": "alpha", "namespace": "n-alpha"},
            {"rank": 3, "repo_key": "gamma", "namespace": "n-gamma"},
        ]
        ranking = routing.hybrid_rank(lexical, semantic)

        self.assertEqual(routing.RRF_K, 60)
        self.assertEqual([item["repo_key"] for item in ranking], ["alpha", "beta", "gamma"])
        self.assertAlmostEqual(ranking[0]["raw_score"], 1 / 61 + 1 / 62)
        self.assertAlmostEqual(ranking[1]["raw_score"], 1 / 62 + 1 / 61)

    def test_benchmark_bias_quantifies_home_title_alias_matches_and_descriptor_free_cases(self) -> None:
        bias = routing.benchmark_bias(routing.load_cards(), routing.load_questions())

        self.assertEqual(bias["evaluated_count"], 90)
        self.assertEqual(bias["home_title_or_alias_present_count"], 79)
        self.assertEqual(bias["descriptor_free_count"], 11)
        self.assertEqual(len(bias["descriptor_free_cases"]), 11)
        self.assertEqual(
            len({case["identity"] for case in bias["descriptor_free_cases"]}),
            11,
        )

    def test_metrics_include_unranked_homes(self) -> None:
        metrics = routing.aggregate_metrics(
            [{"home_namespace_rank": 1}, {"home_namespace_rank": 3}, {"home_namespace_rank": None}]
        )
        self.assertAlmostEqual(metrics["mrr"], (1 + 1 / 3) / 3)
        self.assertEqual(metrics["recall_at_1"], 1 / 3)
        self.assertEqual(metrics["recall_at_3"], 2 / 3)
        self.assertEqual(metrics["recall_at_5"], 2 / 3)
        self.assertEqual(metrics["unranked_count"], 1)
        self.assertEqual(metrics["evaluated_count"], 3)

    def test_existing_final_result_requires_explicit_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = Path(tmp) / "result.json"
            result.write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(routing.ExperimentError, "Refusing to overwrite"):
                routing.refuse_result_overwrite(result, replace=False)
            routing.refuse_result_overwrite(result, replace=True)

    def test_model_constructor_uses_exact_revision_and_local_files_only(self) -> None:
        captured = {}

        def fake_constructor(model_id: str, **kwargs: object) -> object:
            captured.update({"model_id": model_id, **kwargs})
            return object()

        with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace(SentenceTransformer=fake_constructor)}):
            routing.construct_model()

        self.assertEqual(captured["model_id"], routing.MODEL_ID)
        self.assertEqual(captured["revision"], routing.MODEL_REVISION)
        self.assertIs(captured["local_files_only"], True)

    def test_environment_controls_are_exact_and_credentials_are_removed(self) -> None:
        snapshot = routing.model_snapshot_path()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ,
            {name: "must-not-be-read-or-used" for name in routing.CREDENTIAL_ENV},
            clear=True,
        ):
            routing.prepare_environment(Path(tmp), snapshot)
            self.assertTrue(all(os.environ[name] == "1" for name in routing.OFFLINE_ENV))
            self.assertTrue(all(name not in os.environ for name in routing.CREDENTIAL_ENV))
            self.assertEqual(os.environ["TMPDIR"], tmp)
            self.assertEqual(os.environ["HF_HOME"], str(snapshot.parents[3]))

    def test_guards_reject_network_process_escape_and_external_path_mutations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            temp_dir = run_dir / "temp"
            outside = root / "outside.txt"
            outside_symlink = root / "outside-link"
            outside_hardlink = root / "outside-hardlink"
            cache_file = root / "model-cache" / "weights"
            run_dir.mkdir()
            temp_dir.mkdir()
            cache_file.parent.mkdir()
            cache_file.write_text("cached", encoding="utf-8")

            with routing.execution_guards(run_dir, temp_dir):
                with self.assertRaisesRegex(routing.ExperimentError, "Network access"):
                    socket.create_connection(("127.0.0.1", 9))
                with self.assertRaisesRegex(routing.ExperimentError, "Network access"):
                    socket.getaddrinfo("example.com", 443)
                udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                try:
                    with self.assertRaisesRegex(routing.ExperimentError, "Network access"):
                        udp.sendto(b"blocked", ("127.0.0.1", 9))
                finally:
                    udp.close()
                with self.assertRaisesRegex(routing.ExperimentError, "process launch"):
                    subprocess.Popen(["/usr/bin/true"])
                with self.assertRaisesRegex(routing.ExperimentError, "process launch"):
                    os.system("/usr/bin/true")
                with self.assertRaisesRegex(routing.ExperimentError, "outside experiment"):
                    outside.write_text("blocked", encoding="utf-8")
                with self.assertRaisesRegex(routing.ExperimentError, "outside experiment"):
                    cache_file.write_text("mutation", encoding="utf-8")
                with self.assertRaisesRegex(routing.ExperimentError, "outside experiment"):
                    os.symlink("target", outside_symlink)
                with self.assertRaisesRegex(routing.ExperimentError, "outside experiment"):
                    os.link(cache_file, outside_hardlink)
                with self.assertRaisesRegex(routing.ExperimentError, "outside experiment"):
                    os.truncate(cache_file, 0)

                allowed = run_dir / "allowed.txt"
                allowed.write_text("allowed", encoding="utf-8")
                os.truncate(allowed, 3)
                os.link(allowed, run_dir / "allowed-hardlink")
                os.symlink("allowed.txt", run_dir / "allowed-symlink")
                (temp_dir / "allowed.txt").write_text("ok", encoding="utf-8")

            self.assertFalse(outside.exists())
            self.assertFalse(outside_symlink.exists())
            self.assertFalse(outside_hardlink.exists())
            self.assertEqual(cache_file.read_text(encoding="utf-8"), "cached")
            self.assertEqual((run_dir / "allowed.txt").read_text(encoding="utf-8"), "all")
            self.assertEqual((run_dir / "allowed-hardlink").read_text(encoding="utf-8"), "all")
            self.assertEqual((run_dir / "allowed-symlink").read_text(encoding="utf-8"), "all")

    def test_guard_coverage_and_forbidden_module_check_are_explicit(self) -> None:
        coverage = routing.guard_coverage()
        self.assertIn("socket.socket.sendto", coverage["socket_apis"])
        self.assertIn("subprocess.Popen", coverage["process_apis"])
        self.assertIn("os.system", coverage["process_apis"])
        self.assertIn("os.symlink", coverage["path_mutation_apis"])
        self.assertIn("os.link", coverage["path_mutation_apis"])
        self.assertIn("os.truncate", coverage["path_mutation_apis"])
        with patch.dict(sys.modules, {"turbopuffer.client": object()}):
            self.assertEqual(routing.imported_forbidden_clients(), ["turbopuffer"])

    def test_gitignore_exception_tracks_only_the_representative_run(self) -> None:
        target = "autoresearch/runs/semantic-routing-representative-20260715/evaluate.py"
        unrelated = "autoresearch/runs/unrelated-run/result.json"
        target_result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", target], cwd=routing.REPO_ROOT, check=False
        )
        unrelated_result = subprocess.run(
            ["git", "check-ignore", "--no-index", "-q", unrelated], cwd=routing.REPO_ROOT, check=False
        )
        self.assertEqual(target_result.returncode, 1)
        self.assertEqual(unrelated_result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
