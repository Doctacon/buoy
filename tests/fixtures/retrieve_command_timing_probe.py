"""Controlled no-provider subprocess used by the command timing validation ticket."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import patch

started_at_ns = time.time_ns()

from buoy_search import telemetry
from buoy_search.cli import main
from buoy_search.telemetry import (
    EVIDENCE_SPAN_NAME,
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    RERANK_SPAN_NAME,
    retrieval_trace,
    telemetry_span,
)
from buoy_search.telemetry_envelope import decode_trace_envelope_v2
from buoy_search.telemetry_queue import PublicationResult


class ControlledRetriever:
    def __init__(self, mode: str) -> None:
        self.mode = mode

    def retrieve(self, _query: str, _options: object, **_kwargs: object) -> object:
        with retrieval_trace(
            mode=self.mode,
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=5,
            candidates=200,
            namespace_count=1,
            initial_fanout=1,
            routing_selection_reason=(
                "high_confidence_semantic" if self.mode == "automatic" else None
            ),
            routing_semantic_score=0.9 if self.mode == "automatic" else None,
            routing_semantic_margin=0.2 if self.mode == "automatic" else None,
        ) as pipeline:
            with telemetry_span(QUERY_EMBED_SPAN_NAME) as span:
                span.mark_ok()
            with telemetry_span(
                NAMESPACE_QUERY_SPAN_NAME,
                {"buoy.route.rank": 1},
            ) as span:
                span.set_attributes(
                    {
                        "buoy.namespace.status": "ok",
                        "buoy.namespace.hit_count": 0,
                    }
                )
                span.mark_ok()
            if self.mode != "explicit_single":
                with telemetry_span(RERANK_SPAN_NAME) as span:
                    span.mark_ok()
            if self.mode == "automatic":
                with telemetry_span(
                    EVIDENCE_SPAN_NAME,
                    {
                        "buoy.evidence.mode": "active",
                        "buoy.evidence.status": "supported",
                    },
                ):
                    pass
            pipeline.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.final_fanout": 1,
                }
            )
            pipeline.mark_ok()
        return SimpleNamespace(to_dict=lambda: {"dry_run": False, "hits": []})


class ControlledRouting:
    initial_fanout = 1
    selection_reason = "high_confidence_semantic"
    semantic_margin = 0.2
    selected_cards = [
        SimpleNamespace(
            namespace="site-controlled-routing-v1",
            region="gcp-us-central1",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            ranking_mode="page",
            ranking_profile="none",
            ranking_pool=20,
            ranking_aggregation="max",
        )
    ]
    entries = [SimpleNamespace(semantic_score=0.9)]

    def to_dict(self) -> dict[str, object]:
        return {"controlled": True}


def _routing_patches(stage: str, delay_ms: int) -> tuple[object, ...]:
    snapshot = SimpleNamespace(
        eligible_cards=[object()],
        missing_card_ids=(),
        stale_target_ids=(),
        disabled_ids=(),
        incompatible_ids=(),
        snapshot_revision=1,
        counts=SimpleNamespace(
            listed_total=2,
            control_plane_count=1,
            content_live_count=1,
            card_count=1,
            stale_target_count=0,
            missing_card_count=0,
            disabled_count=0,
            incompatible_count=0,
            eligible_count=1,
        ),
        metrics=SimpleNamespace(
            namespace_list_pages=1,
            metadata_requests=1,
            card_query_pages=1,
            billing=(),
        ),
    )
    calibration = SimpleNamespace(
        mode="collect",
        model="cross-encoder/ms-marco-MiniLM-L-6-v2",
        model_revision="0" * 40,
        calibration_id="controlled",
        calibration_revision="controlled",
        feature_contract="controlled",
        threshold=None,
    )

    def route(*_args: object, **_kwargs: object) -> ControlledRouting:
        if stage == "routing":
            time.sleep(delay_ms / 1000)
        return ControlledRouting()

    return (
        patch(
            "buoy_search.cli.ROUTING_CONFIDENCE_FACTORY",
            return_value=SimpleNamespace(mode="collect"),
        ),
        patch("buoy_search.cli.load_evidence_calibration", return_value=calibration),
        patch("buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=object()),
        patch("buoy_search.cli.read_remote_catalog", return_value=snapshot),
        patch("buoy_search.cli.require_eligible", side_effect=lambda value: value),
        patch("buoy_search.cli.ROUTING_EMBEDDER_FACTORY", return_value=object()),
        patch("buoy_search.cli.hybrid_route", side_effect=route),
        patch(
            "buoy_search.cli.MultiNamespaceRetriever.from_configs",
            return_value=ControlledRetriever("automatic"),
        ),
    )


def run(stage: str, delay_ms: int) -> dict[str, object]:
    payloads: list[bytes] = []

    def construct(*_args: object, **_kwargs: object) -> ControlledRetriever:
        if stage == "initialize":
            time.sleep(delay_ms / 1000)
        return ControlledRetriever("explicit_single")

    def render(_value: object) -> None:
        if stage == "render":
            time.sleep(delay_ms / 1000)

    def publish(payload: bytes, *, paths: object) -> PublicationResult:
        del paths
        payloads.append(payload)
        return PublicationResult(True, f"v2-{'0' * 32}.json", "published")

    os.environ["BUOY_TELEMETRY"] = "local"
    if stage == "routing":
        os.environ["TURBOPUFFER_API_KEY"] = "controlled-local-fake"
    args = ["retrieve", "controlled timing query", "--json"]
    if stage != "routing":
        args[2:2] = ["--namespace", "site-controlled-timing-v1"]

    with ExitStack() as stack:
        stack.enter_context(
            patch("buoy_search.cli.HybridRetriever.from_config", side_effect=construct)
        )
        stack.enter_context(patch("buoy_search.cli._print_json", side_effect=render))
        stack.enter_context(patch.object(telemetry, "publish_envelope", side_effect=publish))
        stack.enter_context(patch.object(telemetry, "request_writer_start"))
        for routing_patch in _routing_patches(stage, delay_ms):
            stack.enter_context(routing_patch)
        exit_code = main(args, entry_started_at_ns=started_at_ns)

    rows = decode_trace_envelope_v2(payloads[0])
    assert rows.retrieval_operation is not None
    pipeline = next(span for span in rows.spans if span[3] == "buoy.retrieve.pipeline")
    routing_spans = [
        span
        for span in rows.spans
        if span[3]
        in {"buoy.routing.catalog", "buoy.routing.model", "buoy.routing.select"}
    ]
    return {
        "exit_code": exit_code,
        "stage": stage,
        "delay_ms": delay_ms,
        "command_duration_ms": rows.command[4],
        "pipeline_duration_ms": rows.retrieval_operation[4],
        "routing_stages": [span[3] for span in routing_spans],
        "routing_before_pipeline": bool(routing_spans)
        and all(span[5] <= pipeline[4] for span in routing_spans),
    }


def main_probe() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--stage", choices=("initialize", "routing", "render"), required=True
    )
    parser.add_argument("--delay-ms", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.stage, args.delay_ms), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probe())
