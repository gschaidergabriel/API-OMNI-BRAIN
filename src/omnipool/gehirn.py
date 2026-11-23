"""API-OMNI-BRAIN brain: the organs that make a set of scripts act like one system. Honest label: a well-made set of scripts and proto-AI parts (rules, bandits, a
judge model), not one learned mind. The organs interlock through the one store (omnipool.db):
  Sensor      core.scan_keys           which keys live, which are limited/dead
  Katalog     core.entdecke            which models each provider serves now (new / vanished)
  Sonden      core.sonde_modell        machine-checked tests per class (code json de reason long tool)
  Richter     core.judge_de            the strong NVIDIA model scores what a script cannot check
  Klassifikator  klassifiziere         what kind of request is this (rules now; a trained needle can replace it, same signature)
  Wahl        kandidaten               Thompson sampling over probe + live evidence, minus latency, plus the provider preference
  Immunsystem breaker / key cooldown   a failing model or limited key rests, then returns
  Reflexion   lerne + drift            every real request feeds the class stats (half weight); a top model that starts failing is re-probed at once
  Planer      core.lauf + busy         unseen models first, then the oldest; not while the machine is busy"""
import json
import random
import re
import threading
import time

from . import core

_L = threading.Lock()
BREAKER = {}          # (provider, model) -> {"n": consecutive fails, "bis": ts, "grund": str}
KEYCOOL = {}          # token hash -> ts until which this whole key rests
KEYMODEL = {}         # (token hash, model) -> ts until which this key rests for this model only
KEY429 = {}           # token hash -> [(ts, model)] recent rate-limit answers
CLASS_NAMES = {"omnipool-" + k: k for k in core.KLASSEN}
CLASS_NAMES["omnipool-auto"] = "auto"
DE_W = {"der", "die", "das", "und", "ist", "nicht", "ein", "eine", "mit", "für", "auf", "wie", "was", "ich", "du", "bitte", "kannst", "warum", "wird", "zu"}


def busy():
    """the machine is under pressure: no probing now (load per core > 0.6 or less than 3 GB available)"""
    try:
        load = float(open("/proc/loadavg").read().split()[0])
        cores = max(1, len([ln for ln in open("/proc/cpuinfo") if ln.startswith("processor")]))
        mem = next(int(ln.split()[1]) for ln in open("/proc/meminfo") if ln.startswith("MemAvailable")) / 1048576
        return load / cores > 0.6 or mem < 3.0
    except (OSError, StopIteration, ValueError):
        return False


def _text(c):
    return c if isinstance(c, str) else " ".join(b.get("text", "") for b in c or [] if isinstance(b, dict))


def klassifiziere(body, standard="auto"):
    """-> (class, reason). An explicit model name wins, then the app's preset, then tools, then what the last user message looks like."""
    k = CLASS_NAMES.get(str(body.get("model", "")))
    if k and k != "auto":
        return k, 'Model name'
    if standard not in ("auto", None, ""):
        return standard, 'Application default'
    if body.get("tools"):
        return "tool", 'Tools in call'
    msgs = body.get("messages") or []
    total = sum(len(_text(m.get("content"))) for m in msgs) + len(_text(body.get("system")))
    last = next((_text(m.get("content")) for m in reversed(msgs) if m.get("role") == "user"), "")
    if total > 24000:
        return "long", 'very long context'
    if re.search(r"```|\bdef \w+\(|\bfunction\b|\bclass \w+|traceback|stack ?trace|compile|refactor|\bbug\b|funktion|programmier|skript|code\b", last, re.I):
        return "code", 'Code signals'
    if re.search(r"\bjson\b|schema|als tabelle|strukturiert", last, re.I):
        return "json", 'JSON signals'
    words = re.findall(r"[a-zäöüß]+", last.lower())
    if words and (sum(w in DE_W for w in words) / len(words) > 0.12 or re.search(r"[äöüß]", last)):
        return "de", 'German text'
    return "reason", 'Default'


def frei(p, m):
    b = BREAKER.get((p, m))
    if b and b["bis"] <= time.time():
        BREAKER.pop((p, m), None)
    return not BREAKER.get((p, m))


