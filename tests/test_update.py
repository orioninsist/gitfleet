import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.git import (
    RepositoryStatus,
    update_repository,
)


class UpdateTests(unittest.TestCase):
    def test_up_to_date_does_nothing(self):
        status = RepositoryStatus(
            dirty=False,
            ahead=0,
            behind=0,
            state="UP TO DATE",
            fetch_ok=True,
            fetch_error=None,
        )

        with patch(
            "gitfleet.git.get_repository_status",
            return_value=status,
        ):
            result = update_repository(Path("/tmp/repo"))

        self.assertFalse(result.changed)
        self.assertEqual(result.state, "UP TO DATE")

    def test_dirty_repository_is_protected(self):
        status = RepositoryStatus(
            dirty=True,
            ahead=0,
            behind=1,
            state="UPDATE AVAILABLE",
            fetch_ok=True,
            fetch_error=None,
        )

        with patch(
            "gitfleet.git.get_repository_status",
            return_value=status,
        ):
            result = update_repository(Path("/tmp/repo"))

        self.assertFalse(result.changed)
        self.assertEqual(result.state, "DIRTY")

    def test_diverged_repository_is_protected(self):
        status = RepositoryStatus(
            dirty=False,
            ahead=2,
            behind=3,
            state="DIVERGED",
            fetch_ok=True,
            fetch_error=None,
        )

        with patch(
            "gitfleet.git.get_repository_status",
            return_value=status,
        ):
            result = update_repository(Path("/tmp/repo"))

        self.assertFalse(result.changed)
        self.assertEqual(result.state, "DIVERGED")


if __name__ == "__main__":
    unittest.main()
