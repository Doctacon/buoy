from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from buoy_search.applied_state import (
    ROW_STATUS_RETAINED_STALE,
    AppliedStateRow,
    build_applied_state,
    save_applied_state,
)
from buoy_search.chunker import process_corpus
from buoy_search.command_center_local import (
    InventoryLookupError,
    LocalInventoryService,
    MAX_PAGE_SIZE,
)
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts


DIFF = {
    "first_apply": True,
    "pages_added": 1,
    "pages_changed": 0,
    "pages_unchanged": 0,
    "pages_removed": 0,
    "chunks_unchanged": 0,
    "chunks_to_embed": 1,
    "rows_to_upsert": 1,
    "stale_rows": 0,
    "retained_stale_rows": 0,
}


def write_plan(
    root: Path,
    *,
    plan_id: str,
    namespace: str = "site-example-v1",
    site_id: str = "example",
    created_at: str = "2026-07-23T12:00:00+00:00",
    base_url: str = "https://example.com/docs",
    source_metadata: dict[str, str] | None = None,
    page_content_path: str = "page.md",
    content: str = "# Example\n\nPlain local markdown.",
    canonical_url: str | None = None,
    diff: dict[str, object] | None = DIFF,
    summary: dict[str, object] | None = None,
) -> Path:
    root.mkdir(parents=True)
    pages = root / "pages"
    pages.mkdir()
    if ".." not in Path(page_content_path).parts and not Path(page_content_path).is_absolute():
        page_path = pages / page_content_path
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(content, encoding="utf-8")
    metadata = dict(source_metadata or {})
    page = {
        "canonical_url": canonical_url or base_url.rstrip("/") + "/page",
        "title": "Example page",
        "content_path": page_content_path,
        "page_hash": "page-hash",
        "status": 200,
        "content_type": "text/markdown",
        "source_metadata": metadata,
    }
    chunk = {
        "row_id": "ts_abcdef",
        "row_id_candidate": "ts_abcdef",
        "site_id": site_id,
        "duplicate_ordinal": 0,
        "canonical_url": page["canonical_url"],
        "page_content_path": page_content_path,
        "page_hash": "page-hash",
        "chunk_hash": "chunk-hash",
        "embedding_text_hash": "embedding-hash",
        "title": "Example page",
        "section_path": "Example",
        "chunk_index": 0,
        "content": content,
        "content_preview": content[:240],
        "doc_kind": "page",
        "tags": ["page"],
        "source_metadata": metadata,
    }
    plan = {
        "schema_version": 1,
        "command": "plan",
        "plan_id": plan_id,
        "created_at": created_at,
        "base_url": base_url,
        "site_id": site_id,
        "namespace": namespace,
        "namespace_candidate": namespace,
        "state_backend": "local",
        "state_path": "/private/state/secret.duckdb",
        "crawl_options": {},
        "chunk_options": {},
        "embedding_model": "BAAI/bge-small-en-v1.5",
        "embedding_precision": "float32",
        "artifact_hash": "a" * 64,
        "manifest_path": "/private/artifacts/manifest.json",
        "chunks_path": "/private/artifacts/chunks.jsonl",
        "pages_dir": "/private/artifacts/pages",
        "diff": diff,
    }
    manifest = {
        "schema_version": 1,
        "site_id": site_id,
        "base_url": base_url,
        "namespace": namespace,
        "namespace_candidate": namespace,
        "pages": [page],
        "chunks": [chunk],
    }
    (root / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "chunks.jsonl").write_text(json.dumps(chunk) + "\n", encoding="utf-8")
    if summary is not None:
        payload = {"plan_id": plan_id, **summary}
        (root / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
    return root / "plan.json"


def save_state(
    state_root: Path,
    *,
    namespace: str = "site-example-v1",
    site_id: str = "example",
    active_rows: int = 1,
    retained_stale_rows: int = 0,
) -> None:
    save_applied_state(
        build_applied_state(
            site_id=site_id,
            namespace=namespace,
            base_url="https://example.com/docs" if site_id == "example" else f"https://{site_id}.example.com/docs",
            last_plan_id="plan_applied",
            last_apply_id="apply_applied",
            updated_at="2026-07-23T13:00:00+00:00",
            rows=[
                AppliedStateRow(
                    row_id=f"ts_applied_{index}",
                    canonical_url=f"https://{site_id}.example.com/docs/page/{index}",
                    page_hash=f"page-hash-{index}",
                    chunk_hash=f"chunk-hash-{index}",
                    embedding_text_hash=f"embedding-hash-{index}",
                    plan_id="plan_applied",
                    applied_at="2026-07-23T13:00:00+00:00",
                )
                for index in range(active_rows)
            ]
            + [
                AppliedStateRow(
                    row_id=f"ts_stale_{index}",
                    canonical_url=f"https://{site_id}.example.com/docs/stale/{index}",
                    page_hash=f"stale-page-hash-{index}",
                    chunk_hash=f"stale-chunk-hash-{index}",
                    embedding_text_hash=f"stale-embedding-hash-{index}",
                    plan_id="plan_applied",
                    applied_at="2026-07-23T13:00:00+00:00",
                    status=ROW_STATUS_RETAINED_STALE,
                )
                for index in range(retained_stale_rows)
            ],
        ),
        state_root=state_root,
    )


class LocalInventoryDiscoveryTests(unittest.TestCase):
    def test_recursive_discovery_dedupes_and_sorts_valid_newest_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            write_plan(
                artifacts / "nested" / "old-duplicate",
                plan_id="plan_duplicate",
                created_at="2026-07-22T00:00:00+00:00",
            )
            write_plan(
                artifacts / "new-duplicate",
                plan_id="plan_duplicate",
                created_at="2026-07-23T13:00:00+00:00",
            )
            write_plan(
                artifacts / "newest",
                plan_id="plan_newest",
                created_at="2026-07-23T14:00:00Z",
            )
            write_plan(
                artifacts / "invalid-time",
                plan_id="plan_invalid_time",
                created_at="not-a-time",
            )

            inventory = LocalInventoryService(
                artifacts_root=artifacts, state_root=root / "state"
            ).list_plans()

        self.assertEqual(
            [item.plan_id for item in inventory.items],
            ["plan_newest", "plan_duplicate", "plan_invalid_time"],
        )
        duplicate = inventory.items[1]
        self.assertEqual(duplicate.created_at, "2026-07-23T13:00:00+00:00")
        self.assertIn("duplicate_plan_id", [warning.code for warning in duplicate.warnings])
        self.assertIsNone(inventory.items[2].created_at)

    def test_malformed_plan_isolated_with_safe_error_and_no_private_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "very-private" / "artifacts"
            write_plan(artifacts / "valid", plan_id="plan_valid")
            malformed = artifacts / "customer-secret" / "malformed"
            malformed.mkdir(parents=True)
            (malformed / "plan.json").write_text("{not json", encoding="utf-8")

            inventory = LocalInventoryService(
                artifacts_root=artifacts, state_root=root / "state"
            ).list_plans()

        self.assertEqual([item.plan_id for item in inventory.items], ["plan_valid"])
        self.assertEqual(len(inventory.errors), 1)
        serialized = json.dumps(asdict(inventory.errors[0]))
        self.assertNotIn("customer-secret", serialized)
        self.assertNotIn(str(root), serialized)
        self.assertRegex(inventory.errors[0].artifact_id, r"^artifact_[0-9a-f]{16}$")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_discovery_does_not_follow_symlink_outside_artifacts_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            artifacts.mkdir()
            external = root / "external"
            write_plan(external, plan_id="plan_external")
            os.symlink(external, artifacts / "linked")

            inventory = LocalInventoryService(
                artifacts_root=artifacts, state_root=root / "state"
            ).list_plans()

        self.assertEqual(inventory.items, [])
        self.assertEqual([error.code for error in inventory.errors], ["unsafe_symlink"])

    def test_unknown_diff_counts_remain_unknown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan(root / "artifacts" / "plan", plan_id="plan_unknown", diff={})
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            item = service.list_plans().items[0]
            namespace = service.list_namespaces().items[0]
            dashboard = service.dashboard()

        self.assertIsNone(item.diff.first_apply)
        self.assertIsNone(item.diff.pages_added)
        self.assertIsNone(item.diff.rows_to_upsert)
        self.assertIsNone(namespace.latest_planned_upserts)
        self.assertEqual(namespace.local_status, "planned")
        self.assertEqual(dashboard.pending_namespace_count, 0)

    def test_current_plan_artifact_model_is_read_without_rewriting_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_dir = root / "artifacts" / "real-plan"
            pages = plan_dir / "pages"
            pages.mkdir(parents=True)
            (pages / "page.md").write_text(
                "---\nurl: https://example.com/page\ntitle: Example\n---\n\n# Example\n\nText.\n",
                encoding="utf-8",
            )
            artifacts = build_plan_artifacts(
                indexing_plan=process_corpus(pages),
                base_url="https://example.com",
                out_dir=plan_dir,
                state_root=root / "state",
            )
            write_plan_artifacts(artifacts, plan_dir)

            detail = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            ).get_plan(artifacts.plan.plan_id)

        self.assertEqual(detail.summary.namespace, artifacts.plan.namespace)
        self.assertEqual(detail.summary.page_count, len(artifacts.manifest.pages))
        self.assertEqual(detail.summary.chunk_count, len(artifacts.manifest.chunks))
        self.assertEqual(detail.artifact_hash, artifacts.plan.artifact_hash)


