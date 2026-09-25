from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PROJECT_ROOT / "config.toml"


def load_config(path: Path = DEFAULT_CONFIG) -> dict:
    path = Path(path)

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
