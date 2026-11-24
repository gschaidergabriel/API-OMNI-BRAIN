"""The trained router needle (26M encoder-decoder, numpy only, ~40-60 ms per request). Needs numpy and the files in <data>/needles/ (router.npz, needle.model), otherwise it does nothing and the rules stay in charge.
Setting needle_router: off | shadow | active (default). active: the needle decides the class of content-classified requests (code/json/de/reason) and falls back to the rules on any error, timeout or load.
shadow: the rules decide and the needle only records what it would have said. Stores counts and labels, never the text of a request."""
import json
import os
import queue
import threading
import time

from . import core

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")           # must be set before numpy is first imported (verfuegbar() does that): 16 BLAS threads on a busy machine turn 50 ms into 3-5 s
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

DIR = os.path.join(core.DATA, "needles")
CLASSES = ("code", "json", "de", "reason")
TOOLS = json.dumps([{"name": "route", "description": "task class of a user message", "parameters": {"klasse": {"type": "string", "description": "code, json, de or reason", "required": True}}}])
ANS = {c: json.dumps([{"arguments": {"klasse": c}, "name": "route"}], separators=(",", ":"), sort_keys=True) for c in CLASSES}
_Q = queue.Queue(maxsize=4)
_L = threading.Lock()
STAT = {"seen": 0, "agree": 0, "skipped_busy": 0, "skipped_full": 0, "error": None, "ms": [], "pairs": {}}
_T = []                                                         # loader thread
_TW = []                                                        # shadow worker thread


def verfuegbar():
    try:
        import numpy  # noqa: F401
    except ImportError:
        return False
    return all(os.path.isfile(os.path.join(DIR, f)) for f in ("router.npz", "needle.model"))


def modus():
    m = core.settings().get("needle_router")
    return m if m in ("off", "shadow") else "active"


_N = []                                                         # the loaded Needle (one per process)
_RUN = threading.Lock()                                         # one forward pass at a time
_BREMSE = [0.0]                                                 # monotonic time until which "active" stays off after a slow pass (machine under load)


def _laden():
    from .needle_rt import Needle
    try:
        n = Needle(os.path.join(DIR, "router.npz"), os.path.join(DIR, "needle.model"))
        for _ in range(3):                                      # warm-up: the first passes pay for BLAS start-up (~2.5 s), requests must not
            n.score("warm up the router", TOOLS, ANS)
        _N.append(n)
    except Exception as e:                                      # noqa: BLE001
        STAT["error"] = "%s: %s" % (type(e).__name__, e)


def _notiere(regel, lab, ms, n):
    with _L:
        STAT["seen"] += 1
        STAT["agree"] += lab == regel
        STAT["ms"] = (STAT["ms"] + [ms])[-50:]
        k = "%s>%s" % (regel, lab)
        STAT["pairs"][k] = STAT["pairs"].get(k, 0) + 1
    try:
        with open(os.path.join(DIR, "schatten.jsonl"), "a") as f:           # labels + timing only
            f.write(json.dumps({"t": int(time.time()), "regel": regel, "needle": lab, "ms": ms, "len": n}) + "\n")
    except OSError:
        pass


def entscheide(text, regel):
    """active mode: -> the needle's class, or None (rules decide). Never raises. Loads the weights in the background on first use."""
    try:
        if modus() != "active" or not text or regel not in CLASSES or time.monotonic() < _BREMSE[0] or not verfuegbar():
            return None
        if not _N:
            if not _T:
                _T.append(threading.Thread(target=_laden, daemon=True, name="needle-laden"))
                _T[0].start()
            return None
        if not _RUN.acquire(timeout=0.3):
            return None
        try:
            t0 = time.perf_counter()
            sc = _N[0].score(text[:2000], TOOLS, ANS)
            ms = int((time.perf_counter() - t0) * 1000)
        finally:
            _RUN.release()
        if ms > 500:
            _BREMSE[0] = time.monotonic() + 30
        lab = max(sc, key=sc.get)
        _notiere(regel, lab, ms, len(text))
        return lab
    except Exception as e:                                      # noqa: BLE001
        STAT["error"] = "%s: %s" % (type(e).__name__, e)
        return None


