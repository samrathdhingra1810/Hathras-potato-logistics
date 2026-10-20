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

    def test_backtest_never_sees_future_seasons(self):
        o = yr.BACKTEST_MIN_TRAIN
        future_changed = copy.deepcopy(self.rows)
        for r in future_changed[o + 1:]:
            r["yield_t_ha"] *= 3
            for c in yr.z_columns(future_changed):
                r[c] *= -2
        future_changed[o]["yield_t_ha"] = 999.0  # the target season's yield must not be used either
        for _key, _label, fn in yr.WEATHER_MODELS:
            self.assertAlmostEqual(fn(self.rows, o), fn(future_changed, o), places=9)

    def test_backtest_matches_documented_result(self):
        m = yr.backtest(self.rows)["models"]
        self.assertEqual(m["linear"]["n"], 8)
        for key, mae in (("linear", 2.944), ("mean", 2.486), ("naive", 3.635),
                         ("trend_weather", 3.930), ("trend_weather_weighted", 5.408), ("ridge_weather", 2.495)):
            self.assertAlmostEqual(m[key]["mae_t_ha"], mae, delta=0.001)
        # The basis for not integrating a weather model: none beats the historical-mean baseline.
        best_weather = min(m[k]["mae_t_ha"] for k, _l, _f in yr.WEATHER_MODELS)
        self.assertGreaterEqual(best_weather, m["mean"]["mae_t_ha"])


class ForecastSeasonLabelTests(unittest.TestCase):
    def test_labels_follow_the_data(self):
        from portal import create_app
        from portal.assistant import TOOLS
        from portal.core.analytics import forecast_seasons
        from portal.scenario import hathras_scenario

        fs = forecast_seasons(ds.PRODUCTION_SERIES)
        self.assertEqual(fs, [x["value"] for x in hathras_scenario({})["seasons"][1:]])
        desc = TOOLS[1]["input_schema"]["properties"]["season"]["description"]
        for s in [ds.PRODUCTION_SERIES[-1]["season"], *fs]:
            self.assertIn(s, desc)
        c = create_app({"TESTING": True}).test_client()
        for path in ("/hathras", "/services"):
            html = c.get(path).get_data(as_text=True)
            self.assertIn(f"{fs[0]} and {fs[1]}", html)


if __name__ == "__main__":
    unittest.main()
