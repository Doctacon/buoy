"""Strict packaged authority for active namespace ranking defaults."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
import json
from pathlib import Path
from typing import Any, Mapping

RANKING_DEFAULTS_RESOURCE = files("buoy_search").joinpath("data/ranking_defaults.json")
RANKING_DEFAULTS_SCHEMA_VERSION = 1
RANKING_DEFAULTS_AUTHORITY_REVISION = "repo-and-website-ranking-defaults-v1"
_AUTHORITY_KEYS = {"authority_revision", "repository", "schema_version", "website"}
_DEFAULT_KEYS = {
    "candidates",
    "ranking_aggregation",
    "ranking_mode",
    "ranking_pool",
    "ranking_profile",
}
_RANKING_MODES = {"chunk", "file", "page"}
_RANKING_PROFILES = {"none", "repo_code"}
_RANKING_AGGREGATIONS = {"max", "adaptive_sum_3", "capped_sum_3"}


class RankingDefaultsError(ValueError):
    """Raised when the packaged ranking-default authority is invalid."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RankingDefaultsError(f"Ranking defaults contain duplicate key {key!r}.")
        result[key] = value
    return result


def _require_exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise RankingDefaultsError(
            f"{label} keys differ: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}."
        )


@dataclass(frozen=True)
class NamespaceRankingDefaults:
    """One validated set of active namespace ranking defaults."""

    candidates: int
    ranking_mode: str
    ranking_profile: str
    ranking_pool: int
    ranking_aggregation: str

    def ranking_options(self) -> dict[str, object]:
        """Return the established public ranking-default mapping."""

        return {
            "ranking_mode": self.ranking_mode,
            "ranking_profile": self.ranking_profile,
            "ranking_pool": self.ranking_pool,
            "ranking_aggregation": self.ranking_aggregation,
        }

    def to_dict(self) -> dict[str, object]:
        """Return the canonical authority representation."""

        return {
            "candidates": self.candidates,
            "ranking_aggregation": self.ranking_aggregation,
            "ranking_mode": self.ranking_mode,
            "ranking_pool": self.ranking_pool,
            "ranking_profile": self.ranking_profile,
        }


@dataclass(frozen=True)
class RankingDefaultsAuthority:
    """Validated active ranking-default authority."""

    schema_version: int
    authority_revision: str
    repository: NamespaceRankingDefaults
    website: NamespaceRankingDefaults

    def to_dict(self) -> dict[str, object]:
        """Return the canonical JSON-compatible authority object."""

        return {
            "authority_revision": self.authority_revision,
            "repository": self.repository.to_dict(),
            "schema_version": self.schema_version,
            "website": self.website.to_dict(),
        }


def _parse_namespace_defaults(value: Any, label: str) -> NamespaceRankingDefaults:
    if not isinstance(value, dict):
        raise RankingDefaultsError(f"{label} ranking defaults must be an object.")
    _require_exact_keys(value, _DEFAULT_KEYS, f"{label} ranking defaults")
    candidates = value["candidates"]
    ranking_pool = value["ranking_pool"]
    if isinstance(candidates, bool) or not isinstance(candidates, int) or candidates <= 0:
        raise RankingDefaultsError(f"{label} candidates must be a positive integer.")
    if isinstance(ranking_pool, bool) or not isinstance(ranking_pool, int) or ranking_pool <= 0:
        raise RankingDefaultsError(f"{label} ranking_pool must be a positive integer.")
    ranking_mode = value["ranking_mode"]
    ranking_profile = value["ranking_profile"]
    ranking_aggregation = value["ranking_aggregation"]
    if ranking_mode not in _RANKING_MODES:
        raise RankingDefaultsError(f"{label} ranking_mode is unsupported.")
    if ranking_profile not in _RANKING_PROFILES:
        raise RankingDefaultsError(f"{label} ranking_profile is unsupported.")
    if ranking_aggregation not in _RANKING_AGGREGATIONS:
        raise RankingDefaultsError(f"{label} ranking_aggregation is unsupported.")
    return NamespaceRankingDefaults(
        candidates=candidates,
        ranking_mode=ranking_mode,
        ranking_profile=ranking_profile,
        ranking_pool=ranking_pool,
        ranking_aggregation=ranking_aggregation,
    )


def parse_ranking_defaults(raw: bytes) -> RankingDefaultsAuthority:
    """Parse strict authority bytes without accepting duplicate or unknown keys."""

    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except RankingDefaultsError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RankingDefaultsError(f"Ranking defaults are not valid UTF-8 JSON: {exc}.") from exc
    if not isinstance(value, dict):
        raise RankingDefaultsError("Ranking defaults must contain a JSON object.")
    _require_exact_keys(value, _AUTHORITY_KEYS, "ranking-default authority")
    if value["schema_version"] != RANKING_DEFAULTS_SCHEMA_VERSION:
        raise RankingDefaultsError("Ranking defaults have an unsupported schema_version.")
    if value["authority_revision"] != RANKING_DEFAULTS_AUTHORITY_REVISION:
        raise RankingDefaultsError("Ranking defaults have an unsupported authority_revision.")
    repository = _parse_namespace_defaults(value["repository"], "repository")
    website = _parse_namespace_defaults(value["website"], "website")
    if repository.candidates != website.candidates:
        raise RankingDefaultsError(
            "Repository and website candidates must remain equal while the public CLI has one shared default."
        )
    return RankingDefaultsAuthority(
        schema_version=value["schema_version"],
        authority_revision=value["authority_revision"],
        repository=repository,
        website=website,
    )


def load_ranking_defaults(path: Path | None = None) -> RankingDefaultsAuthority:
    """Load the strict packaged authority or an explicitly supplied test path."""

    try:
        raw = path.read_bytes() if path is not None else RANKING_DEFAULTS_RESOURCE.read_bytes()
    except OSError as exc:
        raise RankingDefaultsError(f"Could not read ranking defaults: {exc}.") from exc
    return parse_ranking_defaults(raw)


RANKING_DEFAULTS_AUTHORITY = load_ranking_defaults()
REPOSITORY_RANKING_DEFAULTS = RANKING_DEFAULTS_AUTHORITY.repository
WEBSITE_RANKING_DEFAULTS = RANKING_DEFAULTS_AUTHORITY.website
