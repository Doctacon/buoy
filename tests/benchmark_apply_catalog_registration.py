"""Repeatable local performance harness for post-apply catalog registration.

This uses the pinned cached routing model and in-memory provider boundaries. It
performs no network or provider write. Run from the repository root with:

    uv run python -m tests.benchmark_apply_catalog_registration --iterations 40
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import math
from pathlib import Path
import statistics
import tempfile
import time
from unittest.mock import patch

import buoy_search.apply as apply_module
from buoy_search.apply import (
    generated_card_for_apply,
    load_verified_apply_plan,
    register_apply_catalog_card,
)
from buoy_search.catalog import load_routing_embedder
from buoy_search.config import RuntimeConfig
from buoy_search.remote_catalog import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V3,
    CompatibilityContract,
    MutationMetrics,
    MutationResult,
    classify_remote_catalog,
    remote_card_id,
)
from tests.test_apply_catalog_registration import FakeClient, MODEL, REGION
from tests.test_apply_cli import build_saved_plan


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def _summary(values: list[float]) -> dict[str, float]:
    return {
        "median_ms": round(statistics.median(values) * 1000, 3),
        "p95_ms": round(_percentile(values, 0.95) * 1000, 3),
    }


def run(iterations: int) -> dict[str, object]:
    if iterations < 10:
        raise ValueError("iterations must be at least 10")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state_root = root / "state"
        artifacts, plan_path = build_saved_plan(root, state_root=state_root)
        verified = load_verified_apply_plan(
            plan_path=plan_path,
            namespace=artifacts.manifest.namespace,
            state_root=state_root,
        )
        baseline = replace(verified, routing_prototypes=())
        maximum = replace(
            verified,
            routing_prototypes=tuple(
                {
                    "passage_text": (
                        f"Specialist routing evidence {ordinal}: "
                        + ("bounded source context " * 24)
                    )[:512]
                }
                for ordinal in range(8)
            ),
        )
        namespace = artifacts.manifest.namespace
        compatibility = CompatibilityContract(
            region=REGION,
            embedding_model=MODEL,
            embedding_precision="float32",
        )
        empty_snapshot = classify_remote_catalog(
            live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
            cards=(),
            compatibility=compatibility,
            catalog_schema_version=REMOTE_SCHEMA_V3,
        )
        embedder = load_routing_embedder()
        client = FakeClient()
        active_snapshot = [empty_snapshot]

        def create(_resource, cards, **_kwargs):  # noqa: ANN001, ANN003, ANN202
            card = cards[0]
            return MutationResult(
                True,
                card,
                1,
                (remote_card_id(namespace),),
                MutationMetrics(1, 2, ()),
            )

        def update(_resource, card, **_kwargs):  # noqa: ANN001, ANN003, ANN202
            return MutationResult(
                True,
                card,
                1,
                (remote_card_id(namespace),),
                MutationMetrics(1, 2, ()),
            )

        def register(candidate):  # noqa: ANN001, ANN202
            return register_apply_catalog_card(
                candidate,
                config=RuntimeConfig(region=REGION, namespace=namespace),
                namespace=namespace,
                apply_id="apply_benchmark",
                api_key="local-benchmark",
            )

        with patch.object(
            apply_module,
            "REMOTE_CATALOG_CLIENT_FACTORY",
            return_value=client,
        ), patch.object(
            apply_module,
            "read_remote_catalog",
            side_effect=lambda *_args, **_kwargs: active_snapshot[0],
        ), patch.object(
            apply_module,
            "create_remote_cards",
            side_effect=create,
        ), patch.object(
            apply_module,
            "update_remote_card",
            side_effect=update,
        ), patch(
            "buoy_search.catalog.load_routing_embedder",
            return_value=embedder,
        ):
            for _ in range(3):
                register(baseline)
                register(maximum)

            baseline_samples: list[float] = []
            maximum_samples: list[float] = []
            for ordinal in range(iterations):
                order = (
                    ((baseline, baseline_samples), (maximum, maximum_samples))
                    if ordinal % 2 == 0
                    else ((maximum, maximum_samples), (baseline, baseline_samples))
                )
                for candidate, samples in order:
                    started = time.perf_counter()
                    result = register(candidate)
                    samples.append(time.perf_counter() - started)
                    if result["routing_embeddings_generated"] not in {1, 9}:
                        raise AssertionError("embedding-path accounting drifted")

            reusable = generated_card_for_apply(
                maximum,
                namespace=namespace,
                region=REGION,
                apply_id="apply_benchmark",
                existing=None,
            )
            active_snapshot[0] = classify_remote_catalog(
                live_namespace_ids=(REMOTE_CATALOG_NAMESPACE, namespace),
                cards=(reusable,),
                compatibility=compatibility,
                catalog_schema_version=REMOTE_SCHEMA_V3,
            )
            reuse_samples: list[float] = []
            for _ in range(iterations):
                started = time.perf_counter()
                result = register(maximum)
                reuse_samples.append(time.perf_counter() - started)
                if result["routing_embeddings_generated"] != 0:
                    raise AssertionError("unchanged projection was re-embedded")

    baseline_summary = _summary(baseline_samples)
    maximum_summary = _summary(maximum_samples)
    return {
        "iterations_per_path": iterations,
        "harness": "actual_cached_bge_in_memory_catalog",
        "provider_network_calls": 0,
        "baseline_one_text": baseline_summary,
        "maximum_nine_text_batch": maximum_summary,
        "unchanged_projection_reuse": _summary(reuse_samples),
        "maximum_minus_baseline": {
            "median_ms": round(
                maximum_summary["median_ms"] - baseline_summary["median_ms"],
                3,
            ),
            "p95_ms": round(
                maximum_summary["p95_ms"] - baseline_summary["p95_ms"],
                3,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=40)
    args = parser.parse_args()
    print(json.dumps(run(args.iterations), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
