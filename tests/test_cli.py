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
        non_git = [
            Path("/tmp/.hidden-data"),
            Path("/tmp/notes"),
        ]

        output = io.StringIO()

        with (
            patch(
                "gitfleet.cli.load_config",
                return_value={"paths": {"scan_root": "/tmp"}},
            ),
            patch(
                "gitfleet.cli.discover_direct_directories",
                return_value=(repositories, non_git),
            ),
            patch("sys.argv", ["gitfleet", "list"]),
            redirect_stdout(output),
        ):
            result = main()

        value = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("TOTAL DIRECTORIES : 4", value)
        self.assertIn("GIT REPOSITORIES  : 2", value)
        self.assertIn("NON-GIT           : 2", value)
        self.assertIn("- .hidden-data", value)
        self.assertIn("- notes", value)
        self.assertIn("1. alpha", value)
        self.assertIn("2. beta", value)
        self.assertIn("Total: 2", value)

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


    def test_status_all_focuses_on_local_work(self):
        from gitfleet.git import RepositoryStatus

        repositories = [
            Path("/tmp/dirty"),
            Path("/tmp/push"),
            Path("/tmp/diverged"),
            Path("/tmp/behind-only"),
            Path("/tmp/no-upstream"),
            Path("/tmp/fetch-failed"),
            Path("/tmp/clean"),
        ]

        statuses = {
            "dirty": RepositoryStatus(
                dirty=True,
                ahead=0,
                behind=3,
                state="UPDATE AVAILABLE",
                fetch_ok=True,
                fetch_error=None,
            ),
            "push": RepositoryStatus(
                dirty=False,
                ahead=2,
                behind=0,
                state="PUSH NEEDED",
                fetch_ok=True,
                fetch_error=None,
            ),
            "diverged": RepositoryStatus(
                dirty=False,
                ahead=1,
                behind=4,
                state="DIVERGED",
                fetch_ok=True,
                fetch_error=None,
            ),
            "behind-only": RepositoryStatus(
                dirty=False,
                ahead=0,
                behind=5,
                state="UPDATE AVAILABLE",
                fetch_ok=True,
                fetch_error=None,
            ),
            "no-upstream": RepositoryStatus(
                dirty=False,
                ahead=None,
                behind=None,
                state="NO UPSTREAM",
                fetch_ok=True,
                fetch_error=None,
            ),
            "fetch-failed": RepositoryStatus(
                dirty=False,
                ahead=0,
                behind=0,
                state="UP TO DATE",
                fetch_ok=False,
                fetch_error="timeout",
            ),
            "clean": RepositoryStatus(
                dirty=False,
                ahead=0,
                behind=0,
                state="UP TO DATE",
                fetch_ok=True,
                fetch_error=None,
            ),
        }

        def fake_status(repo, *, fetch=True):
            return statuses[repo.name], None

        output = io.StringIO()

        with (
            patch(
                "gitfleet.cli.get_repositories",
                return_value=repositories,
            ),
            patch(
                "gitfleet.cli._isolated_repository_status",
                side_effect=fake_status,
            ),
            patch(
                "sys.argv",
                ["gitfleet", "status", "--all"],
            ),
            redirect_stdout(output),
        ):
            result = main()

        value = output.getvalue()

        self.assertEqual(result, 0)
        self.assertIn("TOTAL REPOSITORIES : 7", value)
        self.assertIn("NEEDS ATTENTION    : 5", value)
        self.assertIn("UNCOMMITTED        : 1", value)
        self.assertIn("NEEDS PUSH         : 1", value)
        self.assertIn("DIVERGED LOCAL     : 1", value)
        self.assertIn("NO UPSTREAM        : 1", value)
        self.assertIn("FETCH FAILED       : 1", value)

        self.assertIn("dirty: DIRTY", value)
        self.assertNotIn("behind 3", value)

        self.assertIn("push: PUSH NEEDED (ahead 2)", value)
        self.assertIn("diverged: DIVERGED (ahead 1)", value)
        self.assertIn("no-upstream: NO UPSTREAM", value)
        self.assertIn("fetch-failed: FETCH FAILED", value)

        self.assertNotIn("behind-only:", value)
        self.assertNotIn("clean:", value)


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
