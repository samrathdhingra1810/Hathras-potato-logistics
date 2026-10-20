import unittest

from portal import create_app
from portal.core.allocation import allocate
from portal.core.geo import haversine_km
from portal.scenario import hathras_scenario


def node(i, lat, lng, demand, cap):
    return {"id": i, "name": i, "lat": lat, "lng": lng, "demand_t": demand, "capacity_t": cap}


class AllocationTests(unittest.TestCase):
    def test_two_node_hand_case(self):
        a, b = node("A", 27.5, 78.0, 100, 0), node("B", 27.6, 78.0, 0, 60)
        r = allocate([a, b])
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["stored_t"], 60, places=4)
        self.assertAlmostEqual(r["unstored_t"], 40, places=4)
        self.assertAlmostEqual(r["local_only_stored_t"], 0)
        self.assertAlmostEqual(r["tonne_km"], 60 * haversine_km(a, b), places=2)

    def test_local_storage_is_preferred(self):
        # Both nodes can store everything locally; moving anything would only add haul.
        r = allocate([node("A", 27.5, 78.0, 50, 80), node("B", 27.6, 78.1, 30, 90)])
        self.assertEqual(r["transfers"], [])
        self.assertAlmostEqual(r["stored_t"], 80, places=4)

    def test_max_haul_excludes_far_store(self):
        near_short, far_spare = node("A", 27.5, 78.0, 100, 0), node("B", 28.5, 78.0, 0, 100)  # ~111 km apart
        self.assertAlmostEqual(allocate([near_short, far_spare])["stored_t"], 100, places=4)
        limited = allocate([near_short, far_spare], max_km=50)
        self.assertAlmostEqual(limited["stored_t"], 0, places=4)

    def test_road_factor_scales_distance(self):
        a, b = node("A", 27.5, 78.0, 10, 0), node("B", 27.6, 78.0, 0, 10)
        r1, r13 = allocate([a, b]), allocate([a, b], road_factor=1.3)
        self.assertAlmostEqual(r13["tonne_km"], r1["tonne_km"] * 1.3, places=3)

    def test_hathras_respects_limits_and_gain_equals_spare_capacity(self):
        sc = hathras_scenario({})
        nodes = [{k: b[k] for k in ("id", "name", "lat", "lng", "demand_t", "capacity_t")} for b in sc["blocks"]]
        r = allocate(nodes)
        self.assertAlmostEqual(r["stored_t"], min(r["demand_t"], r["capacity_t"]), delta=1)   # 950,000 t
        spare = sum(max(b["capacity_t"] - b["demand_t"], 0) for b in sc["blocks"])
        self.assertAlmostEqual(r["gain_t"], spare, delta=1)                                     # 48,830 t
        for nd in r["nodes"]:
            self.assertLessEqual(nd["stored_here_t"], nd["capacity_t"] + 1e-3)
            self.assertLessEqual(nd["shipped_t"], nd["demand_t"] + 1e-3)

    def test_api_labels_demo_and_cost_only_with_rate(self):
        c = create_app({"TESTING": True}).test_client()
        r = c.get("/api/allocation?max_km=25").get_json()
        self.assertTrue(r["ok"])
        self.assertIsNone(r["freight_cost_rs"])
        self.assertIn("modelled", r["data_basis"])
        r = c.get("/api/allocation?max_km=25&rate=4").get_json()
        self.assertAlmostEqual(r["freight_cost_rs"], r["tonne_km"] * 4)


if __name__ == "__main__":
    unittest.main()
