from pathlib import Path


def is_git_repository(path: Path) -> bool:
    """Check only the repository marker; never scan repository contents."""
    git_marker = path / ".git"

    try:
        return path.is_dir() and (
            git_marker.is_dir() or git_marker.is_file()
        )
    except OSError:
        return False


def discover_direct_repositories(root: Path) -> list[Path]:
    """
    Discover repositories that are direct children of root.

    Complexity depends on the number of root entries, not on the number
    of files contained inside projects.
    """
    root = Path(root).expanduser().resolve()

    if not root.is_dir():
        raise ValueError(f"Tarama dizini bulunamadi: {root}")

    repositories: list[Path] = []

    try:
        entries = root.iterdir()

        for entry in entries:
            if entry.is_symlink():
                continue

            if is_git_repository(entry):
                repositories.append(entry.resolve())

    except (PermissionError, OSError) as error:
        raise ValueError(
            f"Tarama dizini okunamadi: {root}: {error}"
        ) from error

    return sorted(
        repositories,
        key=lambda path: path.name.casefold(),
    )
