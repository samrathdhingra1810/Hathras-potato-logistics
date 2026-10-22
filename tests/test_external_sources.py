"""UP district production (2022-23) and NHB historical cold storage records."""
import copy
import re
import unittest

from portal import create_app
from portal.core import dataset as ds
from portal.core import external_sources as xs


class DistrictDataTests(unittest.TestCase):
    def test_table_is_complete_and_consistent(self):
        v = xs.validate_districts()
        self.assertEqual((v["rows"], v["unique_districts"], v["duplicates"], v["missing_values"]), (75, 75, 0, 0))
        self.assertEqual(v["crop_years"], ["2022-23"])
        self.assertAlmostEqual(v["total_production_t"] / 1e6, 24.3, delta=0.05)
        self.assertLess(v["max_area_x_yield_gap"], 0.005)

    def test_hathras_values_as_published(self):
        h = xs.district("Hathras")
        self.assertEqual((h["rank"], h["area_ha"], h["production_t"], h["yield_t_ha"]), (4, 50966, 1911218, 37.5))

    def test_discrepancy_reported_not_merged(self):
        before = copy.deepcopy(ds.PRODUCTION_SERIES)
        c = xs.compare_hathras()
        self.assertEqual(c["season"], "2022-23")
        self.assertAlmostEqual(c["difference_pct"]["production"], 0.4147, delta=0.001)
        self.assertEqual(c["coldflow"]["production_t"], 1351000)
        self.assertEqual(ds.PRODUCTION_SERIES, before)                  # ColdFlow's own series untouched


class NhbDataTests(unittest.TestCase):
    def setUp(self):
        self.rows = {r["sr"]: r for r in xs.nhb_projects()}

    def test_rows_rebuilt_completely(self):
        self.assertEqual(sorted(self.rows), list(range(1, 921)))

    def test_known_row_matches_pdf(self):
        r = self.rows[85]                                              # checked against the PDF text
        self.assertEqual((r["name"], r["district"], r["sanctioned_date"], r["capacity_mt_sanctioned"]),
                         ("K R Ice and Cold stoarge", "Hathras", "2002-02-12", 7295.04))

    def test_errors_flagged_not_corrected(self):
        self.assertIn("capacity_implausible", self.rows[357]["flags"])
        self.assertEqual(self.rows[357]["capacity_mt_raw"], "7221093.000")
        self.assertIn("date_unreadable", self.rows[562]["flags"])
        self.assertIn("date_implausible", self.rows[913]["flags"])
        self.assertIsNone(self.rows[913]["sanctioned_year"])
        for sr in (756, 793):
            self.assertIsNone(self.rows[sr]["capacity_mt_sanctioned"])
            self.assertIn("capacity_missing", self.rows[sr]["flags"])

    def test_old_district_name_mapped(self):
        self.assertEqual(self.rows[184]["district_raw"], "Maha Maya Nagar")
        self.assertEqual(self.rows[184]["district"], "Hathras")

    def test_hathras_summary(self):
        h = xs.hathras_facilities()
        self.assertEqual(h["count"], 58)
        self.assertEqual(h["years"], (2000, 2011))
        self.assertEqual(h["by_block"]["sadabad"]["count"], 20)
        self.assertEqual(h["by_block"]["hathras"]["count"], 0)         # "Hathras" in an address is the district name
        self.assertEqual(h["count"], sum(v["count"] for v in h["by_block"].values()) + len(h["unassigned"]))
        self.assertNotIn(357, [r["sr"] for r in h["records"] if r["capacity_mt_sanctioned"] and "capacity_implausible" not in r["flags"]])
        self.assertAlmostEqual(h["capacity_mt_sanctioned"], 328217, delta=1)

    def test_storage_model_unchanged(self):
        self.assertEqual(ds.DEFAULT_REGIONAL_CAPACITY_T, 950_000)


class PageAndApiTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app({"TESTING": True}).test_client()

    def get(self, path):
        r = self.c.get(path)
        self.assertEqual(r.status_code, 200, path)
        return r

    def test_production_page_labels_source(self):
        h = self.get("/tools/production").get_data(as_text=True)
        for s in ("crop year 2022-23", "Secondary source · unverified", "The two sources disagree", "All 75 districts"):
            self.assertIn(s, h)

    def test_map_labels_history_not_live(self):
        h = self.get("/tools/map").get_data(as_text=True)
        for s in ("Historical cold storage projects in Hathras (58 records)", "Historical · not live availability",
                  "Capacity is as sanctioned, not today", "Not identified"):
            self.assertIn(s, h)
        self.assertNotIn("No facility registry is loaded", h)
        self.assertNotRegex(re.sub(r"aria-live|not live", "", h), r"(?i)\blive (availability|capacity|data)\b|real-time")

    def test_apis(self):
        d = self.get("/api/sources/up-districts").get_json()
        self.assertEqual(len(d["rows"]), 75)
        self.assertIn("unverified", d["source"]["status"].lower())
        n = self.get("/api/sources/nhb-cold-storage").get_json()
        self.assertEqual((n["district"], n["count"]), ("Hathras", 58))
        self.assertIn("not current capacity", n["note"])
        self.assertEqual(self.get("/api/sources/nhb-cold-storage?district=all").get_json()["count"], 920)


if __name__ == "__main__":
    unittest.main()
