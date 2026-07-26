from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import URLError

from buoy_search.applied_state import AppliedStateRow, build_applied_state, load_applied_state, save_applied_state
from buoy_search.apply import apply_preflight_summary, load_verified_apply_plan
from buoy_search.crawler import CrawlOptions, parse_github_repo_url
from buoy_search.chunker import parse_markdown_file, process_corpus
from buoy_search.plan_artifacts import build_generic_site_row, build_plan_artifacts, verify_plan_artifacts, write_plan_artifacts
from buoy_search.plan_diff import diff_manifest_against_state
from buoy_search.repo_syntax_chunking import RepoSyntaxChunkingError, chunk_source, source_payload
from buoy_search.treatment_token_budget import (
    TreatmentTokenBudgetError,
    exact_token_count,
    load_pinned_tokenizer,
)
from buoy_search.github_repo import (
    GitHubRepoError,
    GitHubRepoMetadata,
    acquire_github_repo,
    build_github_repo_corpus,
    crawl_github_repo_with_plan,
    fetch_github_repo_metadata,
    process_syntax_repo_corpus,
    resolve_github_repo_metadata,
    run_git_stdout,
    validate_repo_chunking_options,
)


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001 - context manager protocol.
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class GitHubRepoAcquisitionTests(unittest.TestCase):
    def test_fetch_metadata_uses_public_github_rest_payload(self) -> None:
        source = parse_github_repo_url("https://github.com/owner/repo")
        assert source is not None

        def fake_urlopen(request, *, timeout):  # noqa: ANN001 - mirrors urllib opener.
            self.assertIn("https://api.github.com/repos/owner/repo", request.full_url)
            self.assertEqual(timeout, 15)
            return FakeResponse(
                {
                    "full_name": "Owner/Repo",
                    "html_url": "https://github.com/Owner/Repo",
                    "clone_url": "https://github.com/Owner/Repo.git",
                    "default_branch": "main",
                    "size": 123,
                    "language": "Python",
                    "private": False,
                }
            )

        metadata = fetch_github_repo_metadata(source, urlopen_func=fake_urlopen)

        self.assertEqual(metadata.owner, "Owner")
        self.assertEqual(metadata.repo, "Repo")
        self.assertEqual(metadata.repo_full_name, "Owner/Repo")
        self.assertEqual(metadata.repo_root_url, "https://github.com/Owner/Repo")
        self.assertEqual(metadata.clone_url, "https://github.com/Owner/Repo.git")
        self.assertEqual(metadata.default_branch, "main")
        self.assertEqual(metadata.size_kb, 123)
        self.assertEqual(metadata.language, "Python")

    def test_metadata_resolution_falls_back_to_git_ls_remote(self) -> None:
        source = parse_github_repo_url("https://github.com/owner/repo")
        assert source is not None
        commands: list[list[str]] = []

        def failing_urlopen(*args, **kwargs):  # noqa: ANN002, ANN003 - fake urllib opener.
            raise URLError("offline")

        def fake_runner(command, **kwargs):  # noqa: ANN001, ANN003 - fake subprocess runner.
            commands.append(command)
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="ref: refs/heads/main\tHEAD\nabc123\tHEAD\n",
                stderr="",
            )

        metadata = resolve_github_repo_metadata(source, urlopen_func=failing_urlopen, runner=fake_runner)

        self.assertEqual(metadata.default_branch, "main")
        self.assertEqual(metadata.clone_url, "https://github.com/owner/repo.git")
        self.assertEqual(commands[0], ["git", "ls-remote", "--symref", "https://github.com/owner/repo.git", "HEAD"])

    def test_acquire_github_repo_shallow_clones_and_records_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(root / "remote")
            out_dir = root / "out"
            source = parse_github_repo_url("https://github.com/owner/repo")
            assert source is not None
            metadata = GitHubRepoMetadata(
                owner="owner",
                repo="repo",
                repo_full_name="owner/repo",
                repo_root_url="https://github.com/owner/repo",
                clone_url=str(remote),
                default_branch="main",
            )

            with patch("buoy_search.github_repo.resolve_github_repo_metadata", return_value=metadata):
                acquisition = acquire_github_repo(source, out_dir)

            expected_sha = subprocess.run(
                ["git", "-C", str(remote), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            self.assertEqual(acquisition.resolved_ref, "main")
            self.assertEqual(acquisition.commit_sha, expected_sha)
            self.assertEqual(acquisition.checkout_dir, out_dir / "repo-checkout")
            self.assertTrue((acquisition.checkout_dir / "README.md").exists())
            self.assertEqual(acquisition.acquisition_strategy, "git-shallow-clone")

    def test_acquire_github_repo_validates_tree_subdirectory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(root / "remote")
            out_dir = root / "out"
            source = parse_github_repo_url("https://github.com/owner/repo/tree/main/missing-docs")
            assert source is not None
            metadata = GitHubRepoMetadata(
                owner="owner",
                repo="repo",
                repo_full_name="owner/repo",
                repo_root_url="https://github.com/owner/repo",
                clone_url=str(remote),
                default_branch="main",
            )

            with patch("buoy_search.github_repo.resolve_github_repo_metadata", return_value=metadata):
                with self.assertRaisesRegex(GitHubRepoError, "subdirectory"):
                    acquire_github_repo(source, out_dir)

    def test_blob_url_acquisition_fails_clearly_until_single_file_ingestion_exists(self) -> None:
        source = parse_github_repo_url("https://github.com/owner/repo/blob/main/src/app.py")
        assert source is not None
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(GitHubRepoError, "single-file repository ingestion is not implemented"):
                acquire_github_repo(source, Path(tmp))

    def test_build_corpus_filters_files_and_writes_parseable_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "README.md": "# Test Repo\n\nUseful docs.\n",
                    "src/app.py": "def hello():\n    return 'world'\n",
                    "docs/private.md": "# Private docs\n",
                    ".10x/evidence/noise.md": "# Internal evidence\n",
                    ".buoy/state/current.txt": "current state\n",
                    ".turbo-search/state/legacy.txt": "legacy state\n",
                    "autoresearch/run.json": "{}\n",
                    "src/buoy_search/data/repo_search_seed_evals.json": "{}\n",
                    "empty.txt": "",
                    "dist/bundle.js": "console.log('generated');\n",
                    "node_modules/pkg/index.js": "module.exports = {};\n",
                    "package-lock.json": "{}\n",
                    "big.txt": "x" * 80,
                    "binary.bin": b"\x00\x01\x02",
                },
            )
            acquisition = acquire_from_local_remote(root, remote)
            pages_dir = root / "pages"

            corpus = build_github_repo_corpus(
                acquisition,
                pages_dir,
                exclude_paths=("docs/private.md",),
                max_file_bytes=50,
            )

            self.assertEqual(corpus.stats.files_discovered, 14)
            self.assertEqual(corpus.stats.files_selected, 2)
            self.assertEqual(corpus.stats.files_skipped_empty, 1)
            self.assertEqual(corpus.stats.files_skipped_binary, 1)
            self.assertEqual(corpus.stats.files_skipped_oversize, 1)
            self.assertEqual(corpus.stats.files_skipped_filtered, 9)
            generated = sorted(pages_dir.glob("*.md"))
            self.assertEqual(len(generated), 2)
            parsed = [parse_markdown_file(path, pages_dir) for path in generated]
            metadata_by_path = {document.metadata["repo_path"]: document for document in parsed}
            self.assertIn("README.md", metadata_by_path)
            self.assertIn("src/app.py", metadata_by_path)
            readme = metadata_by_path["README.md"]
            self.assertEqual(readme.metadata["source_kind"], "github_repo")
            self.assertEqual(readme.metadata["repo_full_name"], "owner/repo")
            self.assertEqual(readme.metadata["repo_ref"], "main")
            self.assertEqual(readme.metadata["fetcher"], "git-shallow-clone")
            self.assertIn("/blob/main/README.md", readme.url)
            code_page = metadata_by_path["src/app.py"]
            self.assertIn("## Lines 1-2", code_page.body)
            self.assertIn("```python", code_page.body)

            plan = process_corpus(pages_dir)
            self.assertEqual(plan.stats.files_error, 0)
            self.assertGreaterEqual(plan.stats.chunks_generated, 2)

    def test_acquired_crlf_python_is_lf_normalized_without_losing_source_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crlf_source = (
                b"import os\r\n"
                b"\r\n"
                b"\fMODULE = 1\r\n"
                b"class Outer:\r\n"
                b"    def inner(self):\r\n"
                b"        return MODULE"
            )
            remote = create_local_git_repo(root / "remote", files={"src/crlf.py": crlf_source})
            acquisition = acquire_from_local_remote(root, remote)

            corpus = build_github_repo_corpus(acquisition, root / "pages")

            repo_file = corpus.selected_files[0]
            expected = "import os\n\n\fMODULE = 1\nclass Outer:\n    def inner(self):\n        return MODULE"
            self.assertIn(b"\r\n", repo_file.absolute_path.read_bytes())
            self.assertFalse(repo_file.absolute_path.read_bytes().endswith(b"\n"))
            self.assertEqual(repo_file.text, expected)
            self.assertNotIn("\r", repo_file.text)
            self.assertFalse(repo_file.text.endswith("\n"))
            for arm in ("fixed-80-python-breadcrumbs", "python-ast"):
                with self.subTest(arm=arm):
                    chunking = chunk_source(repo_file.text, repo_file.repo_path, repo_file.language, arm)
                    self.assertEqual(
                        chunking.lines,
                        ("import os", "", "\fMODULE = 1", "class Outer:", "    def inner(self):", "        return MODULE"),
                    )
                    self.assertEqual(
                        "\n".join(source_payload(chunking, item) for item in chunking.ranges),
                        expected,
                    )
                    self.assertIn("Outer > inner", {breadcrumb for item in chunking.ranges for breadcrumb in item.breadcrumbs})
            ast_chunking = chunk_source(repo_file.text, repo_file.repo_path, repo_file.language, "python-ast")
            self.assertEqual(
                [(item.start, item.end, item.breadcrumbs) for item in ast_chunking.ranges],
                [(1, 3, ()), (4, 4, ("Outer",)), (5, 6, ("Outer > inner",))],
            )

    def test_build_corpus_can_include_large_file_with_search_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = "\n".join(
                [
                    "class AlphaClass:",
                    "    pass",
                    "",
                    "def helper_function():",
                    "    return AlphaClass()",
                ]
                + ["value = 1"] * 20
            )
            remote = create_local_git_repo(root / "remote", files={"README.md": "# Docs\n", "src/large_module.py": source})
            acquisition = acquire_from_local_remote(root, remote)

            default_corpus = build_github_repo_corpus(acquisition, root / "default-pages", max_file_bytes=50)
            metadata_corpus = build_github_repo_corpus(
                acquisition,
                root / "metadata-pages",
                max_file_bytes=2000,
                code_chunk_lines=4,
                include_search_metadata=True,
            )

            self.assertEqual(default_corpus.stats.files_skipped_oversize, 1)
            self.assertEqual(metadata_corpus.stats.files_selected, 2)
            generated = next(
                path
                for path in (root / "metadata-pages").glob("*.md")
                if parse_markdown_file(path, root / "metadata-pages").metadata["repo_path"] == "src/large_module.py"
            )
            body = parse_markdown_file(generated, root / "metadata-pages").body
            self.assertIn("Search metadata:", body)
            self.assertIn("Path tokens: src large module", body)
            self.assertIn("Symbols: AlphaClass, helper_function", body)
            self.assertIn("Symbol tokens: alpha class helper function", body)
            self.assertIn("Symbol breadcrumbs: AlphaClass, helper_function", body)

    def test_build_corpus_can_write_separate_file_cards(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "README.md": "# Docs\n",
                    "src/app.py": "class App:\n    pass\n\ndef run_app():\n    return App()\n",
                },
            )
            acquisition = acquire_from_local_remote(root, remote)

            corpus = build_github_repo_corpus(acquisition, root / "pages", include_file_cards=True)

            self.assertEqual(corpus.stats.files_selected, 2)
            self.assertEqual(corpus.stats.file_card_pages_generated, 2)
            generated = sorted((root / "pages").glob("*.md"))
            self.assertEqual(len(generated), 4)
            documents = [parse_markdown_file(path, root / "pages") for path in generated]
            card = next(document for document in documents if document.metadata.get("repo_page_kind") == "file_card" and document.metadata["repo_path"] == "src/app.py")
            source_page = next(document for document in documents if document.metadata.get("repo_page_kind") == "source" and document.metadata["repo_path"] == "src/app.py")
            self.assertEqual(card.title, "src/app.py file metadata")
            self.assertEqual(card.metadata["source_kind"], "github_repo")
            self.assertEqual(card.metadata["repo_full_name"], "owner/repo")
            self.assertIn("# File metadata: src/app.py", card.body)
            self.assertIn("Path tokens: src app", card.body)
            self.assertIn("Symbols: App, run_app", card.body)
            self.assertIn("Symbol tokens: app run", card.body)
            self.assertNotIn("Search metadata:", source_page.body)

            plan = process_corpus(root / "pages")
            self.assertEqual(plan.stats.files_error, 0)
            self.assertGreaterEqual(plan.stats.chunks_generated, 4)

    def test_build_corpus_can_write_file_cards_for_oversize_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            large_source = "class HugeApp:\n    pass\n\ndef run_huge_app():\n    return HugeApp()\n" + "# filler\n" * 20
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "README.md": "# Docs\n",
                    "src/huge_app.py": large_source,
                },
            )
            acquisition = acquire_from_local_remote(root, remote)

            corpus = build_github_repo_corpus(
                acquisition,
                root / "pages",
                max_file_bytes=40,
                include_oversize_file_cards=True,
            )

            self.assertEqual(corpus.stats.files_selected, 1)
            self.assertEqual(corpus.stats.files_skipped_oversize, 1)
            self.assertEqual(corpus.stats.file_card_pages_generated, 1)
            generated = sorted((root / "pages").glob("*.md"))
            self.assertEqual(len(generated), 2)
            documents = [parse_markdown_file(path, root / "pages") for path in generated]
            card = next(document for document in documents if document.metadata.get("repo_page_kind") == "oversize_file_card")
            self.assertEqual(card.title, "src/huge_app.py file metadata")
            self.assertEqual(card.metadata["repo_path"], "src/huge_app.py")
            self.assertIn("Path tokens: src huge app", card.body)
            self.assertIn("Symbols: HugeApp, run_huge_app", card.body)
            self.assertNotIn("```python", card.body)

    def test_build_corpus_honors_repo_subdir_and_max_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "docs/a.md": "# A\n",
                    "docs/b.md": "# B\n",
                    "src/app.py": "print('ignored')\n",
                },
            )
            source = parse_github_repo_url("https://github.com/owner/repo/tree/main/docs")
            assert source is not None
            metadata = GitHubRepoMetadata(
                owner="owner",
                repo="repo",
                repo_full_name="owner/repo",
                repo_root_url="https://github.com/owner/repo",
                clone_url=str(remote),
                default_branch="main",
            )
            with patch("buoy_search.github_repo.resolve_github_repo_metadata", return_value=metadata):
                acquisition = acquire_github_repo(source, root / "out")

            corpus = build_github_repo_corpus(acquisition, root / "pages", max_files=1)

            self.assertEqual(corpus.stats.files_selected, 1)
            self.assertEqual(corpus.stats.files_skipped_filtered, 1)
            self.assertEqual(corpus.stats.files_skipped_limit, 1)
            self.assertTrue(corpus.stats.limit_reached)
            self.assertTrue(corpus.selected_files[0].repo_path.startswith("docs/"))

    def test_build_corpus_user_include_can_opt_in_default_filtered_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(root / "remote", files={"package-lock.json": "{}\n"})
            acquisition = acquire_from_local_remote(root, remote)

            corpus = build_github_repo_corpus(
                acquisition,
                root / "pages",
                include_paths=("package-lock.json",),
            )

            self.assertEqual(corpus.stats.files_selected, 1)
            self.assertEqual(corpus.selected_files[0].repo_path, "package-lock.json")

    def test_plan_artifacts_propagate_github_source_metadata_to_chunks_and_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts, _acquisition = build_github_plan_artifacts(root, {"src/app.py": "def hello():\n    return 'world'\n"})

            chunk = artifacts.manifest.chunks[0]
            row = build_generic_site_row(chunk, [0.1, 0.2], plan_id="plan_test", applied_at="2026-06-25T00:00:00+00:00")

            self.assertEqual(chunk.source_metadata["source_kind"], "github_repo")
            self.assertEqual(chunk.source_metadata["repo_full_name"], "owner/repo")
            self.assertEqual(chunk.source_metadata["repo_path"], "src/app.py")
            self.assertEqual(chunk.source_metadata["language"], "python")
            self.assertEqual(row["source_kind"], "github_repo")
            self.assertEqual(row["repo_full_name"], "owner/repo")
            self.assertEqual(row["repo_path"], "src/app.py")
            self.assertEqual(row["language"], "python")

    def test_github_plan_diff_reports_unchanged_changed_and_stale_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            original, _ = build_github_plan_artifacts(
                root / "original",
                {
                    "README.md": "# Docs\n\nStable docs.\n",
                    "src/app.py": "def hello():\n    return 'world'\n",
                },
                state_root=state_root,
            )
            applied_at = "2026-06-25T00:00:00+00:00"
            save_applied_state(
                build_applied_state(
                    site_id=original.manifest.site_id,
                    namespace=original.manifest.namespace,
                    base_url=original.manifest.base_url,
                    last_plan_id="plan_original",
                    last_apply_id="apply_original",
                    rows=[
                        AppliedStateRow(
                            row_id=chunk.row_id,
                            canonical_url=chunk.canonical_url,
                            page_hash=chunk.page_hash,
                            chunk_hash=chunk.chunk_hash,
                            embedding_text_hash=chunk.embedding_text_hash,
                            plan_id="plan_original",
                            applied_at=applied_at,
                        )
                        for chunk in original.manifest.chunks
                    ],
                    updated_at=applied_at,
                ),
                state_root=state_root,
            )
            state = load_applied_state(
                site_id=original.manifest.site_id,
                namespace=original.manifest.namespace,
                base_url=original.manifest.base_url,
                state_root=state_root,
            )
            same, _ = build_github_plan_artifacts(
                root / "same",
                {
                    "README.md": "# Docs\n\nStable docs.\n",
                    "src/app.py": "def hello():\n    return 'world'\n",
                },
                state_root=state_root,
            )
            changed_and_removed, _ = build_github_plan_artifacts(
                root / "changed",
                {"README.md": "# Docs\n\nChanged docs.\n"},
                state_root=state_root,
            )

            same_diff = diff_manifest_against_state(same.manifest, state)
            changed_diff = diff_manifest_against_state(changed_and_removed.manifest, state)

            self.assertEqual(same_diff.summary_dict()["rows_to_upsert"], 0)
            self.assertEqual(same_diff.summary_dict()["chunks_unchanged"], len(same.manifest.chunks))
            self.assertGreater(changed_diff.summary_dict()["rows_to_upsert"], 0)
            self.assertGreater(changed_diff.summary_dict()["stale_rows"], 0)

    def test_compact_artifacts_verify_generated_github_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifacts, _ = build_github_plan_artifacts(
                root,
                {"README.md": "# Docs\n\nUseful docs.\n"},
                state_root=root / "state",
            )
            write_plan_artifacts(artifacts, root / "plan")

            verified = verify_plan_artifacts(root / "plan" / "plan.json")

            self.assertEqual(verified.plan["namespace"], "github-owner-repo-v1")
            self.assertEqual(verified.plan["source"]["kind"], "github_repo")
            self.assertEqual(verified.plan["source"]["attributes"]["repo_full_name"], "owner/repo")
            self.assertEqual(len(verified.upsert_rows), len(artifacts.manifest.chunks))
            self.assertEqual(verified.stale_rows, ())

    def test_explicit_current_default_matches_no_arm_pages_chunks_ids_and_citations(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_text = "\n".join(["def long_function():"] + [f"    value_{index} = {index}" for index in range(120)])
            remote = create_local_git_repo(root / "remote", files={"src/app.py": source_text})
            acquisition = acquire_from_local_remote(root, remote)
            source = acquisition.source
            default_options = CrawlOptions(base_url=source.base_url, out_dir=root / "default")
            control_options = CrawlOptions(
                base_url=source.base_url,
                out_dir=root / "control",
                repo_chunking_arm="current-default",
            )

            with patch("buoy_search.github_repo.acquire_github_repo", return_value=acquisition):
                default = crawl_github_repo_with_plan(source, default_options)
                control = crawl_github_repo_with_plan(source, control_options)

            self.assertEqual(default.indexing_plan.chunks, control.indexing_plan.chunks)
            self.assertNotIn("repo_chunking_arm", default.summary)
            self.assertEqual(control.summary["repo_chunking_arm"], "current-default")
            self.assertEqual(control.summary["repo_header_chunks"], 1)
            self.assertGreater(control.summary["repo_source_chunks"], 0)
            default_page = parse_markdown_file(next((root / "default/pages").glob("*.md")), root / "default/pages")
            control_page = parse_markdown_file(next((root / "control/pages").glob("*.md")), root / "control/pages")
            self.assertEqual(default_page.normalized_body, control_page.normalized_body)
            self.assertEqual(default_page.source_hash, control_page.source_hash)
            self.assertTrue(all(chunk.section_path.startswith("src/app.py") for chunk in control.indexing_plan.chunks))

    def test_explicit_current_default_fails_if_chunk_cap_omits_later_code_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "a.py": "value = 'first'\n",
                    "b.py": "value = 'second'\n",
                },
            )
            acquisition = acquire_from_local_remote(root, remote)
            options = CrawlOptions(
                base_url=acquisition.source.base_url,
                out_dir=root / "control",
                max_chunks=2,
                repo_chunking_arm="current-default",
            )

            with patch("buoy_search.github_repo.acquire_github_repo", return_value=acquisition):
                with self.assertRaisesRegex(
                    RepoSyntaxChunkingError,
                    r"--max-chunks omitted part or all of b\.py",
                ):
                    crawl_github_repo_with_plan(acquisition.source, options)

    def test_python_aware_arms_emit_identical_header_and_exact_isolated_source_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            python_source = "\n".join(
                ["MARKER = '```'", "class App:", "    def run(self):"]
                + [f"        value_{index} = {index}" for index in range(79)]
            )
            javascript_source = "const value = 1;\n"
            remote = create_local_git_repo(
                root / "remote",
                files={
                    "README.md": "# Docs\n\nStable prose.\n",
                    "src/app.py": python_source,
                    "src/app.js": javascript_source,
                },
            )
            acquisition = acquire_from_local_remote(root, remote)
            corpus = build_github_repo_corpus(acquisition, root / "pages")
            control = process_corpus(corpus.pages_dir)
            fixed = process_syntax_repo_corpus(
                corpus,
                arm="fixed-80-python-breadcrumbs",
                limit_chunks=100,
                target_tokens=300,
                overlap_sentences=2,
            )
            fixed_counts = (
                corpus.stats.repo_header_chunks,
                corpus.stats.repo_source_chunks,
                corpus.stats.python_parse_fallbacks,
                corpus.stats.non_python_fallbacks,
            )
            corpus.stats.repo_header_chunks = 0
            corpus.stats.repo_source_chunks = 0
            corpus.stats.python_parse_fallbacks = 0
            corpus.stats.non_python_fallbacks = 0
            syntax = process_syntax_repo_corpus(
                corpus,
                arm="python-ast",
                limit_chunks=100,
                target_tokens=300,
                overlap_sentences=2,
            )

            blob_url = next(item.blob_url for item in corpus.selected_files if item.repo_path == "src/app.py")
            control_header = next(
                chunk
                for chunk in control.chunks
                if chunk.url == blob_url and chunk.section_path == "src/app.py"
            )
            for plan in (fixed, syntax):
                app_chunks = [chunk for chunk in plan.chunks if chunk.url == blob_url]
                self.assertEqual(app_chunks[0], control_header)
                source_chunks = app_chunks[1:]
                self.assertTrue(source_chunks)
                self.assertTrue(all(chunk.url == blob_url for chunk in source_chunks))
                ranges = [
                    tuple(map(int, chunk.section_path.rsplit("Lines ", 1)[1].split("-")))
                    for chunk in source_chunks
                ]
                self.assertEqual(ranges[0][0], 1)
                self.assertEqual(ranges[-1][1], 82)
                self.assertTrue(all(end - start + 1 <= 80 for start, end in ranges))
                self.assertTrue(all(right[0] == left[1] + 1 for left, right in zip(ranges, ranges[1:])))
                reconstructed: list[str] = []
                for chunk, (start, end) in zip(source_chunks, ranges):
                    fenced = chunk.content.splitlines()
                    opening = next(index for index, line in enumerate(fenced) if line.startswith("````"))
                    self.assertEqual(fenced[opening], "````python")
                    reconstructed.extend(fenced[opening + 1 : -1])
                    self.assertEqual(fenced[opening + 1 : -1], python_source.split("\n")[start - 1 : end])
                self.assertEqual(reconstructed, python_source.split("\n"))

            self.assertEqual(fixed_counts, (2, 3, 0, 1))
            self.assertEqual(corpus.stats.repo_header_chunks, 2)
            self.assertEqual(corpus.stats.python_parse_fallbacks, 0)
            self.assertEqual(corpus.stats.non_python_fallbacks, 1)
            artifacts = build_plan_artifacts(
                indexing_plan=syntax,
                base_url=acquisition.source.repo_root_url,
                out_dir=root / "plan",
                crawl_options={"repo_chunking_arm": "python-ast"},
            )
            app_rows = [row for row in artifacts.manifest.chunks if row.canonical_url == blob_url]
            self.assertEqual(len(app_rows), len([chunk for chunk in syntax.chunks if chunk.url == blob_url]))
            self.assertEqual(app_rows[0].section_path, "src/app.py")
            self.assertTrue(all(row.canonical_url == blob_url for row in app_rows[1:]))
            self.assertTrue(all(" > Lines " in row.section_path for row in app_rows[1:]))
            readme_url = next(item.blob_url for item in corpus.selected_files if item.repo_path == "README.md")
            self.assertEqual(
                [chunk for chunk in fixed.chunks if chunk.url == readme_url],
                [chunk for chunk in control.chunks if chunk.url == readme_url],
            )

    def test_malformed_python_fallback_is_sanitized_and_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(root / "remote", files={"broken.py": "def broken(:\n    secret = 'do not expose'\n"})
            acquisition = acquire_from_local_remote(root, remote)
            corpus = build_github_repo_corpus(acquisition, root / "pages")

            plan = process_syntax_repo_corpus(
                corpus,
                arm="python-ast",
                limit_chunks=10,
                target_tokens=300,
                overlap_sentences=99,
            )

            self.assertEqual(corpus.stats.python_parse_fallbacks, 1)
            self.assertEqual(corpus.stats.non_python_fallbacks, 0)
            self.assertEqual(corpus.stats.repo_header_chunks, 1)
            self.assertEqual(corpus.stats.repo_source_chunks, 1)
            self.assertNotIn("Symbol breadcrumbs:", plan.chunks[1].content)
            self.assertEqual(plan.chunks[1].section_path, "broken.py > Lines 1-2")

    def test_token_budget_subdivision_has_golden_boundaries_counts_coverage_and_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_lines = ["def owner():"] + [
                f"    value_{index} = \"{' '.join(['alpha'] * 20)}\""
                for index in range(79)
            ]
            source_text = "\n".join(source_lines)
            remote = create_local_git_repo(root / "remote", files={"owner.py": source_text})
            acquisition = acquire_from_local_remote(root, remote)
            corpus = build_github_repo_corpus(acquisition, root / "pages")

            first = process_syntax_repo_corpus(
                corpus,
                arm="fixed-80-python-breadcrumbs",
                limit_chunks=100,
                target_tokens=300,
                overlap_sentences=2,
            )
            corpus.stats.repo_header_chunks = 0
            corpus.stats.repo_source_chunks = 0
            second = process_syntax_repo_corpus(
                corpus,
                arm="fixed-80-python-breadcrumbs",
                limit_chunks=100,
                target_tokens=300,
                overlap_sentences=2,
            )

            self.assertEqual(first.chunks, second.chunks)
            source_chunks = first.chunks[1:]
            self.assertEqual(
                [chunk.section_path for chunk in source_chunks],
                [
                    "owner.py > Lines 1-19",
                    "owner.py > Lines 20-37",
                    "owner.py > Lines 38-55",
                    "owner.py > Lines 56-73",
                    "owner.py > Lines 74-80",
                ],
            )
            self.assertEqual([chunk.chunk_index for chunk in source_chunks], [1, 2, 3, 4, 5])
            tokenizer = load_pinned_tokenizer()
            self.assertEqual(
                [exact_token_count(tokenizer, chunk.embedding_text) for chunk in source_chunks],
                [506, 501, 501, 501, 215],
            )
            self.assertTrue(all(chunk.content.startswith("Symbol breadcrumbs: owner\n\n") for chunk in source_chunks))
            reconstructed: list[str] = []
            for chunk in source_chunks:
                payload = chunk.content.split("```python\n", 1)[1].rsplit("\n```", 1)[0]
                reconstructed.extend(payload.split("\n"))
            self.assertEqual(reconstructed, source_lines)

            first_rows = build_plan_artifacts(
                indexing_plan=first,
                base_url=acquisition.source.repo_root_url,
                out_dir=root / "first-plan",
                crawl_options={"repo_chunking_arm": "fixed-80-python-breadcrumbs"},
            ).manifest.chunks
            second_rows = build_plan_artifacts(
                indexing_plan=second,
                base_url=acquisition.source.repo_root_url,
                out_dir=root / "second-plan",
                crawl_options={"repo_chunking_arm": "fixed-80-python-breadcrumbs"},
            ).manifest.chunks
            self.assertEqual(
                [(row.row_id, row.section_path, row.content) for row in first_rows],
                [(row.row_id, row.section_path, row.content) for row in second_rows],
            )

    def test_unsplittable_513_token_line_aborts_complete_plan_with_sanitized_identity(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            secret_line = " ".join(["alpha"] * 487)
            remote = create_local_git_repo(root / "remote", files={"huge.py": secret_line})
            acquisition = acquire_from_local_remote(root, remote)
            corpus = build_github_repo_corpus(acquisition, root / "pages")

            with self.assertRaises(TreatmentTokenBudgetError) as raised:
                process_syntax_repo_corpus(
                    corpus,
                    arm="python-ast",
                    limit_chunks=10,
                    target_tokens=300,
                    overlap_sentences=2,
                )

            message = str(raised.exception)
            self.assertIn("repository=owner/repo", message)
            self.assertIn("arm=python-ast", message)
            self.assertIn("path=huge.py", message)
            self.assertIn("line=1 tokens=513", message)
            self.assertIn("max=512", message)
            self.assertNotIn("alpha", message)
            self.assertFalse((root / "plan.json").exists())
            self.assertFalse((root / "manifest.json").exists())
            self.assertFalse((root / "chunks.jsonl").exists())

    def test_header_and_prose_overages_are_independent_fail_closed_gates(self) -> None:
        class SelectiveTokenizer:
            model_max_length = 512

            def __init__(self, marker: str) -> None:
                self.marker = marker

            def __call__(self, text: str, **_kwargs: object) -> dict[str, object]:
                return {"length": [513 if self.marker in text else 10]}

        cases = (
            ({"app.py": "value = 1"}, "Repository file:", "class=header"),
            ({"README.md": "# Docs\n\nprose marker"}, "prose marker", "class=prose"),
        )
        for files, marker, expected_class in cases:
            with self.subTest(row_class=expected_class), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                remote = create_local_git_repo(root / "remote", files=files)
                acquisition = acquire_from_local_remote(root, remote)
                corpus = build_github_repo_corpus(acquisition, root / "pages")
                with patch(
                    "buoy_search.github_repo.load_pinned_tokenizer",
                    return_value=SelectiveTokenizer(marker),
                ):
                    with self.assertRaisesRegex(TreatmentTokenBudgetError, expected_class):
                        process_syntax_repo_corpus(
                            corpus,
                            arm="python-ast",
                            limit_chunks=10,
                            target_tokens=300,
                            overlap_sentences=2,
                        )

    def test_python_aware_plan_refuses_partial_max_chunk_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            remote = create_local_git_repo(root / "remote", files={"app.py": "\n".join(["value = 1"] * 81)})
            acquisition = acquire_from_local_remote(root, remote)
            corpus = build_github_repo_corpus(acquisition, root / "pages")

            with self.assertRaisesRegex(RepoSyntaxChunkingError, "refusing partial source coverage"):
                process_syntax_repo_corpus(
                    corpus,
                    arm="python-ast",
                    limit_chunks=2,
                    target_tokens=300,
                    overlap_sentences=2,
                )

    def test_repo_chunking_arm_rejects_metadata_and_cards_before_acquisition(self) -> None:
        for field_name in ("repo_search_metadata", "repo_file_cards", "repo_oversize_file_cards"):
            with self.subTest(field_name=field_name):
                options = CrawlOptions(
                    base_url="https://github.com/owner/repo",
                    out_dir=Path("unused"),
                    repo_chunking_arm="python-ast",
                    **{field_name: True},
                )
                with self.assertRaisesRegex(GitHubRepoError, "cannot be combined"):
                    validate_repo_chunking_options(options)

    def test_git_missing_error_is_user_friendly(self) -> None:
        def missing_runner(command, **kwargs):  # noqa: ANN001, ANN003 - fake subprocess runner.
            raise FileNotFoundError("git")

        with self.assertRaisesRegex(GitHubRepoError, "git executable was not found"):
            run_git_stdout(["git", "status"], runner=missing_runner, purpose="check git")


def create_local_git_repo(path: Path, files: dict[str, str | bytes] | None = None) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(path)], check=True, capture_output=True, text=True)
    subprocess.run(["git", "-C", str(path), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "Test User"], check=True)
    for relative_path, content in (files or {"README.md": "# Test Repo\n\nUseful docs.\n"}).items():
        destination = path / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            destination.write_bytes(content)
        else:
            destination.write_text(content, encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", "-f", "."], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-m", "initial"], check=True, capture_output=True, text=True)
    return path


def acquire_from_local_remote(root: Path, remote: Path):
    source = parse_github_repo_url("https://github.com/owner/repo")
    assert source is not None
    metadata = GitHubRepoMetadata(
        owner="owner",
        repo="repo",
        repo_full_name="owner/repo",
        repo_root_url="https://github.com/owner/repo",
        clone_url=str(remote),
        default_branch="main",
    )
    with patch("buoy_search.github_repo.resolve_github_repo_metadata", return_value=metadata):
        return acquire_github_repo(source, root / "out")


def build_github_plan_artifacts(root: Path, files: dict[str, str | bytes], *, state_root: Path | None = None):
    remote = create_local_git_repo(root / "remote", files=files)
    acquisition = acquire_from_local_remote(root, remote)
    corpus = build_github_repo_corpus(acquisition, root / "pages")
    indexing_plan = process_corpus(corpus.pages_dir)
    artifacts = build_plan_artifacts(
        indexing_plan=indexing_plan,
        base_url=acquisition.source.repo_root_url,
        out_dir=root / "plan",
        state_root=state_root or root / "state",
    )
    return artifacts, acquisition


if __name__ == "__main__":
    unittest.main()
