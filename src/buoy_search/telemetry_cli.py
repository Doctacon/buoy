"""Content-free management commands for Buoy's private telemetry writer."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import math


def build_parser() -> argparse.ArgumentParser:
    """Build the standalone, provider-free telemetry command parser."""

    parser = argparse.ArgumentParser(
        prog="buoy telemetry",
        description=(
            "Inspect or flush Buoy's private local telemetry queue. These "
            "commands never contact an OpenTelemetry Collector or a network service."
        ),
    )
    commands = parser.add_subparsers(dest="telemetry_command")

    status = commands.add_parser(
        "status",
        help="inspect telemetry enablement, queue, writer, and store state",
    )
    status.add_argument(
        "--json",
        action="store_true",
        help="emit the stable content-free JSON status object",
    )
    status.set_defaults(func=_run_status)

    flush = commands.add_parser(
        "flush",
        help="start the local writer and wait for the current queue snapshot",
    )
    flush.add_argument(
        "--timeout",
        type=_flush_timeout,
        default=30.0,
        metavar="SECONDS",
        help="maximum wait from 0 through 120 seconds (default: 30)",
    )
    flush.add_argument(
        "--json",
        action="store_true",
        help="emit the stable content-free JSON flush result",
    )
    flush.set_defaults(func=_run_flush)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one standalone telemetry management command."""

    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


def _flush_timeout(value: str) -> float:
    try:
        timeout = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number from 0 through 120") from exc
    if not math.isfinite(timeout) or timeout < 0 or timeout > 120:
        raise argparse.ArgumentTypeError("must be a finite number from 0 through 120")
    return timeout


def _run_status(args: argparse.Namespace) -> int:
    from buoy_search.telemetry_writer import telemetry_status_command

    result = telemetry_status_command(json_output=bool(args.json))
    print(result.output)
    return result.exit_code


def _run_flush(args: argparse.Namespace) -> int:
    from buoy_search.telemetry_writer import telemetry_flush_command

    result = telemetry_flush_command(
        timeout=float(args.timeout),
        json_output=bool(args.json),
    )
    print(result.output)
    return result.exit_code
