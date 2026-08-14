#!/usr/bin/env python3
"""Collect and gate Buoy's governed read-only multi-corpus evaluation.

Live collection reads ``TURBOPUFFER_API_KEY`` only from the already-sourced
process environment. It never opens dotenv files and its provider surfaces are
restricted to inventory, catalog reads, and content queries. The persisted run
contains no questions, retrieved text, vectors, model inputs, or credentials.
"""

from __future__ import annotations

import argparse
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from typing import Mapping, Sequence

from buoy_search.catalog import (
    ROUTING_DIMENSIONS,
    ROUTING_MODEL,
    ROUTING_MODEL_REVISION,
    ROUTING_PRECISION,
    ROUTING_QUERY_PREFIX,
    load_routing_embedder,
)
from buoy_search.chunker import SentenceTransformerEmbedder
from buoy_search.config import load_config
from buoy_search.cross_encoder import (
    CROSS_ENCODER_BATCH_SIZE,
    CROSS_ENCODER_MAX_LENGTH,
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
    CrossEncoderReranker,
    load_cross_encoder_reranker,
)
from buoy_search.multi_corpus_evals import (
    DEFAULT_MULTI_CORPUS_EVAL_DATASET,
    EVAL_RUN_SCHEMA_VERSION,
    EVALUATOR_VERSION,
    LIVE_COLLECTOR_PROVENANCE_MARKER,
    MAX_AUTOMATIC_FANOUT,
    MultiCorpusEvalDataset,
    _evaluate_collected_multi_corpus_run,
    canonical_eval_output_url,
    evaluate_multi_corpus_run,
    evaluator_sha256,
    load_multi_corpus_eval_dataset,
)
from buoy_search.remote_catalog import (
    CompatibilityContract,
    RemoteCatalogSnapshot,
    create_client,
    read_remote_catalog,
)
from buoy_search.retriever import (
    CROSS_NAMESPACE_FUSION_COMPONENTS,
    CROSS_NAMESPACE_FUSION_METHOD,
    CROSS_NAMESPACE_RRF_K,
    MAX_RERANK_CANDIDATES_PER_NAMESPACE,
    HybridRetriever,
    MultiNamespaceRetrievalResult,
    MultiNamespaceRetriever,
    RetrievalOptions,
    RetrievalResult,
    SearchHit,
    build_namespace,
    rerank_dedupe_key,
)
from buoy_search.routing import (
    DEFAULT_ROUTE_TOP_K,
    SEMANTIC_CONFIDENCE_FLOOR,
    SEMANTIC_MARGIN_FLOOR,
    hybrid_route,
)


AUTOMATIC_TOP_K = 5
CANDIDATES_PER_NAMESPACE = 200
EXHAUSTIVE_TOP_K = MAX_RERANK_CANDIDATES_PER_NAMESPACE
MAX_EXHAUSTIVE_WORKERS = 3


class EvaluationCollectionError(RuntimeError):
    """A read-only live evaluation could not produce trustworthy observations."""


class _MemoizingCountingEmbedder:
    def __init__(self, delegate: SentenceTransformerEmbedder) -> None:
        self._delegate = delegate
        self._cache: dict[str, list[float]] = {}
        self.inference_calls = 0

    def reset_case_cache(self) -> None:
        self._cache.clear()

    @property
    def model_revision(self) -> str:
        explicit = getattr(self._delegate, "model_revision", None)
        if isinstance(explicit, str) and explicit.strip():
            return explicit.strip()
        model = getattr(self._delegate, "_model", None)
        try:
            config = model[0].auto_model.config
        except (AttributeError, IndexError, KeyError, TypeError) as exc:
            raise EvaluationCollectionError(
                "content embedding model revision could not be resolved for provenance"
            ) from exc
        revision = getattr(config, "_commit_hash", None)
        if not isinstance(revision, str) or not revision.strip():
            raise EvaluationCollectionError(
                "content embedding model revision could not be resolved for provenance"
            )
        return revision.strip()

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        values: list[list[float]] = []
        missing: list[str] = []
        for text in texts:
            if text not in self._cache and text not in missing:
                missing.append(text)
        if missing:
            encoded = self._delegate.encode(missing)
            if len(encoded) != len(missing):
                raise EvaluationCollectionError(
                    "content embedder returned the wrong number of vectors"
                )
            self.inference_calls += 1
            for text, vector in zip(missing, encoded, strict=True):
                self._cache[text] = list(vector)
        for text in texts:
            values.append(list(self._cache[text]))
        return values


