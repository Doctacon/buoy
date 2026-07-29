"""Read-only Turbopuffer namespace discovery."""

from __future__ import annotations

from collections.abc import Iterable


def list_namespace_ids(*, region: str, api_key: str, search: str | None = None) -> list[str]:
    """Return all visible namespace IDs, optionally filtered by ID substring."""

    try:
        import turbopuffer as tpuf
    except ImportError as exc:  # pragma: no cover - dependency is required by the package.
        raise RuntimeError("turbopuffer is required for namespace discovery. Run `uv sync` first.") from exc

    try:
        client = tpuf.Turbopuffer(api_key=api_key, region=region)  # type: ignore[attr-defined]
        summaries: Iterable[object] = client.namespaces()
        namespace_ids = {
            value
            for summary in summaries
            if not (value := _namespace_id(summary)).startswith("buoy-evidence-")
        }
    except Exception as exc:
        message = str(exc) or exc.__class__.__name__
        raise RuntimeError(
            "Namespace discovery failed. Confirm TURBOPUFFER_API_KEY and TURBOPUFFER_REGION, then retry. "
            f"Underlying error: {message}"
        ) from exc

    if search is not None:
        needle = search.casefold()
        namespace_ids = {namespace_id for namespace_id in namespace_ids if needle in namespace_id.casefold()}
    return sorted(namespace_ids)


def _namespace_id(summary: object) -> str:
    if isinstance(summary, dict):
        value = summary.get("id")
    else:
        value = getattr(summary, "id", None)
    if not isinstance(value, str) or not value:
        raise RuntimeError("Turbopuffer returned a namespace summary without a valid ID.")
    return value
