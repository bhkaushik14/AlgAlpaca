import unittest

from codellama_algebra.model import (
    ADAPTER_REPO_ID,
    BASE_MODEL_REVISION,
    ModelLoadConfig,
)


class ModelConfigTests(unittest.TestCase):
    def test_base_only_configuration_is_explicit_and_valid(self):
        config = ModelLoadConfig()
        self.assertIsNone(config.adapter_id_or_path)
        self.assertEqual(config.base_model_revision, BASE_MODEL_REVISION)

    def test_placeholder_adapter_is_rejected(self):
        with self.assertRaises(ValueError):
            ModelLoadConfig(adapter_id_or_path=ADAPTER_REPO_ID)

    def test_revision_must_be_explicit(self):
        with self.assertRaises(ValueError):
            ModelLoadConfig(base_model_revision="")


if __name__ == "__main__":
    unittest.main()
