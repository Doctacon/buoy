#!/usr/bin/env python3
"""Import a local text/code directory into a small DuckDB document relation.

This helper only materializes source documents.  It does not run Buoy planning,
ingestion, embedding, or indexing.

Usage::

    python scripts/import_local_directory.py ROOT OUTPUT.duckdb
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import stat
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

import duckdb

DEFAULT_MAX_FILE_BYTES = 200_000
DEFAULT_MAX_FILES = 10_000

# Deliberately excludes document formats which need an archive parser, OCR, or
# another converter.  Every extension here is expected to contain plain UTF-8.
TEXT_EXTENSIONS = frozenset(
    {
        ".adoc",
        ".asciidoc",
        ".bash",
        ".c",
        ".cc",
        ".cfg",
        ".clj",
        ".cljs",
        ".cmake",
        ".conf",
        ".cpp",
        ".cs",
        ".css",
        ".csv",
        ".cxx",
        ".dart",
        ".el",
        ".erl",
        ".ex",
        ".exs",
        ".fish",
        ".fs",
        ".fsx",
        ".go",
        ".gql",
        ".gradle",
        ".graphql",
        ".h",
        ".hpp",
        ".hrl",
        ".htm",
        ".html",
        ".ini",
        ".java",
        ".jl",
        ".js",
        ".json",
        ".jsonl",
        ".jsx",
        ".kt",
        ".kts",
        ".less",
        ".lua",
        ".markdown",
        ".md",
        ".mjs",
        ".mm",
        ".org",
        ".php",
        ".pl",
        ".pm",
        ".properties",
        ".proto",
        ".ps1",
        ".py",
        ".pyi",
        ".r",
        ".rb",
        ".rs",
        ".rst",
        ".sass",
        ".scala",
        ".scss",
        ".sh",
        ".sql",
        ".svelte",
        ".swift",
        ".tex",
        ".toml",
        ".ts",
        ".tsv",
        ".tsx",
        ".txt",
        ".vb",
        ".vue",
        ".xml",
        ".yaml",
        ".yml",
        ".zsh",
    }
)
TEXT_FILENAMES = frozenset(
    {
        "authors",
        "changelog",
        "cmakelists.txt",
        "code_of_conduct",
        "contributing",
        "copying",
        "dockerfile",
        "gemfile",
        "license",
        "makefile",
        "notice",
        "procfile",
        "readme",
        "requirements",
    }
)
IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "vendor",
    }
)
SENSITIVE_DIRECTORY_NAMES = frozenset(
    {
        ".aws",
        ".ssh",
        "cert",
        "certs",
        "certificate",
        "certificates",
        "credential",
        "credentials",
        "key",
        "keys",
        "secret",
        "secrets",
    }
)
SENSITIVE_EXTENSIONS = frozenset(
    {
        ".cer",
        ".cert",
        ".crt",
        ".der",
        ".jks",
        ".key",
        ".keystore",
        ".p12",
        ".pem",
        ".pfx",
        ".pkcs12",
    }
)
SAFE_DUCKDB_CONFIG = {
    "enable_external_access": "false",
    "autoinstall_known_extensions": "false",
    "autoload_known_extensions": "false",
    "allow_community_extensions": "false",
    "memory_limit": "4GB",
    "threads": "4",
}
SKIP_CATEGORIES = (
    "binary",
    "excluded",
    "hidden_directory",
    "ignored_directory",
    "include_mismatch",
    "non_utf8",
    "not_regular",
    "oversized",
    "sensitive",
    "symlink",
    "unsupported_type",
    "file_limit",
    "unreadable",
)


class LocalDirectoryImportError(RuntimeError):
    """Raised when a safe local-directory import cannot be completed."""


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    content: str


@dataclass
class ImportSummary:
    imported: int = 0
    skipped: dict[str, int] = field(
        default_factory=lambda: {category: 0 for category in SKIP_CATEGORIES}
    )

    def skip(self, category: str) -> None:
        self.skipped[category] += 1

    def as_dict(self, *, output: Path | None = None) -> dict[str, object]:
        result: dict[str, object] = {
            "imported": self.imported,
            "skipped": dict(self.skipped),
            "skipped_total": sum(self.skipped.values()),
        }
        if output is not None:
            result["output"] = os.fspath(output)
        return result


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a local DuckDB documents table from plain UTF-8 files; "
            "this does not run Buoy ingestion or indexing"
        )
    )
    parser.add_argument("root", type=Path, help="real local directory to scan")
    parser.add_argument("output", type=Path, help="DuckDB database to create")
    parser.add_argument(
        "--max-file-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_FILE_BYTES,
        help=f"maximum bytes read from one file (default: {DEFAULT_MAX_FILE_BYTES})",
    )
    parser.add_argument(
        "--max-files",
        type=_positive_int,
        default=DEFAULT_MAX_FILES,
        help=f"maximum candidate files inspected (default: {DEFAULT_MAX_FILES})",
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="include only matching POSIX relative paths (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="exclude matching POSIX relative paths (repeatable)",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace documents in an existing database, preserving other objects",
    )
    return parser


def validate_paths(
    root: Path, output: Path, *, replace: bool
) -> tuple[Path, Path, bool]:
    """Return canonical paths after enforcing the input/output safety boundary."""

    root = root.expanduser()
    if root.is_symlink():
        raise LocalDirectoryImportError("ROOT must not be a symlink")
    try:
        canonical_root = root.resolve(strict=True)
    except FileNotFoundError as exc:
        raise LocalDirectoryImportError(f"ROOT does not exist: {root}") from exc
    if not canonical_root.is_dir():
        raise LocalDirectoryImportError(f"ROOT must be a directory: {root}")

    output = output.expanduser()
    if output.is_symlink():
        raise LocalDirectoryImportError("OUTPUT must not be a symlink")
    canonical_output = output.resolve(strict=False)
    if canonical_output == canonical_root or canonical_output.is_relative_to(
        canonical_root
    ):
        raise LocalDirectoryImportError("OUTPUT must be outside ROOT")

    existed = canonical_output.exists()
    if existed:
        if not canonical_output.is_file():
            raise LocalDirectoryImportError(f"OUTPUT must be a regular file: {output}")
        if not replace:
            raise LocalDirectoryImportError(
                "OUTPUT already exists; pass --replace to replace only its documents table"
            )
    return canonical_root, canonical_output, existed


def _matches(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _directory_skip_category(name: str) -> str | None:
    folded = name.casefold()
    if folded.startswith(".buoy") or folded in IGNORED_DIRECTORY_NAMES:
        return "ignored_directory"
    if folded in SENSITIVE_DIRECTORY_NAMES:
        return "sensitive"
    if name.startswith(".") and folded not in {".", ".."}:
        return "hidden_directory"
    return None


def _sensitive_file(name: str) -> bool:
    folded = name.casefold()
    stem = Path(folded).stem
    return (
        folded == ".env"
        or folded.startswith((".env.", ".buoy"))
        or stem in {"secret", "secrets", "credential", "credentials"}
        or folded in {"id_dsa", "id_ecdsa", "id_ed25519", "id_rsa"}
        or Path(folded).suffix in SENSITIVE_EXTENSIONS
    )


def _supported_text_file(name: str) -> bool:
    folded = name.casefold()
    if Path(folded).suffix in TEXT_EXTENSIONS:
        return True
    return folded in TEXT_FILENAMES or any(
        folded.startswith(f"{base}.") for base in TEXT_FILENAMES
    )


def _read_bounded_regular_file(
    path: Path, max_file_bytes: int
) -> tuple[str, bytes | None]:
    """Read without following a final-component symlink, returning a category/data."""

    # Opening a FIFO read-only can block before fstat can reject it. Nonblocking
    # mode lets us reject special files without ever reading from them.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError:
        # A symlink race and an ordinary permission failure are both safe skips.
        return ("unreadable", None)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            return ("not_regular", None)
        if metadata.st_size > max_file_bytes:
            return ("oversized", None)
        chunks: list[bytes] = []
        remaining = max_file_bytes + 1
        while remaining:
            chunk = os.read(descriptor, min(65_536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        if len(data) > max_file_bytes:
            return ("oversized", None)
        return ("ok", data)
    finally:
        os.close(descriptor)


def collect_documents(
    root: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    includes: Sequence[str] = (),
    excludes: Sequence[str] = (),
) -> tuple[list[Document], ImportSummary]:
    """Collect deterministic documents from an already validated real directory."""

    if max_file_bytes <= 0 or max_files <= 0:
        raise ValueError("max_file_bytes and max_files must be greater than zero")

    documents: list[Document] = []
    summary = ImportSummary()
    candidates = 0

    for current, directory_names, file_names in os.walk(
        root, topdown=True, followlinks=False
    ):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(directory_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                summary.skip("symlink")
                continue
            category = _directory_skip_category(name)
            if category is not None:
                summary.skip(category)
                continue
            if _matches(relative, excludes) or _matches(relative + "/", excludes):
                summary.skip("excluded")
                continue
            kept_directories.append(name)
        directory_names[:] = kept_directories

        for name in sorted(file_names):
            path = current_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                summary.skip("symlink")
                continue
            if name.casefold().startswith(".buoy"):
                summary.skip("ignored_directory")
                continue
            if _sensitive_file(name):
                summary.skip("sensitive")
                continue
            if _matches(relative, excludes):
                summary.skip("excluded")
                continue
            if includes and not _matches(relative, includes):
                summary.skip("include_mismatch")
                continue
            if not _supported_text_file(name):
                summary.skip("unsupported_type")
                continue
            if candidates >= max_files:
                summary.skip("file_limit")
                continue
            candidates += 1

            category, data = _read_bounded_regular_file(path, max_file_bytes)
            if category != "ok":
                summary.skip(category)
                continue
            assert data is not None
            if b"\x00" in data:
                summary.skip("binary")
                continue
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError:
                summary.skip("non_utf8")
                continue
            documents.append(
                Document(
                    document_id=relative,
                    title=relative,
                    content=f"File: {relative}\n\n{text}",
                )
            )

    documents.sort(key=lambda document: document.document_id)
    summary.imported = len(documents)
    return documents, summary


def _replace_documents(
    connection: duckdb.DuckDBPyConnection, documents: Sequence[Document]
) -> None:
    """Replace the one table owned by this helper inside the caller's transaction."""

    connection.execute("DROP TABLE IF EXISTS documents")
    connection.execute(
        "CREATE TABLE documents ("
        "document_id VARCHAR PRIMARY KEY, "
        "title VARCHAR NOT NULL, "
        "content VARCHAR NOT NULL)"
    )
    if documents:
        connection.executemany(
            "INSERT INTO documents (document_id, title, content) VALUES (?, ?, ?)",
            [
                (document.document_id, document.title, document.content)
                for document in documents
            ],
        )


