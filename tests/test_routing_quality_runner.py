from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    NamespaceCard,
    semantic_hash_for_fields,
    vector_hash,
)
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V2,
    CatalogCounts,
    ReadMetrics,
    RemoteCatalogSnapshot,
)
from buoy_search.routing_quality import (
    ROUTING_ROUTE_CONTRACT_REVISION,
    RoutingCanaryPack,
    RoutingCorpusIdentity,
    RoutingQualityCase,
    RoutingQualityDataset,
)
from scripts import evaluate_routing_quality as runner
from tests.routing_confidence_fixtures import (
    load_collect_routing_confidence_fixture,
)


ALPHA = "site-alpha-example-v1"
BETA = "site-beta-example-v1"


def unit_vector(first: float, second: float = 0.0) -> list[float]:
    return [first, second, *([0.0] * (ROUTING_DIMENSIONS - 2))]


def make_card(
    namespace: str,
    *,
    title: str,
    vector: list[float],
) -> NamespaceCard:
    summary = f"Capabilities for {title}."
    semantic_hash = semantic_hash_for_fields(
        title=title,
        summary=summary,
        aliases=[],
        tags=["knowledge"],
    )
    projection_hash = vector_hash(vector)
    return NamespaceCard(
        namespace=namespace,
        enabled=True,
        created_at="2026-08-15T00:00:00+00:00",
        updated_at="2026-08-15T00:00:00+00:00",
        card_revision=f"revision-{namespace}",
        last_plan_id="plan-1",
        last_apply_id="apply-1",
        source_kind="website",
        source_uri=f"https://{namespace}.invalid",
        site_id=namespace,
        title=title,
        summary=summary,
        aliases=[],
        tags=["knowledge"],
        semantic_origin="manual",
        region="aws-us-west-2",
        embedding_model="BAAI/bge-small-en-v1.5",
        embedding_precision="float32",
        vector_dimensions=ROUTING_DIMENSIONS,
        plan_schema_version=2,
        ranking_mode="hybrid",
        ranking_profile="balanced",
        ranking_pool=20,
        ranking_aggregation="weighted_sum",
        routing_model=ROUTING_MODEL,
        routing_model_revision=ROUTING_MODEL_REVISION,
        semantic_hash=semantic_hash,
        vector=list(vector),
        vector_hash=projection_hash,
        routing_examples=[],
        routing_prototype_hash=semantic_hash,
        routing_prototype_vector=list(vector),
        routing_prototype_vector_hash=projection_hash,
    )


def synthetic_dataset(*, approved: bool = False) -> RoutingQualityDataset:
    calibration = RoutingQualityCase(
        id="alpha-calibration",
        origin="canary",
        subject_namespace=ALPHA,
        role="capability_self",
        split="calibration",
        question="Which corpus explains orbital inventory reconciliation?",
        expected_namespaces=(ALPHA,),
        confusable_with=(),
    )
    gate = RoutingQualityCase(
        id="alpha-gate",
        origin="canary",
        subject_namespace=ALPHA,
        role="capability_self",
        split="gate",
        question="Where are satellite stock discrepancies documented?",
        expected_namespaces=(ALPHA,),
        confusable_with=(),
    )
    named = RoutingQualityCase(
        id="beta-named",
        origin="canary",
        subject_namespace=BETA,
        role="named_self",
        split="gate",
        question="What does Beta Product provide?",
        expected_namespaces=(BETA,),
        confusable_with=(),
    )
    pack = RoutingCanaryPack(
        corpus_id="alpha",
        namespace=ALPHA,
        raw_sha256="b" * 64,
        review_status="approved" if approved else "candidate",
        human_approved=approved,
        route_contract_revision=ROUTING_ROUTE_CONTRACT_REVISION,
        canaries_disjoint_from_routing_examples=True,
        cases=(calibration, gate, named),
    )
    return RoutingQualityDataset(
        suite_sha256="a" * 64,
        legacy_dataset_id="synthetic-routing-suite",
        legacy_dataset_sha256="c" * 64,
        legacy_namespaces=(ALPHA, BETA),
        corpora=(
            RoutingCorpusIdentity("alpha", ALPHA),
            RoutingCorpusIdentity("beta", BETA),
        ),
        packs=(pack,),
        cases=(calibration, gate, named),
    )


def synthetic_snapshot() -> RemoteCatalogSnapshot:
    cards = (
        make_card(ALPHA, title="Alpha Product", vector=unit_vector(1.0)),
        make_card(BETA, title="Beta Product", vector=unit_vector(0.8, 0.6)),
    )
    return RemoteCatalogSnapshot(
        cards=cards,
        eligible_cards=cards,
        live_namespace_ids=(ALPHA, BETA),
        missing_card_ids=(),
        stale_target_ids=(),
        disabled_ids=(),
        incompatible_ids=(),
        snapshot_revision="authoritative-snapshot",
        counts=CatalogCounts(
            listed_total=3,
            control_plane_count=1,
            content_live_count=2,
            card_count=2,
            stale_target_count=0,
            missing_card_count=0,
            disabled_count=0,
            incompatible_count=0,
            eligible_count=2,
        ),
        metrics=ReadMetrics(
            namespace_list_pages=2,
            metadata_requests=1,
            card_query_pages=2,
            billing=(),
        ),
        catalog_schema_version=REMOTE_SCHEMA_V2,
    )


