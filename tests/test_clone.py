import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.clone import build_clone_plan


class CloneTests(unittest.TestCase):
    def test_existing_git_repository_is_skipped(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "alpha"
            (target / ".git").mkdir(parents=True)

            manifest = [
                {
                    "name": "alpha",
                    "origin": "https://example.com/alpha.git",
                }
            ]

            config = {
                "paths": {
                    "clone_root": str(root),
                }
            }

            with (
                patch(
                    "gitfleet.clone.load_config",
                    return_value=config,
                ),
                patch(
                    "gitfleet.clone.load_manifest",
                    return_value=manifest,
                ),
            ):
                plan = build_clone_plan()

            self.assertEqual(plan[0].state, "SKIP")

    def test_missing_repository_is_clone(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            manifest = [
                {
                    "name": "alpha",
                    "origin": "https://example.com/alpha.git",
                }
            ]

            config = {
                "paths": {
                    "clone_root": str(root),
                }
            }

            with (
                patch(
                    "gitfleet.clone.load_config",
                    return_value=config,
                ),
                patch(
                    "gitfleet.clone.load_manifest",
                    return_value=manifest,
                ),
            ):
                plan = build_clone_plan()

            self.assertEqual(plan[0].state, "CLONE")

    def test_existing_non_git_directory_is_conflict(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alpha").mkdir()

            manifest = [
                {
                    "name": "alpha",
                    "origin": "https://example.com/alpha.git",
                }
            ]

            config = {
                "paths": {
                    "clone_root": str(root),
                }
            }

            with (
                patch(
                    "gitfleet.clone.load_config",
                    return_value=config,
                ),
                patch(
                    "gitfleet.clone.load_manifest",
                    return_value=manifest,
                ),
            ):
                plan = build_clone_plan()

            self.assertEqual(plan[0].state, "CONFLICT")

    def test_missing_origin_is_not_cloned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            manifest = [
                {
                    "name": "alpha",
                    "origin": None,
                }
            ]

            config = {
                "paths": {
                    "clone_root": str(root),
                }
            }

            with (
                patch(
                    "gitfleet.clone.load_config",
                    return_value=config,
                ),
                patch(
                    "gitfleet.clone.load_manifest",
                    return_value=manifest,
                ),
            ):
                plan = build_clone_plan()

            self.assertEqual(plan[0].state, "NO ORIGIN")


if __name__ == "__main__":
    unittest.main()


class CloneEngineTests(unittest.TestCase):
    def test_real_local_clone(self):
        import subprocess

        from gitfleet.clone import CloneItem, clone_repository

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            remote = root / "remote.git"
            target = root / "target"

            subprocess.run(
                ["git", "init", "-q", "-b", "main", str(source)],
                check=True,
            )

            (source / "README.md").write_text(
                "gitfleet\n",
                encoding="utf-8",
            )

            subprocess.run(
                ["git", "-C", str(source), "add", "README.md"],
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "-C",
                    str(source),
                    "-c",
                    "user.name=Gitfleet Test",
                    "-c",
                    "user.email=gitfleet@test.local",
                    "commit",
                    "-q",
                    "-m",
                    "Initial",
                ],
                check=True,
            )

            subprocess.run(
                ["git", "clone", "-q", "--bare", str(source), str(remote)],
                check=True,
            )

            item = CloneItem(
                name="target",
                origin=str(remote),
                target=target,
                state="CLONE",
            )

            result = clone_repository(item)

            self.assertEqual(result.state, "CLONED")
            self.assertTrue((target / ".git").is_dir())
            self.assertTrue((target / "README.md").is_file())

    def test_non_clone_item_is_not_modified(self):
        from gitfleet.clone import CloneItem, clone_repository

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "existing"

            item = CloneItem(
                name="existing",
                origin="unused",
                target=target,
                state="SKIP",
            )

            result = clone_repository(item)

            self.assertEqual(result.state, "SKIP")
            self.assertFalse(target.exists())

    def test_failed_clone_does_not_raise(self):
        from gitfleet.clone import CloneItem, clone_repository

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "target"

            item = CloneItem(
                name="broken",
                origin=str(Path(directory) / "does-not-exist.git"),
                target=target,
                state="CLONE",
            )

            result = clone_repository(item)

            self.assertEqual(result.state, "FAILED")

    def test_parallel_plan_keeps_other_states(self):
        from gitfleet.clone import CloneItem, execute_clone_plan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            plan = [
                CloneItem(
                    name="skip",
                    origin="",
                    target=root / "skip",
                    state="SKIP",
                ),
                CloneItem(
                    name="conflict",
                    origin="",
                    target=root / "conflict",
                    state="CONFLICT",
                ),
                CloneItem(
                    name="no-origin",
                    origin="",
                    target=root / "no-origin",
                    state="NO ORIGIN",
                ),
            ]

            results = execute_clone_plan(plan, workers=2)

            states = {
                result.name: result.state
                for result in results
            }

            self.assertEqual(states["skip"], "SKIP")
            self.assertEqual(states["conflict"], "CONFLICT")
            self.assertEqual(states["no-origin"], "NO ORIGIN")
