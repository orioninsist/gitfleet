import argparse
import multiprocessing
import os
import signal
import shutil
import subprocess
import sys
from pathlib import Path

from gitfleet.git import inspect_repository, get_repository_status, update_repository, push_repository
from gitfleet.clone import build_clone_plan, execute_clone_plan
from gitfleet.backup import backup, check_backup_tools
from gitfleet.config import load_config
from gitfleet.scanner import discover_direct_directories
from gitfleet.inventory import (
    get_repositories,
    resolve_repository,
    write_markdown,
)


def command_list(_args: argparse.Namespace) -> int:
    config = load_config()
    root = config["paths"]["scan_root"]
    repositories, non_git = discover_direct_directories(root)

    print("SUMMARY")
    print(f"TOTAL DIRECTORIES : {len(repositories) + len(non_git)}")
    print(f"GIT REPOSITORIES  : {len(repositories)}")
    print(f"NON-GIT           : {len(non_git)}")

    if non_git:
        print()
        print("NON-GIT DIRECTORIES")
        for path in non_git:
            print(f"- {path.name}")

    print()
    print("GIT REPOSITORIES")
    for number, path in enumerate(repositories, start=1):
        print(f"{number:>3}. {path.name}")

    print()
    print(f"Total: {len(repositories)}")

    return 0


def command_show(args: argparse.Namespace) -> int:
    path = resolve_repository(args.number)
    info = inspect_repository(path)

    print(f"NUMBER   : {args.number}")
    print(f"NAME     : {info.name}")
    print(f"PATH     : {info.path}")
    print(f"PROVIDER : {info.provider}")
    print(f"BRANCH   : {info.branch or '-'}")
    print(f"UPSTREAM : {info.upstream or '-'}")
    print(f"ORIGIN   : {info.origin or '-'}")

    return 0


def command_report(args: argparse.Namespace) -> int:
    report = write_markdown()

    print(f"Report: {report}")

    if not args.view:
        return 0

    glow = shutil.which("glow")

    if glow is None:
        print(
            "Error: glow bulunamadi. "
            "Arch Linux: sudo pacman -S glow",
            file=sys.stderr,
        )
        return 1

    result = subprocess.run(
        [glow, "-p", str(report)],
        check=False,
    )

    return result.returncode



def _status_worker(path: str, fetch: bool, queue) -> None:
    os.setsid()

    try:
        status = get_repository_status(
            Path(path),
            fetch=fetch,
        )
        queue.put(("OK", status))
    except BaseException as error:
        queue.put(
            (
                "ERROR",
                f"{type(error).__name__}: {error}",
            )
        )


def _isolated_repository_status(
    path: Path,
    *,
    fetch: bool,
    timeout: float = 10.0,
):
    context = multiprocessing.get_context("fork")
    queue = context.Queue()

    process = context.Process(
        target=_status_worker,
        args=(str(path), fetch, queue),
    )
    process.start()
    process.join(timeout)

    if process.is_alive():
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

        process.join()

        queue.close()
        queue.join_thread()
        return None, "TIMEOUT"

    try:
        kind, value = queue.get_nowait()
    except Exception:
        kind = "ERROR"
        value = f"worker exited with code {process.exitcode}"
    finally:
        queue.close()
        queue.join_thread()

    if kind == "OK":
        return value, None

    return None, value


