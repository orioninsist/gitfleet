import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from gitfleet.cli import main


class CliTests(unittest.TestCase):
    def test_list(self):
        repositories = [
            Path("/tmp/alpha"),
            Path("/tmp/beta"),
        ]

        output = io.StringIO()

        with (
            patch(
                "gitfleet.cli.get_repositories",
                return_value=repositories,
            ),
            patch("sys.argv", ["gitfleet", "list"]),
            redirect_stdout(output),
        ):
            result = main()

        self.assertEqual(result, 0)
        self.assertIn("1. alpha", output.getvalue())
        self.assertIn("2. beta", output.getvalue())
        self.assertIn("Total: 2", output.getvalue())

    def test_invalid_show_number(self):
        with (
            patch(
                "gitfleet.cli.resolve_repository",
                side_effect=ValueError("invalid"),
            ),
            patch("sys.argv", ["gitfleet", "show", "999"]),
        ):
            result = main()

        self.assertEqual(result, 2)

    def test_report_without_view_does_not_start_glow(self):
        with (
            patch(
                "gitfleet.cli.write_markdown",
                return_value=Path("/tmp/projects.md"),
            ),
            patch("gitfleet.cli.subprocess.run") as run,
            patch("sys.argv", ["gitfleet", "report"]),
        ):
            result = main()

        self.assertEqual(result, 0)
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class CloneCliTests(unittest.TestCase):
    def test_clone_dry_run_does_not_execute(self):
        from argparse import Namespace
        from io import StringIO
        from unittest.mock import patch

        from gitfleet.cli import command_clone
        from gitfleet.clone import CloneItem

        plan = [
            CloneItem(
                name="alpha",
                origin="/tmp/alpha.git",
                target=Path("/tmp/alpha"),
                state="CLONE",
            )
        ]

        args = Namespace(
            dry_run=True,
            workers=4,
        )

        with (
            patch(
                "gitfleet.cli.build_clone_plan",
                return_value=plan,
            ),
            patch(
                "gitfleet.cli.execute_clone_plan"
            ) as execute,
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_clone(args)

        self.assertEqual(result, 0)
        execute.assert_not_called()

    def test_clone_executes_plan(self):
        from argparse import Namespace
        from io import StringIO
        from unittest.mock import patch

        from gitfleet.cli import command_clone
        from gitfleet.clone import CloneItem, CloneResult

        target = Path("/tmp/alpha")

        plan = [
            CloneItem(
                name="alpha",
                origin="/tmp/alpha.git",
                target=target,
                state="CLONE",
            )
        ]

        results = [
            CloneResult(
                name="alpha",
                target=target,
                state="CLONED",
                message="Clone tamamlandi.",
            )
        ]

        args = Namespace(
            dry_run=False,
            workers=2,
        )

        with (
            patch(
                "gitfleet.cli.build_clone_plan",
                return_value=plan,
            ),
            patch(
                "gitfleet.cli.execute_clone_plan",
                return_value=results,
            ) as execute,
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_clone(args)

        self.assertEqual(result, 0)
        execute.assert_called_once_with(
            plan,
            workers=2,
        )

    def test_clone_failure_returns_nonzero(self):
        from argparse import Namespace
        from io import StringIO
        from unittest.mock import patch

        from gitfleet.cli import command_clone
        from gitfleet.clone import CloneItem, CloneResult

        target = Path("/tmp/broken")

        plan = [
            CloneItem(
                name="broken",
                origin="/tmp/missing.git",
                target=target,
                state="CLONE",
            )
        ]

        results = [
            CloneResult(
                name="broken",
                target=target,
                state="FAILED",
                message="clone failed",
            )
        ]

        args = Namespace(
            dry_run=False,
            workers=4,
        )

        with (
            patch(
                "gitfleet.cli.build_clone_plan",
                return_value=plan,
            ),
            patch(
                "gitfleet.cli.execute_clone_plan",
                return_value=results,
            ),
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_clone(args)

        self.assertEqual(result, 1)


class BackupCliTests(unittest.TestCase):
    def test_backup_dry_run_does_not_execute(self):
        from argparse import Namespace
        from io import StringIO
        from unittest.mock import patch

        from gitfleet.cli import command_backup

        config = {
            "paths": {
                "scan_root": "/tmp/projects",
            },
            "backup": {
                "remote": "gdrive:backups/projects",
                "format": "tar.zst",
            },
        }

        with (
            patch(
                "gitfleet.cli.load_config",
                return_value=config,
            ),
            patch(
                "gitfleet.cli.check_backup_tools",
                return_value=[],
            ),
            patch("gitfleet.cli.backup") as run_backup,
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_backup(
                Namespace(dry_run=True)
            )

        self.assertEqual(result, 0)
        run_backup.assert_not_called()

    def test_backup_success(self):
        from argparse import Namespace
        from io import StringIO
        from pathlib import Path
        from unittest.mock import patch

        from gitfleet.backup import BackupResult
        from gitfleet.cli import command_backup

        config = {
            "paths": {
                "scan_root": "/tmp/projects",
            },
            "backup": {
                "remote": "gdrive:backups/projects",
                "format": "tar.zst",
            },
        }

        backup_result = BackupResult(
            success=True,
            archive=Path("/tmp/projects.tar.zst"),
            remote_target=(
                "gdrive:backups/projects/projects.tar.zst"
            ),
            message="Backup upload tamamlandi.",
        )

        with (
            patch(
                "gitfleet.cli.load_config",
                return_value=config,
            ),
            patch(
                "gitfleet.cli.check_backup_tools",
                return_value=[],
            ),
            patch(
                "gitfleet.cli.backup",
                return_value=backup_result,
            ) as run_backup,
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_backup(
                Namespace(dry_run=False)
            )

        self.assertEqual(result, 0)
        run_backup.assert_called_once_with(
            "/tmp/projects",
            "gdrive:backups/projects",
            upload=True,
        )

    def test_backup_failure_returns_nonzero(self):
        from argparse import Namespace
        from io import StringIO
        from unittest.mock import patch

        from gitfleet.backup import BackupResult
        from gitfleet.cli import command_backup

        config = {
            "paths": {
                "scan_root": "/tmp/projects",
            },
            "backup": {
                "remote": "gdrive:backups/projects",
                "format": "tar.zst",
            },
        }

        backup_result = BackupResult(
            success=False,
            archive=None,
            remote_target=None,
            message="failed",
        )

        with (
            patch(
                "gitfleet.cli.load_config",
                return_value=config,
            ),
            patch(
                "gitfleet.cli.check_backup_tools",
                return_value=[],
            ),
            patch(
                "gitfleet.cli.backup",
                return_value=backup_result,
            ),
            patch("sys.stdout", new_callable=StringIO),
        ):
            result = command_backup(
                Namespace(dry_run=False)
            )

        self.assertEqual(result, 1)
