"""Tests for secret-free AI configuration behaviour."""

from __future__ import annotations

import unittest

from config.ai_config import AIConfig, ProviderKind


class AIConfigTests(unittest.TestCase):
    def test_default_configuration_does_not_enable_ai(self) -> None:
        self.assertFalse(AIConfig().is_enabled)

    def test_serialized_configuration_excludes_api_key(self) -> None:
        config = AIConfig(
            provider=ProviderKind.OPENAI_COMPATIBLE,
            base_url="https://api.example.com/v1",
            model="example-model",
        )
        self.assertNotIn("api_key", config.to_dict())

    def test_enabled_configuration_requires_a_model_and_url(self) -> None:
        with self.assertRaises(ValueError):
            AIConfig(provider=ProviderKind.OPENAI_COMPATIBLE).validate()


if __name__ == "__main__":
    unittest.main()