class FakeRoutingEmbedder:
    def __init__(self) -> None:
        self.calls = 0

    def encode(self, texts):  # noqa: ANN001, ANN201 - protocol fake.
        self.calls += 1
        return [unit_vector(1.0) for _value in texts]


class FakeReranker:
    def __init__(self) -> None:
        self.calls = 0
        self.maximum_passages = 0

    def score(self, _query, passages):  # noqa: ANN001, ANN201 - protocol fake.
        self.calls += 1
        self.maximum_passages = max(self.maximum_passages, len(passages))
        return [10.0 if "Title: Alpha Product" in value else 5.0 for value in passages]


class FakeCatalogResource:
    def __init__(self) -> None:
        self.write_calls = 0

    def metadata(self, **_kwargs):  # noqa: ANN003, ANN201
        return {}

    def query(self, **_kwargs):  # noqa: ANN003, ANN201
        return {"rows": []}

    def write(self, **_kwargs):  # noqa: ANN003, ANN201
        self.write_calls += 1
        raise AssertionError("route-only collector attempted a provider write")


class FakeCatalogClient:
    def __init__(self) -> None:
        self.resource = FakeCatalogResource()
        self.namespace_calls = 0

    def namespaces(self, **_kwargs):  # noqa: ANN003, ANN201
        return []

    def namespace(self, namespace):  # noqa: ANN001, ANN201
        self.namespace_calls += 1
        if namespace != REMOTE_CATALOG_NAMESPACE:
            raise AssertionError("collector acquired a content namespace")
        return self.resource


