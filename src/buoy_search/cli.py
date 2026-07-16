"""Command-line interface for website RAG planning, apply, retrieval, and evals."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
from pathlib import Path
import shutil
import sys
import time
from typing import TextIO, Sequence

from buoy_search import __version__
from buoy_search.applied_state import AppliedStateError, load_applied_state, resolve_state_root
from buoy_search.apply import (
    ApplyPlanError,
    apply_preflight_summary,
    discover_latest_plan_path,
    load_verified_apply_plan,
    run_approved_apply,
)
from buoy_search.catalog import (
    CatalogError,
    generated_semantics,
    load_catalog,
    load_routing_embedder,
    resolve_catalog_path,
)
from buoy_search.catalog_pending import CatalogCommitPartialSuccess
from buoy_search.catalog_cli import configure_catalog_parser
from buoy_search.config import (
    DEFAULT_EMBEDDING_PRECISION,
    DEFAULT_REGION,
    EMBEDDING_PRECISIONS,
    RuntimeConfigError,
    load_config,
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
    CrawlExecution,
    CrawlOptions,
    crawl_local_document,
    crawl_local_document_with_plan,
    crawl_site,
    crawl_site_with_plan,
    elapsed_since,
    observe_monotonic,
    default_out_dir,
    detect_source,
)
from buoy_search.github_repo import GitHubRepoError, crawl_github_repo, crawl_github_repo_with_plan
from buoy_search.evals import (
    build_dry_run_eval_report,
    load_eval_cases,
    run_live_evals,
)
from buoy_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
)
from buoy_search.plan_artifacts import (
    DEFAULT_PLAN_EMBEDDING_MODEL,
    PlanArtifacts,
    build_plan_artifacts,
    write_plan_artifacts,
)
from buoy_search.plan_cleanup import cleanup_applied_plan_directory, cleanup_superseded_plan_directories
from buoy_search.plan_diff import IncrementalPlanDiff, PlanDiffError, diff_manifest_against_state
from buoy_search.namespaces import list_namespace_ids
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
    eligible_catalog_cards,
    hybrid_route,
    require_eligible_cards,
)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buoy",
        description="Local site/repository/local-document RAG utilities. Planning is local-only by default unless explicitly documented otherwise.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="crawl a website, public GitHub repo, or local document and chunk locally; always dry-run",
        description=(
            "Crawl a public website with Scrapling, ingest a public GitHub repository via git, or "
            "convert one local document file with MarkItDown, generate a local Markdown corpus, and chunk it for namespace planning. This command "
            "is local-only with respect to turbopuffer: it does not read turbopuffer credentials, "
            "embed text, create namespaces, or call turbopuffer."
        ),
    )
    crawl_parser.add_argument(
        "--base-url",
        required=True,
        metavar="SOURCE",
        help="Absolute http(s) URL, public GitHub repo URL, or supported local document filepath to crawl.",
    )
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
            "Maximum pages/files to scrape. Defaults: "
            f"websites={DEFAULT_CRAWL_MAX_PAGES}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_FILES}."
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
        help="crawl a website, public GitHub repo, or local document and write local review/apply plan artifacts; no live writes",
        description=(
            "Crawl a public website with Scrapling, ingest a public GitHub repository via git, or "
            "convert one local document file with MarkItDown, generate a local Markdown corpus, chunk it, compare it to local applied state, and "
            "write reviewable plan artifacts. This command is local-only with respect to turbopuffer: "
            "it does not read turbopuffer credentials, embed text, create namespaces, or call turbopuffer."
        ),
    )
    plan_parser.add_argument(
        "url",
        nargs="?",
        metavar="SOURCE",
        help="Absolute http(s) URL, public GitHub repo URL, or supported local document filepath to crawl and plan.",
    )
    plan_parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="Absolute http(s) URL, public GitHub repo URL, or supported local document filepath to crawl and plan. Kept for backwards compatibility; positional source is preferred.",
    )
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
            "Maximum pages/files to scrape. Defaults: "
            f"websites={DEFAULT_CRAWL_MAX_PAGES}, GitHub repos={DEFAULT_GITHUB_REPO_MAX_FILES}."
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
        help="verify and optionally apply a saved generic site RAG plan",
        description=(
            "Verify a saved plan artifact and recompute its local state diff. Default mode is "
            "a safe preflight: no credentials, embeddings, or turbopuffer API calls are used. "
            "Pass --approve to embed and upsert only new/changed rows."
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
        "--catalog",
        default=None,
        help="Override BUOY_CATALOG_PATH and the catalog under the resolved state root.",
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
        "--approve",
        action="store_true",
        help="Explicitly embed and upsert rows selected by the recomputed diff.",
    )
    apply_parser.add_argument(
        "--delete-stale",
        action="store_true",
        help="With --approve, delete exact stale row IDs from the recomputed diff instead of retaining them.",
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
        help="retrieve relevant chunks; dry-run plan by default unless --live is passed",
        description=(
            "Plan or execute hybrid retrieval against explicitly selected namespaces, or opt into "
            "local catalog routing with --auto-route. Default mode is safe: explicit previews do not "
            "load embeddings, while routed previews use only the pinned local routing model; neither "
            "reads credentials nor contacts turbopuffer. Pass --live to query selected namespaces."
        ),
    )
    retrieve_parser.add_argument(
        "query",
        help="Question to retrieve relevant chunks for.",
    )
    retrieve_parser.add_argument(
        "--live",
        action="store_true",
        help="Execute live retrieval. Reads TURBOPUFFER_API_KEY from the environment and calls turbopuffer.",
    )
    retrieve_parser.add_argument(
        "--dry-run",
        "--plan",
        dest="dry_run",
        action="store_true",
        help="Print the local retrieval plan without credentials or turbopuffer API calls (default).",
    )
    retrieve_parser.add_argument(
        "--auto-route",
        action="store_true",
        help="Select enabled compatible namespaces from the canonical local catalog.",
    )
    retrieve_parser.add_argument(
        "--route-top-k",
        type=bounded_route_top_k,
        default=None,
        metavar="N",
        help=f"Maximum routed namespaces (default {DEFAULT_ROUTE_TOP_K}, maximum {MAX_ROUTE_TOP_K}); requires --auto-route.",
    )
    retrieve_parser.add_argument(
        "--catalog",
        default=None,
        help="Override BUOY_CATALOG_PATH and the resolved state-root catalog; requires --auto-route.",
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
            "Select a namespace; repeat to retrieve across multiple namespaces. CLI selections replace "
            "TURBOPUFFER_NAMESPACE."
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


def config_from_args(args: argparse.Namespace):
    """Load non-secret runtime config, applying CLI overrides when supplied."""

    config = load_config()
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
    """Resolve explicit CLI namespaces or one environment namespace without demo fallback."""

    cli_namespaces = args.namespace if isinstance(args.namespace, list) else []
    if cli_namespaces:
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
    environment_namespace = os.environ.get("TURBOPUFFER_NAMESPACE", "").strip()
    if environment_namespace:
        return [environment_namespace]
    raise ValueError(
        "Retrieval requires --namespace or TURBOPUFFER_NAMESPACE; "
        "run `buoy namespaces [search]` to discover available namespace IDs."
    )


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


def _apply_source_cap_defaults(args: argparse.Namespace, source: object) -> None:
    if args.max_pages is None:
        args.max_pages = DEFAULT_GITHUB_REPO_MAX_FILES if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_PAGES
    if args.max_chunks is None:
        args.max_chunks = DEFAULT_GITHUB_REPO_MAX_CHUNKS if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_CHUNKS


def crawl_source(source: object, options: CrawlOptions) -> dict[str, object]:
    if isinstance(source, GitHubRepoSource):
        return crawl_github_repo(source, options)
    if isinstance(source, (PdfSource, LocalFileSource)):
        return crawl_local_document(source, options)
    return crawl_site(options)


def crawl_source_with_plan(source: object, options: CrawlOptions) -> CrawlExecution:
    if isinstance(source, GitHubRepoSource):
        return crawl_github_repo_with_plan(source, options)
    if isinstance(source, (PdfSource, LocalFileSource)):
        return crawl_local_document_with_plan(source, options)
    return crawl_site_with_plan(options)


def _run_crawl(args: argparse.Namespace) -> int:
    try:
        source = detect_source(args.base_url)
        base_url = source.base_url
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _apply_source_cap_defaults(args, source)
    out_dir = args.out_dir if args.out_dir is not None else default_out_dir(base_url)
    progress = OneLineProgress(enabled=should_show_progress(args))
    progress.update(f"crawl: preparing {base_url}", force=True)
    options = CrawlOptions(
        base_url=base_url,
        out_dir=out_dir,
        max_pages=args.max_pages,
        max_chunks=args.max_chunks,
        repo_max_file_bytes=args.repo_max_file_bytes,
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
    except (RuntimeError, GitHubRepoError) as exc:
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
    if not resolve_cli_state_root(args):
        return 2
    try:
        plan_catalog_path, catalog_warning = resolve_catalog_path(None, state_root=args.state_root)
        plan_catalog = load_catalog(plan_catalog_path)
    except CatalogError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if catalog_warning:
        print(catalog_warning, file=sys.stderr)
    if args.url and args.base_url and args.url != args.base_url:
        print("Provide either positional URL or --base-url, not conflicting values.", file=sys.stderr)
        return 2
    requested_url = args.base_url or args.url
    if not requested_url:
        print("source URL/path is required; pass it as `buoy plan <source>` or with --base-url.", file=sys.stderr)
        return 2
    try:
        source = detect_source(requested_url)
        base_url = source.base_url
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    _apply_source_cap_defaults(args, source)
    out_dir = args.out_dir if args.out_dir is not None else default_out_dir(base_url).with_name(
        f"{default_out_dir(base_url).name}-plan"
    )
    progress = OneLineProgress(enabled=should_show_progress(args))
    progress.update(f"plan: preparing {base_url}", force=True)
    options = CrawlOptions(
        base_url=base_url,
        out_dir=out_dir,
        max_pages=args.max_pages,
        max_chunks=args.max_chunks,
        repo_max_file_bytes=args.repo_max_file_bytes,
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
    plan_started_at = observe_monotonic()
    try:
        crawl_execution = crawl_source_with_plan(source, options)
        crawl_summary = crawl_execution.summary
        indexing_plan = crawl_execution.indexing_plan
        namespace = args.namespace or str(crawl_summary["namespace_candidate"])
        progress.update("plan: building artifacts", force=True)
        artifact_started_at = observe_monotonic()
        initial_artifacts = build_plan_artifacts(
            indexing_plan=indexing_plan,
            base_url=base_url,
            out_dir=out_dir,
            namespace=namespace,
            crawl_options=plan_crawl_options(args, crawl_summary),
            chunk_options=plan_chunk_options(args),
            embedding_model=DEFAULT_PLAN_EMBEDDING_MODEL,
            embedding_precision=args.embedding_precision,
            state_root=args.state_root,
        )
        artifact_seconds = elapsed_since(artifact_started_at)
        state = load_applied_state(
            site_id=initial_artifacts.manifest.site_id,
            namespace=initial_artifacts.manifest.namespace,
            base_url=base_url,
            state_root=args.state_root,
        )
        progress.update("plan: diffing against local state", force=True)
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
            catalog=plan_catalog,
            catalog_path=plan_catalog_path,
            region=os.environ.get("TURBOPUFFER_REGION", DEFAULT_REGION),
        )
        progress.update("plan: writing review artifacts", force=True)
        publication_started_at = observe_monotonic()
        write_plan_artifacts(artifacts, out_dir)
        publication_seconds = elapsed_since(publication_started_at)
    except (RuntimeError, GitHubRepoError, OSError, ValueError, AppliedStateError, PlanDiffError, json.JSONDecodeError) as exc:
        progress.finish()
        print(str(exc), file=sys.stderr)
        return 2

    progress.finish()
    source_timing = crawl_summary.get("timing")
    timing = dict(source_timing) if isinstance(source_timing, dict) else {}
    for stage in ("sitemap_policy_seconds", "crawl_seconds", "corpus_write_seconds", "chunking_seconds"):
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
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    for warning in cleanup_superseded_plan_directories(
        out_dir / "plan.json",
        namespace=namespace,
        state_root=args.state_root,
    ):
        print(f"Warning: {warning}", file=sys.stderr)
    if args.json:
        _print_json(summary)
    else:
        print_plan_text(summary)
    return 0


def plan_crawl_options(args: argparse.Namespace, crawl_summary: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "max_pages": args.max_pages,
        "max_chunks": args.max_chunks,
        "repo_max_file_bytes": args.repo_max_file_bytes,
        "repo_search_metadata": args.repo_search_metadata,
        "repo_file_cards": args.repo_file_cards,
        "repo_oversize_file_cards": args.repo_oversize_file_cards,
        "concurrent_requests": args.concurrent_requests,
        "concurrent_requests_per_domain": args.concurrent_requests_per_domain,
        "download_delay": args.download_delay,
        "crawl_strategy": args.crawl_strategy,
        "docs_version_policy": getattr(args, "docs_version_policy", DEFAULT_DOCS_VERSION_POLICY),
        "language_policy": getattr(args, "language_policy", DEFAULT_LANGUAGE_POLICY),
        "include_paths": list(crawl_summary.get("include_paths", args.include_path)) if crawl_summary else list(args.include_path),
        "exclude_paths": list(crawl_summary.get("exclude_paths", args.exclude_path)) if crawl_summary else list(args.exclude_path),
        "strip_trailing_slash": args.strip_trailing_slash,
        "css_selector": args.css_selector,
    }


def plan_chunk_options(args: argparse.Namespace) -> dict[str, object]:
    return {
        "target_tokens": args.target_tokens,
        "overlap_sentences": args.overlap_sentences,
    }


def plan_summary(
    *,
    crawl_summary: dict[str, object],
    artifacts: PlanArtifacts,
    diff: IncrementalPlanDiff,
    state_first_apply: bool,
    catalog_registration: dict[str, object] | None = None,
) -> dict[str, object]:
    plan_dict = artifacts.plan_dict()
    diff_summary = diff.summary_dict()
    summary = dict(crawl_summary)
    summary.update(
        {
            "command": "plan",
            "dry_run": True,
            "credentials_required": False,
            "turbopuffer_api_calls": False,
            "api_calls_occurred": False,
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
    return summary


def plan_catalog_registration_preview(
    artifacts: PlanArtifacts,
    *,
    catalog,
    catalog_path: Path,
    region: str,
) -> dict[str, object]:
    manifest = artifacts.manifest
    existing = next((card for card in catalog.cards if card.namespace == manifest.namespace), None)
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
    ranking = ranking_defaults_for_namespace(manifest.namespace)
    return {
        "catalog_path": str(catalog_path),
        "namespace": manifest.namespace,
        "action": (
            "new" if existing is None else
            "manual-preserving-update" if existing.semantic_origin == "manual" else
            "generated-update"
        ),
        "semantic_origin": "manual" if existing and existing.semantic_origin == "manual" else "generated",
        "source_kind": semantics.source_kind,
        "region": region,
        "vector_dimensions": 384,
        **ranking,
    }


def _run_apply(args: argparse.Namespace) -> int:
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
    try:
        catalog_path, catalog_warning = resolve_catalog_path(
            args.catalog, state_root=args.state_root
        )
    except CatalogError as exc:
        progress.finish()
        print(str(exc), file=sys.stderr)
        return 2
    if catalog_warning:
        print(catalog_warning, file=sys.stderr)
    if not args.approve:
        try:
            summary = apply_preflight_summary(
                verified,
                namespace=namespace,
                catalog_path=catalog_path,
                region=region,
                approved=False,
                delete_stale=args.delete_stale,
            )
        except CatalogError as exc:
            progress.finish()
            print(str(exc), file=sys.stderr)
            return 2
        progress.finish()
        if args.json:
            _print_json(summary)
        else:
            print_apply_text(summary)
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
            catalog_path=catalog_path,
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
    if not args.auto_route and (args.route_top_k is not None or args.catalog is not None):
        print("--route-top-k and --catalog are valid only with --auto-route.", file=sys.stderr)
        return 2
    query = args.query.strip()
    if not query:
        print("A non-empty query is required for retrieval.", file=sys.stderr)
        return 2
    if args.auto_route:
        return _run_auto_routed_retrieve(args, query=query)

    try:
        namespaces = resolve_retrieval_namespaces(args)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    base_config = config_from_args(args)
    configs = [replace(base_config, namespace=namespace) for namespace in namespaces]
    options = [
        retrieval_options_from_args(args, config=config, doc_kind=args.doc_kind)
        for config in configs
    ]
    if not args.live:
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
    environment_namespace = os.environ.get("TURBOPUFFER_NAMESPACE", "").strip()
    if environment_namespace:
        print(
            "Warning: --auto-route replaces TURBOPUFFER_NAMESPACE for this retrieval.",
            file=sys.stderr,
        )
    base_config = config_from_args(args)
    try:
        catalog_path, catalog_warning = resolve_catalog_path(args.catalog)
    except CatalogError as exc:
        print(f"Catalog path resolution failed: {exc}", file=sys.stderr)
        return 2
    if catalog_warning:
        print(catalog_warning, file=sys.stderr)
    try:
        catalog = load_catalog(catalog_path)
    except CatalogError as exc:
        print(f"Catalog load failed: {exc}", file=sys.stderr)
        return 2

    eligibility = eligible_catalog_cards(catalog, config=base_config)
    try:
        eligible_cards = require_eligible_cards(eligibility, catalog_path=catalog_path)
    except CatalogError as exc:
        print(f"Catalog eligibility failed: {exc}", file=sys.stderr)
        return 2
    try:
        route_embedder = load_routing_embedder()
    except (CatalogError, RuntimeError) as exc:
        print(f"Route model load failed: {exc}", file=sys.stderr)
        return 2
    try:
        routing = hybrid_route(
            query,
            eligible_cards,
            embedder=route_embedder,
            route_top_k=args.route_top_k or DEFAULT_ROUTE_TOP_K,
            catalog_path=catalog_path,
            catalog_revision=catalog.catalog_revision,
            exclusion_counts=eligibility.exclusion_counts,
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

    if not args.live:
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
    print("Source crawl dry-run (no credentials, embeddings, or turbopuffer API calls):")
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
    print(f"  namespace_candidate: {payload['namespace_candidate']}")
    print(f"  strategy: {payload['crawl_strategy']}")
    if source_kind in {"pdf", "local_file"}:
        print(f"  documents_converted: {payload.get('documents_converted', payload.get('pages_scraped'))}; chunks_generated: {payload['chunks_generated']}")
    else:
        print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
    print_docs_version_summary(payload)
    print_language_summary(payload)
    print(f"  out_dir: {payload['out_dir']}")
    print("  live writes: not supported by this command")


def print_plan_text(payload: dict[str, object]) -> None:
    source_kind = payload.get("source_kind", "website")
    print("Source RAG plan (local-only; no credentials, embeddings, or turbopuffer API calls):")
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
    print(f"  namespace: {payload['namespace']}")
    print(f"  plan_id: {payload['plan_id']}")
    print(f"  embedding_precision: {payload['embedding_precision']}")
    if source_kind in {"pdf", "local_file"}:
        print(f"  documents_converted: {payload.get('documents_converted', payload.get('pages_scraped'))}; chunks_generated: {payload['chunks_generated']}")
    else:
        print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
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
            f"{registration['action']} ({registration['semantic_origin']}); "
            f"{registration['catalog_path']}"
        )
    print("  live writes: not supported by this command; future apply must be explicit")


def print_limit_summary(payload: dict[str, object]) -> None:
    max_pages = payload.get("max_pages")
    max_chunks = payload.get("max_chunks")
    limit_reached = bool(payload.get("limit_reached"))
    if max_pages is not None or max_chunks is not None:
        print(f"  caps: max_pages={max_pages}; max_chunks={max_chunks}; chunk_limit_reached={limit_reached}")
    warnings: list[str] = []
    if max_pages is not None and payload.get("pages_scraped") == max_pages:
        warnings.append("page cap")
    if limit_reached or (max_chunks is not None and payload.get("chunks_generated") == max_chunks):
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


def print_apply_text(payload: dict[str, object]) -> None:
    approved = bool(payload.get("approved"))
    if approved:
        print("Website RAG apply completed (explicitly approved live upsert path):")
    else:
        print("Website RAG apply preflight (no credentials, embeddings, or turbopuffer API calls):")
    print(f"  source: {payload['base_url']}")
    print(f"  plan_path: {payload['plan_path']}")
    print(f"  plan_id: {payload['plan_id']}")
    print(f"  artifact_hash: {payload['artifact_hash']}")
    print(f"  namespace: {payload['namespace']} ({payload['region']})")
    print(f"  embedding_model: {payload['embedding_model']}")
    print(f"  embedding_precision: {payload['embedding_precision']}")
    print(f"  first_apply: {payload['state_first_apply']}")
    diff = payload.get("diff") if isinstance(payload.get("diff"), dict) else {}
    print(
        f"  rows: to_upsert={payload['rows_to_upsert']}; "
        f"upserted={payload['rows_upserted']}; "
        f"unchanged={diff.get('chunks_unchanged', 0)}"
    )
    print(
        f"  embeddings: to_generate={payload['embeddings_to_generate']}; "
        f"generated={payload['embeddings_generated']}"
    )
    print(
        f"  stale_rows: current={payload['stale_rows']}; "
        f"already_retained={payload['retained_stale_rows']}; "
        f"deleted={payload['rows_deleted']}"
    )
    if payload.get("delete_stale"):
        print(f"  stale_intent: delete {payload['stale_rows_to_delete']} stale rows")
    else:
        print(f"  stale_intent: retain {payload['stale_rows_retained']} stale rows")
    print(f"  state_path: {payload['state_path']}")
    registration = payload.get("catalog_registration")
    if isinstance(registration, dict):
        print(
            "  catalog_registration: "
            f"{registration['action']} ({registration['semantic_origin']}); "
            f"{registration['catalog_path']}"
        )
    if "catalog_updated" in payload:
        print(f"  catalog_updated: {payload['catalog_updated']}; catalog: {payload['catalog_path']}")
        if payload.get("pending_cleanup") is False:
            print(f"  pending_cleanup: False; pending_path: {payload['pending_path']}")
            print(f"  repair: {payload['catalog_repair_command']}")
    timing = payload.get("timing")
    if isinstance(timing, dict):
        print(
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
        print(f"  {label} (preview): {commands['preview']}")
        print(f"  {label} (live): {commands['live']}")
    if not approved:
        print("  live: pass --approve to embed and upsert selected rows")


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
            f"  catalog: {routing.get('catalog_path')} "
            f"(revision {routing.get('catalog_revision')})"
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
            print("Retrieval plan (dry-run; local route model only; no credentials or turbopuffer API calls):")
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
        print("  live: pass --live to execute; TURBOPUFFER_API_KEY is read from the environment only")
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
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    try:
        return args.func(args)
    except RuntimeConfigError as exc:
        try:
            print(str(exc), file=sys.stderr)
        except OSError:
            pass
        return 2


def legacy_main(argv: Sequence[str] | None = None) -> int:
    """Run the 0.2 compatibility alias with a bounded deprecation warning."""

    print("Warning: `turbo-search` is deprecated; use `buoy` instead. It will be removed in 0.3.", file=sys.stderr)
    return main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
