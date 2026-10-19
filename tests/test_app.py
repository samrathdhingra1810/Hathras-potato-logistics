import os
import re
import tempfile
import unittest

from portal import create_app
from portal.core.custom import InputError, analyse, hathras_example, validate


def _csrf(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "csrf token missing from page"
    return m.group(1)


class CustomEngineTests(unittest.TestCase):
    def test_example_matches_hathras_engine(self):
        a = analyse(hathras_example())
        self.assertEqual(a["forecast"]["rows"][0]["season"], "2024-25")
        self.assertAlmostEqual(a["forecast"]["rows"][0]["production_t"], 1400733.33, places=1)
        self.assertEqual(a["simulation"]["status"], "critical")
        self.assertAlmostEqual(a["simulation"]["total_overflow_t"], 71500)
        self.assertEqual(a["warnings"], [])

    def test_rejects_bad_input(self):
        bad = hathras_example()
        bad["series"] = bad["series"][:2]
        with self.assertRaises(InputError):
            validate(bad)
        gap = hathras_example()
        del gap["series"][2]
        with self.assertRaises(InputError) as cm:
            validate(gap)
        self.assertTrue(any("consecutive" in e for e in cm.exception.errors))
        wrong = hathras_example()
        wrong["series"][0]["season"] = "2018-20"
        with self.assertRaises(InputError):
            validate(wrong)

    def test_warns_on_unusual_yield_and_scales_percent_calendar(self):
        p = hathras_example()
        p["series"][0]["production_t"] = 1218  # kg mistaken for tonnes -> tiny yield
        p["intake_profile"] = {"Feb": 20, "Mar": 60, "Apr": 30}  # percentages, sum 110
        v = validate(p)
        self.assertTrue(any("unusual" in w for w in v["warnings"]))
        self.assertTrue(any("scaled" in w for w in v["warnings"]))
        self.assertAlmostEqual(sum(v["intake_profile"].values()), 1)


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        os.environ.pop("VERCEL", None)
        self.app = create_app({"TESTING": True, "SQLITE_PATH": os.path.join(self.tmp.name, "t.db"), "DATABASE_URL": ""})
        self.c = self.app.test_client()

    def tearDown(self):
        self.tmp.cleanup()

    def signup(self, email="test-user@example.test", password="test-pass-123"):
        token = _csrf(self.c.get("/signup").get_data(as_text=True))
        return self.c.post("/signup", data={"csrf_token": token, "name": "Test User", "email": email,
                                            "organisation": "", "password": password, "confirm": password, "terms": "1"})

    def test_public_pages_render(self):
        for path in ["/", "/hathras", "/plan", "/tools", "/tools/production", "/tools/forecast", "/tools/planner",
                     "/tools/map", "/data", "/about", "/services", "/privacy", "/terms", "/login", "/signup"]:
            with self.subTest(path=path):
                self.assertEqual(self.c.get(path).status_code, 200)
        self.assertEqual(self.c.get("/nope").status_code, 404)

    def test_analyse_api(self):
        r = self.c.post("/api/analyse", json=hathras_example())
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["simulation"]["status"], "critical")
        r = self.c.post("/api/analyse", json={"series": []})
        self.assertEqual(r.status_code, 422)
        self.assertTrue(r.get_json()["errors"])

    def test_signup_login_logout(self):
        r = self.signup()
        self.assertEqual(r.status_code, 302)
        self.assertIn("/dashboard", r.headers["Location"])
        self.assertIn("Hello, Test", self.c.get("/dashboard").get_data(as_text=True))
        # duplicate email
        self.c.post("/logout", data={"csrf_token": _csrf(self.c.get("/dashboard").get_data(as_text=True))})
        self.assertEqual(self.signup().status_code, 422)
        # wrong then right password
        token = _csrf(self.c.get("/login").get_data(as_text=True))
        bad = self.c.post("/login", data={"csrf_token": token, "email": "test-user@example.test", "password": "nope-nope"})
        self.assertEqual(bad.status_code, 401)
        good = self.c.post("/login", data={"csrf_token": token, "email": "TEST-USER@example.test", "password": "test-pass-123"})
        self.assertEqual(good.status_code, 302)

    def test_dashboard_requires_login_and_next_is_safe(self):
        r = self.c.get("/dashboard")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login", r.headers["Location"])
        token = _csrf(self.c.get("/signup").get_data(as_text=True))
        r = self.c.post("/signup?next=//evil.example", data={"csrf_token": token, "name": "A", "email": "a@example.test",
                                                              "password": "test-pass-123", "confirm": "test-pass-123", "terms": "1"})
        self.assertNotIn("evil", r.headers["Location"])

    def test_csrf_required_for_forms(self):
        r = self.c.post("/signup", data={"name": "A", "email": "a@example.test", "password": "x" * 9, "confirm": "x" * 9, "terms": "1"})
        self.assertEqual(r.status_code, 400)

    def test_plans_crud_and_isolation(self):
        self.signup()
        token = _csrf(self.c.get("/dashboard").get_data(as_text=True))
        h = {"X-CSRF-Token": token}
        self.assertEqual(self.c.post("/api/plans", json={"name": "X", "payload": hathras_example()}).status_code, 400)
        r = self.c.post("/api/plans", json={"name": "Agra 2025", "payload": hathras_example()}, headers=h)
        self.assertEqual(r.status_code, 201)
        pid = r.get_json()["id"]
        self.assertIn("Agra 2025", self.c.get("/dashboard").get_data(as_text=True))
        self.assertIn('"id": %d' % pid, self.c.get(f"/plan?plan={pid}").get_data(as_text=True))
        r = self.c.put(f"/api/plans/{pid}", json={"name": "Agra v2", "payload": hathras_example()}, headers=h)
        self.assertEqual(r.status_code, 200)
        bad = hathras_example(); bad["series"] = []
        self.assertEqual(self.c.post("/api/plans", json={"name": "bad", "payload": bad}, headers=h).status_code, 422)

        # A second user can't see or change the first user's plan.
        other = self.app.test_client()
        t2 = _csrf(other.get("/signup").get_data(as_text=True))
        other.post("/signup", data={"csrf_token": t2, "name": "Other", "email": "other@example.test",
                                    "password": "test-pass-456", "confirm": "test-pass-456", "terms": "1"})
        t2 = _csrf(other.get("/dashboard").get_data(as_text=True))
        self.assertEqual(other.put(f"/api/plans/{pid}", json={"name": "hijack", "payload": hathras_example()},
                                   headers={"X-CSRF-Token": t2}).status_code, 404)
        self.assertNotIn("Agra v2", other.get("/dashboard").get_data(as_text=True))
        self.assertEqual(other.post(f"/plans/{pid}/delete", data={"csrf_token": t2}).status_code, 404)

        # Owner deletes it.
        self.assertEqual(self.c.post(f"/plans/{pid}/delete", data={"csrf_token": token}).status_code, 302)
        self.assertNotIn("Agra v2", self.c.get("/dashboard").get_data(as_text=True))

    def test_account_password_change_and_delete(self):
        self.signup()
        token = _csrf(self.c.get("/account").get_data(as_text=True))
        r = self.c.post("/account", data={"csrf_token": token, "action": "password", "current_password": "wrong",
                                          "new_password": "new-pass-789", "confirm": "new-pass-789"})
        self.assertEqual(r.status_code, 422)
        r = self.c.post("/account", data={"csrf_token": token, "action": "password", "current_password": "test-pass-123",
                                          "new_password": "new-pass-789", "confirm": "new-pass-789"})
        self.assertEqual(r.status_code, 302)
        r = self.c.post("/account", data={"csrf_token": token, "action": "delete", "delete_password": "new-pass-789"})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.c.get("/dashboard").status_code, 302)


class VercelWithoutDatabaseTests(unittest.TestCase):
    def test_accounts_disabled_gracefully(self):
        os.environ["VERCEL"] = "1"
        os.environ.pop("SECRET_KEY", None)
        try:
            app = create_app({"TESTING": True, "DATABASE_URL": ""})
        finally:
            os.environ.pop("VERCEL", None)
        c = app.test_client()
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.get("/signup").status_code, 503)
        self.assertEqual(c.get("/dashboard").status_code, 302)
        self.assertEqual(c.post("/api/analyse", json=hathras_example()).status_code, 200)
        self.assertFalse(c.get("/api/health").get_json()["accounts"])


if __name__ == "__main__":
    unittest.main()
