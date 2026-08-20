"""Lightweight dispatch for the legacy CLI and local telemetry commands."""

from __future__ import annotations

from collections.abc import Sequence
import sys


def main(argv: Sequence[str] | None = None) -> int:
    """Dispatch telemetry without importing Buoy's provider-facing CLI."""

    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments[:1] == ["telemetry"]:
        from buoy_search.telemetry_cli import main as telemetry_main

        return telemetry_main(arguments[1:])

    from buoy_search.cli import main as legacy_main

    return legacy_main(arguments)
