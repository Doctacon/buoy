from __future__ import annotations

import copy
from contextlib import contextmanager
from dataclasses import replace
import hashlib
import inspect
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest import mock

from buoy_search.applied_state import (
    APPLIED_STATE_SCHEMA_VERSION,
    AppliedState,
    AppliedStateRow,
)
from buoy_search.apply import VerifiedApplyPlan
from buoy_search.catalog import (
    CardFields,
    ROUTING_DIMENSIONS,
    prepare_card,
    prepare_prospective_card,
)
import buoy_search.experimental_baseline as experimental_baseline
from buoy_search.experimental_baseline import (
    APPROVAL_A_GRANTED_PROVENANCE,
    APPROVAL_A_GRANTED_RECORD_SHA256,
    APPROVAL_A_TEXT,
    APPROVAL_A_TEXT_SHA256,
    ARTIFACT_HASH,
    CACHE_MANIFEST_HASH,
    CONTENT_ROWS,
    CONTENT_SCHEMA,
    MODEL,
    MODEL_PRECISION,
    MODEL_REVISION,
    PLAN_ID,
    README_HASH,
    REGION,
    SDK_VERSION,
    SOURCE_COMMIT,
    SOURCE_REPOSITORY,
    TARGET_NAMESPACE,
    CacheAttestation,
    DefinitiveProviderError,
    ExperimentalBaselineError,
    LocalEffects,
    PreparedBaseline,
    ProviderResources,
    simulate_experimental_baseline,
    validate_approval_a_record,
)
from buoy_search.plan_artifacts import (
    ChunkManifestRecord,
    ManifestDocument,
    build_generic_site_row,
)
from buoy_search.plan_diff import DesiredChunkDiffRecord, IncrementalPlanDiff
from buoy_search.remote_catalog import (
    DISTANCE_METRIC,
    REMOTE_CATALOG_SCHEMA,
    card_to_remote_row,
    remote_card_id,
)

UNIT_VECTOR = [1.0] + [0.0] * (ROUTING_DIMENSIONS - 1)
ALT_UNIT_VECTOR = [0.0, 1.0] + [0.0] * (ROUTING_DIMENSIONS - 2)
NOW = "2026-07-20T12:00:00+00:00"
APPLY_ID = "apply_20260720T120000Z_plan_b6c5d128295f442f"
SITE_ID = "github-doctacon-buoy-search"
BASE_URL = "https://github.com/Doctacon/buoy-search"
APPROVAL_RECORD_PATH = (
    Path(__file__).resolve().parents[1]
    / ".10x/evidence/.storage/2026-07-20-experimental-buoy-baseline-approval-a.json"
)
APPROVAL_RECORD_SHA256 = "46a44e9440425ef73c66e69d64d7e83a7c098ce0fa3f85f2caf7f8d7685cc5ec"
APPROVAL_PROVENANCE = {
    "source_system": "pi",
    "conversation_id": "runtime-id-not-exposed",
    "message_id": "sha256:4b066f19c3331b0074d4548b691b293072a50406df6f0557fcdba8e3d3f25d74",
}


def cache_attestation() -> CacheAttestation:
    return CacheAttestation(
        revision=MODEL_REVISION,
        manifest_sha256=CACHE_MANIFEST_HASH,
        readme_sha256=README_HASH,
        license="mit",
        license_statement_present=True,
        file_count=12,
    )


