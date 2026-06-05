import unittest

from catalog import ColumnStats, StatsCatalog, TableStats


class StatsCatalogTest(unittest.TestCase):
    def test_register_and_lookup(self) -> None:
        catalog = StatsCatalog()
        stats = TableStats(10, {"age": ColumnStats(distinct_count=3, min_value=10, max_value=20)})
        catalog.register("people", stats)

        self.assertEqual(catalog.get("people"), stats)

