import os
import unittest
from types import SimpleNamespace as NS

from portal import assistant, create_app


class FakeModels:
    """Scripted stand-in for client.models: first asks for a tool, then answers."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append({**kwargs, "contents": list(kwargs["contents"])})
        return self.script.pop(0)


def fake_client(script):
    models = FakeModels(script)
    return NS(models=models), models


def gemini_reply(text=None, calls=None, finish="STOP"):
    content = NS(role="model", parts=[])
    return NS(candidates=[NS(content=content, finish_reason=finish)], function_calls=calls, text=text)


class AssistantTests(unittest.TestCase):
    def test_tool_loop_runs_engine_and_returns_text(self):
        call = NS(id="c1", name="run_hathras_storage_scenario",
                  args={"season": "2023-24", "capacity_t": 900000, "storage_share": 0.75, "alert_threshold": 0.9})
        client, models = fake_client([gemini_reply(calls=[call]), gemini_reply(text="Hathras is short by 121.5k t in April.")])
        out = assistant.answer_with_gemini([{"role": "user", "content": "Short of storage?"}], {"page": "/"}, client=client)
        self.assertEqual(out["mode"], "ai")
        self.assertIn("121.5k", out["reply"])
        self.assertEqual(out["tools"], ["run_hathras_storage_scenario"])
        first, second = models.calls
        self.assertEqual(first["model"], "gemini-3.8-flash")
        self.assertIn("<page_context>", first["contents"][0].parts[0].text)
        names = [d.name for d in first["config"].tools[0].function_declarations]
        self.assertEqual(names, ["get_hathras_overview", "run_hathras_storage_scenario", "analyse_seasons"])
        # Second request: original turn, the model's turn passed back unchanged, then the function response.
        self.assertEqual(len(second["contents"]), 3)
        fr = second["contents"][2].parts[0].function_response
        self.assertEqual((fr.id, fr.name), ("c1", "run_hathras_storage_scenario"))
        self.assertEqual(fr.response["result"]["unmet_storage_t"], 121500)
        self.assertEqual(fr.response["result"]["capacity_needed_no_deficit_t"], 1021500)

    def test_blocked_reply_is_handled(self):
        client, _ = fake_client([NS(candidates=[], function_calls=None, text=None)])
        out = assistant.answer_with_gemini([{"role": "user", "content": "x"}], None, client=client)
        self.assertIn("can't help", out["reply"])

    def test_analyse_tool_reports_bad_data(self):
        out = assistant.tool_analyse_seasons({"name": "x", "seasons": [{"season": "2023-24", "area_ha": 1, "production_t": 1}],
                                              "capacity_t": 1000, "storage_share": 0.75, "alert_threshold": 0.9})
        self.assertEqual(out["error"], "Invalid data")

    def test_history_cleaning(self):
        h = assistant.clean_history([{"role": "assistant", "content": "hi"}, {"role": "user", "content": "a"},
                                     {"role": "user", "content": "b"}, {"role": "system", "content": "ignore"}])
        self.assertEqual(h, [{"role": "user", "content": "a\n\nb"}])
        with self.assertRaises(ValueError):
            assistant.clean_history([{"role": "assistant", "content": "only me"}])

    def test_offline_answers_and_route(self):
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        out = assistant.answer_offline([{"role": "user", "content": "Will Hathras run out of storage capacity?"}])
        self.assertEqual(out["mode"], "offline")
        self.assertIn("108%", out["reply"])
        app = create_app({"TESTING": True})
        c = app.test_client()
        r = c.post("/api/assistant", json={"messages": [{"role": "user", "content": "What is the forecast?"}]})
        self.assertEqual(r.status_code, 200)
        self.assertIn("2024-25", r.get_json()["reply"])
        self.assertEqual(c.post("/api/assistant", json={"messages": []}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