def make_verified() -> VerifiedApplyPlan:
    chunks: list[ChunkManifestRecord] = []
    records: list[DesiredChunkDiffRecord] = []
    for index in range(CONTENT_ROWS):
        row_id = f"ts_{index:032x}"
        chunk = ChunkManifestRecord(
            row_id=row_id,
            row_id_candidate=row_id,
            site_id=SITE_ID,
            duplicate_ordinal=0,
            canonical_url=f"https://github.com/Doctacon/buoy-search/blob/{SOURCE_COMMIT}/src/{index:04d}.py",
            page_content_path=f"src/{index:04d}.py.md",
            page_hash=f"page-{index}",
            chunk_hash=f"chunk-{index}",
            embedding_text_hash=f"embedding-{index}",
            title=f"File {index}",
            section_path="module",
            chunk_index=0,
            content=f"content {index}",
            content_preview=f"content {index}",
            doc_kind="repo_code",
            tags=["python"],
            source_metadata={
                "source_kind": "github_repo",
                "repo_full_name": SOURCE_REPOSITORY,
                "repo_owner": "Doctacon",
                "repo_name": "buoy-search",
                "repo_ref": "develop",
                "commit_sha": SOURCE_COMMIT,
                "repo_path": f"src/{index:04d}.py",
                "language": "Python",
            },
        )
        chunks.append(chunk)
        records.append(
            DesiredChunkDiffRecord(
                row_id=row_id,
                canonical_url=chunk.canonical_url,
                page_hash=chunk.page_hash,
                chunk_hash=chunk.chunk_hash,
                embedding_text_hash=chunk.embedding_text_hash,
                section_path=chunk.section_path,
                chunk_index=chunk.chunk_index,
                action="new",
            )
        )
    manifest = ManifestDocument(
        schema_version=1,
        site_id=SITE_ID,
        base_url=BASE_URL,
        namespace=TARGET_NAMESPACE,
        namespace_candidate=TARGET_NAMESPACE,
        pages=[],
        chunks=chunks,
    )
    state = AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=SITE_ID,
        namespace=TARGET_NAMESPACE,
        base_url=BASE_URL,
        updated_at="",
        last_plan_id="",
        last_apply_id="",
        rows=[],
        first_apply=True,
    )
    diff = IncrementalPlanDiff(
        first_apply=True,
        pages_added=64,
        pages_changed=0,
        pages_unchanged=0,
        pages_removed=0,
        chunks_unchanged=0,
        chunks_to_embed=CONTENT_ROWS,
        rows_to_upsert=CONTENT_ROWS,
        stale_rows=0,
        retained_stale_rows=0,
        chunks_to_embed_records=records,
        rows_to_upsert_records=records,
    )
    return VerifiedApplyPlan(
        plan_path=Path("/not-retained/plan.json"),
        plan={
            "plan_id": PLAN_ID,
            "artifact_hash": ARTIFACT_HASH,
            "namespace": TARGET_NAMESPACE,
            "embedding_model": MODEL,
            "embedding_precision": MODEL_PRECISION,
        },
        manifest=manifest,
        chunks_by_row_id={chunk.row_id: chunk for chunk in chunks},
        state=state,
        diff=diff,
        state_root=Path("/not-retained/state"),
    )


def make_prepared(verified: VerifiedApplyPlan) -> PreparedBaseline:
    state_rows = [
        AppliedStateRow(
            row_id=chunk.row_id,
            canonical_url=chunk.canonical_url,
            page_hash=chunk.page_hash,
            chunk_hash=chunk.chunk_hash,
            embedding_text_hash=chunk.embedding_text_hash,
            plan_id=PLAN_ID,
            applied_at=NOW,
            status="active",
        )
        for chunk in verified.manifest.chunks
    ]
    next_state = AppliedState(
        schema_version=APPLIED_STATE_SCHEMA_VERSION,
        site_id=SITE_ID,
        namespace=TARGET_NAMESPACE,
        base_url=BASE_URL,
        updated_at=NOW,
        last_plan_id=PLAN_ID,
        last_apply_id=APPLY_ID,
        rows=sorted(state_rows, key=lambda row: row.row_id),
        first_apply=False,
    )
    rows = tuple(
        build_generic_site_row(chunk, UNIT_VECTOR, plan_id=PLAN_ID, applied_at=NOW)
        for chunk in verified.manifest.chunks
    )
    common = dict(
        namespace=TARGET_NAMESPACE,
        enabled=True,
        source_kind="github_repo",
        source_uri=BASE_URL,
        site_id=SITE_ID,
        title=SOURCE_REPOSITORY,
        summary=f"Public GitHub repository {SOURCE_REPOSITORY} indexed from {BASE_URL}.",
        aliases=["buoy-search"],
        tags=["github", "repository"],
        semantic_origin="generated",
        region=REGION,
        embedding_model=MODEL,
        embedding_precision=MODEL_PRECISION,
        plan_schema_version=1,
        ranking_mode="file",
        ranking_profile="repo_code",
        ranking_pool=100,
        ranking_aggregation="adaptive_sum_3",
        last_plan_id=PLAN_ID,
    )
    embedder = SimpleNamespace(encode=lambda _texts: [list(UNIT_VECTOR)])
    prospective = prepare_prospective_card(
        CardFields(**common, last_apply_id=None), embedder=embedder, now=NOW
    )
    card = prepare_card(
        CardFields(**common, last_apply_id=APPLY_ID),
        existing=prospective,
        embedder=embedder,
        now=NOW,
    )
    return PreparedBaseline(
        rows=rows,
        card=card,
        prospective_card=prospective,
        next_state=next_state,
        model=MODEL,
        model_revision=MODEL_REVISION,
        precision=MODEL_PRECISION,
        dimensions=ROUTING_DIMENSIONS,
        normalized=True,
        pooling="cls",
    )


def catalog_metadata() -> dict[str, object]:
    return {
        "schema": {
            "id": {"type": "string", "filterable": True},
            **copy.deepcopy(REMOTE_CATALOG_SCHEMA),
        },
        "distance_metric": DISTANCE_METRIC,
        "billing": {"logical_bytes": 1},
        "request_id": "catalog-metadata-request",
    }