class LocalInventorySourceMappingTests(unittest.TestCase):
    def test_all_supported_source_kinds_use_persisted_safe_provenance(self) -> None:
        cases = (
            (
                "website",
                "https://docs.example.com/guide?private=token",
                {},
                {"kind": "website", "title": "docs.example.com", "uri": "https://docs.example.com/guide"},
            ),
            (
                "github",
                "https://github.com/Doctacon/buoy",
                {"source_kind": "github_repo", "repo_full_name": "Doctacon/buoy"},
                {"kind": "github_repo", "repository": "Doctacon/buoy"},
            ),
            (
                "document",
                "file://file-notes-abc123",
                {
                    "source_kind": "local_file",
                    "file_filename": "Research Notes.docx",
                    "file_source_id": "file-notes-abc123",
                    "file_path": "/Users/secret/Research Notes.docx",
                },
                {"kind": "document", "filename": "Research Notes.docx"},
            ),
            (
                "duckdb",
                "duckdb://calls",
                {
                    "source_kind": "duckdb_relation",
                    "duckdb_source_id": "calls",
                    "duckdb_relation": "analytics.calls",
                    "duckdb_path": "/Users/secret/calls.duckdb",
                },
                {"kind": "database", "database_backend": "duckdb", "database_source_id": "calls", "database_relation": "analytics.calls"},
            ),
            (
                "bigquery",
                "bigquery://calls",
                {
                    "source_kind": "bigquery_relation",
                    "database_backend": "bigquery",
                    "database_source_id": "calls",
                    "database_relation": "project.dataset.calls",
                    "query_project": "private-billing-project",
                },
                {"kind": "database", "database_backend": "bigquery", "database_source_id": "calls", "database_relation": "project.dataset.calls"},
            ),
            (
                "snowflake",
                "snowflake://calls",
                {
                    "source_kind": "snowflake_relation",
                    "database_backend": "snowflake",
                    "database_source_id": "calls",
                    "database_relation": "ANALYTICS.PUBLIC.CALLS",
                    "connection_name": "private-profile",
                },
                {"kind": "database", "database_backend": "snowflake", "database_source_id": "calls", "database_relation": "ANALYTICS.PUBLIC.CALLS"},
            ),
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            for index, (name, base_url, metadata, expected) in enumerate(cases):
                with self.subTest(name=name):
                    plan_id = f"plan_{name}"
                    write_plan(
                        root / "artifacts" / name,
                        plan_id=plan_id,
                        namespace=f"namespace-{index}",
                        site_id=f"site-{index}",
                        base_url=base_url,
                        source_metadata=metadata,
                        created_at=f"2026-07-23T{index:02d}:00:00+00:00",
                    )
                    source = service.get_plan(plan_id).summary.source
                    for key, value in expected.items():
                        self.assertEqual(getattr(source, key), value)
                    serialized = json.dumps(asdict(source))
                    for private in (
                        "/Users/secret",
                        "private-billing-project",
                        "private-profile",
                        "?private=token",
                    ):
                        self.assertNotIn(private, serialized)

    def test_plan_detail_exposes_sanitized_activity_and_retrieval_settings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan(
                root / "artifacts" / "plan",
                plan_id="plan_detail",
                summary={
                    "source_credentials_required": True,
                    "source_api_calls_occurred": True,
                    "connection_name": "secret-profile",
                    "catalog_registration": {
                        "ranking_mode": "page",
                        "ranking_profile": "none",
                        "ranking_pool": 20,
                        "ranking_aggregation": "max",
                        "region": "aws-us-east-1",
                    },
                },
            )
            detail = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            ).get_plan("plan_detail")

        self.assertTrue(detail.source_activity.credentials_required)
        self.assertTrue(detail.source_activity.api_calls_occurred)
        self.assertTrue(detail.summary.source_activity.credentials_required)
        self.assertTrue(detail.summary.source_activity.api_calls_occurred)
        self.assertEqual(detail.retrieval.ranking_pool, 20)
        self.assertEqual(detail.retrieval.region, "aws-us-east-1")
        serialized = json.dumps(asdict(detail))
        self.assertNotIn("secret-profile", serialized)
        self.assertNotIn("/private/", serialized)


