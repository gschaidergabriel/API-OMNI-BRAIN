"""Ranking shrinkage and confirmation probes."""
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("OMNIPOOL_MELDEN", "0")
from omnipool import core  # noqa: E402


@pytest.fixture()
def c(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "DB", str(tmp_path / "w.db"))
    monkeypatch.setattr(core, "DATA", str(tmp_path))
    monkeypatch.setattr(core, "tokens_of", lambda p: ["x"])
    cc = core.db()
    for m, ok, n in (("lucky", 1, 1), ("veteran", 9, 10), ("solid", 6, 6), ("bad", 1, 8)):
        cc.execute("INSERT INTO modell(provider, model, first_seen, faehigkeit, status) VALUES('p',?,?, 'chat','ok')", (m, time.time()))
        cc.execute("INSERT INTO klasse(provider, model, klasse, ok_n, n, lat_sum, last_ts) VALUES('p',?,'code',?,?,?,?)", (m, ok, n, n * 1.0, time.time()))
    cc.commit()
    return cc


def test_one_lucky_probe_does_not_outrank_a_record(c):
    import random
    random.seed(7)
    firsts = {}
    for _ in range(400):
        f = core.rangfolge(c, "code", None, 1)[0][1]
        firsts[f] = firsts.get(f, 0) + 1
    assert firsts.get("lucky", 0) < 0.22 * 400 and firsts.get("bad", 0) < 0.02 * 400 and firsts.get("solid", 0) + firsts.get("veteran", 0) > 0.7 * 400, firsts
    p = {m: pr for _p, m, pr, _n, _l in core.rangfolge(c, "code", None, 9)}
    assert p["lucky"] < p["solid"] and p["bad"] < 0.4


def test_confirmation_picks_thin_evidence_only(c):
    assert ("p", "lucky") in core.bestaetigung(c) and ("p", "veteran") not in core.bestaetigung(c) and ("p", "solid") not in core.bestaetigung(c)
    assert core.bestaetigung(c, 0) == []