class _CachedCountingReranker:
    def __init__(self) -> None:
        self._delegate: CrossEncoderReranker | None = None
        self.inference_calls = 0

    def load(self) -> "_CachedCountingReranker":
        if self._delegate is None:
            self._delegate = load_cross_encoder_reranker()
        return self

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        if self._delegate is None:
            raise EvaluationCollectionError("reranker was not loaded before inference")
        self.inference_calls += 1
        return self._delegate.score(query, passages)


class _ReadOnlyContentNamespace:
    """Expose only the provider query used by ``HybridRetriever``."""

    def __init__(self, delegate: object) -> None:
        self._delegate = delegate
        self._lock = threading.Lock()
        self.query_calls = 0

    def multi_query(self, **kwargs: object) -> object:
        method = getattr(self._delegate, "multi_query", None)
        if method is None:
            raise EvaluationCollectionError("provider namespace has no multi_query API")
        with self._lock:
            self.query_calls += 1
        return method(**kwargs)


def collect_live_run(
    dataset: MultiCorpusEvalDataset,
    *,
    collector_invocation: Sequence[str],
) -> dict[str, object]:
    """Collect all 50 cases using provider reads and exact local model contracts."""

    api_key = os.environ.get("TURBOPUFFER_API_KEY")
    if not api_key:
        raise EvaluationCollectionError(
            "TURBOPUFFER_API_KEY must already be set in the process environment; "
            "this evaluator does not load .env files"
        )
    base_config = load_config()
    client = create_client(api_key=api_key, region=base_config.region)
    snapshot = read_remote_catalog(
        client,
        region=base_config.region,
        compatibility=CompatibilityContract(
            region=base_config.region,
            embedding_model=base_config.embedding_model,
            embedding_precision=base_config.embedding_precision,
        ),
    )
    _require_exact_live_coverage(dataset, snapshot)

    routing_embedder = load_routing_embedder()
    content_embedder = _MemoizingCountingEmbedder(
        SentenceTransformerEmbedder(
            base_config.embedding_model,
            precision=base_config.embedding_precision,
        )
    )
    reranker = _CachedCountingReranker()
    cards = {card.namespace: card for card in snapshot.eligible_cards}
    retrievers: dict[str, HybridRetriever] = {}
    read_only_namespaces: dict[str, _ReadOnlyContentNamespace] = {}
    options: dict[str, RetrievalOptions] = {}
    exhaustive_options: dict[str, RetrievalOptions] = {}
    for namespace in dataset.eligible_namespaces:
        card = cards[namespace]
        config = replace(
            base_config,
            namespace=namespace,
            region=card.region,
            embedding_model=card.embedding_model,
            embedding_precision=card.embedding_precision,
        )
        try:
            content_namespace = build_namespace(config=config, api_key=api_key)
        except Exception:
            content_namespace = None
        if content_namespace is None:
            raise EvaluationCollectionError(
                "content namespace client could not be prepared"
            ) from None
        read_only_namespace = _ReadOnlyContentNamespace(content_namespace)
        read_only_namespaces[namespace] = read_only_namespace
        retrievers[namespace] = HybridRetriever(
            namespace=read_only_namespace,
            embedder=content_embedder,
            config=config,
        )
        options[namespace] = _options_from_card(
            card,
            top_k=AUTOMATIC_TOP_K,
        )
        exhaustive_options[namespace] = _options_from_card(
            card,
            top_k=EXHAUSTIVE_TOP_K,
        )

    cases: list[dict[str, object]] = []
    for case in dataset.cases:
        content_embedder.reset_case_cache()
        case_started = time.perf_counter()
        route_started = time.perf_counter()
        routing = hybrid_route(
            case.question,
            snapshot.eligible_cards,
            embedder=routing_embedder,
            route_top_k=DEFAULT_ROUTE_TOP_K,
            catalog_namespace="buoy-routing-catalog-v1",
            region=base_config.region,
            snapshot_revision=snapshot.snapshot_revision,
        )
        routing_ms = _elapsed_ms(route_started)
        if not 1 <= len(routing.selected_cards) <= MAX_AUTOMATIC_FANOUT:
            raise EvaluationCollectionError(
                f"case {case.id!r} selected an unsafe automatic route size"
            )

        content_before = content_embedder.inference_calls
        reranker_before = reranker.inference_calls
        provider_queries_before = sum(
            namespace.query_calls for namespace in read_only_namespaces.values()
        )
        automatic_started = time.perf_counter()
        query_vectors = content_embedder.encode([case.question])
        if len(query_vectors) != 1 or not query_vectors[0]:
            raise EvaluationCollectionError(
                f"case {case.id!r} did not produce one content query vector"
            )
        selected_namespaces = [card.namespace for card in routing.selected_cards]
        automatic_result = MultiNamespaceRetriever(
            retrievers=[retrievers[namespace] for namespace in selected_namespaces],
            embedder=content_embedder,
            reranker_loader=reranker.load,
        ).retrieve(
            case.question,
            [options[namespace] for namespace in selected_namespaces],
            initial_fanout=routing.initial_fanout,
        )
        automatic_ms = _elapsed_ms(automatic_started)
        provider_queries_after_automatic = sum(
            namespace.query_calls for namespace in read_only_namespaces.values()
        )

        exhaustive_started = time.perf_counter()
        exhaustive_results, exhaustive_failures = _retrieve_exhaustively(
            dataset,
            query=case.question,
            query_vector=query_vectors[0],
            retrievers=retrievers,
            options=exhaustive_options,
        )
        exhaustive_ms = _elapsed_ms(exhaustive_started)
        provider_queries_after_exhaustive = sum(
            namespace.query_calls for namespace in read_only_namespaces.values()
        )
        if content_embedder.inference_calls - content_before != 1:
            raise EvaluationCollectionError(
                f"case {case.id!r} did not reuse exactly one content embedding inference"
            )

        automatic_failures = sorted(
            failure.namespace for failure in automatic_result.failures
        )
        pre_rerank = _pre_rerank_identity_hits(automatic_result)
        cases.append(
            {
                "id": case.id,
                "route": {
                    "namespaces": list(automatic_result.namespaces),
                    # Recall/fanout score the final attempts, while a confident
                    # initial singleton remains reviewable after widening.
                    "initial_high_confidence_namespace": (
                        selected_namespaces[0]
                        if routing.high_confidence and routing.initial_fanout == 1
                        else None
                    ),
                },
                "exhaustive_hits": _identity_hits_from_results(exhaustive_results),
                "automatic_hits": _identity_hits(automatic_result.hits),
                "pre_rerank_hits": pre_rerank,
                "reranked_hits": _identity_hits(automatic_result.hits),
                "timing_ms": {
                    "routing": routing_ms,
                    "automatic": automatic_ms,
                    "exhaustive": exhaustive_ms,
                    "total": _elapsed_ms(case_started),
                },
                "calls": {
                    "routing_embedding_logical_calls": 1,
                    "content_embedding_logical_calls": 1,
                    "reranker_logical_calls": reranker.inference_calls - reranker_before,
                    "automatic_namespace_logical_calls": len(automatic_result.namespaces),
                    "exhaustive_namespace_logical_calls": len(dataset.eligible_namespaces),
                    "automatic_multi_query_logical_calls": (
                        provider_queries_after_automatic - provider_queries_before
                    ),
                    "exhaustive_multi_query_logical_calls": (
                        provider_queries_after_exhaustive
                        - provider_queries_after_automatic
                    ),
                },
                "failures": {
                    "automatic_namespaces": automatic_failures,
                    "exhaustive_namespaces": exhaustive_failures,
                },
            }
        )
        content_embedder.reset_case_cache()

    expected_models = _live_model_provenance(
        base_config=base_config,
        content_model_revision=content_embedder.model_revision,
        content_cards=snapshot.eligible_cards,
    )
    raw_run: dict[str, object] = {
        "schema_version": EVAL_RUN_SCHEMA_VERSION,
        "dataset_id": dataset.dataset_id,
        "mode": "live",
        "provenance": _live_provenance(
            dataset,
            catalog_snapshot_revision=snapshot.snapshot_revision,
            collector_invocation=collector_invocation,
            models=expected_models,
        ),
        "read_only_boundary": {
            # Mutation APIs are intentionally absent from the provider wrapper;
            # this is a structural assertion, not provider telemetry.
            "provider_mutation_methods_exposed": False,
            "provider_mutations_precluded": True,
        },
        "catalog": {
            "snapshot_revision": snapshot.snapshot_revision,
            "live_namespaces": list(snapshot.live_namespace_ids),
            "eligible_namespaces": [card.namespace for card in snapshot.eligible_cards],
            "disabled_namespaces": list(snapshot.disabled_ids),
            "stale_namespaces": list(snapshot.stale_target_ids),
            "missing_namespaces": list(snapshot.missing_card_ids),
            "incompatible_namespaces": list(snapshot.incompatible_ids),
            "read_calls": {
                "namespace_list_logical_calls": snapshot.metrics.namespace_list_pages,
                "metadata_logical_calls": snapshot.metrics.metadata_requests,
                "catalog_query_logical_calls": snapshot.metrics.card_query_pages,
            },
        },
        "cases": cases,
    }
    return _evaluate_collected_multi_corpus_run(
        dataset,
        raw_run,
        expected_catalog_snapshot_revision=snapshot.snapshot_revision,
        expected_models=expected_models,
        expected_collector_invocation=collector_invocation,
    )