class LocalInventoryNamespaceTests(unittest.TestCase):
    def test_namespace_inventory_combines_plans_and_applied_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = root / "artifacts"
            state_root = root / "state-root"
            write_plan(
                artifacts / "plan",
                plan_id="plan_pending",
                namespace="site-example-v1",
            )
            save_state(state_root, retained_stale_rows=2)
            save_state(state_root, namespace="state-only-v1")

            service = LocalInventoryService(
                artifacts_root=artifacts, state_root=state_root
            )
            inventory = service.list_namespaces()
            combined = service.get_namespace("site-example-v1")
            state_only = service.get_namespace("state-only-v1")
            dashboard = service.dashboard()

        self.assertEqual(
            [item.namespace for item in inventory.items],
            ["site-example-v1", "state-only-v1"],
        )
        self.assertEqual(combined.summary.plan_count, 1)
        self.assertTrue(combined.summary.applied)
        self.assertEqual(combined.summary.local_status, "pending_changes")
        self.assertEqual(combined.summary.active_rows, 1)
        self.assertEqual(combined.summary.retained_stale_rows, 2)
        self.assertEqual(combined.summary.latest_planned_upserts, 1)
        self.assertEqual(combined.summary.latest_planned_stale_rows, 0)
        self.assertEqual(combined.summary.document_count, 1)
        self.assertEqual(combined.summary.chunk_count, 1)
        self.assertEqual(combined.state.last_plan_id, "plan_applied")
        self.assertEqual(combined.plans[0].plan_id, "plan_pending")
        self.assertEqual(state_only.summary.plan_count, 0)
        self.assertTrue(state_only.summary.applied)
        self.assertEqual(state_only.summary.source.kind, "website")
        self.assertEqual(state_only.summary.source.title, "example.com")
        self.assertEqual(state_only.summary.local_status, "applied")
        self.assertEqual(dashboard.pending_namespace_count, 1)
        self.assertEqual(dashboard.artifact_error_count, 0)

    def test_duplicate_namespace_state_identity_is_conflicted_without_partial_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state-root"
            save_state(state_root, namespace="shared", site_id="site-a", active_rows=1)
            save_state(state_root, namespace="shared", site_id="site-b", active_rows=3)
            service = LocalInventoryService(artifacts_root=root / "artifacts", state_root=state_root)

            inventory = service.list_namespaces()
            detail = service.get_namespace("shared")
            dashboard = service.dashboard()

        self.assertEqual(inventory.total, 1)
        self.assertTrue(inventory.items[0].applied)
        self.assertIsNone(inventory.items[0].active_rows)
        self.assertIsNone(inventory.items[0].last_apply_id)
        self.assertEqual(inventory.items[0].local_status, "conflict")
        self.assertIn("namespace_identity_conflict", [warning.code for warning in inventory.items[0].warnings])
        self.assertIsNone(detail.state)
        self.assertIsNone(dashboard.active_row_count)
        self.assertIn("namespace_identity_conflict", [warning.code for warning in dashboard.attention_items])

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_symlinked_state_root_is_rejected_without_following_external_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            external = root / "external"
            save_state(external, namespace="external-state")
            linked = root / "linked-state-root"
            os.symlink(external, linked)

            service = LocalInventoryService(artifacts_root=root / "artifacts", state_root=linked)
            inventory = service.list_namespaces()

        self.assertEqual(inventory.items, [])
        self.assertEqual([error.code for error in inventory.errors], ["unsafe_state_root"])

    def test_malformed_state_is_isolated_and_dashboard_aggregates_valid_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state-root"
            save_state(state_root)
            malformed = state_root / "state" / "bad" / "bad"
            malformed.mkdir(parents=True)
            (malformed / "state.duckdb").write_text("not duckdb", encoding="utf-8")
            write_plan(root / "artifacts" / "plan", plan_id="plan_valid")

            dashboard = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=state_root
            ).dashboard()

        self.assertEqual(dashboard.plan_count, 1)
        self.assertEqual(dashboard.namespace_count, 1)
        self.assertIsNone(dashboard.active_row_count)
        self.assertEqual(dashboard.artifact_error_count, 1)
        self.assertEqual(len(dashboard.artifact_errors), 1)
        self.assertEqual(dashboard.artifact_errors[0].code, "malformed_state")


