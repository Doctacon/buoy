"""Reusable local-only planning application service.

The service materializes source content and writes verified review artifacts. It
never embeds content, reads turbopuffer credentials, calls turbopuffer, or
updates applied state.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
from typing import Any, Callable

from buoy_search.applied_state import applied_state_paths, load_applied_state
from buoy_search.config import DEFAULT_EMBEDDING_PRECISION
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
)
from buoy_search.database_relation import DatabaseRelationError
from buoy_search.plan_artifacts import (
    DEFAULT_PLAN_EMBEDDING_MODEL,
    PlanArtifacts,
    build_plan_artifacts,
    site_id_for_url,
    verify_plan_artifacts,
    write_plan_artifacts,
)
from buoy_search.plan_cleanup import cleanup_superseded_plan_directories
from buoy_search.plan_diff import IncrementalPlanDiff

JsonObject = dict[str, Any]
MAX_PROGRESS_STAGE_LENGTH = 64
MAX_PROGRESS_MESSAGE_LENGTH = 500
_COUNT_PATTERN = re.compile(r"(?:^|[;\s])([a-z][a-z0-9_]*)=(\d+)(?=$|[;/\s])")
_DATABASE_KINDS = {"duckdb_relation", "bigquery_relation", "snowflake_relation"}


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
        request: PlanningRequest,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> PlanningResult:
        result = self._plan_to_directory(request, progress_callback=progress_callback)
        emit_progress(
            progress_callback,
            "complete",
            "plan: complete "
            f"pages={len(result.artifacts.manifest.pages)}; "
            f"chunks={len(result.artifacts.manifest.chunks)}; "
            f"upserts={len(result.artifacts.upsert_rows)}; "
            f"stale={len(result.artifacts.stale_rows)}; "
            f"routing_prototypes={len(result.artifacts.routing_prototypes)}",
        )
        return result

    def _plan_to_directory(
        self,
        request: PlanningRequest,
        *,
        progress_callback: ProgressCallback | None,
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

        emit_progress(progress_callback, "plan: preparing", f"plan: preparing {base_url}")
        options = CrawlOptions(
            base_url=base_url,
            out_dir=out_dir,
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
        crawl_summary = crawl_execution.summary
        namespace = request.namespace or str(crawl_summary["namespace_candidate"])

        site_id = site_id_for_url(base_url)
        state_path = applied_state_paths(
            site_id=site_id,
            namespace=namespace,
            state_root=request.state_root,
        ).database_path
        state_present = state_path.exists()
        state = load_applied_state(
            site_id=site_id,
            namespace=namespace,
            base_url=base_url,
            state_root=request.state_root,
        )

        emit_progress(progress_callback, "diff", "plan: diffing against local state")
        diff_started_at = observe_monotonic()
        emit_progress(progress_callback, "artifacts", "plan: building compact delta artifacts")
        artifact_started_at = observe_monotonic()
        artifacts = self._artifact_builder(
            indexing_plan=crawl_execution.indexing_plan,
            base_url=base_url,
            out_dir=out_dir,
            namespace=namespace,
            crawl_options=plan_crawl_options(request, crawl_summary, max_pages, max_chunks),
            chunk_options=plan_chunk_options(request),
            embedding_model=DEFAULT_PLAN_EMBEDDING_MODEL,
            embedding_precision=request.embedding_precision,
            state_root=request.state_root,
            applied_state=state,
            state_present=state_present,
            source_summary=crawl_summary,
        )
        diff = artifacts.diff
        diff_seconds = elapsed_since(diff_started_at)
        artifact_seconds = elapsed_since(artifact_started_at)
        emit_progress(progress_callback, "write", "plan: writing review artifacts")
        publication_started_at = observe_monotonic()
        self._artifact_writer(artifacts, out_dir)
        remove_source_staging(out_dir)
        if {path.name for path in out_dir.iterdir()} != {"plan.json", "delta.duckdb"}:
            raise ValueError("successful compact plan output must contain exactly plan.json and delta.duckdb")
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
        )
        self._artifact_verifier(
            out_dir / "plan.json", request.state_root, artifacts.plan.plan_id
        )

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
            "plan_path": str(Path(str(crawl_summary["out_dir"])) / "plan.json"),
            "delta_filename": "delta.duckdb",
            "state_first_apply": state_first_apply,
            "applied_state": plan_dict["applied_state"],
            "source": plan_dict["source"],
            "embedding_model": plan_dict["embedding_model"],
            "embedding_precision": plan_dict["embedding_precision"],
            "artifact_hash": plan_dict["artifact_hash"],
            "routing_prototypes": plan_dict["routing_prototypes"],
            "routing_prototype_review": [
                dict(row) for row in artifacts.routing_prototypes
            ],
            "diff": diff_summary,
            **diff_summary,
        }
    )
    if originating_job_id is not None:
        summary["originating_job_id"] = originating_job_id
    return summary


def verify_written_plan(plan_path: Path, state_root: Path, expected_plan_id: str) -> None:
    """Require complete compact artifacts to pass logical verification."""

    del state_root
    verified = verify_plan_artifacts(plan_path)
    if verified.plan.get("plan_id") != expected_plan_id:
        raise ValueError("verified plan ID does not match the generated plan")


def remove_source_staging(out_dir: Path) -> None:
    """Remove only known private acquisition roots after compact artifacts exist."""

    for name in ("pages", "repo-checkout"):
        path = out_dir / name
        if path.is_symlink():
            raise ValueError(f"source staging path is an unsafe symlink: {path}")
        if path.is_dir():
            shutil.rmtree(path)
    summary = out_dir / "summary.json"
    if summary.is_symlink():
        raise ValueError(f"source staging path is an unsafe symlink: {summary}")
    if summary.is_file():
        summary.unlink()


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
