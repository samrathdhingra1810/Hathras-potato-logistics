import unittest

from portal.core.dataset import BLOCKS, MONTHLY_INTAKE_PROFILE, MONTHLY_RELEASE_PROFILE, PRODUCTION_SERIES
from portal.core.analytics import LinearModel, cagr, forecast_series, next_season, with_yoy
from portal.core.storage import block_strain, facility_coverage, simulate_storage_year, storage_demand, strain_level


class DatasetTests(unittest.TestCase):
    def test_yield_matches_production_over_area(self):
        for r in PRODUCTION_SERIES:
            self.assertLess(abs(r["production_t"] * 1000 / r["area_ha"] - r["yield_kg_ha"]), 1, r["season"])

    def test_profiles_and_shares_sum_to_one(self):
        self.assertAlmostEqual(sum(MONTHLY_INTAKE_PROFILE.values()), 1)
        self.assertAlmostEqual(sum(MONTHLY_RELEASE_PROFILE.values()), 1)
        self.assertAlmostEqual(sum(b["production_share"] for b in BLOCKS), 1)
        self.assertAlmostEqual(sum(b["capacity_share"] for b in BLOCKS), 1)


class AnalyticsTests(unittest.TestCase):
    def test_regression_recovers_exact_line(self):
        m = LinearModel([0, 1, 2, 3], [5, 7, 9, 11])
        self.assertAlmostEqual(m.slope, 2)
        self.assertAlmostEqual(m.intercept, 5)
        self.assertAlmostEqual(m.r2, 1)

    def test_production_forecast(self):
        fc = forecast_series(PRODUCTION_SERIES, 2)
        self.assertEqual([r["season"] for r in fc["rows"]], ["2024-25", "2025-26"])
        self.assertAlmostEqual(fc["models"]["production_t"]["slope"], 28685.714, places=2)
        first = fc["rows"][0]
        self.assertAlmostEqual(first["production_t"], 1400733.33, places=1)
        self.assertLess(first["production_lower"], first["production_t"])
        self.assertLess(first["production_t"], first["production_upper"])

    def test_yoy_cagr_and_seasons(self):
        s = with_yoy(PRODUCTION_SERIES)
        self.assertIsNone(s[0]["production_yoy"])
        self.assertAlmostEqual(s[-1]["production_yoy"], 11000 / 1351000)
        self.assertEqual(next_season("2023-24"), "2024-25")
        self.assertEqual(next_season("2098-99"), "2099-00")
        self.assertAlmostEqual(cagr(100, 121, 2), 0.1)


class StorageTests(unittest.TestCase):
    def test_demand_and_coverage(self):
        self.assertEqual(storage_demand(1362000, 0.75), 1021500)
        self.assertAlmostEqual(facility_coverage(10215, 1021500), 0.01)

    def test_deficit_when_demand_exceeds_capacity(self):
        sim = simulate_storage_year(demand_t=1021500, capacity_t=900000,
                                    intake_profile=MONTHLY_INTAKE_PROFILE, release_profile=MONTHLY_RELEASE_PROFILE)
        self.assertEqual(sim["peak_month"], "Apr")
        self.assertAlmostEqual(sim["total_overflow_t"], 121500)
        self.assertEqual(sim["deficit_months"], ["Apr"])
        self.assertEqual(sim["status"], "critical")
        self.assertTrue(all(m["stock"] <= 900000 + 1e-6 for m in sim["months"]))

    def test_no_deficit_with_headroom(self):
        sim = simulate_storage_year(demand_t=500000, capacity_t=900000,
                                    intake_profile=MONTHLY_INTAKE_PROFILE, release_profile=MONTHLY_RELEASE_PROFILE)
        self.assertEqual(sim["total_overflow_t"], 0)
        self.assertEqual(sim["status"], "good")
        self.assertAlmostEqual(sim["months"][-1]["stock"], 0, places=6)

    def test_block_strain_and_levels(self):
        rows = block_strain(BLOCKS, demand_t=1000, capacity_t=1000)
        sik = next(r for r in rows if r["id"] == "sikandra-rao")
        self.assertAlmostEqual(sik["utilisation"], 0.18 / 0.13)
        self.assertEqual(sik["level"], "critical")
        self.assertEqual(strain_level(0.5), "good")
        self.assertEqual(strain_level(0.8), "warning")
        self.assertEqual(strain_level(0.95), "serious")


if __name__ == "__main__":
    unittest.main()
