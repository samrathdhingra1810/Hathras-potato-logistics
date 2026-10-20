"""Traces every headline figure back to its inputs and formula (default Hathras assumptions).

Inputs: 2023-24 production 1,362,000 t; 75% stored; capacity 950,000 t (placeholder);
intake Feb 18% / Mar 57% / Apr 25%; release May 8, Jun 12, Jul 15, Aug 17, Sep 18,
Oct 17, Nov 13 (%); 9 kWh per tonne-month at Rs 7.5/kWh (placeholders).
"""
import unittest

from portal.core import dataset as ds
from portal.core.custom import analyse, hathras_example
from portal.core.storage import MONTHS, simulate_storage_year
from portal.scenario import hathras_scenario

DEMAND = 1362000 * 0.75      # 1,021,500 t want cold storage
CAP = 950000


class HathrasTraceTests(unittest.TestCase):
    def setUp(self):
        self.s = hathras_scenario({})
        self.sim = self.s["simulation"]
        self.m = {x["month"]: x for x in self.sim["months"]}

    def test_production_and_demand(self):
        self.assertEqual(self.s["production_t"], 1362000)
        self.assertEqual(self.s["demand_t"], DEMAND)

    def test_monthly_loading_and_overflow(self):
        self.assertAlmostEqual(self.m["Feb"]["intake"], DEMAND * 0.18)          # 183,870
        self.assertAlmostEqual(self.m["Mar"]["stock"], DEMAND * 0.75)           # 766,125 after Feb+Mar
        self.assertAlmostEqual(self.m["Apr"]["accepted"], CAP - DEMAND * 0.75)  # 183,875 fits
        self.assertAlmostEqual(self.m["Apr"]["overflow"], DEMAND - CAP)         # 71,500 has no slot
        self.assertAlmostEqual(self.sim["total_overflow_t"], 71500)
        self.assertEqual(self.sim["deficit_months"], ["Apr"])

    def test_strain_and_capacity_needed(self):
        self.assertAlmostEqual(self.sim["peak_utilisation"], DEMAND / CAP)       # 107.5%
        self.assertEqual(self.sim["peak_month"], "Apr")
        self.assertAlmostEqual(self.sim["capacity_needed_t"], DEMAND)
        self.assertAlmostEqual(self.sim["capacity_needed_threshold_t"], DEMAND / 0.9)
        self.assertAlmostEqual(self.sim["capacity_gap_t"], DEMAND - CAP)
        self.assertAlmostEqual(self.s["district_coverage"], CAP / DEMAND)        # 93.0%
        self.assertAlmostEqual(self.s["facilities_to_close_gap"], (DEMAND - CAP) / 10000)

    def test_mass_balance(self):
        months = self.sim["months"]
        self.assertAlmostEqual(sum(x["intake"] for x in months), DEMAND)
        for x in months:
            self.assertAlmostEqual(x["accepted"] + x["overflow"], x["intake"])
            self.assertGreaterEqual(x["end_stock"], -1e-6)
            self.assertLessEqual(x["stock"], CAP + 1e-6)
        stored = sum(x["accepted"] for x in months)
        self.assertAlmostEqual(stored, CAP)
        self.assertAlmostEqual(sum(x["release"] for x in months), stored)
        self.assertAlmostEqual(months[-1]["end_stock"], 0, places=6)

    def test_releases_follow_calendar_on_stored_stock(self):
        # Overflow never entered storage, so releases are shares of the 950,000 t stored.
        for mo, share in ds.MONTHLY_RELEASE_PROFILE.items():
            self.assertAlmostEqual(self.m[mo]["release"], CAP * share, msg=mo)

    def test_block_strain(self):
        b = {x["id"]: x for x in self.s["blocks"]}
        sik = b["sikandra-rao"]
        self.assertAlmostEqual(sik["demand_t"], DEMAND * 0.18)        # 183,870
        self.assertAlmostEqual(sik["capacity_t"], CAP * 0.13)         # 123,500
        self.assertAlmostEqual(sik["utilisation"], (DEMAND * 0.18) / (CAP * 0.13))  # 148.9%
        self.assertAlmostEqual(sum(x["demand_t"] for x in b.values()), DEMAND)
        self.assertAlmostEqual(sum(x["capacity_t"] for x in b.values()), CAP)
        # District gap = sum of block gaps.
        self.assertAlmostEqual(sum(x["gap_t"] for x in b.values()), CAP - DEMAND)

    def test_holding_economics(self):
        e = self.s["economics"]
        # Average stock per month = (opening + closing) / 2, summed over the year.
        expected_tm = sum((x["start_stock"] + x["end_stock"]) / 2 for x in self.sim["months"])
        self.assertAlmostEqual(e["tonne_months"], expected_tm)
        self.assertAlmostEqual(e["tonne_months"], 5016000, delta=10)
        self.assertAlmostEqual(e["season_cost_rs"], expected_tm * 9 * 7.5)
        self.assertAlmostEqual(e["cost_per_t_stored_rs"], e["season_cost_rs"] / CAP)

    def test_custom_engine_matches_hathras_engine(self):
        a = analyse(hathras_example())
        for k in ("total_overflow_t", "peak_utilisation", "capacity_needed_t", "capacity_gap_t"):
            self.assertAlmostEqual(a["simulation"][k], self.sim[k], msg=k)
        self.assertAlmostEqual(a["economics"]["season_cost_rs"], self.s["economics"]["season_cost_rs"])


class EdgeCaseTests(unittest.TestCase):
    def test_overlapping_calendar_conserves_mass(self):
        sim = simulate_storage_year(demand_t=1000, capacity_t=700, alert_threshold=0.9,
                                    intake_profile={"Feb": 0.5, "Mar": 0.5}, release_profile={"Mar": 0.2, "Apr": 0.8})
        stored = sum(x["accepted"] for x in sim["months"])
        self.assertLessEqual(sum(x["release"] for x in sim["months"]), stored + 1e-6)
        self.assertTrue(all(x["end_stock"] >= -1e-9 for x in sim["months"]))

    def test_ample_capacity_has_no_overflow(self):
        sim = simulate_storage_year(demand_t=500, capacity_t=10_000, alert_threshold=0.9,
                                    intake_profile=ds.MONTHLY_INTAKE_PROFILE, release_profile=ds.MONTHLY_RELEASE_PROFILE)
        self.assertEqual(sim["total_overflow_t"], 0)
        self.assertEqual(sim["capacity_gap_t"], 0)
        self.assertEqual([m["month"] for m in sim["months"]], MONTHS)


if __name__ == "__main__":
    unittest.main()
