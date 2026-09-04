import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.config import AppConfig, load_config, mask_secret


class ConfigTests(unittest.TestCase):
    def test_load_config_applies_defaults_and_preserves_ca_bundle(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "endpoint_url": "https://onefs.example.com",
                        "access_key": "ACCESS1234567890",
                        "secret_key": "SECRET",
                        "bucket_name": "bucket-a",
                        "verify_ssl": True,
                        "ca_bundle": "certs/company-ca.pem",
                    }
                ),
                encoding="utf-8",
            )

            config = load_config(config_path)

        self.assertIsInstance(config, AppConfig)
        self.assertEqual(config.region_name, "us-east-1")
        self.assertEqual(config.s3_addressing_style, "path")
        self.assertEqual(config.ca_bundle, "certs/company-ca.pem")

    def test_load_config_rejects_missing_required_field(self) -> None:
        with TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "endpoint_url": "https://onefs.example.com",
                        "access_key": "ACCESS",
                        "secret_key": "SECRET",
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "bucket_name"):
                load_config(config_path)

    def test_mask_secret_keeps_edges_only_for_long_values(self) -> None:
        self.assertEqual(mask_secret("ABCD12345678WXYZ"), "ABCD********WXYZ")
        self.assertEqual(mask_secret("short"), "*****")


if __name__ == "__main__":
    unittest.main()
