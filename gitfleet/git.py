from dataclasses import dataclass
from pathlib import Path
import subprocess
from urllib.parse import urlparse


def normalize_remote(remote: str | None) -> str | None:
    if not remote:
        return remote

    value = remote.strip()

    # Normal remotes.
    if value.startswith(
        ("https://", "http://", "ssh://", "git://", "git@")
    ):
        return value

    # Accidental Markdown link:
    # [label](https://host/owner/repo.git)
    marker = "]("

    if marker in value and value.endswith(")"):
        target = value.rsplit(marker, 1)[1][:-1].strip()

        if target.startswith(
            ("https://", "http://", "ssh://", "git://", "git@")
        ):
            return target

    return value


def run_git(path: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(path), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    return result.stdout.strip() or None


def detect_provider(remote: str | None) -> str:
    if not remote:
        return "Local"

    host = ""

    if "://" in remote:
        host = (urlparse(remote).hostname or "").lower()
    elif ":" in remote:
        # SSH form: git@github.com:owner/repo.git
        host = remote.split(":", 1)[0].split("@")[-1].lower()

    providers = {
        "github.com": "GitHub",
        "gitlab.com": "GitLab",
        "codeberg.org": "Codeberg",
    }

    return providers.get(host, "Other")



@dataclass(frozen=True)
class RepositoryInfo:
    name: str
    path: Path
    origin: str | None
    provider: str
    branch: str | None
    upstream: str | None

def inspect_repository(path: Path) -> RepositoryInfo:
    path = Path(path).resolve()

    origin = normalize_remote(
        run_git(path, "remote", "get-url", "origin")
    )
    branch = run_git(path, "branch", "--show-current")
    upstream = run_git(
        path,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )

    return RepositoryInfo(
        name=path.name,
        path=path,
        origin=origin,
        provider=detect_provider(origin),
        branch=branch,
        upstream=upstream,
    )


@dataclass(frozen=True)
class RepositoryStatus:
    dirty: bool
    ahead: int | None
    behind: int | None
    state: str
    fetch_ok: bool
    fetch_error: str | None


def get_repository_status(
    path: Path,
    *,
    fetch: bool = True,
) -> RepositoryStatus:
    path = Path(path).resolve()

    fetch_ok = True
    fetch_error = None

    if fetch:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(path),
                "fetch",
                "--prune",
                "--quiet",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            fetch_ok = False
            fetch_error = result.stderr.strip() or "git fetch failed"

    porcelain = run_git(
        path,
        "status",
        "--porcelain",
        "--untracked-files=normal",
    )
    dirty = bool(porcelain)

    upstream = run_git(
        path,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )

    if upstream is None:
        return RepositoryStatus(
            dirty=dirty,
            ahead=None,
            behind=None,
            state="NO UPSTREAM",
            fetch_ok=fetch_ok,
            fetch_error=fetch_error,
        )

    counts = run_git(
        path,
        "rev-list",
        "--left-right",
        "--count",
        f"HEAD...{upstream}",
    )

    if counts is None:
        return RepositoryStatus(
            dirty=dirty,
            ahead=None,
            behind=None,
            state="UNKNOWN",
            fetch_ok=fetch_ok,
            fetch_error=fetch_error,
        )

    parts = counts.split()

    if len(parts) != 2:
        return RepositoryStatus(
            dirty=dirty,
            ahead=None,
            behind=None,
            state="UNKNOWN",
            fetch_ok=fetch_ok,
            fetch_error=fetch_error,
        )

    ahead = int(parts[0])
    behind = int(parts[1])

    if ahead and behind:
        state = "DIVERGED"
    elif ahead:
        state = "PUSH NEEDED"
    elif behind:
        state = "UPDATE AVAILABLE"
    else:
        state = "UP TO DATE"

    return RepositoryStatus(
        dirty=dirty,
        ahead=ahead,
        behind=behind,
        state=state,
        fetch_ok=fetch_ok,
        fetch_error=fetch_error,
    )


@dataclass(frozen=True)
class UpdateResult:
    changed: bool
    state: str
    message: str


def update_repository(path: Path) -> UpdateResult:
    path = Path(path).resolve()

    status = get_repository_status(path, fetch=True)

    if not status.fetch_ok:
        return UpdateResult(
            changed=False,
            state="FETCH FAILED",
            message=status.fetch_error or "git fetch failed",
        )

    if status.dirty:
        return UpdateResult(
            changed=False,
            state="DIRTY",
            message="Working tree dirty; update skipped.",
        )

    if status.state == "UP TO DATE":
        return UpdateResult(
            changed=False,
            state="UP TO DATE",
            message="Degisiklik yok.",
        )

    if status.state == "PUSH NEEDED":
        return UpdateResult(
            changed=False,
            state="PUSH NEEDED",
            message="Local commits are waiting to be pushed.",
        )

    if status.state == "DIVERGED":
        return UpdateResult(
            changed=False,
            state="DIVERGED",
            message="Local and remote histories diverged; update skipped.",
        )

    if status.state == "NO UPSTREAM":
        return UpdateResult(
            changed=False,
            state="NO UPSTREAM",
            message="Upstream branch is not configured.",
        )

    if status.state != "UPDATE AVAILABLE":
        return UpdateResult(
            changed=False,
            state=status.state,
            message="Repository state is not safe for automatic update.",
        )

    upstream = run_git(
        path,
        "rev-parse",
        "--abbrev-ref",
        "--symbolic-full-name",
        "@{upstream}",
    )

    if upstream is None:
        return UpdateResult(
            changed=False,
            state="NO UPSTREAM",
            message="Upstream branch is not configured.",
        )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "merge",
            "--ff-only",
            upstream,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        return UpdateResult(
            changed=False,
            state="UPDATE FAILED",
            message=message or "Fast-forward update failed.",
        )

    return UpdateResult(
        changed=True,
        state="UPDATED",
        message=result.stdout.strip() or "Repository updated.",
    )


@dataclass(frozen=True)
class PushResult:
    pushed: bool
    state: str
    message: str


def push_repository(path: Path) -> PushResult:
    path = Path(path).resolve()

    status = get_repository_status(path, fetch=True)

    if not status.fetch_ok:
        return PushResult(
            pushed=False,
            state="FETCH FAILED",
            message=status.fetch_error or "git fetch failed",
        )

    if status.state == "UP TO DATE":
        return PushResult(
            pushed=False,
            state="UP TO DATE",
            message="Push edilecek commit yok.",
        )

    if status.state == "UPDATE AVAILABLE":
        return PushResult(
            pushed=False,
            state="UPDATE AVAILABLE",
            message="Remote ileride; push yapilmadi.",
        )

    if status.state == "DIVERGED":
        return PushResult(
            pushed=False,
            state="DIVERGED",
            message="Local ve remote ayrismis; push yapilmadi.",
        )

    if status.state == "NO UPSTREAM":
        return PushResult(
            pushed=False,
            state="NO UPSTREAM",
            message="Upstream branch ayarlanmamis.",
        )

    if status.state != "PUSH NEEDED":
        return PushResult(
            pushed=False,
            state=status.state,
            message="Repository push icin guvenli durumda degil.",
        )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(path),
            "push",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        return PushResult(
            pushed=False,
            state="PUSH FAILED",
            message=message or "git push failed",
        )

    return PushResult(
        pushed=True,
        state="PUSHED",
        message=result.stderr.strip()
        or result.stdout.strip()
        or "Push completed.",
    )
