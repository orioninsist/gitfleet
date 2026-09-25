from dataclasses import dataclass
from pathlib import Path
import json

from gitfleet.config import load_config
from gitfleet.git import inspect_repository
from gitfleet.scanner import discover_direct_repositories


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = PROJECT_ROOT / "reports" / "repositories.json"


@dataclass(frozen=True)
class CloneItem:
    name: str
    origin: str
    target: Path
    state: str


def build_manifest() -> Path:
    config = load_config()
    scan_root = Path(config["paths"]["scan_root"]).expanduser().resolve()

    repositories = discover_direct_repositories(scan_root)

    items = []

    for path in repositories:
        info = inspect_repository(path)

        items.append(
            {
                "name": info.name,
                "origin": info.origin,
            }
        )

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)

    MANIFEST_PATH.write_text(
        json.dumps(
            {
                "version": 1,
                "repositories": items,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return MANIFEST_PATH


def load_manifest() -> list[dict]:
    if not MANIFEST_PATH.is_file():
        raise FileNotFoundError(
            "Repository manifest bulunamadi. "
            "Once `gitfleet report` calistir."
        )

    data = json.loads(
        MANIFEST_PATH.read_text(encoding="utf-8")
    )

    repositories = data.get("repositories")

    if not isinstance(repositories, list):
        raise ValueError("Repository manifest gecersiz.")

    return repositories


def build_clone_plan() -> list[CloneItem]:
    config = load_config()

    clone_root = Path(
        config["paths"]["clone_root"]
    ).expanduser().resolve()

    clone_root.mkdir(parents=True, exist_ok=True)

    plan = []

    for item in load_manifest():
        name = item.get("name")
        origin = item.get("origin")

        if not name:
            continue

        target = clone_root / name

        if target.exists():
            git_marker = target / ".git"

            if git_marker.is_dir() or git_marker.is_file():
                state = "SKIP"
            else:
                state = "CONFLICT"

        elif not origin:
            state = "NO ORIGIN"

        else:
            state = "CLONE"

        plan.append(
            CloneItem(
                name=name,
                origin=origin or "",
                target=target,
                state=state,
            )
        )

    return plan


@dataclass(frozen=True)
class CloneResult:
    name: str
    target: Path
    state: str
    message: str


def clone_repository(item: CloneItem) -> CloneResult:
    import subprocess

    if item.state != "CLONE":
        return CloneResult(
            name=item.name,
            target=item.target,
            state=item.state,
            message="Clone gerekmedi.",
        )

    try:
        result = subprocess.run(
            [
                "git",
                "clone",
                "--quiet",
                item.origin,
                str(item.target),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as error:
        return CloneResult(
            name=item.name,
            target=item.target,
            state="FAILED",
            message=str(error),
        )

    if result.returncode == 0:
        return CloneResult(
            name=item.name,
            target=item.target,
            state="CLONED",
            message="Clone tamamlandi.",
        )

    message = result.stderr.strip() or result.stdout.strip()

    return CloneResult(
        name=item.name,
        target=item.target,
        state="FAILED",
        message=message or "git clone basarisiz.",
    )


def execute_clone_plan(
    plan: list[CloneItem],
    workers: int = 4,
) -> list[CloneResult]:
    from concurrent.futures import ThreadPoolExecutor

    if workers < 1:
        raise ValueError("workers en az 1 olmali.")

    results = [
        CloneResult(
            name=item.name,
            target=item.target,
            state=item.state,
            message="Clone gerekmedi.",
        )
        for item in plan
        if item.state != "CLONE"
    ]

    clone_items = [
        item for item in plan
        if item.state == "CLONE"
    ]

    if clone_items:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            results.extend(
                executor.map(clone_repository, clone_items)
            )

    return sorted(
        results,
        key=lambda result: result.name.casefold(),
    )
