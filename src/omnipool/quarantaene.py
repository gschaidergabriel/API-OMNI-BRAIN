"""Quarantine: every file API-OMNI-BRAIN fetches from outside (GitHub, indices, feeds, anything a user asks to inspect) is written to a private folder and scanned by a
sandboxed worker process (own process, no network via a fresh network namespace when the system allows it, no file writes, CPU/memory limits, empty environment).
Anything not 'sauber' is wiped and deleted whether the user likes it or not - there is no release switch anywhere - and a popup message is queued for the user.
Honest label: the sandbox isolates the scanner, which only reads bytes; the scanner itself is signatures + heuristics (scan.py)."""
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import threading
import time

from . import core, scan, sicher

DIR = os.path.join(core.DATA, "quarantaene")
_UNSHARE = {}
_SLOTS = threading.BoundedSemaphore(2)               # at most two scanner processes at once: the service runs under a memory cap


def _netz_aus():
    """can a fresh network namespace be created without root? (checked once)"""
    if "ok" not in _UNSHARE:
        try:
            _UNSHARE["ok"] = bool(shutil.which("unshare")) and subprocess.run(["unshare", "-rn", "true"], capture_output=True, timeout=5).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            _UNSHARE["ok"] = False
    return _UNSHARE["ok"]


def _limits():
    os.setsid()
    for r, v in ((resource.RLIMIT_CPU, 20), (resource.RLIMIT_AS, 1 << 30), (resource.RLIMIT_FSIZE, (64 << 20) if getattr(sys, "frozen", False) else 0), (resource.RLIMIT_NOFILE, 64), (resource.RLIMIT_CORE, 0)):
        resource.setrlimit(r, (v, v))


def sandbox_scan(pfad):
    """-> verdict dict (fail closed: any problem with the sandbox counts as 'verdaechtig')"""
    from .__main__ import selbst
    cmd = (["unshare", "-rn"] if _netz_aus() else []) + selbst() + ["--scan-worker", pfad]
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "PYTHONNOUSERSITE": "1", "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": os.path.dirname(os.path.dirname(os.path.abspath(__file__)))}
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=40, env=env, cwd="/", preexec_fn=_limits, stdin=subprocess.DEVNULL)
        v = json.loads(r.stdout.decode("utf-8", "replace") or "null")
        if not isinstance(v, dict) or v.get("urteil") not in ("sauber", "verdaechtig", "schadhaft"):
            raise ValueError
    except (OSError, subprocess.TimeoutExpired, ValueError) as e:
        grund = 'Timeout' if isinstance(e, subprocess.TimeoutExpired) else ('Scanner finished with code %s' % r.returncode if "r" in dir() and getattr(r, "returncode", 0) else type(e).__name__)
        v = {"urteil": "verdaechtig", "punkte": 5, "art": "fehler", "treffer": [{"id": "sandbox", "text": 'Sandbox check failed (%s), not approved as a precaution' % grund, "zeile": 0}]}
    v["netz_isoliert"] = _netz_aus()
    return v


def tabelle(c):
    c.execute("CREATE TABLE IF NOT EXISTS meldung(id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, art TEXT, titel TEXT, text TEXT, quelle TEXT, gelesen INT DEFAULT 0)")


