from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from buoy_search import routing_quality as routing_quality_module
from buoy_search.catalog import ROUTING_MODEL, ROUTING_MODEL_REVISION
from buoy_search.cross_encoder import CROSS_ENCODER_MODEL, CROSS_ENCODER_REVISION
from buoy_search.routing_quality import (
    DEFAULT_ROUTING_CALIBRATION,
    ROUTING_ACTIVE_CALIBRATION_CASE_COUNT,
    ROUTING_ACTIVE_CALIBRATION_CASE_IDS_SHA256,
    ROUTING_ACTIVE_CALIBRATION_REVISION,
    ROUTING_ACTIVE_CALIBRATION_SCHEMA_VERSION,
    ROUTING_ACTIVE_CANARY_SUITE_SHA256,
    ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
    ROUTING_ACTIVE_CERTIFICATION_CASE_COUNT,
    ROUTING_ACTIVE_CERTIFICATION_CASE_IDS_SHA256,
    ROUTING_ACTIVE_MARGIN_FLOOR,
    ROUTING_ACTIVE_QUALITY_VERDICT_SHA256,
    ROUTING_ACTIVE_SCORE_FLOOR,
    ROUTING_ACTIVE_ANCHOR_NAMESPACES,
    ROUTING_ANCHORED_CALIBRATION_REVISION,
    ROUTING_ANCHORED_CALIBRATION_SCHEMA_VERSION,
    ROUTING_ACTIVATION_AUTHORIZATION_REPORT_SHA256,
    ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_COMMIT,
    ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_TREE,
    ROUTING_CALIBRATION_ID,
    ROUTING_CALIBRATION_SCHEMA_VERSION,
    ROUTING_CATALOG_POLICY,
    ROUTING_COLLECT_ARTIFACT_SHA256,
    ROUTING_CONFIDENCE_FEATURE_CONTRACT,
    ROUTING_CONFIDENCE_MARGIN_FIELD,
    ROUTING_CONFIDENCE_SCORE_FIELD,
    ROUTING_MAX_EXAMPLES,
    ROUTING_PROJECTION_CONTRACT,
    ROUTING_ROUTE_CONTRACT_REVISION,
    ROUTING_SCHEMA_CONTRACT,
    ROUTING_SHORTLIST_LIMIT,
    RoutingCaseObservation,
    RoutingConfidenceCatalogState,
    RoutingCorpusObservation,
    RoutingQualityDataset,
    RoutingQualityMetrics,
    RoutingRouteObservation,
    RoutingThresholdCalibration,
    calibrate_routing_thresholds,
    gate_routing_quality,
    load_routing_canary_pack,
    load_routing_confidence_calibration,
    load_routing_quality_dataset,
    project_approved_50_routes,
    routing_certification_dataset,
    routing_catalog_projection_sha256,
    routing_example_passage,
    routing_prototype_hash,
    routing_source_passage,
    score_routing_quality,
    score_route_selection_quality,
    validate_canary_catalog_contract,
    validate_routing_confidence_calibration,
    validate_routing_confidence_catalog,
)
from buoy_search.multi_corpus_evals import load_multi_corpus_eval_dataset
from tests.routing_confidence_fixtures import (
    collect_calibration_payload,
    load_collect_routing_confidence_fixture,
)


DAGSTER_NAMESPACE = "site-dagster-io-v1"
ALPHA_NAMESPACE = "site-alpha-example-v1"


def canary_pack_payload(
    *,
    corpus_id: str = "alpha",
    namespace: str = ALPHA_NAMESPACE,
    approved: bool = True,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "corpus_id": corpus_id,
        "namespace": namespace,
        "review_status": "approved" if approved else "candidate",
        "human_approved": approved,
        "route_contract_revision": ROUTING_ROUTE_CONTRACT_REVISION,
        "canaries_disjoint_from_routing_examples": True,
        "cases": [
            {
                "id": f"{corpus_id}-named",
                "role": "named_self",
                "split": "gate",
                "question": f"What capabilities does {corpus_id} provide?",
                "expected_namespaces": [namespace],
                "confusable_with": [],
            },
            {
                "id": f"{corpus_id}-capability-calibration",
                "role": "capability_self",
                "split": "calibration",
                "question": "Which source handles orbital warehouse reconciliation?",
                "expected_namespaces": [namespace],
                "confusable_with": [],
            },
            {
                "id": f"{corpus_id}-capability-gate",
                "role": "capability_self",
                "split": "gate",
                "question": "Where are lunar inventory discrepancies explained?",
                "expected_namespaces": [namespace],
                "confusable_with": [],
            },
            {
                "id": f"{corpus_id}-confusable",
                "role": "confusable_self",
                "split": "gate",
                "question": "How are satellite stock counts reconciled after a failed load?",
                "expected_namespaces": [namespace],
                "confusable_with": ["dagster"],
            },
            {
                "id": f"{corpus_id}-contrast",
                "role": "contrast_other",
                "split": "calibration",
                "question": "How are software-defined data assets orchestrated?",
                "expected_namespaces": [DAGSTER_NAMESPACE],
                "confusable_with": [corpus_id],
            },
        ],
    }


def write_pack(directory: Path, payload: dict[str, object]) -> Path:
    path = directory / f"{payload['corpus_id']}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def make_card(
    namespace: str,
    *,
    examples: tuple[str, ...] = (),
    updated_at: str = "2026-08-15T00:00:00+00:00",
    ranking_pool: int = 20,
    prototype_vector_hash: str | None = None,
    passages: tuple[str, ...] = (),
) -> SimpleNamespace:
    return SimpleNamespace(
        namespace=namespace,
        enabled=True,
        title=namespace.removeprefix("site-").removesuffix("-v1"),
        summary=f"Capabilities for {namespace}.",
        aliases=[],
        tags=["knowledge"],
        routing_examples=list(examples),
        routing_passages=list(passages),
        semantic_hash=f"semantic-{namespace}",
        vector_hash=f"vector-{namespace}",
        routing_prototype_hash=f"prototype-{namespace}-{len(examples)}",
        routing_prototype_vector_hash=(
            prototype_vector_hash or f"prototype-vector-{namespace}-{len(examples)}"
        ),
        routing_model=ROUTING_MODEL,
        routing_model_revision=ROUTING_MODEL_REVISION,
        updated_at=updated_at,
        ranking_pool=ranking_pool,
    )


