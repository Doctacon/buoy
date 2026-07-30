from __future__ import annotations

from dataclasses import replace
import unittest

from buoy_search.semantics_pipeline import (
    Candidate,
    SemanticPipelineError,
    TaxonomyJudgment,
    TaxonomyProposal,
    allocate_sample,
    build_taxonomy,
    confidence_policy,
    normalize_label,
    resolve_concepts,
    validate_extraction,
)


def candidate(index: int, label: str, concept_type: str = "technology") -> Candidate:
    return Candidate(
        f"sc_{index:061d}", f"el_{index:061d}", "source", label, label,
        normalize_label(label), normalize_label(label), concept_type,
        f"Definition of {label}", label, 0.92,
    )


class SameVerifier:
    def classify(self, left, right, *, lexical_similarity):  # noqa: ANN001
        del left, right, lexical_similarity
        return type("Judgment", (), {"classification": "same_concept", "confidence": 0.95, "rationale": "same domain sense"})()


class AcceptVerifier:
    def verify(self, proposal, concepts):  # noqa: ANN001
        del proposal, concepts
        return TaxonomyJudgment(True, 0.99, rationale="bounded support")


class MediumSameVerifier:
    def classify(self, left, right, *, lexical_similarity):  # noqa: ANN001
        del left, right, lexical_similarity
        return type("Judgment", (), {
            "classification": "same_concept", "confidence": 0.70,
            "rationale": "Plausible alias requiring provisional disposition.",
        })()


