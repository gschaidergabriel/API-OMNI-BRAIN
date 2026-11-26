"""Vorstufe as a fixed part of OMNI-BRAIN: active only while a usable key serves a Vorstufe model; model choice, key rest, learning."""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMNIPOOL_MELDEN", "0")
from omnipool import core, gehirn, vorstufe  # noqa: E402

ULTRA = "nvidia/nemotron-3-ultra-550b-a55b"
KIMI = "moonshotai/kimi-k3.1-pro"
KEYS = {}
CTX = {"TASK": "find the port", "CANDIDATES": [{"id": "c1", "text": "port 8799"}, {"id": "c2", "text": "x"}], "AVAILABLE_TOOLS": ["Read", "Write"]}
ENV = {"user_intent": "port", "hypotheses": [{"text": "8799", "refs": ["c1"]}], "counter_hypotheses": [{"text": "other", "refs": []}],
       "broadcast_ids": ["c1", "c9"], "tool_selection": ["Read", "Hack"], "epistemik": {"known": ["k"], "unknown": []}, "self_queries": [],
       "world_facts": [{"text": "f", "domain": "WISH", "refs": ["c1", "c7"]}], "impact": {"touches": ["a", "b"], "changes": "nothing"}}


@pytest.fixture()
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", str(tmp_path / "v.db"))
    monkeypatch.setattr(core, "DATA", str(tmp_path))
    monkeypatch.setattr(core, "STATE", str(tmp_path / "state"))
    monkeypatch.setattr(core, "settings", lambda: {"slot_aus": [], "vorrang": {}})
    KEYS.clear()
    KEYS.update({"nvidia": ["k-nv-1"], "openrouter": []})
    keys = KEYS
    monkeypatch.setattr(core, "tokens_of", lambda p: list(keys.get(p, [])))
    gehirn.BREAKER.clear()
    gehirn.KEYCOOL.clear()
    gehirn.KEYMODEL.clear()
    cc = core.db()
    for p, m in (("nvidia", ULTRA), ("nvidia", KIMI), ("nvidia", "small-8b"), ("openrouter", ULTRA + ":free")):
        cc.execute("INSERT INTO modell(provider, model, first_seen, faehigkeit, status) VALUES(?,?,?,'chat','ok')", (p, m, time.time()))
        cc.execute("INSERT INTO klasse(provider, model, klasse, ok_n, n, lat_sum, last_ts) VALUES(?,?,'json',9,10,10,?)", (p, m, time.time()))
    cc.commit()
    return cc


def test_active_only_with_a_key_for_a_vorstufe_model(c):
    b = vorstufe.bereit(c)
    assert b["aktiv"] and sorted(map(tuple, b["modelle"])) == [("nvidia", KIMI), ("nvidia", ULTRA)]
    assert "small-8b" not in json.dumps(b)
    KEYS["nvidia"] = []
    b = vorstufe.bereit(c)
    assert not b["aktiv"] and "no usable key" in b["grund"]
    KEYS["openrouter"] = ["k-or"]                                  # a key for another provider serving the same model switches it on
    assert vorstufe.bereit(c)["modelle"] == [["openrouter", ULTRA + ":free"]]


def test_gone_models_and_manual_off(c, monkeypatch):
    c.execute("UPDATE modell SET gone=1 WHERE provider='nvidia'")
    c.commit()
    assert not vorstufe.bereit(c)["aktiv"]
    monkeypatch.setattr(core, "settings", lambda: {"slot_aus": [], "vorrang": {}, "vorstufe": "aus"})
    assert vorstufe.bereit(c)["grund"].startswith("switched off")


def test_run_without_key_reports_inactive_and_calls_nothing(c):
    KEYS["nvidia"] = []
    code, out = vorstufe.run(c, {"kontext": CTX}, chat=lambda *a: pytest.fail("no call without a key"))
    assert code == 200 and out["aktiv"] is False


def test_run_cleans_envelope_learns_and_hides_the_key(c):
    seen = []

    def chat(p, m, prompt, tok, max_tok, timeout, extra):
        seen.append((p, m, extra["messages"][0]["content"][:60], json.loads(extra["messages"][1]["content"])["TASK"]))
        return 200, "```json\n" + json.dumps(ENV) + "\n```", 1.5
    code, out = vorstufe.run(c, {"kontext": CTX, "name": "FranKenstein"}, chat=chat)
    assert code == 200 and out["aktiv"]
    e = out["envelope"]
    assert e["broadcast_ids"] == ["c1"] and e["invented_ids"] == ["c9"] and e["tool_selection"] == ["Read"]
    assert e["world_facts"] == [{"text": "f", "domain": "OBSERVATION", "refs": ["c1"]}] and e["impact"]["touches"] == "a; b"
    assert seen[0][2].startswith("You are the pre-stage (Vorstufe) of FranKenstein.") and seen[0][3] == "find the port"
    assert "k-nv-1" not in json.dumps(out) and out["beleg"]["key"] == core.token_hash("k-nv-1")
    assert c.execute("SELECT app, ok FROM anfrage").fetchall() == [("vorstufe", 1)]


def test_rounds_append_their_instruction(c):
    assert vorstufe.system("X", "reflection").endswith("There is no further round.")
    assert '"too thin"' in vorstufe.system("X", "negotiation", "too thin")
    assert "<NAME>" not in vorstufe.system(None)


def test_key_errors_rest_the_key_and_bad_json_moves_on(c):
    KEYS["nvidia"] = ["k-nv-1", "k-nv-2"]                          # the second key takes over after the first rests
    calls = []

    def chat(p, m, prompt, tok, max_tok, timeout, extra):
        calls.append(m)
        if len(calls) == 1:
            return 403, "", 0.1
        return 200, "not json", 0.2
    code, out = vorstufe.run(c, {"kontext": json.dumps(CTX)}, chat=chat)
    assert code == 502 and any("key rests" in f for f in out["fehler"]) and any("no json" in f for f in out["fehler"])
    assert len(calls) <= 3                                           # key rested after 403, two no-json answers stop the run
