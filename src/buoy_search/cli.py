"""Command-line interface for website RAG planning, apply, retrieval, and evals."""

from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
from typing import TextIO, Sequence

from buoy_search import __version__
from buoy_search.applied_state import AppliedStateError, resolve_state_root
from buoy_search.apply import (
    ApplyPlanError,
    apply_preflight_summary,
    discover_latest_plan_path,
    load_verified_apply_plan,
    run_approved_apply,
)
from buoy_search.catalog import CatalogError, load_routing_embedder
from buoy_search.catalog_pending import CatalogCommitPartialSuccess
from buoy_search.catalog_cli import configure_catalog_parser
from buoy_search.config import (
    DEFAULT_EMBEDDING_PRECISION,
    DEFAULT_REGION,
    EMBEDDING_PRECISIONS,
    RuntimeConfigError,
    load_config,
    removed_embedding_environment_error,
)
from buoy_search.crawler import (
    CRAWL_STRATEGIES,
    DEFAULT_CRAWL_CONCURRENT_REQUESTS,
    DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN,
    DEFAULT_CRAWL_DOWNLOAD_DELAY,
    DEFAULT_CRAWL_MAX_CHUNKS,
    DEFAULT_CRAWL_MAX_PAGES,
    DEFAULT_CRAWL_STRATEGY,
    DEFAULT_DOCS_VERSION_POLICY,
    DEFAULT_LANGUAGE_POLICY,
    DEFAULT_GITHUB_REPO_MAX_CHUNKS,
    DEFAULT_GITHUB_REPO_MAX_FILE_BYTES,
    DEFAULT_GITHUB_REPO_MAX_FILES,
    DOCS_VERSION_POLICIES,
    LANGUAGE_POLICIES,
    GitHubRepoSource,
    LocalFileSource,
    PdfSource,
    CrawlOptions,
    crawl_local_document,
    crawl_site,
    default_out_dir,
    detect_source,
)
from buoy_search.github_repo import GitHubRepoError, crawl_github_repo
from buoy_search.database_relation import DatabaseRelationError
from buoy_search.repo_syntax_chunking import REPO_CHUNKING_ARMS
from buoy_search.evals import (
    build_dry_run_eval_report,
    load_eval_cases,
    run_live_evals,
)
from buoy_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
)
from buoy_search.plan_cleanup import cleanup_applied_plan_directory
from buoy_search.plan_diff import PlanDiffError
from buoy_search.planning_service import PlanProgress, PlanningRequest, PlanningService
from buoy_search.namespaces import list_namespace_ids
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    CompatibilityContract,
    RemoteCatalogError,
    create_client,
    read_remote_catalog,
    require_eligible,
)
from buoy_search.retriever import (
    DEFAULT_CANDIDATES,
    DEFAULT_TOP_K,
    HybridRetriever,
    MultiNamespaceRetriever,
    MultiNamespaceRetrievalPlan,
    MultiNamespaceRetrievalResult,
    RetrievalOptions,
    RetrievalPlan,
    RetrievalResult,
    multi_namespace_retrieval_plan,
    ranking_defaults_for_namespace,
    retrieval_plan,
)
from buoy_search.routing import (
    DEFAULT_ROUTE_TOP_K,
    MAX_ROUTE_TOP_K,
    AutomaticRoutingError,
    RoutedRetrievalPlan,
    RoutedRetrievalResult,
    hybrid_route,
)


REMOTE_CATALOG_CLIENT_FACTORY = create_client


class OneLineProgress:
    """Tiny stderr progress renderer that reuses one terminal line."""

    def __init__(
        self,
        *,
        enabled: bool,
        stream: TextIO | None = None,
        min_interval: float = 0.2,
        terminal_width: int | None = None,
    ) -> None:
        self.enabled = enabled
        self.stream = stream or sys.stderr
        self.min_interval = min_interval
        self.terminal_width = terminal_width
        self._last_update = 0.0
        self._wrote = False

    def update(self, message: str, *, force: bool = False) -> None:
        if not self.enabled:
            return
        now = time.monotonic()
        if not force and now - self._last_update < self.min_interval:
            return
        self._last_update = now
        try:
            self.stream.write(f"\r\x1b[K{self._fit_message(message)}")
            self.stream.flush()
        except Exception:
            # Progress is advisory; a broken stderr must not affect the command.
            self.enabled = False
            self._wrote = False
            return
        self._wrote = True

    def _fit_message(self, message: str) -> str:
        width = self.terminal_width or shutil.get_terminal_size(fallback=(80, 20)).columns
        max_width = max(1, width - 1)
        if len(message) <= max_width:
            return message
        if max_width <= 3:
            return message[:max_width]
        return f"{message[: max_width - 3]}..."

    def finish(self) -> None:
        if not self.enabled or not self._wrote:
            return
        try:
            self.stream.write("\r\x1b[K")
            self.stream.flush()
        except Exception:
            # Progress is advisory; a broken stderr must not affect the command.
            self.enabled = False
            self._wrote = False
            return
        self._wrote = False


def should_show_progress(args: argparse.Namespace) -> bool:
    return (
        not bool(getattr(args, "json", False))
        and not bool(getattr(args, "no_progress", False))
        and sys.stderr.isatty()
    )