def _arbeit():
    from . import gehirn
    try:
        os.nice(10)
    except OSError:
        pass
    if not _N:
        _laden()
    if not _N:
        return
    while True:
        text, regel = _Q.get()
        if gehirn.busy():
            STAT["skipped_busy"] += 1
            continue
        try:
            with _RUN:
                t0 = time.perf_counter()
                sc = _N[0].score(text, TOOLS, ANS)
                ms = int((time.perf_counter() - t0) * 1000)
            _notiere(regel, max(sc, key=sc.get), ms, len(text))
        except Exception as e:                                  # noqa: BLE001
            STAT["error"] = "%s: %s" % (type(e).__name__, e)


def beobachte(text, regel):
    """called after the rules decided; never blocks, never raises"""
    try:
        if regel not in CLASSES or modus() != "shadow" or not verfuegbar() or not text:
            return
        if not _TW:
            _TW.append(threading.Thread(target=_arbeit, daemon=True, name="needle-schatten"))
            _TW[0].start()
        _Q.put_nowait((text[:1000], regel))
    except queue.Full:
        STAT["skipped_full"] += 1
    except Exception:                                           # noqa: BLE001
        pass


def stand():
    with _L:
        s = dict(STAT)
    ms = sorted(s.pop("ms"))
    s.update({"available": verfuegbar(), "mode": modus(), "median_ms": ms[len(ms) // 2] if ms else None, "agreement": round(s["agree"] / s["seen"], 3) if s["seen"] else None})
    return s


REL = "https://github.com/gschaidergabriel/API-OMNI-BRAIN/releases/download/needles-v1/"


def installieren():
    """--needles-install: fetch router.npz + needle.model from the GitHub release, verify the sha256 from the release's SHA256SUMS, put them in <data>/needles/. Needs numpy to be of any use."""
    import hashlib
    import urllib.request
    os.makedirs(DIR, exist_ok=True)
    get = lambda n: urllib.request.urlopen(REL + n, timeout=120).read()               # noqa: E731
    sums = {ln.split()[1].lstrip("*"): ln.split()[0] for ln in get("SHA256SUMS").decode().splitlines() if len(ln.split()) == 2}
    for n in ("router.npz", "needle.model"):
        data = get(n)
        if hashlib.sha256(data).hexdigest() != sums.get(n):
            print("checksum mismatch for %s, nothing installed" % n)
            return 1
        with open(os.path.join(DIR, n + ".part"), "wb") as f:
            f.write(data)
        os.replace(os.path.join(DIR, n + ".part"), os.path.join(DIR, n))
        print("ok", n, len(data))
    try:
        import numpy  # noqa: F401
    except ImportError:
        print("note: numpy is not installed here; the router needle stays inactive and the rules decide (the single-file binary includes numpy)")
    return 0


def selbsttest():
    """--needles-test: does the needle load and how fast is it here. 0 = ok"""
    if not verfuegbar():
        print("router needle inactive: needs numpy and router.npz + needle.model in %s (run --needles-install)" % DIR)
        return 1
    t0 = time.perf_counter()
    _laden()
    if not _N:
        print("could not load: %s" % STAT["error"])
        return 1
    print("loaded in %.1f s (includes 3 warm-up passes)" % (time.perf_counter() - t0))
    for txt in ("Fix the bug in this Python function", "Antworte bitte auf Deutsch, wie spaet ist es", "Return a JSON object with name and age", "Why is the sky blue?"):
        t = time.perf_counter()
        sc = _N[0].score(txt, TOOLS, ANS)
        print("%-45s -> %-6s %4d ms" % (txt, max(sc, key=sc.get), (time.perf_counter() - t) * 1000))
    return 0
