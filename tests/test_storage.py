import unittest

from storage import Batch, Column, Table, from_rows


class StorageTest(unittest.TestCase):
    def test_from_rows_builds_columnar_table(self) -> None:
        table = from_rows(
            "people",
            [
                {"name": "alice", "age": 10},
                {"name": "bob", "age": 12},
            ],
        )

        self.assertEqual(table.name, "people")
        self.assertEqual(table.batch().row_count, 2)
        self.assertEqual(table.batch().column("name").values, ("alice", "bob"))
        self.assertEqual(table.batch().row(1), {"name": "bob", "age": 12})