def add_database_source_arguments(command_parser: argparse.ArgumentParser) -> None:
    command_parser.add_argument(
        "--database-backend",
        choices=("duckdb", "bigquery", "snowflake"),
        default=None,
        help="Database relation backend. DuckDB is inferred for backward-compatible local-path commands.",
    )
    command_parser.add_argument(
        "--relation",
        "--table",
        dest="relation",
        default=None,
        help="One already-shaped database table or view; BigQuery and Snowflake require three components.",
    )
    command_parser.add_argument(
        "--source-id",
        default=None,
        help="Stable logical database source ID matching lowercase letters/digits separated by single hyphens.",
    )
    command_parser.add_argument(
        "--id-column",
        default=None,
        help="Document ID column (default: document_id).",
    )
    command_parser.add_argument(
        "--content-column",
        default=None,
        help="Document content column (default: content).",
    )
    command_parser.add_argument(
        "--title-column",
        default=None,
        help="Title column; otherwise auto-detect title and fall back to document ID.",
    )
    command_parser.add_argument(
        "--bigquery-project",
        default=None,
        help="BigQuery query-job/billing project (uses Application Default Credentials).",
    )
    command_parser.add_argument(
        "--bigquery-location",
        default=None,
        help="BigQuery job location.",
    )
    command_parser.add_argument(
        "--bigquery-maximum-bytes-billed",
        type=positive_int,
        default=None,
        metavar="BYTES",
        help="BigQuery dry-run and query billing cap in bytes.",
    )
    command_parser.add_argument(
        "--snowflake-connection",
        default=None,
        help="Snowflake named connection profile (credentials remain in Snowflake configuration).",
    )
    command_parser.add_argument(
        "--source-query-timeout",
        type=positive_float,
        default=None,
        metavar="SECONDS",
        help="BigQuery or Snowflake source query timeout in seconds.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buoy",
        description="Plan website, repository, document, DuckDB, BigQuery, and Snowflake sources. Planning is local-only with respect to turbopuffer; remote warehouses authenticate only to the source.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="crawl a website, repository, local document, or one DuckDB/BigQuery/Snowflake relation; always dry-run",
        description=(
            "Crawl an HTTP(S) website, ingest a public GitHub repository or local document, or read "
            "one document-shaped DuckDB, BigQuery, or Snowflake table/view. Remote database sources "
            "use source credentials and APIs only; this command never reads turbopuffer credentials "
            "or writes to turbopuffer."
        ),
    )
    crawl_parser.add_argument(
        "--base-url",
        required=False,
        metavar="SOURCE",
        help="Website/repository/local document source or DuckDB filepath; omit for BigQuery and Snowflake.",
    )
    add_database_source_arguments(crawl_parser)
    crawl_parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Local output directory. Defaults to artifacts/site-crawls/<host>.",
    )
    crawl_parser.add_argument(
        "--max-pages",
        type=positive_int,
        default=None,
        help=(
            "Maximum pages/files/documents to process. Defaults: "
            f"websites and database relations={DEFAULT_CRAWL_MAX_PAGES}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_FILES}."
        ),
    )
    crawl_parser.add_argument(
        "--max-chunks",
        type=positive_int,
        default=None,
        help=(
            "Maximum chunks to generate. Defaults: "
            f"websites={DEFAULT_CRAWL_MAX_CHUNKS}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_CHUNKS}."
        ),
    )
    crawl_parser.add_argument(
        "--repo-max-file-bytes",
        type=positive_int,
        default=DEFAULT_GITHUB_REPO_MAX_FILE_BYTES,
        help="GitHub repo only: maximum bytes per text file to include before chunking.",
    )
    crawl_parser.add_argument(
        "--repo-chunking-arm",
        choices=REPO_CHUNKING_ARMS,
        default=None,
        help="GitHub repo only: opt into one local Python syntax chunking experiment arm.",
    )
    crawl_parser.add_argument(
        "--repo-search-metadata",
        action="store_true",
        help="GitHub repo only: include searchable path and Python symbol metadata in generated code pages.",
    )
    crawl_parser.add_argument(
        "--repo-file-cards",
        action="store_true",
        help="GitHub repo only: add separate searchable file metadata card pages without changing code chunks.",
    )
    crawl_parser.add_argument(
        "--repo-oversize-file-cards",
        action="store_true",
        help="GitHub repo only: add metadata card pages for oversize files that are skipped for code chunking.",
    )
    crawl_parser.add_argument(
        "--concurrent-requests",
        type=positive_int,
        default=DEFAULT_CRAWL_CONCURRENT_REQUESTS,
        help="Global Scrapling crawl concurrency.",
    )
    crawl_parser.add_argument(
        "--concurrent-requests-per-domain",
        type=positive_int,
        default=DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN,
        help="Per-domain Scrapling crawl concurrency.",
    )
    crawl_parser.add_argument(
        "--download-delay",
        type=nonnegative_float,
        default=DEFAULT_CRAWL_DOWNLOAD_DELAY,
        help="Polite delay between crawl requests in seconds.",
    )
    crawl_parser.add_argument(
        "--crawl-strategy",
        choices=CRAWL_STRATEGIES,
        default=DEFAULT_CRAWL_STRATEGY,
        help=(
            "Discovery mode. Default: sitemap, which uses sitemap pages and falls back to link crawl only when empty. "
            "hybrid merges sitemap pages with same-site link discovery; link ignores sitemaps."
        ),
    )
    crawl_parser.add_argument(
        "--docs-version-policy",
        choices=DOCS_VERSION_POLICIES,
        default=DEFAULT_DOCS_VERSION_POLICY,
        help=(
            "Website sitemap docs-version handling. Default: warn detects repeated /docs/{version}/ "
            "families and stops before crawling; latest, stable-latest, and latest-nightly add effective excludes; "
            "all keeps every version."
        ),
    )
    crawl_parser.add_argument(
        "--language-policy",
        choices=LANGUAGE_POLICIES,
        default=DEFAULT_LANGUAGE_POLICY,
        help=(
            "Website sitemap language handling. Default: english keeps unprefixed/en pages and excludes "
            "detected non-English locale prefixes; all keeps every language."
        ),
    )
    crawl_parser.add_argument(
        "--include-path",
        action="append",
        default=[],
        help="Optional URL path glob to include, repeatable. Example: /docs/**. Defaults to all same-site paths.",
    )
    crawl_parser.add_argument(
        "--exclude-path",
        action="append",
        default=[],
        help="Optional URL path glob to exclude, repeatable. Example: /llms-full.txt.",
    )
    crawl_parser.add_argument(
        "--keep-trailing-slash",
        action="store_false",
        dest="strip_trailing_slash",
        default=True,
        help="Preserve trailing-slash URL variants instead of canonicalizing /path/ to /path.",
    )
    crawl_parser.add_argument(
        "--css-selector",
        default=None,
        help=(
            "Optional CSS selector passed to Scrapling extraction to scope content, "
            "e.g. article or .md-content__inner."
        ),
    )
    crawl_parser.add_argument(
        "--target-tokens",
        type=positive_int,
        default=DEFAULT_TARGET_TOKENS,
        help="Approximate target tokens per generated chunk.",
    )
    crawl_parser.add_argument(
        "--overlap-sentences",
        type=nonnegative_int,
        default=DEFAULT_OVERLAP_SENTENCES,
        help="Number of trailing sentences to overlap between adjacent chunks.",
    )
    crawl_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text summary is used by default.",
    )
    crawl_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the default one-line interactive progress indicator.",
    )
    crawl_parser.set_defaults(func=_run_crawl)

    plan_parser = subparsers.add_parser(
        "plan",
        help="plan a website, repository, local document, or one DuckDB/BigQuery/Snowflake relation; no turbopuffer writes",
        description=(
            "Materialize one source into reviewable local plan artifacts. BigQuery uses Application "
            "Default Credentials and Snowflake uses a named connection during planning only. Source "
            "warehouse API calls occur, but turbopuffer credentials are not read and turbopuffer is not called."
        ),
    )
    plan_parser.add_argument(
        "url",
        nargs="?",
        metavar="SOURCE",
        help="Website/repository/local document source or DuckDB filepath; omit for BigQuery and Snowflake.",
    )
    plan_parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="Absolute http(s) URL, public GitHub repo URL, or supported local document filepath to crawl and plan. Kept for backwards compatibility; positional source is preferred.",
    )
    add_database_source_arguments(plan_parser)
    plan_parser.add_argument(
        "--out-dir",
        type=Path,
        default=None,
        help="Local output directory. Defaults to artifacts/site-crawls/<host>-plan.",
    )
    plan_parser.add_argument(
        "--namespace",
        default=None,
        help="Stable target namespace for diffing state. Defaults to the deterministic site namespace candidate.",
    )
    plan_parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Local applied-state root. Defaults to .buoy, with in-place .turbo-search fallback for existing projects.",
    )
    plan_parser.add_argument(
        "--embedding-precision",
        choices=EMBEDDING_PRECISIONS,
        default=DEFAULT_EMBEDDING_PRECISION,
        help="Local embedding inference precision recorded in the plan. Default: float32.",
    )
    plan_parser.add_argument(
        "--max-pages",
        type=positive_int,
        default=None,
        help=(
            "Maximum pages/files/documents to process. Defaults: "
            f"websites and database relations={DEFAULT_CRAWL_MAX_PAGES}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_FILES}."
        ),
    )
    plan_parser.add_argument(
        "--max-chunks",
        type=positive_int,
        default=None,
        help=(
            "Maximum chunks to generate. Defaults: "
            f"websites={DEFAULT_CRAWL_MAX_CHUNKS}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_CHUNKS}."
        ),
    )
    plan_parser.add_argument(
        "--repo-max-file-bytes",
        type=positive_int,
        default=DEFAULT_GITHUB_REPO_MAX_FILE_BYTES,
        help="GitHub repo only: maximum bytes per text file to include before chunking.",
    )
    plan_parser.add_argument(
        "--repo-chunking-arm",
        choices=REPO_CHUNKING_ARMS,
        default=None,
        help="GitHub repo only: opt into one local Python syntax chunking experiment arm.",
    )
    plan_parser.add_argument(
        "--repo-search-metadata",
        action="store_true",
        help="GitHub repo only: include searchable path and Python symbol metadata in generated code pages.",
    )
    plan_parser.add_argument(
        "--repo-file-cards",
        action="store_true",
        help="GitHub repo only: add separate searchable file metadata card pages without changing code chunks.",
    )
    plan_parser.add_argument(
        "--repo-oversize-file-cards",
        action="store_true",
        help="GitHub repo only: add metadata card pages for oversize files that are skipped for code chunking.",
    )
    plan_parser.add_argument(
        "--concurrent-requests",
        type=positive_int,
        default=DEFAULT_CRAWL_CONCURRENT_REQUESTS,
        help="Global Scrapling crawl concurrency.",
    )
    plan_parser.add_argument(
        "--concurrent-requests-per-domain",
        type=positive_int,
        default=DEFAULT_CRAWL_CONCURRENT_REQUESTS_PER_DOMAIN,
        help="Per-domain Scrapling crawl concurrency.",
    )
    plan_parser.add_argument(
        "--download-delay",
        type=nonnegative_float,
        default=DEFAULT_CRAWL_DOWNLOAD_DELAY,
        help="Polite delay between crawl requests in seconds.",
    )
    plan_parser.add_argument(
        "--crawl-strategy",
        choices=CRAWL_STRATEGIES,
        default=DEFAULT_CRAWL_STRATEGY,
        help=(
            "Discovery mode. Default: sitemap, which uses sitemap pages and falls back to link crawl only when empty. "
            "hybrid merges sitemap pages with same-site link discovery; link ignores sitemaps."
        ),
    )
    plan_parser.add_argument(
        "--docs-version-policy",
        choices=DOCS_VERSION_POLICIES,
        default=DEFAULT_DOCS_VERSION_POLICY,
        help=(
            "Website sitemap docs-version handling. Default: warn detects repeated /docs/{version}/ "
            "families and stops before crawling; latest, stable-latest, and latest-nightly add effective excludes; "
            "all keeps every version."
        ),
    )
    plan_parser.add_argument(
        "--language-policy",
        choices=LANGUAGE_POLICIES,
        default=DEFAULT_LANGUAGE_POLICY,
        help=(
            "Website sitemap language handling. Default: english keeps unprefixed/en pages and excludes "
            "detected non-English locale prefixes; all keeps every language."
        ),
    )
    plan_parser.add_argument(
        "--include-path",
        action="append",
        default=[],
        help="Optional URL path glob to include, repeatable. Example: /docs/**. Defaults to all same-site paths.",
    )
    plan_parser.add_argument(
        "--exclude-path",
        action="append",
        default=[],
        help="Optional URL path glob to exclude, repeatable. Example: /llms-full.txt.",
    )
    plan_parser.add_argument(
        "--keep-trailing-slash",
        action="store_false",
        dest="strip_trailing_slash",
        default=True,
        help="Preserve trailing-slash URL variants instead of canonicalizing /path/ to /path.",
    )
    plan_parser.add_argument(
        "--css-selector",
        default=None,
        help=(
            "Optional CSS selector passed to Scrapling extraction to scope content, "
            "e.g. article or .md-content__inner."
        ),
    )
    plan_parser.add_argument(
        "--target-tokens",
        type=positive_int,
        default=DEFAULT_TARGET_TOKENS,
        help="Approximate target tokens per generated chunk.",
    )
    plan_parser.add_argument(
        "--overlap-sentences",
        type=nonnegative_int,
        default=DEFAULT_OVERLAP_SENTENCES,
        help="Number of trailing sentences to overlap between adjacent chunks.",
    )
    plan_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text summary is used by default.",
    )
    plan_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the default one-line interactive progress indicator.",
    )
    plan_parser.set_defaults(func=_run_plan)

    apply_parser = subparsers.add_parser(
        "apply",
        help="preflight and interactively apply a saved generic site RAG plan",
        description=(
            "Verify a saved plan artifact and recompute its local state diff. Plain interactive "
            "apply displays the complete local preflight, then prompts before any live work. "
            "Use --dry-run for prompt-free preflight or --approve for prompt-free automation."
        ),
    )
    apply_parser.add_argument(
        "--plan",
        type=Path,
        default=None,
        help="Path to a saved plan.json artifact. Defaults to the newest artifacts/site-crawls/**/plan.json.",
    )
    apply_parser.add_argument(
        "--namespace",
        default=None,
        help="Expected stable target namespace. Defaults to the namespace recorded in the plan.",
    )
    apply_parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Local applied-state root. Defaults to .buoy, with in-place .turbo-search fallback for existing projects.",
    )
    apply_parser.add_argument(
        "--region",
        default=None,
        help="Override TURBOPUFFER_REGION for apply and the registered retrieval contract.",
    )
    apply_parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=64,
        help="Turbopuffer upsert batch size for approved apply mode.",
    )
    apply_parser.add_argument(
        "--embedding-batch-size",
        type=positive_int,
        default=32,
        help="Local Sentence Transformers computation batch size for approved apply mode.",
    )
    apply_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Perform prompt-free local preflight without credentials, embeddings, or API calls.",
    )
    apply_parser.add_argument(
        "--approve",
        action="store_true",
        help="Bypass the prompt and run the confirmed apply path for automation.",
    )
    apply_parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="Plan stale deletion; execution still requires interactive confirmation or --approve.",
    )
    apply_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text summary is used by default.",
    )
    apply_parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable the default one-line interactive progress indicator.",
    )
    apply_parser.set_defaults(func=_run_apply)

    namespaces_parser = subparsers.add_parser(
        "namespaces",
        help="list and filter visible Turbopuffer namespace IDs",
        description=(
            "List namespace IDs visible to the configured Turbopuffer account and region. "
            "An optional search term filters IDs case-insensitively; namespace contents are not queried."
        ),
    )
    namespaces_parser.add_argument(
        "search",
        nargs="?",
        default=None,
        help="Optional case-insensitive substring to match against namespace IDs.",
    )
    namespaces_parser.add_argument(
        "--region",
        default=None,
        help="Override TURBOPUFFER_REGION for this command.",
    )
    namespaces_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text output lists one namespace ID per line.",
    )
    namespaces_parser.set_defaults(func=_run_namespaces)

    configure_catalog_parser(subparsers)

    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="retrieve relevant chunks through live automatic or explicit namespace routing",
        description=(
            "Execute hybrid retrieval by default. Without --namespace, Buoy discovers live namespaces "
            "and routes through the authenticated remote catalog. Explicit repeatable --namespace "
            "bypasses automatic routing. Use --dry-run/--plan for preview."
        ),
    )
    retrieve_parser.add_argument(
        "query",
        help="Question to retrieve relevant chunks for.",
    )
    retrieve_parser.add_argument(
        "--live",
        action="store_true",
        help="Compatibility no-op; retrieval is live by default. Conflicts with --dry-run/--plan.",
    )
    retrieve_parser.add_argument(
        "--dry-run",
        "--plan",
        dest="dry_run",
        action="store_true",
        help="Preview retrieval; automatic preview reads remote routing state, while explicit --namespace remains local and credential-free.",
    )
    retrieve_parser.add_argument(
        "--auto-route",
        action="store_true",
        help="Compatibility no-op; automatic remote routing is already the default without --namespace.",
    )
    retrieve_parser.add_argument(
        "--route-top-k",
        type=bounded_route_top_k,
        default=None,
        metavar="N",
        help=f"Maximum automatically routed namespaces (default {DEFAULT_ROUTE_TOP_K}, maximum {MAX_ROUTE_TOP_K}).",
    )
    retrieve_parser.add_argument(
        "--top-k",
        type=positive_int,
        default=DEFAULT_TOP_K,
        help="Number of fused chunks to return.",
    )
    retrieve_parser.add_argument(
        "--candidates",
        type=positive_int,
        default=DEFAULT_CANDIDATES,
        help="Candidate limit for each ANN/BM25 subquery before RRF fusion.",
    )
    retrieve_parser.add_argument(
        "--ranking-mode",
        choices=["file", "page", "chunk"],
        default=None,
        help="Final ranking mode. Default is namespace-aware: site-* uses page, other namespaces use file.",
    )
    retrieve_parser.add_argument(
        "--ranking-profile",
        choices=["repo-code", "none"],
        default=None,
        help="Final ranking profile. Default is namespace-aware: site-* uses none, other namespaces use repo-code.",
    )
    retrieve_parser.add_argument(
        "--ranking-pool",
        type=positive_int,
        default=None,
        help="Number of fused candidates to consider during final file/page ranking. Default is 20 for site-* and 100 otherwise.",
    )
    retrieve_parser.add_argument(
        "--ranking-aggregation",
        choices=["max", "adaptive-sum-3", "capped-sum-3"],
        default=None,
        help="Group scoring for file/page ranking. Repo default adaptive-sum-3 adds a small close-chunk bonus; site default max uses the best page chunk.",
    )
    retrieve_parser.add_argument(
        "--doc-kind",
        default=None,
        help="Optional doc_kind filter, e.g. blog, library, platform, integrations.",
    )
    add_runtime_config_arguments(retrieve_parser, repeatable_namespace=True)
    retrieve_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text output is used by default for live results.",
    )
    retrieve_parser.set_defaults(func=_run_retrieve)

    evals_parser = subparsers.add_parser(
        "evals",
        help="list or run retrieval smoke evals for a namespace",
        description=(
            "List or execute hand-authored retrieval smoke evals for the configured namespace. "
            "Default mode is safe: it lists eval questions and expected source hints without "
            "credentials, embeddings, or turbopuffer calls. Pass --live to run retrieval "
            "against turbopuffer."
        ),
    )
    evals_parser.add_argument(
        "--live",
        action="store_true",
        help="Execute live evals. Reads TURBOPUFFER_API_KEY from the environment and calls turbopuffer.",
    )
    evals_parser.add_argument(
        "--dry-run",
        "--list",
        dest="dry_run",
        action="store_true",
        help="List eval questions and expected hints without credentials or turbopuffer API calls (default).",
    )
    evals_parser.add_argument(
        "--top-k",
        type=positive_int,
        default=DEFAULT_TOP_K,
        help="Number of fused chunks to score for each eval question.",
    )
    evals_parser.add_argument(
        "--candidates",
        type=positive_int,
        default=DEFAULT_CANDIDATES,
        help="Candidate limit for each ANN/BM25 subquery before RRF fusion.",
    )
    evals_parser.add_argument(
        "--ranking-mode",
        choices=["file", "page", "chunk"],
        default=None,
        help="Final ranking mode. Default is namespace-aware: site-* uses page, other namespaces use file.",
    )
    evals_parser.add_argument(
        "--ranking-profile",
        choices=["repo-code", "none"],
        default=None,
        help="Final ranking profile. Default is namespace-aware: site-* uses none, other namespaces use repo-code.",
    )
    evals_parser.add_argument(
        "--ranking-pool",
        type=positive_int,
        default=None,
        help="Number of fused candidates to consider during final file/page ranking. Default is 20 for site-* and 100 otherwise.",
    )
    evals_parser.add_argument(
        "--ranking-aggregation",
        choices=["max", "adaptive-sum-3", "capped-sum-3"],
        default=None,
        help="Group scoring for file/page ranking. Repo default adaptive-sum-3 adds a small close-chunk bonus; site default max uses the best page chunk.",
    )
    evals_parser.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="Optional path to a JSON eval dataset. Defaults to the built-in Scrapling docs smoke set; pass a site-specific dataset for other namespaces.",
    )
    add_runtime_config_arguments(evals_parser)
    evals_parser.add_argument(
        "--json",
        action="store_true",
        help="Print JSON output. Text output is used by default.",
    )
    evals_parser.set_defaults(func=_run_evals)

    serve_parser = subparsers.add_parser(
        "serve",
        help="run local Command Center reviews and credential-free HTTP(S)/public GitHub planning",
        description=(
            "Run Command Center on an explicitly loopback-only address. Reviews remain read-only; "
            "one managed credential-free HTTP(S) website or public GitHub repository-root plan may run "
            "at a time and writes only local plan artifacts. Website syntax validation is not a "
            "public-routability or SSRF firewall. Apply remains an explicit CLI action."
        ),
    )
    serve_parser.add_argument(
        "--host",
        type=loopback_host,
        default="127.0.0.1",
        help="Loopback bind host: 127.0.0.1, localhost, or ::1 (default: 127.0.0.1).",
    )
    serve_parser.add_argument(
        "--port",
        type=tcp_port,
        default=8765,
        help="Loopback TCP port (default: 8765).",
    )
    serve_parser.add_argument(
        "--artifacts-root",
        type=Path,
        default=Path("artifacts/site-crawls"),
        help="Root containing saved plans and managed command-center/plans artifacts (default: artifacts/site-crawls).",
    )
    serve_parser.add_argument(
        "--state-root",
        type=Path,
        default=None,
        help="Local applied-state and durable command-center/jobs root. Defaults to .buoy, with in-place .turbo-search fallback for existing projects.",
    )
    serve_parser.add_argument(
        "--no-browser",
        action="store_false",
        dest="browser",
        default=True,
        help="Do not open the Command Center in the default browser.",
    )
    serve_parser.set_defaults(func=_run_serve)

    return parser


