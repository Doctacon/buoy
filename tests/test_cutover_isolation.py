from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import unittest
from unittest.mock import patch

from buoy_search.cli import main
from buoy_search.remote_catalog import CompatibilityContract, ReadMetrics, classify_remote_catalog
from tests.test_remote_catalog import FixedEmbedder, make_card


class CutoverIsolationTests(unittest.TestCase):
    def run_cli(self, args: list[str], *, env: dict[str, str]):
        stdout, stderr = StringIO(), StringIO()
        clean = {
            key: value for key, value in os.environ.items()
            if key not in {"TURBOPUFFER_API_KEY", "TURBOPUFFER_NAMESPACE", "TURBOPUFFER_REGION"}
        }
        clean.update(env)
        with patch.dict(os.environ, clean, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_explicit_namespace_bypass_never_constructs_remote_catalog_client(self) -> None:
        with patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY",
            side_effect=AssertionError("remote factory used for explicit bypass"),
        ), patch(
            "buoy_search.remote_catalog.create_client",
            side_effect=AssertionError("real SDK factory used"),
        ):
            result, stdout, stderr = self.run_cli(
                ["retrieve", "query", "--namespace", "site-explicit-v1", "--json"],
                env={"TURBOPUFFER_API_KEY": "invalid-sentinel", "TURBOPUFFER_NAMESPACE": "ignored"},
            )
        self.assertEqual(result, 0, stderr)
        self.assertEqual(json.loads(stdout)["namespace"], "site-explicit-v1")

    def test_automatic_routing_uses_injected_fake_not_real_sdk_factory(self) -> None:
        card = make_card("site-fake-v1", title="fake route")
        compatibility = CompatibilityContract(
            region=card.region,
            embedding_model=card.embedding_model,
            embedding_precision=card.embedding_precision,
        )
        snapshot = classify_remote_catalog(
            live_namespace_ids=["buoy-routing-catalog-v1", card.namespace],
            cards=[card],
            compatibility=compatibility,
            metrics=ReadMetrics(2, 1, 2, ()),
        )
        fake_client = object()
        with patch(
            "buoy_search.remote_catalog.create_client",
            side_effect=AssertionError("real SDK factory used"),
        ), patch(
            "buoy_search.cli.REMOTE_CATALOG_CLIENT_FACTORY", return_value=fake_client
        ) as factory, patch(
            "buoy_search.cli.read_remote_catalog", return_value=snapshot
        ), patch(
            "buoy_search.cli.load_routing_embedder", return_value=FixedEmbedder()
        ):
            result, stdout, stderr = self.run_cli(
                ["retrieve", "fake route", "--json"],
                env={"TURBOPUFFER_API_KEY": "invalid-sentinel", "TURBOPUFFER_REGION": card.region},
            )
        self.assertEqual(result, 0, stderr)
        factory.assert_called_once_with(api_key="invalid-sentinel", region=card.region)
        payload = json.loads(stdout)
        self.assertEqual(payload["routing"]["selected_cards"][0]["namespace"], card.namespace)
