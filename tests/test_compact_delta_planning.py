from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import quote, urlsplit, urlunsplit

import duckdb

from buoy_search.applied_state import (
    ROW_STATUS_RETAINED_STALE,
    AppliedStateRow,
    build_applied_state,
)
from buoy_search.chunker import process_corpus
from buoy_search.plan_artifacts import (
    DELTA_SCHEMA_VERSION,
    PLAN_SCHEMA_VERSION,
    applied_state_descriptor,
    artifact_identity,
    build_plan_artifacts,
    delta_logical_hash,
    generic_site_row_id,
    stable_hash,
    verify_plan_artifacts,
    write_plan_artifacts,
)


class CompactDeltaPlanningTests(unittest.TestCase):
    def build(
        self,
        root: Path,
        *,
        base_url: str = "https://example.com/docs",
        body: str = "# Guide\n\nStable documentation content.",
        metadata: dict[str, str] | None = None,
        source_summary: dict[str, object] | None = None,
        state=None,  # noqa: ANN001 - compact fixture accepts AppliedState or None.
        state_present: bool = False,
    ):
        pages = root / "pages"
        pages.mkdir(parents=True, exist_ok=True)
        source_metadata = dict(metadata or {})
        kind = str(source_metadata.get("source_kind", "website"))
        if kind == "github_repo":
            source_metadata.setdefault("repo_path", "README.md")
            canonical_url = (
                f"{base_url}/blob/{quote(str(source_metadata['repo_ref']), safe='/')}/"
                f"{quote(str(source_metadata['repo_path']), safe='/')}"
            )
        elif kind in {"local_file", "pdf"}:
            filename = str(
                source_metadata.get("file_filename") or source_metadata.get("pdf_filename")
            )
            canonical_url = f"{base_url}/{quote(filename, safe='')}"
        elif kind.endswith("_relation"):
            canonical_url = f"{base_url}/{quote(str(source_metadata['database_document_id']), safe='')}"
        else:
            parsed_base = urlsplit(base_url)
            canonical_url = urlunsplit(parsed_base._replace(
                path=f"{parsed_base.path.rstrip('/')}/page",
            ))
        frontmatter = {
            "url": canonical_url,
            "title": "Guide",
            "status": "200",
            "content_type": "text/markdown",
            "source_hash": "source-hash",
            **source_metadata,
        }
        text = ["---", *[f'{key}: {json.dumps(value)}' for key, value in frontmatter.items()], "---", "", body, ""]
        (pages / "page.md").write_text("\n".join(text), encoding="utf-8")
        return build_plan_artifacts(
            indexing_plan=process_corpus(pages),
            base_url=base_url,
            out_dir=root / "plan",
            applied_state=state,
            state_present=state_present,
            source_summary=source_summary,
        )

    @staticmethod
    def state_row(chunk, *, status="active"):  # noqa: ANN001 - fixture chunk.
        return AppliedStateRow(
            row_id=chunk.row_id,
            canonical_url=chunk.canonical_url,
            page_hash=chunk.page_hash,
            chunk_hash=chunk.chunk_hash,
            embedding_text_hash=chunk.embedding_text_hash,
            plan_id=f"plan_{'a' * 16}",
            applied_at="2026-07-24T00:00:00+00:00",
            status=status,
        )

    @staticmethod
    def resign(out: Path, *, sync_diff: bool = True) -> None:
        plan_path = out / "plan.json"
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        with duckdb.connect(str(out / "delta.duckdb")) as connection:
            raw_upserts = connection.execute("SELECT * FROM upsert_rows ORDER BY ordinal").fetchall()
            raw_stale = connection.execute("SELECT * FROM stale_rows ORDER BY ordinal").fetchall()
            upserts = [
                {
                    "action": row[1], "row_id": row[2], "row_id_candidate": row[3],
                    "site_id": row[4], "duplicate_ordinal": row[5], "canonical_url": row[6],
                    "source_path": row[7], "page_hash": row[8], "chunk_hash": row[9],
                    "embedding_text_hash": row[10], "title": row[11],
                    "section_path": row[12], "chunk_index": row[13], "content": row[14],
                    "doc_kind": row[15], "tags_json": json.loads(row[16]),
                    "source_metadata_json": json.loads(row[17]),
                }
                for row in raw_upserts
            ]
            stale = [
                {
                    "category": row[1], "row_id": row[2], "canonical_url": row[3],
                    "page_hash": row[4], "chunk_hash": row[5],
                    "embedding_text_hash": row[6], "prior_plan_id": row[7],
                    "prior_applied_at": row[8], "prior_status": row[9], "reason": row[10],
                }
                for row in raw_stale
            ]
            logical_hash = delta_logical_hash(upserts, stale)
            stale_count = sum(row["category"] == "stale" for row in stale)
            retained_count = sum(row["category"] == "retained_stale" for row in stale)
            plan["delta"].update({
                "logical_hash": logical_hash,
                "upsert_count": len(upserts),
                "stale_count": stale_count,
                "retained_stale_count": retained_count,
            })
            if sync_diff:
                plan["diff"].update({
                    "chunks_to_embed": len(upserts), "rows_to_upsert": len(upserts),
                    "stale_rows": stale_count, "retained_stale_rows": retained_count,
                })
            plan["artifact_hash"] = stable_hash(artifact_identity(plan))
            plan["plan_id"] = f"plan_{plan['artifact_hash'][:16]}"
            connection.execute(
                """
                UPDATE delta_metadata SET plan_id=?, logical_hash=?, upsert_count=?,
                  stale_count=?, retained_stale_count=?
                """,
                [plan["plan_id"], logical_hash, len(upserts), stale_count, retained_count],
            )
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_logical_hash_uses_exact_sql_field_names_and_parsed_json_values(self) -> None:
        upsert = {
            "action": "new", "row_id": f"ts_{'1' * 32}",
            "row_id_candidate": f"ts_{'1' * 32}", "site_id": "example-com",
            "duplicate_ordinal": 0, "canonical_url": "https://example.com/a",
            "source_path": "a.md", "page_hash": "2" * 64, "chunk_hash": "3" * 64,
            "embedding_text_hash": "4" * 64, "title": "A", "section_path": "A",
            "chunk_index": 0, "content": "body", "doc_kind": "docs",
            "tags_json": ["docs"], "source_metadata_json": {"source_kind": "website"},
        }
        stale = {
            "category": "stale", "row_id": f"ts_{'5' * 32}",
            "canonical_url": "https://example.com/old", "page_hash": "6" * 64,
            "chunk_hash": "7" * 64, "embedding_text_hash": "8" * 64,
            "prior_plan_id": f"plan_{'9' * 16}",
            "prior_applied_at": "2026-07-24T00:00:00+00:00",
            "prior_status": "active", "reason": "not_in_desired_source",
        }
        self.assertEqual(
            delta_logical_hash([upsert], [stale]),
            "63be0bcd5baa1f70a8af47dcb7cea715156cdbc00db1a60f632200a7d1a5419b",
        )
        renamed = {**upsert, "tags": upsert["tags_json"]}
        del renamed["tags_json"]
        self.assertNotEqual(delta_logical_hash([renamed], [stale]), delta_logical_hash([upsert], [stale]))

    def test_incremental_plan_persists_only_changed_and_stale_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial = self.build(root / "initial")
            prior = initial.manifest.chunks[0]
            extra_active = AppliedStateRow(
                f"ts_{'1' * 32}", "https://example.com/removed", "1" * 64, "2" * 64, "3" * 64,
                f"plan_{'b' * 16}", "2026-07-24T00:00:00+00:00",
            )
            extra_retained = AppliedStateRow(
                f"ts_{'4' * 32}", "https://example.com/old", "4" * 64, "5" * 64, "6" * 64,
                f"plan_{'c' * 16}", "2026-07-24T00:00:00+00:00", ROW_STATUS_RETAINED_STALE,
            )
            state = build_applied_state(
                site_id=initial.manifest.site_id,
                namespace=initial.manifest.namespace,
                base_url=initial.manifest.base_url,
                last_plan_id="plan_previous",
                last_apply_id="apply_previous",
                rows=[self.state_row(prior), extra_active, extra_retained],
                updated_at="2026-07-24T00:00:00+00:00",
            )
            changed = self.build(
                root / "changed", body="# Guide\n\nChanged documentation content.",
                state=state, state_present=True,
            )
            out = root / "out"
            write_plan_artifacts(changed, out)
            verified = verify_plan_artifacts(out / "plan.json")
            output_names = {path.name for path in out.iterdir()}
            plan_text = out.joinpath("plan.json").read_text(encoding="utf-8")

        self.assertEqual(output_names, {"plan.json", "delta.duckdb"})
        self.assertEqual(len(verified.upsert_rows), 1)
        self.assertEqual(verified.upsert_rows[0]["action"], "changed")
        self.assertIn("Changed documentation", verified.upsert_rows[0]["content"])
        self.assertNotIn("Stable documentation", plan_text)
        self.assertEqual(
            {(row["row_id"], row["category"]) for row in verified.stale_rows},
            {
                (f"ts_{'4' * 32}", "retained_stale"),
                (f"ts_{'1' * 32}", "stale"),
                (prior.row_id, "stale"),
            },
        )
        self.assertTrue(verified.plan["applied_state"]["present"])

    def test_no_change_stores_no_content_and_reactivation_stores_exact_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial = self.build(root / "initial")
            chunk = initial.manifest.chunks[0]
            active_state = build_applied_state(
                site_id=initial.manifest.site_id,
                namespace=initial.manifest.namespace,
                base_url=initial.manifest.base_url,
                last_plan_id="plan_previous", last_apply_id="apply_previous",
                rows=[self.state_row(chunk)], updated_at="2026-07-24T00:00:00+00:00",
            )
            unchanged = self.build(root / "unchanged", state=active_state, state_present=True)
            retained_state = build_applied_state(
                site_id=initial.manifest.site_id,
                namespace=initial.manifest.namespace,
                base_url=initial.manifest.base_url,
                last_plan_id="plan_previous", last_apply_id="apply_previous",
                rows=[self.state_row(chunk, status=ROW_STATUS_RETAINED_STALE)],
                updated_at="2026-07-24T00:00:00+00:00",
            )
            reactivated = self.build(root / "reactivated", state=retained_state, state_present=True)

        self.assertEqual(unchanged.upsert_rows, ())
        self.assertEqual(unchanged.stale_rows, ())
        self.assertEqual(unchanged.plan.delta["upsert_count"], 0)
        self.assertEqual(reactivated.upsert_rows[0]["action"], "reactivate_retained_stale")
        self.assertEqual(reactivated.upsert_rows[0]["row_id"], chunk.row_id)

    def test_presence_bit_changes_baseline_identity_without_creating_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.build(root / "first")
            state = build_applied_state(
                site_id=first.manifest.site_id,
                namespace=first.manifest.namespace,
                base_url=first.manifest.base_url,
                last_plan_id="", last_apply_id="", rows=[],
                updated_at="",
            )
            absent = applied_state_descriptor(state, present=False)
            present = applied_state_descriptor(state, present=True)

        self.assertNotEqual(absent["hash"], present["hash"])
        self.assertFalse((root / "state").exists())

    def test_every_source_kind_has_complete_plan_level_provenance_with_zero_upserts(self) -> None:
        cases = [
            ("website", "https://example.com/docs", {}, {}),
            (
                "github_repo", "https://github.com/octocat/Hello-World",
                {"source_kind": "github_repo", "repo_full_name": "octocat/Hello-World", "repo_owner": "octocat", "repo_name": "Hello-World", "repo_ref": "master", "commit_sha": "a" * 40},
                {"source_kind": "github_repo", "repo_full_name": "octocat/Hello-World", "repo_owner": "octocat", "repo_name": "Hello-World", "repo_ref": "master", "commit_sha": "a" * 40, "repo_subdir": None},
            ),
            (
                "local_file", "file://file-notes-abc",
                {"source_kind": "local_file", "file_filename": "notes.md", "file_extension": "md", "file_sha256": "abc", "file_source_id": "file-notes-abc"},
                {"source_kind": "local_file", "file_filename": "notes.md", "file_extension": "md", "file_sha256": "abc", "file_source_id": "file-notes-abc"},
            ),
            (
                "pdf", "pdf://pdf-notes-abc",
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc", "file_filename": "notes.pdf", "file_extension": "pdf", "file_sha256": "abc", "file_source_id": "pdf-notes-abc"},
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc"},
            ),
            *[
                (
                    f"{backend}_relation", f"{backend}://docs",
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": {"duckdb": "documents", "bigquery": "proj.dataset.documents", "snowflake": "DB.SCHEMA.DOCUMENTS"}[backend], "database_document_id": "1"},
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": {"duckdb": "documents", "bigquery": "proj.dataset.documents", "snowflake": "DB.SCHEMA.DOCUMENTS"}[backend]},
                )
                for backend in ("duckdb", "bigquery", "snowflake")
            ],
        ]
        for kind, uri, metadata, summary in cases:
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                first = self.build(root / "first", base_url=uri, metadata=metadata, source_summary=summary)
                chunk = first.manifest.chunks[0]
                state = build_applied_state(
                    site_id=first.manifest.site_id, namespace=first.manifest.namespace,
                    base_url=first.manifest.base_url, last_plan_id="plan_previous",
                    last_apply_id="apply_previous", rows=[self.state_row(chunk)],
                    updated_at="2026-07-24T00:00:00+00:00",
                )
                plan = self.build(root / "second", base_url=uri, metadata=metadata,
                                  source_summary=summary, state=state, state_present=True)
                self.assertEqual(plan.upsert_rows, ())
                self.assertEqual(plan.plan.source["kind"], kind)
                self.assertTrue(plan.plan.source["attributes"] or kind == "website")
                out = root / "out"
                write_plan_artifacts(plan, out)
                verified = verify_plan_artifacts(out / "plan.json")
                self.assertEqual(verified.upsert_rows, ())
                self.assertEqual(verified.plan["source"]["kind"], kind)

    def test_resigned_foreign_canonical_urls_are_rejected_for_every_source_variant(self) -> None:
        cases = [
            ("website", "https://example.com/docs", {}, {}, "https://evil.example/page"),
            (
                "github", "https://github.com/owner/repo",
                {"source_kind": "github_repo", "repo_full_name": "owner/repo", "repo_owner": "owner", "repo_name": "repo", "repo_ref": "main", "commit_sha": "abc", "repo_path": "README.md"},
                {"source_kind": "github_repo", "repo_full_name": "owner/repo", "repo_owner": "owner", "repo_name": "repo", "repo_ref": "main", "commit_sha": "abc", "repo_path": "README.md"},
                "https://github.com/other/repo/blob/main/README.md",
            ),
            (
                "local", "file://file-notes-abc",
                {"source_kind": "local_file", "file_filename": "notes.md", "file_extension": "md", "file_sha256": "abc", "file_source_id": "file-notes-abc"},
                {"source_kind": "local_file", "file_filename": "notes.md", "file_extension": "md", "file_sha256": "abc", "file_source_id": "file-notes-abc"},
                "file://other/notes.md",
            ),
            (
                "pdf", "pdf://pdf-notes-abc",
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc", "file_filename": "notes.pdf", "file_extension": "pdf", "file_sha256": "abc", "file_source_id": "pdf-notes-abc"},
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc"},
                "pdf://other/notes.pdf",
            ),
            *[
                (
                    backend, f"{backend}://docs",
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": relation, "database_document_id": "1", **({"duckdb_source_id": "docs", "duckdb_relation": relation, "duckdb_document_id": "1"} if backend == "duckdb" else {})},
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": relation},
                    f"{backend}://other/1",
                )
                for backend, relation in (("duckdb", "documents"), ("bigquery", "proj.dataset.documents"), ("snowflake", "DB.SCHEMA.DOCUMENTS"))
            ],
        ]
        for name, uri, metadata, summary, foreign_url in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(
                    self.build(root / "build", base_url=uri, metadata=metadata, source_summary=summary),
                    out,
                )
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    row = connection.execute(
                        "SELECT site_id, section_path, chunk_hash, duplicate_ordinal FROM upsert_rows"
                    ).fetchone()
                    row_id = generic_site_row_id(
                        site_id=row[0], canonical_url=foreign_url, section_path=row[1],
                        chunk_hash=row[2], duplicate_ordinal=row[3],
                    )
                    connection.execute(
                        "UPDATE upsert_rows SET canonical_url=?, row_id=?, row_id_candidate=?",
                        [foreign_url, row_id, row_id],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, "authority|contradicts"):
                    verify_plan_artifacts(out / "plan.json")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial = self.build(root / "initial")
            foreign_stale = AppliedStateRow(
                f"ts_{'e' * 32}", "https://evil.example/old", "1" * 64, "2" * 64,
                "3" * 64, f"plan_{'e' * 16}", "2026-07-24T00:00:00+00:00",
            )
            state = build_applied_state(
                site_id=initial.manifest.site_id, namespace=initial.manifest.namespace,
                base_url=initial.manifest.base_url, last_plan_id=f"plan_{'d' * 16}",
                last_apply_id="apply_previous", rows=[foreign_stale],
                updated_at="2026-07-24T00:00:00+00:00",
            )
            artifacts = self.build(root / "next", state=state, state_present=True)
            with self.assertRaisesRegex(ValueError, "outside website source authority"):
                write_plan_artifacts(artifacts, root / "out")

    def test_resigned_source_alias_identity_schema_and_privacy_tampering_is_rejected(self) -> None:
        pdf_metadata = {
            "source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc",
            "pdf_source_id": "pdf-notes-abc", "file_filename": "notes.pdf",
            "file_extension": "pdf", "file_sha256": "abc", "file_source_id": "pdf-notes-abc",
        }
        pdf_summary = {
            "source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc",
            "pdf_source_id": "pdf-notes-abc",
        }
        duck_metadata = {
            "source_kind": "duckdb_relation", "database_backend": "duckdb",
            "database_source_id": "docs", "database_relation": "documents",
            "database_document_id": "1", "duckdb_source_id": "docs",
            "duckdb_relation": "documents", "duckdb_document_id": "1",
        }
        duck_summary = {
            "source_kind": "duckdb_relation", "database_backend": "duckdb",
            "database_source_id": "docs", "database_relation": "documents",
        }
        alias_cases = [
            *[
                (f"pdf-{field}", "pdf://pdf-notes-abc", pdf_metadata, pdf_summary, field, "wrong")
                for field in ("file_filename", "file_extension", "file_sha256", "file_source_id")
            ],
            *[
                (f"duckdb-{field}", "duckdb://docs", duck_metadata, duck_summary, field, "wrong")
                for field in ("duckdb_source_id", "duckdb_relation", "duckdb_document_id")
            ],
        ]
        for name, uri, metadata, summary, field, value in alias_cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build", base_url=uri, metadata=metadata, source_summary=summary), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    stored = json.loads(connection.execute("SELECT source_metadata_json FROM upsert_rows").fetchone()[0])
                    stored[field] = value
                    connection.execute(
                        "UPDATE upsert_rows SET source_metadata_json=?",
                        [json.dumps(stored, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, "alias .* contradicts"):
                    verify_plan_artifacts(out / "plan.json")

        plan_mutations = [
            ("site_id", "other-site", "site_id does not match"),
            ("namespace_candidate", "other-v1", "namespace_candidate does not match"),
            ("applied_schema", 999, "schema version"),
            ("profile", "secret-profile", "provider-connection"),
            ("connection", "postgres://user:pass@example.com/db", "provider-connection"),
        ]
        for name, value, error in plan_mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                if name == "applied_schema":
                    plan["applied_state"]["schema_version"] = value
                elif name in {"profile", "connection"}:
                    plan["crawl_options"][f"source_{name}"] = value
                else:
                    plan[name] = value
                plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(plan_path)

        for key in ("access_token", "provider_profile", "connection_string", "authorization", "cookie", "api_key", "client_secret"):
            with self.subTest(metadata_key=key), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    connection.execute(
                        "UPDATE upsert_rows SET source_metadata_json=?",
                        [json.dumps({key: "private"}, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, "credential-bearing or provider-connection"):
                    verify_plan_artifacts(out / "plan.json")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            write_plan_artifacts(self.build(root / "build"), out)
            plan_path = out / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["chunk_options"].update({
                "ranking_profile": "repo_code", "target_tokens": 300,
                "tokenizer_model": "safe-public-model",
            })
            plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.resign(out)
            verified = verify_plan_artifacts(plan_path)
            self.assertEqual(verified.plan["chunk_options"]["ranking_profile"], "repo_code")

    def test_hash_count_schema_and_identity_tampering_are_rejected(self) -> None:
        mutations = [
            ("count", "UPDATE delta_metadata SET upsert_count = upsert_count + 1", "metadata"),
            ("logical", "UPDATE upsert_rows SET content = 'tampered'", "logical hash"),
            ("identity", "UPDATE delta_metadata SET namespace = 'other'", "metadata"),
        ]
        for name, sql, error in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                artifacts = self.build(root / "build")
                out = root / "out"
                write_plan_artifacts(artifacts, out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    connection.execute(sql)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

        for object_sql in (
            "CREATE TABLE unexpected(value INTEGER)",
            "CREATE SCHEMA extra; CREATE TABLE extra.unexpected(value INTEGER)",
            "CREATE SCHEMA extra; CREATE VIEW extra.unexpected AS SELECT * FROM main.upsert_rows",
            "CREATE SCHEMA extra; CREATE MACRO extra.unexpected(x) AS x + 1",
        ):
            with self.subTest(object_sql=object_sql), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                artifacts = self.build(root / "build")
                out = root / "out"
                write_plan_artifacts(artifacts, out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    connection.execute(object_sql)
                with self.assertRaisesRegex(ValueError, "tables/views|macros/functions"):
                    verify_plan_artifacts(out / "plan.json")

    def test_credential_bearing_source_uri_is_rejected_before_persistence_and_on_verify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaisesRegex(ValueError, "userinfo or credentials"):
                self.build(root / "bad", base_url="https://user:secret@example.com/docs")
            artifacts = self.build(root / "safe")
            out = root / "out"
            write_plan_artifacts(artifacts, out)
            plan_path = out / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["source"]["uri"] = "https://user:secret@example.com/docs"
            plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "userinfo or credentials"):
                verify_plan_artifacts(plan_path)

    def test_secret_queries_fragments_provider_metadata_and_cross_kind_fields_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "source-query"
            write_plan_artifacts(self.build(root / "source-build"), out)
            plan_path = out / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["source"]["uri"] = "https://example.com/docs?access_token=top-secret"
            plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "secret-bearing URI query"):
                verify_plan_artifacts(plan_path)

        row_urls = (
            ("https://example.com/docs/page?api_key=top-secret", "secret-bearing URI query"),
            ("https://example.com/docs/page#private=ordinary", "secret-bearing URI fragment"),
            ("https://example.com/docs/page#section=secret", "secret-bearing URI fragment"),
        )
        for canonical_url, error in row_urls:
            with self.subTest(canonical_url=canonical_url), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    site_id, section_path, chunk_hash, duplicate_ordinal, metadata_text = connection.execute(
                        "SELECT site_id, section_path, chunk_hash, duplicate_ordinal, source_metadata_json FROM upsert_rows"
                    ).fetchone()
                    metadata = json.loads(metadata_text)
                    metadata["url"] = canonical_url
                    row_id = generic_site_row_id(
                        site_id=site_id,
                        canonical_url=canonical_url,
                        section_path=section_path,
                        chunk_hash=chunk_hash,
                        duplicate_ordinal=duplicate_ordinal,
                    )
                    connection.execute(
                        "UPDATE upsert_rows SET canonical_url=?, row_id=?, row_id_candidate=?, source_metadata_json=?",
                        [canonical_url, row_id, row_id, json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

        metadata_cases = (
            ({"postgres_endpoint": "postgres://db.example/private"}, "unapproved provider connection URI"),
            ({"snowflake_account": "private-account"}, "unapproved custom/provider"),
            ({"duckdb_document_id": "foreign-document"}, "fields from another source kind"),
        )
        for injected, error in metadata_cases:
            with self.subTest(injected=injected), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    metadata = json.loads(connection.execute(
                        "SELECT source_metadata_json FROM upsert_rows"
                    ).fetchone()[0])
                    metadata.update(injected)
                    connection.execute(
                        "UPDATE upsert_rows SET source_metadata_json=?",
                        [json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

    def test_recursive_privacy_validation_rejects_nested_uris_and_allows_safe_public_urls(self) -> None:
        option_cases = (
            (
                "crawl_options",
                {"references": [{"next": "https://relay.example/?target=https%253A%252F%252Fuser%253Asecret%2540private.example%252Fdocs"}]},
                "credential-bearing URI",
            ),
            (
                "chunk_options",
                {"references": ["https://relay.example/?target=postgresql%253A%252F%252Fdb.example%252Fprivate"]},
                "unapproved provider connection URI",
            ),
        )
        for field, value, error in option_cases:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan[field] = value
                plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(plan_path)

        metadata_cases = (
            (
                "https://relay.example/?target=https%253A%252F%252Fuser%253Asecret%2540private.example%252Fdocs",
                "credential-bearing URI",
            ),
            (
                "https://relay.example/?target=postgresql%253A%252F%252Fdb.example%252Fprivate",
                "unapproved provider connection URI",
            ),
        )
        for value, error in metadata_cases:
            with self.subTest(value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    metadata = json.loads(connection.execute(
                        "SELECT source_metadata_json FROM upsert_rows"
                    ).fetchone()[0])
                    metadata["fetcher"] = value
                    connection.execute(
                        "UPDATE upsert_rows SET source_metadata_json=?",
                        [json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            write_plan_artifacts(self.build(root / "build"), out)
            plan_path = out / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            safe_nested = "https://relay.example/?target=https%253A%252F%252Fpublic.example%252Fdocs%253Flang%253Den"
            plan["crawl_options"] = {"references": [{"next": safe_nested}]}
            plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with duckdb.connect(str(out / "delta.duckdb")) as connection:
                metadata = json.loads(connection.execute(
                    "SELECT source_metadata_json FROM upsert_rows"
                ).fetchone()[0])
                metadata["fetcher"] = safe_nested
                connection.execute(
                    "UPDATE upsert_rows SET source_metadata_json=?",
                    [json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                )
            self.resign(out)
            verified = verify_plan_artifacts(plan_path)
            self.assertEqual(verified.plan["crawl_options"]["references"][0]["next"], safe_nested)
            self.assertEqual(verified.upsert_rows[0]["source_metadata_json"]["fetcher"], safe_nested)

    def test_privacy_validation_fails_closed_on_unstable_url_decoding(self) -> None:
        credential_uri = "https://user:secret@private.example/docs"
        encoded = credential_uri
        for _ in range(7):
            encoded = quote(encoded, safe="")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            write_plan_artifacts(self.build(root / "build"), out)
            plan_path = out / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            plan["crawl_options"] = {"redirect": encoded}
            plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            self.resign(out)
            with self.assertRaisesRegex(ValueError, "URL decode limit"):
                verify_plan_artifacts(plan_path)

    def test_privacy_validation_rejects_all_absolute_filesystem_path_forms(self) -> None:
        path_cases = (
            "/var/lib/buoy/private.db",
            "C:\\Users\\operator\\private.db",
            "\\\\server\\share\\private.db",
        )
        for value in path_cases:
            with self.subTest(location="options", value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["crawl_options"] = {"cache": value}
                plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.resign(out)
                with self.assertRaisesRegex(ValueError, "private absolute path"):
                    verify_plan_artifacts(plan_path)

            with self.subTest(location="metadata", value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    metadata = json.loads(connection.execute(
                        "SELECT source_metadata_json FROM upsert_rows"
                    ).fetchone()[0])
                    metadata["fetcher"] = value
                    connection.execute(
                        "UPDATE upsert_rows SET source_metadata_json=?",
                        [json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                    )
                self.resign(out)
                with self.assertRaisesRegex(ValueError, "private absolute path"):
                    verify_plan_artifacts(out / "plan.json")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            write_plan_artifacts(
                self.build(root / "build", base_url="https://example.com/var/lib/docs"),
                out,
            )
            verified = verify_plan_artifacts(out / "plan.json")
            self.assertEqual(verified.plan["source"]["uri"], "https://example.com/var/lib/docs")

    def test_legitimate_website_query_and_fragment_are_preserved_safely(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "out"
            write_plan_artifacts(
                self.build(root / "build", base_url="https://example.com/docs?lang=en#guide"),
                out,
            )
            verified = verify_plan_artifacts(out / "plan.json")
            self.assertEqual(verified.plan["source"]["uri"], "https://example.com/docs?lang=en")
            self.assertEqual(
                verified.upsert_rows[0]["canonical_url"],
                "https://example.com/docs/page?lang=en#guide",
            )

            canonical_url = "https://example.com/docs/page?lang=en#install"
            with duckdb.connect(str(out / "delta.duckdb")) as connection:
                site_id, section_path, chunk_hash, duplicate_ordinal, metadata_text = connection.execute(
                    "SELECT site_id, section_path, chunk_hash, duplicate_ordinal, source_metadata_json FROM upsert_rows"
                ).fetchone()
                metadata = json.loads(metadata_text)
                metadata["url"] = canonical_url
                row_id = generic_site_row_id(
                    site_id=site_id,
                    canonical_url=canonical_url,
                    section_path=section_path,
                    chunk_hash=chunk_hash,
                    duplicate_ordinal=duplicate_ordinal,
                )
                connection.execute(
                    "UPDATE upsert_rows SET canonical_url=?, row_id=?, row_id_candidate=?, source_metadata_json=?",
                    [canonical_url, row_id, row_id, json.dumps(metadata, sort_keys=True, separators=(",", ":"))],
                )
            self.resign(out)
            verified = verify_plan_artifacts(out / "plan.json")
            self.assertEqual(verified.upsert_rows[0]["canonical_url"], canonical_url)

    def test_all_source_variants_reject_resigned_identity_contradictions(self) -> None:
        github = {
            "source_kind": "github_repo", "repo_full_name": "owner/repo",
            "repo_owner": "owner", "repo_name": "repo", "repo_ref": "main",
            "commit_sha": "abc123", "repo_path": "README.md", "language": "markdown",
        }
        cases = [
            ("website", "https://example.com/docs", {}, {}, "title", "other.example", "consistent HTTP"),
            ("github", "https://github.com/owner/repo", github, github, "repo_full_name", "other/repo", "inconsistent"),
            (
                "pdf", "pdf://pdf-notes-abc",
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc"},
                {"source_kind": "pdf", "pdf_filename": "notes.pdf", "pdf_sha256": "abc", "pdf_source_id": "pdf-notes-abc"},
                "source_id", "other", "inconsistent",
            ),
            *[
                (
                    backend, f"{backend}://docs",
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": relation, "database_document_id": "1"},
                    {"source_kind": f"{backend}_relation", "database_backend": backend, "database_source_id": "docs", "database_relation": relation},
                    "database_source_id", "other", "inconsistent",
                )
                for backend, relation in (
                    ("duckdb", "documents"),
                    ("bigquery", "proj.dataset.documents"),
                    ("snowflake", "DB.SCHEMA.DOCUMENTS"),
                )
            ],
        ]
        for name, uri, metadata, summary, field, value, error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(
                    self.build(
                        root / "build", base_url=uri, metadata=metadata,
                        source_summary=summary,
                    ),
                    out,
                )
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                if field == "title":
                    plan["source"][field] = value
                else:
                    plan["source"]["attributes"][field] = value
                plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(plan_path)

    def test_document_source_basename_authority_and_variant_consistency_are_verified(self) -> None:
        metadata = {
            "source_kind": "local_file", "file_filename": "notes.md",
            "file_extension": "md", "file_sha256": "abc", "file_source_id": "file-notes-abc",
        }
        summary = dict(metadata)
        mutations = [
            ("filename", "../notes.md", "safe basename"),
            ("source_id", "other-source", "identity is inconsistent"),
            ("extension", "txt", "extension contradicts"),
            ("filename", "https://user:secret@example.com/notes.md", "credential-bearing URI"),
        ]
        for field, value, error in mutations:
            with self.subTest(field=field, value=value), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(
                    self.build(
                        root / "build", base_url="file://file-notes-abc",
                        metadata=metadata, source_summary=summary,
                    ),
                    out,
                )
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["source"]["attributes"][field] = value
                plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(plan_path)

    def test_resigned_upsert_privacy_identity_and_content_tampering_is_rejected(self) -> None:
        mutations = [
            ("content", "UPDATE upsert_rows SET content='different'", "chunk hash"),
            ("path", "UPDATE upsert_rows SET source_path='/Users/private/secret.md'", "safe relative path"),
            ("identity", f"UPDATE upsert_rows SET row_id='ts_{'f' * 32}', row_id_candidate='ts_{'f' * 32}'", "identity formula"),
            ("empty", "UPDATE upsert_rows SET title=''", "empty or invalid"),
            ("metadata", "", "credential-bearing or provider-connection field"),
            ("metadata_uri", "", "credential-bearing URI"),
        ]
        for name, sql, error in mutations:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    if name == "metadata":
                        connection.execute(
                            "UPDATE upsert_rows SET source_metadata_json=?",
                            [json.dumps({"api_key": "secret"}, sort_keys=True, separators=(",", ":"))],
                        )
                    elif name == "metadata_uri":
                        connection.execute(
                            "UPDATE upsert_rows SET source_metadata_json=?",
                            [json.dumps({"note": "https://user:secret@example.com/private"}, sort_keys=True, separators=(",", ":"))],
                        )
                    else:
                        connection.execute(sql)
                self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

        for tags_json, error in (
            ('[ "docs" ]', "not canonical"),
            ('["z","a"]', "sorted and unique"),
            ('["docs","docs"]', "sorted and unique"),
        ):
            with self.subTest(tags_json=tags_json), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    connection.execute("UPDATE upsert_rows SET tags_json=?", [tags_json])
                if tags_json.startswith('["'):
                    self.resign(out)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

    def test_zero_chunk_first_apply_preserves_page_count_without_false_derivation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts = self.build(root / "build", body="")
            self.assertEqual(artifacts.plan.diff["pages_added"], 1)
            self.assertEqual(artifacts.plan.diff["rows_to_upsert"], 0)
            out = root / "out"
            write_plan_artifacts(artifacts, out)
            verified = verify_plan_artifacts(out / "plan.json")
            self.assertEqual(verified.upsert_rows, ())

    def test_diff_stale_order_and_application_object_tampering_is_rejected(self) -> None:
        for field in (
            "chunks_to_embed", "rows_to_upsert", "stale_rows", "retained_stale_rows",
        ):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["diff"][field] += 1
                plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
                self.resign(out, sync_diff=False)
                with self.assertRaisesRegex(ValueError, "diff counts"):
                    verify_plan_artifacts(plan_path)

        for field in (
            "pages_changed", "pages_unchanged", "pages_removed", "chunks_unchanged",
        ):
            with self.subTest(first_apply_field=field), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                plan_path = out / "plan.json"
                plan = json.loads(plan_path.read_text(encoding="utf-8"))
                plan["diff"][field] = 1
                plan_path.write_text(json.dumps(plan, sort_keys=True), encoding="utf-8")
                self.resign(out, sync_diff=False)
                with self.assertRaisesRegex(ValueError, "first-apply diff counts"):
                    verify_plan_artifacts(plan_path)

        for object_sql, error in [
            ("CREATE VIEW unexpected_view AS SELECT * FROM upsert_rows", "tables/views"),
            ("CREATE MACRO unexpected_macro(x) AS x + 1", "macros/functions"),
        ]:
            with self.subTest(sql=object_sql), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                out = root / "out"
                write_plan_artifacts(self.build(root / "build"), out)
                with duckdb.connect(str(out / "delta.duckdb")) as connection:
                    connection.execute(object_sql)
                with self.assertRaisesRegex(ValueError, error):
                    verify_plan_artifacts(out / "plan.json")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            initial = self.build(root / "initial")
            chunk = initial.manifest.chunks[0]
            stale_one = AppliedStateRow(
                f"ts_{'1' * 32}", "https://example.com/a", "1" * 64, "2" * 64,
                "3" * 64, f"plan_{'1' * 16}", "2026-07-24T00:00:00+00:00",
            )
            stale_two = AppliedStateRow(
                f"ts_{'2' * 32}", "https://example.com/b", "4" * 64, "5" * 64,
                "6" * 64, f"plan_{'2' * 16}", "2026-07-24T00:00:00+00:00",
            )
            state = build_applied_state(
                site_id=initial.manifest.site_id, namespace=initial.manifest.namespace,
                base_url=initial.manifest.base_url, last_plan_id=f"plan_{'3' * 16}",
                last_apply_id="apply_previous", rows=[self.state_row(chunk), stale_one, stale_two],
                updated_at="2026-07-24T00:00:00+00:00",
            )
            out = root / "out"
            write_plan_artifacts(self.build(root / "next", state=state, state_present=True), out)
            with duckdb.connect(str(out / "delta.duckdb")) as connection:
                connection.execute("UPDATE stale_rows SET ordinal=99 WHERE ordinal=0")
                connection.execute("UPDATE stale_rows SET ordinal=0 WHERE ordinal=1")
                connection.execute("UPDATE stale_rows SET ordinal=1 WHERE ordinal=99")
            with self.assertRaisesRegex(ValueError, "canonical sort order"):
                verify_plan_artifacts(out / "plan.json")

            write_plan_artifacts(self.build(root / "again", state=state, state_present=True), out)
            with duckdb.connect(str(out / "delta.duckdb")) as connection:
                connection.execute(
                    "UPDATE stale_rows SET category='retained_stale' WHERE ordinal=0"
                )
            self.resign(out)
            with self.assertRaisesRegex(ValueError, "category/status/reason"):
                verify_plan_artifacts(out / "plan.json")

    def test_plan_identity_ignores_output_directory_time_and_managed_job(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = self.build(root / "first")
            pages = root / "second" / "pages"
            pages.mkdir(parents=True)
            (pages / "page.md").write_text((root / "first/pages/page.md").read_text(encoding="utf-8"), encoding="utf-8")
            second = build_plan_artifacts(
                indexing_plan=process_corpus(pages), base_url="https://example.com/docs",
                out_dir=root / "elsewhere", originating_job_id=f"planjob_{'b' * 32}",
            )

        self.assertEqual(first.plan.artifact_hash, second.plan.artifact_hash)
        self.assertEqual(first.plan.plan_id, second.plan.plan_id)
        self.assertNotEqual(first.plan.created_at, "")
        self.assertEqual(second.plan.originating_job_id, f"planjob_{'b' * 32}")
        self.assertNotIn("originating_job_id", first.plan_dict())
        self.assertEqual(PLAN_SCHEMA_VERSION, 2)
        self.assertEqual(DELTA_SCHEMA_VERSION, 1)


if __name__ == "__main__":
    unittest.main()
