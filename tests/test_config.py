from __future__ import annotations

import os
from unittest.mock import patch
import unittest

from buoy_search.config import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_PRECISION,
    RuntimeConfigError,
    load_config,
    removed_embedding_environment_error,
)


class RuntimeConfigTests(unittest.TestCase):
    def test_default_embedding_model_uses_no_branded_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = load_config(warning_callback=lambda _message: self.fail("unexpected warning"))

        self.assertEqual(config.embedding_model, DEFAULT_EMBEDDING_MODEL)

    def test_current_embedding_model_environment_wins(self) -> None:
        warnings: list[str] = []
        with patch.dict(os.environ, {"BUOY_EMBEDDING_MODEL": "current/model"}, clear=True):
            config = load_config(warning_callback=warnings.append)

        self.assertEqual(config.embedding_model, "current/model")
        self.assertEqual(warnings, [])

    def test_removed_embedding_model_never_becomes_configuration(self) -> None:
        warnings: list[str] = []
        with patch.dict(os.environ, {"TURBO_SEARCH_EMBEDDING_MODEL": "removed/model"}, clear=True):
            config = load_config(warning_callback=warnings.append)

        self.assertEqual(config.embedding_model, DEFAULT_EMBEDDING_MODEL)
        self.assertEqual(warnings, [])

    def test_current_embedding_model_is_unchanged_when_removed_name_is_present(self) -> None:
        warnings: list[str] = []
        with patch.dict(
            os.environ,
            {"BUOY_EMBEDDING_MODEL": "current/model", "TURBO_SEARCH_EMBEDDING_MODEL": "removed/model"},
            clear=True,
        ):
            config = load_config(warning_callback=warnings.append)

        self.assertEqual(config.embedding_model, "current/model")
        self.assertEqual(warnings, [])

    def test_removed_environment_diagnostic_is_presence_based_and_ordered(self) -> None:
        self.assertIsNone(removed_embedding_environment_error({}))
        self.assertEqual(
            removed_embedding_environment_error({"TURBO_SEARCH_EMBEDDING_MODEL": ""}),
            "Removed environment variable is not supported in Buoy 0.4.0: "
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL",
        )
        self.assertEqual(
            removed_embedding_environment_error(
                {
                    "TURBO_SEARCH_EMBEDDING_PRECISION": "precision-secret",
                    "TURBO_SEARCH_EMBEDDING_MODEL": "model-secret",
                }
            ),
            "Removed environment variables are not supported in Buoy 0.4.0: "
            "TURBO_SEARCH_EMBEDDING_MODEL -> BUOY_EMBEDDING_MODEL; "
            "TURBO_SEARCH_EMBEDDING_PRECISION -> BUOY_EMBEDDING_PRECISION",
        )

    def test_embedding_precision_defaults_to_float32(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = load_config(warning_callback=lambda _message: self.fail("unexpected warning"))
        self.assertEqual(config.embedding_precision, DEFAULT_EMBEDDING_PRECISION)

    def test_current_embedding_precision_environment_is_unchanged(self) -> None:
        with patch.dict(os.environ, {"BUOY_EMBEDDING_PRECISION": "float16"}, clear=True):
            config = load_config(warning_callback=lambda _message: self.fail("unexpected warning"))
        self.assertEqual(config.embedding_precision, "float16")

    def test_removed_embedding_precision_never_becomes_configuration(self) -> None:
        with patch.dict(os.environ, {"TURBO_SEARCH_EMBEDDING_PRECISION": "float16"}, clear=True):
            config = load_config(warning_callback=lambda _message: self.fail("unexpected warning"))
        self.assertEqual(config.embedding_precision, DEFAULT_EMBEDDING_PRECISION)

    def test_embedding_precision_invalid_current_value_fails(self) -> None:
        with patch.dict(os.environ, {"BUOY_EMBEDDING_PRECISION": "int8"}, clear=True):
            with self.assertRaisesRegex(RuntimeConfigError, "float32, float16"):
                load_config(warning_callback=lambda _message: None)

    def test_turbopuffer_environment_names_remain_unchanged(self) -> None:
        with patch.dict(
            os.environ,
            {"TURBOPUFFER_REGION": "local-region", "TURBOPUFFER_NAMESPACE": "site-preserved-v1"},
            clear=True,
        ):
            config = load_config(warning_callback=lambda _message: None)

        self.assertEqual(config.region, "local-region")
        self.assertEqual(config.namespace, "site-preserved-v1")


if __name__ == "__main__":
    unittest.main()
