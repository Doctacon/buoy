"""Command-line interface for website RAG planning, apply, retrieval, and evals."""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path
import shutil
import sys
import time
from typing import TextIO, Sequence

from turbo_search import __version__
from turbo_search.applied_state import AppliedStateError, load_applied_state
from turbo_search.apply import (
    ApplyPlanError,
    apply_preflight_summary,
    discover_latest_plan_path,
    load_verified_apply_plan,
    run_approved_apply,
)
from turbo_search.config import load_config
from turbo_search.crawler import (
    CRAWL_STRATEGIES,
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
    DOCS_VERSION_POLICIES,
    GitHubRepoSource,
    CrawlOptions,
    crawl_site,
    default_out_dir,
    detect_source,
)
from turbo_search.github_repo import GitHubRepoError, crawl_github_repo
from turbo_search.evals import (
    build_dry_run_eval_report,
    load_eval_cases,
    run_live_evals,
)
from turbo_search.chunker import (
    DEFAULT_OVERLAP_SENTENCES,
    DEFAULT_TARGET_TOKENS,
    process_corpus,
)
from turbo_search.plan_artifacts import (
    DEFAULT_PLAN_EMBEDDING_MODEL,
    PlanArtifacts,
    build_plan_artifacts,
    write_plan_artifacts,
)
from turbo_search.plan_diff import IncrementalPlanDiff, PlanDiffError, diff_manifest_against_state
from turbo_search.retriever import (
    DEFAULT_CANDIDATES,
    DEFAULT_TOP_K,
    HybridRetriever,
    RetrievalOptions,
    RetrievalPlan,
    RetrievalResult,
    ranking_defaults_for_namespace,
    retrieval_plan,
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
        self._wrote = True
        self.stream.write(f"\r\x1b[K{self._fit_message(message)}")
        self.stream.flush()

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
        self.stream.write("\r\x1b[K")
        self.stream.flush()
        self._wrote = False


def should_show_progress(args: argparse.Namespace) -> bool:
    return (
        not bool(getattr(args, "json", False))
        and not bool(getattr(args, "no_progress", False))
        and sys.stderr.isatty()
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="turbo-search",
        description="Local site/repository RAG utilities. Planning is local-only by default unless explicitly documented otherwise.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    crawl_parser = subparsers.add_parser(
        "crawl",
        help="crawl a website or public GitHub repo and chunk locally; always dry-run",
        description=(
            "Crawl a public website with Scrapling or ingest a public GitHub repository via git, "
            "generate a local Markdown corpus, and chunk it for namespace planning. This command "
            "is local-only with respect to turbopuffer: it does not read turbopuffer credentials, "
            "embed text, create namespaces, or call turbopuffer."
        ),
    )
    crawl_parser.add_argument(
        "--base-url",
        required=True,
        help="Absolute http(s) URL to crawl.",
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
            "Discovery mode. Default: hybrid, which merges sitemap pages with same-site link discovery. "
            "sitemap trusts sitemap pages with link fallback only when empty; link ignores sitemaps."
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
        help="crawl a website or public GitHub repo and write local review/apply plan artifacts; no live writes",
        description=(
            "Crawl a public website with Scrapling or ingest a public GitHub repository via git, "
            "generate a local Markdown corpus, chunk it, compare it to local applied state, and "
            "write reviewable plan artifacts. This command is local-only with respect to turbopuffer: "
            "it does not read turbopuffer credentials, embed text, create namespaces, or call turbopuffer."
        ),
    )
    plan_parser.add_argument(
        "url",
        nargs="?",
        help="Absolute http(s) URL to crawl and plan.",
    )
    plan_parser.add_argument(
        "--base-url",
        dest="base_url",
        default=None,
        help="Absolute http(s) URL to crawl and plan. Kept for backwards compatibility; positional URL is preferred.",
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
        default=Path(".turbo-search"),
        help="Local applied-state root. Defaults to .turbo-search.",
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
            "Discovery mode. Default: hybrid, which merges sitemap pages with same-site link discovery. "
            "sitemap trusts sitemap pages with link fallback only when empty; link ignores sitemaps."
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
        default=Path(".turbo-search"),
        help="Local applied-state root. Defaults to .turbo-search.",
    )
    apply_parser.add_argument(
        "--batch-size",
        type=positive_int,
        default=64,
        help="Turbopuffer upsert batch size for approved apply mode.",
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
    apply_parser.set_defaults(func=_run_apply)

    retrieve_parser = subparsers.add_parser(
        "retrieve",
        help="retrieve relevant chunks; dry-run plan by default unless --live is passed",
        description=(
            "Plan or execute hybrid retrieval against the configured turbopuffer namespace. "
            "Default mode is safe: it prints the multi-query plan without loading embeddings, "
            "reading credentials, or contacting turbopuffer. Pass --live to embed the query "
            "and query turbopuffer."
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
        help="Print the retrieval plan without credentials, embeddings, or turbopuffer API calls (default).",
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
    add_runtime_config_arguments(retrieve_parser)
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


def add_runtime_config_arguments(command_parser: argparse.ArgumentParser) -> None:
    """Add non-secret turbopuffer runtime overrides to a command."""

    command_parser.add_argument(
        "--region",
        default=None,
        help="Override TURBOPUFFER_REGION for this command without changing the environment.",
    )
    command_parser.add_argument(
        "--namespace",
        default=None,
        help="Override TURBOPUFFER_NAMESPACE for this command without changing the environment.",
    )
    command_parser.add_argument(
        "--embedding-model",
        default=None,
        help="Override TURBO_SEARCH_EMBEDDING_MODEL for this command.",
    )


def config_from_args(args: argparse.Namespace):
    """Load non-secret runtime config, applying CLI overrides when supplied."""

    config = load_config()
    return replace(
        config,
        region=args.region or config.region,
        namespace=args.namespace or config.namespace,
        embedding_model=args.embedding_model or config.embedding_model,
    )


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
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


def _print_json(payload: dict[str, object]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _apply_source_cap_defaults(args: argparse.Namespace, source: object) -> None:
    if args.max_pages is None:
        args.max_pages = DEFAULT_GITHUB_REPO_MAX_FILES if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_PAGES
    if args.max_chunks is None:
        args.max_chunks = DEFAULT_GITHUB_REPO_MAX_CHUNKS if isinstance(source, GitHubRepoSource) else DEFAULT_CRAWL_MAX_CHUNKS


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
        include_paths=tuple(args.include_path),
        exclude_paths=tuple(args.exclude_path),
        strip_trailing_slash=args.strip_trailing_slash,
        css_selector=args.css_selector,
        target_tokens=args.target_tokens,
        overlap_sentences=args.overlap_sentences,
        progress_callback=progress.update if progress.enabled else None,
    )
    try:
        summary = crawl_github_repo(source, options) if isinstance(source, GitHubRepoSource) else crawl_site(options)
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
    if args.url and args.base_url and args.url != args.base_url:
        print("Provide either positional URL or --base-url, not conflicting values.", file=sys.stderr)
        return 2
    requested_url = args.base_url or args.url
    if not requested_url:
        print("base URL is required; pass it as `turbo-search plan <url>` or with --base-url.", file=sys.stderr)
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
        include_paths=tuple(args.include_path),
        exclude_paths=tuple(args.exclude_path),
        strip_trailing_slash=args.strip_trailing_slash,
        css_selector=args.css_selector,
        target_tokens=args.target_tokens,
        overlap_sentences=args.overlap_sentences,
        progress_callback=progress.update if progress.enabled else None,
    )
    try:
        crawl_summary = crawl_github_repo(source, options) if isinstance(source, GitHubRepoSource) else crawl_site(options)
        pages_dir = out_dir / "pages"
        progress.update("plan: chunking generated pages", force=True)
        indexing_plan = process_corpus(
            pages_dir,
            limit_chunks=args.max_chunks,
            target_tokens=args.target_tokens,
            overlap_sentences=args.overlap_sentences,
        )
        namespace = args.namespace or str(crawl_summary["namespace_candidate"])
        progress.update("plan: building initial artifacts", force=True)
        initial_artifacts = build_plan_artifacts(
            indexing_plan=indexing_plan,
            base_url=base_url,
            out_dir=out_dir,
            namespace=namespace,
            crawl_options=plan_crawl_options(args, crawl_summary),
            chunk_options=plan_chunk_options(args),
            embedding_model=DEFAULT_PLAN_EMBEDDING_MODEL,
            state_root=args.state_root,
        )
        state = load_applied_state(
            site_id=initial_artifacts.manifest.site_id,
            namespace=initial_artifacts.manifest.namespace,
            base_url=base_url,
            state_root=args.state_root,
        )
        progress.update("plan: diffing against local state", force=True)
        diff = diff_manifest_against_state(initial_artifacts.manifest, state)
        progress.update("plan: writing review artifacts", force=True)
        artifacts = build_plan_artifacts(
            indexing_plan=indexing_plan,
            base_url=base_url,
            out_dir=out_dir,
            namespace=namespace,
            crawl_options=plan_crawl_options(args, crawl_summary),
            chunk_options=plan_chunk_options(args),
            embedding_model=DEFAULT_PLAN_EMBEDDING_MODEL,
            diff=diff.to_dict(),
            state_root=args.state_root,
        )
        write_plan_artifacts(artifacts, out_dir)
    except (RuntimeError, GitHubRepoError, OSError, ValueError, AppliedStateError, PlanDiffError, json.JSONDecodeError) as exc:
        progress.finish()
        print(str(exc), file=sys.stderr)
        return 2

    progress.finish()
    summary = plan_summary(
        crawl_summary=crawl_summary,
        artifacts=artifacts,
        diff=diff,
        state_first_apply=state.first_apply,
    )
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
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
            "artifact_hash": plan_dict["artifact_hash"],
            "diff": diff_summary,
            **diff_summary,
        }
    )
    return summary


def _run_apply(args: argparse.Namespace) -> int:
    try:
        plan_path = args.plan if args.plan is not None else discover_latest_plan_path()
        verified = load_verified_apply_plan(
            plan_path=plan_path,
            namespace=args.namespace,
            state_root=args.state_root,
        )
    except (ApplyPlanError, AppliedStateError, PlanDiffError, OSError, ValueError, json.JSONDecodeError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    namespace = args.namespace or verified.manifest.namespace
    if not args.approve:
        summary = apply_preflight_summary(
            verified,
            namespace=namespace,
            approved=False,
            delete_stale=args.delete_stale,
        )
        if args.json:
            _print_json(summary)
        else:
            print_apply_text(summary)
        return 0

    config = replace(load_config(), namespace=namespace, embedding_model=str(verified.plan["embedding_model"]))
    try:
        summary = run_approved_apply(
            verified,
            config=config,
            namespace=namespace,
            batch_size=args.batch_size,
            delete_stale=args.delete_stale,
        )
    except (RuntimeError, AppliedStateError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.json:
        _print_json(summary)
    else:
        print_apply_text(summary)
    return 0


def _run_retrieve(args: argparse.Namespace) -> int:
    config = config_from_args(args)
    options = retrieval_options_from_args(args, config=config, doc_kind=args.doc_kind)
    if args.dry_run and args.live:
        print("Choose either --live or --dry-run/--plan, not both.", file=sys.stderr)
        return 2
    if not args.live:
        plan = retrieval_plan(args.query, config=config, options=options)
        if args.json:
            _print_json(plan.to_dict())
        else:
            print_retrieval_text(plan)
        return 0

    try:
        result = HybridRetriever.from_config(config).retrieve(args.query, options)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
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
    print(f"  namespace_candidate: {payload['namespace_candidate']}")
    print(f"  strategy: {payload['crawl_strategy']}")
    print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
    print_docs_version_summary(payload)
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
    print(f"  namespace: {payload['namespace']}")
    print(f"  plan_id: {payload['plan_id']}")
    print(f"  pages_scraped: {payload['pages_scraped']}; chunks_generated: {payload['chunks_generated']}")
    print_limit_summary(payload)
    print_filter_summary(payload)
    print_docs_version_summary(payload)
    diff = payload.get("diff", {}) if isinstance(payload.get("diff"), dict) else {}
    print(
        "  diff: "
        f"first_apply={diff.get('first_apply')}, "
        f"upsert={diff.get('rows_to_upsert')}, "
        f"unchanged={diff.get('chunks_unchanged')}, "
        f"stale={diff.get('stale_rows')}, "
        f"retained_stale={diff.get('retained_stale_rows')}"
    )
    print(f"  plan_path: {payload['plan_path']}")
    print(f"  state_path: {payload['state_path']}")
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


def print_apply_text(payload: dict[str, object]) -> None:
    if payload.get("approved"):
        print("Website RAG apply completed (explicitly approved live upsert path):")
    else:
        print("Website RAG apply preflight (no credentials, embeddings, or turbopuffer API calls):")
    print(f"  namespace: {payload['namespace']}")
    print(f"  plan_id: {payload['plan_id']}")
    print(f"  rows_to_upsert: {payload['rows_to_upsert']}; rows_upserted: {payload['rows_upserted']}")
    print(
        f"  stale_rows: {payload['stale_rows']}; "
        f"retained_stale_rows: {payload['retained_stale_rows']}; "
        f"stale_rows_to_delete: {payload['stale_rows_to_delete']}; "
        f"rows_deleted: {payload['rows_deleted']}"
    )
    print(f"  state_path: {payload['state_path']}")
    if not payload.get("approved"):
        print("  live: pass --approve to embed and upsert selected rows")


def print_retrieval_text(output: RetrievalPlan | RetrievalResult) -> None:
    payload = output.to_dict()
    if payload.get("dry_run"):
        print("Retrieval plan (dry-run; no credentials, embeddings, or turbopuffer API calls):")
        print(f"  query: {payload['query']}")
        print(f"  namespace: {payload['namespace']} ({payload['region']})")
        print(f"  embedding_model: {payload['embedding_model']}")
        print(f"  top_k: {payload['top_k']}; candidates per subquery: {payload['candidates']}")
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
    print(
        f"Retrieved {len(hits)} chunks using {payload.get('fusion')} "
        f"with ranking mode={payload.get('ranking_mode')} profile={payload.get('ranking_profile')} "
        f"aggregation={payload.get('ranking_aggregation')}:"
    )
    for index, hit in enumerate(hits, start=1):
        if not isinstance(hit, dict):
            continue
        title = hit.get("title") or "Untitled"
        url = hit.get("url") or "no URL"
        section_path = hit.get("section_path") or ""
        print(f"\n{index}. {title}")
        print(f"   URL: {url}")
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
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
