from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import traceback
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from buoy_search import multi_corpus_evals as eval_contract
from buoy_search.multi_corpus_evals import (
    DEFAULT_MULTI_CORPUS_EVAL_DATASET,
    EVAL_RUN_SCHEMA_VERSION,
    EVALUATOR_VERSION,
    LIVE_COLLECTOR_PROVENANCE_MARKER,
    evaluate_multi_corpus_run,
    evaluator_sha256,
    load_multi_corpus_eval_dataset,
)
from buoy_search.config import RuntimeConfig
from buoy_search.retriever import SearchHit
from scripts import evaluate_multi_corpus_retrieval as runner


TEST_COLLECTOR_INVOCATION = (
    "collect",
    "--dataset",
    str(DEFAULT_MULTI_CORPUS_EVAL_DATASET.resolve()),
    "--output",
    "/tmp/buoy-test-multi-corpus-report.json",
)


class MultiCorpusEvalRunGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = load_multi_corpus_eval_dataset()

    def test_approved_fixture_scores_every_exact_gate_but_cannot_pass_release(self) -> None:
        report = evaluate_multi_corpus_run(self.dataset, perfect_fixture_run(self.dataset))
        live_candidate = evaluate_multi_corpus_run(
            self.dataset,
            as_claimed_live_run(perfect_fixture_run(self.dataset), self.dataset),
        )

        verdict = report["verdict"]
        self.assertFalse(verdict["release_ready"])
        self.assertEqual(verdict["status"], "fixture")
        self.assertEqual(
            verdict["failed_checks"],
            ["provider_backed_live_run"],
        )
        self.assertEqual(report["metrics"]["routing"]["route_recall_at_3"], 1.0)
        self.assertEqual(report["metrics"]["retrieval"]["automatic_recall_at_5"], 1.0)
        self.assertGreaterEqual(
            report["metrics"]["retrieval"]["ndcg_at_5_improvement"], 0.03
        )
        self.assertLessEqual(
            report["metrics"]["routing"]["average_automatic_fanout"], 2.0
        )
        self.assertFalse(live_candidate["verdict"]["release_ready"])
        self.assertEqual(live_candidate["verdict"]["status"], "fail")
        self.assertEqual(
            live_candidate["verdict"]["failed_checks"],
            ["provider_backed_live_run"],
        )

    def test_only_private_collector_evaluation_can_pass_live_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = json.loads(
                DEFAULT_MULTI_CORPUS_EVAL_DATASET.read_text(encoding="utf-8")
            )
            payload["human_approved_ground_truth"] = True
            payload["review_status"] = "approved"
            dataset_path = Path(temp_dir) / "approved.json"
            dataset_path.write_text(json.dumps(payload), encoding="utf-8")
            dataset = load_multi_corpus_eval_dataset(dataset_path)

            fixture_report = evaluate_multi_corpus_run(
                dataset, perfect_fixture_run(dataset)
            )
            live_report = evaluate_multi_corpus_run(
                dataset, as_collector_live_run(perfect_fixture_run(dataset), dataset)
            )
            collected_run = as_collector_live_run(
                perfect_fixture_run(dataset), dataset
            )
            provenance = collected_run["provenance"]
            with patch.object(
                eval_contract,
                "_current_git_code_identity",
                return_value=dict(provenance["code"]),
            ):
                collector_report = eval_contract._evaluate_collected_multi_corpus_run(
                    dataset,
                    collected_run,
                    expected_catalog_snapshot_revision=collected_run["catalog"][
                        "snapshot_revision"
                    ],
                    expected_models=provenance["models"],
                    expected_collector_invocation=provenance[
                        "collector_invocation"
                    ],
                )

        self.assertFalse(fixture_report["verdict"]["release_ready"])
        self.assertEqual(fixture_report["verdict"]["status"], "fixture")
        self.assertIn(
            "provider_backed_live_run", fixture_report["verdict"]["failed_checks"]
        )
        self.assertFalse(live_report["verdict"]["release_ready"])
        self.assertIn(
            "provider_backed_live_run", live_report["verdict"]["failed_checks"]
        )
        self.assertTrue(collector_report["verdict"]["release_ready"])
        self.assertEqual(collector_report["verdict"]["status"], "pass")
        self.assertEqual(collector_report["verdict"]["failed_checks"], [])

    def test_forged_collector_marker_never_qualifies_on_public_evaluator(self) -> None:
        forged = as_collector_live_run(
            perfect_fixture_run(self.dataset), self.dataset
        )

        with patch.object(
            eval_contract,
            "_current_git_code_identity",
            return_value=dict(forged["provenance"]["code"]),
        ):
            report = evaluate_multi_corpus_run(self.dataset, forged)

        self.assertFalse(
            report["verdict"]["checks"]["provider_backed_live_run"]["passed"]
        )

    def test_collector_qualification_binds_current_code_models_and_invocation(self) -> None:
        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        expected_models = json.loads(json.dumps(run["provenance"]["models"]))
        expected_code = dict(run["provenance"]["code"])
        expected_invocation = list(run["provenance"]["collector_invocation"])
        snapshot_revision = run["catalog"]["snapshot_revision"]

        def qualifies(
            candidate: dict[str, object],
            *,
            current_code: dict[str, object] | None = None,
        ) -> bool:
            with patch.object(
                eval_contract,
                "_current_git_code_identity",
                return_value=current_code or expected_code,
            ):
                report = eval_contract._evaluate_collected_multi_corpus_run(
                    self.dataset,
                    candidate,
                    expected_catalog_snapshot_revision=snapshot_revision,
                    expected_models=expected_models,
                    expected_collector_invocation=expected_invocation,
                )
            return report["verdict"]["checks"]["provider_backed_live_run"][
                "passed"
            ]

        self.assertTrue(qualifies(json.loads(json.dumps(run))))

        for field in ("commit", "tree"):
            with self.subTest(code=field):
                candidate = json.loads(json.dumps(run))
                candidate["provenance"]["code"][field] = "4" * 40
                self.assertFalse(qualifies(candidate))

        dirty_code = {**expected_code, "working_tree_clean": False}
        self.assertFalse(
            qualifies(json.loads(json.dumps(run)), current_code=dirty_code)
        )

        config_fields = {
            "routing": "route_top_k",
            "content_embedding": "automatic_top_k",
            "reranker": "batch_size",
        }
        for role, config_field in config_fields.items():
            with self.subTest(role=role, mismatch="identity"):
                candidate = json.loads(json.dumps(run))
                candidate["provenance"]["models"][role]["model"] += "-forged"
                self.assertFalse(qualifies(candidate))
            with self.subTest(role=role, mismatch="revision"):
                candidate = json.loads(json.dumps(run))
                candidate["provenance"]["models"][role]["revision"] = "5" * 40
                self.assertFalse(qualifies(candidate))
            with self.subTest(role=role, mismatch="config"):
                candidate = json.loads(json.dumps(run))
                candidate["provenance"]["models"][role]["config"][
                    config_field
                ] = 999
                self.assertFalse(qualifies(candidate))

        for field, forged_value in (("version", "forged"), ("sha256", "6" * 64)):
            with self.subTest(evaluator=field):
                candidate = json.loads(json.dumps(run))
                candidate["provenance"]["evaluator"][field] = forged_value
                self.assertFalse(qualifies(candidate))

        candidate = json.loads(json.dumps(run))
        candidate["provenance"]["collector_invocation"] = [
            "collect",
            "--output",
            "/tmp/report.json",
            "--dataset",
            "/tmp/evals.json",
        ]
        self.assertFalse(qualifies(candidate))

        candidate = json.loads(json.dumps(run))
        candidate["provenance"]["catalog_snapshot_revision"] = "other-snapshot"
        candidate["catalog"]["snapshot_revision"] = "other-snapshot"
        self.assertFalse(qualifies(candidate))

    def test_live_model_configs_must_be_complete_and_record_local_rank_one_policy(self) -> None:
        for role, field in (
            ("routing", "route_top_k"),
            ("content_embedding", "automatic_top_k"),
            ("reranker", "batch_size"),
        ):
            with self.subTest(role=role):
                run = as_collector_live_run(
                    perfect_fixture_run(self.dataset), self.dataset
                )
                del run["provenance"]["models"][role]["config"][field]
                with self.assertRaisesRegex(ValueError, "model config fields are invalid"):
                    evaluate_multi_corpus_run(self.dataset, run)

        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["models"]["content_embedding"]["config"][
            "namespace_retrieval"
        ].pop(self.dataset.eligible_namespaces[0])
        with self.assertRaisesRegex(ValueError, "cover exactly the eligible namespaces"):
            evaluate_multi_corpus_run(self.dataset, run)

        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["models"]["reranker"]["config"][
            "namespace_coverage_policy"
        ] = "best-fused-hit"
        with self.assertRaisesRegex(ValueError, "local-rank-one"):
            evaluate_multi_corpus_run(self.dataset, run)

    def test_saved_live_report_revalidation_cannot_reestablish_collector_trust(self) -> None:
        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        provenance = run["provenance"]
        with patch.object(
            eval_contract,
            "_current_git_code_identity",
            return_value=dict(provenance["code"]),
        ):
            collected_report = eval_contract._evaluate_collected_multi_corpus_run(
                self.dataset,
                run,
                expected_catalog_snapshot_revision=run["catalog"][
                    "snapshot_revision"
                ],
                expected_models=provenance["models"],
                expected_collector_invocation=provenance["collector_invocation"],
            )

        self.assertTrue(
            collected_report["verdict"]["checks"]["provider_backed_live_run"][
                "passed"
            ]
        )
        revalidated = evaluate_multi_corpus_run(self.dataset, collected_report)
        self.assertFalse(
            revalidated["verdict"]["checks"]["provider_backed_live_run"][
                "passed"
            ]
        )

    def test_validate_run_cannot_upgrade_claimed_live_mode_without_collector_provenance(self) -> None:
        claimed = as_claimed_live_run(perfect_fixture_run(self.dataset), self.dataset)

        report = evaluate_multi_corpus_run(self.dataset, claimed)

        self.assertFalse(report["verdict"]["release_ready"])
        self.assertFalse(
            report["verdict"]["checks"]["provider_backed_live_run"]["passed"]
        )
        self.assertEqual(report["provenance"], {"origin": "offline_fixture"})

    def test_live_provenance_binds_dataset_evaluator_catalog_and_clean_code(self) -> None:
        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["dataset_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "canonical dataset"):
            evaluate_multi_corpus_run(self.dataset, run)

        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["catalog_snapshot_revision"] = "other-snapshot"
        with self.assertRaisesRegex(ValueError, "catalog snapshot"):
            evaluate_multi_corpus_run(self.dataset, run)

        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["evaluator"]["sha256"] = "0" * 64
        report = evaluate_multi_corpus_run(self.dataset, run)
        self.assertFalse(
            report["verdict"]["checks"]["provider_backed_live_run"]["passed"]
        )

        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        run["provenance"]["code"]["working_tree_clean"] = False
        report = evaluate_multi_corpus_run(self.dataset, run)
        self.assertFalse(
            report["verdict"]["checks"]["provider_backed_live_run"]["passed"]
        )

    def test_provider_mutation_is_a_structural_assertion_not_call_telemetry(self) -> None:
        run = perfect_fixture_run(self.dataset)
        run["cases"][0]["calls"]["provider_mutations"] = 0
        with self.assertRaisesRegex(ValueError, "unknown=.*provider_mutations"):
            evaluate_multi_corpus_run(self.dataset, run)

        run = perfect_fixture_run(self.dataset)
        run["read_only_boundary"]["provider_mutations_precluded"] = False
        report = evaluate_multi_corpus_run(self.dataset, run)
        self.assertFalse(
            report["verdict"]["checks"]["complete_read_only_collection"]["passed"]
        )

    def test_validate_run_recomputes_tampered_derived_metrics_and_verdict(self) -> None:
        report = evaluate_multi_corpus_run(self.dataset, perfect_fixture_run(self.dataset))
        report["metrics"] = {"routing": {"route_recall_at_3": 999}}
        report["verdict"] = {"release_ready": True}

        recomputed = evaluate_multi_corpus_run(self.dataset, report)

        self.assertEqual(recomputed["metrics"]["routing"]["route_recall_at_3"], 1.0)
        self.assertFalse(recomputed["verdict"]["release_ready"])

    def test_verdict_publishes_the_specification_thresholds_exactly(self) -> None:
        report = evaluate_multi_corpus_run(self.dataset, perfect_fixture_run(self.dataset))
        checks = report["verdict"]["checks"]

        self.assertEqual(checks["route_recall_at_3"]["required"], ">=0.95")
        self.assertEqual(checks["automatic_recall_at_5"]["required"], ">=0.95")
        self.assertEqual(
            checks["reranking_ndcg_at_5_improvement"]["required"], ">=0.03"
        )
        self.assertEqual(checks["average_automatic_fanout"]["required"], "<=2.0")
        self.assertEqual(checks["maximum_automatic_fanout"]["required"], "<=3")

    def test_each_ranking_quality_failure_changes_the_executable_verdict(self) -> None:
        multi_ids = {
            case.id for case in self.dataset.cases if case.category == "multi_corpus"
        }
        automatic_failure = perfect_fixture_run(self.dataset)
        for case in automatic_failure["cases"]:
            case["automatic_hits"] = []
        automatic_report = evaluate_multi_corpus_run(self.dataset, automatic_failure)
        self.assertFalse(
            automatic_report["verdict"]["checks"]["automatic_recall_at_5"]["passed"]
        )

        ndcg_failure = perfect_fixture_run(self.dataset)
        for case in ndcg_failure["cases"]:
            if case["id"] in multi_ids:
                case["pre_rerank_hits"] = list(case["reranked_hits"])
        ndcg_report = evaluate_multi_corpus_run(self.dataset, ndcg_failure)
        self.assertFalse(
            ndcg_report["verdict"]["checks"]["reranking_ndcg_at_5_improvement"]["passed"]
        )

        recall_failure = perfect_fixture_run(self.dataset)
        for case in recall_failure["cases"]:
            if case["id"] in multi_ids:
                case["reranked_hits"] = []
        recall_report = evaluate_multi_corpus_run(self.dataset, recall_failure)
        self.assertFalse(
            recall_report["verdict"]["checks"]["reranking_recall_at_5_not_reduced"]["passed"]
        )

    def test_more_than_three_automatic_namespaces_fails_closed(self) -> None:
        run = perfect_fixture_run(self.dataset)
        run["cases"][0]["route"] = {
            "namespaces": list(self.dataset.eligible_namespaces),
            "initial_high_confidence_namespace": None,
        }

        with self.assertRaisesRegex(ValueError, "fanout must be between one and 3"):
            evaluate_multi_corpus_run(self.dataset, run)

    def test_wrong_initial_confident_singleton_is_counted_after_final_widening(self) -> None:
        run = perfect_fixture_run(self.dataset)
        case = next(
            case for case in self.dataset.cases if len(case.expected_namespaces) == 1
        )
        observation = next(item for item in run["cases"] if item["id"] == case.id)
        expected = case.expected_namespaces[0]
        wrong = next(
            namespace
            for namespace in self.dataset.eligible_namespaces
            if namespace != expected
        )
        third = next(
            namespace
            for namespace in self.dataset.eligible_namespaces
            if namespace not in {wrong, expected}
        )
        observation["route"] = {
            "namespaces": [wrong, expected, third],
            "initial_high_confidence_namespace": wrong,
        }

        report = evaluate_multi_corpus_run(self.dataset, run)

        self.assertEqual(report["metrics"]["routing"]["route_recall_at_3"], 1.0)
        self.assertEqual(
            report["metrics"]["routing"]["incorrect_high_confidence_single_routes"],
            1,
        )
        self.assertFalse(
            report["verdict"]["checks"]["incorrect_high_confidence_single_routes"][
                "passed"
            ]
        )

    def test_missing_disabled_or_incompatible_coverage_fails_closed(self) -> None:
        mutations = (
            ("missing_namespaces", [self.dataset.eligible_namespaces[0]], "missing"),
            ("incompatible_namespaces", [self.dataset.eligible_namespaces[0]], "incompatible"),
            ("disabled_namespaces", [], "disabled coverage"),
        )
        for field, value, message in mutations:
            with self.subTest(field=field):
                run = perfect_fixture_run(self.dataset)
                run["catalog"][field] = value
                with self.assertRaisesRegex(ValueError, message):
                    evaluate_multi_corpus_run(self.dataset, run)

    def test_partial_collection_is_a_nonpassing_quality_run(self) -> None:
        run = perfect_fixture_run(self.dataset)
        namespace = run["cases"][0]["route"]["namespaces"][0]
        run["cases"][0]["failures"]["automatic_namespaces"] = [namespace]

        report = evaluate_multi_corpus_run(self.dataset, run)

        self.assertFalse(report["verdict"]["release_ready"])
        self.assertEqual(report["verdict"]["status"], "fail")
        self.assertIn("complete_read_only_collection", report["verdict"]["failed_checks"])

    def test_content_or_vector_fields_cannot_enter_a_saved_run(self) -> None:
        for forbidden in ("content", "vector", "question"):
            with self.subTest(field=forbidden):
                run = perfect_fixture_run(self.dataset)
                run["cases"][0]["automatic_hits"][0][forbidden] = "do not retain"
                with self.assertRaisesRegex(ValueError, "unknown"):
                    evaluate_multi_corpus_run(self.dataset, run)


class MultiCorpusEvalRunnerCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataset = load_multi_corpus_eval_dataset()

    def test_fixture_and_validate_run_are_offline_and_use_zero_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            fixture_path = root / "fixture.json"
            report_path = root / "report.json"
            fixture_path.write_text(
                json.dumps(perfect_fixture_run(self.dataset)), encoding="utf-8"
            )
            forbidden = AssertionError("offline fixture attempted a live dependency")
            with (
                patch.object(runner, "create_client", side_effect=forbidden),
                patch.object(runner, "load_routing_embedder", side_effect=forbidden),
                patch.object(runner, "SentenceTransformerEmbedder", side_effect=forbidden),
                patch.object(runner, "build_namespace", side_effect=forbidden),
                patch.object(runner, "load_cross_encoder_reranker", side_effect=forbidden),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                result = runner.main(
                    [
                        "fixture",
                        "--input",
                        str(fixture_path),
                        "--output",
                        str(report_path),
                    ]
                )
            self.assertEqual(result, 1)
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report["mode"], "fixture")
            self.assertEqual(
                report["metrics"]["collection"]["calls"],
                {
                    "automatic_multi_query_logical_calls": 0,
                    "automatic_namespace_logical_calls": 0,
                    "content_embedding_logical_calls": 0,
                    "exhaustive_multi_query_logical_calls": 0,
                    "exhaustive_namespace_logical_calls": 0,
                    "reranker_logical_calls": 0,
                    "routing_embedding_logical_calls": 0,
                },
            )
            self.assert_no_sensitive_payload_keys(report)

            stdout = StringIO()
            stderr = StringIO()
            with (
                patch.object(runner, "create_client", side_effect=forbidden),
                patch.object(runner, "load_routing_embedder", side_effect=forbidden),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                validate_result = runner.main(["validate-run", str(report_path)])
            self.assertEqual(validate_result, 1)
            validated = json.loads(stdout.getvalue())
            self.assertFalse(validated["verdict"]["release_ready"])
            self.assertIn('"status": "fixture"', stderr.getvalue())

    def test_validate_run_cannot_reestablish_saved_collector_trust(self) -> None:
        run = as_collector_live_run(perfect_fixture_run(self.dataset), self.dataset)
        provenance = run["provenance"]
        with patch.object(
            eval_contract,
            "_current_git_code_identity",
            return_value=dict(provenance["code"]),
        ):
            collected_report = eval_contract._evaluate_collected_multi_corpus_run(
                self.dataset,
                run,
                expected_catalog_snapshot_revision=run["catalog"][
                    "snapshot_revision"
                ],
                expected_models=provenance["models"],
                expected_collector_invocation=provenance["collector_invocation"],
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "saved-live-report.json"
            report_path.write_text(json.dumps(collected_report), encoding="utf-8")
            stdout = StringIO()
            forbidden = AssertionError("validate-run attempted a live dependency")
            with (
                patch.object(runner, "create_client", side_effect=forbidden),
                patch.object(runner, "load_routing_embedder", side_effect=forbidden),
                patch.object(
                    runner, "SentenceTransformerEmbedder", side_effect=forbidden
                ),
                patch.object(runner, "build_namespace", side_effect=forbidden),
                patch.object(
                    runner, "load_cross_encoder_reranker", side_effect=forbidden
                ),
                redirect_stdout(stdout),
                redirect_stderr(StringIO()),
            ):
                result = runner.main(["validate-run", str(report_path)])

        self.assertEqual(result, 1)
        revalidated = json.loads(stdout.getvalue())
        self.assertFalse(
            revalidated["verdict"]["checks"]["provider_backed_live_run"][
                "passed"
            ]
        )

    def test_collect_requires_an_explicitly_sourced_environment_key_before_live_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            stdout = StringIO()
            stderr = StringIO()
            with (
                patch.dict(os.environ, {}, clear=True),
                patch.object(
                    runner,
                    "create_client",
                    side_effect=AssertionError("provider must not be called"),
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = runner.main(["collect", "--output", str(output)])

        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("process environment", stderr.getvalue())
        self.assertIn("does not load .env files", stderr.getvalue())

    def test_catalog_resource_failure_cannot_leak_secret_from_live_collector(self) -> None:
        secret = "tpuf_EVALUATOR_RESOURCE_SECRET"

        class LeakyProviderError(Exception):
            pass

        class ResourceExplodingClient:
            def namespaces(self, **_kwargs: object) -> object:
                return [
                    {"id": "buoy-routing-catalog-v1"},
                    {"id": "site-example-v1"},
                ]

            def namespace(self, _namespace: str) -> object:
                raise LeakyProviderError(f"Authorization: Bearer {secret}")

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            stdout = StringIO()
            stderr = StringIO()
            with (
                patch.dict(
                    os.environ,
                    {"TURBOPUFFER_API_KEY": secret},
                    clear=True,
                ),
                patch.object(runner, "load_config", return_value=RuntimeConfig()),
                patch.object(
                    runner,
                    "create_client",
                    return_value=ResourceExplodingClient(),
                ),
                patch.object(
                    runner,
                    "load_routing_embedder",
                    side_effect=AssertionError("routing model loaded after catalog failure"),
                ),
                redirect_stdout(stdout),
                redirect_stderr(stderr),
            ):
                result = runner.main(["collect", "--output", str(output)])

            self.assertFalse(output.exists())

        self.assertEqual((result, stdout.getvalue()), (2, ""))
        self.assertIn("namespace resource acquisition", stderr.getvalue())
        self.assertIn("LeakyProviderError", stderr.getvalue())
        self.assertNotIn(secret, stderr.getvalue())
        self.assertNotIn("Authorization", stderr.getvalue())
        self.assertNotIn("Bearer", stderr.getvalue())

    def test_content_namespace_construction_failure_cannot_leak_secret(self) -> None:
        secret = "secret-sentinel-should-never-appear"
        cards = fake_cards(self.dataset)
        snapshot = SimpleNamespace(
            eligible_cards=tuple(cards),
            live_namespace_ids=tuple(
                item.namespace for item in self.dataset.physical_namespaces
            ),
            missing_card_ids=(),
            stale_target_ids=(),
            disabled_ids=self.dataset.disabled_duplicate_namespaces,
            incompatible_ids=(),
            snapshot_revision="fake-live-snapshot",
            metrics=SimpleNamespace(
                namespace_list_pages=1,
                metadata_requests=1,
                card_query_pages=1,
            ),
        )

        def secret_failure(**_kwargs):  # noqa: ANN003, ANN202
            raise RuntimeError(f"SDK setup failed with token {secret}")

        patches = (
            patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "test-key"}, clear=True),
            patch.object(runner, "load_config", return_value=RuntimeConfig()),
            patch.object(runner, "create_client", return_value=object()),
            patch.object(runner, "read_remote_catalog", return_value=snapshot),
            patch.object(runner, "load_routing_embedder", return_value=object()),
            patch.object(
                runner,
                "SentenceTransformerEmbedder",
                return_value=FakeContentEmbedder(),
            ),
            patch.object(runner, "build_namespace", side_effect=secret_failure),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
            with self.assertRaises(runner.EvaluationCollectionError) as raised:
                runner.collect_live_run(
                    self.dataset,
                    collector_invocation=TEST_COLLECTOR_INVOCATION,
                )

        formatted = "".join(
            traceback.format_exception(
                type(raised.exception), raised.exception, raised.exception.__traceback__
            )
        )
        self.assertEqual(
            str(raised.exception), "content namespace client could not be prepared"
        )
        self.assertIsNone(raised.exception.__cause__)
        self.assertIsNone(raised.exception.__context__)
        self.assertNotIn(secret, formatted)

        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            stderr = StringIO()
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], redirect_stdout(
                StringIO()
            ), redirect_stderr(stderr):
                result = runner.main(["collect", "--output", str(output)])
        self.assertEqual(result, 2)
        self.assertNotIn(secret, stderr.getvalue())
        self.assertIn("content namespace client could not be prepared", stderr.getvalue())

    def test_fixture_command_rejects_a_non_fixture_mode(self) -> None:
        run = as_claimed_live_run(perfect_fixture_run(self.dataset), self.dataset)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input.json"
            output_path = root / "output.json"
            input_path.write_text(json.dumps(run), encoding="utf-8")
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                result = runner.main(
                    ["fixture", "--input", str(input_path), "--output", str(output_path)]
                )

        self.assertEqual(result, 2)
        self.assertFalse(output_path.exists())

    def test_fake_live_collector_exercises_read_only_orchestration_and_pre_rerank_order(self) -> None:
        cards = fake_cards(self.dataset)
        empty_case = next(
            case
            for case in self.dataset.cases
            if case.category == "descriptor_free_confusable"
        )
        providers = {
            namespace: FakeContentNamespace(
                namespace,
                empty_query=(
                    empty_case.question
                    if namespace == self.dataset.eligible_namespaces[0]
                    else None
                ),
            )
            for namespace in self.dataset.eligible_namespaces
        }
        snapshot = SimpleNamespace(
            eligible_cards=tuple(cards),
            live_namespace_ids=tuple(
                item.namespace for item in self.dataset.physical_namespaces
            ),
            missing_card_ids=(),
            stale_target_ids=(),
            disabled_ids=self.dataset.disabled_duplicate_namespaces,
            incompatible_ids=(),
            snapshot_revision="fake-live-snapshot",
            metrics=SimpleNamespace(
                namespace_list_pages=2,
                metadata_requests=1,
                card_query_pages=2,
            ),
        )
        route_embedder = FakeRoutingEmbedder()
        content_embedder = FakeContentEmbedder()
        reranker = FakeReranker()

        with (
            patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "test-key"}, clear=True),
            patch.object(runner, "load_config", return_value=RuntimeConfig()),
            patch.object(runner, "create_client", return_value=object()),
            patch.object(runner, "read_remote_catalog", return_value=snapshot),
            patch.object(runner, "load_routing_embedder", return_value=route_embedder),
            patch.object(
                runner,
                "SentenceTransformerEmbedder",
                return_value=content_embedder,
            ),
            patch.object(
                runner,
                "build_namespace",
                side_effect=lambda *, config, api_key: providers[config.namespace],
            ),
            patch.object(
                runner,
                "load_cross_encoder_reranker",
                return_value=reranker,
            ),
        ):
            report = runner.collect_live_run(
                self.dataset,
                collector_invocation=TEST_COLLECTOR_INVOCATION,
            )

        self.assertEqual(report["mode"], "live")
        self.assertEqual(
            report["provenance"]["models"]["reranker"]["config"][
                "namespace_coverage_policy"
            ],
            "retain_one_namespace_local_rank_one_hit_per_nonempty_namespace_when_top_k_allows",
        )
        self.assertEqual(route_embedder.calls, 50)
        self.assertEqual(content_embedder.calls, 50)
        collection_calls = report["metrics"]["collection"]["calls"]
        self.assertEqual(collection_calls["routing_embedding_logical_calls"], 50)
        self.assertEqual(collection_calls["content_embedding_logical_calls"], 50)
        self.assertEqual(collection_calls["exhaustive_namespace_logical_calls"], 200)
        self.assertEqual(collection_calls["exhaustive_multi_query_logical_calls"], 200)
        self.assertEqual(
            collection_calls["automatic_multi_query_logical_calls"],
            collection_calls["automatic_namespace_logical_calls"],
        )
        self.assertEqual(
            collection_calls["automatic_multi_query_logical_calls"]
            + collection_calls["exhaustive_multi_query_logical_calls"],
            sum(provider.query_calls for provider in providers.values()),
        )
        self.assertEqual(collection_calls["reranker_logical_calls"], reranker.calls)
        self.assertEqual(
            report["read_only_boundary"],
            {
                "provider_mutation_methods_exposed": False,
                "provider_mutations_precluded": True,
            },
        )
        self.assertTrue(all(provider.write_calls == 0 for provider in providers.values()))

        cases = {case["id"]: case for case in report["cases"]}
        widened = cases[empty_case.id]
        self.assertEqual(len(widened["route"]["namespaces"]), 3)
        self.assertEqual(
            widened["route"]["initial_high_confidence_namespace"],
            widened["route"]["namespaces"][0],
        )
        self.assertEqual(widened["failures"]["automatic_namespaces"], [])
        multi_case = next(
            case for case in self.dataset.cases if case.category == "multi_corpus"
        )
        multi_observation = cases[multi_case.id]
        self.assertNotEqual(
            multi_observation["pre_rerank_hits"],
            multi_observation["reranked_hits"],
        )
        self.assertEqual(
            multi_observation["pre_rerank_hits"][0]["namespace"],
            multi_observation["route"]["namespaces"][0],
        )
        self.assert_no_sensitive_payload_keys(report)

    def test_pre_rerank_capture_uses_final_hits_when_reranking_was_not_applied(self) -> None:
        final_hit = SearchHit(
            id="final",
            namespace="site-dagster-io-v1",
            url="https://dagster.io/final",
        )
        unreturned_local_hit = SearchHit(
            id="local-only",
            namespace="site-dagster-io-v1",
            url="https://dagster.io/local-only",
        )
        result = SimpleNamespace(
            reranking=SimpleNamespace(applied=False),
            hits=[final_hit],
            namespace_results=[
                SimpleNamespace(
                    namespace="site-dagster-io-v1",
                    hits=[final_hit, unreturned_local_hit],
                )
            ],
            namespace_route_ranks={"site-dagster-io-v1": 1},
        )

        captured = runner._pre_rerank_identity_hits(result)

        self.assertEqual(
            captured,
            [
                {
                    "namespace": "site-dagster-io-v1",
                    "url": "https://dagster.io/final",
                }
            ],
        )

    def test_pre_rerank_capture_round_robins_namespace_local_ranks(self) -> None:
        namespaces = ("site-dagster-io-v1", "site-oscilar-com-v1")
        namespace_results = []
        expected: list[dict[str, str]] = []
        for namespace_index, namespace in enumerate(namespaces):
            hits = [
                SearchHit(
                    id=f"{namespace_index}-{rank}",
                    namespace=namespace,
                    url=f"https://example.invalid/{namespace_index}/{rank}",
                )
                for rank in range(2)
            ]
            namespace_results.append(SimpleNamespace(namespace=namespace, hits=hits))
        for rank in range(2):
            for namespace_index, namespace in enumerate(namespaces):
                expected.append(
                    {
                        "namespace": namespace,
                        "url": f"https://example.invalid/{namespace_index}/{rank}",
                    }
                )
        result = SimpleNamespace(
            reranking=SimpleNamespace(applied=True),
            hits=[],
            namespace_results=namespace_results,
            namespace_route_ranks={namespace: index for index, namespace in enumerate(namespaces)},
        )

        self.assertEqual(runner._pre_rerank_identity_hits(result), expected)

    def assert_no_sensitive_payload_keys(self, value: object) -> None:
        forbidden = {"api_key", "content", "passages", "query", "question", "vector"}
        if isinstance(value, dict):
            self.assertTrue(forbidden.isdisjoint(value))
            for child in value.values():
                self.assert_no_sensitive_payload_keys(child)
        elif isinstance(value, list):
            for child in value:
                self.assert_no_sensitive_payload_keys(child)


def perfect_fixture_run(dataset) -> dict[str, object]:
    first_namespace = dataset.eligible_namespaces[0]
    cases: list[dict[str, object]] = []
    for case in dataset.cases:
        relevant = [
            {"namespace": judgment.namespace, "url": judgment.url}
            for judgment in case.judgments
        ]
        if case.category == "multi_corpus":
            noise = [
                {
                    "namespace": dataset.eligible_namespaces[0],
                    "url": f"https://example.invalid/{case.id}/noise-one",
                },
                {
                    "namespace": dataset.eligible_namespaces[1],
                    "url": f"https://example.invalid/{case.id}/noise-two",
                },
            ]
            pre_rerank = [*noise, *relevant]
            reranked = [*relevant, *noise]
        else:
            pre_rerank = list(relevant)
            reranked = list(relevant)
        route = list(case.expected_namespaces) or [first_namespace]
        cases.append(
            {
                "id": case.id,
                "route": {
                    "namespaces": route,
                    "initial_high_confidence_namespace": (
                        route[0]
                        if bool(case.expected_namespaces) and len(route) == 1
                        else None
                    ),
                },
                "exhaustive_hits": relevant,
                "automatic_hits": relevant,
                "pre_rerank_hits": pre_rerank,
                "reranked_hits": reranked,
                "timing_ms": {
                    "routing": 0,
                    "automatic": 0,
                    "exhaustive": 0,
                    "total": 0,
                },
                "calls": {
                    "routing_embedding_logical_calls": 0,
                    "content_embedding_logical_calls": 0,
                    "reranker_logical_calls": 0,
                    "automatic_namespace_logical_calls": 0,
                    "exhaustive_namespace_logical_calls": 0,
                    "automatic_multi_query_logical_calls": 0,
                    "exhaustive_multi_query_logical_calls": 0,
                },
                "failures": {
                    "automatic_namespaces": [],
                    "exhaustive_namespaces": [],
                },
            }
        )
    return {
        "schema_version": EVAL_RUN_SCHEMA_VERSION,
        "dataset_id": dataset.dataset_id,
        "mode": "fixture",
        "provenance": {"origin": "offline_fixture"},
        "read_only_boundary": {
            "provider_mutation_methods_exposed": False,
            "provider_mutations_precluded": True,
        },
        "catalog": {
            "snapshot_revision": "fixture-snapshot",
            "live_namespaces": [
                item.namespace for item in dataset.physical_namespaces
            ],
            "eligible_namespaces": list(dataset.eligible_namespaces),
            "disabled_namespaces": list(dataset.disabled_duplicate_namespaces),
            "stale_namespaces": [],
            "missing_namespaces": [],
            "incompatible_namespaces": [],
            "read_calls": {
                "namespace_list_logical_calls": 0,
                "metadata_logical_calls": 0,
                "catalog_query_logical_calls": 0,
            },
        },
        "cases": cases,
    }


def as_claimed_live_run(run: dict[str, object], dataset) -> dict[str, object]:
    run["mode"] = "live"
    run["catalog"]["read_calls"] = {
        "namespace_list_logical_calls": 2,
        "metadata_logical_calls": 1,
        "catalog_query_logical_calls": 2,
    }
    categories = {case.id: case.category for case in dataset.cases}
    for case in run["cases"]:
        fanout = len(case["route"]["namespaces"])
        case["calls"] = {
            "routing_embedding_logical_calls": 1,
            "content_embedding_logical_calls": 1,
            "reranker_logical_calls": int(categories[case["id"]] == "multi_corpus"),
            "automatic_namespace_logical_calls": fanout,
            "exhaustive_namespace_logical_calls": 4,
            "automatic_multi_query_logical_calls": fanout,
            "exhaustive_multi_query_logical_calls": 4,
        }
    return run


def as_collector_live_run(run: dict[str, object], dataset) -> dict[str, object]:
    as_claimed_live_run(run, dataset)
    models = runner._live_model_provenance(
        base_config=RuntimeConfig(),
        content_model_revision="3" * 40,
        content_cards=fake_cards(dataset),
    )
    run["provenance"] = {
        "origin": LIVE_COLLECTOR_PROVENANCE_MARKER,
        "collector_produced": True,
        "dataset_sha256": dataset.canonical_sha256,
        "code": {
            "commit": "1" * 40,
            "tree": "2" * 40,
            "working_tree_clean": True,
        },
        "catalog_snapshot_revision": run["catalog"]["snapshot_revision"],
        "models": models,
        "evaluator": {
            "version": EVALUATOR_VERSION,
            "sha256": evaluator_sha256(),
        },
        "collector_invocation": [
            "collect",
            "--dataset",
            "/tmp/evals.json",
            "--output",
            "/tmp/report.json",
        ],
    }
    return run


def fake_cards(dataset) -> list[SimpleNamespace]:
    cards: list[SimpleNamespace] = []
    for index, corpus in enumerate(dataset.logical_corpora):
        vector = [0.0] * 384
        vector[index] = 1.0
        cards.append(
            SimpleNamespace(
                namespace=corpus.namespace,
                title=corpus.title,
                aliases=list(corpus.aliases),
                tags=[],
                vector=vector,
                region="gcp-us-central1",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_precision="float32",
                ranking_mode="page",
                ranking_profile="none",
                ranking_pool=20,
                ranking_aggregation="max",
            )
        )
    return cards


class FakeRoutingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts):
        self.calls += 1
        return [[1.0, *([0.0] * 383)] for _text in texts]