def add_runtime_config_arguments(
    command_parser: argparse.ArgumentParser,
    *,
    repeatable_namespace: bool = False,
) -> None:
    """Add non-secret turbopuffer runtime overrides to a command."""

    command_parser.add_argument(
        "--region",
        default=None,
        help="Override TURBOPUFFER_REGION for this command without changing the environment.",
    )
    command_parser.add_argument(
        "--namespace",
        action="append" if repeatable_namespace else "store",
        default=None,
        help=(
            "Select a namespace; repeat to retrieve across multiple namespaces. This is the sole "
            "routing bypass; TURBOPUFFER_NAMESPACE is ignored."
            if repeatable_namespace
            else "Override TURBOPUFFER_NAMESPACE for this command without changing the environment."
        ),
    )
    command_parser.add_argument(
        "--embedding-model",
        default=None,
        help="Override BUOY_EMBEDDING_MODEL for this command.",
    )
    command_parser.add_argument(
        "--embedding-precision",
        choices=EMBEDDING_PRECISIONS,
        default=None,
        help="Override BUOY_EMBEDDING_PRECISION for this command.",
    )


def config_from_args(
    args: argparse.Namespace,
    *,
    ignore_environment_namespace: bool = False,
):
    """Load non-secret runtime config, applying CLI overrides when supplied."""

    config = load_config(ignore_environment_namespace=ignore_environment_namespace)
    namespace_override = args.namespace
    if isinstance(namespace_override, list):
        namespace_override = namespace_override[0] if namespace_override else None
    return replace(
        config,
        region=args.region or config.region,
        namespace=namespace_override or config.namespace,
        embedding_model=args.embedding_model or config.embedding_model,
        embedding_precision=args.embedding_precision or config.embedding_precision,
    )


