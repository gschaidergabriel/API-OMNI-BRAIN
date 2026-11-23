"""API-OMNI-BRAIN core: tests every free API key, lists the models each provider serves, probes them per class (code, json, de, reason, long),
and ranks them for a task. Keys are read in place (never copied, never printed: slot name + 8-char hash only). Own store: ~/.local/share/omnipool/omnipool.db.
Kill switch: file ~/.cache/omnipool/AUS. Fail-open: a failing probe/provider never stops the run."""
import fcntl
import json
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pkgutil

HERE = os.path.dirname(os.path.abspath(__file__))
HOME = os.path.expanduser("~")
DATA = os.environ.get("OMNIPOOL_HOME", os.path.join(HOME, ".local", "share", "omnipool"))


def res(name):
    """bytes of a packaged file: from disk, from inside the zipapp, or from the PyInstaller bundle (same call everywhere)"""
    return pkgutil.get_data("omnipool", name)


if not os.environ.get("TOKEN_PROVIDERS") and not os.path.exists(os.path.join(HERE, "vendor", "providers_free.json")):
    os.makedirs(DATA, mode=0o700, exist_ok=True)                    # zipapp / bundle: the provider list is not a plain file, so it is unpacked once
    os.environ["TOKEN_PROVIDERS"] = os.path.join(DATA, "providers_free.json")
    with open(os.environ["TOKEN_PROVIDERS"], "wb") as _f:
        _f.write(res("vendor/providers_free.json"))
sys.path.insert(0, os.path.join(HERE, "vendor"))
import keypool as KP  # noqa: E402
import token_check as TC  # noqa: E402
from . import anbieter as AN  # noqa: E402

STATE = os.environ.get("OMNIPOOL_STATE", os.path.join(HOME, ".cache", "omnipool"))
DB = os.path.join(DATA, "omnipool.db")
CACHE = os.path.join(STATE, "katalog.json")
UNIFIED = os.path.join(HOME, ".local", "share", "agentzero", "unified.db")
EVENTS = os.path.join(HOME, ".cache", "mund_say", "modellwahl_events.jsonl")   # FranKenstein organ "modellwahl" learns from real outcomes
JUDGE = ("nvidia", "nvidia/nemotron-3-ultra-550b-a55b")                         # strong NVIDIA model: judge and categoriser
PRIOR_K = 6.0                                                   # pseudo-observations; measured: k=2 at the class mean even RAISED a lucky n=1 model from 15 % to 24 % of first places
KLASSEN = ("code", "json", "de", "reason", "long", "tool")
TASK = {"code": "code", "json": "json", "de": "speak_de", "reason": "generic", "long": "generic", "tool": "generic"}
TOOL = [{"type": "function", "function": {"name": "hole_wert", "description": 'Reads a value from storage.',
                                         "parameters": {"type": "object", "properties": {"schluessel": {"type": "string"}}, "required": ["schluessel"]}}}]


def _tool_ok(msg):
    try:
        tc = msg["tool_calls"][0]["function"]
        return tc["name"] == "hole_wert" and json.loads(tc["arguments"]).get("schluessel") == "alpha"
    except (TypeError, KeyError, IndexError, ValueError, AttributeError):
        return False
def token_hash(t):
    return TC.hash8(t)


def custom():
    """providers onboarded at run time (data, see anbieter.py) that serve something we can use for free-form routing"""
    return AN.liste()


SKIP = re.compile(r"embed|rerank|guard|safety|whisper|tts|orpheus|vision|image|audio|reward|parse|moderat|ocr|transcri|diffus|flux|clip|\bvl\b|-vl-|"
                  r"retriev|translat|nv-", re.I)
PYTHON = shutil.which("python3") or "/usr/bin/python3"


