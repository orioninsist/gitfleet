import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.git import (
    RepositoryStatus,
    push_repository,
)


class PushTests(unittest.TestCase):
    def test_up_to_date_does_not_push(self):
        status = RepositoryStatus(
            dirty=False,
            ahead=0,
            behind=0,
            state="UP TO DATE",
            fetch_ok=True,
            fetch_error=None,
        )

        with (
            patch(
                "gitfleet.git.get_repository_status",
                return_value=status,
            ),
            patch("gitfleet.git.subprocess.run") as run,
        ):
            result = push_repository(Path("/tmp/repo"))

        self.assertFalse(result.pushed)
        self.assertEqual(result.state, "UP TO DATE")
        run.assert_not_called()

    def test_remote_ahead_is_protected(self):
        status = RepositoryStatus(
            dirty=False,
            ahead=0,
            behind=2,
            state="UPDATE AVAILABLE",
            fetch_ok=True,
            fetch_error=None,
        )

        with patch(
            "gitfleet.git.get_repository_status",
            return_value=status,
        ):
            result = push_repository(Path("/tmp/repo"))

        self.assertFalse(result.pushed)
        self.assertEqual(result.state, "UPDATE AVAILABLE")

    def test_diverged_is_protected(self):
        status = RepositoryStatus(
            dirty=False,
            ahead=1,
            behind=1,
            state="DIVERGED",
            fetch_ok=True,
            fetch_error=None,
        )

        with patch(
            "gitfleet.git.get_repository_status",
            return_value=status,
        ):
            result = push_repository(Path("/tmp/repo"))

        self.assertFalse(result.pushed)
        self.assertEqual(result.state, "DIVERGED")


if __name__ == "__main__":
    unittest.main()
