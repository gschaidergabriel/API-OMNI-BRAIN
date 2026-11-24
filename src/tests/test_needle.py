"""Needle runtime: tokenizer must equal sentencepiece (ids recorded from the reference), the heap BPE must equal the quadratic reference, active mode falls back to the rules on any problem, shadow/off never change the rule answer."""
import os

import pytest

from omnipool import gehirn, needle_rt, schatten

MODEL = os.path.expanduser("~/omnipool-needles/rt/needle.model")


@pytest.mark.skipif(not os.path.isfile(MODEL), reason="needle.model not present")
def test_tokenizer_matches_reference():
    t = needle_rt.Tok(MODEL)
    assert t.encode("hello world, kimi/code-5b") == [706, 8055, 363, 5338, 745, 8052, 571, 626, 8043, 8106, 1061, 3762, 8064]
    assert t.encode("a\n\nb")[1:4] == [t.byte[10], t.byte[10], t.id["b"]] or t.byte[10] in t.encode("a\n\nb")      # newline is not a space: byte fallback
    assert t.encode("  x   y ") == t.encode("x y")                                                                # only plain spaces collapse and trim


def test_shadow_is_inert_without_weights(tmp_path, monkeypatch):
    monkeypatch.setattr(schatten, "DIR", str(tmp_path))
    assert not schatten.verfuegbar()
    schatten.beobachte("fix my python function", "code")
    assert schatten.stand()["available"] is False


def test_rules_unchanged_by_shadow():
    assert gehirn.klassifiziere({"messages": [{"role": "user", "content": "fix my python function"}]}) == ("code", "Code signals")
    assert gehirn.klassifiziere({"model": "omnipool-json", "messages": []}) == ("json", "Model name")


def _quadratic_bpe(t, text):
    """the original O(n^2) merge loop, as an independent reference for the heap version"""
    text = text.strip(" ")
    text = "▁" + "▁".join(x for x in text.split(" ") if x) if text else ""
    syms = list(text)
    while len(syms) > 1:
        best, bi = None, -1
        for i in range(len(syms) - 1):
            s = t.score.get(syms[i] + syms[i + 1])
            if s is not None and (best is None or s > best):
                best, bi = s, i
        if bi < 0:
            break
        syms[bi:bi + 2] = [syms[bi] + syms[bi + 1]]
    return [t.id[s] if s in t.id else None for s in syms]


@pytest.mark.skipif(not os.path.isfile(MODEL), reason="needle.model not present")
def test_heap_bpe_equals_quadratic_reference():
    t = needle_rt.Tok(MODEL)
    for s in ("Schreibe eine Funktion, die JSON parst und Fehler meldet.", "def foo(x):\n    return x**2  # fix the bug in my parser", "kimi/code-5b-instruct-v2.1_q4", "aaaa bbbb  cccc " * 30):
        ref = _quadratic_bpe(t, s)
        if None not in ref:
            assert t.encode(s) == ref


def test_active_mode_uses_needle_and_falls_back(monkeypatch):
    class Fake:
        def score(self, text, tools, ans):
            return {"code": -5.0, "json": -1.0, "de": -9.0, "reason": -7.0}
    monkeypatch.setattr(schatten, "modus", lambda: "active")
    monkeypatch.setattr(schatten, "verfuegbar", lambda: True)
    monkeypatch.setattr(schatten, "_N", [Fake()])
    monkeypatch.setattr(schatten, "_BREMSE", [0.0])
    monkeypatch.setattr(schatten, "_notiere", lambda *a: None)
    body = {"messages": [{"role": "user", "content": "fix my python function"}]}
    assert gehirn.klassifiziere(body) == ("json", "Trained router")                              # the needle decides content classes
    assert gehirn.klassifiziere({"model": "omnipool-code", "messages": []}) == ("code", "Model name")   # explicit choices never go to the needle
    assert gehirn.klassifiziere({"tools": [{}], "messages": body["messages"]})[1] == "Tools in call"

    class Boom:
        def score(self, *a):
            raise RuntimeError("x")
    monkeypatch.setattr(schatten, "_N", [Boom()])
    assert gehirn.klassifiziere(body) == ("code", "Code signals")                                  # error -> rules decide
    monkeypatch.setattr(schatten, "_N", [])
    assert gehirn.klassifiziere(body) == ("code", "Code signals")                                  # not loaded yet -> rules decide


@pytest.mark.skipif(not os.path.isfile(os.path.expanduser("~/omnipool-needles/rt/router.npz")), reason="weights not present")
def test_real_router_is_fast_and_sane():
    pytest.importorskip("numpy")
    import time
    n = needle_rt.Needle(os.path.expanduser("~/omnipool-needles/rt/router.npz"), MODEL)
    n.score("warm", schatten.TOOLS, schatten.ANS)
    t = time.perf_counter()
    sc = n.score("Schreibe eine Python-Funktion, die eine CSV-Datei einliest", schatten.TOOLS, schatten.ANS)
    assert (time.perf_counter() - t) < 1.0
    assert max(sc, key=sc.get) in ("code", "de")
