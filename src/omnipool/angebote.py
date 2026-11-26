"""Offers: OMNI keeps looking for new free AI APIs by itself and offers the best new one in the AI chat, without nagging.

- Finding: every 6 h (radar cycle) new rows of the free-API index and free-API news are read; AI-related ones that the user does
  not have yet become candidates. Reddit stays out (radar rule), the safety check of the radar cards applies when shown.
- Offering: at most `angebote_pro_tag` per day (default 2, max 2, 0 = off), at least 6 h apart, never the same one twice, and a
  3-day pause after three "no" answers in a row. Only shown in the AI chat; nothing is installed or sent by itself.
- Learning: every answer counts for the offer's features (kind, category, source, capability); the next candidates are ranked
  by their base value plus what the answers taught (Beta mean per feature)."""
import json
import re
import time
import urllib.parse

from . import core, radar, sicher

INTERVALL = 6 * 3600
ABSTAND_S = 6 * 3600
PAUSE_NEIN, PAUSE_S = 3, 3 * 86400
FRISCH_S = 30 * 86400
KI = re.compile(r"\b(llms?|gpt|large language|(?:language|ai|ml|image|video|speech|embedding|vision|open[- ]weights?) models?|inference|"
                r"chat ?completions?|chatbots?|embeddings?|ai|artificial intelligence|machine learning|openai[- ]compatible|transcri\w*|"
                r"speech[- ]to[- ]text|text[- ]to[- ]speech|tts|image generation|video generation|ocr|rerank\w*)\b", re.I)
API = re.compile(r"\bapis?\b|\bendpoints?\b|free tier|free credits?|\bsdk\b|api key", re.I)   # a news item must be about an API, not about AI in general
STARK = re.compile(r"inference|llm|text generation|image generation|video generation|speech|embedding|transcri|ocr|vision|openai[- ]compatible", re.I)


def tabellen(c):
    c.executescript("""
CREATE TABLE IF NOT EXISTS angebot(id TEXT PRIMARY KEY, art TEXT, name TEXT, url TEXT, beschr TEXT, merkmale TEXT, basis REAL,
  gefunden REAL, angeboten REAL, antwort TEXT, beantwortet REAL);
CREATE TABLE IF NOT EXISTS angebot_lern(merkmal TEXT PRIMARY KEY, ja REAL DEFAULT 0, nein REAL DEFAULT 0);""")


def _host(url):
    return sicher.registrierbar((urllib.parse.urlsplit(url or "").hostname or "").lower())


def bekannt():
    """names and domains of providers the user already has (built-in list and own providers)"""
    namen, hosts = set(), set()
    for pid, v in core.TC.PROVIDERS.items():
        namen |= {str(pid).lower(), str(v[0]).lower()}
        hosts.add(_host(v[1] if len(v) > 1 and isinstance(v[1], str) else ""))
    for pid, v in core.custom().items():
        namen |= {str(pid).lower(), str(v.get("label", "")).lower()}
        hosts.add(_host(v.get("base", "")))
    for info in (getattr(core.TC, "PINFO", {}) or {}).values():
        u = ((info or {}).get("check") or {}).get("url") if isinstance(info, dict) else None
        if u:
            hosts.add(_host(u))
    namen.discard("")
    hosts.discard("")
    return namen, hosts


def _schon_da(name, url, namen, hosts):
    n = re.sub(r"[^a-z0-9 ]", " ", (name or "").lower())
    return _host(url) in hosts or any(len(x) >= 4 and re.search(r"\b%s\b" % re.escape(x), n) for x in namen)


def sammle(c, jetzt=None):
    """new candidates since the last run (first run: the last 14 days) -> number of new candidates"""
    jetzt = jetzt or time.time()
    radar.tabellen(c)
    tabellen(c)
    r = c.execute("SELECT ts FROM radar_state WHERE name='angebote'").fetchone()
    seit = r[0] if r else jetzt - 14 * 86400
    namen, hosts = bekannt()
    neu = 0
    da = {_host(u) for (u,) in c.execute("SELECT url FROM angebot WHERE art='api'")}   # one offer per provider domain
    rows = [("api", "a:" + i, n, u, b, k, a, q, ts, 0) for i, n, u, b, k, a, q, ts in
            c.execute("SELECT id, name, url, beschr, kategorie, auth, quelle, ts FROM api_index WHERE ts>?", (seit,))]
    rows += [("news", "n:" + i, t, l, x, "", "", f, ts, sc) for i, t, l, x, f, ts, sc in
             c.execute("SELECT id, titel, link, text, feed, ts, score FROM nachricht WHERE gratis=1 AND score>0 AND ts>?", (seit,))]
    for art, aid, name, url, beschr, kat, auth, quelle, _ts, score in rows:
        text = " ".join(str(x or "") for x in (name, beschr, kat))
        if not url or not str(url).startswith("https:") or radar.gesperrt(url) or not KI.search(text) or (art == "news" and not API.search(text)) or _schon_da(name, url, namen, hosts):
            continue
        if art == "api":
            if _host(url) in da:
                continue
            da.add(_host(url))
        basis = 0.5 if art == "api" else 0.3 + min(0.2, (score or 0) / 20)     # an API entry is more concrete than a news item
        basis += 0.15 if radar.GRATIS.search(text) else 0
        basis += 0.05 if str(auth or "").lower() in ("", "no", "none", "apikey") else 0
        basis += 0.1 if STARK.search(text) else 0                     # a model API (inference, speech, vision ...) beats AI-adjacent tools
        merk = ["art:" + art, "quelle:" + str(quelle or "")[:40].lower()] + (["kat:" + str(kat).lower()[:30]] if kat else [])
        merk += ["faeh:" + f for f in radar.faehigkeiten_regel(text)]
        cur = c.execute("INSERT OR IGNORE INTO angebot(id, art, name, url, beschr, merkmale, basis, gefunden) VALUES(?,?,?,?,?,?,?,?)",
                        (aid, art, str(name)[:160], str(url)[:500], str(beschr or "")[:400], json.dumps(merk), round(basis, 3), jetzt))
        neu += cur.rowcount
    c.execute("INSERT OR REPLACE INTO radar_state VALUES('angebote',?,?)", (jetzt, json.dumps({"neu": neu})))
    if neu:
        core.ereignis(c, "angebote", "%d new free AI API candidate(s) found" % neu)
    c.commit()
    return neu


