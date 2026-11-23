import json
import os
import sys

os.environ["OMNIPOOL_HOME"] = "/tmp/op-unit"
os.environ["OMNIPOOL_MELDEN"] = "0"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from omnipool import anbieter, core, gehirn, server  # noqa: E402


def test_klassifikator():
    k = lambda t, **kw: gehirn.klassifiziere({"messages": [{"role": "user", "content": t}], **kw})[0]  # noqa: E731
    assert k("Schreibe eine Funktion in Python") == "code"
    assert k("Erkläre bitte, was ein Router ist") == "de"
    assert k("give me json output") == "json"
    assert k("hi", tools=[{"x": 1}]) == "tool"
    assert k("x" * 30000) == "long"
    assert gehirn.klassifiziere({"model": "omnipool-json", "messages": []})[0] == "json"
    assert gehirn.klassifiziere({"messages": [{"role": "user", "content": "hi"}]}, "code")[0] == "code"


def test_anthropic_roundtrip():
    b = {"system": "sei kurz", "max_tokens": 50, "messages": [{"role": "user", "content": "hi"},
         {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "f", "input": {"a": 1}}]},
         {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}],
         "tools": [{"name": "f", "description": "d", "input_schema": {"type": "object"}}]}
    o = server.a2o(b)
    assert o["messages"][0]["role"] == "system" and o["messages"][2]["tool_calls"][0]["function"]["name"] == "f"
    assert o["messages"][3] == {"role": "tool", "tool_call_id": "t1", "content": "ok"} and o["tools"][0]["function"]["name"] == "f"
    resp = {"choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "function": {"name": "f", "arguments": "{\"a\": 2}"}}]}, "finish_reason": "tool_calls"}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3}}
    a = server.o2a(resp, "m")
    assert a["stop_reason"] == "tool_use" and a["content"][0]["input"] == {"a": 2} and b"message_stop" in server.sse(a)


def test_breaker_and_keycool():
    gehirn.bremse("p", "m", 429)
    assert not gehirn.frei("p", "m")
    gehirn.gut("p", "m")
    assert gehirn.frei("p", "m")
    gehirn.bremse("p", "m2", 404)
    assert gehirn.BREAKER[("p", "m2")]["bis"] > __import__("time").time() + 3600


def test_capability_inference():
    assert [anbieter.infer(x) for x in ("veo-3-fast", "flux-pro", "tts-voice-1", "embed-v2", "llama-3-70b")] == ["video", "bild", "audio", "embedding", "chat"]


def test_probe_checks():
    assert core._json_ok('```json\n{"stadt":"Wien","einwohner_mio":1.9,"sprachen":["Deutsch","Englisch"]}\n```')
    assert not core._json_ok('{"stadt":"Graz"}')
    assert core._code_ok("```python\ndef fib(n):\n    a, b = 0, 1\n    for _ in range(n):\n        a, b = b, a + b\n    return a\n```")
    assert not core._code_ok("import os\ndef fib(n): os.system('x')")
    assert core._reason_ok("Ben") and not core._reason_ok("Anna")
    assert core._tool_ok({"tool_calls": [{"function": {"name": "hole_wert", "arguments": "{\"schluessel\": \"alpha\"}"}}]})


def test_rank_and_learn():
    c = core.db()
    c.execute("INSERT OR REPLACE INTO modell(provider, model, first_seen, status, faehigkeit) VALUES('t','good',0,'ok','chat'),('t','bad',0,'ok','chat')")
    for m, ok in (("good", 9), ("bad", 1)):
        c.execute("INSERT OR REPLACE INTO klasse VALUES('t',?,?,?,10,10,0)", (m, "code", ok))
    c.commit()
    wins = sum(core.rangfolge(c, "code", "t", 1)[0][1] == "good" for _ in range(50))
    assert wins > 40
    gehirn.lerne(c, "app", "code", "t", "bad", True, 1.0)
    assert c.execute("SELECT ok_n FROM klasse WHERE model='bad'").fetchone()[0] == 1.5