class InterceptResource:
    def __init__(self, resource: object, harness: "Harness") -> None:
        self.resource = resource
        self.harness = harness

    def _call(self, method: str, kwargs: dict[str, object]) -> object:
        self.harness.attempt_count += 1
        slot = self.harness.attempt_count
        if self.harness.fail_attempt == slot:
            raise self.harness.failure or DefinitiveProviderError("fake definitive failure")
        result = getattr(self.resource, method)(**kwargs)
        if self.harness.transform_attempt == slot and self.harness.transform is not None:
            result = self.harness.transform(result)
        return result

    def metadata(self, **kwargs: object) -> object:
        return self._call("metadata", kwargs)

    def query(self, **kwargs: object) -> object:
        return self._call("query", kwargs)

    def write(self, **kwargs: object) -> object:
        return self._call("write", kwargs)


class FakeTarget:
    def __init__(self, prepared: PreparedBaseline, events: list[str], *, absent: bool) -> None:
        self.prepared = prepared
        self.events = events
        self.absent = absent
        self.written: list[dict[str, object]] = []
        self.write_calls = 0
        self.write_sizes: list[int] = []
        self.metadata_calls = 0
        self.query_calls = 0
        self.verification_reads = 0
        self.fail_write: int | None = None
        self.missing_rows_affected: int | None = None
        self.mismatched_verify = False
        self.quantized_vectors = False
        self.unstable_verify = False
        self.incompatible_metadata = False
        self.ambiguous_absence = False

    def metadata(self, **kwargs: object) -> object:
        self.events.append("target-metadata")
        self.metadata_calls += 1
        if self.absent and self.metadata_calls == 1:
            if self.ambiguous_absence:
                return response(namespace_absent=True, schema=copy.deepcopy(CONTENT_SCHEMA))
            return response(namespace_absent=True)
        schema = copy.deepcopy(CONTENT_SCHEMA)
        if self.incompatible_metadata:
            schema["vector"] = {"type": "[3]f32", "ann": True}
        return response(
            schema={
                "id": {"type": "string", "filterable": True},
                **schema,
            },
            distance_metric=DISTANCE_METRIC,
        )

    def query(self, **kwargs: object) -> object:
        self.events.append(f"target-query-{kwargs['top_k']}")
        self.query_calls += 1
        if kwargs["top_k"] == 1:
            return response(rows=[])
        self.verification_reads += 1
        rows = copy.deepcopy(self.written)
        if self.quantized_vectors:
            for row in rows:
                row["vector"] = list(ALT_UNIT_VECTOR)
        if self.unstable_verify and self.verification_reads == 2:
            rows[0]["vector"] = list(UNIT_VECTOR)
        if self.mismatched_verify:
            rows = rows[:-1]
        return response(rows=rows)

    def write(self, **kwargs: object) -> object:
        self.write_calls += 1
        self.events.append(f"content-write-{self.write_calls}")
        rows = copy.deepcopy(list(kwargs["upsert_rows"]))
        self.write_sizes.append(len(rows))
        if self.fail_write == self.write_calls:
            raise TimeoutError("secret provider timeout detail")
        self.written.extend(rows)
        payload = response(
            rows_affected=len(rows),
            upserted_ids=[row["id"] for row in rows],
        )
        if self.missing_rows_affected == self.write_calls:
            payload.pop("rows_affected")
        return payload


class FakeCatalog:
    def __init__(self, prepared: PreparedBaseline, events: list[str]) -> None:
        self.prepared = prepared
        self.events = events
        self.card_row: dict[str, object] | None = None
        self.write_calls = 0
        self.incompatible_metadata = False
        self.missing_rows_affected = False
        self.mismatched_verify = False
        self.unstable_preflight = False
        self.duplicate_rows = False
        self.query_calls = 0

    def metadata(self, **kwargs: object) -> object:
        self.events.append("catalog-metadata")
        payload = catalog_metadata()
        if self.incompatible_metadata:
            payload["schema"] = {"id": {"type": "string", "filterable": True}}
        return payload

    def query(self, **kwargs: object) -> object:
        self.query_calls += 1
        self.events.append("catalog-query")
        rows: list[dict[str, object]] = []
        if self.card_row is not None:
            rows = [copy.deepcopy(self.card_row)]
        if self.unstable_preflight and self.query_calls == 2:
            rows = [card_to_remote_row(self.prepared.card)]
        if self.mismatched_verify and self.write_calls and rows:
            rows[0]["title"] = "mismatch"
        if self.duplicate_rows and rows:
            rows.append(copy.deepcopy(rows[0]))
        return response(rows=rows)

    def write(self, **kwargs: object) -> object:
        self.write_calls += 1
        self.events.append("card-write")
        self.card_row = copy.deepcopy(list(kwargs["upsert_rows"])[0])
        payload = response(
            rows_affected=1,
            upserted_ids=[remote_card_id(TARGET_NAMESPACE)],
        )
        if self.missing_rows_affected:
            payload.pop("rows_affected")
        return payload


