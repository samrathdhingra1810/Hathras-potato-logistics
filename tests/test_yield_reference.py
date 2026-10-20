import copy
import unittest

from portal.core import dataset as ds
from portal.core import yield_reference as yr


class YieldReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = yr.load()
        cls.report = yr.validate(cls.rows)

    def test_schema_and_coverage(self):
        r = self.report
        self.assertEqual((r["rows"], r["columns"]), (16, 45))
        self.assertEqual(r["coverage"], ("2005-06", "2020-21"))
        self.assertEqual(r["missing_cells"], 0)
        self.assertEqual(list(self.rows[0])[:3], ["season", "time_index", "yield_t_ha"])
        self.assertEqual(len(yr.z_columns(self.rows)), 42)

    def test_seasons_unique_well_formed_and_consecutive(self):
        r = self.report
        self.assertEqual(r["duplicate_seasons"], 0)
        self.assertEqual(r["duplicate_rows"], 0)
        self.assertEqual(r["bad_season_format"], [])
        self.assertEqual(r["season_gaps"], [])
        self.assertTrue(r["time_index_consecutive"])
        self.assertEqual(r["yield_out_of_band"], [])

    def test_validator_flags_injected_problems(self):
        rows = copy.deepcopy(self.rows)
        rows[3]["season"] = "2008-10"
        rows[5]["Z10"] = None
        rows.append(dict(rows[0]))
        r = yr.validate(rows)
        self.assertIn("2008-10", r["bad_season_format"])
        self.assertEqual(r["missing_cells"], 1)
        self.assertEqual(r["duplicate_seasons"], 1)

    def test_identical_source_columns_are_detected(self):
        self.assertEqual(self.report["identical_columns"], [("Z460", "Z560"), ("Z461", "Z561")])

    def test_overlap_is_reported_not_replaced(self):
        before = copy.deepcopy(ds.PRODUCTION_SERIES)
        cmp = yr.compare_with_coldflow(self.rows)
        self.assertEqual([c["season"] for c in cmp], ["2018-19", "2019-20", "2020-21"])
        for c, pct in zip(cmp, (0.114, 0.260, 0.156)):
            self.assertAlmostEqual(c["difference_pct"], pct, delta=0.001)
        self.assertEqual(ds.PRODUCTION_SERIES, before)

    def test_kept_separate_from_production(self):
        cols = set(self.rows[0])
        self.assertFalse(cols & {"area_ha", "production_t"})
        self.assertNotIn("2005-06", {s["season"] for s in ds.PRODUCTION_SERIES})


if __name__ == "__main__":
    unittest.main()
