from pathlib import Path

from gitfleet.config import load_config
from gitfleet.git import inspect_repository
from gitfleet.scanner import discover_direct_repositories


def get_repositories() -> list[Path]:
    config = load_config()
    root = Path(config["paths"]["scan_root"])

    return discover_direct_repositories(root)


def resolve_repository(number: int) -> Path:
    repositories = get_repositories()

    if number < 1 or number > len(repositories):
        raise ValueError(
            f"Gecersiz proje numarasi: {number}. "
            f"Aralik: 1-{len(repositories)}"
        )

    return repositories[number - 1]


def build_markdown() -> str:
    config = load_config()
    root = Path(config["paths"]["scan_root"])
    repositories = discover_direct_repositories(root)

    lines = [
        "# Gitfleet Projects",
        "",
        f"- Scan root: `{root}`",
        f"- Repository count: **{len(repositories)}**",
        "",
        "| # | Project | Provider | Branch | Upstream | Origin |",
        "|---:|---|---|---|---|---|",
    ]

    for number, path in enumerate(repositories, start=1):
        info = inspect_repository(path)

        lines.append(
            "| "
            f"{number} | "
            f"`{info.name}` | "
            f"{info.provider} | "
            f"`{info.branch or '-'}` | "
            f"`{info.upstream or '-'}` | "
            f"`{info.origin or '-'}` |"
        )

    lines.append("")

    return "\n".join(lines)


def write_markdown() -> Path:
    # Keep the recovery/clone manifest synchronized with the report.
    from gitfleet.clone import build_manifest

    build_manifest()

    config = load_config()
    report = Path(config["paths"]["report"])

    if not report.is_absolute():
        report = Path(__file__).resolve().parent.parent / report

    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(build_markdown(), encoding="utf-8")

    return report