def changed_response(value: object, **changes: object) -> object:
    if not isinstance(value, dict):
        return value
    payload = copy.deepcopy(value)
    payload.update(changes)
    return payload


def response(**values: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "rows": [],
        "billing": {
            "logical_bytes": 123,
            "secret_token": "tpuf_SHOULD_NOT_PERSIST",
            "opaque": "also-not-persisted",
        },
        "request_id": "provider-request-identity",
    }
    payload.update(values)
    return payload


class Harness:
    def __init__(self, *, absent: bool = True) -> None:
        self.verified = make_verified()
        self.prepared = make_prepared(self.verified)
        self.events: list[str] = []
        self.target = FakeTarget(self.prepared, self.events, absent=absent)
        self.catalog = FakeCatalog(self.prepared, self.events)
        self.pending = False
        self.committed = False
        self.removed = False
        self.fail_remove = False
        self.fail_create_after_effect = False
        self.fail_commit_after_effect = False
        self.attempt_count = 0
        self.fail_attempt: int | None = None
        self.failure: BaseException | None = None
        self.transform_attempt: int | None = None
        self.transform = None

    def prepare(self, verified: VerifiedApplyPlan) -> PreparedBaseline:
        self.events.append("prepare-model")
        self.assert_offline()
        self.assert_same(verified, self.verified)
        return self.prepared

    def provider(self) -> ProviderResources:
        return ProviderResources(
            target=InterceptResource(self.target, self),
            catalog=InterceptResource(self.catalog, self),
        )

    def effects(self) -> LocalEffects:
        def create(_prepared: PreparedBaseline, _existing: object) -> None:
            self.events.append("create-pending")
            self.pending = True
            if self.fail_create_after_effect:
                raise OSError("fake partial pending creation")

        def commit(_prepared: PreparedBaseline) -> None:
            self.events.append("commit-state")
            self.committed = True
            if self.fail_commit_after_effect:
                raise OSError("fake partial state commit")

        def remove() -> None:
            self.events.append("remove-pending")
            if self.fail_remove:
                raise OSError("fake pending removal failure")
            self.removed = True
            self.pending = False

        @contextmanager
        def lock():
            self.events.append("acquire-lock")
            try:
                yield
            finally:
                self.events.append("release-lock")

        def validate(verified: VerifiedApplyPlan) -> None:
            self.events.append("validate-local-preconditions")
            self.assert_same(verified, self.verified)

        return LocalEffects(
            lock=lock,
            validate_preconditions=validate,
            create_pending=create,
            commit_state=commit,
            remove_pending=remove,
            pending_exists=lambda: self.pending,
            state_matches=lambda _prepared: self.committed,
        )

    def execute(self) -> dict[str, object]:
        return simulate_experimental_baseline(
            self.verified,
            cache_attestation=cache_attestation(),
            prepare=self.prepare,
            provider=self.provider(),
            local_effects=self.effects(),
        )

    def assert_offline(self) -> None:
        import os
        assert os.environ.get("HF_HUB_OFFLINE") == "1"
        assert os.environ.get("TRANSFORMERS_OFFLINE") == "1"

    @staticmethod
    def assert_same(first: object, second: object) -> None:
        assert first is second