def command_status(args: argparse.Namespace) -> int:
    if args.all:
        repositories = get_repositories()
        attention = []

        counts = {
            "PUSH NEEDED": 0,
            "DIRTY": 0,
            "DIVERGED": 0,
            "NO UPSTREAM": 0,
            "FETCH FAILED": 0,
        }

        total = len(repositories)

        for number, path in enumerate(repositories, start=1):
            print(
                f"\rChecking: {number}/{total}",
                end="",
                flush=True,
            )

            status, worker_error = _isolated_repository_status(
                path,
                fetch=not args.no_fetch,
            )

            if status is None:
                counts["FETCH FAILED"] += 1
                attention.append(
                    (
                        number,
                        path.name,
                        None,
                        [
                            "FETCH TIMEOUT"
                            if worker_error == "TIMEOUT"
                            else "CHECK FAILED"
                        ],
                    )
                )
                continue

            reasons = []

            if status.dirty:
                counts["DIRTY"] += 1
                reasons.append("DIRTY")

            if not status.fetch_ok:
                counts["FETCH FAILED"] += 1
                reasons.append("FETCH FAILED")
            elif status.state == "PUSH NEEDED":
                counts["PUSH NEEDED"] += 1
                reasons.append("PUSH NEEDED")
            elif status.state == "DIVERGED" and status.ahead:
                counts["DIVERGED"] += 1
                reasons.append("DIVERGED")
            elif status.state == "NO UPSTREAM":
                counts["NO UPSTREAM"] += 1
                reasons.append("NO UPSTREAM")

            if reasons:
                attention.append(
                    (
                        number,
                        path.name,
                        status,
                        reasons,
                    )
                )

        print("\r" + (" " * 50) + "\r", end="", flush=True)

        print("LOCAL WORK SUMMARY")
        print(f"TOTAL REPOSITORIES : {len(repositories)}")
        print(f"NEEDS ATTENTION    : {len(attention)}")
        print(f"UNCOMMITTED        : {counts['DIRTY']}")
        print(f"NEEDS PUSH         : {counts['PUSH NEEDED']}")
        print(f"DIVERGED LOCAL     : {counts['DIVERGED']}")
        print(f"NO UPSTREAM        : {counts['NO UPSTREAM']}")
        print(f"FETCH FAILED       : {counts['FETCH FAILED']}")

        if attention:
            print()
            print("NEEDS ATTENTION")

            for number, name, status, reasons in attention:
                details = []

                if status is not None and status.ahead:
                    details.append(f"ahead {status.ahead}")

                suffix = ""
                if details:
                    suffix = f" ({', '.join(details)})"

                print(
                    f"{number:>3}. {name}: "
                    f"{', '.join(reasons)}{suffix}"
                )
        else:
            print()
            print("No uncommitted or unpushed local work found.")

        return 0

    path = resolve_repository(args.number)
    info = inspect_repository(path)

    print(f"Checking #{args.number}: {info.name}")

    status = get_repository_status(
        path,
        fetch=not args.no_fetch,
    )

    print()
    print(f"NUMBER   : {args.number}")
    print(f"PROJECT  : {info.name}")
    print(f"PATH     : {info.path}")
    print(f"BRANCH   : {info.branch or '-'}")
    print(f"UPSTREAM : {info.upstream or '-'}")
    print(f"STATE    : {status.state}")
    print(f"WORKTREE : {'DIRTY' if status.dirty else 'CLEAN'}")
    print(
        f"AHEAD    : "
        f"{status.ahead if status.ahead is not None else '-'}"
    )
    print(
        f"BEHIND   : "
        f"{status.behind if status.behind is not None else '-'}"
    )
    print(f"FETCH    : {'OK' if status.fetch_ok else 'FAILED'}")

    if status.fetch_error:
        print(f"FETCH ERROR: {status.fetch_error}")

    return 0 if status.fetch_ok else 1

def command_update(args: argparse.Namespace) -> int:
    path = resolve_repository(args.number)
    info = inspect_repository(path)

    print(f"Updating #{args.number}: {info.name}")

    result = update_repository(path)

    print()
    print(f"PROJECT : {info.name}")
    print(f"STATE   : {result.state}")
    print(f"CHANGED : {'YES' if result.changed else 'NO'}")
    print(f"MESSAGE : {result.message}")

    if result.state in {
        "UP TO DATE",
        "UPDATED",
        "DIRTY",
        "PUSH NEEDED",
        "DIVERGED",
        "NO UPSTREAM",
    }:
        return 0

    return 1


def command_push(args: argparse.Namespace) -> int:
    path = resolve_repository(args.number)
    info = inspect_repository(path)

    print(f"Pushing #{args.number}: {info.name}")

    result = push_repository(path)

    print()
    print(f"PROJECT : {info.name}")
    print(f"STATE   : {result.state}")
    print(f"PUSHED  : {'YES' if result.pushed else 'NO'}")
    print(f"MESSAGE : {result.message}")

    if result.state in {
        "UP TO DATE",
        "PUSHED",
        "UPDATE AVAILABLE",
        "DIVERGED",
        "NO UPSTREAM",
    }:
        return 0

    return 1


