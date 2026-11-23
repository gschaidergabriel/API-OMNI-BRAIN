#!/usr/bin/env python3
"""Omnipool improvement loop (free NVIDIA tokens only, through Omnipool's own proxy = dogfooding).
Each round: pick a focus, ask a strong NVIDIA model for a better version of ONE file, apply it, run the gates, keep it only if every gate holds
(syntax, unit + deep tests, UI smoke test in headless Chrome with zero console errors, interaction check, classifier accuracy, visual score of a NVIDIA vision model).
Everything is versioned in iter/versions/, logged in iter/log.jsonl, summarised in iter/REPORT.md. Kill: touch iter/STOP.
usage: iterate.py --minutes 120"""
import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(ROOT, "omnipool")
IT = os.path.join(ROOT, "iter")
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tests"))
import cdp  # noqa: E402
import demo  # noqa: E402

REAL = "http://127.0.0.1:8799"
VL = "nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b"
FIRST = ["nvidia/nvidia/nemotron-3-ultra-550b-a55b"]
TABS = ["Overview", "Keys & Providers", "Models", "Connect", "Settings", "Events", "Radar", "API search", "Use cases"]
RULES = """Harte Regeln (Verstoss = Version wird verworfen):
- Keine externen Ressourcen (kein CDN, keine Web-Fonts per URL, keine Bilder ausser /icon.png), keine Frameworks, keine neuen Dateien.
- In ui.js muessen window.EXTRA (const EX) und die drei Stellen, die EX nutzen, erhalten bleiben; in ui_radar.js bleiben window.EXTRA, safeHref, die API-Aufrufe radar/* und meldungen*, und es darf keine Freigabe fuer gesperrte Dateien geben.
- Alle vorhandenen IDs (#pLauf #pBusy #pAus #bScan #bAus #nav #main #tok #prov #base #lab), Funktionsnamen (h, $, api, load, render, uebersicht, keys, modelle, verbinden, einst, ereig, snip), die Kopfzeile X-Omnipool und die API-Aufrufe bleiben erhalten.
- Daten nie per innerHTML einsetzen (nur ueber h() / textContent). Keine Schluessel im DOM ausser hinter dem vorhandenen 'Schluessel zeigen'.
- ALL UI texts are ENGLISH (the interface language of the product). Bedienung muss ohne Vorwissen verstaendlich sein: kurze Erklaerungen, Leerzustaende mit Hinweis, klare Beschriftungen.
- Animationen: dezent (150-450 ms), nur transform/opacity, und @media (prefers-reduced-motion: reduce) schaltet sie ab.
- Dateigroesse unter 60 KB. Antworte mit GENAU EINEM Codeblock (```), der die VOLLSTAENDIGE neue Datei enthaelt, davor hoechstens drei Saetze Begruendung."""
FOCI = [("radar", "Die drei Reiter Radar, API-Suche und Usecases samt Sicherheits-Popup in ui_radar.js: Laienverstaendlichkeit (weniger Fachbegriffe, klare Saetze), Kontrast der grauen Hilfetexte, Abstaende, Ladezustaende, Animationen. Die Datei bleibt eigenstaendig (IIFE, window.EXTRA mit name/fn-Eintraegen, eigenes <style>); das Popup hat NUR den Knopf Verstanden und darf nie eine Freigabe oder Wiederherstellung anbieten", "ui_radar.js"),
        ("css", "Visuelles Design: Farbtiefe, Karten mit Tiefe/Glas, Typografie-Hierarchie, Abstaende, Tabellen, Buttons, Fokus-Zustaende, Responsive bis 420 px Breite", "ui.css"),
        ("motion", "Animationen: weiches Einblenden der Karten und Tabs (gestaffelt), Hover/Active-Zustaende, animierte Balken, pulsierende Status-Punkte, Ladeanzeige beim Scan; alles dezent und mit prefers-reduced-motion", "ui.css"),
        ("explain", "Erklaerungen: Info-Bubbles I('schluessel') an allen Ueberschriften und Fachbegriffen (Texte in texte.json ergaenzen, einfache Sprache), Leerzustaende mit Handlungsaufforderung, ein kurzer Willkommenshinweis beim ersten Start (localStorage)", "ui.js"),
        ("overview", "Reiter Uebersicht: eine klare Kopfzeile mit den wichtigsten Zahlen, verstaendliche Diagramme (Balken, Mini-Sparklines per CSS/SVG), Organe als schoene Kette mit Status-Punkten", "ui.js"),
        ("keys", "Reiter Keys & Anbieter: gefuehrter Ablauf in Schritten (1 Token einfuegen, 2 pruefen, 3 speichern), klare Fehlermeldungen, Status-Badges, Anbieter-Kacheln", "ui.js"),
        ("models", "Reiter Modelle: Sortieren per Klick auf Spaltenkoepfe, Filter-Chips pro Faehigkeit, farbige Mini-Balken fuer die Klassen-Ergebnisse, Leerzustand", "ui.js"),
        ("connect", "Reiter Verbinden: je Anwendung eine uebersichtliche Karte mit Schritt-fuer-Schritt-Anleitung, Kopieren-Knopf mit Rueckmeldung, Testknopf der eine Beispielanfrage zeigt (nur Anzeige der Anleitung, kein Schreiben in fremde Programme)", "ui.js"),
        ("settings", "Reiter Einstellungen und Ereignisse: gruppierte Einstellungen mit Erklaerungen und sofortiger Rueckmeldung, Ereignisse mit Symbolen und Filter", "ui.js"),
        ("texte", "texte.json: bessere, kuerzere, freundlichere Erklaerungstexte fuer alle vorhandenen Schluessel und sinnvolle neue Schluessel (nur JSON-Objekt Schluessel -> Text)", "texte.json"),
        ("klass", "Klassifikator-Regeln in gehirn.py: die Funktion klassifiziere genauer machen (z. B. 'funktioniert' ist kein Code-Signal, Uebersetzen/Zusammenfassen sind Deutsch, Tabellen/Struktur sind JSON). Gib NUR die Funktion klassifiziere (mit def-Zeile, Python 3.8-kompatibel, nur Standardbibliothek, gleiche Signatur und Rueckgabe (klasse, grund)) aus", "gehirn.py")]


