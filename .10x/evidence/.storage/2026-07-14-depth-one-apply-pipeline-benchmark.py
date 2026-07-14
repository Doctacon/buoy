"""No-remote benchmark for the depth-one approved-apply pipeline."""

from __future__ import annotations

from concurrent.futures import Future
from contextlib import nullcontext
import json
from pathlib import Path
import statistics
import tempfile
import time
from unittest.mock import patch

from buoy_search.apply import load_verified_apply_plan, run_approved_apply
from buoy_search.chunker import process_corpus
from buoy_search.config import RuntimeConfig
from buoy_search.plan_artifacts import build_plan_artifacts, write_plan_artifacts

ROWS = 16
EMBED_SECONDS = 0.04
WRITE_SECONDS = 0.02
RUNS = 5


def write_page(corpus: Path, index: int) -> None:
    corpus.mkdir(parents=True, exist_ok=True)
    (corpus / f"{index}.md").write_text(
        "\n".join(
            [
                "---",
                f'url: "https://example.com/docs/{index}"',
                f'title: "Page {index}"',
                'status: "200"',
                'content_type: "text/html"',
                'source_hash: "source-hash"',
                'crawl_timestamp: "2026-07-14T00:00:00+00:00"',
                'fetcher: "benchmark"',
                "---",
                "",
                f"# Page {index}\n\nUseful benchmark content {index}.",
            ]
        )
    )


class DelayEmbedder:
    def __init__(self, _model_name: str, *, precision: str = "float32") -> None:
        self.precision = precision

    def encode(self, texts, *, batch_size: int = 32):
        del batch_size
        time.sleep(EMBED_SECONDS)
        return [[1.0, 0.0, 1.0] for _ in texts]


class DelayWriter:
    def __init__(self, *, config, api_key: str, schema=None) -> None:
        del config, api_key, schema

    def upsert_rows(self, rows) -> None:
        assert len(rows) == 1
        time.sleep(WRITE_SECONDS)

    def delete_rows(self, row_ids) -> None:
        raise AssertionError(f"unexpected delete: {row_ids}")


class ImmediateExecutor:
    """Execute submit synchronously to reproduce the previous serial ordering."""

    def __init__(self, *, max_workers: int, thread_name_prefix: str) -> None:
        assert max_workers == 1
        del thread_name_prefix

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        del exc_type, exc, traceback

    def submit(self, fn, *args) -> Future:
        future: Future = Future()
        try:
            future.set_result(fn(*args))
        except BaseException as exc:
            future.set_exception(exc)
        return future


def run_once(*, pipelined: bool) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        corpus = root / "pages"
        for index in range(ROWS):
            write_page(corpus, index)
        state_root = root / "state"
        out_dir = root / "plan"
        artifacts = build_plan_artifacts(
            indexing_plan=process_corpus(corpus),
            base_url="https://example.com/docs/",
            out_dir=out_dir,
            state_root=state_root,
        )
        write_plan_artifacts(artifacts, out_dir)
        verified = load_verified_apply_plan(
            plan_path=out_dir / "plan.json",
            namespace=artifacts.manifest.namespace,
            state_root=state_root,
        )
        executor_patch = (
            nullcontext()
            if pipelined
            else patch("buoy_search.apply.ThreadPoolExecutor", ImmediateExecutor)
        )
        with patch.dict("os.environ", {"TURBOPUFFER_API_KEY": "no-remote-benchmark"}, clear=True), patch(
            "buoy_search.apply.SentenceTransformerEmbedder", DelayEmbedder
        ), patch("buoy_search.apply.TurbopufferWriter", DelayWriter), executor_patch:
            started = time.perf_counter()
            summary = run_approved_apply(
                verified,
                config=RuntimeConfig(namespace=artifacts.manifest.namespace),
                namespace=artifacts.manifest.namespace,
                batch_size=1,
                embedding_batch_size=1,
            )
            elapsed = time.perf_counter() - started
        assert summary["rows_upserted"] == ROWS
        assert summary["timing"]["pipeline_mode"] == "depth_one"
        return elapsed


def main() -> None:
    serial = [run_once(pipelined=False) for _ in range(RUNS)]
    pipeline = [run_once(pipelined=True) for _ in range(RUNS)]
    serial_median = statistics.median(serial)
    pipeline_median = statistics.median(pipeline)
    output = {
        "created": "2026-07-14",
        "kind": "deterministic no-remote delay benchmark",
        "rows": ROWS,
        "write_batch_size": 1,
        "embedding_delay_seconds_per_batch": EMBED_SECONDS,
        "write_delay_seconds_per_batch": WRITE_SECONDS,
        "runs": RUNS,
        "serial_seconds": serial,
        "pipeline_seconds": pipeline,
        "serial_median_seconds": serial_median,
        "pipeline_median_seconds": pipeline_median,
        "median_reduction_seconds": serial_median - pipeline_median,
        "median_reduction_fraction": 1.0 - pipeline_median / serial_median,
        "remote_calls": 0,
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
