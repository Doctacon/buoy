"""Reusable local-only planning application service.

The service materializes source content and writes verified review artifacts. It
never embeds content, reads turbopuffer credentials, calls turbopuffer, or
updates applied state or routing catalogs.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
from typing import Any, Callable, Literal

from buoy_search.applied_state import load_applied_state
from buoy_search.catalog import generated_semantics
from buoy_search.config import DEFAULT_EMBEDDING_PRECISION, DEFAULT_REGION
from buoy_search.crawler import (
    DEFAULT_CRAWL_CONCURRENT_REQUESTS,
    DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN,
    DEFAULT_CRAWL_DOWNLOAD_DELAY,
    DEFAULT_CRAWL_MAX_CHUNKS,
    DEFAULT_CRAWL_MAX_PAGES,
    DEFAULT_CRAWL_STRATEGY,
    DEFAULT_DOCS_VERSION_POLICY,
    DEFAULT_GITHUB_REPO_MAX_CHUNKS,
    DEFAULT_GITHUB_REPO_MAX_FILE_BYTES,
    DEFAULT_GITHUB_REPO_MAX_FILES,
    DEFAULT_LANGUAGE_POLICY,
    GitHubRepoSource,
    LocalFileSource,
    PdfSource,
    CrawlExecution,
    CrawlOptions,
    default_out_dir,
    detect_source,
    elapsed_since,
    observe_monotonic,
)
from buoy_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
    parse_markdown_file,
)
from buoy_search.database_relation import DatabaseRelationError
from buoy_search.plan_artifacts import (
    DEFAULT_PLAN_EMBEDDING_MODEL,
    PlanArtifacts,
    build_plan_artifacts,
    write_plan_artifacts,
)
from buoy_search.plan_cleanup import cleanup_superseded_plan_directories
from buoy_search.plan_diff import IncrementalPlanDiff, diff_manifest_against_state
from buoy_search.source_url import validate_http_url_authority
from buoy_search.remote_catalog import REMOTE_CATALOG_NAMESPACE
from buoy_search.retriever import ranking_defaults_for_namespace

JsonObject = dict[str, Any]
SourceKind = Literal["website", "github_repo"]
MAX_MANAGED_SOURCE_URL_LENGTH = 2_048
MAX_PROGRESS_STAGE_LENGTH = 64
MAX_PROGRESS_MESSAGE_LENGTH = 500
_COUNT_PATTERN = re.compile(r"(?:^|[;\s])([a-z][a-z0-9_]*)=(\d+)(?=$|[;/\s])")
_DATABASE_KINDS = {"duckdb_relation", "bigquery_relation", "snowflake_relation"}
_MANAGED_JOB_ID = re.compile(r"planjob_[0-9a-f]{32}")


@dataclass(frozen=True)
class PlanProgress:
    """One bounded progress update suitable for CLI or durable job adapters."""

    stage: str
    message: str
    counts: dict[str, int]


ProgressCallback = Callable[[PlanProgress], None]


@dataclass(frozen=True)
class PlanningRequest:
    """Complete typed input for one existing CLI-compatible planning run."""

    source: str | None
    state_root: Path
    out_dir: Path | None = None
    namespace: str | None = None
    embedding_precision: str = DEFAULT_EMBEDDING_PRECISION
    max_pages: int | None = None
    max_chunks: int | None = None
    repo_max_file_bytes: int = DEFAULT_GITHUB_REPO_MAX_FILE_BYTES
    repo_chunking_arm: str | None = None
    repo_search_metadata: bool = False
    repo_file_cards: bool = False
    repo_oversize_file_cards: bool = False
    concurrent_requests: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS
    concurrent_requests_per_domain: int = DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN
    download_delay: float = DEFAULT_CRAWL_DOWNLOAD_DELAY
    crawl_strategy: str = DEFAULT_CRAWL_STRATEGY
    docs_version_policy: str = DEFAULT_DOCS_VERSION_POLICY
    language_policy: str = DEFAULT_LANGUAGE_POLICY
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    strip_trailing_slash: bool = True
    css_selector: str | None = None
    target_tokens: int = DEFAULT_TARGET_TOKENS
    overlap_sentences: int = DEFAULT_OVERLAP_SENTENCES
    database_backend: str | None = None
    relation: str | None = None
    database_source_id: str | None = None
    id_column: str | None = None
    content_column: str | None = None
    title_column: str | None = None
    bigquery_project: str | None = None
    bigquery_location: str | None = None
    bigquery_maximum_bytes_billed: int | None = None
    snowflake_connection: str | None = None
    source_query_timeout: float | None = None
    require_new_output: bool = False
    cleanup_superseded: bool = True
    precreated_output_identity: tuple[int, int] | None = None
    precreated_output_ancestor_identities: tuple[tuple[int, int], ...] = ()
    precreated_output_descriptor: int | None = None
    originating_job_id: str | None = None


@dataclass(frozen=True)
class ManagedPublicPlanningRequest:
    """Narrow request for one credential-free HTTP(S) or public GitHub source."""

    source_url: str
    out_dir: Path
    state_root: Path
    max_pages_or_files: int | None = None
    max_chunks: int | None = None
    namespace: str | None = None
    include_paths: tuple[str, ...] = ()
    exclude_paths: tuple[str, ...] = ()
    precreated_output_identity: tuple[int, int] | None = None
    precreated_output_ancestor_identities: tuple[tuple[int, int], ...] = ()
    precreated_output_descriptor: int | None = None
    originating_job_id: str | None = None

    def to_planning_request(self) -> PlanningRequest:
        source = validate_managed_public_source(self.source_url)
        if (
            self.originating_job_id is not None
            and _MANAGED_JOB_ID.fullmatch(self.originating_job_id) is None
        ):
            raise ValueError("originating_job_id must be a safe managed plan-job ID")
        for name, value in (
            ("max_pages_or_files", self.max_pages_or_files),
            ("max_chunks", self.max_chunks),
        ):
            if value is not None and (type(value) is not int or value <= 0):
                raise ValueError(f"{name} must be a positive integer")
        return PlanningRequest(
            source=source.base_url,
            state_root=Path(self.state_root),
            out_dir=Path(self.out_dir),
            namespace=self.namespace,
            max_pages=self.max_pages_or_files,
            max_chunks=self.max_chunks,
            include_paths=tuple(self.include_paths),
            exclude_paths=tuple(self.exclude_paths),
            require_new_output=True,
            cleanup_superseded=False,
            precreated_output_identity=self.precreated_output_identity,
            precreated_output_ancestor_identities=self.precreated_output_ancestor_identities,
            precreated_output_descriptor=self.precreated_output_descriptor,
            originating_job_id=self.originating_job_id,
        )


@dataclass(frozen=True)
class PlanningResult:
    """Verified result and CLI-only cleanup diagnostics from one planning run."""

    summary: JsonObject
    artifacts: PlanArtifacts
    diff: IncrementalPlanDiff
    out_dir: Path
    source_kind: str
    cleanup_warnings: tuple[str, ...]


CrawlRunner = Callable[[object, CrawlOptions], CrawlExecution]
ArtifactBuilder = Callable[..., PlanArtifacts]
ArtifactWriter = Callable[[PlanArtifacts, Path], None]
ArtifactVerifier = Callable[[Path, Path, str], None]
CleanupRunner = Callable[..., list[str]]


class PlanningService:
    """Apply the current planning domain workflow without invoking the CLI."""

    def __init__(
        self,
        *,
        crawl_runner: CrawlRunner | None = None,
        artifact_builder: ArtifactBuilder = build_plan_artifacts,
        artifact_writer: ArtifactWriter = write_plan_artifacts,
        artifact_verifier: ArtifactVerifier | None = None,
        cleanup_runner: CleanupRunner = cleanup_superseded_plan_directories,
    ) -> None:
        self._crawl_runner = crawl_runner or crawl_source_with_plan
        self._artifact_builder = artifact_builder
        self._artifact_writer = artifact_writer
        self._artifact_verifier = artifact_verifier or verify_written_plan
        self._cleanup_runner = cleanup_runner

    def plan(
        self,
        request: PlanningRequest | ManagedPublicPlanningRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PlanningResult:
        if isinstance(request, ManagedPublicPlanningRequest):
            request = request.to_planning_request()
        if request.precreated_output_identity is None:
            result = self._plan_to_directory(request, progress_callback=progress_callback)
        else:
            validate_precreated_output(request, require_empty=True)
            staging_path, staging_descriptor = create_private_staging_directory()
            published = False
            try:
                result = self._plan_to_directory(
                    request,
                    progress_callback=progress_callback,
                    write_out_dir=staging_path,
                )
                copy_staged_artifacts(
                    request,
                    staging_descriptor,
                    require_complete=True,
                )
                published = True
                validate_precreated_output(request)
            except Exception:
                if not published:
                    try:
                        copy_staged_artifacts(
                            request,
                            staging_descriptor,
                            require_complete=False,
                        )
                    except Exception:
                        pass
                raise
            finally:
                os.close(staging_descriptor)
                shutil.rmtree(staging_path, ignore_errors=True)
        emit_progress(
            progress_callback,
            "complete",
            "plan: complete "
            f"pages={len(result.artifacts.manifest.pages)}; "
            f"chunks={len(result.artifacts.manifest.chunks)}",
        )
        return result

    def _plan_to_directory(
        self,
        request: PlanningRequest,
        *,
        progress_callback: ProgressCallback | None,
        write_out_dir: Path | None = None,
    ) -> PlanningResult:
        source = source_from_request(request)
        base_url = str(getattr(source, "base_url"))
        if request.repo_chunking_arm and not isinstance(source, GitHubRepoSource):
            raise ValueError("--repo-chunking-arm is supported only for GitHub repositories.")

        max_pages = request.max_pages
        if max_pages is None:
            max_pages = (
                DEFAULT_GITHUB_REPO_MAX_FILES
                if isinstance(source, GitHubRepoSource)
                else DEFAULT_CRAWL_MAX_PAGES
            )
        max_chunks = request.max_chunks
        if max_chunks is None:
            max_chunks = (
                DEFAULT_GITHUB_REPO_MAX_CHUNKS
                if isinstance(source, GitHubRepoSource)
                else DEFAULT_CRAWL_MAX_CHUNKS
            )
        out_dir = request.out_dir or default_plan_out_dir(source, base_url)
        write_out_dir = write_out_dir or out_dir
        if request.require_new_output:
            if request.precreated_output_identity is None:
                if out_dir.exists() or out_dir.is_symlink():
                    raise ValueError(f"managed plan output directory already exists: {out_dir}")
            else:
                validate_precreated_output(request, require_empty=True)
                if write_out_dir == out_dir:
                    raise ValueError("managed plan output requires a private staging directory")

        emit_progress(progress_callback, "plan: preparing", f"plan: preparing {base_url}")
        options = CrawlOptions(
            base_url=base_url,
            out_dir=write_out_dir,
            max_pages=max_pages,
            max_chunks=max_chunks,
            repo_max_file_bytes=request.repo_max_file_bytes,
            repo_chunking_arm=request.repo_chunking_arm,
            repo_search_metadata=request.repo_search_metadata,
            repo_file_cards=request.repo_file_cards,
            repo_oversize_file_cards=request.repo_oversize_file_cards,
            concurrent_requests=request.concurrent_requests,
            concurrent_requests_per_domain=request.concurrent_requests_per_domain,
            download_delay=request.download_delay,
            crawl_strategy=request.crawl_strategy,
            docs_version_policy=request.docs_version_policy,
            language_policy=request.language_policy,
            include_paths=request.include_paths,
            exclude_paths=request.exclude_paths,
            strip_trailing_slash=request.strip_trailing_slash,
            css_selector=request.css_selector,
            target_tokens=request.target_tokens,
            overlap_sentences=request.overlap_sentences,
            progress_callback=(
                lambda message: emit_progress(progress_callback, stage_from_message(message), message)
                if progress_callback is not None
                else None
            ),
        )
        plan_started_at = observe_monotonic()
        crawl_execution = self._crawl_runner(source, options)
        validate_precreated_output(request)
        crawl_summary = crawl_execution.summary
        if write_out_dir != out_dir:
            # Persist stable logical paths, never the process-local descriptor alias.
            crawl_summary["out_dir"] = str(out_dir)
            crawl_summary["pages_dir"] = str(out_dir / "pages")
        namespace = request.namespace or str(crawl_summary["namespace_candidate"])

        emit_progress(progress_callback, "artifacts", "plan: building artifacts")
        artifact_started_at = observe_monotonic()
        initial_artifacts = self._artifact_builder(
            indexing_plan=crawl_execution.indexing_plan,
            base_url=base_url,
            out_dir=out_dir,
            namespace=namespace,
            crawl_options=plan_crawl_options(request, crawl_summary, max_pages, max_chunks),
            chunk_options=plan_chunk_options(request),
            embedding_model=DEFAULT_PLAN_EMBEDDING_MODEL,
            embedding_precision=request.embedding_precision,
            state_root=request.state_root,
        )
        artifact_seconds = elapsed_since(artifact_started_at)
        state = load_applied_state(
            site_id=initial_artifacts.manifest.site_id,
            namespace=initial_artifacts.manifest.namespace,
            base_url=base_url,
            state_root=request.state_root,
        )

        emit_progress(progress_callback, "diff", "plan: diffing against local state")
        diff_started_at = observe_monotonic()
        diff = diff_manifest_against_state(initial_artifacts.manifest, state)
        diff_seconds = elapsed_since(diff_started_at)
        artifacts = PlanArtifacts(
            plan=replace(initial_artifacts.plan, diff=diff.to_dict()),
            manifest=initial_artifacts.manifest,
            chunks_jsonl=initial_artifacts.chunks_jsonl,
        )
        catalog_preview = plan_catalog_registration_preview(
            artifacts,
            region=os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION),
        )

        emit_progress(progress_callback, "write", "plan: writing review artifacts")
        validate_precreated_output(request)
        publication_started_at = observe_monotonic()
        self._artifact_writer(artifacts, write_out_dir)
        validate_precreated_output(request)
        publication_seconds = elapsed_since(publication_started_at)

        source_timing = crawl_summary.get("timing")
        timing = dict(source_timing) if isinstance(source_timing, dict) else {}
        for stage in (
            "sitemap_policy_seconds",
            "crawl_seconds",
            "corpus_write_seconds",
            "chunking_seconds",
        ):
            timing.setdefault(stage, 0.0)
        timing.update(
            {
                "elapsed_seconds": elapsed_since(plan_started_at),
                "diff_seconds": diff_seconds,
                "artifact_seconds": artifact_seconds,
                "publication_seconds": publication_seconds,
            }
        )
        crawl_summary["timing"] = timing
        summary = plan_summary(
            crawl_summary=crawl_summary,
            artifacts=artifacts,
            diff=diff,
            state_first_apply=state.first_apply,
            catalog_registration=catalog_preview,
            originating_job_id=request.originating_job_id,
        )
        validate_precreated_output(request)
        (write_out_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
        )
        validate_precreated_output(request)
        self._artifact_verifier(
            write_out_dir / "plan.json", request.state_root, artifacts.plan.plan_id
        )
        validate_precreated_output(request)

        warnings: list[str] = []
        if request.cleanup_superseded:
            warnings = self._cleanup_runner(
                out_dir / "plan.json",
                namespace=namespace,
                state_root=request.state_root,
            )
        return PlanningResult(
            summary=summary,
            artifacts=artifacts,
            diff=diff,
            out_dir=out_dir,
            source_kind=str(getattr(source, "kind", "unknown")),
            cleanup_warnings=tuple(warnings),
        )


def validate_precreated_output(
    request: PlanningRequest, *, require_empty: bool = False
) -> None:
    """Fail closed if a descriptor-created managed output path was replaced."""

    identity = request.precreated_output_identity
    if identity is None:
        return
    out_dir = request.out_dir
    descriptor = request.precreated_output_descriptor
    if out_dir is None or descriptor is None:
        raise ValueError("managed precreated output requires a held directory descriptor")
    try:
        opened = os.fstat(descriptor)
    except OSError as exc:
        raise ValueError("managed plan output descriptor is unavailable") from exc
    if not stat.S_ISDIR(opened.st_mode) or (opened.st_dev, opened.st_ino) != identity:
        raise ValueError("managed plan output descriptor is unsafe or was replaced")
    ancestors = request.precreated_output_ancestor_identities
    if len(ancestors) != 3:
        raise ValueError("managed plan output directory has no verified ancestry")
    for ancestor, expected in zip(
        (out_dir.parents[2], out_dir.parents[1], out_dir.parents[0]),
        ancestors,
        strict=True,
    ):
        try:
            current_ancestor = os.lstat(ancestor)
        except OSError as exc:
            raise ValueError(
                "managed plan output ancestry is unavailable or was replaced"
            ) from exc
        if (
            not stat.S_ISDIR(current_ancestor.st_mode)
            or stat.S_ISLNK(current_ancestor.st_mode)
            or (current_ancestor.st_dev, current_ancestor.st_ino) != expected
        ):
            raise ValueError("managed plan output ancestry is unsafe or was replaced")
    try:
        current = os.lstat(out_dir)
    except OSError as exc:
        raise ValueError("managed plan output directory is unavailable or was replaced") from exc
    if (
        not stat.S_ISDIR(current.st_mode)
        or stat.S_ISLNK(current.st_mode)
        or (current.st_dev, current.st_ino) != identity
    ):
        raise ValueError("managed plan output directory is unsafe or was replaced")
    if require_empty:
        if os.listdir not in os.supports_fd:
            raise ValueError("managed descriptor-relative directory inspection is unsupported")
        try:
            if os.listdir(descriptor):
                raise ValueError("managed plan output directory is not empty")
        except OSError as exc:
            raise ValueError("managed plan output directory could not be inspected safely") from exc


_MANAGED_ARTIFACT_FILES = frozenset(
    {"plan.json", "manifest.json", "chunks.jsonl", "summary.json"}
)
_MANAGED_ARTIFACT_ROOTS = _MANAGED_ARTIFACT_FILES | {"pages"}


def create_private_staging_directory() -> tuple[Path, int]:
    """Create and retain one private directory for existing path-based writers."""

    path = Path(tempfile.mkdtemp(prefix="buoy-managed-plan-"))
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    try:
        os.chmod(path, 0o700)
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        current = os.lstat(path)
        if (
            not stat.S_ISDIR(opened.st_mode)
            or stat.S_ISLNK(current.st_mode)
            or (opened.st_dev, opened.st_ino) != (current.st_dev, current.st_ino)
            or opened.st_mode & 0o077
        ):
            os.close(descriptor)
            raise ValueError("managed plan staging directory is unsafe")
        return path, descriptor
    except Exception:
        shutil.rmtree(path, ignore_errors=True)
        raise


def copy_staged_artifacts(
    request: PlanningRequest,
    staging_descriptor: int,
    *,
    require_complete: bool,
) -> None:
    """Copy only ordinary review artifacts into the held final directory."""

    destination = request.precreated_output_descriptor
    if destination is None:
        raise ValueError("managed plan output requires a held directory descriptor")
    source_names = set(os.listdir(staging_descriptor))
    selected = source_names & _MANAGED_ARTIFACT_ROOTS
    if require_complete and selected != _MANAGED_ARTIFACT_ROOTS:
        raise ValueError("managed plan staging artifacts are incomplete")
    if os.listdir(destination):
        if require_complete:
            raise ValueError("managed plan output directory is not empty")
        return
    for name in sorted(selected):
        if name == "pages":
            _copy_staged_directory(staging_descriptor, destination, name)
        else:
            _copy_staged_file(staging_descriptor, destination, name)
    _fsync_directory_descriptor(destination)
    source_hashes = _ordinary_tree_hashes(staging_descriptor, selected)
    destination_hashes = _ordinary_tree_hashes(destination, selected)
    if source_hashes != destination_hashes or set(os.listdir(destination)) != selected:
        raise ValueError("managed plan artifacts failed post-copy integrity verification")


def _copy_staged_directory(source_parent: int, destination_parent: int, name: str) -> None:
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    source = os.open(name, flags, dir_fd=source_parent)
    try:
        opened = os.fstat(source)
        if not stat.S_ISDIR(opened.st_mode):
            raise ValueError("managed plan staging artifact is not an ordinary directory")
        os.mkdir(name, 0o700, dir_fd=destination_parent)
        destination = os.open(name, flags, dir_fd=destination_parent)
        try:
            for child in sorted(os.listdir(source)):
                child_stat = os.stat(child, dir_fd=source, follow_symlinks=False)
                if stat.S_ISDIR(child_stat.st_mode):
                    _copy_staged_directory(source, destination, child)
                elif stat.S_ISREG(child_stat.st_mode):
                    _copy_staged_file(source, destination, child)
                else:
                    raise ValueError("managed plan staging artifact is not ordinary")
            _fsync_directory_descriptor(destination)
        finally:
            os.close(destination)
    finally:
        os.close(source)


def _copy_staged_file(source_parent: int, destination_parent: int, name: str) -> None:
    source = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=source_parent,
    )
    try:
        source_stat = os.fstat(source)
        if not stat.S_ISREG(source_stat.st_mode) or source_stat.st_nlink != 1:
            raise ValueError("managed plan staging artifact is not a private regular file")
        destination = os.open(
            name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
            0o600,
            dir_fd=destination_parent,
        )
        try:
            while True:
                block = os.read(source, 64 * 1024)
                if not block:
                    break
                offset = 0
                while offset < len(block):
                    written = os.write(destination, block[offset:])
                    if written <= 0:
                        raise OSError("managed artifact copy made no progress")
                    offset += written
            os.fsync(destination)
            copied = os.fstat(destination)
            if not stat.S_ISREG(copied.st_mode) or copied.st_nlink != 1:
                raise ValueError("managed plan destination artifact is not a private regular file")
        finally:
            os.close(destination)
    finally:
        os.close(source)


def _ordinary_tree_hashes(directory: int, roots: set[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in sorted(roots):
        _collect_ordinary_hashes(directory, name, name, hashes)
    return hashes


def _collect_ordinary_hashes(
    parent: int,
    name: str,
    relative: str,
    hashes: dict[str, str],
) -> None:
    opened = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if stat.S_ISDIR(opened.st_mode):
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        descriptor = os.open(name, flags, dir_fd=parent)
        try:
            bound = os.fstat(descriptor)
            if (bound.st_dev, bound.st_ino) != (opened.st_dev, opened.st_ino):
                raise ValueError("managed plan artifact directory was replaced during verification")
            hashes[f"{relative}/"] = "directory"
            for child in sorted(os.listdir(descriptor)):
                _collect_ordinary_hashes(descriptor, child, f"{relative}/{child}", hashes)
        finally:
            os.close(descriptor)
        return
    if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
        raise ValueError("managed plan artifact tree contains a non-ordinary entry")
    descriptor = os.open(
        name,
        os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
        dir_fd=parent,
    )
    try:
        bound = os.fstat(descriptor)
        if (
            not stat.S_ISREG(bound.st_mode)
            or bound.st_nlink != 1
            or (bound.st_dev, bound.st_ino) != (opened.st_dev, opened.st_ino)
        ):
            raise ValueError("managed plan artifact file was replaced during verification")
        digest = hashlib.sha256()
        while True:
            block = os.read(descriptor, 64 * 1024)
            if not block:
                break
            digest.update(block)
        hashes[relative] = digest.hexdigest()
    finally:
        os.close(descriptor)


def _fsync_directory_descriptor(descriptor: int) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise ValueError("managed plan artifact directory could not be synced") from exc


def validate_managed_public_source(source_url: str) -> object:
    """Validate a credential-free HTTP(S) website or public GitHub repository root."""

    if not isinstance(source_url, str) or not source_url.strip():
        raise ValueError("source_url must be a non-empty HTTP(S) URL")
    if len(source_url) > MAX_MANAGED_SOURCE_URL_LENGTH:
        raise ValueError(
            f"source_url must be at most {MAX_MANAGED_SOURCE_URL_LENGTH} characters"
        )
    validate_http_url_authority(source_url)
    source = detect_source(source_url)
    if isinstance(source, GitHubRepoSource) and (
        source.tree_ref is not None or source.blob_hint is not None
    ):
        raise ValueError("managed GitHub source_url must be a repository root URL")
    if getattr(source, "kind", None) not in {"website", "github_repo"}:
        raise ValueError(
            "managed source_url must identify a credential-free HTTP(S) website or public GitHub repository root"
        )
    return source


def source_from_request(request: PlanningRequest) -> object:
    """Detect one source, importing database adapters only for requested database modes."""

    database_values = {
        "--database-backend": request.database_backend,
        "--source-id": request.database_source_id,
        "--id-column": request.id_column,
        "--content-column": request.content_column,
        "--title-column": request.title_column,
        "--bigquery-project": request.bigquery_project,
        "--bigquery-location": request.bigquery_location,
        "--bigquery-maximum-bytes-billed": request.bigquery_maximum_bytes_billed,
        "--snowflake-connection": request.snowflake_connection,
        "--source-query-timeout": request.source_query_timeout,
    }
    if request.relation is None:
        supplied = [flag for flag, value in database_values.items() if value is not None]
        if supplied:
            raise ValueError(
                f"{', '.join(supplied)} require --relation to activate database relation mode."
            )
        if request.source is None:
            raise ValueError("source URL/path is required.")
        return detect_source(request.source)

    backend = request.database_backend or "duckdb"
    if request.database_source_id is None:
        raise ValueError("--source-id is required when --relation activates database relation mode.")
    if backend != "bigquery":
        supplied = [
            flag
            for flag, value in {
                "--bigquery-project": request.bigquery_project,
                "--bigquery-location": request.bigquery_location,
                "--bigquery-maximum-bytes-billed": request.bigquery_maximum_bytes_billed,
            }.items()
            if value is not None
        ]
        if supplied:
            raise ValueError(
                f"{', '.join(supplied)} are supported only with --database-backend bigquery."
            )
    if backend != "snowflake" and request.snowflake_connection is not None:
        raise ValueError(
            "--snowflake-connection is supported only with --database-backend snowflake."
        )
    if backend == "duckdb" and request.source_query_timeout is not None:
        raise ValueError(
            "--source-query-timeout is supported only with BigQuery or Snowflake database backends."
        )

    id_column = "document_id" if request.id_column is None else request.id_column
    content_column = "content" if request.content_column is None else request.content_column
    if backend == "duckdb":
        if request.source is None:
            raise ValueError("DuckDB database filepath is required when --relation is used.")
        from buoy_search.duckdb_relation import duckdb_relation_source

        return duckdb_relation_source(
            request.source,
            relation=request.relation,
            source_id=request.database_source_id,
            id_column=id_column,
            content_column=content_column,
            title_column=request.title_column,
        )
    if request.source is not None:
        raise ValueError(
            f"A local source path/--base-url is not accepted with --database-backend {backend}."
        )
    if backend == "bigquery":
        from buoy_search.bigquery_relation import bigquery_relation_source

        return bigquery_relation_source(
            relation=request.relation,
            source_id=request.database_source_id,
            id_column=id_column,
            content_column=content_column,
            title_column=request.title_column,
            query_project=request.bigquery_project,
            location=request.bigquery_location,
            maximum_bytes_billed=request.bigquery_maximum_bytes_billed,
            query_timeout=request.source_query_timeout or 300.0,
            operation="plan",
        )
    if request.snowflake_connection is None:
        raise ValueError("--snowflake-connection is required for Snowflake database mode.")
    from buoy_search.snowflake_relation import snowflake_relation_source

    return snowflake_relation_source(
        relation=request.relation,
        source_id=request.database_source_id,
        connection_name=request.snowflake_connection,
        id_column=id_column,
        content_column=content_column,
        title_column=request.title_column,
        query_timeout=request.source_query_timeout or 300.0,
        operation="plan",
    )


def crawl_source_with_plan(source: object, options: CrawlOptions) -> CrawlExecution:
    """Dispatch to the current source implementation through lazy adapter imports."""

    source_kind = getattr(source, "kind", None)
    if source_kind == "duckdb_relation":
        from buoy_search.duckdb_relation import crawl_duckdb_relation_with_plan

        return crawl_duckdb_relation_with_plan(source, options)  # type: ignore[arg-type,return-value]
    if source_kind == "bigquery_relation":
        from buoy_search.bigquery_relation import crawl_bigquery_relation_with_plan

        return crawl_bigquery_relation_with_plan(source, options)  # type: ignore[arg-type,return-value]
    if source_kind == "snowflake_relation":
        from buoy_search.snowflake_relation import crawl_snowflake_relation_with_plan

        return crawl_snowflake_relation_with_plan(source, options)  # type: ignore[arg-type,return-value]
    if isinstance(source, GitHubRepoSource):
        from buoy_search.github_repo import crawl_github_repo_with_plan

        return crawl_github_repo_with_plan(source, options)
    if isinstance(source, (PdfSource, LocalFileSource)):
        from buoy_search.crawler import crawl_local_document_with_plan

        return crawl_local_document_with_plan(source, options)
    from buoy_search.crawler import crawl_site_with_plan

    return crawl_site_with_plan(options)


def default_plan_out_dir(source: object, base_url: str) -> Path:
    if getattr(source, "kind", None) in _DATABASE_KINDS:
        return Path(getattr(source, "default_out_dir"))
    crawl_dir = default_out_dir(base_url)
    return crawl_dir.with_name(f"{crawl_dir.name}-plan")


def plan_crawl_options(
    request: PlanningRequest,
    crawl_summary: JsonObject,
    max_pages: int,
    max_chunks: int,
) -> JsonObject:
    options: JsonObject = {
        "max_pages": max_pages,
        "max_chunks": max_chunks,
        "repo_max_file_bytes": request.repo_max_file_bytes,
        "repo_search_metadata": request.repo_search_metadata,
        "repo_file_cards": request.repo_file_cards,
        "repo_oversize_file_cards": request.repo_oversize_file_cards,
        "concurrent_requests": request.concurrent_requests,
        "concurrent_requests_per_domain": request.concurrent_requests_per_domain,
        "download_delay": request.download_delay,
        "crawl_strategy": request.crawl_strategy,
        "docs_version_policy": request.docs_version_policy,
        "language_policy": request.language_policy,
        "include_paths": list(crawl_summary.get("include_paths", request.include_paths)),
        "exclude_paths": list(crawl_summary.get("exclude_paths", request.exclude_paths)),
        "strip_trailing_slash": request.strip_trailing_slash,
        "css_selector": request.css_selector,
    }
    if request.repo_chunking_arm is not None:
        options["repo_chunking_arm"] = request.repo_chunking_arm
    if crawl_summary.get("source_kind") in _DATABASE_KINDS:
        options.update(
            {
                "source_kind": crawl_summary["source_kind"],
                "database_backend": crawl_summary["database_backend"],
                "database_source_id": crawl_summary["database_source_id"],
                "database_relation": crawl_summary["database_relation"],
                "id_column": crawl_summary["id_column"],
                "content_column": crawl_summary["content_column"],
                "title_column": crawl_summary["title_column"],
            }
        )
        if crawl_summary.get("source_kind") == "duckdb_relation":
            options.update(
                {
                    "duckdb_source_id": crawl_summary["duckdb_source_id"],
                    "duckdb_relation": crawl_summary["duckdb_relation"],
                }
            )
    return options


def plan_chunk_options(request: PlanningRequest) -> JsonObject:
    return {
        "target_tokens": request.target_tokens,
        "overlap_sentences": request.overlap_sentences,
    }


def plan_summary(
    *,
    crawl_summary: JsonObject,
    artifacts: PlanArtifacts,
    diff: IncrementalPlanDiff,
    state_first_apply: bool,
    catalog_registration: JsonObject | None = None,
    originating_job_id: str | None = None,
) -> JsonObject:
    plan_dict = artifacts.plan_dict()
    diff_summary = diff.summary_dict()
    summary = dict(crawl_summary)
    summary.update(
        {
            "command": "plan",
            "dry_run": True,
            "credentials_required": bool(crawl_summary.get("source_credentials_required", False)),
            "source_credentials_required": bool(
                crawl_summary.get("source_credentials_required", False)
            ),
            "source_api_calls_occurred": bool(
                crawl_summary.get("source_api_calls_occurred", False)
            ),
            "turbopuffer_credentials_required": False,
            "turbopuffer_api_calls": False,
            "api_calls_occurred": bool(crawl_summary.get("source_api_calls_occurred", False)),
            "namespace": plan_dict["namespace"],
            "namespace_candidate": plan_dict["namespace_candidate"],
            "site_id": plan_dict["site_id"],
            "plan_id": plan_dict["plan_id"],
            "plan_path": str(Path(str(plan_dict["manifest_path"])).with_name("plan.json")),
            "manifest_path": plan_dict["manifest_path"],
            "chunks_path": plan_dict["chunks_path"],
            "pages_dir": plan_dict["pages_dir"],
            "state_backend": plan_dict["state_backend"],
            "state_path": plan_dict["state_path"],
            "state_first_apply": state_first_apply,
            "embedding_model": plan_dict["embedding_model"],
            "embedding_precision": plan_dict["embedding_precision"],
            "artifact_hash": plan_dict["artifact_hash"],
            "diff": diff_summary,
            **diff_summary,
        }
    )
    if catalog_registration is not None:
        summary["catalog_registration"] = catalog_registration
    if originating_job_id is not None:
        summary["originating_job_id"] = originating_job_id
    return summary


def plan_catalog_registration_preview(
    artifacts: PlanArtifacts,
    *,
    region: str,
) -> JsonObject:
    manifest = artifacts.manifest
    metadata = [
        dict(record.source_metadata)
        for record in [*manifest.pages, *manifest.chunks]
        if record.source_metadata
    ]
    semantics = generated_semantics(
        base_url=manifest.base_url,
        site_id=manifest.site_id,
        plan_schema_version=artifacts.plan.schema_version,
        source_metadata=metadata,
    )
    ranking = ranking_defaults_for_namespace(
        manifest.namespace, source_kind=semantics.source_kind
    )
    return {
        "catalog_namespace": REMOTE_CATALOG_NAMESPACE,
        "namespace": manifest.namespace,
        "action": "unknown_until_approved",
        "remote_catalog_state": "unknown_until_approved",
        "manual_semantics_preservation": "unknown_until_approved",
        "source_kind": semantics.source_kind,
        "region": region,
        "vector_dimensions": 384,
        **ranking,
    }


def verify_written_plan(plan_path: Path, state_root: Path, expected_plan_id: str) -> None:
    """Require complete ordinary artifacts to pass the existing apply verifier."""

    from buoy_search.apply import load_verified_apply_plan

    verified = load_verified_apply_plan(
        plan_path=plan_path,
        namespace=None,
        state_root=state_root,
    )
    if verified.plan.get("plan_id") != expected_plan_id:
        raise ValueError("verified plan ID does not match the generated plan")
    summary_path = plan_path.with_name("summary.json")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if not isinstance(summary, dict) or summary.get("plan_id") != expected_plan_id:
        raise ValueError("summary.json does not match the generated plan")
    pages_dir = plan_path.with_name("pages")
    if pages_dir.is_symlink() or not pages_dir.is_dir():
        raise ValueError("pages artifact directory is missing or unsafe")
    pages_root = pages_dir.resolve(strict=True)
    for page in verified.manifest.pages:
        relative_path = Path(page.content_path)
        if (
            relative_path.is_absolute()
            or not relative_path.parts
            or any(part in {"", ".", ".."} for part in relative_path.parts)
        ):
            raise ValueError("manifest page artifact is missing or unsafe")
        page_path = pages_dir / relative_path
        current = pages_dir
        for part in relative_path.parts:
            current /= part
            if current.is_symlink():
                raise ValueError("manifest page artifact is missing or unsafe")
        try:
            page_path.resolve(strict=True).relative_to(pages_root)
        except (OSError, ValueError) as exc:
            raise ValueError("manifest page artifact is missing or unsafe") from exc
        if not page_path.is_file():
            raise ValueError("manifest page artifact is missing or unsafe")
        if parse_markdown_file(page_path, pages_dir).source_hash != page.page_hash:
            raise ValueError("manifest page artifact content hash does not match")


def emit_progress(callback: ProgressCallback | None, stage: str, message: str) -> None:
    if callback is None:
        return
    clean_stage = sanitize_progress_text(stage, MAX_PROGRESS_STAGE_LENGTH) or "planning"
    clean_message = sanitize_progress_text(message, MAX_PROGRESS_MESSAGE_LENGTH)
    counts = {
        key: int(value)
        for key, value in _COUNT_PATTERN.findall(clean_message)
    }
    callback(PlanProgress(stage=clean_stage, message=clean_message, counts=counts))


def stage_from_message(message: str) -> str:
    prefix = message.partition(":")[0].strip().lower()
    return prefix or "planning"


def sanitize_progress_text(value: str, max_length: int) -> str:
    text = " ".join(str(value).split())
    if len(text) <= max_length:
        return text
    return text[:max_length]