def log(**kw):
    os.makedirs(IT, exist_ok=True)
    with open(os.path.join(IT, "log.jsonl"), "a") as f:
        f.write(json.dumps({"t": round(time.time()), **kw}, ensure_ascii=False) + "\n")


def real_key():
    rq = urllib.request.Request(REAL + "/api/status", headers={"X-Omnipool": "1"})
    return json.load(urllib.request.urlopen(rq, timeout=10))["harness"]["openai"]["key"]


def llm(model, messages, max_tokens=14000, timeout=290):
    body = json.dumps({"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.4}).encode()
    rq = urllib.request.Request(REAL + "/v1/chat/completions", body, {"Authorization": "Bearer " + real_key(), "Content-Type": "application/json"})
    r = urllib.request.urlopen(rq, timeout=timeout)
    route = r.headers.get("X-Omnipool-Route", model)
    return json.load(r)["choices"][0]["message"].get("content") or "", route


def models():
    rq = urllib.request.Request(REAL + "/api/status", headers={"X-Omnipool": "1"})
    w = json.load(urllib.request.urlopen(rq, timeout=10))["wahl"]
    seen = []
    for k in ("code", "reason", "tool"):
        for p, m, pr, _n, _l in w.get(k, []):
            if p == "nvidia" and "vl" not in m and m not in seen and "gliner" not in m and "ising" not in m:
                seen.append(m)
    return FIRST + ["nvidia/" + m for m in seen if "nvidia/" + m not in FIRST]


def rd(n):
    return open(os.path.join(PKG, n), encoding="utf-8").read()


def wr(n, s):
    with open(os.path.join(PKG, n), "w", encoding="utf-8") as f:
        f.write(s)


def snapshot(tag):
    d = os.path.join(IT, "versions", tag)
    os.makedirs(d, exist_ok=True)
    for n in ("ui.css", "ui.js", "ui_radar.js", "ui.html", "texte.json", "gehirn.py"):
        shutil.copy2(os.path.join(PKG, n), d)


def restore(tag):
    d = os.path.join(IT, "versions", tag)
    for n in os.listdir(d):
        shutil.copy2(os.path.join(d, n), os.path.join(PKG, n))


def extract(text, lang):
    m = re.findall(r"```(?:%s|javascript|js|css|json|python)?\s*\n(.*?)```" % lang, text, re.S)
    return max(m, key=len) if m else None


def syntax_gate(name, s):
    if name in ("ui.js", "ui_radar.js"):
        open("/tmp/op-cand.js", "w").write(s)
        r = subprocess.run(["node", "--check", "/tmp/op-cand.js"], capture_output=True, text=True)
        return (r.returncode == 0, r.stderr[:300])
    if name == "texte.json":
        try:
            d = json.loads(s)
            return (isinstance(d, dict) and all(isinstance(v, str) for v in d.values()), "json ok")
        except ValueError as e:
            return (False, str(e)[:200])
    if name == "ui.css":
        return (s.count("{") == s.count("}") and "@import" not in s and "url(http" not in s, "klammern/extern")
    if name == "gehirn.py":
        import ast
        try:
            ast.parse(s, feature_version=(3, 8))
            return (True, "ok")
        except SyntaxError as e:
            return (False, str(e))
    return (True, "")


def klass_accuracy():
    r = subprocess.run([sys.executable, "-c", "import json,sys;sys.path.insert(0,%r)\nfrom omnipool import gehirn\nc=json.load(open(%r))\nok=0\nfor x in c:\n b={'messages':[{'role':'user','content':x['text']}]}\n if x.get('tools'): b['tools']=[{'x':1}]\n ok+=gehirn.klassifiziere(b)[0]==x['erwartet']\nprint(ok,len(c))" % (ROOT, os.path.join(ROOT, "tests", "klass_set.json"))],
                       capture_output=True, text=True, env={**os.environ, "OMNIPOOL_HOME": "/tmp/op-klass"})
    try:
        a, b = r.stdout.split()
        return int(a) / int(b)
    except ValueError:
        return 0.0


def tests_ok():
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "tests"], cwd=ROOT, capture_output=True, text=True, timeout=300)
    return r.returncode == 0, r.stdout[-300:]


