"""Bind incremental apply to the actual local index, not only its state ledger."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from contextlib import contextmanager
from typing import TYPE_CHECKING

import portalocker

from buoy_search.local_paths import default_buoy_home, prepare_default_buoy_home
from buoy_search.storage.duckdb import DuckDBClient, DuckDBStorageError

if TYPE_CHECKING:
    from buoy_search.planning.apply import VerifiedApplyPlan


@contextmanager
def local_namespace_apply_lock(namespace: str) -> Iterator[None]:
    """Serialize a namespace across every source and explicit state-root override.

    This lock spans batches and the state/catalog commits, unlike the shorter
    database connection lock. Retrieval remains available between transactions.
    """
    home = default_buoy_home()
    prepare_default_buoy_home(home, require_resolved_home=True)
    directory = home / "index-apply-locks"
    directory.mkdir(mode=0o700, exist_ok=True)
    identity = hashlib.sha256(namespace.encode("utf-8")).hexdigest()
    try:
        with portalocker.Lock(
            str(directory / f"{identity}.lock"),
            mode="a+",
            timeout=0,
            fail_when_locked=True,
        ):
            yield
    except portalocker.exceptions.LockException as exc:
        raise DuckDBStorageError(
            f"another local apply already owns namespace {namespace!r}; retry after it finishes"
        ) from exc


def validate_local_index_baseline(
    verified: VerifiedApplyPlan, *, delete_stale: bool
) -> None:
    """Refuse mismatched/missing index data before models, writes or state commit.

    Allow the exact current plan's already-written upserts/deletes so a failed
    batched apply can be retried. Unchanged rows must still exist and match.
    Unexpected rows for this source indicate a lost/wrong applied-state ledger.
    """
    namespace = str(verified.plan["namespace"])
    site_id = str(verified.plan["site_id"])
    expected = {
        row.row_id: row.embedding_text_hash
        for row in verified.state.rows
        if row.status in {"active", "retained_stale"}
    }
    upserts = {
        str(row["row_id"]): str(row["embedding_text_hash"])
        for row in verified.upsert_rows
    }
    # Only an explicitly approved delete may account for an absent stale row.
    stale = (
        {str(row["row_id"]) for row in verified.stale_rows} if delete_stale else set()
    )
    actual = DuckDBClient().source_row_fingerprints(namespace, site_id)
    required = set(expected) - set(upserts) - stale
    missing = required - set(actual)
    unexpected = set(actual) - set(expected) - set(upserts)
    mismatched = {
        row_id
        for row_id in set(actual) & required
        if actual[row_id] != expected[row_id]
    }
    # New rows from a partial attempt must be exactly this plan's rows, not
    # another embedding contract that happened to retain an ID.
    mismatched.update(
        row_id
        for row_id in set(actual) & set(upserts)
        if actual[row_id] not in {upserts[row_id], expected.get(row_id)}
    )
    if missing or unexpected or mismatched:
        raise DuckDBStorageError(
            "Local index and applied-state baseline do not match "
            f"(missing={len(missing)}, unexpected={len(unexpected)}, changed={len(mismatched)}). "
            "The search database may have been removed/replaced, or --state-root belongs "
            "to another index. Restore the complete BUOY_HOME backup, or re-plan and "
            "rebuild in a fresh BUOY_HOME with no old state override. Nothing was applied."
        )