class RoutingQualityCollectorTests(unittest.TestCase):
    def test_live_collection_reuses_one_embedding_and_never_exposes_writes(self) -> None:
        dataset = synthetic_dataset(approved=False)
        snapshot = synthetic_snapshot()
        client = FakeCatalogClient()
        embedder = FakeRoutingEmbedder()
        reranker = FakeReranker()
        read_calls = 0

        def read_catalog(read_only_client, **_kwargs):  # noqa: ANN001, ANN003, ANN202
            nonlocal read_calls
            read_calls += 1
            resource = read_only_client.namespace(REMOTE_CATALOG_NAMESPACE)
            self.assertFalse(hasattr(resource, "write"))
            return snapshot

        with (
            patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "test-key"}, clear=True),
            patch.object(runner, "load_config", return_value=RuntimeConfig()),
            patch.object(runner, "create_client", return_value=client),
            patch.object(runner, "read_remote_catalog", side_effect=read_catalog),
            patch.object(runner, "load_routing_embedder", return_value=embedder),
            patch.object(
                runner, "load_cross_encoder_reranker", return_value=reranker
            ),
            patch.object(
                runner,
                "_git_code_identity",
                return_value={
                    "commit": "1" * 40,
                    "tree": "2" * 40,
                    "working_tree_clean": True,
                },
            ),
            patch.object(
                runner,
                "load_routing_confidence_calibration",
                return_value=load_collect_routing_confidence_fixture(),
            ),
        ):
            report = runner.collect_live_run(
                dataset,
                collector_invocation=(
                    "collect",
                    "--canary-dir",
                    "/tmp/canaries",
                    "--legacy-dataset",
                    "/tmp/legacy.json",
                    "--output",
                    "/tmp/report.json",
                ),
            )

        self.assertEqual(read_calls, 1)
        self.assertEqual(client.namespace_calls, 1)
        self.assertEqual(client.resource.write_calls, 0)
        self.assertEqual(embedder.calls, len(dataset.cases))
        self.assertEqual(reranker.calls, len(dataset.cases))
        self.assertLessEqual(reranker.maximum_passages, 12 * 9)
        self.assertEqual(
            report["calls"]["routing_query_embedding_inference_calls"],
            len(dataset.cases),
        )
        self.assertEqual(report["calls"]["provider"]["content_queries"], 0)
        self.assertEqual(report["calls"]["provider"]["writes"], 0)
        self.assertTrue(report["quality_verdict"]["passed"])
        self.assertFalse(report["activation"]["ready"])
        self.assertIn(
            "canary_packs_owner_approved", report["activation"]["failed_checks"]
        )
        self.assertIn(
            "owner_approved_active_confidence_artifact",
            report["activation"]["failed_checks"],
        )

        candidates = {
            item["case_id"]: item for item in report["candidate_observations"]
        }
        self.assertEqual(
            candidates["alpha-gate"]["selection_reason"],
            "high_confidence_prototype",
        )
        self.assertEqual(candidates["alpha-gate"]["initial_namespaces"], [ALPHA])
        self.assertEqual(candidates["beta-named"]["fallback_namespaces"][0], BETA)
        self.assertEqual(
            candidates["beta-named"]["selection_reason"],
            "unique_title_or_alias",
        )

        baselines = {
            item["case_id"]: item
            for item in report["legacy_baseline_observations"]
        }
        self.assertEqual(
            baselines["alpha-gate"]["selection_reason"],
            "high_confidence_semantic",
        )
        self.assertNotIn("reranker_score", baselines["alpha-gate"])
        self.assert_content_free(report, dataset)

    def test_approved_pack_still_cannot_activate_collect_only_artifact(self) -> None:
        dataset = synthetic_dataset(approved=True)
        snapshot = synthetic_snapshot()
        with (
            patch.dict(os.environ, {"TURBOPUFFER_API_KEY": "test-key"}, clear=True),
            patch.object(runner, "load_config", return_value=RuntimeConfig()),
            patch.object(runner, "create_client", return_value=FakeCatalogClient()),
            patch.object(runner, "read_remote_catalog", return_value=snapshot),
            patch.object(
                runner, "load_routing_embedder", return_value=FakeRoutingEmbedder()
            ),
            patch.object(
                runner, "load_cross_encoder_reranker", return_value=FakeReranker()
            ),
            patch.object(
                runner,
                "_git_code_identity",
                return_value={
                    "commit": "1" * 40,
                    "tree": "2" * 40,
                    "working_tree_clean": True,
                },
            ),
            patch.object(
                runner,
                "load_routing_confidence_calibration",
                return_value=load_collect_routing_confidence_fixture(),
            ),
        ):
            report = runner.collect_live_run(
                dataset, collector_invocation=("collect",)
            )

        self.assertNotIn(
            "canary_packs_owner_approved", report["activation"]["failed_checks"]
        )
        self.assertIn(
            "owner_approved_active_confidence_artifact",
            report["activation"]["failed_checks"],
        )
        self.assertFalse(report["activation"]["ready"])

    def test_missing_environment_key_fails_before_client_or_models(self) -> None:
        forbidden = AssertionError("live dependency called before credential gate")
        with (
            patch.dict(os.environ, {}, clear=True),
            patch.object(runner, "create_client", side_effect=forbidden),
            patch.object(runner, "load_routing_embedder", side_effect=forbidden),
        ):
            with self.assertRaisesRegex(
                runner.RoutingQualityCollectionError, "process environment"
            ):
                runner.collect_live_run(
                    synthetic_dataset(), collector_invocation=("collect",)
                )

    def assert_content_free(
        self,
        report: object,
        dataset: RoutingQualityDataset,
    ) -> None:
        forbidden_keys = {
            "api_key",
            "content",
            "passages",
            "provider_payload",
            "query",
            "question",
            "routing_examples",
            "vector",
        }

        def visit(value: object) -> None:
            if isinstance(value, dict):
                self.assertTrue(forbidden_keys.isdisjoint(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(report)
        serialized = json.dumps(report, sort_keys=True)
        for case in dataset.cases:
            self.assertNotIn(case.question, serialized)


class RoutingQualityRunnerCliTests(unittest.TestCase):
    def test_cli_forwards_external_canary_directory_and_writes_atomically(self) -> None:
        dataset = synthetic_dataset()
        report = {
            "activation": {
                "ready": False,
                "status": "collect_only",
                "failed_checks": ["owner_approved_active_confidence_artifact"],
            }
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            canary_dir = root / "canaries"
            legacy = root / "legacy.json"
            output = root / "report.json"
            canary_dir.mkdir()
            legacy.write_text("{}", encoding="utf-8")
            with (
                patch.object(
                    runner,
                    "load_routing_quality_dataset",
                    return_value=dataset,
                ) as loader,
                patch.object(runner, "collect_live_run", return_value=report) as collect,
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                result = runner.main(
                    [
                        "collect",
                        "--canary-dir",
                        str(canary_dir),
                        "--legacy-dataset",
                        str(legacy),
                        "--output",
                        str(output),
                    ]
                )

            self.assertEqual(result, 1)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), report)
            loader.assert_called_once_with(
                canary_dir=canary_dir,
                legacy_dataset_path=legacy,
            )
            invocation = collect.call_args.kwargs["collector_invocation"]
            self.assertEqual(invocation[2], str(canary_dir.resolve()))
            self.assertEqual(invocation[4], str(legacy.resolve()))
            self.assertEqual(invocation[6], str(output.resolve()))

    def test_existing_output_is_rejected_before_dataset_or_live_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            output.write_text("sentinel", encoding="utf-8")
            with (
                patch.object(
                    runner,
                    "load_routing_quality_dataset",
                    side_effect=AssertionError("dataset loaded before overwrite gate"),
                ),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                result = runner.main(["collect", "--output", str(output)])
            self.assertEqual(result, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

    def test_parser_exposes_no_threshold_or_activation_override(self) -> None:
        parser = runner.build_parser()
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    ["collect", "--score-floor", "1", "--output", "/tmp/x"]
                )
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parser.parse_args(
                    ["collect", "--activate", "--output", "/tmp/x"]
                )

    def test_atomic_writer_removes_temporary_file_when_replace_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "report.json"
            with patch.object(runner.os, "replace", side_effect=OSError("failed")):
                with self.assertRaises(OSError):
                    runner._write_report(output, {"finite": 1.0})
            self.assertFalse(output.exists())
            self.assertEqual(list(root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