def write_database(
    output: Path, documents: Sequence[Document], *, existed: bool
) -> None:
    """Transactionally replace ``documents`` while retaining unrelated objects."""

    output.parent.mkdir(parents=True, exist_ok=True)
    connection: duckdb.DuckDBPyConnection | None = None
    try:
        connection = duckdb.connect(os.fspath(output), config=SAFE_DUCKDB_CONFIG)
        connection.execute("BEGIN TRANSACTION")
        try:
            _replace_documents(connection, documents)
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise
    except BaseException:
        if not existed and output.exists():
            try:
                output.unlink()
            except OSError:
                pass
        raise
    finally:
        if connection is not None:
            connection.close()


def run(
    root: Path,
    output: Path,
    *,
    max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
    max_files: int = DEFAULT_MAX_FILES,
    includes: Sequence[str] = (),
    excludes: Sequence[str] = (),
    replace: bool = False,
) -> ImportSummary:
    canonical_root, canonical_output, existed = validate_paths(
        root, output, replace=replace
    )
    documents, summary = collect_documents(
        canonical_root,
        max_file_bytes=max_file_bytes,
        max_files=max_files,
        includes=includes,
        excludes=excludes,
    )
    write_database(canonical_output, documents, existed=existed)
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        canonical_root, canonical_output, existed = validate_paths(
            args.root, args.output, replace=args.replace
        )
        documents, summary = collect_documents(
            canonical_root,
            max_file_bytes=args.max_file_bytes,
            max_files=args.max_files,
            includes=args.include,
            excludes=args.exclude,
        )
        write_database(canonical_output, documents, existed=existed)
    except (LocalDirectoryImportError, OSError, duckdb.Error) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(summary.as_dict(output=canonical_output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
