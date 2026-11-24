"""In-app assistant: language, key refusal, read actions answered from the local DB, state changes only proposed."""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from omnipool import assistent, core  # noqa: E402
from test_deep import env  # noqa: E402,F401  (fixture)


@pytest.fixture
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "STATE", str(tmp_path))
    monkeypatch.setattr(core, "DB", str(tmp_path / "t.db"), raising=False)
    return core.db()


def stub(*answers):
    seen = []
    it = iter(answers)

    def ask(body, klasse):
        seen.append((body, klasse))
        return next(it), "prov/model"
    ask.seen = seen
    return ask


def test_language_and_secret_refusal(c):
    assert assistent.lang("Welche Keys sind kaputt?") == "de" and assistent.lang("Which keys are broken?") == "en"
    ask = stub("never called")
    r = assistent.chat(c, [{"role": "user", "content": "mein key ist gsk_" + "a1" * 16}], ask)
    assert r["model"] is None and "Schlüssel" in r["reply"] and not ask.seen                      # nothing went to a model
    r = assistent.chat(c, [{"role": "user", "content": "here: sk-" + "x" * 30}], ask)
    assert "API key" in r["reply"] and not ask.seen
    for ok in ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning is slow?", "Was ist mit mistral-large-4-1t-a52b-instruct-2512-preview?"):
        assert not assistent.SECRET.search(ok)                                                   # model names are not keys
    assert assistent.SECRET.search("token " + "AbC9" * 12) and assistent.SECRET.search("hash " + "a1" * 20)


def test_plain_answer_uses_german_class_and_hides_nothing_secret(c):
    ask = stub("Hallo, alles gut.")
    r = assistent.chat(c, [{"role": "user", "content": "Wie geht es dem Pool?"}], ask)
    assert r["reply"] == "Hallo, alles gut." and r["model"] == "prov/model" and r["proposal"] is None and ask.seen[0][1] == "de"
    sysmsg = ask.seen[0][0]["messages"][0]["content"]
    assert "LIVE STATE" in sysmsg and "MANUAL" in sysmsg and "German" in sysmsg


def test_read_action_is_answered_from_local_data(c):
    ask = stub('Ich schaue nach.\nACTION: {"do": "best", "args": {"klasse": "code"}}', "Fertig: kein Modell.")
    r = assistent.chat(c, [{"role": "user", "content": "Welches Modell ist das beste fuer Code?"}], ask)
    assert r["reply"] == "Fertig: kein Modell." and len(ask.seen) == 2 and "RESULT of best" in ask.seen[1][0]["messages"][-1]["content"] and "ACTION" not in r["reply"]


def test_state_change_is_only_proposed(c):
    r = assistent.chat(c, [{"role": "user", "content": "scan now"}], stub('OK.\nACTION: {"do": "scan", "args": {}}'))
    assert r["proposal"] == {"api": "lauf", "body": {}, "label": "scan"} and r["reply"] == "OK."
    r = assistent.chat(c, [{"role": "user", "content": "stop everything"}], stub('ACTION: {"do": "stop_all"}'))
    assert r["proposal"]["api"] == "aus" and r["proposal"]["body"] == {"aus": True}
    r = assistent.chat(c, [{"role": "user", "content": "open settings"}], stub('ACTION: {"do": "open", "args": {"tab": "Settings"}}'))
    assert r["proposal"] == {"tab": "Settings", "label": "Settings"}


def test_unknown_or_hostile_action_is_ignored(c):
    for a in ('ACTION: {"do": "delete_keys", "args": {}}', 'ACTION: {"do": "open", "args": {"tab": "../../etc"}}', "ACTION: not json {"):
        r = assistent.chat(c, [{"role": "user", "content": "do it"}], stub("x\n" + a))
        assert r["proposal"] is None


def test_bad_input_and_endpoint(env):
    with pytest.raises(ValueError):
        assistent.chat(None, [{"role": "assistant", "content": "hi"}], None)
    c_, _h, r = env.req("POST", "/api/chat", {"messages": [{"role": "user", "content": "token nvapi-" + "z" * 30}]}, {"X-Omnipool": "1"})
    assert c_ == 200 and r["model"] is None and "key" in r["reply"].lower()
    c_, _h, r = env.req("POST", "/api/chat", {"messages": []}, {"X-Omnipool": "1"})
    assert c_ == 400


def test_find_api_reads_the_local_index(c, monkeypatch):
    from omnipool import radar
    monkeypatch.setattr(radar, "suche", lambda cc, q, n, z: {"apis": [{"name": "OCR.space", "beschr": "ocr pdf", "auth": "apiKey", "sicher": {"urteil": "unauffaellig"}}]})
    ask = stub('ACTION: {"do": "find_api", "args": {"q": "ocr"}}', "OCR.space passt.")
    r = assistent.chat(c, [{"role": "user", "content": "free ocr api?"}], ask)
    assert r["reply"] == "OCR.space passt." and "OCR.space" in ask.seen[1][0]["messages"][-1]["content"]


def test_read_then_task_in_one_message(c):
    ask = stub('ACTION: {"do": "best", "args": {"klasse": "de"}}', 'Erst die Antwort.\nACTION: {"do": "scan", "args": {}}')
    r = assistent.chat(c, [{"role": "user", "content": "Bestes Modell fuer Deutsch und dann scannen"}], ask)
    assert r["reply"] == "Erst die Antwort." and r["proposal"]["api"] == "lauf"
    ask = stub('ACTION: {"do": "best"}', 'x\nACTION: {"do": "status"}')                      # a chained read is ignored, no loop
    r = assistent.chat(c, [{"role": "user", "content": "best?"}], ask)
    assert r["proposal"] is None and len(ask.seen) == 2
    r = assistent.chat(c, [{"role": "user", "content": "hi"}], stub("no action at all"))      # plain text must not crash
    assert r["reply"] == "no action at all" and r["proposal"] is None


def test_no_model_reachable_explains_itself(c):
    r = assistent.chat(c, [{"role": "user", "content": "hello there"}], lambda body, k: (None, []))
    assert r["model"] is None and "No key added yet" in r["reply"]
    r = assistent.chat(c, [{"role": "user", "content": "hallo, wie geht es dir"}], lambda body, k: (None, ["nvidia: HTTP 500"]))
    assert "nvidia: HTTP 500" in r["reply"] and r["reply"].startswith("Kein freies Modell")