def bremse(p, m, status):
    """Immunsystem: 404/410 rest for 6 h, 429 for 90 s, other failures 30 s doubling up to 10 min"""
    with _L:
        b = BREAKER.setdefault((p, m), {"n": 0, "bis": 0, "grund": ""})
        b["n"] += 1
        if status in (404, 410):
            b["bis"], b["grund"] = time.time() + 6 * 3600, 'not available'
        elif status == 429:
            b["bis"], b["grund"] = time.time() + 90, "Limit"
        else:
            b["bis"], b["grund"] = time.time() + min(600, 30 * 2 ** (b["n"] - 1)), 'Error %s' % status


def gut(p, m):
    with _L:
        BREAKER.pop((p, m), None)


def key_waehlen(p, m=None):
    """a token of provider p that is not resting (neither as a whole nor for model m); None if all rest"""
    now = time.time()
    toks = [t for t in core.tokens_of(p) if KEYCOOL.get(core.token_hash(t), 0) <= now and KEYMODEL.get((core.token_hash(t), m), 0) <= now]
    return random.choice(toks) if toks else None


def limit(p, m, tok, sek=90):
    """a 429: the model rests, the key rests for that model; only when the same key is limited on two different models within a minute is the whole key resting"""
    h, now = core.token_hash(tok), time.time()
    sek = max(1, min(300, sek))
    with _L:
        KEYMODEL[(h, m)] = now + sek
        recent = [x for x in KEY429.get(h, []) if now - x[0] < 60] + [(now, m)]
        KEY429[h] = recent
        if len({x[1] for x in recent}) >= 2:
            KEYCOOL[h] = now + sek
    bremse(p, m, 429)


def key_ruhe(tok, sek=90):
    KEYCOOL[core.token_hash(tok)] = time.time() + sek


def kandidaten(c, klasse, n=6):
    """Wahl: ranked (provider, model) pairs that are free, have a usable key, with fallbacks when a class has no evidence yet"""
    vorrang = core.settings().get("vorrang", {"nvidia": 0.1})
    kette = {"tool": ["tool", "code", "reason"], "code": ["code", "reason"], "json": ["json", "code"], "de": ["de", "reason"], "long": ["long", "reason"]}.get(klasse, [klasse, "reason"])
    out, seen = [], set()
    for k in kette:
        for p, m, pr, _nn, _lat in core.rangfolge(c, k, None, 40):
            if (p, m) in seen or not frei(p, m) or not core.tokens_of(p):
                continue
            seen.add((p, m))
            out.append((pr + vorrang.get(p, 0.0) + (0.0 if k == klasse else -0.15), p, m))
        if len(out) >= n:
            break
    out.sort(reverse=True)
    return [(p, m) for _s, p, m in out[:n]]


def lerne(c, app, klasse, p, m, ok, lat, tin=0, tout=0, status=200):
    """Reflexion: log the request; a real outcome counts half as much as a probe in the class stats"""
    c.execute("INSERT INTO anfrage VALUES(?,?,?,?,?,?,?,?,?,?)", (time.time(), app, klasse, p, m, int(ok), lat, tin, tout, status))
    k = klasse if klasse in core.KLASSEN else "reason"
    c.execute("INSERT INTO klasse(provider, model, klasse, ok_n, n, lat_sum, last_ts) VALUES(?,?,?,?,0.5,?,?) ON CONFLICT(provider, model, klasse) DO UPDATE SET "
              "ok_n=ok_n+?, n=n+0.5, lat_sum=lat_sum+?, last_ts=?", (p, m, k, 0.5 * int(ok), lat * 0.5, time.time(), 0.5 * int(ok), lat * 0.5, time.time()))
    c.commit()


