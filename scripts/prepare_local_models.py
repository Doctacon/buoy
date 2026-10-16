#!/usr/bin/env python3
"""ONLINE provisioning for Buoy's exact local model cache.

This command deliberately uses the network.  Run it only on an online staging
machine, then copy the resulting Hugging Face cache to the offline target and
point ``HF_HOME`` at the copied cache if it is not in the default location.

Usage::

    python scripts/prepare_local_models.py --download
    python scripts/prepare_local_models.py --download --cache-dir /mnt/buoy-hf-cache
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
        description=(
            "ONLINE: download Buoy's two exact pinned model snapshots into a "
            "copyable Hugging Face cache"
        )
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="acknowledge and permit network access",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help=(
            "HF_HOME-compatible cache root (snapshots are stored under PATH/hub; "
            "default: the normal Hugging Face cache)"
        ),
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
    args = _parser().parse_args(argv)
    if not args.download:
        raise SystemExit(
            "network use was not authorized; rerun with --download on an online machine"
        )

    # An operator may invoke this script from an otherwise offline-configured
    # shell.  Consent is explicit, so do not pass forced-offline flags into the
    # Hub client.  Import it only after those flags are removed because the Hub
    # reads some environment settings at import time.
    os.environ.pop("HF_HUB_OFFLINE", None)
    os.environ.pop("TRANSFORMERS_OFFLINE", None)
    from huggingface_hub import snapshot_download

    cache_root = args.cache_dir.expanduser().resolve() if args.cache_dir else None
    # Hugging Face interprets cache_dir as HF_HUB_CACHE, while operators copy
    # this script's PATH as HF_HOME.  Store Hub data below PATH/hub so the copy
    # can be selected directly with HF_HOME=PATH on the offline target.
    hub_cache = os.fspath(cache_root / "hub") if cache_root else None
    for snapshot in MODEL_SNAPSHOTS:
        print(f"ONLINE download: {snapshot.model}@{snapshot.revision}")
        result = snapshot_download(
            repo_id=snapshot.model,
            revision=snapshot.revision,
            cache_dir=hub_cache,
            allow_patterns=list(snapshot.files),
            local_files_only=False,
        )
        _validate_snapshot(Path(result), snapshot)

    location = os.fspath(cache_root) if cache_root else "the default Hugging Face cache"
    suffix = (
        f" Set HF_HOME={cache_root} on the offline target."
        if cache_root is not None
        else ""
    )
    print(
        f"Prepared {location}. Copy the complete cache (including blobs and "
        f"symlinks) to the offline target.{suffix}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