def perfect_observations(
    dataset: RoutingQualityDataset,
) -> dict[str, RoutingCaseObservation]:
    all_namespaces = [corpus.namespace for corpus in dataset.corpora]
    observations: dict[str, RoutingCaseObservation] = {}
    for case in dataset.cases:
        expected = list(case.expected_namespaces)
        ordered = [*expected, *(value for value in all_namespaces if value not in expected)]
        ordered = ordered[:ROUTING_SHORTLIST_LIMIT]
        scores = tuple(
            RoutingCorpusObservation(
                namespace=namespace,
                shortlist_rank=index,
                shortlist_cosine_score=1.0 - index / 100.0,
                reranker_rank=index,
                reranker_score=10.0 - index,
                exact_name_match=(
                    case.role in {"named_self", "legacy_named", "legacy_multi"}
                    and namespace in case.expected_namespaces
                ),
                winning_prototype_kind="card",
                winning_prototype_index=None,
                winning_prototype_hash=hashlib.sha256(
                    namespace.encode("utf-8")
                ).hexdigest(),
            )
            for index, namespace in enumerate(ordered, start=1)
        )
        if case.role in {"named_self", "legacy_named"}:
            fallback = tuple(ordered[:3])
            initial = fallback[:1]
            reason = "unique_title_or_alias"
            high_confidence = True
        elif len(expected) > 1:
            fallback = tuple(expected)
            initial = fallback
            reason = "multiple_named_corpora"
            high_confidence = True
        elif not expected:
            fallback = tuple(ordered[:3])
            initial = fallback
            reason = "ambiguous_prototype"
            high_confidence = False
        else:
            fallback = tuple(ordered[:3])
            initial = fallback[:1]
            reason = "high_confidence_prototype"
            high_confidence = True
        margin = scores[0].reranker_score - scores[1].reranker_score if len(scores) > 1 else None
        observations[case.id] = RoutingCaseObservation(
            case_id=case.id,
            corpus_scores=scores,
            reranker_margin=margin,
            fallback_namespaces=fallback,
            initial_namespaces=initial,
            selection_reason=reason,
            high_confidence=high_confidence,
            initial_fanout=len(initial),
        )
    return observations


def active_calibration_payload() -> dict[str, object]:
    module_dir = Path(routing_quality_module.__file__).resolve().parent

    def file_hash(name: str) -> str:
        return hashlib.sha256((module_dir / name).read_bytes()).hexdigest()

    return {
        "schema_version": ROUTING_ACTIVE_CALIBRATION_SCHEMA_VERSION,
        "calibration_id": ROUTING_CALIBRATION_ID,
        "calibration_revision": ROUTING_ACTIVE_CALIBRATION_REVISION,
        "mode": "active",
        "owner_approved": True,
        "score_floor": ROUTING_ACTIVE_SCORE_FLOOR,
        "margin_floor": ROUTING_ACTIVE_MARGIN_FLOOR,
        "bindings": {
            "routing_model": ROUTING_MODEL,
            "routing_model_revision": ROUTING_MODEL_REVISION,
            "routing_reranker_model": CROSS_ENCODER_MODEL,
            "routing_reranker_revision": CROSS_ENCODER_REVISION,
            "schema_contract": ROUTING_SCHEMA_CONTRACT,
            "projection": ROUTING_PROJECTION_CONTRACT,
            "shortlist_limit": ROUTING_SHORTLIST_LIMIT,
            "max_examples": ROUTING_MAX_EXAMPLES,
            "feature_contract": ROUTING_CONFIDENCE_FEATURE_CONTRACT,
            "score_field": ROUTING_CONFIDENCE_SCORE_FIELD,
            "margin_field": ROUTING_CONFIDENCE_MARGIN_FIELD,
            "canary_suite_sha256": ROUTING_ACTIVE_CANARY_SUITE_SHA256,
            "catalog_projection_sha256": (
                ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256
            ),
        },
        "calibration": {
            "case_count": ROUTING_ACTIVE_CALIBRATION_CASE_COUNT,
            "case_ids_sha256": ROUTING_ACTIVE_CALIBRATION_CASE_IDS_SHA256,
            "incorrect_high_confidence_singletons": 0,
        },
        "certification": {
            "passed": True,
            "case_count": ROUTING_ACTIVE_CERTIFICATION_CASE_COUNT,
            "case_ids_sha256": ROUTING_ACTIVE_CERTIFICATION_CASE_IDS_SHA256,
            "verdict_sha256": ROUTING_ACTIVE_QUALITY_VERDICT_SHA256,
        },
        "receipts": {
            "authorization_report_sha256": (
                ROUTING_ACTIVATION_AUTHORIZATION_REPORT_SHA256
            ),
            "authorization_source_commit": (
                ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_COMMIT
            ),
            "authorization_source_tree": (
                ROUTING_ACTIVATION_AUTHORIZATION_SOURCE_TREE
            ),
            "certified_dormant_report_sha256": "ab" * 32,
            "certified_dormant_source_commit": "bc" * 20,
            "certified_dormant_source_tree": "cd" * 20,
            "certified_dormant_working_tree_clean": True,
            "evaluator_runner_sha256": "de" * 32,
            "evaluator_scorer_sha256": file_hash("routing_quality.py"),
            "routing_module_sha256": file_hash("routing.py"),
            "cli_module_sha256": file_hash("cli.py"),
            "evidence_module_sha256": file_hash("evidence.py"),
            "collect_artifact_sha256": ROUTING_COLLECT_ARTIFACT_SHA256,
        },
    }


def anchored_calibration_payload() -> dict[str, object]:
    payload = active_calibration_payload()
    payload["schema_version"] = ROUTING_ANCHORED_CALIBRATION_SCHEMA_VERSION
    payload["calibration_revision"] = ROUTING_ANCHORED_CALIBRATION_REVISION
    payload["bindings"].update(
        {
            "certified_namespaces": list(ROUTING_ACTIVE_ANCHOR_NAMESPACES),
            "certified_catalog_projection_sha256": (
                ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256
            ),
            "catalog_policy": ROUTING_CATALOG_POLICY,
        }
    )
    return payload


def certification_inputs(
    dataset: RoutingQualityDataset,
    observations: dict[str, RoutingCaseObservation],
) -> tuple[
    RoutingQualityDataset,
    RoutingThresholdCalibration,
    RoutingQualityMetrics,
]:
    calibration = calibrate_routing_thresholds(dataset, observations)
    certification = routing_certification_dataset(dataset)
    certification_observations = {
        case.id: observations[case.id] for case in certification.cases
    }
    metrics = score_routing_quality(certification, certification_observations)
    return certification, calibration, metrics


def route_only_observations(
    observations: dict[str, RoutingCaseObservation],
) -> dict[str, RoutingRouteObservation]:
    return {
        case_id: RoutingRouteObservation(
            case_id=case_id,
            shortlist_namespaces=tuple(
                item.namespace
                for item in sorted(
                    observation.corpus_scores,
                    key=lambda item: item.shortlist_rank,
                )
            ),
            exact_name_namespaces=tuple(
                item.namespace
                for item in observation.corpus_scores
                if item.exact_name_match
            ),
            fallback_namespaces=observation.fallback_namespaces,
            initial_namespaces=observation.initial_namespaces,
            selection_reason=observation.selection_reason,
            high_confidence=observation.high_confidence,
            initial_fanout=observation.initial_fanout,
        )
        for case_id, observation in observations.items()
    }


