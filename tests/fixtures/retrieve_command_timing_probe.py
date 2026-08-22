"""Controlled no-provider subprocess used by the command timing validation ticket."""

from __future__ import annotations

import argparse
import json
import os
import time
from types import SimpleNamespace
from unittest.mock import patch

started_at_ns = time.time_ns()

from buoy_search import telemetry
from buoy_search.cli import main
from buoy_search.telemetry import (
    NAMESPACE_QUERY_SPAN_NAME,
    QUERY_EMBED_SPAN_NAME,
    retrieval_trace,
    telemetry_span,
)
from buoy_search.telemetry_envelope import decode_trace_envelope_v2
from buoy_search.telemetry_queue import PublicationResult


class ControlledRetriever:
    def retrieve(self, _query: str, _options: object) -> object:
        with retrieval_trace(
            mode="explicit_single",
            embedding_model="BAAI/bge-small-en-v1.5",
            embedding_precision="float32",
            top_k=5,
            candidates=200,
            namespace_count=1,
            initial_fanout=1,
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
            pipeline.set_attributes(
                {
                    "buoy.retrieval.outcome": "success",
                    "buoy.retrieval.final_fanout": 1,
                }
            )
            pipeline.mark_ok()
        return SimpleNamespace(to_dict=lambda: {"dry_run": False, "hits": []})


def run(stage: str, delay_ms: int) -> dict[str, object]:
    payloads: list[bytes] = []

    def construct(*_args: object, **_kwargs: object) -> ControlledRetriever:
        if stage == "initialize":
            time.sleep(delay_ms / 1000)
        return ControlledRetriever()

    def render(_value: object) -> None:
        if stage == "render":
            time.sleep(delay_ms / 1000)

    def publish(payload: bytes, *, paths: object) -> PublicationResult:
        del paths
        payloads.append(payload)
        return PublicationResult(True, f"v2-{'0' * 32}.json", "published")

    os.environ["BUOY_TELEMETRY"] = "local"
    with patch(
        "buoy_search.cli.HybridRetriever.from_config", side_effect=construct
    ), patch("buoy_search.cli._print_json", side_effect=render), patch.object(
        telemetry, "publish_envelope", side_effect=publish
    ), patch.object(telemetry, "request_writer_start"):
        exit_code = main(
            [
                "retrieve",
                "controlled timing query",
                "--namespace",
                "site-controlled-timing-v1",
                "--json",
            ],
            entry_started_at_ns=started_at_ns,
        )
    rows = decode_trace_envelope_v2(payloads[0])
    assert rows.retrieval_operation is not None
    return {
        "exit_code": exit_code,
        "stage": stage,
        "delay_ms": delay_ms,
        "command_duration_ms": rows.command[4],
        "pipeline_duration_ms": rows.retrieval_operation[4],
    }


def main_probe() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("initialize", "render"), required=True)
    parser.add_argument("--delay-ms", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.stage, args.delay_ms), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main_probe())