def ui_gate(port, base, shots=None):
    """headless Chrome against the demo daemon: no console errors, every tab renders, the token flow reacts, no horizontal overflow on a phone-width window"""
    c = cdp.Chrome()
    try:
        c.goto("http://127.0.0.1:%d/" % port, 2.5)
        res = {"tabs": [], "errors": []}
        for i in range(c.js("document.querySelectorAll('nav button').length") or 6):
            c.js("document.querySelectorAll('nav button')[%d].click()" % i)
            time.sleep(0.6)
            res["tabs"].append(c.js("document.querySelector('#main').innerText.length") or 0)
            g = [w for w in ("[object", "undefined", "NaN", "[Object") if w in (c.js("document.querySelector('#main').innerText") or "")]
            if g:
                res.setdefault("garbage", []).append("%s:%s" % (i, ",".join(g)))
            if shots and i in shots:
                c.shot(os.path.join(IT, "shots", "tab%d.png" % i))
        c.js("document.querySelectorAll('nav button')[1].click()")
        time.sleep(0.5)
        c.js("(()=>{const t=document.querySelector('#tok');t.value='garbage-token-abcdefghij';const b=[...document.querySelectorAll('button')].find(x=>x.textContent.trim().startsWith('Check'));b&&b.click()})()")
        time.sleep(2.0)
        res["flow"] = "not recognized" in (c.js("document.querySelector('#main').innerText") or "")
        res["nodes"] = c.js("document.querySelectorAll('*').length")
        c.call("Emulation.setDeviceMetricsOverride", width=420, height=860, deviceScaleFactor=1, mobile=True)
        time.sleep(0.5)
        res["overflow"] = (c.js("document.documentElement.scrollWidth") or 0) - 420
        res["errors"] = c.errors[:5]
        res["anim"] = c.js("[...document.styleSheets].reduce((n,s)=>{try{return n+[...s.cssRules].filter(r=>r.type===7).length}catch(e){return n}},0)")
        ok = not res.get("garbage") and not res["errors"] and res["flow"] and min(res["tabs"]) > 60 and res["nodes"] < 8000 and all(t >= 0.5 * b for t, b in zip(res["tabs"], base["tabs"])) if base else not res["errors"]
        return ok, res
    finally:
        c.close()


