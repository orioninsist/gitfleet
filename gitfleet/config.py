import os
from pathlib import Path
import tomllib


def default_config_path() -> Path:
    config_home = Path(
        os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    ).expanduser()

    return config_home / "gitfleet" / "config.toml"


def load_config(path: Path | None = None) -> dict:
    path = default_config_path() if path is None else Path(path).expanduser()

    if not path.is_file():
        raise FileNotFoundError(f"Config bulunamadi: {path}")

    with path.open("rb") as file:
        config = tomllib.load(file)

    if "paths" not in config:
        raise ValueError("Config icinde [paths] bolumu yok")

    if "scan_root" not in config["paths"]:
        raise ValueError("Config icinde paths.scan_root yok")

    scan_root = Path(config["paths"]["scan_root"]).expanduser()

    if not scan_root.is_dir():
        raise ValueError(f"scan_root dizini bulunamadi: {scan_root}")

    return config