def resolve_retrieval_namespaces(args: argparse.Namespace) -> list[str]:
    """Validate explicit CLI namespaces; environment namespace is never retrieval authority."""

    cli_namespaces = args.namespace if isinstance(args.namespace, list) else []
    namespaces = [namespace.strip() for namespace in cli_namespaces]
    if any(not namespace for namespace in namespaces):
        raise ValueError("--namespace must contain a non-empty namespace ID.")
    duplicate = next(
        (namespace for index, namespace in enumerate(namespaces) if namespace in namespaces[:index]),
        None,
    )
    if duplicate is not None:
        raise ValueError(f"--namespace must not repeat namespace ID {duplicate!r}.")
    return namespaces


def resolve_cli_state_root(args: argparse.Namespace) -> bool:
    """Resolve an implicit plan/apply state root and emit warnings on stderr."""

    try:
        state_root, warning = resolve_state_root(args.state_root)
    except AppliedStateError as exc:
        try:
            print(str(exc), file=sys.stderr)
        except OSError:
            pass
        return False
    args.state_root = state_root
    if warning is not None:
        try:
            print(warning, file=sys.stderr)
        except OSError:
            pass
    return True


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def loopback_host(value: str) -> str:
    if value not in {"127.0.0.1", "localhost", "::1"}:
        raise argparse.ArgumentTypeError("must be one of: 127.0.0.1, localhost, ::1")
    return value


def tcp_port(value: str) -> int:
    parsed = int(value)
    if parsed < 1 or parsed > 65_535:
        raise argparse.ArgumentTypeError("must be between 1 and 65535")
    return parsed


def bounded_route_top_k(value: str) -> int:
    parsed = positive_int(value)
    if parsed > MAX_ROUTE_TOP_K:
        raise argparse.ArgumentTypeError(f"must be no greater than {MAX_ROUTE_TOP_K}")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def positive_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("must be a finite value greater than zero")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or greater")
    return parsed


def ranking_profile_from_cli(value: str) -> str:
    return value.replace("-", "_")


def ranking_aggregation_from_cli(value: str) -> str:
    return value.replace("-", "_")


def retrieval_options_from_args(
    args: argparse.Namespace,
    *,
    config: RuntimeConfig,
    doc_kind: str | None = None,
) -> RetrievalOptions:
    defaults = ranking_defaults_for_namespace(config.namespace)
    ranking_profile = args.ranking_profile or str(defaults["ranking_profile"]).replace("_", "-")
    ranking_aggregation = args.ranking_aggregation or str(defaults["ranking_aggregation"]).replace("_", "-")
    return RetrievalOptions(
        top_k=args.top_k,
        candidates=args.candidates,
        doc_kind=doc_kind,
        ranking_mode=args.ranking_mode or str(defaults["ranking_mode"]),
        ranking_profile=ranking_profile_from_cli(ranking_profile),
        ranking_pool=args.ranking_pool or int(defaults["ranking_pool"]),
        ranking_aggregation=ranking_aggregation_from_cli(ranking_aggregation),
    )


def routed_retrieval_options_from_args(args: argparse.Namespace, *, card) -> RetrievalOptions:
    """Apply each supplied ranking override independently over one card contract."""

    return RetrievalOptions(
        top_k=args.top_k,
        candidates=args.candidates,
        doc_kind=args.doc_kind,
        ranking_mode=args.ranking_mode or card.ranking_mode,
        ranking_profile=(
            ranking_profile_from_cli(args.ranking_profile)
            if args.ranking_profile is not None
            else card.ranking_profile
        ),
        ranking_pool=args.ranking_pool if args.ranking_pool is not None else card.ranking_pool,
        ranking_aggregation=(
            ranking_aggregation_from_cli(args.ranking_aggregation)
            if args.ranking_aggregation is not None
            else card.ranking_aggregation
        ),
    )


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


DATABASE_RELATION_KINDS = {"duckdb_relation", "bigquery_relation", "snowflake_relation"}


def _is_database_source(source: object) -> bool:
    return getattr(source, "kind", None) in DATABASE_RELATION_KINDS


def source_from_cli_args(args: argparse.Namespace, requested_source: str | None) -> object:
    database_flags = {
        "--database-backend": args.database_backend,
        "--source-id": args.source_id,
        "--id-column": args.id_column,
        "--content-column": args.content_column,
        "--title-column": args.title_column,
        "--bigquery-project": args.bigquery_project,
        "--bigquery-location": args.bigquery_location,
        "--bigquery-maximum-bytes-billed": args.bigquery_maximum_bytes_billed,
        "--snowflake-connection": args.snowflake_connection,
        "--source-query-timeout": args.source_query_timeout,
    }
    if args.relation is None:
        supplied = [flag for flag, value in database_flags.items() if value is not None]
        if supplied:
            raise ValueError(
                f"{', '.join(supplied)} require --relation to activate database relation mode."
            )
        if requested_source is None:
            raise ValueError("source URL/path is required.")
        return detect_source(requested_source)

    backend = args.database_backend or "duckdb"
    if args.source_id is None:
        raise ValueError("--source-id is required when --relation activates database relation mode.")
    if backend != "bigquery":
        supplied = [
            flag
            for flag, value in {
                "--bigquery-project": args.bigquery_project,
                "--bigquery-location": args.bigquery_location,
                "--bigquery-maximum-bytes-billed": args.bigquery_maximum_bytes_billed,
            }.items()
            if value is not None
        ]
        if supplied:
            raise ValueError(f"{', '.join(supplied)} are supported only with --database-backend bigquery.")
    if backend != "snowflake" and args.snowflake_connection is not None:
        raise ValueError(
            "--snowflake-connection is supported only with --database-backend snowflake."
        )
    if backend == "duckdb" and args.source_query_timeout is not None:
        raise ValueError(
            "--source-query-timeout is supported only with BigQuery or Snowflake database backends."
        )

    id_column = "document_id" if args.id_column is None else args.id_column
    content_column = "content" if args.content_column is None else args.content_column
    operation = str(args.command or "plan")
    if backend == "duckdb":
        if requested_source is None:
            raise ValueError("DuckDB database filepath is required when --relation is used.")
        from buoy_search.duckdb_relation import duckdb_relation_source

        return duckdb_relation_source(
            requested_source,
            relation=args.relation,
            source_id=args.source_id,
            id_column=id_column,
            content_column=content_column,
            title_column=args.title_column,
        )
    if requested_source is not None:
        raise ValueError(
            f"A local source path/--base-url is not accepted with --database-backend {backend}."
        )
    if backend == "bigquery":
        from buoy_search.bigquery_relation import bigquery_relation_source

        return bigquery_relation_source(
            relation=args.relation,
            source_id=args.source_id,
            id_column=id_column,
            content_column=content_column,
            title_column=args.title_column,
            query_project=args.bigquery_project,
            location=args.bigquery_location,
            maximum_bytes_billed=args.bigquery_maximum_bytes_billed,
            query_timeout=args.source_query_timeout or 300.0,
            operation=operation,
        )
    if args.snowflake_connection is None:
        raise ValueError("--snowflake-connection is required for Snowflake database mode.")
    from buoy_search.snowflake_relation import snowflake_relation_source

    return snowflake_relation_source(
        relation=args.relation,
        source_id=args.source_id,
        connection_name=args.snowflake_connection,
        id_column=id_column,
        content_column=content_column,
        title_column=args.title_column,
        query_timeout=args.source_query_timeout or 300.0,
        operation=operation,
    )


def _apply_source_cap_defaults(args: argparse.Namespace, source: object) -> None:
    if args.max_pages is None:
        args.max_pages = DEFAULT_GITHUB_REPO_MAX_FILES if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_PAGES
    if args.max_chunks is None:
        args.max_chunks = DEFAULT_GITHUB_REPO_MAX_CHUNKS if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_CHUNKS


