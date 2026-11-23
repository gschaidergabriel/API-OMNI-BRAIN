"""Shared pieces of the Omnipool team program: model pool, tolerant LLM calls through Omnipool's own proxy (free NVIDIA tokens), file snapshots, gates, logging."""
import ast
import base64
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import iterate as it  # noqa: E402
import team_patch as tp  # noqa: E402

TEAM = os.path.join(it.ROOT, "team")
os.makedirs(TEAM, exist_ok=True)
SKIP = ("ising", "-vl-", "gliner", "embed", "rerank", "safety", "guard")
UI_FILES = ("ui.css", "ui.js", "ui_radar.js", "texte.json", "ui.html")
CODE_FILES = ("server.py", "core.py", "scan.py", "gehirn.py", "radar.py")      # sicher.py / quarantaene.py (the hardening) stay human-only
ALL = UI_FILES + CODE_FILES
ONBOARD = ("Bewerte diese Oberflaeche (Reiter '%s') streng als Design-Reviewer fuer eine Anwendung, die Laien an die Hand nehmen und Profis nicht bevormunden soll. Kriterien: "
           "(1) Weiss ein Erstnutzer in 5 Sekunden, was das ist und was er als Naechstes tun soll? (2) Wird er NICHT erschlagen (wenige Elemente pro Blick, klare Hierarchie)? "
           "(3) Fuehlt sich ein Profi nicht bevormundet (nichts Aufdringliches, schnelle Wege, Dichte moeglich)? (4) Kontrast, Abstaende, Konsistenz, Hochwertigkeit. "
           "Antworte NUR mit JSON {\"score\": Zahl 1-10, \"issues\": [max 4 konkrete, umsetzbare Probleme]}.")


def log(**kw):
    with open(os.path.join(TEAM, "log.jsonl"), "a") as f:
        f.write(json.dumps({"t": round(time.time()), **kw}, ensure_ascii=False) + "\n")


def status(**kw):
    p = os.path.join(TEAM, "STATUS.json")
    try:
        d = json.load(open(p))
    except (OSError, ValueError):
        d = {}
    d.update(kw, t=round(time.time()))
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=1)


def pool():
    import urllib.request
    rq = urllib.request.Request(it.REAL + "/v1/models", headers={"Authorization": "Bearer " + it.real_key()})
    ids = [m["id"] for m in json.load(urllib.request.urlopen(rq, timeout=20))["data"]]
    return [i for i in ids if i.startswith("nvidia/") and not any(s in i for s in SKIP)]


def pick(models, *names):
    """first pool model whose id contains one of the names (order = preference), else None"""
    for n in names:
        for m in models:
            if n in m:
                return m
    return None


def ask(models, prompt, max_tokens=6000, timeout=240):
    """tolerant: try the given models in order until one returns text -> (text, model) or (None, None)"""
    for m in models:
        if not m:
            continue
        try:
            t, route = it.llm(m, [{"role": "user", "content": prompt}], max_tokens, timeout)
            if t and len(t.strip()) > 40:
                return t, m
            log(art="leer", modell=m)
        except Exception as e:  # noqa: BLE001
            log(art="llm_fehler", modell=m, fehler=type(e).__name__)
            time.sleep(3)
    return None, None


def jsonblock(text):
    m = re.findall(r"```(?:json)?\s*\n(.*?)```", text or "", re.S)
    for s in sorted(m, key=len, reverse=True) or [text or ""]:
        try:
            return json.loads(s)
        except ValueError:
            continue
    m = re.search(r"[\[{].*[\]}]", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else None
    except ValueError:
        return None


def read_all(names=ALL):
    return {n: it.rd(n) for n in names}


def write_all(files, only=None):
    for n, s in files.items():
        if only is None or n in only:
            it.wr(n, s)


def syntax(name, s):
    if name.endswith(".py"):
        try:
            ast.parse(s, feature_version=(3, 8))
            return True, ""
        except SyntaxError as e:
            return False, "%s:%s %s" % (name, e.lineno, e.msg)
    ok, why = it.syntax_gate(name, s)
    return ok, "" if ok else "%s: %s" % (name, why)


def tests(py_changed):
    if py_changed:
        return it.tests_ok()
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "tests/test_ui_rules.py"], cwd=it.ROOT, capture_output=True, text=True, timeout=200)
    return r.returncode == 0, r.stdout[-200:]


def judge2(port, tabs=(0, 1, 3)):
    """vision judge with the onboarding criteria -> (average score | None, issues)"""
    import cdp
    c = cdp.Chrome()
    imgs, sc, iss = [], [], []
    try:
        c.goto("http://127.0.0.1:%d/" % port, 2.5)
        os.makedirs(os.path.join(it.IT, "shots"), exist_ok=True)
        for i in tabs:
            c.js("document.querySelectorAll('nav button')[%d].click()" % i)
            time.sleep(1.2)
            imgs.append((i, base64.b64encode(open(c.shot(os.path.join(it.IT, "shots", "t%d.png" % i)), "rb").read()).decode()))
    finally:
        c.close()
    for i, b64 in imgs:
        try:
            txt, _ = it.llm(it.VL, [{"role": "user", "content": [{"type": "text", "text": ONBOARD % it.TABS[i]}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}], 700, 120)
            d = jsonblock(txt)
            sc.append(float(d["score"]))
            iss += ["[%s] %s" % (it.TABS[i], x) for x in d.get("issues", [])[:4]]
        except Exception as e:  # noqa: BLE001
            log(art="judge_fehler", tab=i, fehler=type(e).__name__)
    return (sum(sc) / len(sc) if sc else None), iss