def melde(c, art, titel, text, quelle=""):
    """queue a popup message (one per source and kind per day) and show a desktop notification when possible"""
    tabelle(c)
    if c.execute("SELECT 1 FROM meldung WHERE quelle=? AND art=? AND ts>?", (quelle, art, time.time() - 86400)).fetchone():
        return False
    c.execute("INSERT INTO meldung(ts, art, titel, text, quelle) VALUES(?,?,?,?,?)", (time.time(), art, titel[:120], text[:700], quelle[:300]))
    core.ereignis(c, art, "%s: %s" % (titel, quelle))
    c.commit()
    if os.environ.get("OMNIPOOL_MELDEN") != "0" and shutil.which("notify-send"):
        try:
            subprocess.Popen(["notify-send", "-u", "critical", "-a", "API-OMNI-BRAIN", titel[:80], text[:200]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass
    return True


def offene(c):
    tabelle(c)
    return [dict(zip(("id", "ts", "art", "titel", "text", "quelle"), r)) for r in c.execute("SELECT id, ts, art, titel, text, quelle FROM meldung WHERE gelesen=0 ORDER BY id")]


def gelesen(c, ids):
    tabelle(c)
    for i in ids:
        c.execute("UPDATE meldung SET gelesen=1 WHERE id=?", (int(i),))
    c.commit()


def vernichte(pfad):
    """overwrite with zeros, then delete"""
    try:
        n = os.path.getsize(pfad)
        with open(pfad, "r+b") as f:
            f.write(b"\0" * n)
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    try:
        os.remove(pfad)
    except OSError:
        pass


def scanne_bytes(body, name=""):
    """quarantine copy (private folder, no exec bit) -> sandbox verdict -> the copy is wiped and deleted in every case; no database access, safe in worker threads"""
    os.makedirs(DIR, mode=0o700, exist_ok=True)
    ext = os.path.splitext(name)[1].lower()
    ext = ext if re.fullmatch(r"\.[a-z0-9]{1,6}", ext) else ".q"                  # the extension tells the scanner what kind of file this is
    pfad = os.path.join(DIR, "%s-%d%s" % (hashlib.sha256(body).hexdigest()[:20], threading.get_ident(), ext))
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(body)
    try:
        with _SLOTS:
            return sandbox_scan(pfad)
    finally:
        vernichte(pfad)


def befund(c, v, name, quelle, still=False):
    """a verdict that is not 'sauber': popup (soft findings of silent sources are only logged, hard ones always pop up). Nothing is ever released."""
    gruende = "; ".join("%s (line %s)" % (t["text"], t["zeile"]) if t.get("zeile") else t["text"] for t in v["treffer"][:4])
    if not still or v["urteil"] == "schadhaft":
        melde(c, "quarantaene", 'File not approved and deleted',
              "Unfortunately, the file '%s' from %s cannot be approved (%s) and was therefore deleted - regardless of whether you wanted it. Finding: %s" % (name, quelle, v["urteil"], gruende), quelle + "|" + name)
    else:
        core.ereignis(c, "quarantaene_still", '%s from %s discarded: %s' % (name, quelle, gruende[:120]))
        c.commit()


def pruefe_bytes(c, body, name, quelle, still=False):
    """the one gate for fetched content -> {ok, urteil, treffer, geloescht}; ok=True only when the sandbox found nothing"""
    v = scanne_bytes(body, name)
    if v["urteil"] == "sauber":
        return {"ok": True, "urteil": "sauber", "treffer": v.get("treffer", []), "netz_isoliert": v["netz_isoliert"]}
    befund(c, v, name, quelle, still)
    return {"ok": False, "urteil": v["urteil"], "treffer": v["treffer"], "geloescht": True, "netz_isoliert": v["netz_isoliert"]}


def laden(c, url, name=None, still=False, max_bytes=3 << 20, accept="*/*"):
    """fetch over the hardened client, then through the quarantine. -> {ok, daten (bytes) | fehler | urteil...}"""
    name = name or url.rsplit("/", 1)[-1] or "datei"
    try:
        st, body, _h = sicher.hole(url, timeout=25, max_bytes=max_bytes, accept=accept)
    except ValueError as e:
        return {"ok": False, "fehler": str(e)}
    if st != 200:
        return {"ok": False, "fehler": "HTTP %d" % st}
    r = pruefe_bytes(c, body, name, url, still)
    if r["ok"]:
        r["daten"] = body
    return r


def github_roh(url):
    """github.com/<o>/<r>/blob/<ref>/<path> -> raw.githubusercontent.com/<o>/<r>/<ref>/<path>; raw links and other hosts stay as they are"""
    m = re.match(r"^https://github\.com/([^/]+)/([^/]+)/blob/(.+)$", url)
    return "https://raw.githubusercontent.com/%s/%s/%s" % m.groups() if m else url
