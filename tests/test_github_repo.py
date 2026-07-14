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
from buoy_search.crawler import parse_github_repo_url
from buoy_search.chunker import parse_markdown_file, process_corpus
from buoy_search.plan_artifacts import build_generic_site_row, build_plan_artifacts, write_plan_artifacts
from buoy_search.plan_diff import diff_manifest_against_state
from buoy_search.github_repo import (
    GitHubRepoError,
    GitHubRepoMetadata,
    acquire_github_repo,
    build_github_repo_corpus,
    fetch_github_repo_metadata,
    resolve_github_repo_metadata,
    run_git_stdout,
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

    def test_apply_preflight_accepts_generated_github_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state_root = root / "state"
            artifacts, _ = build_github_plan_artifacts(
                root,
                {"README.md": "# Docs\n\nUseful docs.\n"},
                state_root=state_root,
            )
            write_plan_artifacts(artifacts, root / "plan")

            verified = load_verified_apply_plan(
                plan_path=root / "plan" / "plan.json",
                namespace=None,
                state_root=state_root,
            )
            summary = apply_preflight_summary(verified, namespace=verified.manifest.namespace)

            self.assertEqual(summary["namespace"], "github-owner-repo-v1")
            self.assertEqual(summary["rows_to_upsert"], len(artifacts.manifest.chunks))
            self.assertFalse(summary["api_calls_occurred"])
            self.assertFalse(summary["state_updated"])

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
