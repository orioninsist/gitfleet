import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gitfleet.inventory import resolve_repository


class InventoryTests(unittest.TestCase):
    def test_resolve_repository_by_number(self):
        repositories = [
            Path("/tmp/alpha"),
            Path("/tmp/beta"),
            Path("/tmp/gamma"),
        ]

        with patch(
            "gitfleet.inventory.get_repositories",
            return_value=repositories,
        ):
            self.assertEqual(
                resolve_repository(1),
                Path("/tmp/alpha"),
            )

            self.assertEqual(
                resolve_repository(3),
                Path("/tmp/gamma"),
            )

    def test_invalid_repository_number_fails(self):
        repositories = [
            Path("/tmp/alpha"),
            Path("/tmp/beta"),
        ]

        with patch(
            "gitfleet.inventory.get_repositories",
            return_value=repositories,
        ):
            with self.assertRaises(ValueError):
                resolve_repository(0)

            with self.assertRaises(ValueError):
                resolve_repository(3)


if __name__ == "__main__":
    unittest.main()