def command_clone(args: argparse.Namespace) -> int:
    plan = build_clone_plan()

    counts = {
        "CLONE": 0,
        "SKIP": 0,
        "CONFLICT": 0,
        "NO ORIGIN": 0,
    }

    for item in plan:
        counts[item.state] += 1

        if item.state != "SKIP":
            print(
                f"{item.state:<9} "
                f"{item.name} -> {item.target}"
            )

    print()
    print(f"TOTAL    : {len(plan)}")
    print(f"CLONE    : {counts['CLONE']}")
    print(f"SKIP     : {counts['SKIP']}")
    print(f"CONFLICT : {counts['CONFLICT']}")
    print(f"NO ORIGIN: {counts['NO ORIGIN']}")

    if args.dry_run:
        print()
        print("DRY RUN: hicbir repository clone edilmedi.")
        return 0

    print()
    print(f"Cloning with {args.workers} worker(s)...")
    print()

    results = execute_clone_plan(
        plan,
        workers=args.workers,
    )

    cloned = 0
    failed = 0

    for result in results:
        if result.state == "CLONED":
            cloned += 1
            print(
                f"CLONED    "
                f"{result.name} -> {result.target}"
            )

        elif result.state == "FAILED":
            failed += 1
            print(
                f"FAILED    "
                f"{result.name}: {result.message}"
            )

    print()
    print(f"CLONED   : {cloned}")
    print(f"FAILED   : {failed}")

    return 1 if failed else 0



def command_backup(args: argparse.Namespace) -> int:
    config = load_config()

    source = config["paths"]["scan_root"]
    remote = config["backup"]["remote"]
    backup_format = config["backup"].get("format", "tar.zst")

    print(f"SOURCE : {source}")
    print(f"REMOTE : {remote}")
    print(f"FORMAT : {backup_format}")

    if backup_format != "tar.zst":
        print(
            f"Error: desteklenmeyen backup format: {backup_format}",
            file=sys.stderr,
        )
        return 1

    missing = check_backup_tools()

    if missing:
        print(
            "Error: eksik araclar: " + ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print()
        print("DRY RUN: archive ve upload yapilmadi.")
        return 0

    print()
    print("Backup baslatiliyor...")

    result = backup(
        source,
        remote,
        upload=True,
    )

    print()
    print(f"SUCCESS : {'YES' if result.success else 'NO'}")
    print(f"ARCHIVE : {result.archive or '-'}")
    print(f"REMOTE  : {result.remote_target or '-'}")
    print(f"MESSAGE : {result.message}")

    return 0 if result.success else 1

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitfleet",
        description="Fast Git project manager.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    list_parser = subparsers.add_parser(
        "list",
        help="List projects with current inventory numbers.",
    )
    list_parser.set_defaults(func=command_list)

    show_parser = subparsers.add_parser(
        "show",
        help="Show one project's Git metadata.",
    )
    show_parser.add_argument(
        "number",
        type=int,
        help="Project number.",
    )
    show_parser.set_defaults(func=command_show)

    clone_parser = subparsers.add_parser(
        "clone",
        help="Restore missing repositories from the manifest.",
    )
    clone_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the clone plan without changing anything.",
    )
    clone_parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Maximum parallel clones (default: 4).",
    )
    clone_parser.set_defaults(func=command_clone)

    backup_parser = subparsers.add_parser(
        "backup",
        help="Archive projects and upload the backup.",
    )
    backup_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate backup configuration without creating or uploading.",
    )
    backup_parser.set_defaults(func=command_backup)

    push_parser = subparsers.add_parser(
        "push",
        help="Safely push committed local changes.",
    )
    push_parser.add_argument(
        "number",
        type=int,
        help="Project number.",
    )
    push_parser.set_defaults(func=command_push)

    update_parser = subparsers.add_parser(
        "update",
        help="Safely fast-forward one project.",
    )
    update_parser.add_argument(
        "number",
        type=int,
        help="Project number.",
    )
    update_parser.set_defaults(func=command_update)

    status_parser = subparsers.add_parser(
        "status",
        help="Check one project's local and remote status.",
    )
    status_target = status_parser.add_mutually_exclusive_group(
        required=True,
    )
    status_target.add_argument(
        "number",
        type=int,
        nargs="?",
        help="Project number.",
    )
    status_target.add_argument(
        "--all",
        action="store_true",
        help="Check all projects and report repositories needing attention.",
    )
    status_parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="Use cached remote refs without network access.",
    )
    status_parser.set_defaults(func=command_status)

    report_parser = subparsers.add_parser(
        "report",
        help="Generate Markdown project report.",
    )
    report_parser.add_argument(
        "--view",
        action="store_true",
        help="Render the generated report with glow.",
    )
    report_parser.set_defaults(func=command_report)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
