import json
import os
import unittest
from types import SimpleNamespace as NS

from portal import assistant, create_app


class FakeMessages:
    """Scripted stand-in for client.beta.messages: first asks for a tool, then answers."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.script.pop(0)


def fake_client(script):
    msgs = FakeMessages(script)
    return NS(beta=NS(messages=msgs)), msgs


class AssistantTests(unittest.TestCase):
    def test_tool_loop_runs_engine_and_returns_text(self):
        tool_turn = NS(stop_reason="tool_use", content=[
            NS(type="tool_use", id="t1", name="run_hathras_storage_scenario",
               input={"season": "2023-24", "capacity_t": 900000, "storage_share": 0.75, "alert_threshold": 0.9})])
        final = NS(stop_reason="end_turn", content=[NS(type="text", text="Hathras is short by 121.5k t in April.")])
        client, msgs = fake_client([tool_turn, final])
        out = assistant.answer_with_claude([{"role": "user", "content": "Short of storage?"}], {"page": "/"}, client=client)
        self.assertEqual(out["mode"], "ai")
        self.assertIn("121.5k", out["reply"])
        self.assertEqual(out["tools"], ["run_hathras_storage_scenario"])
        # The tool result sent back carries the engine's numbers.
        result = msgs.calls[1]["messages"][-1]["content"][0]
        data = json.loads(result["content"])
        self.assertEqual(data["unmet_storage_t"], 121500)
        self.assertEqual(data["capacity_needed_no_deficit_t"], 1021500)
        first = msgs.calls[0]
        self.assertEqual(first["model"], "claude-opus-5-5")
        self.assertEqual(first["fallbacks"], "default")
        self.assertIn("<page_context>", first["messages"][0]["content"])

    def test_refusal_is_handled(self):
        client, _ = fake_client([NS(stop_reason="refusal", content=[])])
        out = assistant.answer_with_claude([{"role": "user", "content": "x"}], None, client=client)
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
        os.environ.pop("ANTHROPIC_API_KEY", None)
        os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
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