def crawl_source(source: object, options: CrawlOptions) -> dict[str, object]:
    source_kind = getattr(source, "kind", None)
    if source_kind == "duckdb_relation":
        from buoy_search.duckdb_relation import crawl_duckdb_relation

        return crawl_duckdb_relation(source, options)  # type: ignore[arg-type]
    if source_kind == "bigquery_relation":
        from buoy_search.bigquery_relation import crawl_bigquery_relation

        return crawl_bigquery_relation(source, options)  # type: ignore[arg-type]
    if source_kind == "snowflake_relation":
        from buoy_search.snowflake_relation import crawl_snowflake_relation

        return crawl_snowflake_relation(source, options)  # type: ignore[arg-type]
    if isinstance(source, GitHubRepoSource):
        return crawl_github_repo(source, options)
    if isinstance(source, (PdfSource, LocalFileSource)):
        return crawl_local_document(source, options)
    return crawl_site(options)


def _run_serve(args: argparse.Namespace) -> int:
    if not resolve_cli_state_root(args):
        return 2
    from buoy_search.command_center_server import (
        CommandCenterDependencyError,
        run_server,
    )

    try:
        run_server(
            host=args.host,
            port=args.port,
            artifacts_root=args.artifacts_root,
            state_root=args.state_root,
            open_browser=args.browser,
        )
    except CommandCenterDependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _run_crawl(args: argparse.Namespace) -> int:
    try:
        source = source_from_cli_args(args, args.base_url)
        base_url = source.base_url
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.repo_chunking_arm and not isinstance(source, GitHubRepoSource):
        print("--repo-chunking-arm is supported only for GitHub repositories.", file=sys.stderr)
        return 2

    _apply_source_cap_defaults(args, source)
    out_dir = args.out_dir if args.out_dir is not None else (
        source.default_out_dir if _is_database_source(source) else default_out_dir(base_url)
    )
    progress = OneLineProgress(enabled=should_show_progress(args))
    progress.update(f"crawl: preparing {base_url}", force=True)
    options = CrawlOptions(
        base_url=base_url,
        out_dir=out_dir,
        max_pages=args.max_pages,
        max_chunks=args.max_chunks,
        repo_max_file_bytes=args.repo_max_file_bytes,
        repo_chunking_arm=args.repo_chunking_arm,
        repo_search_metadata=args.repo_search_metadata,
        repo_file_cards=args.repo_file_cards,
        repo_oversize_file_cards=args.repo_oversize_file_cards,
        concurrent_requests=args.concurrent_requests,
        concurrent_requests_per_domain=args.concurrent_requests_per_domain,
        download_delay=args.download_delay,
        crawl_strategy=args.crawl_strategy,
        docs_version_policy=args.docs_version_policy,
        language_policy=args.language_policy,
        include_paths=tuple(args.include_path),
        exclude_paths=tuple(args.exclude_path),
        strip_trailing_slash=args.strip_trailing_slash,
        css_selector=args.css_selector,
        target_tokens=args.target_tokens,
        overlap_sentences=args.overlap_sentences,
        progress_callback=progress.update if progress.enabled else None,
    )
    try:
        summary = crawl_source(source, options)
    except (
        RuntimeError,
        GitHubRepoError,
        DatabaseRelationError,
    ) as exc:
        progress.finish()
        print(str(exc), file=sys.stderr)
        return 2

    progress.finish()
    if args.json:
        _print_json(summary)
    else:
        print_crawl_text(summary)
    return 0


def _run_plan(args: argparse.Namespace) -> int:
    if args.url and args.base_url and args.url != args.base_url:
        print("Provide either positional URL or --base-url, not conflicting values.", file=sys.stderr)
        return 2
    if not resolve_cli_state_root(args):
        return 2

    request = PlanningRequest(
        source=args.base_url or args.url,
        state_root=args.state_root,
        out_dir=args.out_dir,
        namespace=args.namespace,
        embedding_precision=args.embedding_precision,
        max_pages=args.max_pages,
        max_chunks=args.max_chunks,
        repo_max_file_bytes=args.repo_max_file_bytes,
        repo_chunking_arm=args.repo_chunking_arm,
        repo_search_metadata=args.repo_search_metadata,
        repo_file_cards=args.repo_file_cards,
        repo_oversize_file_cards=args.repo_oversize_file_cards,
        concurrent_requests=args.concurrent_requests,
        concurrent_requests_per_domain=args.concurrent_requests_per_domain,
        download_delay=args.download_delay,
        crawl_strategy=args.crawl_strategy,
        docs_version_policy=args.docs_version_policy,
        language_policy=args.language_policy,
        include_paths=tuple(args.include_path),
        exclude_paths=tuple(args.exclude_path),
        strip_trailing_slash=args.strip_trailing_slash,
        css_selector=args.css_selector,
        target_tokens=args.target_tokens,
        overlap_sentences=args.overlap_sentences,
        database_backend=args.database_backend,
        relation=args.relation,
        database_source_id=args.source_id,
        id_column=args.id_column,
        content_column=args.content_column,
        title_column=args.title_column,
        bigquery_project=args.bigquery_project,
        bigquery_location=args.bigquery_location,
        bigquery_maximum_bytes_billed=args.bigquery_maximum_bytes_billed,
        snowflake_connection=args.snowflake_connection,
        source_query_timeout=args.source_query_timeout,
    )
    progress = OneLineProgress(enabled=should_show_progress(args))

    def update_progress(event: PlanProgress) -> None:
        if event.stage != "complete":
            progress.update(event.message, force=event.message.startswith("plan:"))

    service = PlanningService()
    try:
        result = service.plan(
            request,
            progress_callback=update_progress if progress.enabled else None,
        )
    except (
        RuntimeError,
        GitHubRepoError,
        DatabaseRelationError,
        OSError,
        ValueError,
        AppliedStateError,
        PlanDiffError,
        ApplyPlanError,
        json.JSONDecodeError,
    ) as exc:
        progress.finish()
        message = str(exc)
        if message == "source URL/path is required.":
            message = "source URL/path is required; pass it as `buoy plan <source>` or with --base-url."
        print(message, file=sys.stderr)
        return 2

    progress.finish()
    for warning in result.cleanup_warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.json:
        _print_json(result.summary)
    else:
        print_plan_text(result.summary)
    return 0


def _stdin_is_interactive() -> bool:
    try:
        return bool(sys.stdin.isatty())
    except Exception:
        return False


def _confirm_apply() -> bool:
    try:
        sys.stderr.write("Apply this plan? [y/N] ")
        sys.stderr.flush()
        response = sys.stdin.readline()
    except Exception:
        return False
    return response.strip().lower() in {"y", "yes"}


def _run_apply(args: argparse.Namespace) -> int:
    if args.dry_run and args.approve:
        print("Choose either --dry-run or --approve, not both.", file=sys.stderr)
        return 2
    interactive = not args.dry_run and not args.approve
    if interactive and not _stdin_is_interactive():
        print(
            "Plain apply requires an interactive stdin; use --dry-run for preflight or --approve for confirmed execution.",
            file=sys.stderr,
        )
        return 2
    if not resolve_cli_state_root(args):
        return 2
    progress = OneLineProgress(enabled=should_show_progress(args))
    progress.update("apply: verifying plan", force=True)
    try:
        plan_path = args.plan if args.plan is not None else discover_latest_plan_path()
        verified = load_verified_apply_plan(
            plan_path=plan_path,
            namespace=args.namespace,
            state_root=args.state_root,
        )
    except (ApplyPlanError, AppliedStateError, PlanDiffError, OSError, ValueError, json.JSONDecodeError) as exc:
        progress.finish()
        print(str(exc), file=sys.stderr)
        return 2

    namespace = args.namespace or verified.manifest.namespace
    region = args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)
    if not args.approve:
        try:
            summary = apply_preflight_summary(
                verified,
                namespace=namespace,
                region=region,
                approved=False,
                delete_stale=args.delete_stale,
            )
        except CatalogError as exc:
            progress.finish()
            print(str(exc), file=sys.stderr)
            return 2
        progress.finish()
        if args.dry_run:
            if args.json:
                _print_json(summary)
            else:
                print_apply_text(summary)
            return 0

        prompt_available = True
        try:
            if args.json:
                print_apply_text({**summary, "confirmation_pending": True}, stream=sys.stderr)
            else:
                print_apply_text({**summary, "confirmation_pending": True})
        except OSError:
            prompt_available = False
        confirmed = prompt_available and _confirm_apply()
        if not confirmed:
            cancelled = {
                **summary,
                "approved": False,
                "dry_run": False,
                "cancelled": True,
                "confirmation": "declined_or_unavailable",
                "turbopuffer_api_calls": False,
                "api_calls_occurred": False,
                "state_updated": False,
                "catalog_updated": False,
            }
            if args.json:
                _print_json(cancelled)
            else:
                print("Apply cancelled; nothing was written.")
            return 0

    config = replace(
        load_config(),
        namespace=namespace,
        region=region,
        embedding_model=str(verified.plan["embedding_model"]),
        embedding_precision=str(verified.plan.get("embedding_precision", "float32")),
    )
    try:
        summary = run_approved_apply(
            verified,
            config=config,
            namespace=namespace,
            batch_size=args.batch_size,
            embedding_batch_size=args.embedding_batch_size,
            delete_stale=args.delete_stale,
            progress_callback=lambda message: progress.update(message, force=True) if progress.enabled else None,
        )
    except CatalogCommitPartialSuccess as exc:
        progress.finish()
        if args.json:
            _print_json(exc.summary)
        else:
            print_apply_text(exc.summary)
            print(f"  partial_success: {exc}", file=sys.stderr)
        return 2
    except (RuntimeError, AppliedStateError, OSError, ValueError) as exc:
        progress.finish()
        try:
            print(str(exc), file=sys.stderr)
        except OSError:
            pass
        return 2

    progress.update("apply: cleaning up successful plan", force=True)
    cleanup_warnings = cleanup_applied_plan_directory(verified.plan_path, state_root=verified.state_root)
    progress.finish()
    for warning in cleanup_warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    if args.json:
        _print_json(summary)
    else:
        print_apply_text(summary)
    return 0


