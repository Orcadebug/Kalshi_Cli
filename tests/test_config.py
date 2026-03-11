import tempfile
import textwrap
import unittest
from pathlib import Path

from kalshi_cli.config import load_config, write_default_config


class ConfigTests(unittest.TestCase):
    def test_load_config_prefers_env_over_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.toml"
            config_path.write_text(
                textwrap.dedent(
                    """
                    environment = "production"
                    api_key_id = "file-key"
                    private_key_path = "/file/key.pem"
                    output = "table"
                    """
                ).strip()
                + "\n",
                encoding="utf-8",
            )

            config = load_config(
                config_path,
                env={
                    "KALSHI_ENV": "demo",
                    "KALSHI_API_KEY_ID": "env-key",
                    "KALSHI_PRIVATE_KEY_PATH": "/env/key.pem",
                    "KALSHI_OUTPUT": "json",
                },
            )

            self.assertEqual(config.environment, "demo")
            self.assertEqual(config.api_key_id, "env-key")
            self.assertEqual(config.private_key_path, "/env/key.pem")
            self.assertEqual(config.output, "json")

    def test_load_config_defaults_to_production(self) -> None:
        config = load_config(None, env={})
        self.assertEqual(config.environment, "production")
        self.assertEqual(config.base_url, "https://api.elections.kalshi.com")
        self.assertEqual(config.output, "table")

    def test_write_default_config_creates_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "nested" / "config.toml"
            write_default_config(config_path, overwrite=False)
            written = config_path.read_text(encoding="utf-8")

            self.assertIn('environment = "production"', written)
            self.assertIn('api_key_id = ""', written)
            self.assertIn('private_key_path = ""', written)
