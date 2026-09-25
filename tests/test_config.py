import tempfile
import unittest
from pathlib import Path

from gitfleet.config import load_config


class ConfigTests(unittest.TestCase):
    def test_real_config_loads(self):
        config = load_config()

        self.assertEqual(
            config["paths"]["scan_root"],
            "/mnt/.data/local/projects",
        )

    def test_missing_config_fails(self):
        with self.assertRaises(FileNotFoundError):
            load_config(Path("/definitely/not/existing/config.toml"))

    def test_missing_scan_root_key_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "config.toml"
            config_file.write_text("[paths]\n", encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(config_file)


if __name__ == "__main__":
    unittest.main()