class SemanticPipelineTests(unittest.TestCase):
    def test_exact_extraction_validation_normalization_and_deduplication(self) -> None:
        content = "Café search uses BM25. Café search is useful."
        raw = {"candidates": [{
            "surface_form": "Café search", "canonical_label": "  CAFÉ   Search! ",
            "concept_type": "technology", "definition": "A retrieval technique.",
            "supporting_excerpt": "Café search uses BM25.", "confidence": 0.9,
        }] * 2}
        values = validate_extraction(raw, content=content, evidence_row_id="el_1", source_namespace="source")
        self.assertEqual(len(values), 1)
        self.assertEqual(values[0].normalized_label, "café search")
        with self.assertRaisesRegex(SemanticPipelineError, "exact content substring"):
            validate_extraction({"candidates": [{**raw["candidates"][0], "surface_form": "cafe search"}]}, content=content, evidence_row_id="el_1", source_namespace="source")

    def test_confidence_formula_thresholds_and_raw_confidence_not_dominant(self) -> None:
        low = confidence_policy({"schema_validity": 0, "exact_substring": 0, "extraction_confidence": 1, "type_consistency": 0, "structural_validity": 0})
        self.assertEqual(low.status, "rejected")
        provisional = confidence_policy({"schema_validity": 1, "exact_substring": 1, "extraction_confidence": 1, "type_consistency": 1, "structural_validity": 1})
        self.assertEqual(provisional.status, "provisional")
        accepted = confidence_policy({"schema_validity": 1, "exact_substring": 1, "extraction_confidence": 0.8, "verifier_judgment": 0.95, "type_consistency": 1, "structural_validity": 1})
        self.assertEqual(accepted.status, "accepted")
        self.assertEqual(accepted.breakdown["verifier_judgment"], 0.95)
        with self.assertRaises(SemanticPipelineError):
            confidence_policy({"schema_validity": 1}, accepted_threshold=0.6, provisional_threshold=0.6)

    def test_medium_same_concept_remains_distinct_with_provisional_close_match(self) -> None:
        values = [candidate(1, "customer flow"), candidate(2, "customer flow process")]
        concepts, mentions, proposals, calls = resolve_concepts(
            values, merge_verifier=MediumSameVerifier()
        )
        self.assertEqual((len(concepts), len(mentions), calls), (2, 2, 1))
        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].predicate, "close_match")
        self.assertEqual(proposals[0].status_ceiling, "provisional")
        concepts = tuple(replace(value, status="accepted") for value in concepts)
        edges, _, _ = build_taxonomy(
            concepts, proposals, verifier=AcceptVerifier()
        )
        self.assertEqual((len(edges), edges[0].status), (1, "provisional"))

    def test_union_find_merges_aliases_but_keeps_incompatible_senses_distinct(self) -> None:
        values = [candidate(1, "vector database"), candidate(2, "vector database system"), candidate(3, "vector database", "product")]
        concepts, mentions, _, calls = resolve_concepts(values, merge_verifier=SameVerifier())
        self.assertEqual(len(concepts), 2)
        self.assertEqual(len(mentions), 3)
        self.assertGreaterEqual(calls, 1)
        self.assertEqual({item.concept_type for item in concepts}, {"technology", "product"})

    def test_lexical_only_fallback_is_deterministic_and_conservative(self) -> None:
        values = [candidate(1, "SSO"), candidate(2, "SSO"), candidate(3, "single sign on")]
        first = resolve_concepts(values, merge_verifier=None)
        second = resolve_concepts(list(reversed(values)), merge_verifier=None)
        self.assertEqual(first, second)
        self.assertEqual(len(first[0]), 2)
        self.assertEqual(first[3], 0)

    def test_taxonomy_enforces_grammar_symmetry_cycles_depth_parents_and_status(self) -> None:
        concepts, _, _, _ = resolve_concepts([candidate(index, f"term {index}") for index in range(16)], merge_verifier=None)
        concepts = tuple(replace(item, status="accepted") for item in concepts)
        ids = [item.concept_id for item in concepts]
        proposals = [TaxonomyProposal(ids[0], "related", ids[1]), TaxonomyProposal(ids[1], "related", ids[0])]
        proposals += [TaxonomyProposal(ids[0], "broader", ids[index]) for index in range(1, 6)]
        proposals += [TaxonomyProposal(ids[index], "broader", ids[index + 1]) for index in range(1, 15)]
        proposals += [TaxonomyProposal(ids[15], "broader", ids[0]), TaxonomyProposal(ids[0], "narrower", ids[1])]
        edges, diagnostics, calls = build_taxonomy(concepts, proposals, verifier=AcceptVerifier())
        symmetric = [item for item in edges if item.predicate == "related"]
        self.assertEqual(len(symmetric), 1)
        self.assertGreater(diagnostics["prevented_parent_limit"], 0)
        self.assertGreater(diagnostics["invalid_edges"], 0)
        self.assertGreater(diagnostics["prevented_cycles"] + diagnostics["prevented_depth"], 0)
        self.assertGreaterEqual(calls, len(edges))
        self.assertTrue(all(item.predicate in {"broader", "related", "close_match"} for item in edges))

    def test_generic_noun_rejected_and_supported_aliases_merge(self) -> None:
        generic = {
            "surface_form": "system", "canonical_label": "system",
            "concept_type": "domain_concept", "definition": "Generic filler.",
            "supporting_excerpt": "system", "confidence": 0.99,
        }
        self.assertEqual(
            validate_extraction(
                {"candidates": [generic]}, content="system",
                evidence_row_id="el_generic", source_namespace="source",
            ),
            (),
        )
        values = [candidate(1, "SSO"), candidate(2, "single sign on")]
        concepts, mentions, _, calls = resolve_concepts(
            values, merge_verifier=SameVerifier()
        )
        self.assertEqual((len(concepts), len(mentions), calls), (1, 2, 1))
        self.assertIn("SSO", concepts[0].aliases)
        self.assertEqual(concepts[0].status, "accepted")
        self.assertEqual(concepts[0].policy_breakdown["verifier_judgment"], 0.95)

    def test_customer_onboarding_merge_and_deployment_senses_remain_distinct(self) -> None:
        onboarding = candidate(1, "customer implementation", "process")
        onboarding = replace(onboarding, definition="Customer onboarding delivery process")
        customer = candidate(2, "customer onboarding", "process")
        customer = replace(customer, definition="Customer onboarding delivery process")
        software = replace(
            candidate(3, "deployment", "process"),
            definition="Releasing software to production",
        )
        account = replace(
            candidate(4, "deployment", "process"),
            definition="Deploying a customer onboarding team",
        )

        class SenseVerifier:
            def classify(self, left, right, *, lexical_similarity):  # noqa: ANN001
                del lexical_similarity
                pair = {left.candidate_id, right.candidate_id}
                if pair == {onboarding.candidate_id, customer.candidate_id}:
                    return type("J", (), {"classification": "same_concept", "confidence": 0.96, "rationale": "Same customer process."})()
                return type("J", (), {"classification": "distinct", "confidence": 0.98, "rationale": "Different senses."})()

        concepts, _, _, _ = resolve_concepts(
            [onboarding, customer, software, account],
            merge_verifier=SenseVerifier(),
        )
        self.assertEqual(len(concepts), 3)
        deployments = [item for item in concepts if item.normalized_label == "deployment"]
        self.assertEqual(len(deployments), 2)

    def test_taxonomy_verifier_confidence_is_a_direct_publication_gate(self) -> None:
        concepts, _, _, _ = resolve_concepts(
            [candidate(1, "alpha"), candidate(2, "beta")], merge_verifier=None
        )
        concepts = tuple(replace(value, status="accepted") for value in concepts)
        ids = [value.concept_id for value in concepts]

        class MediumVerifier:
            def verify(self, proposal, concepts):  # noqa: ANN001
                del proposal, concepts
                return TaxonomyJudgment(True, 0.65, rationale="Medium support.")

        edges, _, _ = build_taxonomy(
            concepts, [TaxonomyProposal(ids[0], "related", ids[1])],
            verifier=MediumVerifier(),
        )
        self.assertEqual((len(edges), edges[0].status), (1, "provisional"))

    def test_rejected_alternative_does_not_suppress_later_valid_edge(self) -> None:
        concepts, _, _, _ = resolve_concepts(
            [candidate(1, "alpha"), candidate(2, "beta")], merge_verifier=None
        )
        concepts = tuple(replace(value, status="accepted") for value in concepts)
        ids = [value.concept_id for value in concepts]

        class SequencedVerifier:
            def verify(self, proposal, concepts):  # noqa: ANN001
                del concepts
                if proposal.predicate == "broader":
                    return TaxonomyJudgment(
                        False, 0.50, alternative="related", rationale="Too weak."
                    )
                return TaxonomyJudgment(True, 0.95, rationale="Supported.")

        edges, _, _ = build_taxonomy(
            concepts,
            [
                TaxonomyProposal(ids[0], "broader", ids[1]),
                TaxonomyProposal(ids[0], "related", ids[1]),
            ],
            verifier=SequencedVerifier(),
        )
        self.assertEqual((len(edges), edges[0].predicate), (1, "related"))
        self.assertEqual(edges[0].status, "accepted")

    def test_taxonomy_alternatives_rededuplicate_and_overlong_basis_is_rejected(self) -> None:
        concepts, _, _, _ = resolve_concepts(
            [candidate(1, "alpha"), candidate(2, "beta")],
            merge_verifier=SameVerifier(),
        )
        # SameVerifier does not compare disjoint tokens, so force publishable endpoints.
        concepts = tuple(replace(item, status="accepted") for item in concepts)
        ids = [item.concept_id for item in concepts]

        class AlternativeVerifier:
            def verify(self, proposal, concepts):  # noqa: ANN001
                del proposal, concepts
                return TaxonomyJudgment(False, 0.95, alternative="related", rationale="Better related.")

        proposals = [
            TaxonomyProposal(ids[0], "broader", ids[1]),
            TaxonomyProposal(ids[0], "close_match", ids[1]),
            TaxonomyProposal(ids[0], "related", ids[1], representative_mention_ids=tuple(str(i) for i in range(9))),
        ]
        edges, diagnostics, _ = build_taxonomy(
            concepts, proposals, verifier=AlternativeVerifier()
        )
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0].predicate, "related")
        self.assertGreaterEqual(diagnostics["invalid_edges"], 2)

    def test_namespace_aware_sampling_allocation_is_exact_and_deterministic(self) -> None:
        counts = {"large": 90, "small": 10, "empty": 0}
        self.assertEqual(sum(allocate_sample(counts, 25).values()), 25)
        self.assertEqual(allocate_sample(counts, 25), allocate_sample(dict(reversed(list(counts.items()))), 25))
        self.assertGreaterEqual(allocate_sample(counts, 25)["small"], 1)


if __name__ == "__main__":
    unittest.main()
