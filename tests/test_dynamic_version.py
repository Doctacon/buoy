from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from packaging.version import Version

from scripts import release_checks


ROOT = Path(__file__).resolve().parents[1]
VERSION_ASSIGNMENT = re.compile(
    r'^__version__\s*=\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE
)


def run(
    *args: str, cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise AssertionError(
            f"command failed ({completed.returncode}): {' '.join(args)}\n"
            f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        )
    return completed


def clone_source(parent: Path) -> Path:
    source = parent / "source"
    run("git", "clone", "--quiet", "--no-hardlinks", str(ROOT), str(source), cwd=parent)
    run("git", "checkout", "--quiet", "--detach", "HEAD", cwd=source)
    return source


def create_empty_post_tag_commit(source: Path) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_AUTHOR_NAME": "Buoy version test",
            "GIT_AUTHOR_EMAIL": "buoy-version-test@example.invalid",
            "GIT_AUTHOR_DATE": "2020-01-02T03:04:05+00:00",
            "GIT_COMMITTER_NAME": "Buoy version test",
            "GIT_COMMITTER_EMAIL": "buoy-version-test@example.invalid",
            "GIT_COMMITTER_DATE": "2020-01-02T03:04:05+00:00",
        }
    )
    run(
        "git",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--quiet",
        "--no-verify",
        "--allow-empty",
        "--message",
        "test: controlled post-tag commit",
        cwd=source,
        env=environment,
    )


def create_annotated_tag(source: Path, tag: str) -> None:
    environment = os.environ.copy()
    environment.update(
        {
            "GIT_COMMITTER_NAME": "Buoy version test",
            "GIT_COMMITTER_EMAIL": "buoy-version-test@example.invalid",
            "GIT_COMMITTER_DATE": "2020-01-02T03:05:06+00:00",
        }
    )
    run(
        "git",
        "-c",
        "tag.gpgSign=false",
        "tag",
        "--annotate",
        tag,
        "--message",
        f"test: {tag}",
        cwd=source,
        env=environment,
    )


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def venv_buoy(venv: Path) -> Path:
    return venv / ("Scripts/buoy.exe" if os.name == "nt" else "bin/buoy")


def installed_versions(python: Path, cwd: Path) -> dict[str, str]:
    completed = run(
        str(python),
        "-c",
        (
            "import importlib.metadata, json, buoy_search; "
            "print(json.dumps({'metadata': importlib.metadata.version('buoy-search'), "
            "'module': buoy_search.__version__}))"
        ),
        cwd=cwd,
    )
    return json.loads(completed.stdout)