def drift(c):
    """a model whose last 10 real requests (>= 6 of them within 24 h) failed more than half of the time is probed again at once (probed=0 puts it first in the plan);
    the same model is not flagged again within 6 hours"""
    rows = c.execute("SELECT provider, model, COUNT(*), SUM(1-ok) FROM (SELECT provider, model, ok, ROW_NUMBER() OVER (PARTITION BY provider, model ORDER BY ts DESC) rn "
                     "FROM anfrage WHERE ts>?) WHERE rn<=10 GROUP BY 1, 2 HAVING COUNT(*)>=6 AND SUM(1-ok)*2>COUNT(*)", (time.time() - 86400,)).fetchall()
    n = 0
    for p, m, cnt, f in rows:
        tag = "%s/%s:" % (p, m)
        if c.execute("SELECT 1 FROM ereignis WHERE art='drift' AND text LIKE ? AND ts>?", (tag + "%", time.time() - 6 * 3600)).fetchone():
            continue
        c.execute("UPDATE modell SET probed=0 WHERE provider=? AND model=? AND probed>0", (p, m))
        core.ereignis(c, "drift", '%s: %d of the last %d real requests failed -> probe again' % (tag, f, cnt))
        n += 1
    c.commit()
    return n


def bericht(c):
    now = time.time()
    one = lambda q, *a: c.execute(q, a).fetchone()[0]  # noqa: E731
    anf = c.execute("SELECT app, COUNT(*), SUM(ok), SUM(tin), SUM(tout), AVG(lat) FROM anfrage WHERE ts>? GROUP BY app", (now - 86400,)).fetchall()
    prov = c.execute("SELECT provider, COUNT(*), SUM(ok), SUM(tin+tout) FROM anfrage WHERE ts>? GROUP BY provider", (now - 86400,)).fetchall()
    return {
        "organe": [
            {"name": "Sensor", "info": '%d Keys checked' % one("SELECT COUNT(*) FROM key"), "ts": one("SELECT MAX(checked) FROM key")},
            {"name": 'Catalog', "info": '%d models, %d omitted' % (one("SELECT COUNT(*) FROM modell"), one("SELECT COUNT(*) FROM modell WHERE gone>=3")),
             "ts": one("SELECT MAX(ts) FROM ereignis WHERE art='neue_modelle'")},
            {"name": 'Probes', "info": '%d samples, %d models tested' % (one("SELECT COUNT(*) FROM sonde"), one("SELECT COUNT(*) FROM modell WHERE n_try>0")),
             "ts": one("SELECT MAX(ts) FROM sonde")},
            {"name": 'Judge', "info": '%s evaluates German (%d judgments)' % (core.JUDGE[1].split("/")[-1], one("SELECT COUNT(*) FROM sonde WHERE judge IS NOT NULL")),
             "ts": one("SELECT MAX(ts) FROM sonde WHERE judge IS NOT NULL")},
            {"name": 'Classifier', "info": 'Rules (Needle 1 planned, waiting for approval)', "ts": None},
            {"name": 'Choice', "info": 'Thompson over probes + live operation, priority %s' % json.dumps(core.settings().get("vorrang", {"nvidia": 0.1})),
             "ts": one("SELECT MAX(ts) FROM anfrage")},
            {"name": "Immune system", "info": '%d models idle, %d keys idle' % (sum(1 for b in BREAKER.values() if b["bis"] > now), sum(1 for t in KEYCOOL.values() if t > now)), "ts": None},
            {"name": "Reflexion", "info": '%d real requests learned, %d drift findings' % (one("SELECT COUNT(*) FROM anfrage"), one("SELECT COUNT(*) FROM ereignis WHERE art='drift'")),
             "ts": one("SELECT MAX(ts) FROM ereignis WHERE art='drift'")},
            {"name": 'Needle 2 (choice) + 0.8B', "info": 'planned: training requires approval with an amount', "ts": None},
        ],
        "anwendungen": [{"app": a, "n": n, "ok": int(o or 0), "tin": int(i or 0), "tout": int(u or 0), "lat": round(lt or 0, 1)} for a, n, o, i, u, lt in anf],
        "anbieter": [{"provider": p, "n": n, "ok": int(o or 0), "tokens": int(t or 0)} for p, n, o, t in prov],
        "ruhende": [{"modell": "%s/%s" % k, "grund": b["grund"], "noch_s": int(b["bis"] - now)} for k, b in BREAKER.items() if b["bis"] > now],
        "ereignisse": [{"ts": t, "art": a, "text": x} for t, a, x in c.execute("SELECT ts, art, text FROM ereignis ORDER BY ts DESC LIMIT 40")],
    }
