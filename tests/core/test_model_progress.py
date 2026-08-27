from __future__ import annotations

import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from buoy_search.model_progress import suppress_model_progress_bars


class ModelProgressTests(unittest.TestCase):
    def test_suppression_restores_enabled_third_party_progress(self) -> None:
        transformers_logging = SimpleNamespace(
            is_progress_bar_enabled=Mock(return_value=True),
            disable_progress_bar=Mock(),
            enable_progress_bar=Mock(),
        )
        huggingface_utils = SimpleNamespace(
            are_progress_bars_disabled=Mock(return_value=False),
            disable_progress_bars=Mock(),
            enable_progress_bars=Mock(),
        )

        with patch.dict(
            sys.modules,
            {
                "transformers.utils.logging": transformers_logging,
                "huggingface_hub.utils": huggingface_utils,
            },
        ):
            with suppress_model_progress_bars():
                transformers_logging.disable_progress_bar.assert_called_once_with()
                huggingface_utils.disable_progress_bars.assert_called_once_with()
                transformers_logging.enable_progress_bar.assert_not_called()
                huggingface_utils.enable_progress_bars.assert_not_called()

        transformers_logging.enable_progress_bar.assert_called_once_with()
        huggingface_utils.enable_progress_bars.assert_called_once_with()

    def test_suppression_preserves_an_already_disabled_state(self) -> None:
        transformers_logging = SimpleNamespace(
            is_progress_bar_enabled=Mock(return_value=False),
            disable_progress_bar=Mock(),
            enable_progress_bar=Mock(),
        )
        huggingface_utils = SimpleNamespace(
            are_progress_bars_disabled=Mock(return_value=True),
            disable_progress_bars=Mock(),
            enable_progress_bars=Mock(),
        )

        with patch.dict(
            sys.modules,
            {
                "transformers.utils.logging": transformers_logging,
                "huggingface_hub.utils": huggingface_utils,
            },
        ):
            with suppress_model_progress_bars():
                pass

        transformers_logging.enable_progress_bar.assert_not_called()
        huggingface_utils.enable_progress_bars.assert_not_called()


if __name__ == "__main__":
    unittest.main()