class DynamicVersionTests(unittest.TestCase):
    def test_clean_editable_install_derives_development_version_from_vcs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = clone_source(root)
            create_empty_post_tag_commit(source)
            commit = run("git", "rev-parse", "--short", "HEAD", cwd=source).stdout.strip()
            venv = root / "venv"
            run(
                "uv",
                "venv",
                "--python",
                sys.executable,
                "--system-site-packages",
                str(venv),
                cwd=root,
            )
            environment = os.environ.copy()
            environment.pop("SETUPTOOLS_SCM_PRETEND_VERSION", None)
            environment.pop(
                "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH",
                None,
            )
            run(
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_python(venv)),
                "--editable",
                str(source),
                cwd=root,
                env=environment,
            )

            versions = installed_versions(venv_python(venv), root)
            parsed = Version(versions["metadata"])
            self.assertTrue(parsed.is_devrelease, versions)
            self.assertIn(f"g{commit}", versions["metadata"])
            self.assertEqual(versions["module"], versions["metadata"])
            self.assertEqual(
                run(str(venv_buoy(venv)), "--version", cwd=root).stdout.strip(),
                f"buoy {versions['metadata']}",
            )

    def test_exact_annotated_tag_derives_stable_version(self) -> None:
        target = "9.8.7"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = clone_source(root)
            create_empty_post_tag_commit(source)
            create_annotated_tag(source, f"v{target}")
            self.assertEqual(
                run(
                    "git",
                    "cat-file",
                    "-t",
                    f"refs/tags/v{target}",
                    cwd=source,
                ).stdout.strip(),
                "tag",
            )

            venv = root / "venv"
            run(
                "uv",
                "venv",
                "--python",
                sys.executable,
                "--system-site-packages",
                str(venv),
                cwd=root,
            )
            environment = os.environ.copy()
            environment.pop("SETUPTOOLS_SCM_PRETEND_VERSION", None)
            environment.pop(
                "SETUPTOOLS_SCM_PRETEND_VERSION_FOR_BUOY_SEARCH",
                None,
            )
            run(
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_python(venv)),
                "--editable",
                str(source),
                cwd=root,
                env=environment,
            )

            self.assertEqual(
                installed_versions(venv_python(venv), root),
                {"metadata": target, "module": target},
            )
            self.assertEqual(
                run(str(venv_buoy(venv)), "--version", cwd=root).stdout.strip(),
                f"buoy {target}",
            )

    def test_exact_override_agrees_across_artifacts_install_module_and_cli(self) -> None:
        target = "0.4.1"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = clone_source(root)
            dist = root / "dist"
            environment = os.environ.copy()
            environment["SETUPTOOLS_SCM_PRETEND_VERSION"] = target
            run("uv", "build", "--out-dir", str(dist), cwd=source, env=environment)

            wheel = dist / f"buoy_search-{target}-py3-none-any.whl"
            sdist = dist / f"buoy_search-{target}.tar.gz"
            self.assertEqual(
                {path.name for path in dist.iterdir() if not path.name.startswith(".")},
                {wheel.name, sdist.name},
            )
            with zipfile.ZipFile(wheel) as archive:
                wheel_metadata = archive.read(
                    f"buoy_search-{target}.dist-info/METADATA"
                ).decode()
                wheel_generated = archive.read("buoy_search/_version.py").decode()
            with tarfile.open(sdist) as archive:
                prefix = f"buoy_search-{target}"
                sdist_metadata = archive.extractfile(f"{prefix}/PKG-INFO")
                sdist_generated = archive.extractfile(
                    f"{prefix}/src/buoy_search/_version.py"
                )
                assert sdist_metadata is not None
                assert sdist_generated is not None
                sdist_metadata_text = sdist_metadata.read().decode()
                sdist_generated_text = sdist_generated.read().decode()
            for metadata in (wheel_metadata, sdist_metadata_text):
                self.assertIn(f"Version: {target}\n", metadata)
            for generated in (wheel_generated, sdist_generated_text):
                match = VERSION_ASSIGNMENT.search(generated)
                self.assertIsNotNone(match, generated)
                self.assertEqual(match.group(1), target)

            venv = root / "venv"
            run(
                "uv",
                "venv",
                "--python",
                sys.executable,
                "--system-site-packages",
                str(venv),
                cwd=root,
            )
            run(
                "uv",
                "pip",
                "install",
                "--python",
                str(venv_python(venv)),
                str(wheel),
                cwd=root,
            )
            self.assertEqual(
                installed_versions(venv_python(venv), root),
                {"metadata": target, "module": target},
            )
            self.assertEqual(
                run(str(venv_buoy(venv)), "--version", cwd=root).stdout.strip(),
                f"buoy {target}",
            )

    def test_legacy_checker_requires_override_and_rejects_stale_version(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "src" / "buoy_search"
            package.mkdir(parents=True)
            (root / "pyproject.toml").write_text(
                '[project]\nname = "buoy-search"\ndynamic = ["version"]\n'
            )
            (package / "__init__.py").write_text("from ._version import __version__\n")
            (package / "_version.py").write_text(
                '__version__ = version = "0.4.1"\n'
            )
            with patch.object(release_checks, "ROOT", root):
                with patch.dict(os.environ, {}, clear=True):
                    with self.assertRaisesRegex(
                        ValueError, "requires SETUPTOOLS_SCM_PRETEND_VERSION"
                    ):
                        release_checks.verify_tag("v0.4.1")
                with patch.dict(
                    os.environ,
                    {"SETUPTOOLS_SCM_PRETEND_VERSION": "0.4.2"},
                    clear=True,
                ):
                    with self.assertRaisesRegex(ValueError, "package version mismatch"):
                        release_checks.verify_tag("v0.4.2")
                with patch.dict(
                    os.environ,
                    {"SETUPTOOLS_SCM_PRETEND_VERSION": "0.4.1"},
                    clear=True,
                ):
                    release_checks.verify_tag("v0.4.1")


if __name__ == "__main__":
    unittest.main()