def _run_namespaces(args: argparse.Namespace) -> int:
    region = args.region or os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION)
    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        print("TURBOPUFFER_API_KEY must be set in the environment for namespace discovery.", file=sys.stderr)
        return 2
    try:
        namespace_ids = list_namespace_ids(region=region, api_key=api_key, search=args.search)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        _print_json(
            {
                "command": "namespaces",
                "region": region,
                "search": args.search,
                "count": len(namespace_ids),
                "namespaces": namespace_ids,
            }
        )
    elif namespace_ids:
        for namespace_id in namespace_ids:
            print(namespace_id)
    else:
        print("No namespaces matched.")
    return 0


def _run_retrieve(args: argparse.Namespace) -> int:
    if args.dry_run and args.live:
        print("Choose either --live or --dry-run/--plan, not both.", file=sys.stderr)
        return 2
    cli_namespaces = args.namespace if isinstance(args.namespace, list) else []
    if args.auto_route and cli_namespaces:
        print("--auto-route and --namespace are mutually exclusive.", file=sys.stderr)
        return 2
    if cli_namespaces and args.route_top_k is not None:
        print("--route-top-k is valid only for automatic retrieval without --namespace.", file=sys.stderr)
        return 2
    try:
        namespaces = resolve_retrieval_namespaces(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    query = args.query.strip()
    if not query:
        print("A non-empty query is required for retrieval.", file=sys.stderr)
        return 2
    if not namespaces:
        return _run_auto_routed_retrieve(args, query=query)

    base_config = config_from_args(args, ignore_environment_namespace=True)
    configs = [replace(base_config, namespace=namespace) for namespace in namespaces]
    options = [
        retrieval_options_from_args(args, config=config, doc_kind=args.doc_kind)
        for config in configs
    ]
    if args.dry_run:
        plan: RetrievalPlan | MultiNamespaceRetrievalPlan
        if len(configs) == 1:
            plan = retrieval_plan(query, config=configs[0], options=options[0])
        else:
            plan = multi_namespace_retrieval_plan(query, configs=configs, options=options)
        if args.json:
            _print_json(plan.to_dict())
        else:
            print_retrieval_text(plan)
        return 0

    try:
        result: RetrievalResult | MultiNamespaceRetrievalResult
        if len(configs) == 1:
            try:
                result = HybridRetriever.from_config(configs[0]).retrieve(query, options[0])
            except RuntimeError as exc:
                raise RuntimeError(
                    f"Retrieval failed for namespace {configs[0].namespace!r}: {exc}"
                ) from exc
        else:
            result = MultiNamespaceRetriever.from_configs(configs).retrieve(query, options)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.json:
        _print_json(result.to_dict())
    else:
        print_retrieval_text(result)
    return 0


def _run_auto_routed_retrieve(args: argparse.Namespace, *, query: str) -> int:
    base_config = config_from_args(args, ignore_environment_namespace=True)
    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        print("TURBOPUFFER_API_KEY must be set for automatic remote routing.", file=sys.stderr)
        return 2
    compatibility = CompatibilityContract(
        region=base_config.region,
        embedding_model=base_config.embedding_model,
        embedding_precision=base_config.embedding_precision,
    )
    try:
        client = REMOTE_CATALOG_CLIENT_FACTORY(api_key=api_key, region=base_config.region)
        snapshot = require_eligible(
            read_remote_catalog(client, region=base_config.region, compatibility=compatibility)
        )
    except (RemoteCatalogError, CatalogError, RuntimeError) as exc:
        print(f"Remote catalog read failed: {exc}", file=sys.stderr)
        return 2
    try:
        route_embedder = load_routing_embedder()
    except (CatalogError, RuntimeError) as exc:
        print(f"Route model load failed: {exc}", file=sys.stderr)
        return 2
    exclusions = {
        "missing_card": snapshot.counts.missing_card_count,
        "stale_target": snapshot.counts.stale_target_count,
        "disabled": snapshot.counts.disabled_count,
        "incompatible": snapshot.counts.incompatible_count,
    }
    try:
        routing = hybrid_route(
            query,
            snapshot.eligible_cards,
            embedder=route_embedder,
            route_top_k=args.route_top_k or DEFAULT_ROUTE_TOP_K,
            catalog_namespace=REMOTE_CATALOG_NAMESPACE,
            region=base_config.region,
            snapshot_revision=snapshot.snapshot_revision,
            exclusion_counts={key: value for key, value in exclusions.items() if value},
            remote_counts=asdict(snapshot.counts),
            read_metrics={
                "namespace_list_pages": snapshot.metrics.namespace_list_pages,
                "metadata_requests": snapshot.metrics.metadata_requests,
                "card_query_pages": snapshot.metrics.card_query_pages,
                "billing": list(snapshot.metrics.billing),
            },
        )
    except (AutomaticRoutingError, CatalogError, RuntimeError) as exc:
        print(f"Route scoring failed: {exc}", file=sys.stderr)
        return 2

    configs = [
        replace(
            base_config,
            namespace=card.namespace,
            region=card.region,
            embedding_model=card.embedding_model,
            embedding_precision=card.embedding_precision,
        )
        for card in routing.selected_cards
    ]
    try:
        options = [
            routed_retrieval_options_from_args(args, card=card)
            for card in routing.selected_cards
        ]
    except ValueError as exc:
        print(f"Selected namespace preparation failed: {exc}", file=sys.stderr)
        return 2

    if args.dry_run:
        plan = RoutedRetrievalPlan(
            plan=multi_namespace_retrieval_plan(
                query,
                configs=configs,
                options=options,
            ),
            routing=routing,
        )
        if args.json:
            _print_json(plan.to_dict())
        else:
            print_retrieval_text(plan)
        return 0

    try:
        retriever = MultiNamespaceRetriever.from_configs(configs)
    except (RuntimeError, ValueError) as exc:
        print(f"Selected namespace preparation failed: {exc}", file=sys.stderr)
        return 2
    try:
        result = RoutedRetrievalResult(
            result=retriever.retrieve(query, options),
            routing=routing,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"Namespace retrieval failed: {exc}", file=sys.stderr)
        return 2
    if args.json:
        _print_json(result.to_dict())
    else:
        print_retrieval_text(result)
    return 0


def _run_evals(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    options = retrieval_options_from_args(args, config=config)
    if args.dry_run and args.live:
        print("Choose either --live or --dry-run/--list, not both.", file=sys.stderr)
        return 2
    try:
        cases = load_eval_cases(args.dataset)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Could not load retrieval eval dataset: {exc}", file=sys.stderr)
        return 2

    if args.live:
        try:
            report = run_live_evals(cases, config=config, options=options)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
    else:
        report = build_dry_run_eval_report(cases, config=config, options=options)

    if args.json:
        _print_json(report.to_dict())
    else:
        print_eval_text(report.to_dict())
    return 0


def print_crawl_text(payload: dict[str, object]) -> None:
    source_kind = payload.get("source_kind", "website")
    print("Source crawl dry-run (no turbopuffer credentials, embeddings, or turbopuffer API calls):")
    print(f"  source_kind: {source_kind}")
    print(f"  base_url: {payload['base_url']}")
    if source_kind == "github_repo":
        print(f"  repo: {payload.get('repo_full_name')} @ {payload.get('repo_ref')} ({payload.get('commit_sha')})")
        print(
            "  files: "
            f"selected={payload.get('files_selected')}; "
            f"discovered={payload.get('files_discovered')}; "
            f"filtered={payload.get('files_skipped_filtered')}; "
            f"binary={payload.get('files_skipped_binary')}; "
            f"oversize={payload.get('files_skipped_oversize')}"
        )
    if source_kind == "pdf":
        print(f"  pdf: {payload.get('pdf_filename')} ({str(payload.get('pdf_sha256', ''))[:16]})")
    if source_kind == "local_file":
        print(
            "  file: "
            f"{payload.get('file_filename')} ({payload.get('file_extension')}; {str(payload.get('file_sha256', ''))[:16]})"
        )
    if source_kind in DATABASE_RELATION_KINDS:
        print(
            f"  relation: {payload.get('database_relation')} "
            f"(backend={payload.get('database_backend')}; source_id={payload.get('database_source_id')})"
        )
        print(
            "  documents: "
            f"selected={payload.get('documents_selected')}; "
            f"empty={payload.get('documents_skipped_empty')}; "
            f"capped={payload.get('documents_skipped_limit')}; "
            f"rows={payload.get('rows_scanned')}"
        )
    print(f"  namespace_candidate: {payload['namespace_candidate']}")
    print(f"  strategy: {payload['crawl_strategy']}")
    if source_kind in {"pdf", "local_file"}:
        print(f"  documents_converted: {payload.get('documents_converted', payload.get('pages_scraped'))}; chunks_generated: {payload['chunks_generated']}")
    elif source_kind in DATABASE_RELATION_KINDS:
        print(f"  documents_generated: {payload.get('documents_generated')}; chunks_generated: {payload['chunks_generated']}")
    else:
        print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
    print_crawl_boundary_summary(payload)
    print_docs_version_summary(payload)
    print_language_summary(payload)
    print(f"  out_dir: {payload['out_dir']}")
    print("  live writes: not supported by this command")


def print_plan_text(payload: dict[str, object]) -> None:
    source_kind = payload.get("source_kind", "website")
    print("Source RAG plan (no turbopuffer credentials, embeddings, or turbopuffer API calls):")
    print(f"  source_kind: {source_kind}")
    print(f"  base_url: {payload['base_url']}")
    if source_kind == "github_repo":
        print(f"  repo: {payload.get('repo_full_name')} @ {payload.get('repo_ref')} ({payload.get('commit_sha')})")
        print(
            "  files: "
            f"selected={payload.get('files_selected')}; "
            f"discovered={payload.get('files_discovered')}; "
            f"filtered={payload.get('files_skipped_filtered')}; "
            f"binary={payload.get('files_skipped_binary')}; "
            f"oversize={payload.get('files_skipped_oversize')}"
        )
    if source_kind == "pdf":
        print(f"  pdf: {payload.get('pdf_filename')} ({str(payload.get('pdf_sha256', ''))[:16]})")
    if source_kind == "local_file":
        print(
            "  file: "
            f"{payload.get('file_filename')} ({payload.get('file_extension')}; {str(payload.get('file_sha256', ''))[:16]})"
        )
    if source_kind in DATABASE_RELATION_KINDS:
        print(
            f"  relation: {payload.get('database_relation')} "
            f"(backend={payload.get('database_backend')}; source_id={payload.get('database_source_id')})"
        )
        print(
            "  documents: "
            f"selected={payload.get('documents_selected')}; "
            f"empty={payload.get('documents_skipped_empty')}; "
            f"capped={payload.get('documents_skipped_limit')}; "
            f"rows={payload.get('rows_scanned')}"
        )
    print(f"  namespace: {payload['namespace']}")
    print(f"  plan_id: {payload['plan_id']}")
    print(f"  embedding_precision: {payload['embedding_precision']}")
    if source_kind in {"pdf", "local_file"}:
        print(f"  documents_converted: {payload.get('documents_converted', payload.get('pages_scraped'))}; chunks_generated: {payload['chunks_generated']}")
    elif source_kind in DATABASE_RELATION_KINDS:
        print(f"  documents_generated: {payload.get('documents_generated')}; chunks_generated: {payload['chunks_generated']}")
    else:
        print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
    print_crawl_boundary_summary(payload)
    print_docs_version_summary(payload)
    print_language_summary(payload)
    diff = payload.get("diff", {}) if isinstance(payload.get("diff"), dict) else {}
    print(
        "  diff: "
        f"first_apply={diff.get('first_apply')}, "
        f"upsert={diff.get('rows_to_upsert')}, "
        f"unchanged={diff.get('chunks_unchanged')}, "
        f"stale={diff.get('stale_rows')}, "
        f"retained_stale={diff.get('retained_stale_rows')}"
    )
    timing = payload.get("timing")
    if isinstance(timing, dict):
        print(
            "  timing: "
            f"elapsed={float(timing.get('elapsed_seconds', 0.0)):.1f}s; "
            f"policy={float(timing.get('sitemap_policy_seconds', 0.0)):.1f}s; "
            f"crawl={float(timing.get('crawl_seconds', 0.0)):.1f}s; "
            f"write={float(timing.get('corpus_write_seconds', 0.0)):.1f}s; "
            f"chunk={float(timing.get('chunking_seconds', 0.0)):.1f}s; "
            f"diff={float(timing.get('diff_seconds', 0.0)):.1f}s; "
            f"artifact={float(timing.get('artifact_seconds', 0.0)):.1f}s; "
            f"publish={float(timing.get('publication_seconds', 0.0)):.1f}s"
        )
    print(f"  plan_path: {payload['plan_path']}")
    print(f"  state_path: {payload['state_path']}")
    registration = payload.get("catalog_registration")
    if isinstance(registration, dict):
        print(
            "  catalog_registration: "
            f"{registration['action']}; {registration['catalog_namespace']} "
            f"(remote_state={registration.get('remote_catalog_state', 'resolved')})"
        )
    print("  live writes: not supported by this command; future apply must be explicit")


def print_limit_summary(payload: dict[str, object]) -> None:
    max_pages = payload.get("max_pages")
    max_chunks = payload.get("max_chunks")
    limit_reached = bool(payload.get("limit_reached"))
    source_kind = payload.get("source_kind", "website")
    chunk_limit_reached = bool(payload.get("chunk_limit_reached", limit_reached))
    if max_pages is not None or max_chunks is not None:
        label = "max_documents" if source_kind in DATABASE_RELATION_KINDS else "max_pages"
        print(f"  caps: {label}={max_pages}; max_chunks={max_chunks}; chunk_limit_reached={chunk_limit_reached}")
    warnings: list[str] = []
    if source_kind in DATABASE_RELATION_KINDS:
        if payload.get("document_limit_reached"):
            warnings.append("document cap")
    elif max_pages is not None and payload.get("pages_scraped") == max_pages:
        warnings.append("page cap")
    if chunk_limit_reached or (max_chunks is not None and payload.get("chunks_generated") == max_chunks):
        warnings.append("chunk cap")
    if warnings:
        print(
            "  warning: reached "
            f"{', '.join(warnings)}; this is probably capped/incomplete. "
            "Increase --max-pages and/or --max-chunks and rerun."
        )


def print_filter_summary(payload: dict[str, object]) -> None:
    include_paths = payload.get("include_paths") or []
    exclude_paths = payload.get("exclude_paths") or []
    strip_trailing_slash = payload.get("strip_trailing_slash")
    if include_paths or exclude_paths or strip_trailing_slash is not None:
        print(
            "  filters: "
            f"include={list(include_paths)}; "
            f"exclude={list(exclude_paths)}; "
            f"strip_trailing_slash={strip_trailing_slash}"
        )


def print_crawl_boundary_summary(payload: dict[str, object]) -> None:
    if payload.get("source_kind", "website") != "website" or (
        "blocked_discovery_count" not in payload
        and "blocked_redirect_count" not in payload
    ):
        return
    print(
        "  exact_host_boundary: "
        f"blocked_discoveries={int(payload.get('blocked_discovery_count', 0) or 0)}; "
        f"blocked_redirects={int(payload.get('blocked_redirect_count', 0) or 0)}"
    )


def print_docs_version_summary(payload: dict[str, object]) -> None:
    report = payload.get("docs_version_report")
    if not isinstance(report, dict) or not report.get("detected"):
        return
    policy = report.get("policy")
    root_path = report.get("root_path")
    version_count = report.get("version_count")
    url_count = report.get("versioned_url_count")
    if report.get("applied"):
        selected = report.get("selected_versions") or []
        excluded = report.get("excluded_versions") or []
        print(
            "  docs_versions: "
            f"policy={policy}; root={root_path}; versions={version_count}; "
            f"versioned_urls={url_count}; selected={list(selected)}; excluded_versions={len(list(excluded))}"
        )
    else:
        suggested = report.get("suggested_policy")
        print(
            "  docs_versions: "
            f"detected root={root_path}; versions={version_count}; versioned_urls={url_count}; policy={policy}"
        )
        if suggested:
            print(
                "  suggestion: rerun with "
                f"--docs-version-policy {suggested} to keep current docs and prune old versions, "
                "or --docs-version-policy all to keep/suppress this warning."
            )


def print_language_summary(payload: dict[str, object]) -> None:
    report = payload.get("language_report")
    if not isinstance(report, dict) or not report.get("detected"):
        return
    if report.get("applied"):
        print(
            "  languages: "
            f"policy={report.get('policy')}; "
            f"localized_urls={report.get('localized_url_count')}; "
            f"non_english_urls={report.get('non_english_url_count')}; "
            f"excluded={list(report.get('excluded_languages') or [])}"
        )
    else:
        print(
            "  languages: "
            f"detected non_english={list(report.get('non_english_locales') or [])}; "
            f"policy={report.get('policy')}"
        )


def print_apply_text(payload: dict[str, object], *, stream: TextIO | None = None) -> None:
    output = stream or sys.stdout

    def emit(message: str) -> None:
        print(message, file=output)

    approved = bool(payload.get("approved"))
    if approved:
        emit("Website RAG apply completed (confirmed live upsert path):")
    else:
        emit("Website RAG apply preflight (no credentials, embeddings, or turbopuffer API calls):")
    emit(f"  source: {payload['base_url']}")
    emit(f"  plan_path: {payload['plan_path']}")
    emit(f"  plan_id: {payload['plan_id']}")
    emit(f"  artifact_hash: {payload['artifact_hash']}")
    emit(f"  namespace: {payload['namespace']} ({payload['region']})")
    emit(f"  embedding_model: {payload['embedding_model']}")
    emit(f"  embedding_precision: {payload['embedding_precision']}")
    emit(f"  first_apply: {payload['state_first_apply']}")
    diff = payload.get("diff") if isinstance(payload.get("diff"), dict) else {}
    emit(
        f"  rows: to_upsert={payload['rows_to_upsert']}; "
        f"upserted={payload['rows_upserted']}; "
        f"unchanged={diff.get('chunks_unchanged', 0)}"
    )
    emit(
        f"  embeddings: to_generate={payload['embeddings_to_generate']}; "
        f"generated={payload['embeddings_generated']}"
    )
    emit(
        f"  stale_rows: current={payload['stale_rows']}; "
        f"already_retained={payload['retained_stale_rows']}; "
        f"deleted={payload['rows_deleted']}"
    )
    if payload.get("delete_stale"):
        emit(f"  stale_intent: delete {payload['stale_rows_to_delete']} stale rows")
    else:
        emit(f"  stale_intent: retain {payload['stale_rows_retained']} stale rows")
    emit(f"  state_path: {payload['state_path']}")
    registration = payload.get("catalog_registration")
    if isinstance(registration, dict):
        emit(
            "  catalog_registration: "
            f"{registration['action']}; {registration['catalog_namespace']} "
            f"(remote_state={registration.get('remote_catalog_state', 'resolved')})"
        )
    if "catalog_updated" in payload and approved:
        emit(
            f"  catalog_updated: {payload['catalog_updated']}; "
            f"catalog: {payload['catalog_namespace']}"
        )
        if payload.get("card_revision"):
            emit(f"  committed_card_revision: {payload['card_revision']}")
        if payload.get("catalog_snapshot_complete") is False:
            emit("  catalog_snapshot: incomplete; no final stable snapshot is claimed")
        elif payload.get("snapshot_revision"):
            emit(f"  catalog_snapshot_revision: {payload['snapshot_revision']}")
        if payload.get("pending_cleanup") is False:
            emit(f"  pending_cleanup: False; pending_path: {payload['pending_path']}")
            emit(f"  repair: {payload['catalog_repair_command']}")
    timing = payload.get("timing")
    if isinstance(timing, dict):
        emit(
            "  timing: "
            f"elapsed={timing['elapsed_seconds']:.1f}s; "
            f"embedding={timing['embedding_seconds']:.1f}s; "
            f"write={timing['write_seconds']:.1f}s; "
            f"embedding_batch_size={timing['embedding_batch_size']}; "
            f"write_batch_size={timing['write_batch_size']}; "
            f"precision={timing['embedding_precision']}; "
            f"pipeline={timing['pipeline_mode']}"
        )
    commands = payload.get("retrieval_commands")
    if isinstance(commands, dict):
        label = "next retrieval step" if approved else "retrieval after successful apply"
        emit(f"  {label} (preview): {commands['preview']}")
        emit(f"  {label} (live): {commands['live']}")
    if payload.get("confirmation_pending"):
        emit("  live: confirmation required at the prompt below")
    elif not approved:
        emit("  live: rerun without --dry-run for interactive confirmation, or pass --approve for automation")


def print_retrieval_text(
    output: (
        RetrievalPlan
        | MultiNamespaceRetrievalPlan
        | RetrievalResult
        | MultiNamespaceRetrievalResult
        | RoutedRetrievalPlan
        | RoutedRetrievalResult
    ),
) -> None:
    payload = output.to_dict()
    routing = payload.get("routing")
    if isinstance(routing, dict):
        exclusions = routing.get("exclusion_counts")
        exclusion_text = (
            ", ".join(f"{key}={value}" for key, value in exclusions.items())
            if isinstance(exclusions, dict) and exclusions
            else "none"
        )
        print("Automatic namespace route (hybrid_rrf):")
        print(
            f"  catalog: {routing.get('catalog_namespace')} "
            f"(snapshot {routing.get('snapshot_revision')}; region {routing.get('region')})"
        )
        print(
            f"  routing_model: {routing.get('routing_model')}@"
            f"{routing.get('routing_model_revision')}"
        )
        print(
            f"  eligible: {routing.get('eligible_count')}; excluded: {exclusion_text}; "
            f"requested_limit: {routing.get('requested_limit')}"
        )
        selected = routing.get("selected_cards")
        if isinstance(selected, list):
            for entry in selected:
                if isinstance(entry, dict):
                    print(
                        f"  route {entry.get('route_rank')}: {entry.get('namespace')} "
                        f"hybrid={float(entry.get('hybrid_score', 0.0)):.8f} "
                        f"lexical_rank={entry.get('lexical_rank')} "
                        f"semantic_rank={entry.get('semantic_rank')}"
                    )
    if payload.get("dry_run"):
        if isinstance(routing, dict):
            print(
                "Retrieval plan (authenticated remote preview; credentials required; "
                "read-only namespace-list/catalog-query API calls occurred; no content retrieval):"
            )
        else:
            print("Retrieval plan (dry-run; no credentials, embeddings, or turbopuffer API calls):")
        print(f"  query: {payload['query']}")
        if "namespaces" in payload:
            print(f"  namespaces: {', '.join(payload['namespaces'])} ({payload['region']})")
        else:
            print(f"  namespace: {payload['namespace']} ({payload['region']})")
        print(f"  embedding_model: {payload['embedding_model']}")
        print(f"  embedding_precision: {payload['embedding_precision']}")
        print(f"  top_k: {payload['top_k']}; candidates per subquery: {payload['candidates']}")
        if "namespace_plans" in payload:
            for namespace_plan in payload["namespace_plans"]:
                print(
                    f"  ranking {namespace_plan['namespace']}: "
                    f"mode={namespace_plan.get('ranking_mode')}; "
                    f"profile={namespace_plan.get('ranking_profile')}; "
                    f"pool={namespace_plan.get('ranking_pool')}; "
                    f"aggregation={namespace_plan.get('ranking_aggregation')}"
                )
        else:
            print(
                "  ranking: "
                f"mode={payload.get('ranking_mode')}; "
                f"profile={payload.get('ranking_profile')}; "
                f"pool={payload.get('ranking_pool')}; "
                f"aggregation={payload.get('ranking_aggregation')}"
            )
        print("  hybrid: ANN over vector + boosted BM25 over title/section_path/content + RRF")
        print("  live: omit --dry-run/--plan to execute; TURBOPUFFER_API_KEY is read from the environment only")
        return

    hits = payload.get("hits", [])
    if "namespaces" in payload:
        print(
            f"Retrieved {len(hits)} chunks across {len(payload['namespaces'])} namespaces "
            f"using {payload.get('fusion')}:"
        )
        print(f"  namespaces: {', '.join(payload['namespaces'])}")
    else:
        print(
            f"Retrieved {len(hits)} chunks using {payload.get('fusion')} "
            f"with ranking mode={payload.get('ranking_mode')} profile={payload.get('ranking_profile')} "
            f"aggregation={payload.get('ranking_aggregation')}:"
        )
    print(f"  embedding_precision: {payload['embedding_precision']}")
    for index, hit in enumerate(hits, start=1):
        if not isinstance(hit, dict):
            continue
        title = hit.get("title") or "Untitled"
        url = hit.get("url") or "no URL"
        section_path = hit.get("section_path") or ""
        print(f"\n{index}. {title}")
        print(f"   URL: {url}")
        if hit.get("namespace"):
            print(f"   Namespace: {hit['namespace']}")
        if section_path:
            print(f"   Section: {section_path}")
        if hit.get("path"):
            print(f"   Path: {hit['path']}")
        tags = hit.get("tags")
        if isinstance(tags, list) and tags:
            print(f"   Tags: {', '.join(tags)}")
        print(f"   Score: {hit.get('score_info', {})}")
        content = str(hit.get("content") or "").strip()
        if content:
            preview = content if len(content) <= 600 else content[:597].rstrip() + "..."
            print(f"   Content: {preview}")


def print_eval_text(payload: dict[str, object]) -> None:
    if payload.get("dry_run"):
        print("Retrieval smoke evals (dry-run; no credentials, embeddings, or turbopuffer API calls):")
        print(f"  namespace: {payload['namespace']} ({payload['region']})")
        print(
            f"  evals: {payload['total']}; top_k: {payload['top_k']}; "
            f"candidates: {payload['candidates']}; "
            f"ranking: {payload.get('ranking_mode')}/{payload.get('ranking_profile')}/"
            f"{payload.get('ranking_aggregation')}"
        )
        print("  live: pass --live to execute; TURBOPUFFER_API_KEY is read from the environment only")
    else:
        print(
            f"Retrieval smoke evals: {payload['passed']}/{payload['total']} passed "
            f"({float(payload['pass_rate']) * 100:.1f}%)"
        )
        print(f"  namespace: {payload['namespace']} ({payload['region']})")
    print(f"  embedding_precision: {payload['embedding_precision']}")
    cases = payload.get("cases", [])
    if not isinstance(cases, list):
        return
    for case in cases:
        if not isinstance(case, dict):
            continue
        print(f"\n- {case.get('id')}: {case.get('question')}")
        if payload.get("dry_run"):
            print(f"  expected_urls: {case.get('expected_urls', [])}")
            print(f"  expected_topics: {case.get('expected_topics', [])}")
            continue
        score = case.get("score") if isinstance(case.get("score"), dict) else {}
        print(f"  status: {case.get('status')} (matched_rank={score.get('matched_rank')})")
        top_hits = case.get("top_hits", [])
        if not isinstance(top_hits, list):
            continue
        for hit in top_hits:
            if not isinstance(hit, dict):
                continue
            print(f"  {hit.get('rank')}. {hit.get('title') or 'Untitled'}")
            print(f"     URL: {hit.get('url') or 'no URL'}")
            if hit.get("section_path"):
                print(f"     Section: {hit['section_path']}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if (
        getattr(args, "command", None) == "crawl"
        and getattr(args, "base_url", None) is None
        and not (
            getattr(args, "relation", None) is not None
            and getattr(args, "database_backend", None) in {"bigquery", "snowflake"}
        )
    ):
        parser.error("the following arguments are required: --base-url")
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    removed_environment_error = removed_embedding_environment_error()
    if removed_environment_error is not None:
        try:
            print(removed_environment_error, file=sys.stderr)
        except OSError:
            pass
        return 2
    try:
        return args.func(args)
    except RuntimeConfigError as exc:
        try:
            print(str(exc), file=sys.stderr)
        except OSError:
            pass
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
