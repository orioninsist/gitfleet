import tempfile
import unittest
from pathlib import Path
import subprocess

from gitfleet.git import detect_provider, inspect_repository


class GitTests(unittest.TestCase):
    def test_provider_detection(self):
        cases = {
            "https://github.com/user/repo.git": "GitHub",
            "git@github.com:user/repo.git": "GitHub",
            "https://gitlab.com/user/repo.git": "GitLab",
            "git@gitlab.com:user/repo.git": "GitLab",
            "https://codeberg.org/user/repo.git": "Codeberg",
            "git@codeberg.org:user/repo.git": "Codeberg",
            "https://example.com/user/repo.git": "Other",
            None: "Local",
        }

        for remote, expected in cases.items():
            with self.subTest(remote=remote):
                self.assertEqual(detect_provider(remote), expected)

    def test_repository_inspection(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / "example"
            repo.mkdir()

            subprocess.run(
                ["git", "init", "-b", "main", str(repo)],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo),
                    "remote",
                    "add",
                    "origin",
                    "https://github.com/example/example.git",
                ],
                check=True,
            )

            info = inspect_repository(repo)

            self.assertEqual(info.name, "example")
            self.assertEqual(info.provider, "GitHub")
            self.assertEqual(
                info.origin,
                "https://github.com/example/example.git",
            )
            self.assertEqual(info.branch, "main")
            self.assertIsNone(info.upstream)


if __name__ == "__main__":
    unittest.main()



class RemoteNormalizerTests(unittest.TestCase):
    def test_real_markdown_remote_is_repaired(self):
        from gitfleet.git import normalize_remote

        value = (
            "[https://github.com/orioninsist/aardvark-dns.git]"
            "(https://github.com/orioninsist/aardvark-dns.git)"
        )

        self.assertEqual(
            normalize_remote(value),
            "https://github.com/orioninsist/aardvark-dns.git",
        )

    def test_normal_https_remote_is_unchanged(self):
        from gitfleet.git import normalize_remote

        value = "https://github.com/user/repo.git"

        self.assertEqual(normalize_remote(value), value)

    def test_normal_ssh_remote_is_unchanged(self):
        from gitfleet.git import normalize_remote

        value = "git@codeberg.org:user/repo.git"

        self.assertEqual(normalize_remote(value), value)


if __name__ == "__main__":
    unittest.main()
