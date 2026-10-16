#!/usr/bin/env python3
"""Exercise real cached CPU models and DuckDB without touching existing Buoy data.

Run after installing this branch and transferring the pinned model cache:
    python scripts/smoke_local_install.py

No downloads are attempted. Python INET socket connections are forbidden for
this in-process check; this guard is not a replacement for an OS firewall.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path


def main() -> None:
    previous_environment = dict(os.environ)
    os.environ.update(
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        BUOY_TELEMETRY="off",
        BUOY_DEVICE="cpu",
    )
    os.environ.pop("BUOY_ALLOW_NETWORK", None)
    original_connect = socket.socket.connect

    def local_connect(connection: socket.socket, address: object) -> object:
        if connection.family != socket.AF_UNIX:
            raise AssertionError(
                "Network connection attempted during offline smoke test"
            )
        return original_connect(connection, address)

    socket.socket.connect = local_connect
    from buoy_search.cli.main import main as buoy_main

    def cli(*args: str) -> dict:
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = buoy_main([*args, "--json"])
        if result != 0:
            raise RuntimeError(
                f"{' '.join(args)}: {stderr.getvalue()} {stdout.getvalue()}"
            )
        return json.loads(stdout.getvalue())

    try:
        with tempfile.TemporaryDirectory(prefix="buoy-offline-smoke-") as temporary:
            root = Path(temporary)
            os.environ["BUOY_HOME"] = str(root / "home")
            document = root / "deployment.md"
            document.write_text(
                "# Deployment procedure\n\nDeploy the payment service using a blue-green "
                "rollout. Run health checks on the green environment before switching "
                "traffic. Roll back by switching the load balancer to the blue environment.\n",
                encoding="utf-8",
            )
            cli("plan", str(document), "--namespace", "offline-smoke")
            applied = cli("apply", "--approve")
            explicit = cli(
                "retrieve",
                "How do we roll back the payment service?",
                "--namespace",
                "offline-smoke",
                "--no-embedding-worker",
            )
            automatic = cli(
                "retrieve",
                "How do we roll back the payment service?",
                "--no-embedding-worker",
            )
            if (
                not applied["catalog_registered"]
                or not explicit["hits"]
                or not automatic["hits"]
            ):
                raise RuntimeError(
                    "Offline apply/search smoke test returned no registered hits"
                )
            if "blue environment" not in explicit["hits"][0]["content"]:
                raise RuntimeError(
                    "Offline retrieval did not return the expected local passage"
                )
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "inference": "pinned CPU models, offline",
                        "rows_upserted": applied["rows_upserted"],
                        "explicit_hits": len(explicit["hits"]),
                        "automatic_hits": len(automatic["hits"]),
                        "fusion": explicit["fusion"],
                        "catalog_registered": applied["catalog_registered"],
                    },
                    indent=2,
                )
            )
    finally:
        socket.socket.connect = original_connect
        os.environ.clear()
        os.environ.update(previous_environment)


if __name__ == "__main__":
    main()
