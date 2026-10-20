"""Farmer / FPO / owner workspaces: plain-language view first, dense data behind a toggle."""
import re
import unittest
from unittest import mock

from portal import create_app
from portal import roles
from portal.core import dataset as ds
from portal.scenario import hathras_scenario


class FieldViewTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app({"TESTING": True}).test_client()

    def page(self, path):
        r = self.c.get(path)
        self.assertEqual(r.status_code, 200, path)
        return r.get_data(as_text=True)

    def test_fpo_three_second_view_comes_first(self):
        html = self.page("/workspace/fpo")
        order = [html.index(t) for t in ("Storage space near you", "Expected peak filling", "Contact a storage facility",
                                         "Advanced Data &amp; Methodology")]
        self.assertEqual(order, sorted(order))
        # Dense content is inside the collapsed advanced section, not above it.
        adv = html.index("data-advanced")
        self.assertGreater(html.index("Where storage is still available"), adv)
        self.assertNotIn("<details class=\"advanced\" data-advanced open", html)

    def test_block_status_matches_the_scenario(self):
        sc = hathras_scenario({})
        ws = roles.workspace_data("fpo")
        by_id = {b["id"]: b for b in sc["blocks"]}
        for s in ws["space"]:
            b = by_id[s["id"]]
            self.assertEqual(s["level"], b["level"])
            self.assertEqual(s["spare_t"], max(b["gap_t"], 0))
            self.assertEqual(s["short_t"], max(-b["gap_t"], 0))
            self.assertEqual(s["light"], {"good": "green", "warning": "yellow", "serious": "red", "critical": "red"}[b["level"]])
        self.assertEqual(ws["peak_month"], sc["simulation"]["peak_month"])
        html = self.page("/workspace/fpo")
        self.assertEqual(html.count('class="fv-card fv-'), len(sc["blocks"]))
        for light in ("green", "yellow", "red"):          # colour is never alone: shape + words
            self.assertNotRegex(html, r'fv-status fv-%s"><i aria-hidden="true"></i>' % light)

    def test_peak_and_book_before_highlighted(self):
        ws = roles.workspace_data("fpo")
        html = self.page("/workspace/fpo")
        self.assertEqual(html.count(" is-peak"), 1)
        self.assertIn("is-book", html)
        months = {"Feb": "February", "Mar": "March", "Apr": "April"}
        self.assertIsNotNone(ws["book_before"])
        self.assertIn("Book space before <strong>%s</strong>" % months[ws["book_before"]], html)

    def test_contacts_are_not_invented(self):
        self.assertEqual(roles.FACILITY_CONTACTS, [])
        html = self.page("/workspace/fpo")
        self.assertIn("doesn't have a verified cold storage phone directory yet", html)
        self.assertNotIn('href="tel:', html)

    def test_contacts_render_when_supplied(self):
        entry = {"name": "Test store", "block_id": "sasni", "phone": "+910000000000"}
        with mock.patch.object(roles, "FACILITY_CONTACTS", [entry]):
            html = self.page("/workspace/fpo")
        self.assertIn('href="tel:+910000000000"', html)

    def test_owner_overflow_alerts_in_plain_numbers(self):
        html = self.page("/workspace/owner")
        self.assertIn("Sadabad: +12.2k t</strong> expected overflow", html)
        shorts = [b for b in hathras_scenario({})["blocks"] if b["gap_t"] < 0]
        self.assertEqual(html.count("expected overflow <span"), len(shorts))
        for t in ("District stores at peak", "Produce looking for space", "Power cost per tonne", "District power bill"):
            self.assertIn(t, html)

    def test_admin_keeps_full_access(self):
        html = self.page("/workspace/admin")
        self.assertNotIn("data-advanced", html)          # nothing hidden for the district view
        for href in ("/tools/forecast#evaluation", "/tools/planner", "/tools/map", "/data/production.csv"):
            self.assertIn(href, html)
        self.assertIn("Rolling-origin", self.page("/tools/forecast"))

    def test_estimate_badge_stays_prominent(self):
        html = self.page("/workspace/fpo")
        self.assertIn('<span class="est-tag">ESTIMATED (Pending Actuals)</span>', html)
        self.assertIn('class="rec-tag">Verified actual', html)

    def test_hindi_subtitles_available(self):
        for path in ("/workspace/fpo", "/workspace/owner", "/plan"):
            html = self.page(path)
            self.assertIn("data-hindi-toggle", html)
            self.assertIn('lang="hi"', html)
        self.assertIn("भंडारण क्षमता", self.page("/plan"))

    def test_plan_progressive_disclosure(self):
        html = self.page("/plan")
        adv = html.index("data-advanced")
        for inside in ('id="storage-chart"', 'id="forecast-chart"', 'data-bind="cagr"'):
            self.assertGreater(html.index(inside), adv, inside)
        for before in ('id="alert"', 'data-bind="need"', 'data-bind="production"'):
            self.assertLess(html.index(before), adv, before)
        self.assertIsNone(re.search(r'<details class="panel" open>\s*<summary>What-if', html))

    def test_touch_targets(self):
        css = open("portal/static/css/site.css").read()
        self.assertIn(".fv-select, .fv-btn { min-height: 48px;", css)
        self.assertRegex(css, r"@media \(pointer: coarse\) \{\s*\.btn, \.btn-sm, select\.input[^}]*min-height: 48px")

    def test_dataset_untouched(self):
        self.assertEqual(len(ds.PRODUCTION_SERIES), 6)
        self.assertEqual(ds.PRODUCTION_SERIES[-1]["production_t"], 1362000)


if __name__ == "__main__":
    unittest.main()