SETTINGS = os.path.join(DATA, "settings.json")
SHARED_KEYS = os.path.join(HOME, ".last-resort", "keys.env")        # on a FranKenstein host the free-key pool already lives here
DEFAULTS = {"port": 8799, "lauf_min": 30, "max_modelle": 8, "keys_file": "", "melden": True, "app_key": "", "slot_aus": [],
            "harness": {"claude_code": {"an": False, "klasse": "auto"}, "hermes": {"an": False, "klasse": "auto"}, "grokbot": {"an": False, "klasse": "auto"},
                        "crush": {"an": False, "klasse": "code"}, "aider": {"an": False, "klasse": "code"}, "openai": {"an": True, "klasse": "auto"}}}


def settings():
    try:
        d = json.load(open(SETTINGS))
    except (OSError, ValueError):
        d = {}
    out = {**DEFAULTS, **d, "harness": {**DEFAULTS["harness"], **(d.get("harness") or {})}}
    if not out["app_key"]:
        out["app_key"] = "op-" + os.urandom(16).hex()
        if not d.get("slot_aus") and os.path.exists(SHARED_KEYS):
            out["slot_aus"] = ["GROQ_API_KEY", "GROQ2_API_KEY"]         # those two belong to the data agents of the shared pool, not to routing
        save_settings(out)
    return out


