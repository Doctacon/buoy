from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from buoy_search.evidence_remote import LEDGER_ATTRIBUTES
from buoy_search.semantics_models import ModelContract, StructuredResult
from buoy_search.semantics_pipeline import (
    EXTRACTION_SCHEMA,
    PAIR_VERIFICATION_SCHEMA,
    TAXONOMY_PROPOSAL_SCHEMA,
    TAXONOMY_VERIFICATION_SCHEMA,
    TaxonomyJudgment,
    TaxonomyProposal,
)
from buoy_search.semantics_remote import (
    CATALOG_SCHEMA,
    CONCEPT_SCHEMA,
    EXTRACTION_SCHEMA_REMOTE,
    MENTION_SCHEMA,
    TAXONOMY_SCHEMA,
    BuildLimits,
    SemanticBuildError,
    _BudgetedInferenceClient,
    _catalog_manifest,
    _identity_payload,
    _manifest_hash,
    _model_extract,
    _persisted_row_hash,
    _semantic_logical_hash,
    create_semantic_build,
    derive_build_names,
    estimate_semantic_build,
    inspect_semantic_build,
    verify_semantic_build,
)


class FakeNamespace:
    def __init__(self, client: "FakeRemote", name: str) -> None:
        self.client, self.name = client, name

    @property
    def data(self):  # noqa: ANN201
        return self.client.data.setdefault(self.name, {"exists": False, "rows": {}, "schema": {}})

    def exists(self, **kwargs):  # noqa: ANN001, ANN201
        del kwargs
        return self.data["exists"]

    def metadata(self, **kwargs):  # noqa: ANN001, ANN201
        del kwargs
        if not self.data["exists"]:
            raise RuntimeError("not found")
        return {"schema": {"id": {"type": "string"}, **copy.deepcopy(self.data["schema"])}, "approx_row_count": len(self.data["rows"]), "approx_logical_bytes": 1000, "created_at": "2026-07-29T00:00:00Z", "last_write_at": "2026-07-29T00:00:01Z"}

    def query(self, **kwargs):  # noqa: ANN001, ANN201
        self.client.query_calls.append((self.name, copy.deepcopy(kwargs)))
        self.client.events.append(("query", self.name))
        rows = list(self.data["rows"].values())

        def matches(row, expression):  # noqa: ANN001, ANN202
            if expression is None:
                return True
            if expression[0] == "And":
                return all(matches(row, item) for item in expression[1])
            field, operation, value = expression
            if operation == "Eq":
                return row.get(field) == value
            if operation == "Gt":
                return row.get(field) > value
            raise AssertionError(expression)

        rows = [row for row in rows if matches(row, kwargs.get("filters"))]
        field, direction = kwargs.get("rank_by", ("id", "asc"))
        rows.sort(key=lambda row: row[field], reverse=direction == "desc")
        include = kwargs.get("include_attributes", [])
        projected = [{"id": row["id"], **{key: row[key] for key in include if key in row}} for row in rows[:kwargs.get("limit", 10)]]
        return {"rows": projected, "billing": {"billable_logical_bytes_queried": 1, "billable_logical_bytes_returned": len(projected)}}

    def write(self, **kwargs):  # noqa: ANN001, ANN201
        if self.name.startswith("evidence-branch") or self.name == "source":
            raise AssertionError("source/evidence branch write attempted")
        if self.client.fail_namespace == self.name:
            raise RuntimeError("injected failure")
        self.client.write_calls.append((self.name, copy.deepcopy(kwargs)))
        self.client.events.append(("write", self.name))
        self.data["exists"] = True
        if "schema" in kwargs:
            self.data["schema"] = copy.deepcopy(kwargs["schema"])
        affected = []
        for row in kwargs.get("upsert_rows", []):
            if kwargs.get("upsert_condition") == ("id", "Eq", None) and row["id"] in self.data["rows"]:
                continue
            self.data["rows"][row["id"]] = copy.deepcopy(row)
            affected.append(row["id"])
        return {"rows_affected": len(affected), "upserted_ids": affected}


class FakeRemote:
    def __init__(self, row_count: int, *, candidates_per_row: int = 1) -> None:
        self.data: dict[str, dict[str, object]] = {}
        self.query_calls: list[tuple[str, dict[str, object]]] = []
        self.write_calls: list[tuple[str, dict[str, object]]] = []
        self.events: list[tuple[str, str]] = []
        self.fail_namespace: str | None = None
        ledger_rows = {}
        branch_rows = {}
        for index in range(row_count):
            source_id = f"row_{index:06d}"
            ledger_id = f"el_{index:061d}"
            surfaces = [f"Term{index:04d}x{part}" for part in range(candidates_per_row)]
            if index == 0 and candidates_per_row >= 2:
                surfaces[:2] = ["SSO", "single-sign-on"]
            content = " ".join(surfaces)
            chunk_hash = f"c{index:063d}"
            branch_rows[source_id] = {
                "id": source_id, "content": content, "title": f"Title {index}",
                "section_path": f"Section {index}",
                "canonical_url": f"https://example.com/{index}",
                "chunk_hash": chunk_hash, "page_hash": f"p{index:063d}",
                "doc_kind": "documentation", "tags": ["synthetic"],
                "vector": [9.0],
            }
            values = {
                "snapshot_id": "evidence_test", "source_namespace": "source", "branch_namespace": "evidence-branch-test",
                "source_row_id": source_id, "site_id": "site", "status": "active", "canonical_url": f"https://example.com/{index}",
                "page_hash": f"p{index:063d}", "chunk_hash": chunk_hash, "embedding_text_hash": f"e{index:063d}",
                "plan_id": "plan", "applied_at": "2026-07-29T00:00:00Z", "ordinal": index,
            }
            ledger_rows[ledger_id] = {"id": ledger_id, **values}
        stale = {key: value for key, value in next(iter(ledger_rows.values())).items()}
        stale["id"] = "el_stale"; stale["source_row_id"] = "row_stale"; stale["status"] = "retained_stale"
        ledger_rows[stale["id"]] = stale
        self.data["evidence-ledger-test"] = {"exists": True, "rows": ledger_rows, "schema": {}}
        self.data["evidence-branch-test"] = {"exists": True, "rows": branch_rows, "schema": {}}

    def namespace(self, namespace: str) -> FakeNamespace:
        return FakeNamespace(self, namespace)