def _gelernt(c, merkmale):
    w = [(ja + 1.0) / (ja + nein + 2.0) for m in merkmale for ja, nein in c.execute("SELECT ja, nein FROM angebot_lern WHERE merkmal=?", (m,))]
    return sum(w) / len(w) if w else 0.5


def wert(c, basis, merkmale):
    return basis + (_gelernt(c, merkmale) - 0.5)


def darf(c, jetzt=None):
    """-> (may offer now, reason)"""
    jetzt = jetzt or time.time()
    tabellen(c)
    try:
        n = max(0, min(2, int(core.settings().get("angebote_pro_tag", 2))))
    except (TypeError, ValueError):
        n = 2
    if n == 0:
        return False, "off"
    if c.execute("SELECT COUNT(*) FROM angebot WHERE angeboten>?", (jetzt - 86400,)).fetchone()[0] >= n:
        return False, "daily limit"
    last = c.execute("SELECT MAX(angeboten) FROM angebot").fetchone()[0]
    if last and jetzt - last < ABSTAND_S:
        return False, "too soon"
    ant = c.execute("SELECT antwort, beantwortet FROM angebot WHERE antwort IS NOT NULL ORDER BY beantwortet DESC LIMIT ?", (PAUSE_NEIN,)).fetchall()
    if len(ant) == PAUSE_NEIN and all(a == "nein" for a, _ in ant) and jetzt - ant[0][1] < PAUSE_S:
        return False, "paused after %d no" % PAUSE_NEIN
    return True, "ok"


def naechstes(c, jetzt=None):
    """the one offer to show now, or None; showing it counts against the daily limit"""
    jetzt = jetzt or time.time()
    ok, _ = darf(c, jetzt)
    if not ok:
        return None
    namen, hosts = bekannt()
    best = None
    for aid, art, name, url, beschr, merk, basis, gef in c.execute(
            "SELECT id, art, name, url, beschr, merkmale, basis, gefunden FROM angebot WHERE angeboten IS NULL AND gefunden>?", (jetzt - FRISCH_S,)).fetchall():
        if _schon_da(name, url, namen, hosts):                       # added since it was found
            continue
        w = wert(c, basis, json.loads(merk or "[]"))
        if best is None or w > best[0]:
            best = (w, aid, art, name, url, beschr, gef)
    if not best:
        return None
    c.execute("UPDATE angebot SET angeboten=? WHERE id=?", (jetzt, best[1]))
    c.commit()
    return {"id": best[1], "art": best[2], "name": best[3], "url": best[4], "beschr": best[5], "gefunden": best[6], "wert": round(best[0], 2)}


def antworte(c, aid, antwort, jetzt=None):
    if antwort not in ("ja", "nein"):
        return False
    tabellen(c)
    r = c.execute("SELECT merkmale FROM angebot WHERE id=? AND angeboten IS NOT NULL AND antwort IS NULL", (str(aid),)).fetchone()
    if not r:
        return False
    c.execute("UPDATE angebot SET antwort=?, beantwortet=? WHERE id=?", (antwort, jetzt or time.time(), str(aid)))
    for m in json.loads(r[0] or "[]"):
        c.execute("INSERT OR IGNORE INTO angebot_lern(merkmal) VALUES(?)", (m,))
        c.execute("UPDATE angebot_lern SET %s=%s+1 WHERE merkmal=?" % ((antwort,) * 2), (m,))
    c.commit()
    return True


def stand(c):
    tabellen(c)
    jetzt = time.time()
    ok, grund = darf(c, jetzt)
    return {"kandidaten": c.execute("SELECT COUNT(*) FROM angebot WHERE angeboten IS NULL").fetchone()[0],
            "heute_angeboten": c.execute("SELECT COUNT(*) FROM angebot WHERE angeboten>?", (jetzt - 86400,)).fetchone()[0],
            "ja": c.execute("SELECT COUNT(*) FROM angebot WHERE antwort='ja'").fetchone()[0],
            "nein": c.execute("SELECT COUNT(*) FROM angebot WHERE antwort='nein'").fetchone()[0],
            "darf_jetzt": ok, "grund": grund}
