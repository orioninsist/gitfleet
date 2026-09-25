import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.backup import (
    backup,
    check_backup_tools,
    create_archive,
    verify_archive,
)


@unittest.skipUnless(
    shutil.which("tar") and shutil.which("zstd"),
    "tar/zstd required",
)
class BackupTests(unittest.TestCase):
    def test_archive_contains_normal_and_git_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            git_dir = source / "project" / ".git"

            git_dir.mkdir(parents=True)

            (source / "README.txt").write_text(
                "backup test\n",
                encoding="utf-8",
            )

            (git_dir / "HEAD").write_text(
                "ref: refs/heads/main\n",
                encoding="utf-8",
            )

            archive = root / "backup.tar.zst"

            create_archive(source, archive)

            self.assertTrue(archive.is_file())
            self.assertTrue(verify_archive(archive))

            import subprocess

            listing = subprocess.run(
                [
                    "tar",
                    "--zstd",
                    "-tf",
                    str(archive),
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout

            self.assertIn("source/README.txt", listing)
            self.assertIn(
                "source/project/.git/HEAD",
                listing,
            )

    def test_missing_source_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            with self.assertRaises(ValueError):
                create_archive(
                    root / "missing",
                    root / "backup.tar.zst",
                )

    def test_local_backup_does_not_upload(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source"
            source.mkdir()

            (source / "file.txt").write_text(
                "test\n",
                encoding="utf-8",
            )

            with patch(
                "gitfleet.backup.upload_archive"
            ) as upload:
                result = backup(
                    source,
                    "gdrive:test",
                    upload=False,
                )

            self.assertTrue(result.success)
            self.assertIsNotNone(result.archive)
            upload.assert_not_called()

    def test_tool_check_returns_list(self):
        self.assertIsInstance(
            check_backup_tools(),
            list,
        )


if __name__ == "__main__":
    unittest.main()