class LocalInventoryPreviewTests(unittest.TestCase):
    def test_pages_and_chunks_are_bounded_and_paginated(self) -> None:
        content = "plain <script>alert('no')</script> markdown " * 100
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan(
                root / "artifacts" / "plan", plan_id="plan_preview", content=content
            )
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )

            pages = service.list_plan_pages("plan_preview", offset=0, limit=1)
            page = service.get_plan_page("plan_preview", 0, max_chars=20)
            chunks = service.list_plan_chunks(
                "plan_preview", offset=0, limit=1, max_chars=25
            )

        self.assertEqual(pages.total, 1)
        self.assertEqual(page.markdown, content[:20])
        self.assertTrue(page.truncated)
        self.assertEqual(chunks.total, 1)
        self.assertEqual(chunks.items[0].content, content[:25])
        self.assertTrue(chunks.items[0].truncated)
        self.assertIn("<script>", content)

    def test_citations_strip_fragments_and_reject_path_shaped_internal_uris(self) -> None:
        cases = (
            (
                "https://example.test/doc?access_token=top-secret#access_token=fragment-secret",
                "https://example.test/doc",
            ),
            ("file://document-id/Users/private/secret.txt", ""),
            ("duckdb://knowledge-base/Users/private/secret.txt", ""),
            ("bigquery://knowledge-base/Users/private/secret.txt", ""),
            ("snowflake://knowledge-base/Users/private/secret.txt", ""),
            (
                "pdf://pdf-research-notes-abc123/Research%20Notes.pdf",
                "pdf://pdf-research-notes-abc123/Research%20Notes.pdf",
            ),
        )
        for index, (citation, expected) in enumerate(cases):
            with self.subTest(citation=citation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_plan(
                    root / "artifacts" / "plan",
                    plan_id=f"plan_citation_{index}",
                    canonical_url=citation,
                )
                service = LocalInventoryService(
                    artifacts_root=root / "artifacts", state_root=root / "state"
                )

                pages = service.list_plan_pages(f"plan_citation_{index}")
                chunks = service.list_plan_chunks(f"plan_citation_{index}")

            self.assertEqual(pages.items[0].canonical_url, expected)
            self.assertEqual(chunks.items[0].canonical_url, expected)
            self.assertNotIn("top-secret", repr((pages, chunks)))
            self.assertNotIn("fragment-secret", repr((pages, chunks)))
            self.assertNotIn("/Users/private", repr((pages, chunks)))

    def test_pagination_preview_and_lookup_bounds_fail_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan(root / "artifacts" / "plan", plan_id="plan_bounds")
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )
            cases = (
                lambda: service.list_plans(offset=-1),
                lambda: service.list_plans(limit=MAX_PAGE_SIZE + 1),
                lambda: service.list_plan_chunks("plan_bounds", max_chars=20_001),
                lambda: service.get_plan_page("plan_bounds", 5),
                lambda: service.get_plan("../../secret"),
            )
            for operation in cases:
                with self.subTest(operation=operation), self.assertRaises(InventoryLookupError):
                    operation()

    def test_traversal_page_path_makes_plan_an_item_level_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_plan(
                root / "artifacts" / "plan",
                plan_id="plan_traversal",
                page_content_path="../secret.md",
            )
            (root / "artifacts" / "plan" / "secret.md").write_text(
                "do not expose", encoding="utf-8"
            )
            inventory = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            ).list_plans()

        self.assertEqual(inventory.items, [])
        self.assertEqual(inventory.errors[0].code, "malformed_plan")

    @unittest.skipUnless(hasattr(os, "symlink"), "symlinks are unavailable")
    def test_page_preview_rejects_symlink_even_when_target_is_inside_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan_dir = root / "artifacts" / "plan"
            write_plan(plan_dir, plan_id="plan_symlink")
            page_path = plan_dir / "pages" / "page.md"
            target = plan_dir / "pages" / "target.md"
            target.write_text("target", encoding="utf-8")
            page_path.unlink()
            os.symlink(target, page_path)
            service = LocalInventoryService(
                artifacts_root=root / "artifacts", state_root=root / "state"
            )

            with self.assertRaisesRegex(InventoryLookupError, "unsafe"):
                service.get_plan_page("plan_symlink", 0)


class LocalInventoryIsolationTests(unittest.TestCase):
    def test_clean_import_does_not_import_adapters_remote_clients_or_model_packages(self) -> None:
        script = """
import sys
import buoy_search.command_center_local
forbidden = {
    'buoy_search.bigquery_relation',
    'buoy_search.snowflake_relation',
    'buoy_search.remote_catalog',
    'turbopuffer',
    'sentence_transformers',
    'transformers',
    'google.cloud.bigquery',
    'snowflake.connector',
}
loaded = sorted(name for name in forbidden if name in sys.modules)
assert loaded == [], loaded
print('isolated')
"""
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), "isolated")


if __name__ == "__main__":
    unittest.main()