def save_settings(d):
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    fd = os.open(SETTINGS + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(d, f, indent=1)
    os.replace(SETTINGS + ".tmp", SETTINGS)


def keys_file():
    kf = settings()["keys_file"] or (SHARED_KEYS if os.path.exists(SHARED_KEYS) else os.path.join(DATA, "keys.env"))
    TC.KEYS_FILE = KP.KEYS_FILE = kf
    KP.DEAD_FILE = os.path.join(os.path.dirname(kf), "dead-keys.json")
    return kf


def aus():
    return os.environ.get("OMNIPOOL") == "aus" or os.path.exists(os.path.join(STATE, "AUS"))


def db():
    os.makedirs(DATA, mode=0o700, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA busy_timeout=30000")
    c.executescript("""
CREATE TABLE IF NOT EXISTS key(slot TEXT PRIMARY KEY, provider TEXT, hash8 TEXT, status TEXT, n_models INT, first_seen REAL, checked REAL);
CREATE TABLE IF NOT EXISTS modell(provider TEXT, model TEXT, first_seen REAL, probed REAL, n_try INT DEFAULT 0, status TEXT DEFAULT 'neu', gone INT DEFAULT 0,
  PRIMARY KEY(provider, model));
CREATE TABLE IF NOT EXISTS klasse(provider TEXT, model TEXT, klasse TEXT, ok_n INT DEFAULT 0, n INT DEFAULT 0, lat_sum REAL DEFAULT 0, last_ts REAL,
  PRIMARY KEY(provider, model, klasse));
CREATE TABLE IF NOT EXISTS sonde(ts REAL, provider TEXT, model TEXT, klasse TEXT, ok INT, lat REAL, status INT, judge REAL);
CREATE TABLE IF NOT EXISTS ereignis(ts REAL, art TEXT, text TEXT);
CREATE TABLE IF NOT EXISTS anfrage(ts REAL, app TEXT, klasse TEXT, provider TEXT, model TEXT, ok INT, lat REAL, tin INT, tout INT, status INT);""")
    if not any(r[1] == "faehigkeit" for r in c.execute("PRAGMA table_info(modell)")):
        c.execute("ALTER TABLE modell ADD COLUMN faehigkeit TEXT")
    return c


def ereignis(c, art, text):
    c.execute("INSERT INTO ereignis VALUES(?,?,?)", (time.time(), art, text[:300]))


# ------------------------------------------------------------------ keys + discovery
def scan_keys(c):
    """one read-only check per free-provider slot -> {provider: {"slots": [ok slots], "models": set}}; new slots are logged as events"""
    keys_file()
    vals, out = TC._vault_values(), {}
    for it in TC.vault_items():
        p, slot = it["provider"], it["slot"]
        if p not in TC.FREE:
            continue
        r = TC.check(p, vals[slot])
        st = "ok" if r.get("ok") else "limit" if r.get("status") == 429 else "invalid" if r.get("status") in (401, 402, 403) else "unknown"
        old = c.execute("SELECT first_seen FROM key WHERE slot=?", (slot,)).fetchone()
        if not old:
            ereignis(c, "neuer_key", '%s %s hash %s status %s, %d models' % (p, slot, it["hash8"], st, len(r.get("models") or [])))
        c.execute("INSERT INTO key VALUES(?,?,?,?,?,?,?) ON CONFLICT(slot) DO UPDATE SET provider=?,hash8=?,status=?,n_models=?,checked=?",
                  (slot, p, it["hash8"], st, len(r.get("models") or []), old[0] if old else time.time(), time.time(), p, it["hash8"], st,
                   len(r.get("models") or []), time.time()))
        d = out.setdefault(p, {"slots": [], "models": set()})
        if st in ("ok", "limit"):
            d["slots"].append(slot)
        d["models"].update(r.get("models") or [])
    for pid, pr in custom().items():
        for slot, tok in AN.tokens(pid):
            r = AN.check(pr, tok)
            st = "ok" if r["ok"] else "limit" if r["status"] == 429 else "invalid" if r["status"] in (401, 402, 403) else "unknown"
            old = c.execute("SELECT first_seen FROM key WHERE slot=?", (slot,)).fetchone()
            if not old:
                ereignis(c, "neuer_key", '%s %s hash %s status %s, %d models (own provider)' % (pid, slot, token_hash(tok), st, len(r["models"])))
            c.execute("INSERT INTO key VALUES(?,?,?,?,?,?,?) ON CONFLICT(slot) DO UPDATE SET provider=?,hash8=?,status=?,n_models=?,checked=?",
                      (slot, pid, token_hash(tok), st, len(r["models"]), old[0] if old else time.time(), time.time(), pid, token_hash(tok), st, len(r["models"]), time.time()))
            d = out.setdefault(pid, {"slots": [], "models": set()})
            if st in ("ok", "limit"):
                d["slots"].append(slot)
            d["models"].update(r["models"])
    c.commit()
    return out


def entdecke(c, found):
    """diff the served model lists against the catalogue: new -> candidate, vanished -> gone counter"""
    now = time.time()
    for p, d in found.items():
        ids = {m for m in d["models"] if p != "openrouter" or m.endswith(":free")}
        if not ids:
            continue
        known = {m: g for m, g in c.execute("SELECT model, gone FROM modell WHERE provider=?", (p,))}
        new = ids - set(known)
        for m in new:
            c.execute("INSERT INTO modell(provider, model, first_seen, faehigkeit) VALUES(?,?,?,?)", (p, m, now, AN.infer(m)))
        if new:
            ereignis(c, "neue_modelle", '%s: %d new (e.g. %s)' % (p, len(new), sorted(new)[0]))
        for m in set(known) - ids:
            c.execute("UPDATE modell SET gone=gone+1 WHERE provider=? AND model=?", (p, m))
        for m in ids & set(known):
            if known[m]:
                c.execute("UPDATE modell SET gone=0 WHERE provider=? AND model=?", (p, m))
    c.commit()


# ------------------------------------------------------------------ calls
def chat_url(p):
    cp = custom().get(p)
    if cp:
        return (cp["base"].rstrip("/") + cp["chat_path"]) if cp.get("chat_path") else None
    spec = (TC.PINFO.get(p) or {}).get("check") or {}
    u = spec.get("url") or ""
    if spec.get("type") == "chat1":
        return u
    return u.rsplit("/models", 1)[0] + "/chat/completions" if spec.get("type") in ("openai_models", "openrouter") else None


def auth_kopf(p, token):
    cp = custom().get(p)
    return AN.kopf(cp, token) if cp else {"Authorization": "Bearer " + token}


def chat(p, model, prompt, token, max_tokens=900, timeout=90, extra=None, raw=False):
    """-> (http status, text, seconds); raw=True: the message dict instead of the text (tool calls)"""
    url = chat_url(p)
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens, **(extra or {})}).encode()
    rq = urllib.request.Request(url, body, {**auth_kopf(p, token), "Content-Type": "application/json", "User-Agent": "API-OMNI-BRAIN/1.0"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(rq, timeout=timeout) as r:
            js = json.loads(r.read().decode())
            msg = js["choices"][0]["message"]
            return 200, (msg if raw else (msg.get("content") or "")), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, "", time.time() - t0
    except Exception:  # noqa: BLE001
        return 0, "", time.time() - t0


# ------------------------------------------------------------------ probes (deterministic checks)
def _code_ok(text):
    m = re.search(r"```(?:python)?\n(.*?)```", text, re.S)
    code = m.group(1) if m else text
    if re.search(r"\b(os|sys|subprocess|socket|shutil|ctypes|requests|urllib)\b|__import__|\bexec\b|\beval\b|\bopen\s*\(|input\s*\(", code):
        return False
    prog = code + "\nassert fib(0) == 0 and fib(1) == 1 and fib(10) == 55 and fib(20) == 6765\n"

    def lim():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
        resource.setrlimit(resource.RLIMIT_AS, (512 << 20, 512 << 20))
    try:
        r = subprocess.run([PYTHON, "-I", "-c", prog], capture_output=True, timeout=10, cwd="/tmp", preexec_fn=lim)
        return r.returncode == 0
    except Exception:  # noqa: BLE001
        return False


def _json_ok(text):
    t = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        d = json.loads(t)
    except ValueError:
        return False
    return isinstance(d, dict) and d.get("stadt") == "Wien" and isinstance(d.get("einwohner_mio"), (int, float)) and 1.5 <= d["einwohner_mio"] <= 2.3 \
        and isinstance(d.get("sprachen"), list) and len(d["sprachen"]) == 2 and all(isinstance(s, str) for s in d["sprachen"])


def _de_heur(text):
    w = [x.lower() for x in re.findall(r"[A-Za-zÄÖÜäöüß]+", text)]
    de = sum(x in {"der", "die", "das", "und", "ist", "ein", "eine", "zu", "von", "mit", "für", "auf", "nicht", "den", "dem", "wird", "werden", "sich"} for x in w)
    en = sum(x in {"the", "and", "is", "of", "to", "that", "which"} for x in w)
    return 12 <= len(w) <= 140 and de >= 3 and en <= 1


def _reason_ok(text):
    return {n for n in ("anna", "ben", "cem", "dora") if re.search(r"\b%s\b" % n, text.lower())} == {"ben"}


FILL = "\n".join("Notiz %d: Der Wert von Eintrag %d ist %d." % (i, i, i * 7 % 97) for i in range(1, 160)).split("\n")
FILL.insert(80, "WICHTIG: Der Geheimcode lautet KIRSCHE-4711.")
PROBES = {
    "code": ("Write a Python function fib(n) returning the n-th Fibonacci number (fib(0)=0, fib(1)=1). Reply with only the code in one ```python block.", _code_ok),
    "json": ('Gib NUR ein JSON-Objekt aus (kein Text drumherum) mit den Schlüsseln "stadt" (String, Wert "Wien"), "einwohner_mio" (Zahl, ungefähr 1.9) und '
             '"sprachen" (Liste mit genau 2 Strings).', _json_ok),
    "de": ("Erkläre in genau zwei deutschen Sätzen, was ein Load-Balancer ist.", _de_heur),
    "reason": ("Anna ist älter als Ben. Ben ist älter als Cem. Dora ist jünger als Cem. Wer ist der Zweitälteste? Antworte nur mit dem Namen.", _reason_ok),
    "long": ("\n".join(FILL) + "\n\nWie lautet der Geheimcode? Antworte nur mit dem Code.", lambda t: "KIRSCHE-4711" in t),
    "tool": ("Rufe das Werkzeug hole_wert mit schluessel=alpha auf.", _tool_ok),
}


def judge_de(c, tokens, text):
    """the strong NVIDIA model scores a German answer 0..10 (None if it cannot be reached)"""
    for tok in tokens:
        st, ans, _ = chat(JUDGE[0], JUDGE[1], 'Bewerte diese Antwort auf "Erkläre in genau zwei deutschen Sätzen, was ein Load-Balancer ist." nach korrektem Deutsch, '
                          'Fachlichkeit und genau zwei Sätzen. Antworte NUR mit JSON {"score": 0-10}.\n\nAntwort:\n' + text[:1200], tok, 300, 90)
        m = re.search(r'"score"\s*:\s*(\d+(?:\.\d+)?)', ans)
        if st == 200 and m:
            return float(m.group(1))
        if st != 429:
            break
    return None


def sonde_modell(c, p, model, tokens, melden=True):
    """all probes for one model; -> 'ok' | 'nicht_verfuegbar' | 'limit' | 'fehler'"""
    ok_any = False
    for kl in KLASSEN:
        prompt, check = PROBES[kl]
        st, txt, lat = 0, "", 0.0
        for tok in random.sample(tokens, min(2, len(tokens))):          # a second key only if the first is rate-limited
            st, txt, lat = chat(p, model, prompt, tok, timeout=50, extra={"tools": TOOL, "tool_choice": "auto"} if kl == "tool" else None, raw=(kl == "tool"))
            if st != 429:
                break
        if st in (404, 410):
            c.execute("UPDATE modell SET status='nicht_verfuegbar', probed=?, n_try=n_try+1 WHERE provider=? AND model=?", (time.time(), p, model))
            return "nicht_verfuegbar"
        if st == 429:
            return "limit"
        if st in (401, 403) or st == 0 or st >= 500:
            c.execute("UPDATE modell SET status='fehler', probed=?, n_try=n_try+1 WHERE provider=? AND model=?", (time.time(), p, model))
            return "fehler"
        ok, jd = (st == 200 and bool(txt) and check(txt)), None
        if kl == "de" and ok:
            jd = judge_de(c, [t for t in tokens_of(JUDGE[0])], txt)
            ok = jd is None or jd >= 6
        ok_any = ok_any or ok
        c.execute("INSERT INTO sonde VALUES(?,?,?,?,?,?,?,?)", (time.time(), p, model, kl, int(ok), lat, st, jd))
        c.execute("INSERT INTO klasse(provider, model, klasse, ok_n, n, lat_sum, last_ts) VALUES(?,?,?,?,1,?,?) ON CONFLICT(provider, model, klasse) DO UPDATE SET "
                  "ok_n=ok_n+?, n=n+1, lat_sum=lat_sum+?, last_ts=?", (p, model, kl, int(ok), lat, time.time(), int(ok), lat, time.time()))
        c.commit()                                     # short write locks: the proxy and the UI write to the same store while probes run
        if melden:
            melde(TASK[kl], p, model, ok, lat)
    c.execute("UPDATE modell SET status=?, probed=?, n_try=n_try+1 WHERE provider=? AND model=?", ("ok" if ok_any else "keine_klasse", time.time(), p, model))
    return "ok"


def tokens_of(p):
    cp = custom().get(p)
    if cp:
        return [v for s, v in AN.tokens(p) if s not in set(settings()["slot_aus"])]
    keys_file()
    vals, aus_ = TC._vault_values(), set(settings()["slot_aus"])
    dead = KP.dead_slots(vals)
    return [vals[s] for s in KP.names_of(p, vals) if vals.get(s) and s not in aus_ and s not in dead]


def melde(task, p, model, ok, lat):
    """real, machine-checked outcome -> FranKenstein organ "modellwahl" (only where that host exists; numbers only)"""
    if not os.path.isdir(os.path.dirname(EVENTS)) or os.path.exists(os.path.join(STATE, "MELDEN_AUS")) or os.environ.get("OMNIPOOL_MELDEN") == "0":
        return
    try:
        with open(EVENTS, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "task": task, "p": p, "m": model, "ok": int(ok), "ms": int(lat * 1000), "src": "omnipool"}) + "\n")
    except OSError:
        pass