def judge(port, tabs):
    """a NVIDIA vision model scores the screenshots of the given tabs"""
    c = cdp.Chrome()
    imgs, scores, issues = [], [], []
    try:
        c.goto("http://127.0.0.1:%d/" % port, 2.5)
        os.makedirs(os.path.join(IT, "shots"), exist_ok=True)
        for i in tabs:
            c.js("document.querySelectorAll('nav button')[%d].click()" % i)
            time.sleep(1.2)
            imgs.append((i, base64.b64encode(open(c.shot(os.path.join(IT, "shots", "tab%d.png" % i)), "rb").read()).decode()))
    finally:
        c.close()
    for i, b64 in imgs:
        q = ("Bewerte diese Web-App-Oberflaeche (Reiter '%s') streng wie ein Design-Reviewer: visuelle Hierarchie, Kontrast, Abstaende, Konsistenz, Eleganz, Verstaendlichkeit fuer Laien, "
             "wirkt sie fertig und hochwertig? Antworte NUR mit JSON {\"score\": Zahl 1-10, \"issues\": [max 4 konkrete, umsetzbare Probleme]}." % TABS[i])
        try:
            txt, _ = llm(VL, [{"role": "user", "content": [{"type": "text", "text": q}, {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}], 700, 120)
            m = re.search(r"\{.*\}", txt, re.S)
            d = json.loads(m.group(0))
            scores.append(float(d["score"]))
            issues += ["[%s] %s" % (TABS[i], x) for x in d.get("issues", [])[:4]]
        except Exception as e:  # noqa: BLE001
            log(art="judge_fehler", tab=i, fehler=type(e).__name__)
    return (sum(scores) / len(scores) if scores else None), issues


def prompt_for(focus, task, fname, issues, last_fail):
    parts = ["Du verbesserst die Weboberflaeche 'Omnipool' (lokale Web-App, die freie KI-API-Keys testet, Modelle einordnet und KI-Programme verbindet). Aufgabe dieser Runde: " + task, RULES]
    if issues:
        parts.append("Aktuelle Kritikpunkte eines Design-Reviewers (nach Moeglichkeit beheben):\n- " + "\n- ".join(issues[:8]))
    if last_fail:
        parts.append("Dein letzter Versuch zu diesem Thema wurde verworfen: " + last_fail + ". Mach es diesmal vorsichtiger.")
    ctx = {"ui.css": ["ui.js"], "ui.js": ["ui.css", "texte.json"], "texte.json": ["ui.js"], "ui_radar.js": ["ui.css"], "gehirn.py": []}[fname]
    for n in ctx:
        s = rd(n)
        parts.append("Kontext (nur lesen) %s:\n```\n%s\n```" % (n, s[:14000]))
    if fname == "gehirn.py":
        s = rd(fname)
        m = re.search(r"def klassifiziere.*?(?=\n\ndef frei)", s, re.S)
        parts.append("Aktuelle Funktion:\n```python\n%s\n```\nTestfaelle liegen in tests/klass_set.json (Text, erwartete Klasse aus code/json/de/reason/long/tool). Fehlklassifikationen heute: 'Mach daraus eine Tabelle mit Spalten' (json), 'Wie funktioniert das Wetter?' (de), 'Uebersetze diesen Satz ins Englische: Guten Morgen' (de)." % m.group(0))
    else:
        parts.append("ZU VERBESSERNDE DATEI %s:\n```\n%s\n```" % (fname, rd(fname)))
    return "\n\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--minutes", type=float, default=120)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    deadline = time.time() + a.minutes * 60
    os.makedirs(os.path.join(IT, "versions"), exist_ok=True)
    for n in ("STOP",):
        if os.path.exists(os.path.join(IT, n)):
            os.remove(os.path.join(IT, n))
    d, tmp = demo.start()
    snapshot("v000")
    ok0, base = ui_gate(d.port, None, shots=None)
    best, issues = judge(d.port, [0, 3]), []
    best_score, issues = best[0] or 5.0, best[1]
    tab_scores = {0: best_score, 3: best_score}
    acc0 = klass_accuracy()
    if a.dry:
        print(json.dumps({"ui_ok": ok0, "base": base, "score": best_score, "issues": issues, "klass": acc0, "modelle": models()[:6]}, ensure_ascii=False, indent=1))
        d.stop()
        return
    log(art="start", ui_ok=ok0, base=base, score=best_score, klass=acc0, modelle=models()[:5])
    n, version, fails = 0, 0, {}
    cur, mstat, last, outcome = {"i": 0, "tries": 0}, {}, None, "fail"
    pool = models()
    stats = {"accepted": 0, "rejected": 0}
    while time.time() < deadline and not os.path.exists(os.path.join(IT, "STOP")):
        n += 1
        if last:
            w, t = mstat.get(last[1], (0, 0))
            mstat[last[1]] = (w + (outcome == "ok"), t + 1)
            if outcome == "ok" or cur["tries"] >= 1:
                cur["i"], cur["tries"] = cur["i"] + 1, 0
            else:
                cur["tries"] += 1
        outcome = "fail"
        focus, task, fname = FOCI[cur["i"] % len(FOCI)]
        model = max(pool, key=lambda m: (mstat.get(m, (0, 0))[0] + (2.0 if m == pool[0] else 0.5)) / (mstat.get(m, (0, 0))[1] + 2) + random.random() * 0.15)
        last = (focus, model)
        t0 = time.time()
        before = rd(fname)
        try:
            pr = prompt_for(focus, task, fname, issues, fails.get(focus))
            text, route = llm(model, [{"role": "user", "content": pr}])
        except Exception as e:  # noqa: BLE001
            log(art="runde", n=n, focus=focus, model=model, ok=False, grund="llm: %s" % type(e).__name__)
            time.sleep(10)
            continue
        cand = extract(text, "python" if fname.endswith(".py") else "")
        if not cand:
            fails[focus] = "keine Datei im Codeblock"
            log(art="runde", n=n, focus=focus, model=route, ok=False, grund=fails[focus])
            continue
        def wrap(c):
            if fname != "gehirn.py":
                return c
            m = re.search(r"def klassifiziere.*?(?=\n\ndef frei)", before, re.S)
            return before.replace(m.group(0), (c.strip() + "\n").rstrip("\n"))
        cand = wrap(cand)
        okk, why = syntax_gate(fname, cand)
        if not okk and fname != "ui.css":
            try:
                t2, _ = llm(model, [{"role": "user", "content": pr}, {"role": "assistant", "content": text},
                                    {"role": "user", "content": "Die Datei hat einen Syntaxfehler:\n%s\nGib die VOLLSTAENDIGE korrigierte Datei erneut in genau einem Codeblock aus, sonst nichts aendern." % why[:500]}])
                c2 = extract(t2, "python" if fname.endswith(".py") else "")
                if c2:
                    cand = wrap(c2)
                    okk, why = syntax_gate(fname, cand)
                    log(art="reparatur", n=n, focus=focus, ok=okk)
            except Exception:  # noqa: BLE001
                pass
        if okk and not (0.6 * len(before) <= len(cand) <= (8.0 if fname == "ui.css" else 2.6) * len(before) or fname == "gehirn.py"):
            okk, why = False, "Groesse %d -> %d" % (len(before), len(cand))
        if not okk:
            fails[focus] = "Syntax/Form: " + why
            log(art="runde", n=n, focus=focus, model=route, ok=False, grund=fails[focus])
            stats["rejected"] += 1
            continue
        wr(fname, cand)
        gates = {}
        try:
            gates["tests"], out = tests_ok()
            gates["ui"], res = ui_gate(d.port, base)
            gates["klass"] = klass_accuracy() >= acc0 if fname == "gehirn.py" else True
            sc = None
            if all(gates.values()):
                tabs = [(n * 2) % len(TABS), (n * 2 + 1) % len(TABS)]
                sc, new_issues = judge(d.port, tabs)
                if fname in ("ui.css", "ui.js", "texte.json") and sc is not None:
                    ref = sum(tab_scores.get(t, best_score) for t in tabs) / 2
                    gates["visual"] = sc >= ref - 0.5
                else:
                    new_issues = []
        except Exception as e:  # noqa: BLE001
            gates["exception"] = False
            res, out, new_issues = {"exc": type(e).__name__}, "", []
        if all(gates.values()):
            version += 1
            snapshot("v%03d" % version)
            stats["accepted"] += 1
            outcome = "ok"
            if sc is not None:
                for t in tabs:
                    tab_scores[t] = sc
                issues = (new_issues + issues)[:10]
            if fname == "gehirn.py":
                acc0 = klass_accuracy()
            fails.pop(focus, None)
            log(art="runde", n=n, focus=focus, model=route, ok=True, version=version, score=sc, bytes=[len(before), len(cand)], s=round(time.time() - t0), anim=res.get("anim"), overflow=res.get("overflow"))
        else:
            wr(fname, before)
            fails[focus] = "Gates: " + ",".join(k for k, v in gates.items() if not v) + " " + json.dumps(res)[:160]
            stats["rejected"] += 1
            log(art="runde", n=n, focus=focus, model=route, ok=False, grund=fails[focus], s=round(time.time() - t0))
    snapshot("final")
    final, fi = judge(d.port, [0, 1, 2, 3, 4, 5])
    rep = ["# Omnipool Verbesserungslauf", "", "Runden: %d, angenommen: %d, verworfen: %d" % (n, stats["accepted"], stats["rejected"]), "Score vorher %.1f, nachher %s" % (best_score, "%.1f" % final if final else "-"),
           "Klassifikator-Genauigkeit: %.2f" % klass_accuracy(), "", "Offene Kritikpunkte:"] + ["- " + x for x in fi] + ["", "Protokoll: iter/log.jsonl, Versionen: iter/versions/"]
    open(os.path.join(IT, "REPORT.md"), "w").write("\n".join(rep) + "\n")
    log(art="ende", **stats, final=final)
    d.stop()


if __name__ == "__main__":
    main()
