"""Explicit one-time model provisioning for an installed Buoy tool.

Normal indexing and search stay offline. Only ``buoy setup --download-models``
permits fetching the two pinned public model snapshots.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path
from typing import NamedTuple

from buoy_search.local_models import BGE_MODEL, BGE_REVISION
from buoy_search.retrieval.cross_encoder import (
    CROSS_ENCODER_MODEL,
    CROSS_ENCODER_REVISION,
)


class ModelSnapshot(NamedTuple):
    model: str
    revision: str
    files: tuple[str, ...]


MODEL_SNAPSHOTS = (
    ModelSnapshot(
        BGE_MODEL,
        BGE_REVISION,
        (
            "1_Pooling/config.json",
            "config_sentence_transformers.json",
            "config.json",
            "model.safetensors",
            "modules.json",
            "sentence_bert_config.json",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.txt",
        ),
    ),
    ModelSnapshot(
        CROSS_ENCODER_MODEL,
        CROSS_ENCODER_REVISION,
        (
            "config.json",
            "model.safetensors",
            "special_tokens_map.json",
            "tokenizer_config.json",
            "tokenizer.json",
            "vocab.txt",
        ),
    ),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="buoy setup",
        description="One-time setup: download Buoy's pinned local models. Indexing and search remain offline.",
    )
    parser.add_argument(
        "--download-models",
        "--download",
        dest="download",
        action="store_true",
        help="permit this command to download the two pinned public models",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="optional HF_HOME-compatible cache root; defaults to the normal Hugging Face cache",
    )
    return parser


def _validate_snapshot(path: Path, snapshot: ModelSnapshot) -> None:
    missing = [name for name in snapshot.files if not (path / name).is_file()]
    if missing:
        names = ", ".join(missing)
        raise RuntimeError(
            f"downloaded snapshot {snapshot.model}@{snapshot.revision} is "
            f"missing required files: {names}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if not args.download:
        parser.error(
            "network use was not authorized; run `buoy setup --download-models` "
            "once on a computer allowed to download model weights"
        )

    # Consent is explicit. Import Hub only after removing offline flags because
    # it reads environment settings at import time. Do not enable remote source
    # acquisition or change the offline-only model constructors.
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    from huggingface_hub import snapshot_download

    cache_root = args.cache_dir.expanduser().resolve() if args.cache_dir else None
    # Operators can copy PATH and select it with HF_HOME=PATH. Hub's cache_dir
    # points one level lower, at PATH/hub.
    hub_cache = os.fspath(cache_root / "hub") if cache_root else None
    for snapshot in MODEL_SNAPSHOTS:
        print(f"Downloading local model: {snapshot.model}@{snapshot.revision}")
        result = snapshot_download(
            repo_id=snapshot.model,
            revision=snapshot.revision,
            cache_dir=hub_cache,
            allow_patterns=list(snapshot.files),
            local_files_only=False,
            token=False,
        )
        _validate_snapshot(Path(result), snapshot)

    if cache_root is not None:
        print(f"Models saved in {cache_root}. Set HF_HOME={cache_root} when running Buoy.")
    print("Models ready. Buoy can now index and search locally without network access.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