class FakeModel:
    def __init__(self, candidates_per_row: int = 1, *, rich: bool = False) -> None:
        self.candidates_per_row = candidates_per_row
        self.rich = rich
        self.calls = 0
        self.maximum_concurrent = 0
        self.concurrent = 0
        self.taxonomy_proposal_calls = 0
        self.taxonomy_verification_calls = 0
        self.doctor_calls = 0
        self.drift_contract = None

    def doctor(self):  # noqa: ANN201
        self.calls += 1
        self.doctor_calls += 1
        contract = self.drift_contract or model_contract()
        return {"model_contract": contract.to_dict(), "evidence_transmitted": False}

    def structured_chat(self, *, messages, schema, max_output_tokens):  # noqa: ANN001, ANN201
        del max_output_tokens
        self.concurrent += 1; self.maximum_concurrent = max(self.maximum_concurrent, self.concurrent)
        try:
            self.calls += 1
            if schema == EXTRACTION_SCHEMA:
                content = json.loads(messages[1]["content"])["content"]
                surfaces = content.split()[:self.candidates_per_row]
                value = {"candidates": [{"surface_form": surface, "canonical_label": surface, "concept_type": "technology", "definition": f"Definition for {surface}.", "supporting_excerpt": surface, "confidence": 0.92} for surface in surfaces]}
            elif schema == PAIR_VERIFICATION_SCHEMA:
                pair = json.loads(messages[1]["content"])
                labels = {pair["left"]["label"].casefold(), pair["right"]["label"].casefold()}
                same = labels == {"sso", "single-sign-on"}
                if self.rich:
                    roots = {value.split("-", 1)[0] for value in labels}
                    same = same or (len(roots) == 1 and len(labels) == 2)
                value = {
                    "classification": "same_concept" if same else "distinct",
                    "confidence": 0.96,
                    "rationale": "Same synthetic sign-on concept." if same else "Different synthetic terms.",
                }
            elif schema == TAXONOMY_PROPOSAL_SCHEMA:
                concepts = json.loads(messages[1]["content"])
                proposals = []
                if self.rich:
                    accepted = [value for value in concepts if value["mention_count"] >= 2]
                    predicates = ("broader", "related", "close_match")
                    for offset, predicate in enumerate(predicates):
                        if len(accepted) > offset + 1:
                            proposals.append({
                                "subject_id": accepted[offset]["id"],
                                "predicate": predicate,
                                "object_id": accepted[offset + 1]["id"],
                                "basis": "semantic_induction",
                                "representative_mention_ids": [],
                            })
                    self.taxonomy_proposal_calls += 1
                elif len(concepts) >= 2:
                    proposals.append({
                        "subject_id": concepts[0]["id"], "predicate": "related",
                        "object_id": concepts[1]["id"], "basis": "semantic_induction",
                        "representative_mention_ids": [],
                    })
                value = {"proposals": proposals}
            elif schema == TAXONOMY_VERIFICATION_SCHEMA:
                self.taxonomy_verification_calls += 1
                confidence = (
                    0.70
                    if self.rich and self.taxonomy_verification_calls % 5 == 0
                    else 0.95
                )
                value = {"supported": True, "alternative": "none", "confidence": confidence, "rationale": "Synthetic relation supported."}
            else:
                raise AssertionError("unexpected semantic schema")
            return StructuredResult(value, len(json.dumps(value)), 0.001)
        finally:
            self.concurrent -= 1


def model_contract() -> ModelContract:
    return ModelContract(1, "openai_chat_completions_local_v1", "fake-local", "1", "fake", "sha256:" + "a" * 64, "runtime_digest", None, 8192, 7, True, True, "openai_json_schema", "semantic-extraction-v1")


def evidence_catalog_row() -> dict[str, object]:
    identity = {"sources": [{"namespace": "source", "embedding_model": "local-model", "embedding_precision": "float32", "vector_dimensions": 384}]}
    return {"state": "complete", "snapshot_id": "evidence_test", "ledger_namespace": "evidence-ledger-test", "source_identity_json": json.dumps(identity)}


class SequencedModel:
    def __init__(self, values):  # noqa: ANN001
        self.values = list(values)
        self.calls = 0
        self.messages = []

    def structured_chat(self, *, messages, schema, max_output_tokens):  # noqa: ANN001, ANN201
        del schema, max_output_tokens
        self.messages.append(tuple(dict(value) for value in messages))
        self.calls += 1
        return StructuredResult(self.values.pop(0), 1, 0.001)


