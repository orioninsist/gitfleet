from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import tempfile


@dataclass(frozen=True)
class BackupResult:
    success: bool
    archive: Path | None
    remote_target: str | None
    message: str


def check_backup_tools() -> list[str]:
    missing = []

    for command in ("tar", "zstd", "rclone"):
        if shutil.which(command) is None:
            missing.append(command)

    return missing


def create_archive(
    source_root: Path,
    output: Path,
) -> Path:
    source_root = Path(source_root).expanduser().resolve()
    output = Path(output).expanduser().resolve()

    if not source_root.is_dir():
        raise ValueError(
            f"Backup source bulunamadi: {source_root}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)

    command = [
        "tar",
        "--zstd",
        "-cf",
        str(output),
        "-C",
        str(source_root.parent),
        source_root.name,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        output.unlink(missing_ok=True)

        message = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            message or "tar.zst olusturulamadi."
        )

    return output


def verify_archive(archive: Path) -> bool:
    result = subprocess.run(
        [
            "tar",
            "--zstd",
            "-tf",
            str(archive),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    return result.returncode == 0


def upload_archive(
    archive: Path,
    remote_root: str,
) -> BackupResult:
    remote_root = remote_root.rstrip("/")
    remote_target = f"{remote_root}/{archive.name}"

    result = subprocess.run(
        [
            "rclone",
            "copyto",
            str(archive),
            remote_target,
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip()

        return BackupResult(
            success=False,
            archive=archive,
            remote_target=remote_target,
            message=message or "Upload basarisiz.",
        )

    return BackupResult(
        success=True,
        archive=archive,
        remote_target=remote_target,
        message="Backup upload tamamlandi.",
    )


def backup(
    source_root: Path,
    remote_root: str,
    *,
    upload: bool = True,
) -> BackupResult:
    missing = check_backup_tools()

    if missing:
        return BackupResult(
            success=False,
            archive=None,
            remote_target=None,
            message=(
                "Eksik araclar: "
                + ", ".join(missing)
            ),
        )

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    temp_root = Path(
        tempfile.mkdtemp(prefix="gitfleet-backup-")
    )

    archive = temp_root / (
        f"projects-{timestamp}.tar.zst"
    )

    try:
        create_archive(source_root, archive)

        if not verify_archive(archive):
            return BackupResult(
                success=False,
                archive=archive,
                remote_target=None,
                message="Archive verification failed.",
            )

        if not upload:
            return BackupResult(
                success=True,
                archive=archive,
                remote_target=None,
                message="Local backup test tamamlandi.",
            )

        return upload_archive(
            archive,
            remote_root,
        )

    except (OSError, RuntimeError, ValueError) as error:
        return BackupResult(
            success=False,
            archive=(
                archive
                if archive.exists()
                else None
            ),
            remote_target=None,
            message=str(error),
        )
