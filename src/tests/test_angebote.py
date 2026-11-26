"""Offers: OMNI finds new free AI APIs by itself and offers them in the chat at most twice a day; it learns from the answers."""
import json
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMNIPOOL_MELDEN", "0")
from omnipool import angebote, core, radar  # noqa: E402

T0 = 1_800_000_000.0
SET = {"slot_aus": [], "vorrang": {}}


@pytest.fixture()
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", str(tmp_path / "a.db"))
    monkeypatch.setattr(core, "DATA", str(tmp_path))
    monkeypatch.setattr(core, "settings", lambda: SET)
    monkeypatch.setattr(core, "custom", lambda: {"myllm": {"label": "My LLM", "base": "https://api.myllm.dev/v1"}})
    SET.pop("angebote_pro_tag", None)
    cc = core.db()
    radar.tabellen(cc)
    rows = [("1", "Speechly", "https://speechly.example.com/api", "free tier speech to text API", "Machine Learning", "apiKey", "public-apis"),
            ("2", "CatFacts", "https://catfacts.example.com", "random cat facts", "Animals", "no", "public-apis"),
            ("3", "Groq Cloud", "https://console.groq.com", "free LLM inference", "Machine Learning", "apiKey", "public-apis"),
            ("4", "Other LLM", "https://chat.myllm.dev", "LLM chat completions", "Machine Learning", "apiKey", "public-apis"),
            ("5", "VisionX", "https://visionx.example.org", "free image generation and vision models", "Machine Learning", "apiKey", "awesome"),
            ("6", "RedditAI", "https://www.reddit.com/r/ai", "free ai api", "Machine Learning", "no", "x"),
            ("7", "PlainHTTP", "http://plain.example.net", "free llm api", "Machine Learning", "no", "x")]
    for r in rows:
        cc.execute("INSERT INTO api_index VALUES(?,?,?,?,?,?,?,?)", r + (T0 - 3600,))
    cc.execute("INSERT INTO nachricht VALUES('n1',?,'feedA','New free embedding API launched','https://embed.example.io/blog','free tier embeddings',4,1)", (T0 - 7200,))
    cc.execute("INSERT INTO nachricht VALUES('n2',?,'feedA','Stock market news','https://stocks.example.io','markets',4,1)", (T0 - 7200,))
    cc.execute("INSERT INTO nachricht VALUES('n3',?,'feedA','How positional embeddings work in LLMs','https://blog.example.io/p','theory article',4,1)", (T0 - 7200,))
    cc.execute("INSERT INTO api_index VALUES('9','Speechly Pro','https://pro.speechly.example.com','speech to text API','Machine Learning','apiKey','x',?)", (T0 - 3600,))
    cc.execute("INSERT INTO api_index VALUES('8','ExactCup','https://exactcup.example.com','cooking ingredient densities and unit models','Food','no','x',?)", (T0 - 3600,))
    cc.commit()
    return cc


def test_sammle_takes_new_ai_apis_and_skips_known_unsafe_and_off_topic(c):
    assert angebote.sammle(c, T0) == 3
    names = {r[0] for r in c.execute("SELECT name FROM angebot")}
    assert names == {"Speechly", "VisionX", "New free embedding API launched"}      # Groq is built in, My LLM is the user's own provider
    assert angebote.sammle(c, T0 + 60) == 0                                          # nothing new since the last run


def test_at_most_two_a_day_six_hours_apart_never_twice(c):
    angebote.sammle(c, T0)
    a = angebote.naechstes(c, T0)
    assert a and a["name"] in ("Speechly", "VisionX")
    assert angebote.naechstes(c, T0 + 3600) is None                                  # too soon
    b = angebote.naechstes(c, T0 + 7 * 3600)
    assert b and b["id"] != a["id"]
    assert angebote.naechstes(c, T0 + 14 * 3600) is None                             # two within 24 h
    third = angebote.naechstes(c, T0 + 31 * 3600)
    assert third and third["id"] not in (a["id"], b["id"])
    assert angebote.naechstes(c, T0 + 40 * 3600) is None                             # nothing left: never repeats


def test_setting_zero_switches_offers_off(c):
    angebote.sammle(c, T0)
    SET["angebote_pro_tag"] = 0
    assert angebote.naechstes(c, T0) is None and angebote.darf(c, T0) == (False, "off")


def test_answers_teach_the_ranking(c):
    angebote.sammle(c, T0)
    a = angebote.naechstes(c, T0)
    assert angebote.antworte(c, a["id"], "nein", T0 + 10)
    assert not angebote.antworte(c, a["id"], "ja", T0 + 20)                          # one answer per offer
    assert not angebote.antworte(c, "a:2", "ja")                                     # never offered
    merk = json.loads(c.execute("SELECT merkmale FROM angebot WHERE id=?", (a["id"],)).fetchone()[0])
    assert angebote._gelernt(c, merk) < 0.5
    rest = [r for r in c.execute("SELECT basis, merkmale FROM angebot WHERE angeboten IS NULL")]
    assert all(angebote.wert(c, b, json.loads(m)) <= b + 0.01 for b, m in rest if "kat:machine learning" in m)


def test_three_no_in_a_row_pause_three_days(c):
    angebote.tabellen(c)
    for i in range(4):
        c.execute("INSERT INTO angebot(id, art, name, url, merkmale, basis, gefunden) VALUES(?,?,?,?,?,?,?)",
                  ("x%d" % i, "api", "X%d" % i, "https://x%d.example.com" % i, "[]", 0.5, T0))
    c.commit()
    t = T0
    for _ in range(3):
        o = angebote.naechstes(c, t)
        assert o
        angebote.antworte(c, o["id"], "nein", t + 1)
        t += 13 * 3600
    assert angebote.darf(c, t)[1].startswith("paused")
    assert angebote.naechstes(c, t + 3 * 86400 + 10)
