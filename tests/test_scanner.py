import tempfile
import unittest
from pathlib import Path

from gitfleet.scanner import (
    discover_direct_repositories,
    is_git_repository,
)


class ScannerTests(unittest.TestCase):
    def test_normal_git_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "project"
            (repo / ".git").mkdir(parents=True)

            self.assertTrue(is_git_repository(repo))

    def test_worktree_git_file(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "worktree"
            repo.mkdir()

            (repo / ".git").write_text(
                "gitdir: /tmp/example\n",
                encoding="utf-8",
            )

            self.assertTrue(is_git_repository(repo))

    def test_direct_repositories_are_found(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            repo_a = root / "alpha"
            repo_b = root / "beta"

            (repo_a / ".git").mkdir(parents=True)
            (repo_b / ".git").mkdir(parents=True)

            self.assertEqual(
                discover_direct_repositories(root),
                [repo_a, repo_b],
            )

    def test_repository_contents_are_not_scanned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            outer = root / "outer"
            nested = outer / "huge" / "nested"

            (outer / ".git").mkdir(parents=True)
            (nested / ".git").mkdir(parents=True)

            self.assertEqual(
                discover_direct_repositories(root),
                [outer],
            )

    def test_hidden_direct_repository_is_found(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            repo = root / ".hidden-project"
            (repo / ".git").mkdir(parents=True)

            self.assertEqual(
                discover_direct_repositories(root),
                [repo],
            )

    def test_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            real = root / "real"
            (real / ".git").mkdir(parents=True)

            link = root / "linked"
            link.symlink_to(real, target_is_directory=True)

            self.assertEqual(
                discover_direct_repositories(root),
                [real],
            )

    def test_missing_root_fails(self):
        with self.assertRaises(ValueError):
            discover_direct_repositories(
                Path("/definitely/not/existing/gitfleet-root")
            )


if __name__ == "__main__":
    unittest.main()
