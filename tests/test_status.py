import subprocess
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()