def _live_provenance(
    dataset: MultiCorpusEvalDataset,
    *,
    catalog_snapshot_revision: str,
    collector_invocation: Sequence[str],
    models: Mapping[str, object],
) -> dict[str, object]:
    return {
        "origin": LIVE_COLLECTOR_PROVENANCE_MARKER,
        "collector_produced": True,
        "dataset_sha256": dataset.canonical_sha256,
        "code": _git_code_identity(),
        "catalog_snapshot_revision": catalog_snapshot_revision,
        # Copy the independently computed contract into the saved observation;
        # the private evaluator compares it back to the original mapping.
        "models": json.loads(json.dumps(models)),
        "evaluator": {
            "version": EVALUATOR_VERSION,
            "sha256": evaluator_sha256(),
        },
        "collector_invocation": list(collector_invocation),
    }


def _live_model_provenance(
    *,
    base_config: object,
    content_model_revision: str,
    content_cards: Sequence[object],
) -> dict[str, object]:
    """Describe the collector's exact three-model execution contract."""

    return {
        "routing": {
            "model": ROUTING_MODEL,
            "revision": ROUTING_MODEL_REVISION,
            "config": {
                "dimensions": ROUTING_DIMENSIONS,
                "normalized": True,
                "precision": ROUTING_PRECISION,
                "query_prefix": ROUTING_QUERY_PREFIX,
                "route_top_k": DEFAULT_ROUTE_TOP_K,
                "semantic_confidence_floor": SEMANTIC_CONFIDENCE_FLOOR,
                "semantic_margin_floor": SEMANTIC_MARGIN_FLOOR,
            },
        },
        "content_embedding": {
            "model": str(getattr(base_config, "embedding_model")),
            "revision": content_model_revision,
            "config": {
                "automatic_top_k": AUTOMATIC_TOP_K,
                "candidates_per_namespace": CANDIDATES_PER_NAMESPACE,
                "exhaustive_top_k": EXHAUSTIVE_TOP_K,
                "normalize_embeddings": True,
                "precision": str(getattr(base_config, "embedding_precision")),
                "region": str(getattr(base_config, "region")),
                "namespace_retrieval": {
                    str(getattr(card, "namespace")): {
                        "ranking_aggregation": str(
                            getattr(card, "ranking_aggregation")
                        ),
                        "ranking_mode": str(getattr(card, "ranking_mode")),
                        "ranking_pool": int(getattr(card, "ranking_pool")),
                        "ranking_profile": str(getattr(card, "ranking_profile")),
                    }
                    for card in sorted(
                        content_cards,
                        key=lambda value: str(getattr(value, "namespace")),
                    )
                },
            },
        },
        "reranker": {
            "model": CROSS_ENCODER_MODEL,
            "revision": CROSS_ENCODER_REVISION,
            "config": {
                "batch_size": CROSS_ENCODER_BATCH_SIZE,
                "cross_namespace_fusion_components": list(
                    CROSS_NAMESPACE_FUSION_COMPONENTS
                ),
                "cross_namespace_fusion_method": CROSS_NAMESPACE_FUSION_METHOD,
                "cross_namespace_rrf_k": CROSS_NAMESPACE_RRF_K,
                "device": "cpu",
                "max_candidates_per_namespace": MAX_RERANK_CANDIDATES_PER_NAMESPACE,
                "max_length": CROSS_ENCODER_MAX_LENGTH,
                "namespace_coverage_policy": (
                    "retain_one_namespace_local_rank_one_hit_per_nonempty_namespace_when_top_k_allows"
                ),
            },
        },
    }