class ExperimentalBaselineTests(unittest.TestCase):
    def test_absent_target_exact_success_uses_fixed_slots_and_order(self) -> None:
        harness = Harness(absent=True)
        result = harness.execute()

        self.assertTrue(result["success"])
        self.assertEqual(result["physical_attempts"], 25)
        self.assertEqual(result["write_row_positions"], 904)
        self.assertEqual(result["returned_row_positions"], 1808)
        self.assertEqual(result["delete_attempts"], 0)
        self.assertEqual(result["slots"][1]["status"], "unused")
        self.assertEqual(harness.target.write_calls, 15)
        self.assertEqual(harness.target.write_sizes, [64] * 14 + [7])
        self.assertEqual(len(harness.target.written), CONTENT_ROWS)
        self.assertTrue(result["simulation"])
        self.assertEqual(result["execution_mode"], "simulation")
        self.assertFalse(result["provider_attested"])
        self.assertIsNone(result["max_retries"])
        self.assertLess(harness.events.index("create-pending"), harness.events.index("content-write-1"))
        self.assertLess(harness.events.index("catalog-query"), harness.events.index("create-pending"))
        self.assertLess(harness.events.index("content-write-15"), harness.events.index("card-write"))
        self.assertLess(harness.events.index("card-write"), harness.events.index("commit-state"))
        self.assertLess(harness.events.index("commit-state"), harness.events.index("remove-pending"))
        self.assertTrue(harness.committed)
        self.assertTrue(harness.removed)
        serialized = json.dumps(result)
        self.assertNotIn("tpuf_", serialized)
        self.assertNotIn("provider-request-identity", serialized)
        self.assertIn("<redacted>", serialized)
        attempted = [slot for slot in result["slots"] if slot["status"] != "unused"]
        self.assertTrue(all(slot["billing_present"] for slot in attempted))
        self.assertTrue(all(slot["request_identity_present"] for slot in attempted))

    def test_verified_empty_target_uses_all_26_slots(self) -> None:
        harness = Harness(absent=False)
        result = harness.execute()
        self.assertEqual(result["physical_attempts"], 26)
        self.assertEqual(result["returned_row_positions"], 1808)
        self.assertTrue(all(slot["status"] != "unused" for slot in result["slots"]))

    def test_local_mismatch_aborts_before_model_credential_or_provider(self) -> None:
        harness = Harness()
        harness.verified.plan["artifact_hash"] = "wrong"
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertEqual(harness.events, ["acquire-lock", "release-lock"])
        self.assertFalse(harness.pending)

    def test_cache_mismatch_aborts_before_model_credential_or_provider(self) -> None:
        harness = Harness()
        with self.assertRaises(ExperimentalBaselineError):
            simulate_experimental_baseline(
                harness.verified,
                cache_attestation=replace(cache_attestation(), readme_sha256="wrong"),
                prepare=harness.prepare,
                provider=harness.provider(),
                local_effects=harness.effects(),
            )
        self.assertEqual(
            harness.events,
            ["acquire-lock", "validate-local-preconditions", "release-lock"],
        )

    def test_nonempty_target_aborts_with_zero_writes_and_no_pending(self) -> None:
        harness = Harness(absent=False)
        harness.target.query = lambda **_kwargs: response(rows=[{"id": "existing"}])  # type: ignore[method-assign]
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertEqual(harness.target.write_calls, 0)
        self.assertEqual(harness.catalog.write_calls, 0)
        self.assertFalse(harness.pending)
        self.assertEqual(raised.exception.evidence["write_row_positions"], 0)
        self.assertEqual(raised.exception.evidence["delete_attempts"], 0)

    def test_ambiguous_target_absence_aborts_before_pending_or_write(self) -> None:
        harness = Harness()
        harness.target.ambiguous_absence = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertFalse(harness.pending)
        self.assertEqual(harness.target.write_calls, 0)

    def test_incompatible_target_schema_aborts_before_pending_or_write(self) -> None:
        harness = Harness(absent=False)
        harness.target.incompatible_metadata = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertFalse(harness.pending)
        self.assertEqual(harness.target.write_calls, 0)

    def test_incompatible_catalog_aborts_before_pending_or_write(self) -> None:
        harness = Harness()
        harness.catalog.incompatible_metadata = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertFalse(harness.pending)
        self.assertEqual(harness.target.write_calls, 0)
        self.assertEqual(harness.catalog.write_calls, 0)

    def test_unstable_catalog_preflight_aborts_before_write(self) -> None:
        harness = Harness()
        harness.catalog.unstable_preflight = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertFalse(harness.pending)
        self.assertEqual(harness.target.write_calls, 0)

    def test_missing_content_accounting_fails_closed_and_retains_pending(self) -> None:
        harness = Harness()
        harness.target.missing_rows_affected = 3
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertTrue(harness.pending)
        self.assertFalse(harness.committed)
        self.assertEqual(harness.catalog.write_calls, 0)
        entry = raised.exception.evidence["slots"][7]
        self.assertEqual(entry["status"], "failed")
        self.assertFalse(entry["rows_affected_present"])
        self.assertTrue(entry["billing_present"])
        self.assertTrue(entry["request_identity_present"])
        self.assertEqual(raised.exception.evidence["write_row_positions"], 192)

    def test_timeout_is_indeterminate_without_retry_and_retains_pending(self) -> None:
        harness = Harness()
        harness.target.fail_write = 2
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertEqual(harness.target.write_calls, 2)
        self.assertEqual(raised.exception.evidence["slots"][6]["status"], "indeterminate")
        self.assertNotIn("secret provider timeout detail", json.dumps(raised.exception.evidence))
        self.assertTrue(harness.pending)
        self.assertFalse(harness.committed)

    def test_normalized_provider_quantized_vectors_are_compatible(self) -> None:
        harness = Harness()
        harness.target.quantized_vectors = True
        result = harness.execute()
        self.assertTrue(result["success"])
        self.assertTrue(harness.committed)

    def test_unstable_target_vectors_prevent_card_and_local_commit(self) -> None:
        harness = Harness()
        harness.target.quantized_vectors = True
        harness.target.unstable_verify = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertEqual(harness.catalog.write_calls, 0)
        self.assertFalse(harness.committed)
        self.assertTrue(harness.pending)

    def test_target_verification_mismatch_prevents_card_and_local_commit(self) -> None:
        harness = Harness()
        harness.target.mismatched_verify = True
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertEqual(harness.target.write_calls, 15)
        self.assertEqual(harness.catalog.write_calls, 0)
        self.assertFalse(harness.committed)
        self.assertTrue(harness.pending)

    def test_catalog_write_missing_accounting_prevents_state_and_card_success(self) -> None:
        harness = Harness()
        harness.catalog.missing_rows_affected = True
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertEqual(harness.catalog.write_calls, 1)
        self.assertFalse(harness.committed)
        self.assertTrue(harness.pending)
        self.assertFalse(raised.exception.evidence["card_success"])
        self.assertEqual(raised.exception.evidence["write_row_positions"], 904)

    def test_catalog_verification_mismatch_prevents_state_and_card_success(self) -> None:
        harness = Harness()
        harness.catalog.mismatched_verify = True
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertFalse(harness.committed)
        self.assertTrue(harness.pending)
        self.assertFalse(raised.exception.evidence["card_success"])
        self.assertEqual(raised.exception.evidence["delete_attempts"], 0)

    def test_pending_removal_failure_reports_committed_state_and_retained_pending(self) -> None:
        harness = Harness()
        harness.fail_remove = True
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        self.assertTrue(harness.committed)
        self.assertTrue(harness.pending)
        self.assertTrue(raised.exception.evidence["local_state_committed"])
        self.assertTrue(raised.exception.evidence["remote_card_verified"])
        self.assertTrue(raised.exception.evidence["pending_retained"])

    def test_simulation_cannot_claim_live_sdk_or_zero_retries(self) -> None:
        harness = Harness()
        with self.assertRaises(ExperimentalBaselineError):
            simulate_experimental_baseline(
                harness.verified,
                cache_attestation=cache_attestation(),
                prepare=harness.prepare,
                provider=ProviderResources(
                    target=harness.target,
                    catalog=harness.catalog,
                    sdk_version=SDK_VERSION,
                    max_retries=0,
                ),
                local_effects=harness.effects(),
            )
        self.assertEqual(harness.target.metadata_calls, 0)
        self.assertFalse(harness.pending)

    def test_malformed_vector_aborts_before_credential(self) -> None:
        harness = Harness()
        bad_rows = list(harness.prepared.rows)
        bad_rows[0] = {**bad_rows[0], "vector": [float("nan")] + UNIT_VECTOR[1:]}
        harness.prepared = replace(harness.prepared, rows=tuple(bad_rows))
        harness.target.prepared = harness.prepared
        harness.catalog.prepared = harness.prepared
        with self.assertRaises(ExperimentalBaselineError):
            harness.execute()
        self.assertNotIn("create-pending", harness.events)
        self.assertFalse(harness.pending)

    def test_existing_card_compatible_incompatible_and_duplicate_matrix(self) -> None:
        compatible = Harness(absent=False)
        compatible.catalog.card_row = card_to_remote_row(compatible.prepared.card)
        self.assertTrue(compatible.execute()["success"])

        incompatible = Harness(absent=False)
        incompatible.catalog.card_row = card_to_remote_row(incompatible.prepared.card)
        incompatible.catalog.card_row["title"] = "incompatible"
        with self.assertRaises(ExperimentalBaselineError):
            incompatible.execute()
        self.assertEqual(incompatible.target.write_calls, 0)
        self.assertFalse(incompatible.pending)

        duplicate = Harness(absent=False)
        duplicate.catalog.card_row = card_to_remote_row(duplicate.prepared.card)
        duplicate.catalog.duplicate_rows = True
        with self.assertRaises(ExperimentalBaselineError):
            duplicate.execute()
        self.assertEqual(duplicate.target.write_calls, 0)
        self.assertFalse(duplicate.pending)

    def test_every_one_of_26_slots_fails_without_reassignment_or_retry(self) -> None:
        for slot in range(1, 27):
            with self.subTest(slot=slot):
                harness = Harness(absent=False)
                harness.fail_attempt = slot
                with self.assertRaises(ExperimentalBaselineError) as raised:
                    harness.execute()
                evidence = raised.exception.evidence
                self.assertEqual(evidence["physical_attempts"], slot)
                self.assertEqual(evidence["slots"][slot - 1]["status"], "failed")
                self.assertTrue(
                    all(item["status"] == "unused" for item in evidence["slots"][slot:])
                )
                self.assertEqual(evidence["delete_attempts"], 0)

    def test_malformed_response_and_accounting_matrix(self) -> None:
        cases = [
            (1, lambda _value: []),
            (1, lambda value: changed_response(value, rows=[{"id": "forbidden"}])),
            (1, lambda value: changed_response(value, billing="not-an-object")),
            (1, lambda value: changed_response(value, request_id=None)),
            (2, lambda value: changed_response(value, rows="not-an-array")),
            (2, lambda value: changed_response(value, rows=[{"id": "a"}, {"id": "b"}])),
            (6, lambda value: changed_response(value, rows_affected=True)),
            (6, lambda value: changed_response(value, rows_affected=-1)),
            (6, lambda value: changed_response(value, rows_affected=64.0)),
            (6, lambda value: changed_response(value, rows_affected=63)),
            (6, lambda value: changed_response(value, upserted_ids=None)),
            (6, lambda value: changed_response(value, upserted_ids=["wrong"] * 64)),
            (6, lambda value: changed_response(value, rows=[{"id": "forbidden"}])),
            (24, lambda value: changed_response(value, rows_affected=2)),
            (24, lambda value: changed_response(value, upserted_ids=[])),
        ]
        for slot, transform in cases:
            with self.subTest(slot=slot, transform=transform):
                harness = Harness(absent=False)
                harness.transform_attempt = slot
                harness.transform = transform
                with self.assertRaises(ExperimentalBaselineError) as raised:
                    harness.execute()
                self.assertEqual(raised.exception.evidence["slots"][slot - 1]["status"], "failed")

    def test_missing_distance_and_unknown_schema_keys_are_rejected(self) -> None:
        def remove_distance(value: object) -> object:
            payload = copy.deepcopy(value)
            assert isinstance(payload, dict)
            payload.pop("distance_metric", None)
            return payload

        def add_unknown_schema_key(value: object) -> object:
            payload = copy.deepcopy(value)
            assert isinstance(payload, dict)
            schema = payload["schema"]
            assert isinstance(schema, dict)
            vector = schema["vector"]
            assert isinstance(vector, dict)
            vector["unknown"] = True
            return payload

        for slot, transform in (
            (1, remove_distance),
            (1, add_unknown_schema_key),
            (3, remove_distance),
            (3, add_unknown_schema_key),
            (21, remove_distance),
            (21, add_unknown_schema_key),
        ):
            with self.subTest(slot=slot):
                harness = Harness(absent=False)
                harness.transform_attempt = slot
                harness.transform = transform
                with self.assertRaises(ExperimentalBaselineError):
                    harness.execute()
                if slot <= 3:
                    self.assertEqual(harness.target.write_calls, 0)

    def test_attached_error_response_and_metrics_accounting_is_preserved(self) -> None:
        class AttachedError(DefinitiveProviderError):
            def __init__(self) -> None:
                super().__init__("secret error text")
                self.response = {
                    "rows_affected": 17,
                    "billing": {"logical_bytes": 91, "account_id": "secret"},
                    "request_id": "attached-request",
                }
                self.metrics = {"other_metric": 4}

        harness = Harness(absent=False)
        harness.fail_attempt = 6
        harness.failure = AttachedError()
        with self.assertRaises(ExperimentalBaselineError) as raised:
            harness.execute()
        attempt = raised.exception.evidence["slots"][5]
        self.assertEqual(attempt["status"], "failed")
        self.assertEqual(attempt["rows_affected"], 17)
        self.assertTrue(attempt["rows_affected_present"])
        self.assertEqual(attempt["billing"]["logical_bytes"], 91)
        self.assertEqual(attempt["billing"]["account_id"], "<redacted>")
        self.assertTrue(attempt["request_identity_present"])
        self.assertTrue(attempt["metrics_present"])
        self.assertEqual(attempt["metrics"]["other_metric"], 4)
        self.assertNotIn("attached-request", json.dumps(attempt))
        self.assertNotIn("secret error text", json.dumps(attempt))

    def test_local_partial_create_commit_and_cleanup_failures_are_observed(self) -> None:
        create = Harness()
        create.fail_create_after_effect = True
        with self.assertRaises(ExperimentalBaselineError) as raised:
            create.execute()
        self.assertTrue(raised.exception.evidence["pending_retained"])
        self.assertFalse(raised.exception.evidence["local_state_committed"])
        self.assertEqual(create.target.write_calls, 0)

        commit = Harness()
        commit.fail_commit_after_effect = True
        with self.assertRaises(ExperimentalBaselineError) as raised:
            commit.execute()
        self.assertTrue(raised.exception.evidence["pending_retained"])
        self.assertTrue(raised.exception.evidence["local_state_committed"])
        self.assertTrue(raised.exception.evidence["remote_card_verified"])

    def test_every_immutable_cache_and_prepared_attestation_fails_closed(self) -> None:
        cache_changes = {
            "revision": "wrong",
            "manifest_sha256": "wrong",
            "readme_sha256": "wrong",
            "license": "apache",
            "license_statement_present": False,
            "file_count": 11,
        }
        for field, value in cache_changes.items():
            with self.subTest(cache_field=field):
                harness = Harness()
                with self.assertRaises(ExperimentalBaselineError):
                    simulate_experimental_baseline(
                        harness.verified,
                        cache_attestation=replace(cache_attestation(), **{field: value}),
                        prepare=harness.prepare,
                        provider=harness.provider(),
                        local_effects=harness.effects(),
                    )
                self.assertNotIn("prepare-model", harness.events)

        prepared_changes = {
            "model": "wrong",
            "model_revision": "wrong",
            "precision": "float16",
            "dimensions": 3,
            "normalized": False,
            "pooling": "mean",
        }
        for field, value in prepared_changes.items():
            with self.subTest(prepared_field=field):
                harness = Harness()
                harness.prepared = replace(harness.prepared, **{field: value})
                with self.assertRaises(ExperimentalBaselineError):
                    harness.execute()
                self.assertEqual(harness.attempt_count, 0)
                self.assertFalse(harness.pending)

    def test_exact_plan_identity_gate_matrix(self) -> None:
        for field in ("plan_id", "artifact_hash", "namespace", "embedding_model", "embedding_precision"):
            with self.subTest(field=field):
                harness = Harness()
                harness.verified.plan[field] = "wrong"
                with self.assertRaises(ExperimentalBaselineError):
                    harness.execute()
                self.assertEqual(harness.attempt_count, 0)
                self.assertNotIn("prepare-model", harness.events)

    def test_checked_in_approval_record_exactness_and_live_signature(self) -> None:
        signature = inspect.signature(experimental_baseline.execute_experimental_baseline)
        self.assertEqual(
            list(signature.parameters),
            ["approval_record", "plan_path", "cache_root", "state_root"],
        )
        self.assertTrue(all(parameter.kind is inspect.Parameter.KEYWORD_ONLY for parameter in signature.parameters.values()))

        raw = APPROVAL_RECORD_PATH.read_bytes()
        result = validate_approval_a_record(APPROVAL_RECORD_PATH)
        self.assertEqual(len(raw), 2627)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), APPROVAL_RECORD_SHA256)
        self.assertEqual(len(APPROVAL_A_TEXT.encode("utf-8")), 2206)
        self.assertEqual(APPROVAL_A_TEXT_SHA256, "bafc2500292bc8fcfc4aa806873782d43689330c704620f8981684a3796bfa10")
        self.assertEqual(APPROVAL_A_GRANTED_RECORD_SHA256, APPROVAL_RECORD_SHA256)
        self.assertEqual(APPROVAL_A_GRANTED_PROVENANCE, APPROVAL_PROVENANCE)
        self.assertEqual(result["record_sha256"], APPROVAL_RECORD_SHA256)
        self.assertEqual(result["provenance"], APPROVAL_PROVENANCE)

    def test_every_checked_in_approval_record_byte_mutation_fails_closed(self) -> None:
        raw = APPROVAL_RECORD_PATH.read_bytes()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approval-a.json"
            for index in range(len(raw)):
                with self.subTest(byte_index=index):
                    mutated = bytearray(raw)
                    mutated[index] ^= 1
                    path.write_bytes(mutated)
                    with self.assertRaises(ExperimentalBaselineError):
                        validate_approval_a_record(path)

    def test_approval_provenance_and_text_mutations_fail_closed(self) -> None:
        record = json.loads(APPROVAL_RECORD_PATH.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "approval-a.json"
            for field in APPROVAL_PROVENANCE:
                with self.subTest(provenance_field=field):
                    mutated = copy.deepcopy(record)
                    mutated["provenance"][field] += "-altered"
                    raw = json.dumps(
                        mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                    ).encode("utf-8")
                    path.write_bytes(raw)
                    with mock.patch.object(
                        experimental_baseline,
                        "APPROVAL_A_GRANTED_RECORD_SHA256",
                        hashlib.sha256(raw).hexdigest(),
                    ):
                        with self.assertRaises(ExperimentalBaselineError):
                            validate_approval_a_record(path)

            mutated = copy.deepcopy(record)
            mutated["approval_text"] += " altered"
            mutated["approval_text_sha256"] = hashlib.sha256(
                mutated["approval_text"].encode("utf-8")
            ).hexdigest()
            raw = json.dumps(
                mutated, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            path.write_bytes(raw)
            with mock.patch.object(
                experimental_baseline,
                "APPROVAL_A_GRANTED_RECORD_SHA256",
                hashlib.sha256(raw).hexdigest(),
            ):
                with self.assertRaises(ExperimentalBaselineError):
                    validate_approval_a_record(path)


if __name__ == "__main__":
    unittest.main()