# ------------------------------------------------------------------ run, rank, status
def lauf(max_modelle=8):
    """scan keys, discover models, probe up to max_modelle (never probed first, then the oldest) -> summary dict"""
    if aus():
        return {"aus": True}
    os.makedirs(STATE, mode=0o700, exist_ok=True)
    lock = open(os.path.join(STATE, "lauf.lock"), "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return {"belegt": True}
    c = db()
    found = scan_keys(c)
    entdecke(c, found)
    ziele = []
    for p, d in found.items():
        if d["slots"] and chat_url(p):
            ziele += [(p, m) for (m,) in c.execute("SELECT model FROM modell WHERE provider=? AND gone<3 AND status!='nicht_verfuegbar' AND COALESCE(faehigkeit,'chat')='chat' ORDER BY COALESCE(probed,0)", (p,))]
    prio = {"nvidia": 0, "groq": 1, "openrouter": 2, "zai": 3}
    ziele.sort(key=lambda x: (c.execute("SELECT COALESCE(probed,0) FROM modell WHERE provider=? AND model=?", x).fetchone()[0] > 0, prio.get(x[0], 9)))
    conf = [pm for pm in bestaetigung(c, 4) if pm[0] in found and found[pm[0]]["slots"]]
    ziele = conf + [z for z in ziele if z not in conf]            # confirmation probes first, then unseen models, then the oldest
    res, limit = {}, set()
    from concurrent.futures import ThreadPoolExecutor

    def eins(pm):
        p, m = pm
        if p in limit:
            return pm, "uebersprungen"
        cc = db()
        try:
            r = sonde_modell(cc, p, m, tokens_of(p))
            cc.commit()
        finally:
            cc.close()
        if r == "limit":
            limit.add(p)
        return pm, r
    with ThreadPoolExecutor(max_workers=3) as ex:
        for (p, m), r in ex.map(eins, ziele[:max_modelle]):
            res[p + "/" + m] = r
    out = {"ts": time.time(), "keys": {p: len(d["slots"]) for p, d in found.items()}, "geprobt": res}
    ereignis(c, "lauf", json.dumps({"geprobt": len(res), "keys": out["keys"]}))
    c.commit()
    schreibe_cache(c)
    spiegel(c, out)
    return out


def rangfolge(c, klasse, anbieter=None, n=5):
    """Thompson sample over a shrunk success rate per class minus a small latency cost; -> [(provider, model, p, tries, mean seconds)].
    Shrinkage: every model starts with PRIOR_K pseudo-observations at the class average, so one lucky probe (n=1) no longer outranks a model with a record."""
    rows = c.execute("SELECT k.provider, k.model, k.ok_n, k.n, k.lat_sum FROM klasse k JOIN modell m USING(provider, model) WHERE k.klasse=? AND m.gone<3 "
                     "AND m.status NOT IN ('nicht_verfuegbar', 'keine_klasse') AND COALESCE(m.faehigkeit,'chat')='chat'", (klasse,)).fetchall()
    tot_n = sum(r[3] for r in rows)
    p0 = min(0.8, max(0.2, sum(r[2] for r in rows) / tot_n)) if tot_n else 0.5
    a0, b0 = PRIOR_K * p0 * 0.85, PRIOR_K * (1 - p0 * 0.85)        # pessimistic prior: an unproven model has to earn its rank
    sc = []
    for p, m, ok, nn, ls in rows:
        if anbieter and p != anbieter:
            continue
        lat = ls / max(nn, 1)
        sc.append((random.betavariate(ok + a0, nn - ok + b0) - 0.03 * min(lat, 60) ** 0.5, p, m, (ok + a0) / (nn + PRIOR_K), nn, lat))
    return [(p, m, round(pr, 3), nn, round(lat, 1)) for _s, p, m, pr, nn, lat in sorted(sc, reverse=True)[:n]]


def bestaetigung(c, n=4, min_n=3):
    """promising models with too little evidence (fewer than min_n probes in a class they lead): probed again before real requests rely on them -> [(provider, model)]"""
    out = []
    for k in KLASSEN:
        rows = c.execute("SELECT k.provider, k.model, k.ok_n, k.n FROM klasse k JOIN modell m USING(provider, model) WHERE k.klasse=? AND m.gone<3 AND m.status NOT IN ('nicht_verfuegbar','keine_klasse','fehler') "
                         "AND COALESCE(m.faehigkeit,'chat')='chat'", (k,)).fetchall()
        for p, m, ok, nn in sorted(rows, key=lambda r: -(r[2] + 1) / (r[3] + 2))[:3]:
            if nn < min_n and (p, m) not in out and tokens_of(p):
                out.append((p, m))
    return out[:n]


def schreibe_cache(c):
    d = {"ts": time.time(), "keys": [dict(zip(("slot", "provider", "hash8", "status", "n_models", "checked"), r))
                                      for r in c.execute("SELECT slot, provider, hash8, status, n_models, checked FROM key ORDER BY provider, slot")],
         "wahl": {k: rangfolge(c, k, None, 6) for k in KLASSEN}, "modelle": c.execute("SELECT COUNT(*) FROM modell").fetchone()[0],
         "geprobt": c.execute("SELECT COUNT(*) FROM modell WHERE n_try>0").fetchone()[0]}
    with open(CACHE + ".tmp", "w") as f:
        json.dump(d, f)
    os.replace(CACHE + ".tmp", CACHE)


def spiegel(c, out):
    """optional mirror into the FranKenstein unified.db (organ registry + one row per run); silently skipped where the host does not exist"""
    if not os.path.exists(UNIFIED):
        return
    try:
        u = sqlite3.connect(UNIFIED, timeout=5)
        u.execute("CREATE TABLE IF NOT EXISTS omnipool_lauf(ts REAL, json TEXT)")
        u.execute("INSERT INTO omnipool_lauf VALUES(?,?)", (out["ts"], json.dumps({"keys": out["keys"], "geprobt": len(out["geprobt"])})))
        u.execute("INSERT OR IGNORE INTO organ_registry(organ_id, store_path, live, mode, registered_at, note) VALUES('omnipool', ?, 1, 'active', ?, "
                  "'API-OMNI-BRAIN: Keys testen, Modelle sondieren, Klassen waehlen (Gabriel 2026-11-23)')", (DB, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        u.commit()
        u.close()
    except sqlite3.Error:
        pass


def status():
    c = db()
    k = c.execute("SELECT provider, status, COUNT(*) FROM key GROUP BY 1, 2").fetchall()
    z = ["Keys: " + (", ".join("%s %s x%d" % r for r in k) or 'no scan yet'),
         'Models: %d in the catalog, %d tested' % (c.execute("SELECT COUNT(*) FROM modell").fetchone()[0], c.execute("SELECT COUNT(*) FROM modell WHERE n_try>0").fetchone()[0])]
    for kl in KLASSEN:
        top = rangfolge(c, kl, None, 3)
        z.append("  %-6s %s" % (kl, ", ".join("%s/%s p=%.2f n=%d" % (p, m.split("/")[-1][:24], pr, nn) for p, m, pr, nn, _l in top) or "-"))
    return "\n".join(z)