def _git_code_identity() -> dict[str, object]:
    repo = Path(__file__).resolve().parents[1]

    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip()

    try:
        commit = run("rev-parse", "HEAD")
        tree = run("rev-parse", "HEAD^{tree}")
        status = run("status", "--porcelain", "--untracked-files=normal")
    except (OSError, subprocess.CalledProcessError) as exc:
        raise EvaluationCollectionError(
            "live release evidence requires an identifiable Git commit and tree"
        ) from exc
    return {
        "commit": commit,
        "tree": tree,
        "working_tree_clean": not bool(status),
    }


def _require_exact_live_coverage(
    dataset: MultiCorpusEvalDataset,
    snapshot: RemoteCatalogSnapshot,
) -> None:
    expected_live = {item.namespace for item in dataset.physical_namespaces}
    expected_eligible = set(dataset.eligible_namespaces)
    expected_disabled = set(dataset.disabled_duplicate_namespaces)
    if set(snapshot.live_namespace_ids) != expected_live:
        raise EvaluationCollectionError(
            "live content namespace inventory does not match the governed five-namespace basket"
        )
    if snapshot.missing_card_ids:
        raise EvaluationCollectionError("live routing catalog has missing card coverage")
    if snapshot.incompatible_ids:
        raise EvaluationCollectionError("live routing catalog has incompatible card coverage")
    if {card.namespace for card in snapshot.eligible_cards} != expected_eligible:
        raise EvaluationCollectionError(
            "live routing catalog does not expose exactly the governed four eligible corpora"
        )
    if set(snapshot.disabled_ids) != expected_disabled:
        raise EvaluationCollectionError(
            "live routing catalog must disable exactly the governed duplicate Dagster namespace"
        )