class SemanticRemoteTests(unittest.TestCase):
    def run_build(self, remote, model, out, **kwargs):  # noqa: ANN001, ANN201
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            return create_semantic_build(remote, evidence_snapshot_id="evidence_test", model_client=model, model_contract=model_contract(), out_root=out, **kwargs)

    def test_semantic_exact_support_repair_is_bounded_and_failure_is_safe(self) -> None:
        invalid = {"candidates": [{"surface_form": "missing", "canonical_label": "missing", "concept_type": "technology", "definition": "Definition.", "supporting_excerpt": "missing", "confidence": 0.9}]}
        valid = {"candidates": [{"surface_form": "present", "canonical_label": "present", "concept_type": "technology", "definition": "Definition.", "supporting_excerpt": "present", "confidence": 0.9}]}
        model = SequencedModel([invalid, valid])
        candidates, retries = _model_extract(model, content="present", evidence_row_id="el_1", source_namespace="source")
        self.assertEqual((len(candidates), retries, model.calls), (1, 1, 2))
        self.assertIn("missing", model.messages[1][-1]["content"])
        self.assertIn("semantic_exact_support", model.messages[1][-1]["content"])
        exhausted = SequencedModel([invalid, invalid, invalid])
        with self.assertRaisesRegex(SemanticBuildError, "bounded repair"):
            _model_extract(exhausted, content="present", evidence_row_id="el_1", source_namespace="source")
        self.assertEqual(exhausted.calls, 3)

    def test_build_identity_includes_sampling_thresholds_and_limits(self) -> None:
        base = dict(snapshot_id="evidence_test", coverage="full", sample_size=None, sample_seed=0, model_contract=model_contract(), embedding_contract=[], accepted_threshold=0.85, provisional_threshold=0.65, limits=BuildLimits())
        identity = _identity_payload(**base)
        self.assertEqual(derive_build_names(identity), derive_build_names(dict(reversed(list(identity.items())))))
        for field, value in (("sample_seed", 1), ("accepted_threshold", 0.9), ("limits", BuildLimits(maximum_rows=499))):
            changed = dict(base); changed[field] = value
            self.assertNotEqual(derive_build_names(identity).build_id, derive_build_names(_identity_payload(**changed)).build_id)
        self.assertNotIn("endpoint", json.dumps(identity))
        self.assertEqual(EXTRACTION_SCHEMA["additionalProperties"], False)

    def test_budget_wrapper_counts_failed_calls_and_stops_before_overrun(self) -> None:
        failing = SequencedModel([{"candidates": []}])
        budgeted = _BudgetedInferenceClient(failing, 1)
        budgeted.structured_chat(messages=(), schema={}, max_output_tokens=1)
        with self.assertRaisesRegex(SemanticBuildError, "model-call budget"):
            budgeted.structured_chat(messages=(), schema={}, max_output_tokens=1)
        self.assertEqual((budgeted.calls, failing.calls), (1, 1))

    def test_model_call_budget_is_hard_before_the_next_call(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(SemanticBuildError, "no remaining model-call budget"):
            self.run_build(remote, model, Path(temporary), limits=BuildLimits(maximum_model_calls=1))
        self.assertEqual(model.calls, 1)
        self.assertFalse(remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False))

    def test_exact_remote_schemas_and_catalog_is_written_last(self) -> None:
        remote, model = FakeRemote(3), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_build(remote, model, Path(temporary))
        schema_by_prefix = {
            "buoy-semantics-extractions-": EXTRACTION_SCHEMA_REMOTE,
            "buoy-semantics-concepts-": CONCEPT_SCHEMA,
            "buoy-semantics-mentions-": MENTION_SCHEMA,
            "buoy-semantics-taxonomy-": TAXONOMY_SCHEMA,
            "buoy-semantics-catalog-v1": CATALOG_SCHEMA,
        }
        for namespace, expected in schema_by_prefix.items():
            matches = [value for name, value in remote.data.items() if name == namespace or name.startswith(namespace)]
            self.assertEqual(matches[0]["schema"], expected)
        self.assertEqual(remote.write_calls[-1][0], "buoy-semantics-catalog-v1")
        self.assertEqual(result["selected_rows"], 3)
        self.assertTrue(all(call[0] != "evidence-branch-test" for call in remote.write_calls))
        ledger_queries = [kwargs for name, kwargs in remote.query_calls if name == "evidence-ledger-test"]
        self.assertTrue(all("content" not in kwargs["include_attributes"] and "vector" not in kwargs["include_attributes"] for kwargs in ledger_queries))

    def test_incomplete_staging_requires_resume_and_conflicts_fail_closed(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            identity_row = evidence_catalog_row()
            # Derive the deterministic concepts namespace from a first injected failure.
            remote.fail_namespace = "pending"
            with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=identity_row):
                # Discover the name by failing every concepts write after staging.
                original = FakeNamespace.write
                def fail_concepts(namespace, **kwargs):  # noqa: ANN001, ANN202
                    if namespace.name.startswith("buoy-semantics-concepts-"):
                        raise RuntimeError("injected failure")
                    return original(namespace, **kwargs)
                with patch.object(FakeNamespace, "write", fail_concepts), self.assertRaises(Exception):
                    create_semantic_build(remote, evidence_snapshot_id="evidence_test", model_client=model, model_contract=model_contract(), out_root=out)
            self.assertEqual(model.calls, 4)
            with self.assertRaisesRegex(SemanticBuildError, "--resume"):
                self.run_build(remote, model, out)
            staging_name = next(name for name in remote.data if name.startswith("buoy-semantics-extractions-"))
            staged = next(iter(remote.data[staging_name]["rows"].values()))
            original_hash = staged["chunk_hash"]
            staged["chunk_hash"] = "conflict"
            with self.assertRaisesRegex(SemanticBuildError, "conflicts"):
                self.run_build(remote, model, out, resume=True)
            staged["chunk_hash"] = original_hash
            branch_row = remote.data["evidence-branch-test"]["rows"]["row_000000"]
            original_content = branch_row["content"]
            branch_row["content"] = f"{original_content} changed"
            with self.assertRaisesRegex(SemanticBuildError, "conflicts"):
                self.run_build(remote, model, out, resume=True)
            branch_row["content"] = original_content
            result = self.run_build(remote, model, out, resume=True)
            self.assertEqual(result["model_calls"], 5)
            self.assertEqual(model.calls, 7)

    def test_evidence_bytes_and_full_rows_fail_before_model_while_sample_is_explicit(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(SemanticBuildError, "evidence byte budget"):
                self.run_build(
                    remote, model, Path(temporary),
                    limits=BuildLimits(maximum_evidence_bytes=1),
                )
        self.assertEqual(model.calls, 0)
        self.assertFalse(any(
            name.startswith("buoy-semantics-extractions-") and value["exists"]
            for name, value in remote.data.items()
        ))

        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(SemanticBuildError, "maximum rows"):
                self.run_build(
                    remote, model, Path(temporary),
                    limits=BuildLimits(maximum_rows=1),
                )
        self.assertEqual(model.calls, 0)

        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            sampled = self.run_build(
                remote, model, Path(temporary), sample_size=1, sample_seed=17,
                limits=BuildLimits(maximum_rows=1),
            )
        self.assertEqual(sampled["selected_rows"], 1)

    def test_final_rows_use_conditional_first_write_and_race_conflicts(self) -> None:
        remote, model = FakeRemote(1), FakeModel()
        original = FakeNamespace.write

        def race(namespace, **kwargs):  # noqa: ANN001, ANN202
            if namespace.name.startswith("buoy-semantics-concepts-") and kwargs.get("upsert_rows"):
                first = kwargs["upsert_rows"][0]
                namespace.data["exists"] = True
                namespace.data["rows"][first["id"]] = {**copy.deepcopy(first), "definition": "raced"}
            return original(namespace, **kwargs)

        with tempfile.TemporaryDirectory() as temporary, patch.object(FakeNamespace, "write", race):
            with self.assertRaisesRegex(SemanticBuildError, "write count mismatch"):
                self.run_build(remote, model, Path(temporary))
        final_writes = [
            kwargs for name, kwargs in remote.write_calls
            if name.startswith("buoy-semantics-") and name != "buoy-semantics-catalog-v1"
            and kwargs.get("upsert_rows")
        ]
        self.assertTrue(all(kwargs.get("upsert_condition") == ("id", "Eq", None) for kwargs in final_writes))
        self.assertFalse(remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False))

    def test_final_exact_scan_detects_post_write_mutation_before_catalog(self) -> None:
        remote, model = FakeRemote(1), FakeModel()
        original = FakeNamespace.write

        def mutate_after_write(namespace, **kwargs):  # noqa: ANN001, ANN202
            response = original(namespace, **kwargs)
            if namespace.name.startswith("buoy-semantics-concepts-") and kwargs.get("upsert_rows"):
                first_id = kwargs["upsert_rows"][0]["id"]
                namespace.data["rows"][first_id]["definition"] = "mutated after write"
            return response

        with tempfile.TemporaryDirectory() as temporary, patch.object(FakeNamespace, "write", mutate_after_write):
            with self.assertRaisesRegex(SemanticBuildError, "row hash|hash or count"):
                self.run_build(remote, model, Path(temporary))
        self.assertFalse(remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False))

    def test_completed_reuse_recomputes_row_hashes_from_persisted_contents(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            self.run_build(remote, model, out)
            concepts = next(
                value for name, value in remote.data.items()
                if name.startswith("buoy-semantics-concepts-")
            )
            next(iter(concepts["rows"].values()))["definition"] = "corrupted"
            with self.assertRaisesRegex(SemanticBuildError, "row hash"):
                self.run_build(remote, model, out)

    def test_completed_reuse_rejects_coherently_rehashed_catalog_contract_drift(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            built = self.run_build(remote, model, out)
            catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
            catalog["evidence_snapshot_id"] = "evidence_different"
            catalog["manifest_hash"] = _catalog_manifest(catalog)["manifest_hash"]
            with self.assertRaisesRegex(SemanticBuildError, "build identity"):
                self.run_build(remote, model, out)

    def test_completed_reuse_rejects_coherently_rehashed_schema_version_drift(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            built = self.run_build(remote, model, out)
            catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
            catalog["semantic_schema_version"] = 999
            catalog["manifest_hash"] = _catalog_manifest(catalog)["manifest_hash"]
            with self.assertRaisesRegex(SemanticBuildError, "schema version"):
                self.run_build(remote, model, out)

    def test_build_rejects_unknown_taxonomy_representative_mentions(self) -> None:
        remote, model = FakeRemote(2), FakeModel()

        class DanglingProposer:
            call_count = 0

            def propose(self, concepts):  # noqa: ANN001, ANN201
                self.call_count += 1
                return [TaxonomyProposal(
                    concepts[0].concept_id,
                    "related",
                    concepts[1].concept_id,
                    representative_mention_ids=("mention_missing",),
                )]

        class SupportingVerifier:
            def verify(self, proposal, concepts):  # noqa: ANN001, ANN201
                del proposal, concepts
                return TaxonomyJudgment(True, 0.95, rationale="Synthetic support.")

        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(
            SemanticBuildError, "representative mention does not exist"
        ):
            self.run_build(
                remote,
                model,
                Path(temporary),
                taxonomy_proposer=DanglingProposer(),
                taxonomy_verifier=SupportingVerifier(),
            )
        self.assertFalse(
            remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False)
        )

    def test_resume_staging_reads_exact_selected_ids_and_bounds_full_rows(self) -> None:
        remote, model = FakeRemote(2), FakeModel()
        limits = BuildLimits(maximum_derived_bytes=100_000)
        original = FakeNamespace.write

        def fail_concepts(namespace, **kwargs):  # noqa: ANN001, ANN202
            if namespace.name.startswith("buoy-semantics-concepts-"):
                raise RuntimeError("injected failure")
            return original(namespace, **kwargs)

        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            with patch.object(FakeNamespace, "write", fail_concepts), self.assertRaises(Exception):
                self.run_build(remote, model, out, limits=limits)
            staging_name = next(
                name for name in remote.data
                if name.startswith("buoy-semantics-extractions-")
            )
            next(iter(remote.data[staging_name]["rows"].values()))["content_hash"] = (
                "x" * 100_001
            )
            remote.query_calls.clear()
            with self.assertRaisesRegex(SemanticBuildError, "staging exceeds"):
                self.run_build(remote, model, out, limits=limits, resume=True)
        staging_queries = [
            kwargs for name, kwargs in remote.query_calls if name == staging_name
        ]
        self.assertEqual(staging_queries[0]["include_attributes"], [])
        self.assertTrue(all(
            query["limit"] == 2 and query["filters"][0] == "id"
            for query in staging_queries[1:]
        ))

    def test_evidence_reverification_precedes_adjacent_final_scans_and_catalog(self) -> None:
        remote, model = FakeRemote(2), FakeModel()

        def verify(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            del args, kwargs
            remote.events.append(("verify", "evidence"))
            return {"verified": True}

        with tempfile.TemporaryDirectory() as temporary, patch(
            "buoy_search.semantics_remote.verify_evidence_snapshot",
            side_effect=verify,
        ), patch(
            "buoy_search.semantics_remote._read_catalog_row",
            return_value=evidence_catalog_row(),
        ):
            create_semantic_build(
                remote, evidence_snapshot_id="evidence_test",
                model_client=model, model_contract=model_contract(),
                out_root=Path(temporary),
            )
        last_verify = max(
            index for index, event in enumerate(remote.events)
            if event == ("verify", "evidence")
        )
        catalog_write = remote.events.index(
            ("write", "buoy-semantics-catalog-v1"), last_verify
        )
        adjacent = remote.events[last_verify + 1:catalog_write]
        self.assertEqual([kind for kind, _ in adjacent], ["query", "query", "query"])
        self.assertEqual(
            [name.split("-", 3)[2] for _, name in adjacent],
            ["concepts", "mentions", "taxonomy"],
        )

    def test_500_row_structural_measurement_is_streamed_bounded_and_exact(self) -> None:
        remote = FakeRemote(500, candidates_per_row=6)
        for index, row in enumerate(
            remote.data["evidence-branch-test"]["rows"].values()
        ):
            if index >= 100:
                break
            surfaces = row["content"].split()
            surfaces[:2] = [f"Flow{index:04d}", f"Flow{index:04d}-step"]
            row["content"] = " ".join(surfaces)
        model = FakeModel(6, rich=True)

        class StructuralProposer:
            call_count = 0

            def propose(self, concepts):  # noqa: ANN001, ANN201
                self.call_count += 1
                accepted = [value for value in concepts if value.mention_count >= 2]
                ids = [value.concept_id for value in accepted[:5]]
                return [
                    TaxonomyProposal(ids[0], "broader", ids[1]),
                    TaxonomyProposal(ids[1], "related", ids[2]),
                    TaxonomyProposal(ids[2], "close_match", ids[3]),
                    TaxonomyProposal(ids[3], "related", ids[4]),
                ]

        class StructuralVerifier:
            def __init__(self) -> None:
                self.calls = 0

            def verify(self, proposal, concepts):  # noqa: ANN001, ANN201
                del proposal, concepts
                self.calls += 1
                return TaxonomyJudgment(
                    True, 0.70 if self.calls == 4 else 0.95,
                    rationale="Synthetic structural support.",
                )

        proposer, verifier = StructuralProposer(), StructuralVerifier()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary)
            result = self.run_build(
                remote, model, out,
                taxonomy_proposer=proposer, taxonomy_verifier=verifier,
                limits=BuildLimits(
                    maximum_candidates=10_000, maximum_concepts=5_000
                ),
            )
            manifest_path = Path(result["local_manifest_path"])
            manifest_size = manifest_path.stat().st_size
            local_files = [path for path in out.rglob("*") if path.is_file()]
        self.assertEqual(
            (result["selected_rows"], result["candidates"], result["concepts"], result["mentions"]),
            (500, 3000, 2900, 3000),
        )
        self.assertEqual(
            (model.maximum_concurrent, result["maximum_model_concurrency"]),
            (1, 1),
        )
        self.assertEqual(result["model_calls"], model.calls + proposer.call_count + verifier.calls)
        self.assertLessEqual(manifest_size, 256 * 1024)
        self.assertEqual([path.name for path in local_files if path.suffix == ".json"], ["build.json"])

        concept_namespace = next(
            value for name, value in remote.data.items()
            if name.startswith("buoy-semantics-concepts-")
        )
        mention_namespace = next(
            value for name, value in remote.data.items()
            if name.startswith("buoy-semantics-mentions-")
        )
        taxonomy_namespace = next(
            value for name, value in remote.data.items()
            if name.startswith("buoy-semantics-taxonomy-")
        )
        concepts = list(concept_namespace["rows"].values())
        mentions = list(mention_namespace["rows"].values())
        taxonomy = list(taxonomy_namespace["rows"].values())
        self.assertTrue(any(row["aliases"] for row in concepts))
        self.assertTrue(any(row["status"] == "accepted" for row in concepts))
        self.assertTrue(any(row["status"] == "provisional" for row in concepts))
        self.assertEqual(
            {row["predicate"] for row in taxonomy},
            {"broader", "related", "close_match"},
        )
        self.assertTrue(any(row["status"] == "accepted" for row in taxonomy))
        self.assertTrue(any(row["status"] == "provisional" for row in taxonomy))

        active_ledger = {
            row["id"]: row
            for row in remote.data["evidence-ledger-test"]["rows"].values()
            if row["status"] == "active"
        }
        concept_ids = {row["id"] for row in concepts}
        for mention in mentions:
            ledger = active_ledger[mention["evidence_row_id"]]
            self.assertIn(mention["concept_id"], concept_ids)
            self.assertEqual(mention["source_row_id"], ledger["source_row_id"])
            self.assertEqual(mention["chunk_hash"], ledger["chunk_hash"])

        accepted_broader = [
            row for row in taxonomy
            if row["predicate"] == "broader" and row["status"] == "accepted"
        ]
        parents: dict[str, set[str]] = {}
        for edge in accepted_broader:
            parents.setdefault(edge["subject_id"], set()).add(edge["object_id"])
        self.assertTrue(all(len(values) <= 3 for values in parents.values()))

        def depth(node, trail=frozenset()):  # noqa: ANN001, ANN202
            self.assertNotIn(node, trail)
            values = parents.get(node, set())
            return 0 if not values else 1 + max(
                depth(parent, trail | {node}) for parent in values
            )

        self.assertLessEqual(max((depth(node) for node in concept_ids), default=0), 12)
        for row in [*concepts, *mentions, *taxonomy]:
            self.assertEqual(row["semantic_hash"], _persisted_row_hash(row))
        expected_logical = _semantic_logical_hash(concepts, mentions, taxonomy)
        catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][result["build_id"]]
        self.assertEqual(result["semantic_logical_hash"], expected_logical)
        self.assertEqual(catalog["semantic_logical_hash"], expected_logical)

        semantic_writes = [
            kwargs for name, kwargs in remote.write_calls
            if name.startswith("buoy-semantics-") and kwargs.get("upsert_rows")
        ]
        self.assertEqual(result["remote_write_calls"], len(semantic_writes))
        self.assertTrue(all(len(kwargs["upsert_rows"]) <= 500 for kwargs in semantic_writes))
        self.assertTrue(all(
            len(json.dumps(kwargs, separators=(",", ":")).encode()) <= 16 * 1024 * 1024
            for kwargs in semantic_writes
        ))
        branch_queries = [
            kwargs for name, kwargs in remote.query_calls
            if name == "evidence-branch-test"
        ]
        self.assertEqual(len(branch_queries), 500)
        self.assertTrue(all(
            kwargs["include_attributes"] == [
                "content", "title", "section_path", "canonical_url", "chunk_hash",
                "page_hash", "doc_kind", "tags",
            ] and kwargs["limit"] == 2
            for kwargs in branch_queries
        ))
        self.assertGreater(result["derived_bytes"], 0)
        self.assertGreater(result["observed_max_rss"], 0)


class SemanticOperationsTests(unittest.TestCase):
    def run_build(self, remote, model, out, **kwargs):  # noqa: ANN001, ANN201
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            return create_semantic_build(
                remote, evidence_snapshot_id="evidence_test", model_client=model,
                model_contract=model_contract(), out_root=out, **kwargs,
            )

    def completed(self, row_count=3):  # noqa: ANN201
        remote = FakeRemote(row_count)
        model = FakeModel()
        temporary = tempfile.TemporaryDirectory()
        out = Path(temporary.name)
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            built = create_semantic_build(
                remote, evidence_snapshot_id="evidence_test", model_client=model,
                model_contract=model_contract(), out_root=out,
            )
        return remote, model, out, temporary, built

    def rehash_completed(self, remote, built):  # noqa: ANN001
        catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
        concepts = list(remote.data[str(catalog["concepts_namespace"])]["rows"].values())
        mentions = list(remote.data[str(catalog["mentions_namespace"])]["rows"].values())
        taxonomy = list(remote.data[str(catalog["taxonomy_namespace"])]["rows"].values())
        for value in [*concepts, *mentions, *taxonomy]:
            value["semantic_hash"] = _persisted_row_hash(value)
        catalog["concept_count"] = len(concepts)
        catalog["mention_count"] = len(mentions)
        catalog["taxonomy_count"] = len(taxonomy)
        catalog["accepted_concept_count"] = sum(value["status"] == "accepted" for value in concepts)
        catalog["provisional_concept_count"] = sum(value["status"] == "provisional" for value in concepts)
        catalog["semantic_logical_hash"] = _semantic_logical_hash(concepts, mentions, taxonomy)
        catalog["manifest_hash"] = _catalog_manifest(catalog)["manifest_hash"]

    def verify_with_fakes(self, remote, built, **kwargs):  # noqa: ANN001, ANN201
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            return verify_semantic_build(remote, build_id=built["build_id"], **kwargs)

    def test_estimate_is_sampled_read_only_and_writes_no_artifact(self) -> None:
        remote = FakeRemote(25)
        model = FakeModel()
        with tempfile.TemporaryDirectory() as directory, patch(
            "buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}
        ), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            result = estimate_semantic_build(
                remote, evidence_snapshot_id="evidence_test", model_client=model,
                sample_rows=20,
            )
            self.assertEqual(result["sampled_rows"], 20)
            self.assertEqual(result["total_active_rows"], 25)
            self.assertEqual(result["sample_model_calls"], 20)
            self.assertFalse(result["remote_writes_occurred"])
            self.assertFalse(result["local_artifacts_written"])
            self.assertEqual(remote.write_calls, [])
            self.assertEqual(list(Path(directory).iterdir()), [])
            self.assertEqual(result["token_estimate_method"], "conservative_utf8_bytes_divided_by_3")
            self.assertEqual(
                result["estimated_taxonomy_relation_count_range"][1],
                result["estimated_candidate_count"] * 3,
            )
            self.assertIn("derived_utf8_bytes", result["limit_results"])
            self.assertEqual(
                result["would_pass_limits"],
                all(value["passes"] for value in result["limit_results"].values()),
            )

    def test_estimate_counts_prior_probe_and_stops_at_model_call_limit(self) -> None:
        remote, model = FakeRemote(1), FakeModel()
        limits = BuildLimits(maximum_model_calls=1)
        with patch(
            "buoy_search.semantics_remote.verify_evidence_snapshot",
            return_value={"verified": True},
        ), patch(
            "buoy_search.semantics_remote._read_catalog_row",
            return_value=evidence_catalog_row(),
        ):
            result = estimate_semantic_build(
                remote,
                evidence_snapshot_id="evidence_test",
                model_client=model,
                limits=limits,
                sample_rows=1,
                prior_model_calls=1,
            )
        self.assertEqual(model.calls, 0)
        self.assertEqual(result["sample_model_calls"], 0)
        self.assertEqual(result["model_call_count"], 1)
        self.assertGreater(result["evidence_utf8_bytes"], 0)
        self.assertGreater(result["estimated_model_calls"], 1)
        self.assertFalse(result["limit_results"]["model_calls"]["passes"])
        self.assertFalse(result["would_pass_limits"])

    def test_estimate_reports_each_failed_limit_without_clipping(self) -> None:
        remote, model = FakeRemote(25), FakeModel()
        limits = BuildLimits(
            maximum_rows=1, maximum_evidence_bytes=1,
            maximum_model_calls=1, maximum_candidates=1, maximum_concepts=1,
            maximum_taxonomy_rows=1, maximum_derived_bytes=1,
            maximum_wall_seconds=1,
        )
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            result = estimate_semantic_build(
                remote, evidence_snapshot_id="evidence_test", model_client=model,
                limits=limits, sample_rows=1,
            )
        self.assertFalse(result["would_pass_limits"])
        self.assertGreater(result["estimated_taxonomy_relation_count_range"][1], 1)
        self.assertGreater(result["estimated_derived_utf8_bytes"], 1)
        self.assertFalse(result["limit_results"]["evidence_rows"]["passes"])

    def test_verify_full_remote_state_is_model_inert_and_detects_corruption(self) -> None:
        remote, model, out, temporary, built = self.completed()
        self.addCleanup(temporary.cleanup)
        manifest = out / built["build_id"] / "build.json"
        before_calls = model.calls
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()):
            result = verify_semantic_build(remote, build_id=built["build_id"], manifest_path=manifest)
        self.assertTrue(result["verified"])
        self.assertEqual(model.calls, before_calls)
        self.assertFalse(result["turbopuffer_writes_occurred"])
        concept_ns = next(name for name in remote.data if name.startswith("buoy-semantics-concepts-"))
        concept = next(iter(remote.data[concept_ns]["rows"].values()))
        concept["definition"] = "altered"
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()), self.assertRaisesRegex(SemanticBuildError, "hash"):
            verify_semantic_build(remote, build_id=built["build_id"])

    def test_verify_rejects_missing_concept_and_inactive_evidence_reference(self) -> None:
        remote, _model, _out, temporary, built = self.completed()
        self.addCleanup(temporary.cleanup)
        mention_ns = next(name for name in remote.data if name.startswith("buoy-semantics-mentions-"))
        mention = next(iter(remote.data[mention_ns]["rows"].values()))
        mention["concept_id"] = "concept_missing"
        mention["semantic_hash"] = _persisted_row_hash(mention)
        catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
        concepts_ns = str(catalog["concepts_namespace"])
        taxonomy_ns = str(catalog["taxonomy_namespace"])
        catalog["semantic_logical_hash"] = _semantic_logical_hash(
            list(remote.data[concepts_ns]["rows"].values()),
            list(remote.data[mention_ns]["rows"].values()),
            list(remote.data[taxonomy_ns]["rows"].values()),
        )
        with patch("buoy_search.semantics_remote.verify_evidence_snapshot", return_value={"verified": True}), patch("buoy_search.semantics_remote._read_catalog_row", return_value=evidence_catalog_row()), self.assertRaisesRegex(SemanticBuildError, "missing concept"):
            verify_semantic_build(remote, build_id=built["build_id"])

    def test_model_contract_is_reprobed_and_drift_blocks_catalog(self) -> None:
        remote, model = FakeRemote(1), FakeModel()
        model.drift_contract = ModelContract(
            **{**model_contract().to_dict(), "model_revision": "sha256:" + "b" * 64}
        )
        with tempfile.TemporaryDirectory() as temporary, self.assertRaisesRegex(
            SemanticBuildError, "contract drifted"
        ):
            self.run_build(remote, model, Path(temporary))
        self.assertEqual(model.doctor_calls, 1)
        self.assertFalse(remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False))

    def test_incomplete_final_namespaces_are_reported_and_not_deleted(self) -> None:
        remote, model = FakeRemote(1), FakeModel()
        original = FakeNamespace.write

        def fail_mentions(namespace, **kwargs):  # noqa: ANN001, ANN202
            if namespace.name.startswith("buoy-semantics-mentions-"):
                raise RuntimeError("injected failure")
            return original(namespace, **kwargs)

        with tempfile.TemporaryDirectory() as temporary, patch.object(
            FakeNamespace, "write", fail_mentions
        ), self.assertRaises(SemanticBuildError) as caught:
            self.run_build(remote, model, Path(temporary))
        self.assertTrue(any("concepts" in value for value in caught.exception.incomplete_namespaces))
        self.assertTrue(any("extractions" in value for value in caught.exception.incomplete_namespaces))
        self.assertFalse(remote.data.get("buoy-semantics-catalog-v1", {}).get("exists", False))

    def test_verify_recomputed_hash_rejects_identity_basis_status_and_contract_corruption(self) -> None:
        cases = (
            ("concept identity", "concept", lambda row, _catalog: row.__setitem__("build_id", "semantics_wrong"), "identity"),
            ("mention snapshot", "mention", lambda row, _catalog: row.__setitem__("evidence_snapshot_id", "evidence_wrong"), "identity"),
            ("mention chunk", "mention", lambda row, _catalog: row.__setitem__("chunk_hash", "wrong"), "provenance"),
            ("mention status", "mention", lambda row, _catalog: row.__setitem__("status", "accepted" if row["status"] == "provisional" else "provisional"), "status"),
            ("mention model", "mention", lambda row, _catalog: row.__setitem__("model_contract_hash", "wrong"), "model"),
            ("taxonomy basis", "taxonomy", lambda row, _catalog: row.__setitem__("basis", "uses"), "basis"),
        )
        for label, kind, mutate, message in cases:
            with self.subTest(label=label):
                remote, _model, _out, temporary, built = self.completed(3)
                self.addCleanup(temporary.cleanup)
                catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
                namespace = str(catalog[{"concept": "concepts_namespace", "mention": "mentions_namespace", "taxonomy": "taxonomy_namespace"}[kind]])
                row = next(iter(remote.data[namespace]["rows"].values()))
                mutate(row, catalog)
                self.rehash_completed(remote, built)
                with self.assertRaisesRegex(SemanticBuildError, message):
                    self.verify_with_fakes(remote, built)

    def test_verify_rejects_catalog_identity_count_and_semantic_hash_mismatch(self) -> None:
        for field, value, message in (
            ("build_id", "semantics_wrong", "identity"),
            ("concept_count", 999, "count"),
            ("semantic_logical_hash", "wrong", "logical hash"),
        ):
            with self.subTest(field=field):
                remote, _model, _out, temporary, built = self.completed(2)
                self.addCleanup(temporary.cleanup)
                catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
                catalog[field] = value
                if field != "build_id":
                    catalog["manifest_hash"] = _catalog_manifest(catalog)["manifest_hash"]
                with self.assertRaisesRegex(SemanticBuildError, message):
                    self.verify_with_fakes(remote, built)

    def test_verify_rejects_inactive_evidence_and_manifest_mismatch_without_model_or_write(self) -> None:
        remote, model, out, temporary, built = self.completed(2)
        self.addCleanup(temporary.cleanup)
        mention_ns = next(name for name in remote.data if name.startswith("buoy-semantics-mentions-"))
        mention = next(iter(remote.data[mention_ns]["rows"].values()))
        ledger = remote.data["evidence-ledger-test"]["rows"][mention["evidence_row_id"]]
        ledger["status"] = "deleted"
        before_calls, before_writes = model.calls, len(remote.write_calls)
        with self.assertRaisesRegex(SemanticBuildError, "active evidence"):
            self.verify_with_fakes(remote, built)
        self.assertEqual((model.calls, len(remote.write_calls)), (before_calls, before_writes))
        ledger["status"] = "active"
        manifest = out / built["build_id"] / "build.json"
        payload = json.loads(manifest.read_text())
        payload["coverage"] = "changed"
        manifest.write_text(json.dumps(payload))
        with self.assertRaisesRegex(SemanticBuildError, "manifest"):
            self.verify_with_fakes(remote, built, manifest_path=manifest)

    def test_verify_rejects_unknown_and_unrelated_taxonomy_representatives(self) -> None:
        for mode in ("unknown", "unrelated"):
            with self.subTest(mode=mode):
                remote, _model, _out, temporary, built = self.completed(3)
                self.addCleanup(temporary.cleanup)
                catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
                taxonomy = list(
                    remote.data[str(catalog["taxonomy_namespace"])]["rows"].values()
                )
                self.assertTrue(taxonomy)
                edge = taxonomy[0]
                if mode == "unknown":
                    edge["representative_mention_ids"] = ["mention_missing"]
                else:
                    mentions = list(
                        remote.data[str(catalog["mentions_namespace"])]["rows"].values()
                    )
                    unrelated = next(
                        value for value in mentions
                        if value["concept_id"]
                        not in {edge["subject_id"], edge["object_id"]}
                    )
                    edge["representative_mention_ids"] = [unrelated["id"]]
                self.rehash_completed(remote, built)
                with self.assertRaisesRegex(
                    SemanticBuildError, "representative mention"
                ):
                    self.verify_with_fakes(remote, built)

    def test_verify_rejects_accepted_taxonomy_cycle_with_recomputed_hashes(self) -> None:
        remote, _model, _out, temporary, built = self.completed(3)
        self.addCleanup(temporary.cleanup)
        catalog = remote.data["buoy-semantics-catalog-v1"]["rows"][built["build_id"]]
        concepts = list(remote.data[str(catalog["concepts_namespace"])]["rows"].values())
        mentions = list(remote.data[str(catalog["mentions_namespace"])]["rows"].values())
        for concept in concepts[:2]:
            concept["status"] = "accepted"
        accepted_ids = {value["id"] for value in concepts[:2]}
        for mention in mentions:
            if mention["concept_id"] in accepted_ids:
                mention["status"] = "accepted"
        taxonomy_rows = remote.data[str(catalog["taxonomy_namespace"])]["rows"]
        taxonomy_rows.clear()
        for index, (left, right) in enumerate(((concepts[0]["id"], concepts[1]["id"]), (concepts[1]["id"], concepts[0]["id"]))):
            value = {
                "id": f"taxonomy_cycle_{index}", "build_id": built["build_id"],
                "evidence_snapshot_id": "evidence_test", "subject_id": left,
                "predicate": "broader", "object_id": right, "status": "accepted",
                "policy_version": "semantic-taxonomy-structure-v1", "policy_score": 0.95,
                "policy_breakdown_json": "{}", "basis": "semantic_induction",
                "representative_mention_ids": [], "rationale": "Synthetic.",
                "created_at": concepts[0]["created_at"], "semantic_hash": "pending",
            }
            taxonomy_rows[value["id"]] = value
        self.rehash_completed(remote, built)
        with self.assertRaisesRegex(SemanticBuildError, "cycle"):
            self.verify_with_fakes(remote, built)

    def test_inspect_is_bounded_filtered_safe_and_model_inert(self) -> None:
        remote, model, _out, temporary, built = self.completed(5)
        self.addCleanup(temporary.cleanup)
        before_writes = len(remote.write_calls); before_calls = model.calls
        concepts = inspect_semantic_build(
            remote, build_id=built["build_id"], kind="concepts",
            status="accepted", limit=2,
        )
        self.assertLessEqual(len(concepts["items"]), 2)
        self.assertTrue(all(value["status"] == "accepted" for value in concepts["items"]))
        self.assertFalse(any("content" in value for value in concepts["items"]))
        mentions = inspect_semantic_build(
            remote, build_id=built["build_id"], kind="mentions", limit=2,
        )
        self.assertLessEqual(len(mentions["items"]), 2)
        self.assertTrue(all("content" not in value and len(value["excerpt"]) <= 600 for value in mentions["items"]))
        taxonomy = inspect_semantic_build(
            remote, build_id=built["build_id"], kind="taxonomy", limit=2,
        )
        self.assertLessEqual(len(taxonomy["items"]), 2)
        self.assertTrue(all("content" not in value for value in taxonomy["items"]))
        summary = inspect_semantic_build(remote, build_id=built["build_id"], kind="summary", limit=1)
        self.assertIsInstance(summary["items"], dict)
        self.assertEqual((len(remote.write_calls), model.calls), (before_writes, before_calls))
        with self.assertRaisesRegex(SemanticBuildError, "between 1 and 100"):
            inspect_semantic_build(remote, build_id=built["build_id"], kind="mentions", limit=101)


if __name__ == "__main__":
    unittest.main()
