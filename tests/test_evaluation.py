import unittest

from portal.core.dataset import PRODUCTION_SERIES as S
from portal.core.evaluation import RELIABLE_POINTS, evaluate, rolling_origin

SEASONS = [r["season"] for r in S]
YS = [r["production_t"] for r in S]


class RollingOriginTests(unittest.TestCase):
    def test_naive_errors_match_hand_calculation(self):
        ev = evaluate(S)
        rows = [r for r in ev["rows"] if r["model"] == "naive" and r["horizon"] == 1]
        # Trained to 2020-21 -> 2021-22: 1,298,000 vs 1,312,000, and so on.
        self.assertEqual([r["error"] for r in rows], [-14000, -39000, -11000])
        m = ev["metrics"]["naive"]["1"]
        self.assertAlmostEqual(m["mae"], 64000 / 3)
        self.assertAlmostEqual(m["wape"], 64000 / (1312000 + 1351000 + 1362000))
        self.assertAlmostEqual(m["bias"], -64000 / 3)

    def test_linear_errors_match_ols_by_hand(self):
        rows = [r for r in rolling_origin(SEASONS, YS) if r["model"] == "linear" and r["horizon"] == 1]
        # OLS on (0,1218k),(1,1261k),(2,1298k): slope 40,000, intercept 1,219,000 -> x=3 gives 1,339,000.
        self.assertAlmostEqual(rows[0]["forecast"], 1339000)
        self.assertEqual([round(r["error"]) for r in rows], [27000, 1000, 21100])

    def test_no_future_leakage(self):
        """Changing later seasons must not change forecasts made from earlier origins."""
        base = rolling_origin(SEASONS, YS)
        altered = YS[:4] + [YS[4] * 2, YS[5] * 3]
        changed = rolling_origin(SEASONS, altered)
        for a, b in zip(base, changed):
            if a["trained_on"] <= 4:  # origins that never saw index 4 or 5
                self.assertAlmostEqual(a["forecast"], b["forecast"])

    def test_horizon_two_pairs_and_counts(self):
        ev = evaluate(S)
        self.assertEqual(ev["metrics"]["linear"]["1"]["n"], 3)   # targets 2021-22, 2022-23, 2023-24
        self.assertEqual(ev["metrics"]["linear"]["2"]["n"], 2)   # targets 2022-23, 2023-24
        targets = {r["target"] for r in ev["rows"] if r["horizon"] == 2}
        self.assertEqual(targets, {"2022-23", "2023-24"})

    def test_skill_and_assessment(self):
        ev = evaluate(S)
        self.assertEqual(ev["metrics"]["naive"]["1"]["skill_vs_naive"], 0)
        a = ev["assessment"]
        self.assertEqual(a["level"], "indicative")
        self.assertIn("3 one-season-ahead tests", a["message"])
        self.assertTrue(a["linear_beats_naive"])

    def test_insufficient_history(self):
        ev = evaluate(S[:3])
        self.assertEqual(ev["assessment"]["level"], "insufficient")
        self.assertEqual(ev["rows"], [])

    def test_long_exact_trend_is_usable_and_linear_is_exact(self):
        n = RELIABLE_POINTS + 3
        series = [{"season": f"{2000 + i}-{(2001 + i) % 100:02d}", "production_t": 1000 + 50 * i} for i in range(n)]
        ev = evaluate(series)
        self.assertEqual(ev["assessment"]["level"], "usable")
        self.assertAlmostEqual(ev["metrics"]["linear"]["1"]["mae"], 0, places=6)
        self.assertAlmostEqual(ev["metrics"]["drift"]["1"]["mae"], 0, places=6)
        self.assertGreater(ev["metrics"]["naive"]["1"]["mae"], 0)


if __name__ == "__main__":
    unittest.main()