def _options_from_card(card: object, *, top_k: int) -> RetrievalOptions:
    return RetrievalOptions(
        top_k=top_k,
        candidates=CANDIDATES_PER_NAMESPACE,
        ranking_mode=str(getattr(card, "ranking_mode")),
        ranking_profile=str(getattr(card, "ranking_profile")),
        ranking_pool=int(getattr(card, "ranking_pool")),
        ranking_aggregation=str(getattr(card, "ranking_aggregation")),
    )


def _retrieve_exhaustively(
    dataset: MultiCorpusEvalDataset,
    *,
    query: str,
    query_vector: Sequence[float],
    retrievers: Mapping[str, HybridRetriever],
    options: Mapping[str, RetrievalOptions],
) -> tuple[list[RetrievalResult], list[str]]:
    futures: dict[Future[RetrievalResult], str] = {}
    with ThreadPoolExecutor(max_workers=MAX_EXHAUSTIVE_WORKERS) as executor:
        for namespace in dataset.eligible_namespaces:
            futures[
                executor.submit(
                    retrievers[namespace].retrieve_embedded,
                    query,
                    query_vector,
                    options[namespace],
                )
            ] = namespace
        results: list[RetrievalResult] = []
        failures: list[str] = []
        for future, namespace in futures.items():
            try:
                results.append(future.result())
            except RuntimeError:
                failures.append(namespace)
    results.sort(key=lambda result: dataset.eligible_namespaces.index(result.namespace))
    return results, sorted(failures)


