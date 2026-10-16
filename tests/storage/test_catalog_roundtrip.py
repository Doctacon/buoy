from dataclasses import replace

import duckdb
import pytest

from buoy_search.catalog.local import (
    card_revision,
    card_to_dict,
    parse_card,
    vector_hash,
)
from buoy_search.catalog.remote import (
    REMOTE_CATALOG_NAMESPACE,
    REMOTE_SCHEMA_V3,
    CompatibilityContract,
    RemoteCatalogError,
    create_remote_cards,
    initialize_local_catalog,
    read_remote_catalog,
)
from buoy_search.storage.duckdb import DuckDBClient, DuckDBStorageError
from tests.catalog.test_remote_catalog import MODEL, REGION, make_card


def test_generated_catalog_roundtrip_keeps_vector_hashes(tmp_path):
    client = DuckDBClient(tmp_path / "search.duckdb")
    initialize_local_catalog(client)
    card = make_card("test-docs")
    create_remote_cards(
        client.namespace(REMOTE_CATALOG_NAMESPACE),
        [card],
        region=REGION,
        schema_version=REMOTE_SCHEMA_V3,
    )
    reopened = read_remote_catalog(
        DuckDBClient(client.path),
        region=REGION,
        compatibility=CompatibilityContract(REGION, MODEL, "float32"),
    )
    assert card_to_dict(reopened.cards[0], include_vector=True) == card_to_dict(
        card, include_vector=True
    )


def test_noncanonical_card_is_rejected_before_persistence(tmp_path):
    client = DuckDBClient(tmp_path / "search.duckdb")
    card = make_card("test-docs")
    vector = [1.0 - 1e-10] + [0.0] * 383
    card = replace(
        card,
        vector=vector,
        vector_hash=vector_hash(vector),
        routing_prototype_vector=vector,
        routing_prototype_vector_hash=vector_hash(vector),
    )
    card = replace(card, card_revision=card_revision(card))
    parse_card(
        card_to_dict(card, include_vector=True)
    )  # Valid logical card, not float32.
    with pytest.raises(RemoteCatalogError):
        create_remote_cards(
            client.namespace(REMOTE_CATALOG_NAMESPACE), [card], region=REGION
        )
    assert not client.path.exists()


def test_storage_rejects_changed_retrieval_contract_without_mutation(tmp_path):
    client = DuckDBClient(tmp_path / "search.duckdb")
    initialize_local_catalog(client)
    with duckdb.connect(str(client.path)) as connection:
        connection.execute(
            "UPDATE buoy_storage_metadata SET retrieval_contract = 'older-tokenizer-or-model'"
        )
    with pytest.raises(DuckDBStorageError, match="retrieval contract"):
        client.namespaces()
    with pytest.raises(DuckDBStorageError, match="retrieval contract"):
        client.namespace("new-namespace").write(schema={"title": {"type": "string"}})
    with duckdb.connect(str(client.path), read_only=True) as connection:
        assert connection.execute(
            "SELECT namespace FROM buoy_namespaces"
        ).fetchall() == [(REMOTE_CATALOG_NAMESPACE,)]
