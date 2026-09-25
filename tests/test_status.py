import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from gitfleet.git import get_repository_status


def git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(path), *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class StatusTests(unittest.TestCase):
    def test_clean_repository_without_upstream(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()

            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Gitfleet Test")
            git(repo, "config", "user.email", "gitfleet@example.invalid")

            (repo / "README.md").write_text(
                "test\n",
                encoding="utf-8",
            )

            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "Initial")

            status = get_repository_status(repo, fetch=False)

            self.assertFalse(status.dirty)
            self.assertIsNone(status.ahead)
            self.assertIsNone(status.behind)
            self.assertEqual(status.state, "NO UPSTREAM")

    def test_dirty_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()

            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Gitfleet Test")
            git(repo, "config", "user.email", "gitfleet@example.invalid")

            (repo / "README.md").write_text(
                "test\n",
                encoding="utf-8",
            )

            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "Initial")

            (repo / "dirty.txt").write_text(
                "dirty\n",
                encoding="utf-8",
            )

            status = get_repository_status(repo, fetch=False)

            self.assertTrue(status.dirty)
            self.assertEqual(status.state, "NO UPSTREAM")


    def test_fetch_timeout_does_not_abort_status(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "repo"
            repo.mkdir()

            git(repo, "init", "-b", "main")
            git(repo, "config", "user.name", "Gitfleet Test")
            git(repo, "config", "user.email", "gitfleet@example.invalid")

            (repo / "README.md").write_text(
                "test\n",
                encoding="utf-8",
            )

            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "Initial")

            process = unittest.mock.MagicMock()
            process.pid = 12345
            process.communicate.side_effect = [
                subprocess.TimeoutExpired(["git", "fetch"], 0.01),
                ("", ""),
            ]

            with (
                patch(
                    "gitfleet.git.subprocess.Popen",
                    return_value=process,
                ),
                patch(
                    "gitfleet.git.os.getpgid",
                    return_value=12345,
                ),
                patch("gitfleet.git.os.killpg") as killpg,
                patch(
                    "gitfleet.git.run_git",
                    side_effect=[
                        None,
                        None,
                    ],
                ),
            ):
                status = get_repository_status(
                    repo,
                    fetch=True,
                    fetch_timeout=0.01,
                )

            killpg.assert_called_once()
            self.assertFalse(status.fetch_ok)
            self.assertEqual(
                status.fetch_error,
                "git fetch timed out after 0.01 seconds",
            )
            self.assertEqual(status.state, "NO UPSTREAM")
            self.assertFalse(status.dirty)


if __name__ == "__main__":
    unittest.main()
