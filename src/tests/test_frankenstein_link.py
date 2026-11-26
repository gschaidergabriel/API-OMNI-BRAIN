"""FranKenstein link: /api/waehle ranking over an allowed set and /api/lerne outside outcomes."""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMNIPOOL_MELDEN", "0")
from omnipool import core, gehirn  # noqa: E402


@pytest.fixture()
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", str(tmp_path / "w.db"))
    monkeypatch.setattr(core, "DATA", str(tmp_path))
    monkeypatch.setattr(core, "tokens_of", lambda p: ["x"])
    gehirn.BREAKER.clear()
    cc = core.db()
    for m, ok, n, st in (("ultra", 9, 10, "ok"), ("small", 10, 10, "ok"), ("broken", 9, 10, "fehler"), ("rest", 9, 10, "ok")):
        cc.execute("INSERT INTO modell(provider, model, first_seen, faehigkeit, status) VALUES('nvidia',?,?,'chat',?)", (m, time.time(), st))
        cc.execute("INSERT INTO klasse(provider, model, klasse, ok_n, n, lat_sum, last_ts) VALUES('nvidia',?,'tool',?,?,?,?)", (m, ok, n, n * 1.0, time.time()))
    cc.commit()
    return cc


def test_waehle_respects_allowed_set_breaker_and_failed_probe(c):
    gehirn.bremse("nvidia", "rest", 429)
    r = gehirn.waehle_fuer(c, "tool", [["nvidia", "ultra"], ["nvidia", "broken"], ["nvidia", "rest"], ["nvidia", "unseen"]])
    names = [x["model"] for x in r["rang"]]
    assert names == ["ultra", "broken"] and "small" not in names
    assert r["ruhend"] == [{"provider": "nvidia", "model": "rest"}] and r["ohne_beleg"] == [["nvidia", "unseen"]]
    assert gehirn.waehle_fuer(c, "bogus", None)["klasse"] == "reason"


def test_lerne_extern_counts_half_and_validates(c):
    ok, _ = gehirn.lerne_extern(c, {"app": "Machine-God", "klasse": "tool", "provider": "nvidia", "model": "ultra", "ok": False, "lat_s": 30})
    assert ok
    okn, n = c.execute("SELECT ok_n, n FROM klasse WHERE model='ultra' AND klasse='tool'").fetchone()
    assert (okn, n) == (9, 10.5)
    assert c.execute("SELECT app, ok FROM anfrage").fetchall() == [("ext-machine-god", 0)]
    assert not gehirn.lerne_extern(c, {"app": "x", "klasse": "tool", "provider": "nvidia", "model": "nope", "ok": True})[0]
    assert not gehirn.lerne_extern(c, {"app": "", "klasse": "tool", "provider": "nvidia", "model": "ultra", "ok": True})[0]
    assert not gehirn.lerne_extern(c, {"app": "x", "klasse": "evil", "provider": "nvidia", "model": "ultra", "ok": True})[0]
