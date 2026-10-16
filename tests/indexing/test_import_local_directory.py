from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

from scripts import import_local_directory as importer


class ImportLocalDirectoryTests(unittest.TestCase):
    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX named pipes")
    def test_reader_rejects_fifo_without_waiting_for_a_writer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            fifo = Path(temporary) / "race.md"
            os.mkfifo(fifo)
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import sys; from pathlib import Path; "
                        "from scripts.import_local_directory import _read_bounded_regular_file; "
                        "assert _read_bounded_regular_file(Path(sys.argv[1]), 100) == ('not_regular', None)"
                    ),
                    str(fifo),
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_creates_deterministic_documents_relation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            (root / "docs").mkdir(parents=True)
            (root / "z.py").write_text("print('z')\n", encoding="utf-8")
            (root / "docs" / "a.md").write_text("# Alpha\n", encoding="utf-8")
            output = base / "documents.duckdb"

            summary = importer.run(root, output)

            self.assertEqual(summary.imported, 2)
            with duckdb.connect(str(output), read_only=True) as connection:
                rows = connection.execute(
                    "SELECT document_id, title, content FROM documents ORDER BY document_id"
                ).fetchall()
            self.assertEqual([row[0] for row in rows], ["docs/a.md", "z.py"])
            self.assertEqual(rows[0][1], "docs/a.md")
            self.assertEqual(rows[0][2], "File: docs/a.md\n\n# Alpha\n")

    def test_builtin_and_requested_exclusions_are_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            root.mkdir()
            fixtures = {
                "keep.md": "keep",
                "skip.txt": "excluded",
                ".env": "TOKEN=secret",
                "secrets.txt": "secret",
                "private.pem": "certificate",
                "image.png": "not text",
                ".hidden/hidden.md": "hidden",
                ".git/config.txt": "git",
                ".buoy-cache/cache.md": "buoy",
                "vendor/vendored.py": "vendor",
                "node_modules/package.js": "node",
                "build/output.txt": "build",
                "dist/output.txt": "dist",
                ".venv/site.py": "venv",
                "__pycache__/cached.py": "cache",
            }
            for relative, text in fixtures.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(text, encoding="utf-8")

            documents, summary = importer.collect_documents(root, excludes=("skip.*",))

            self.assertEqual(
                [document.document_id for document in documents], ["keep.md"]
            )
            self.assertGreater(summary.skipped["hidden_directory"], 0)
            self.assertGreater(summary.skipped["sensitive"], 0)
            self.assertGreater(summary.skipped["ignored_directory"], 0)
            self.assertEqual(summary.skipped["excluded"], 1)
            self.assertEqual(summary.skipped["unsupported_type"], 1)

    def test_include_globs_are_repeatable_and_match_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "src").mkdir()
            (root / "docs" / "guide.md").write_text("guide", encoding="utf-8")
            (root / "src" / "main.py").write_text("main", encoding="utf-8")
            (root / "notes.txt").write_text("notes", encoding="utf-8")

            documents, summary = importer.collect_documents(
                root, includes=("docs/*.md", "src/*.py")
            )

            self.assertEqual(
                [document.document_id for document in documents],
                ["docs/guide.md", "src/main.py"],
            )
            self.assertEqual(summary.skipped["include_mismatch"], 1)

    def test_symlinks_are_never_followed_and_symlink_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            root.mkdir()
            outside = base / "outside.txt"
            outside.write_text("outside secret", encoding="utf-8")
            try:
                (root / "linked.txt").symlink_to(outside)
                (root / "linked-dir").symlink_to(base, target_is_directory=True)
                root_link = base / "root-link"
                root_link.symlink_to(root, target_is_directory=True)
            except (NotImplementedError, OSError):
                self.skipTest("symlinks are unavailable")

            documents, summary = importer.collect_documents(root)

            self.assertEqual(documents, [])
            self.assertEqual(summary.skipped["symlink"], 2)
            with self.assertRaisesRegex(
                importer.LocalDirectoryImportError, "ROOT must not"
            ):
                importer.run(root_link, base / "out.duckdb")

    def test_binary_non_utf8_and_oversized_files_are_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "binary.txt").write_bytes(b"before\x00after")
            (root / "latin.txt").write_bytes(b"caf\xe9")
            (root / "large.txt").write_text("12345", encoding="utf-8")
            (root / "ok.txt").write_text("1234", encoding="utf-8")

            documents, summary = importer.collect_documents(root, max_file_bytes=4)

            self.assertEqual(
                [document.document_id for document in documents], ["ok.txt"]
            )
            self.assertEqual(summary.skipped["binary"], 0)
            # binary.txt is over the four-byte bound and is never decoded.
            self.assertEqual(summary.skipped["oversized"], 2)
            self.assertEqual(summary.skipped["non_utf8"], 1)

    def test_binary_file_within_bound_is_skipped_as_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "binary.txt").write_bytes(b"a\x00b")

            documents, summary = importer.collect_documents(root)

            self.assertEqual(documents, [])
            self.assertEqual(summary.skipped["binary"], 1)

    def test_file_limit_is_deterministic_and_bounds_candidate_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("c.txt", "a.txt", "b.txt"):
                (root / name).write_text(name, encoding="utf-8")

            documents, summary = importer.collect_documents(root, max_files=2)

            self.assertEqual(
                [document.document_id for document in documents], ["a.txt", "b.txt"]
            )
            self.assertEqual(summary.skipped["file_limit"], 1)

    def test_output_must_be_outside_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "readme.md").write_text("hello", encoding="utf-8")

            with self.assertRaisesRegex(
                importer.LocalDirectoryImportError, "outside ROOT"
            ):
                importer.run(root, root / "documents.duckdb")

            self.assertFalse((root / "documents.duckdb").exists())

    def test_existing_output_requires_replace_and_preserves_unrelated_tables(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            root.mkdir()
            (root / "new.md").write_text("new body", encoding="utf-8")
            output = base / "existing.duckdb"
            with duckdb.connect(str(output)) as connection:
                connection.execute(
                    "CREATE TABLE documents AS SELECT 'old' AS document_id, 'old' AS title, 'old' AS content"
                )
                connection.execute("CREATE TABLE unrelated(value INTEGER)")
                connection.execute("INSERT INTO unrelated VALUES (42)")

            with self.assertRaisesRegex(
                importer.LocalDirectoryImportError, "--replace"
            ):
                importer.run(root, output)
            with duckdb.connect(str(output), read_only=True) as connection:
                self.assertEqual(
                    connection.execute("SELECT document_id FROM documents").fetchone(),
                    ("old",),
                )

            importer.run(root, output, replace=True)

            with duckdb.connect(str(output), read_only=True) as connection:
                self.assertEqual(
                    connection.execute("SELECT value FROM unrelated").fetchone(), (42,)
                )
                self.assertEqual(
                    connection.execute("SELECT document_id FROM documents").fetchall(),
                    [("new.md",)],
                )

    def test_failed_replacement_rolls_back_old_table_and_unrelated_data(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            output = base / "existing.duckdb"
            with duckdb.connect(str(output)) as connection:
                connection.execute(
                    "CREATE TABLE documents(document_id VARCHAR, title VARCHAR, content VARCHAR)"
                )
                connection.execute("INSERT INTO documents VALUES ('old', 'old', 'old')")
                connection.execute("CREATE TABLE unrelated(value INTEGER)")
                connection.execute("INSERT INTO unrelated VALUES (7)")

            def fail_after_replacement_starts(connection, documents):
                connection.execute("DROP TABLE documents")
                connection.execute("CREATE TABLE documents(document_id VARCHAR)")
                raise RuntimeError("injected failure")

            with (
                patch.object(
                    importer,
                    "_replace_documents",
                    side_effect=fail_after_replacement_starts,
                ),
                self.assertRaisesRegex(RuntimeError, "injected failure"),
            ):
                importer.write_database(output, [], existed=True)

            with duckdb.connect(str(output), read_only=True) as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT document_id, title, content FROM documents"
                    ).fetchall(),
                    [("old", "old", "old")],
                )
                self.assertEqual(
                    connection.execute("SELECT value FROM unrelated").fetchone(), (7,)
                )

    def test_main_prints_machine_readable_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root = base / "source"
            root.mkdir()
            (root / "readme.md").write_text("hello", encoding="utf-8")
            output = base / "documents.duckdb"
            with patch("builtins.print") as print_mock:
                result = importer.main([str(root), str(output)])

            self.assertEqual(result, 0)
            payload = json.loads(print_mock.call_args.args[0])
            self.assertEqual(payload["imported"], 1)
            self.assertEqual(payload["skipped_total"], 0)


if __name__ == "__main__":
    unittest.main()