def _pre_rerank_identity_hits(
    result: MultiNamespaceRetrievalResult,
) -> list[dict[str, str]]:
    if not result.reranking.applied:
        return _identity_hits(result.hits)
    ordered_results = sorted(
        result.namespace_results,
        key=lambda item: result.namespace_route_ranks[item.namespace],
    )
    seen_content: set[tuple[str, str, str]] = set()
    candidates: list[SearchHit] = []
    # Compare reranking against a deterministic, route-aware interleave. A
    # route-concatenated list unfairly gives the first namespace every early
    # position, while this round-robin preserves each namespace's local rank.
    for local_rank in range(MAX_RERANK_CANDIDATES_PER_NAMESPACE):
        for namespace_result in ordered_results:
            if local_rank >= len(namespace_result.hits):
                continue
            hit = namespace_result.hits[local_rank]
            namespaced = replace(hit, namespace=namespace_result.namespace)
            key = rerank_dedupe_key(namespaced)
            if key in seen_content:
                continue
            seen_content.add(key)
            candidates.append(namespaced)
    return _identity_hits(candidates)


def _identity_hits_from_results(
    results: Sequence[RetrievalResult],
) -> list[dict[str, str]]:
    hits: list[SearchHit] = []
    for result in results:
        hits.extend(replace(hit, namespace=result.namespace) for hit in result.hits)
    return _identity_hits(hits)


def _identity_hits(hits: Sequence[SearchHit]) -> list[dict[str, str]]:
    identities: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for hit in hits:
        if not hit.namespace or not hit.url:
            raise EvaluationCollectionError(
                "evaluation retrieval returned a hit without namespace/URL identity"
            )
        url = canonical_eval_output_url(hit.url)
        key = hit.namespace, url
        if key in seen:
            continue
        seen.add(key)
        identities.append({"namespace": hit.namespace, "url": url})
    return identities


def _elapsed_ms(started: float) -> float:
    return (time.perf_counter() - started) * 1000.0


def _load_json(path: Path) -> Mapping[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_report(path: Path, report: Mapping[str, object]) -> None:
    if path.exists():
        raise ValueError(f"refusing to overwrite existing evaluation report: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.replace(temp_path, path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect or validate Buoy's read-only 50-case multi-corpus gate."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    collect = commands.add_parser(
        "collect",
        help="run the provider-backed read-only collector",
    )
    collect.add_argument("--dataset", type=Path, default=DEFAULT_MULTI_CORPUS_EVAL_DATASET)
    collect.add_argument("--output", type=Path, required=True)

    fixture = commands.add_parser(
        "fixture",
        help="score injected observations without loading credentials, providers, or models",
    )
    fixture.add_argument("--dataset", type=Path, default=DEFAULT_MULTI_CORPUS_EVAL_DATASET)
    fixture.add_argument("--input", type=Path, required=True)
    fixture.add_argument("--output", type=Path, required=True)

    validate = commands.add_parser(
        "validate-run",
        help="recompute a saved run's metrics and release verdict offline",
    )
    validate.add_argument("run", type=Path)
    validate.add_argument("--dataset", type=Path, default=DEFAULT_MULTI_CORPUS_EVAL_DATASET)
    validate.add_argument("--output", type=Path, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        dataset = load_multi_corpus_eval_dataset(args.dataset)
        if args.command == "collect":
            report = collect_live_run(
                dataset,
                collector_invocation=(
                    "collect",
                    "--dataset",
                    str(args.dataset.resolve()),
                    "--output",
                    str(args.output.resolve()),
                ),
            )
            _write_report(args.output, report)
        elif args.command == "fixture":
            fixture_payload = _load_json(args.input)
            if fixture_payload.get("mode") != "fixture":
                raise ValueError("fixture input must declare mode='fixture'")
            report = evaluate_multi_corpus_run(dataset, fixture_payload)
            _write_report(args.output, report)
        else:
            report = evaluate_multi_corpus_run(dataset, _load_json(args.run))
            if args.output is not None:
                _write_report(args.output, report)
            else:
                print(json.dumps(report, indent=2, sort_keys=True))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Multi-corpus evaluation failed: {exc}", file=sys.stderr)
        return 2

    verdict = report["verdict"]
    if not isinstance(verdict, Mapping):
        raise AssertionError("evaluation verdict must be an object")
    print(
        json.dumps(
            {
                "release_ready": verdict["release_ready"],
                "status": verdict["status"],
                "failed_checks": verdict["failed_checks"],
            },
            sort_keys=True,
        ),
        file=sys.stderr if args.command == "validate-run" and args.output is None else sys.stdout,
    )
    return 0 if verdict["release_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