class ApprovedRouteProjectionTests(unittest.TestCase):
    def test_projection_reuses_all_50_route_labels_without_answer_judgments(self) -> None:
        source = load_multi_corpus_eval_dataset()

        projected = project_approved_50_routes(source)

        self.assertEqual(len(projected), 50)
        self.assertEqual(sum(len(case.expected_namespaces) for case in projected), 58)
        self.assertEqual(projected[0].id, f"approved50:{source.cases[0].id}")
        self.assertEqual(projected[0].question, source.cases[0].question)
        self.assertFalse(hasattr(projected[0], "judgments"))
        self.assertEqual(
            {
                case.role for case in projected
            },
            {
                "legacy_named",
                "legacy_descriptor",
                "legacy_multi",
                "legacy_no_answer",
            },
        )

    def test_unapproved_legacy_basket_cannot_be_projected(self) -> None:
        source = replace(
            load_multi_corpus_eval_dataset(),
            human_approved_ground_truth=False,
            review_status="candidate",
        )

        with self.assertRaisesRegex(ValueError, "exact approved 50-case"):
            project_approved_50_routes(source)


class RoutingCanaryDatasetTests(unittest.TestCase):
    def test_exact_five_role_pack_loads_and_merges_deterministically(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            path = write_pack(directory, canary_pack_payload())

            pack = load_routing_canary_pack(path)
            first = load_routing_quality_dataset(canary_dir=directory)
            second = load_routing_quality_dataset(canary_dir=directory)

        self.assertEqual(len(pack.cases), 5)
        self.assertTrue(pack.human_approved)
        self.assertEqual(len(first.cases), 55)
        self.assertEqual(first.suite_sha256, second.suite_sha256)
        self.assertIn(ALPHA_NAMESPACE, first.approved_covered_namespaces)
        self.assertEqual(first.corpus_namespaces["alpha"], ALPHA_NAMESPACE)

    def test_pack_shape_roles_approval_and_disjointness_fail_closed(self) -> None:
        mutations = (
            ("unknown field", lambda value: value.update({"extra": True}), "fields are invalid"),
            (
                "unknown review status",
                lambda value: value.update({"review_status": "reviewed"}),
                "candidate.*approved",
            ),
            (
                "missing role",
                lambda value: value["cases"].pop(),
                "exactly five",
            ),
            (
                "approval mismatch",
                lambda value: value.update({"review_status": "candidate"}),
                "must agree",
            ),
            (
                "approval disjointness",
                lambda value: value.update(
                    {"canaries_disjoint_from_routing_examples": False}
                ),
                "must affirm",
            ),
            (
                "alternate route contract revision",
                lambda value: value.update(
                    {"route_contract_revision": "bounded-card-prototypes-v1"}
                ),
                "route_contract_revision",
            ),
            (
                "wrong self namespace",
                lambda value: value["cases"][0].update(
                    {"expected_namespaces": [DAGSTER_NAMESPACE]}
                ),
                "pack namespace",
            ),
            (
                "confusable self",
                lambda value: value["cases"][3].update({"confusable_with": []}),
                "at least one other",
            ),
            (
                "contrast subject",
                lambda value: value["cases"][4].update(
                    {"confusable_with": ["dagster"]}
                ),
                "corpus under test",
            ),
        )
        for label, mutate, message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                payload = canary_pack_payload()
                mutate(payload)
                path = write_pack(Path(temp_dir), payload)
                with self.assertRaisesRegex(ValueError, message):
                    load_routing_canary_pack(path)

    def test_cross_pack_corpus_references_and_normalized_questions_are_unique(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            payload = canary_pack_payload()
            payload["cases"][3]["confusable_with"] = ["unknown-corpus"]
            write_pack(directory, payload)
            with self.assertRaisesRegex(ValueError, "unknown confusable corpus"):
                load_routing_quality_dataset(canary_dir=directory)

        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            payload = canary_pack_payload()
            payload["cases"][1]["question"] = payload["cases"][0]["question"].upper()
            path = write_pack(directory, payload)
            with self.assertRaisesRegex(ValueError, "normalized questions"):
                load_routing_canary_pack(path)

    def test_pack_order_is_semantic_and_independent_of_filenames(self) -> None:
        beta = canary_pack_payload(
            corpus_id="beta",
            namespace="site-beta-example-v1",
        )
        for case in beta["cases"]:
            if case["role"] != "named_self":
                case["question"] = f"{case['question']} For beta."

        datasets = []
        for reverse_names in (False, True):
            with tempfile.TemporaryDirectory() as temp_dir:
                directory = Path(temp_dir)
                alpha_path = write_pack(directory, canary_pack_payload())
                beta_path = write_pack(directory, beta)
                if reverse_names:
                    alpha_path.rename(directory / "z.json")
                    beta_path.rename(directory / "a.json")
                datasets.append(load_routing_quality_dataset(canary_dir=directory))

        self.assertEqual(
            [pack.namespace for pack in datasets[0].packs],
            [pack.namespace for pack in datasets[1].packs],
        )
        self.assertEqual(
            [case.id for case in datasets[0].cases],
            [case.id for case in datasets[1].cases],
        )
        self.assertEqual(datasets[0].suite_sha256, datasets[1].suite_sha256)

    def test_candidate_pack_loads_but_does_not_supply_approved_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            write_pack(directory, canary_pack_payload(approved=False))
            dataset = load_routing_quality_dataset(canary_dir=directory)

        self.assertNotIn(ALPHA_NAMESPACE, dataset.approved_covered_namespaces)
        self.assertIn(ALPHA_NAMESPACE, dataset.covered_namespaces)
        cards = [make_card(corpus.namespace) for corpus in dataset.corpora]
        self.assertEqual(
            validate_canary_catalog_contract(dataset, cards),
            routing_catalog_projection_sha256(cards),
        )
        certification, calibration, metrics = certification_inputs(
            dataset, perfect_observations(dataset)
        )
        verdict = gate_routing_quality(
            certification, metrics, calibration=calibration, baseline=metrics
        )
        self.assertIn("approved_corpus_coverage", verdict.failed_checks)


class RoutingCatalogProjectionTests(unittest.TestCase):
    def test_digest_ignores_operational_fields_but_binds_examples_and_prototypes(self) -> None:
        original = make_card(ALPHA_NAMESPACE)
        operational_change = make_card(
            ALPHA_NAMESPACE,
            updated_at="2026-08-16T00:00:00+00:00",
            ranking_pool=999,
        )
        semantic_change = make_card(
            ALPHA_NAMESPACE,
            examples=("How is orbital inventory reconciled?",),
        )

        self.assertEqual(
            routing_catalog_projection_sha256([original]),
            routing_catalog_projection_sha256([operational_change]),
        )
        self.assertNotEqual(
            routing_catalog_projection_sha256([original]),
            routing_catalog_projection_sha256([semantic_change]),
        )
        projection_change = make_card(
            ALPHA_NAMESPACE,
            prototype_vector_hash="different-prototype-vector",
        )
        self.assertNotEqual(
            routing_catalog_projection_sha256([original]),
            routing_catalog_projection_sha256([projection_change]),
        )
        passage = routing_example_passage(
            title=semantic_change.title,
            summary=semantic_change.summary,
            example=semantic_change.routing_examples[0],
        )
        self.assertEqual(len(routing_prototype_hash(passage)), 64)

    def test_source_passages_bind_projection_without_changing_empty_legacy_bytes(
        self,
    ) -> None:
        legacy = make_card(ALPHA_NAMESPACE)
        without_field = SimpleNamespace(**vars(legacy))
        del without_field.routing_passages
        generated = make_card(
            ALPHA_NAMESPACE,
            passages=(
                "Section: Reconciliation\n"
                "Orbital inventory is reconciled after the warehouse load.",
            ),
        )

        self.assertEqual(
            routing_catalog_projection_sha256([legacy]),
            routing_catalog_projection_sha256([without_field]),
        )
        self.assertNotEqual(
            routing_catalog_projection_sha256([legacy]),
            routing_catalog_projection_sha256([generated]),
        )
        source = routing_source_passage(
            title=generated.title,
            summary=generated.summary,
            passage=generated.routing_passages[0],
        )
        self.assertEqual(len(routing_prototype_hash(source)), 64)

    def test_individual_evidence_vector_hash_binds_shortlist_authority(self) -> None:
        original = make_card(ALPHA_NAMESPACE)
        original.routing_evidence_vectors = [1.0]
        original.routing_evidence_vectors_hash = "a" * 64
        changed = SimpleNamespace(**vars(original))
        changed.routing_evidence_vectors_hash = "b" * 64

        self.assertNotEqual(
            routing_catalog_projection_sha256([original]),
            routing_catalog_projection_sha256([changed]),
        )

        stale = SimpleNamespace(**vars(original))
        stale.routing_evidence_vectors = []
        with self.assertRaisesRegex(ValueError, "hash without vectors"):
            routing_catalog_projection_sha256([stale])

    def test_source_passage_projection_rejects_malformed_or_over_budget_cards(
        self,
    ) -> None:
        malformed = make_card(ALPHA_NAMESPACE, passages=(" padded ",))
        with self.assertRaisesRegex(ValueError, "routing_passages"):
            routing_catalog_projection_sha256([malformed])

        over_budget = make_card(
            ALPHA_NAMESPACE,
            examples=tuple(f"Manual {index}" for index in range(8)),
            passages=("Section: Extra\nGenerated evidence.",),
        )
        with self.assertRaisesRegex(ValueError, "more than 8"):
            routing_catalog_projection_sha256([over_budget])

    def test_catalog_contract_requires_approved_coverage_and_exact_disjointness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            write_pack(directory, canary_pack_payload())
            dataset = load_routing_quality_dataset(canary_dir=directory)

        cards = [make_card(corpus.namespace) for corpus in dataset.corpora]
        digest = validate_canary_catalog_contract(dataset, cards)
        self.assertEqual(digest, routing_catalog_projection_sha256(cards))

        missing = [card for card in cards if card.namespace != ALPHA_NAMESPACE]
        with self.assertRaisesRegex(ValueError, "expects a non-eligible"):
            validate_canary_catalog_contract(dataset, missing)

        collision_question = dataset.cases_by_id["alpha-capability-gate"].question
        colliding = [
            make_card(
                card.namespace,
                examples=(collision_question,) if card.namespace == ALPHA_NAMESPACE else (),
            )
            for card in cards
        ]
        with self.assertRaisesRegex(ValueError, "duplicates a stored routing example"):
            validate_canary_catalog_contract(dataset, colliding)


class RoutingThresholdCalibrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        directory = Path(self.temp_dir.name)
        write_pack(directory, canary_pack_payload())
        self.dataset = load_routing_quality_dataset(canary_dir=directory)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_calibration_uses_only_calibration_split_and_is_deterministic(self) -> None:
        observations = perfect_observations(self.dataset)

        first = calibrate_routing_thresholds(self.dataset, observations)
        gate_case = self.dataset.cases_by_id["alpha-capability-gate"]
        changed = dict(observations)
        gate_observation = changed[gate_case.id]
        changed[gate_case.id] = replace(
            gate_observation,
            high_confidence=False,
            initial_namespaces=gate_observation.fallback_namespaces,
            initial_fanout=len(gate_observation.fallback_namespaces),
            selection_reason="ambiguous_prototype",
        )
        second = calibrate_routing_thresholds(self.dataset, changed)

        self.assertEqual(first, second)
        self.assertEqual(first.calibration_case_count, 2)
        self.assertEqual(first.correct_high_confidence_singletons, 2)
        self.assertEqual(first.incorrect_high_confidence_singletons, 0)

    def test_source_passage_winners_are_valid_quality_observations(self) -> None:
        observations = perfect_observations(self.dataset)
        case = self.dataset.cases[0]
        observation = observations[case.id]
        first = observation.corpus_scores[0]
        observations[case.id] = replace(
            observation,
            corpus_scores=(
                replace(
                    first,
                    winning_prototype_kind="source",
                    winning_prototype_index=0,
                ),
                *observation.corpus_scores[1:],
            ),
        )

        metrics = score_routing_quality(self.dataset, observations)

        self.assertIn(case.id, metrics.cases_by_id)

    def test_unsafe_top_case_is_excluded_by_next_breakpoint_margin(self) -> None:
        observations = perfect_observations(self.dataset)
        calibration_id = "alpha-capability-calibration"
        original = observations[calibration_id]
        expected = self.dataset.cases_by_id[calibration_id].expected_namespaces[0]
        subject = DAGSTER_NAMESPACE
        by_namespace = {item.namespace: item for item in original.corpus_scores}
        ordered_namespaces = [
            subject,
            expected,
            *(
                item.namespace
                for item in sorted(
                    original.corpus_scores, key=lambda value: value.reranker_rank
                )
                if item.namespace not in {subject, expected}
            ),
        ]
        unsafe_scores = tuple(
            replace(
                by_namespace[namespace],
                shortlist_rank=index,
                reranker_rank=index,
                reranker_score=(6.0 if index == 1 else 5.9 if index == 2 else 5.9 - index),
            )
            for index, namespace in enumerate(ordered_namespaces, start=1)
        )
        observations[calibration_id] = replace(
            original,
            corpus_scores=unsafe_scores,
            reranker_margin=0.1,
            fallback_namespaces=tuple(ordered_namespaces[:3]),
            initial_namespaces=(subject,),
            initial_fanout=1,
            high_confidence=True,
        )

        result = calibrate_routing_thresholds(self.dataset, observations)

        self.assertEqual(result.incorrect_high_confidence_singletons, 0)
        self.assertEqual(result.correct_high_confidence_singletons, 1)
        self.assertEqual(result.score_floor, 9.0)
        # Equal observed decisions choose the more conservative governed floor.
        self.assertEqual(result.margin_floor, 1.0)

    def test_single_eligible_corpus_cannot_satisfy_a_two_corpus_margin(self) -> None:
        observations = perfect_observations(self.dataset)
        for case in self.dataset.cases:
            if case.split != "calibration":
                continue
            original = observations[case.id]
            expected = case.expected_namespaces[0]
            sole = replace(
                next(
                    score
                    for score in original.corpus_scores
                    if score.namespace == expected
                ),
                shortlist_rank=1,
                reranker_rank=1,
            )
            observations[case.id] = replace(
                original,
                corpus_scores=(sole,),
                reranker_margin=None,
                fallback_namespaces=(expected,),
                initial_namespaces=(expected,),
                initial_fanout=1,
            )

        result = calibrate_routing_thresholds(self.dataset, observations)

        self.assertEqual(result.correct_high_confidence_singletons, 0)
        self.assertEqual(result.incorrect_high_confidence_singletons, 0)


class RoutingQualityGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        directory = Path(self.temp_dir.name)
        write_pack(directory, canary_pack_payload())
        self.dataset = load_routing_quality_dataset(canary_dir=directory)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_perfect_route_only_observations_pass_every_pure_gate(self) -> None:
        certification, calibration, metrics = certification_inputs(
            self.dataset, perfect_observations(self.dataset)
        )
        verdict = gate_routing_quality(
            certification, metrics, calibration=calibration, baseline=metrics
        )

        self.assertTrue(verdict.passed, verdict.failed_checks)
        self.assertEqual(metrics.shortlist_recall_at_12, 1.0)
        self.assertEqual(metrics.route_recall_at_3, 1.0)
        self.assertEqual(metrics.incorrect_high_confidence_singletons, 0)
        self.assertLessEqual(metrics.average_initial_fanout, 2.0)

    def test_strategy_neutral_baseline_has_no_fake_prototype_scores(self) -> None:
        candidate = perfect_observations(self.dataset)
        certification = routing_certification_dataset(self.dataset)
        candidate_subset = {
            case.id: candidate[case.id] for case in certification.cases
        }

        candidate_metrics = score_routing_quality(
            certification, candidate_subset
        )
        baseline_metrics = score_route_selection_quality(
            certification, route_only_observations(candidate_subset)
        )

        self.assertEqual(candidate_metrics, baseline_metrics)
        baseline = route_only_observations(candidate_subset)
        first_id = certification.cases[0].id
        baseline[first_id] = replace(
            baseline[first_id], shortlist_namespaces=()
        )
        with self.assertRaisesRegex(ValueError, "shortlist must contain"):
            score_route_selection_quality(certification, baseline)

    def test_activation_rejects_calibration_case_reuse_and_bad_receipt(self) -> None:
        observations = perfect_observations(self.dataset)
        calibration = calibrate_routing_thresholds(self.dataset, observations)
        full_metrics = score_routing_quality(self.dataset, observations)
        with self.assertRaisesRegex(ValueError, "certification-only"):
            gate_routing_quality(
                self.dataset,
                full_metrics,
                calibration=calibration,
            )

        certification = routing_certification_dataset(self.dataset)
        metrics = score_routing_quality(
            certification,
            {case.id: observations[case.id] for case in certification.cases},
        )
        verdict = gate_routing_quality(
            certification,
            metrics,
            calibration=replace(calibration, calibration_case_count=999),
            baseline=metrics,
        )
        self.assertIn("calibration_contract", verdict.failed_checks)

        missing_baseline = gate_routing_quality(
            certification,
            metrics,
            calibration=calibration,
        )
        self.assertIn("baseline_bound", missing_baseline.failed_checks)

    def test_aggregate_pass_cannot_hide_one_corpus_route_miss(self) -> None:
        observations = perfect_observations(self.dataset)
        case_id = "approved50:d11-vector-recall-debug"
        original = observations[case_id]
        expected = self.dataset.cases_by_id[case_id].expected_namespaces[0]
        replacement = tuple(
            item.namespace
            for item in sorted(original.corpus_scores, key=lambda value: value.reranker_rank)
            if item.namespace != expected
        )[:3]
        observations[case_id] = replace(
            original,
            fallback_namespaces=replacement,
            initial_namespaces=replacement,
            initial_fanout=len(replacement),
            high_confidence=False,
            selection_reason="ambiguous_prototype",
        )

        certification, calibration, metrics = certification_inputs(
            self.dataset, observations
        )
        verdict = gate_routing_quality(
            certification, metrics, calibration=calibration, baseline=metrics
        )

        self.assertGreaterEqual(metrics.route_recall_at_3, 0.95)
        self.assertIn("per_corpus_positive_recall_at_3", verdict.failed_checks)
        turbopuffer = metrics.per_corpus_by_namespace[expected]
        self.assertLess(turbopuffer.positive_recall_at_3, 1.0)

    def test_known_d11_and_d12_growth_displacements_are_case_visible(self) -> None:
        observations = perfect_observations(self.dataset)
        for raw_id in (
            "d11-vector-recall-debug",
            "d12-namespace-schema-inspection",
        ):
            case_id = f"approved50:{raw_id}"
            original = observations[case_id]
            expected = self.dataset.cases_by_id[case_id].expected_namespaces[0]
            replacement = tuple(
                item.namespace
                for item in sorted(
                    original.corpus_scores, key=lambda value: value.reranker_rank
                )
                if item.namespace != expected
            )[:3]
            observations[case_id] = replace(
                original,
                fallback_namespaces=replacement,
                initial_namespaces=replacement,
                initial_fanout=3,
                high_confidence=False,
                selection_reason="ambiguous_prototype",
            )

        metrics = score_routing_quality(self.dataset, observations)

        for raw_id in (
            "d11-vector-recall-debug",
            "d12-namespace-schema-inspection",
        ):
            self.assertFalse(
                metrics.cases_by_id[f"approved50:{raw_id}"].route_complete
            )

    def test_wrong_no_answer_singleton_fails(self) -> None:
        observations = perfect_observations(self.dataset)
        no_answer_id = "approved50:n01-transit-schedule"
        no_answer = observations[no_answer_id]
        observations[no_answer_id] = replace(
            no_answer,
            initial_namespaces=no_answer.fallback_namespaces[:1],
            initial_fanout=1,
            high_confidence=True,
            selection_reason="high_confidence_prototype",
        )
        certification, calibration, metrics = certification_inputs(
            self.dataset, observations
        )
        verdict = gate_routing_quality(
            certification, metrics, calibration=calibration, baseline=metrics
        )

        self.assertEqual(metrics.no_answer_high_confidence_singletons, 1)
        self.assertIn("no_answer_high_confidence_singletons", verdict.failed_checks)

    def test_contrast_rank_one_cannot_calibrate(self) -> None:
        observations = perfect_observations(self.dataset)
        contrast_id = "alpha-contrast"
        contrast = observations[contrast_id]
        subject = ALPHA_NAMESPACE
        reordered = (
            subject,
            *(value for value in contrast.fallback_namespaces if value != subject),
        )
        if len(reordered) < 3:
            reordered = (
                *reordered,
                next(
                    item.namespace
                    for item in contrast.corpus_scores
                    if item.namespace not in reordered
                ),
            )
        observations[contrast_id] = replace(
            contrast,
            fallback_namespaces=reordered[:3],
            initial_namespaces=(subject,),
            initial_fanout=1,
            high_confidence=True,
        )

        with self.assertRaisesRegex(ValueError, "fails its route contract"):
            calibrate_routing_thresholds(self.dataset, observations)

    def test_baseline_regression_is_independent_of_aggregate_threshold(self) -> None:
        baseline_observations = perfect_observations(self.dataset)
        certification = routing_certification_dataset(self.dataset)
        baseline = score_routing_quality(
            certification,
            {case.id: baseline_observations[case.id] for case in certification.cases},
        )
        current_observations = dict(baseline_observations)
        case_id = "alpha-capability-gate"
        original = current_observations[case_id]
        current_observations[case_id] = replace(
            original,
            fallback_namespaces=original.fallback_namespaces[1:],
            initial_namespaces=original.fallback_namespaces[1:],
            initial_fanout=len(original.fallback_namespaces[1:]),
            high_confidence=False,
            selection_reason="ambiguous_prototype",
        )
        current = score_routing_quality(
            certification,
            {case.id: current_observations[case.id] for case in certification.cases},
        )
        calibration = calibrate_routing_thresholds(
            self.dataset, current_observations
        )

        verdict = gate_routing_quality(
            certification,
            current,
            calibration=calibration,
            baseline=baseline,
        )

        self.assertIn("no_previously_passing_case_regression", verdict.failed_checks)
        self.assertIn("no_per_corpus_recall_regression", verdict.failed_checks)


class RoutingConfidenceCalibrationLoaderTests(unittest.TestCase):
    def write_payload(self, payload: object) -> tuple[tempfile.TemporaryDirectory, Path]:
        temporary = tempfile.TemporaryDirectory()
        path = Path(temporary.name) / "calibration.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return temporary, path

    def load_active_calibration(self):  # noqa: ANN201 - focused test helper.
        temporary, path = self.write_payload(active_calibration_payload())
        self.addCleanup(temporary.cleanup)
        with patch.object(
            routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
        ):
            return load_routing_confidence_calibration()

    def load_anchored_calibration(self):  # noqa: ANN201 - focused test helper.
        temporary, path = self.write_payload(anchored_calibration_payload())
        self.addCleanup(temporary.cleanup)
        with patch.object(
            routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
        ):
            return load_routing_confidence_calibration()

    def test_default_path_and_exact_collect_artifact_are_inactive(self) -> None:
        self.assertEqual(
            DEFAULT_ROUTING_CALIBRATION.name,
            "automatic_routing_confidence_calibration.json",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            path.write_text(json.dumps(collect_calibration_payload()), encoding="utf-8")

            calibration = load_routing_confidence_calibration(path)

        self.assertEqual(calibration.mode, "collect")
        self.assertFalse(calibration.owner_approved)
        self.assertIsNone(calibration.score_floor)
        self.assertIsNone(calibration.margin_floor)
        self.assertFalse(calibration.certification_passed)

    def test_active_or_malformed_artifact_cannot_self_activate(self) -> None:
        mutations = (
            (
                "active",
                lambda value: value.update(
                    {
                        "mode": "active",
                        "owner_approved": True,
                        "score_floor": 1.0,
                        "margin_floor": 0.1,
                    }
                ),
                "Schema-v1",
            ),
            (
                "wrong model",
                lambda value: value["bindings"].update(
                    {"routing_reranker_model": "mutable/model"}
                ),
                "incompatible",
            ),
            (
                "threshold",
                lambda value: value.update({"score_floor": 0.0}),
                "has no thresholds",
            ),
            (
                "certification",
                lambda value: value["certification"].update({"passed": True}),
                "cannot pass",
            ),
            (
                "boolean case count",
                lambda value: value["certification"].update({"case_count": False}),
                "zero cases",
            ),
            (
                "unknown field",
                lambda value: value.update({"threshold_override": 0.0}),
                "fields are invalid",
            ),
        )
        for label, mutate, message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                payload = collect_calibration_payload()
                mutate(payload)
                path = Path(temp_dir) / "calibration.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    load_routing_confidence_calibration(path)

    def test_exact_schema_v2_active_artifact_loads_only_as_package_resource(self) -> None:
        temporary, path = self.write_payload(active_calibration_payload())
        self.addCleanup(temporary.cleanup)

        with self.assertRaisesRegex(ValueError, "installed package artifact"):
            load_routing_confidence_calibration(path)

        with patch.object(
            routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
        ):
            calibration = load_routing_confidence_calibration()

        self.assertEqual(calibration.mode, "active")
        self.assertTrue(calibration.owner_approved)
        self.assertEqual(calibration.score_floor, ROUTING_ACTIVE_SCORE_FLOOR)
        self.assertEqual(calibration.margin_floor, ROUTING_ACTIVE_MARGIN_FLOOR)
        self.assertTrue(calibration.certification_passed)
        self.assertEqual(
            calibration.certification_case_ids_sha256,
            ROUTING_ACTIVE_CERTIFICATION_CASE_IDS_SHA256,
        )
        self.assertIsNotNone(calibration.calibration)
        self.assertIsNotNone(calibration.receipts)

    def test_schema_v3_artifact_carries_the_exact_certified_anchor(self) -> None:
        calibration = self.load_anchored_calibration()

        self.assertEqual(
            calibration.schema_version,
            ROUTING_ANCHORED_CALIBRATION_SCHEMA_VERSION,
        )
        self.assertEqual(
            calibration.bindings.certified_namespaces,
            tuple(ROUTING_ACTIVE_ANCHOR_NAMESPACES),
        )
        self.assertEqual(
            calibration.bindings.certified_catalog_projection_sha256,
            ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
        )
        self.assertEqual(calibration.bindings.catalog_policy, ROUTING_CATALOG_POLICY)

    def test_schema_v3_classifies_exact_anchor_and_every_valid_drift(self) -> None:
        calibration = self.load_anchored_calibration()
        anchor_cards = [
            SimpleNamespace(namespace=namespace)
            for namespace in ROUTING_ACTIVE_ANCHOR_NAMESPACES
        ]
        with patch.object(
            routing_quality_module,
            "routing_catalog_projection_sha256",
            return_value=ROUTING_ACTIVE_CATALOG_PROJECTION_SHA256,
        ):
            exact = validate_routing_confidence_catalog(calibration, anchor_cards)

        self.assertIsInstance(exact, RoutingConfidenceCatalogState)
        self.assertEqual(exact.mode, "certified")
        self.assertEqual(exact.provisional_namespaces, ())

        drift_cases = {
            "added": [*anchor_cards, SimpleNamespace(namespace="site-new-example-v1")],
            "missing": anchor_cards[:-1],
            "changed projection": anchor_cards,
        }
        for label, cards in drift_cases.items():
            with self.subTest(label=label), patch.object(
                routing_quality_module,
                "routing_catalog_projection_sha256",
                return_value="11" * 32,
            ):
                state = validate_routing_confidence_catalog(calibration, cards)

            self.assertEqual(state.mode, "provisional")
            self.assertEqual(
                state.provisional_namespaces,
                tuple(sorted(card.namespace for card in cards)),
            )

    def test_schema_v2_retains_strict_whole_catalog_drift_failure(self) -> None:
        calibration = self.load_active_calibration()
        with patch.object(
            routing_quality_module,
            "routing_catalog_projection_sha256",
            return_value="11" * 32,
        ), self.assertRaisesRegex(ValueError, "does not match"):
            validate_routing_confidence_catalog(
                calibration,
                [SimpleNamespace(namespace="site-new-example-v1")],
            )

    def test_schema_v3_rejects_mutated_anchor_authority(self) -> None:
        payload = anchored_calibration_payload()
        payload["bindings"]["certified_namespaces"] = [
            *ROUTING_ACTIVE_ANCHOR_NAMESPACES,
            "site-new-example-v1",
        ]
        temporary, path = self.write_payload(payload)
        self.addCleanup(temporary.cleanup)
        with patch.object(
            routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
        ), self.assertRaisesRegex(ValueError, "certified_namespaces"):
            load_routing_confidence_calibration()

    def test_explicit_collect_authority_is_independent_of_default_active_phase(
        self,
    ) -> None:
        temporary, path = self.write_payload(active_calibration_payload())
        self.addCleanup(temporary.cleanup)
        with patch.object(
            routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
        ):
            active = load_routing_confidence_calibration()
            collect = load_collect_routing_confidence_fixture()

        self.assertEqual(active.mode, "active")
        self.assertEqual(collect.mode, "collect")
        self.assertFalse(collect.owner_approved)
        validate_routing_confidence_calibration(collect)

    def test_schema_v2_active_artifact_rejects_every_frozen_authority_change(self) -> None:
        mutations = (
            ("revision", lambda value: value.update({"calibration_revision": "other-v1"})),
            ("owner", lambda value: value.update({"owner_approved": False})),
            ("score", lambda value: value.update({"score_floor": ROUTING_ACTIVE_SCORE_FLOOR + 0.1})),
            ("margin", lambda value: value.update({"margin_floor": ROUTING_ACTIVE_MARGIN_FLOOR + 0.1})),
            ("suite", lambda value: value["bindings"].update({"canary_suite_sha256": "12" * 32})),
            ("projection", lambda value: value["bindings"].update({"catalog_projection_sha256": "23" * 32})),
            ("calibration", lambda value: value["calibration"].update({"case_count": 7})),
            ("certification", lambda value: value["certification"].update({"passed": False})),
            ("authorization", lambda value: value["receipts"].update({"authorization_report_sha256": "34" * 32})),
            ("dirty", lambda value: value["receipts"].update({"certified_dormant_working_tree_clean": False})),
            ("source", lambda value: value["receipts"].update({"routing_module_sha256": "45" * 32})),
            ("unknown", lambda value: value.update({"threshold_override": 0.0})),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                payload = active_calibration_payload()
                mutate(payload)
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_schema_v2_active_artifact_rejects_each_bound_byte_hash_mismatch(
        self,
    ) -> None:
        for receipt_field in (
            "evaluator_scorer_sha256",
            "routing_module_sha256",
            "cli_module_sha256",
            "evidence_module_sha256",
            "collect_artifact_sha256",
        ):
            with self.subTest(receipt_field=receipt_field):
                payload = active_calibration_payload()
                payload["receipts"][receipt_field] = "00" * 32
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_schema_v2_active_artifact_rejects_each_missing_receipt_field(
        self,
    ) -> None:
        receipt_fields = tuple(active_calibration_payload()["receipts"])
        for receipt_field in receipt_fields:
            with self.subTest(receipt_field=receipt_field):
                payload = active_calibration_payload()
                del payload["receipts"][receipt_field]
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_schema_v2_active_artifact_rejects_malformed_receipts(self) -> None:
        mutations = (
            ("receipt container", lambda value: value.update({"receipts": []})),
            (
                "digest",
                lambda value: value["receipts"].update(
                    {"evaluator_runner_sha256": "not-a-sha256"}
                ),
            ),
            (
                "commit",
                lambda value: value["receipts"].update(
                    {"certified_dormant_source_commit": "ab" * 19}
                ),
            ),
            (
                "tree",
                lambda value: value["receipts"].update(
                    {"certified_dormant_source_tree": "not-a-git-object"}
                ),
            ),
            (
                "clean flag",
                lambda value: value["receipts"].update(
                    {"certified_dormant_working_tree_clean": 1}
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label):
                payload = active_calibration_payload()
                mutate(payload)
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_schema_mode_mixtures_and_nonfinite_active_thresholds_fail(self) -> None:
        schema_two_collect = collect_calibration_payload()
        schema_two_collect["schema_version"] = ROUTING_ACTIVE_CALIBRATION_SCHEMA_VERSION
        schema_one_active = active_calibration_payload()
        schema_one_active["schema_version"] = ROUTING_CALIBRATION_SCHEMA_VERSION
        for label, payload in (
            ("schema-two collect", schema_two_collect),
            ("schema-one active", schema_one_active),
        ):
            with self.subTest(label=label):
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

        for value in (math.nan, math.inf, -math.inf, True):
            with self.subTest(threshold=value):
                payload = active_calibration_payload()
                payload["score_floor"] = value
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_schema_version_requires_an_exact_integer_for_both_schemas(self) -> None:
        cases = (
            ("schema-v1 boolean", collect_calibration_payload, True),
            ("schema-v1 float", collect_calibration_payload, 1.0),
            ("schema-v2 boolean", active_calibration_payload, True),
            ("schema-v2 float", active_calibration_payload, 2.0),
        )
        for label, payload_factory, schema_version in cases:
            with self.subTest(label=label):
                payload = payload_factory()
                payload["schema_version"] = schema_version
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaisesRegex(ValueError, "schema is incompatible"):
                    load_routing_confidence_calibration()

    def test_raw_frozen_fields_reject_coercible_values_in_both_schemas(
        self,
    ) -> None:
        cases = (
            (
                "collect ID whitespace",
                collect_calibration_payload,
                lambda value: value.update(
                    {"calibration_id": f" {ROUTING_CALIBRATION_ID} "}
                ),
            ),
            (
                "active ID whitespace",
                active_calibration_payload,
                lambda value: value.update(
                    {"calibration_id": f" {ROUTING_CALIBRATION_ID} "}
                ),
            ),
            (
                "collect shortlist float",
                collect_calibration_payload,
                lambda value: value["bindings"].update(
                    {"shortlist_limit": float(ROUTING_SHORTLIST_LIMIT)}
                ),
            ),
            (
                "active shortlist float",
                active_calibration_payload,
                lambda value: value["bindings"].update(
                    {"shortlist_limit": float(ROUTING_SHORTLIST_LIMIT)}
                ),
            ),
            (
                "collect max examples float",
                collect_calibration_payload,
                lambda value: value["bindings"].update(
                    {"max_examples": float(ROUTING_MAX_EXAMPLES)}
                ),
            ),
            (
                "active max examples float",
                active_calibration_payload,
                lambda value: value["bindings"].update(
                    {"max_examples": float(ROUTING_MAX_EXAMPLES)}
                ),
            ),
            (
                "collect certification count float",
                collect_calibration_payload,
                lambda value: value["certification"].update({"case_count": 0.0}),
            ),
            (
                "active calibration count float",
                active_calibration_payload,
                lambda value: value["calibration"].update(
                    {"case_count": float(ROUTING_ACTIVE_CALIBRATION_CASE_COUNT)}
                ),
            ),
            (
                "active calibration false singleton count float",
                active_calibration_payload,
                lambda value: value["calibration"].update(
                    {"incorrect_high_confidence_singletons": 0.0}
                ),
            ),
            (
                "active certification count float",
                active_calibration_payload,
                lambda value: value["certification"].update(
                    {"case_count": float(ROUTING_ACTIVE_CERTIFICATION_CASE_COUNT)}
                ),
            ),
            (
                "collect owner integer",
                collect_calibration_payload,
                lambda value: value.update({"owner_approved": 0}),
            ),
            (
                "active owner integer",
                active_calibration_payload,
                lambda value: value.update({"owner_approved": 1}),
            ),
            (
                "collect certification integer",
                collect_calibration_payload,
                lambda value: value["certification"].update({"passed": 0}),
            ),
            (
                "active certification integer",
                active_calibration_payload,
                lambda value: value["certification"].update({"passed": 1}),
            ),
            (
                "active clean integer",
                active_calibration_payload,
                lambda value: value["receipts"].update(
                    {"certified_dormant_working_tree_clean": 1}
                ),
            ),
        )
        for label, payload_factory, mutate in cases:
            with self.subTest(label=label):
                payload = payload_factory()
                mutate(payload)
                temporary, path = self.write_payload(payload)
                self.addCleanup(temporary.cleanup)
                with patch.object(
                    routing_quality_module, "DEFAULT_ROUTING_CALIBRATION", path
                ), self.assertRaises(ValueError):
                    load_routing_confidence_calibration()

    def test_constructed_collect_authority_requires_exact_scalar_types(self) -> None:
        class StringSubclass(str):
            pass

        collect = load_collect_routing_confidence_fixture()
        mutations = (
            ("schema", lambda value: replace(value, schema_version=1.0)),
            ("ID", lambda value: replace(
                value,
                calibration_id=StringSubclass(ROUTING_CALIBRATION_ID),
            )),
            ("owner", lambda value: replace(value, owner_approved=0)),
            (
                "certification passed",
                lambda value: replace(value, certification_passed=0),
            ),
            (
                "certification count",
                lambda value: replace(value, certification_case_count=0.0),
            ),
            (
                "shortlist",
                lambda value: replace(
                    value,
                    bindings=replace(
                        value.bindings,
                        shortlist_limit=float(ROUTING_SHORTLIST_LIMIT),
                    ),
                ),
            ),
            (
                "max examples",
                lambda value: replace(
                    value,
                    bindings=replace(
                        value.bindings,
                        max_examples=float(ROUTING_MAX_EXAMPLES),
                    ),
                ),
            ),
            (
                "binding string",
                lambda value: replace(
                    value,
                    bindings=replace(
                        value.bindings,
                        routing_model=StringSubclass(ROUTING_MODEL),
                    ),
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), self.assertRaises(ValueError):
                validate_routing_confidence_calibration(mutate(collect))

    def test_constructed_active_authority_validates_the_exact_nested_graph(
        self,
    ) -> None:
        class StringSubclass(str):
            pass

        class FloatSubclass(float):
            pass

        active = self.load_active_calibration()
        mutations = (
            ("schema", lambda value: replace(value, schema_version=2.0)),
            ("owner", lambda value: replace(value, owner_approved=1)),
            (
                "score",
                lambda value: replace(
                    value,
                    score_floor=FloatSubclass(ROUTING_ACTIVE_SCORE_FLOOR),
                ),
            ),
            (
                "certification passed",
                lambda value: replace(value, certification_passed=1),
            ),
            (
                "certification count",
                lambda value: replace(
                    value,
                    certification_case_count=float(
                        ROUTING_ACTIVE_CERTIFICATION_CASE_COUNT
                    ),
                ),
            ),
            (
                "shortlist",
                lambda value: replace(
                    value,
                    bindings=replace(
                        value.bindings,
                        shortlist_limit=float(ROUTING_SHORTLIST_LIMIT),
                    ),
                ),
            ),
            (
                "max examples",
                lambda value: replace(
                    value,
                    bindings=replace(
                        value.bindings,
                        max_examples=float(ROUTING_MAX_EXAMPLES),
                    ),
                ),
            ),
            (
                "calibration count",
                lambda value: replace(
                    value,
                    calibration=replace(
                        value.calibration,
                        case_count=float(ROUTING_ACTIVE_CALIBRATION_CASE_COUNT),
                    ),
                ),
            ),
            (
                "calibration false singleton count",
                lambda value: replace(
                    value,
                    calibration=replace(
                        value.calibration,
                        incorrect_high_confidence_singletons=0.0,
                    ),
                ),
            ),
            (
                "receipt clean",
                lambda value: replace(
                    value,
                    receipts=replace(
                        value.receipts,
                        certified_dormant_working_tree_clean=1,
                    ),
                ),
            ),
            (
                "receipt string",
                lambda value: replace(
                    value,
                    receipts=replace(
                        value.receipts,
                        evaluator_runner_sha256=StringSubclass(
                            value.receipts.evaluator_runner_sha256
                        ),
                    ),
                ),
            ),
            (
                "bindings structural stand-in",
                lambda value: replace(
                    value, bindings=SimpleNamespace(**vars(value.bindings))
                ),
            ),
            (
                "calibration structural stand-in",
                lambda value: replace(
                    value,
                    calibration=SimpleNamespace(**vars(value.calibration)),
                ),
            ),
            (
                "receipts structural stand-in",
                lambda value: replace(
                    value, receipts=SimpleNamespace(**vars(value.receipts))
                ),
            ),
        )
        for label, mutate in mutations:
            with self.subTest(label=label), self.assertRaises(ValueError):
                validate_routing_confidence_calibration(mutate(active))

    def test_duplicate_json_fields_and_nonfinite_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate fields"):
                load_routing_confidence_calibration(path)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "calibration.json"
            path.write_text('{"schema_version":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "non-finite"):
                load_routing_confidence_calibration(path)


if __name__ == "__main__":
    unittest.main()
