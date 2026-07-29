from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
import os
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from buoy_search.cli import main
from buoy_search.namespaces import list_namespace_ids


class FakePaginator:
    def __init__(self) -> None:
        self.pages_consumed: list[int] = []

    def __iter__(self):
        self.pages_consumed.append(1)
        yield SimpleNamespace(id="site-Dagster-v1")
        yield {"id": "github-owner-repo-v1"}
        self.pages_consumed.append(2)
        yield SimpleNamespace(id="site-other-v1")
        yield SimpleNamespace(id="buoy-evidence-ledger-internal")
        yield SimpleNamespace(id="site-Dagster-v1")


class NamespaceDiscoveryTests(unittest.TestCase):
    def run_main(self, argv: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str, str]:
        stdout = StringIO()
        stderr = StringIO()
        with patch.dict(os.environ, env or {}, clear=True), redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(argv)
        return result, stdout.getvalue(), stderr.getvalue()

    def test_list_namespace_ids_consumes_all_pages_filters_and_sorts(self) -> None:
        paginator = FakePaginator()
        calls: list[tuple[str, str]] = []

        class FakeClient:
            def __init__(self, *, api_key: str, region: str) -> None:
                calls.append((api_key, region))

            def namespaces(self):
                calls.append(("namespaces", "read-only"))
                return paginator

        fake_sdk = SimpleNamespace(Turbopuffer=FakeClient)
        with patch.dict(sys.modules, {"turbopuffer": fake_sdk}):
            result = list_namespace_ids(
                region="gcp-us-west1",
                api_key="secret-test-key",
                search="DAGSTER",
            )

        self.assertEqual(result, ["site-Dagster-v1"])
        self.assertEqual(paginator.pages_consumed, [1, 2])
        self.assertEqual(calls, [("secret-test-key", "gcp-us-west1"), ("namespaces", "read-only")])

    def test_list_namespace_ids_wraps_api_failure(self) -> None:
        class FailingClient:
            def __init__(self, **_kwargs) -> None:
                pass

            def namespaces(self):
                raise OSError("network unavailable")

        with patch.dict(sys.modules, {"turbopuffer": SimpleNamespace(Turbopuffer=FailingClient)}):
            with self.assertRaisesRegex(RuntimeError, "Namespace discovery failed") as raised:
                list_namespace_ids(region="gcp-us-central1", api_key="secret-test-key")

        self.assertIn("network unavailable", str(raised.exception))

    def test_namespaces_text_uses_region_override_and_one_id_per_line(self) -> None:
        with patch("buoy_search.cli.list_namespace_ids", return_value=["github-b-v1", "site-a-v1"]) as listing:
            result, stdout, stderr = self.run_main(
                ["namespaces", "docs", "--region", "aws-us-west-2"],
                env={"TURBOPUFFER_API_KEY": "secret-test-key", "TURBOPUFFER_REGION": "ignored-region"},
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(stdout, "github-b-v1\nsite-a-v1\n")
        self.assertEqual(stderr, "")
        listing.assert_called_once_with(region="aws-us-west-2", api_key="secret-test-key", search="docs")

    def test_namespaces_json_uses_environment_region(self) -> None:
        with patch("buoy_search.cli.list_namespace_ids", return_value=["site-a-v1"]):
            result, stdout, stderr = self.run_main(
                ["namespaces", "--json"],
                env={"TURBOPUFFER_API_KEY": "secret-test-key", "TURBOPUFFER_REGION": "gcp-europe-west3"},
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(
            json.loads(stdout),
            {
                "command": "namespaces",
                "region": "gcp-europe-west3",
                "search": None,
                "count": 1,
                "namespaces": ["site-a-v1"],
            },
        )
        self.assertEqual(stderr, "")

    def test_namespaces_empty_match_is_successful(self) -> None:
        with patch("buoy_search.cli.list_namespace_ids", return_value=[]):
            result, stdout, stderr = self.run_main(
                ["namespaces", "missing"],
                env={"TURBOPUFFER_API_KEY": "secret-test-key"},
            )

        self.assertEqual(result, 0, stderr)
        self.assertEqual(stdout, "No namespaces matched.\n")
        self.assertEqual(stderr, "")

    def test_namespaces_missing_key_fails_before_client_call(self) -> None:
        with patch("buoy_search.cli.list_namespace_ids", side_effect=AssertionError("client called")):
            result, stdout, stderr = self.run_main(["namespaces"])

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertIn("TURBOPUFFER_API_KEY", stderr)

    def test_namespaces_api_failure_is_user_friendly(self) -> None:
        with patch("buoy_search.cli.list_namespace_ids", side_effect=RuntimeError("friendly discovery failure")):
            result, stdout, stderr = self.run_main(
                ["namespaces"],
                env={"TURBOPUFFER_API_KEY": "secret-test-key"},
            )

        self.assertEqual(result, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "friendly discovery failure\n")


if __name__ == "__main__":
    unittest.main()
