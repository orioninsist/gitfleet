import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.config import default_config_path, load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_path_uses_xdg_config_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(
                os.environ,
                {"XDG_CONFIG_HOME": directory},
            ):
                self.assertEqual(
                    default_config_path(),
                    Path(directory) / "gitfleet" / "config.toml",
                )

    def test_default_config_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scan_root = root / "projects"
            scan_root.mkdir()

            config_dir = root / "gitfleet"
            config_dir.mkdir()
            config_file = config_dir / "config.toml"
            config_file.write_text(
                f'[paths]\nscan_root = "{scan_root}"\n',
                encoding="utf-8",
            )

            with patch.dict(
                os.environ,
                {"XDG_CONFIG_HOME": directory},
            ):
                config = load_config()

            self.assertEqual(
                config["paths"]["scan_root"],
                str(scan_root),
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
