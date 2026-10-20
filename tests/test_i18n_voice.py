"""EN | हिंदी switch and voice accessibility (read aloud, speak a block name)."""
import re
import unittest

from portal import create_app
from portal import i18n
from portal.core import dataset as ds
from portal.roles import workspace_data


class LanguageTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app({"TESTING": True}).test_client()

    def html(self, path):
        r = self.c.get(path)
        self.assertEqual(r.status_code, 200, path)
        return r.get_data(as_text=True)

    def test_switch_in_header_on_every_page(self):
        for path in ("/", "/workspace/fpo", "/plan", "/tools/map", "/tools/forecast", "/workspace/admin"):
            h = self.html(path)
            header = h[h.index('<header class="nav"'):h.index("</header>")]
            self.assertIn('data-set-lang="en"', header, path)
            self.assertIn('data-set-lang="hi" lang="hi"', header, path)

    def test_saved_language_applied_before_paint(self):
        h = self.html("/workspace/fpo")
        head = h[:h.index("</head>")]
        self.assertIn("localStorage.getItem('cf-lang')", head)            # in <head>, before any CSS-rendered content
        self.assertLess(head.index("cf-lang"), head.index("site.css"))

    def test_brief_examples_translated(self):
        fpo, plan = self.html("/workspace/fpo"), self.html("/plan")
        self.assertIn("स्थान आरक्षित करें", fpo)                            # "Book space"
        self.assertIn("उपलब्ध भंडारण", plan)                                # "Available storage"
        self.assertIn("भंडारण क्षमता", plan)                                # "Storage capacity"

    def test_every_translation_has_both_languages(self):
        for path in ("/workspace/fpo", "/plan"):
            h = self.html(path)
            en = re.findall(r'<span class="t-en">', h)
            hi = re.findall(r'<span class="t-hi" lang="hi">', h)
            self.assertEqual(len(en), len(hi), path)
            self.assertGreater(len(en), 20, path)

    def test_block_names_cover_dataset(self):
        ids = {b["id"] for b in ds.BLOCKS}
        self.assertEqual(set(i18n.BLOCK_HI), ids)
        self.assertEqual(set(i18n.BLOCK_ALIASES), ids)


class VoiceTests(unittest.TestCase):
    def setUp(self):
        self.c = create_app({"TESTING": True}).test_client()

    def test_read_aloud_buttons_on_status_cards(self):
        h = self.c.get("/workspace/fpo").get_data(as_text=True)
        n_blocks = len(ds.BLOCKS)
        self.assertEqual(h.count("data-say "), 2 * n_blocks + 1)            # your-block panels, block cards, peak tile
        btn = re.search(r'<button class="say-btn"[^>]*>', h).group(0)
        self.assertIn("hidden", btn)                                         # shown only if speechSynthesis exists
        self.assertIn('aria-label="Read', btn)

    def test_speech_uses_scenario_figures(self):
        ws = workspace_data("fpo")
        s = next(x for x in ws["space"] if x["spare_t"] > 0)
        h = self.c.get("/workspace/fpo").get_data(as_text=True)
        spoken = i18n.spoken_tonnes(s["spare_t"])
        self.assertIn('About %s tonnes of space left' % spoken, h)
        self.assertIn('लगभग %s टन जगह बाकी है' % spoken, h)

    def test_mic_on_map_and_fpo(self):
        fpo = self.c.get("/workspace/fpo").get_data(as_text=True)
        mp = self.c.get("/tools/map").get_data(as_text=True)
        self.assertIn('data-voice-target="#fv-block"', fpo)
        self.assertIn('data-voice-target="#block-filter"', mp)
        self.assertIn('id="block-filter" data-block-filter', mp)
        for h in (fpo, mp):
            self.assertIn("data-voice-note", h)                              # privacy note about the speech service

    def test_voice_script_loaded_and_offline(self):
        h = self.c.get("/").get_data(as_text=True)
        self.assertIn("/static/js/voice.js", h)
        self.assertIn("/static/js/voice.js", self.c.get("/sw.js").get_data(as_text=True))

    def test_touch_targets(self):
        css = open("portal/static/css/site.css").read()
        self.assertIn("min-height: 48px; min-width: 48px; padding: 0 10px;", css)   # language buttons
        self.assertRegex(css, r"\.say-btn, \.mic-btn \{[^}]*min-height: 48px; min-width: 48px;")


if __name__ == "__main__":
    unittest.main()