class FakeContentEmbedder:
    def __init__(self) -> None:
        self.calls = 0
        self.model_revision = "4" * 40

    def encode(self, texts):
        self.calls += 1
        return [[1.0, *([0.0] * 383)] for _text in texts]


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0

    def score(self, query, passages):
        self.calls += 1
        return [float(index) for index, _passage in enumerate(passages)]


class FakeContentNamespace:
    def __init__(self, namespace: str, *, empty_query: str | None = None) -> None:
        self.namespace = namespace
        self.empty_query = empty_query
        self.query_calls = 0
        self.write_calls = 0

    def multi_query(self, **kwargs):
        self.query_calls += 1
        if self.empty_query and self.empty_query in str(kwargs):
            return {"rows": []}
        return {
            "rows": [
                {
                    "id": f"{self.namespace}-{index}",
                    "title": f"Fake {self.namespace} {index}",
                    "url": f"https://example.invalid/{self.namespace}/{index}",
                    "section_path": f"Section {index}",
                    "content": f"Fake bounded content {self.namespace} {index}",
                    "path": f"/{index}",
                    "tags": [],
                    "doc_kind": "guide",
                    "chunk_index": index,
                }
                for index in (1, 2)
            ]
        }

    def write(self, **kwargs):
        self.write_calls += 1
        raise AssertionError("read-only collector attempted a provider write")


if __name__ == "__main__":
    unittest.main()
