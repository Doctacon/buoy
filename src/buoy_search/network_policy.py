"""Explicit opt-in for source acquisition; search and models are always local."""

from __future__ import annotations

import os

REMOTE_SOURCE_KINDS = frozenset(
    {"website", "github_repo", "bigquery_relation", "snowflake_relation"}
)


def require_source_network(source: object) -> None:
    """Reject online source acquisition unless this command was explicitly enabled.

    This is an application guard, not an OS firewall. The setting never enables
    remote vector storage, model downloads, or telemetry exporters.
    """
    if getattr(source, "kind", None) not in REMOTE_SOURCE_KINDS:
        return
    if os.environ.get("BUOY_ALLOW_NETWORK") != "1":
        raise RuntimeError(
            "Network source acquisition is disabled in local Buoy. Use a local document "
            "or DuckDB relation. Only on an approved connected machine, set "
            "BUOY_ALLOW_NETWORK=1 for an explicit website/GitHub/warehouse import."
        )
