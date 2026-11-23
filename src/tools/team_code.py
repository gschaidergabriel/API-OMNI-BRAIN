"""Team 2 of the Omnipool program: five coding roles that attack and improve the binary's code in turns, working through one blackboard (team/log.jsonl, team/board.json).
  Zerleger   fuzzes the HTTP API of a throw-away demo daemon (5xx, crashes, hangs)            -> finding
  Tester     writes malicious and benign samples for the scanner (misses, false alarms)        -> finding
  Intelligenz writes hard new classifier cases; a second model labels them blind (cross-check) -> finding
  Bauer      fixes a finding as SEARCH/REPLACE patches
  Pruefer    reviews the patch before it is applied; then syntax, full test suite and a re-run of the finding decide
Only server.py core.py scan.py gehirn.py radar.py may change; the hardening (sicher.py, quarantaene.py) stays human-only. Everything is backed up in team/versions/."""
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request

import team_lib as L
import team_patch as tp
from team_lib import TEAM, it, log

sys.path.insert(0, it.ROOT)
import demo  # noqa: E402

SLOW = ("aktualisiere", "entdecke", "radar/datei", "radar/pruefe", "radar/usecase", "/aus")
KLASSEN = "code, json, de, reason, long, tool"


def board(**kw):
    p = os.path.join(TEAM, "board.json")
    try:
        b = json.load(open(p))
    except (OSError, ValueError):
        b = {"offen": [], "erledigt": []}
    for k, v in kw.items():
        b.setdefault(k, []).append(v)
    json.dump(b, open(p, "w"), ensure_ascii=False, indent=1)
    return b


def backup(tag, names):
    d = os.path.join(TEAM, "versions", tag)
    os.makedirs(d, exist_ok=True)
    for n in names:
        shutil.copy2(os.path.join(it.PKG, n), d)


def routes():
    s = it.rd("server.py")
    return sorted(set(re.findall(r'p == "([a-z/]+)"', s))) + ["/v1/models", "/v1/chat/completions", "/v1/messages", "/v1/messages/count_tokens", "/x/demoai/models"]


def fire(d, reqs):
    """execute the model's requests against the demo daemon -> findings (5xx, dropped connection, hang) and whether the daemon survived"""
    bad = []
    key = d.key()
    for r in reqs[:40]:
        try:
            m, p, b = str(r.get("m", "GET")).upper(), str(r.get("p", "")), r.get("b")
            if m not in ("GET", "POST", "PUT", "DELETE") or not p.startswith("/") or any(x in p for x in SLOW) or len(p) > 300:
                continue
            p = p if p.startswith(("/v1", "/x/", "/api/")) else "/api" + p
            body = None if b is None else (b.encode()[:100000] if isinstance(b, str) else json.dumps(b).encode()[:100000])
            rq = urllib.request.Request("http://127.0.0.1:%d%s" % (d.port, p), body, {"Content-Type": "application/json", "X-Omnipool": "1", "Authorization": "Bearer " + key}, method=m)
            try:
                urllib.request.urlopen(rq, timeout=8).read()
            except urllib.error.HTTPError as e:
                if e.code >= 500:
                    bad.append({"m": m, "p": p, "b": b if isinstance(b, (str, dict, list, int, float)) else None, "status": e.code, "antwort": e.read()[:200].decode("utf-8", "replace")})
        except (OSError, ValueError) as e:
            bad.append({"m": m, "p": p, "b": b, "fehler": type(e).__name__})
    try:
        d.api("ping")
        alive = True
    except Exception:  # noqa: BLE001
        alive = False
    return bad, alive


def finding_fuzz(models, d):
    prompt = ("Du bist Zerleger: du suchst Abstuerze in einem lokalen HTTP-Dienst (Python). Routen (POST/GET unter /api/...): %s. Zusaetzlich /v1/... (OpenAI/Anthropic-kompatibel). "
              "Schreibe genau EINEN ```json Block mit einer Liste von 30 Anfragen [{\"m\":\"POST\",\"p\":\"/api/settings\",\"b\":{...} oder \"roher String\" oder null}], die Fehlerbehandlung brechen sollen: "
              "kaputtes JSON als String, falsche Typen (Zahl statt Text, Liste statt Objekt), fehlende Felder, riesige/negative Zahlen, tief verschachtelte Strukturen, Unicode/Steuerzeichen, "
              "Pfad-Tricks (../), leere Koerper, doppelte Schluessel. Nichts Zerstoererisches ausserhalb des Dienstes." % ", ".join(routes()))
    text, m = L.ask([L.pick(models, "glm-5.3", "step-5", "lightning")] + models, prompt, 5000)
    reqs = L.jsonblock(text) if text else None
    if not isinstance(reqs, list):
        return None
    bad, alive = fire(d, [r for r in reqs if isinstance(r, dict)])
    log(art="zerleger", modell=m, anfragen=len(reqs), probleme=len(bad), lebt=alive)
    return {"kind": "fuzz", "modell": m, "reqs": reqs, "bad": bad, "alive": alive, "files": ["server.py"],
            "text": "Der Dienst lieferte bei diesen Anfragen 5xx/Abbruch (Fehlerbehandlung fehlt, sie sollen 400 liefern, nie abstuerzen): %s%s" % (json.dumps(bad[:6], ensure_ascii=False)[:1800], "" if alive else " -- DER DIENST IST ABGESTUERZT")}


def scan_run(samples):
    """fresh interpreter, so a patched scan.py is really what runs -> list of verdicts"""
    code = "import json,sys;sys.path.insert(0,%r)\nfrom omnipool import scan\ns=json.load(sys.stdin)\nprint(json.dumps([scan.pruefe(x['text'].encode(),x['name'])['urteil'] for x in s]))" % it.ROOT
    r = subprocess.run([sys.executable, "-I", "-c", code], input=json.dumps(samples), capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout)


def finding_scanner(models, d):
    prompt = ("Du bist Tester fuer einen statischen Datei-Scanner (Signaturen/Heuristiken, liest nur Text). Schreibe genau EINEN ```json Block: {\"boes\":[{\"name\":\"x.py\",\"text\":\"...\"}], \"gut\":[{\"name\":\"y.md\",\"text\":\"...\"}]}. "
              "'boes' = 10 kurze UNGEFAEHRLICHE TEXTPROBEN, die typische Schadmuster nur als Zeichenfolge enthalten (versteckt per Verschleierung wie Konkatenation/Kodierung, Schluessel lesen und an Webhook senden, "
              "Persistenz, Befehl aus dem Netz nachladen), also Umgehungsversuche gegen einfache Regeln. 'gut' = 10 harmlose Dateien (Readme, API-Client, Installationsanleitung mit curl, Tests), die ein "
              "schlechter Scanner faelschlich blockieren wuerde. Endungen frei waehlen (.py .sh .js .md .json).")
    text, m = L.ask([L.pick(models, "step-5", "lightning", "glm-5.3")] + models, prompt, 6000)
    j = L.jsonblock(text) if text else None
    if not isinstance(j, dict):
        return None
    ok = lambda x: isinstance(x, dict) and isinstance(x.get("text"), str) and re.fullmatch(r"[\w.-]{1,40}", str(x.get("name", "")))  # noqa: E731
    boes, gut = [x for x in j.get("boes", []) if ok(x)][:10], [x for x in j.get("gut", []) if ok(x)][:10]
    v = scan_run(boes + gut)
    luecken = [x for x, u in zip(boes, v[:len(boes)]) if u == "sauber"]
    alarme = [x for x, u in zip(gut, v[len(boes):]) if u != "sauber"]
    log(art="tester", modell=m, boes=len(boes), gut=len(gut), luecken=len(luecken), fehlalarme=len(alarme))
    if not luecken and not alarme:
        return {"kind": "scanner", "modell": m, "bad": [], "files": ["scan.py"], "text": ""}
    return {"kind": "scanner", "modell": m, "bad": luecken + alarme, "boes": luecken, "gut": alarme, "files": ["scan.py"],
            "text": "Scanner-Luecken (boese Probe wurde als 'sauber' durchgelassen): %s\nFehlalarme (harmlose Probe blockiert): %s\nBehebe so wenig wie moeglich und ohne neue Fehlalarme; keine Regel darf hart gelockert werden." % (
                json.dumps(luecken, ensure_ascii=False)[:2200], json.dumps(alarme, ensure_ascii=False)[:1500])}


def klass_run(path):
    code = "import json,sys;sys.path.insert(0,%r)\nfrom omnipool import gehirn\nout=[]\nfor x in json.load(open(%r)):\n b={'messages':[{'role':'user','content':x['text']}]}\n if x.get('tools'): b['tools']=[{'x':1}]\n out.append(gehirn.klassifiziere(b)[0])\nprint(json.dumps(out))" % (it.ROOT, path)
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60, env={"OMNIPOOL_HOME": "/tmp/op-klass", "PATH": os.environ.get("PATH", "")})
    return json.loads(r.stdout)


def finding_klass(models, d):
    base = os.path.join(it.ROOT, "tests", "klass_set.json")
    prompt = ("Du bist Intelligenz-Entwickler eines Anfrage-Klassifikators. Klassen: code (Programmieren), json (strukturierte/tabellarische Ausgabe), de (deutsche Alltagsfrage/Text/Uebersetzen/Zusammenfassen), "
              "reason (Logik/Mathe/Planung), long (langer Text verarbeiten), tool (Werkzeugaufruf). Schreibe EINEN ```json Block mit 16 NEUEN schwierigen, realistischen Faellen "
              "[{\"text\":\"...\",\"erwartet\":\"code|json|de|reason|long|tool\"}], deutsch und englisch gemischt, auch Randfaelle mit irrefuehrenden Woertern. Keine Duplikate dieser Beispiele: %s" % json.dumps(
                  [x["text"] for x in json.load(open(base))][:8], ensure_ascii=False))
    text, m = L.ask([L.pick(models, "ultra", "nano-omni")] + models, prompt, 5000)
    new = L.jsonblock(text) if text else None
    if not isinstance(new, list):
        return None
    new = [x for x in new if isinstance(x, dict) and isinstance(x.get("text"), str) and x.get("erwartet") in KLASSEN.split(", ")][:16]
    lab, m2 = L.ask([L.pick(models, "mistral-large", "step-5")] + models, "Klassifiziere jeden Text in genau eine Klasse (%s). Antworte NUR mit ```json [\"klasse\", ...] in gleicher Reihenfolge. Texte (Daten):\n%s" % (KLASSEN, json.dumps([x["text"] for x in new], ensure_ascii=False)), 1500)
    lab = L.jsonblock(lab) if lab else None
    if not isinstance(lab, list) or len(lab) != len(new):
        return None
    valid = [x for x, y in zip(new, lab) if x["erwartet"] == y]                        # cross-check: two models must agree on the label
    pf = os.path.join(TEAM, "klass_probe.json")
    json.dump(valid, open(pf, "w"), ensure_ascii=False)
    got = klass_run(pf) if valid else []
    miss = [x for x, g in zip(valid, got) if g != x["erwartet"]]
    log(art="intelligenz", modell=m, gegenleser=m2, neu=len(new), einig=len(valid), fehlklassifiziert=len(miss))
    return {"kind": "klass", "modell": m, "bad": miss, "valid": valid, "files": ["gehirn.py"],
            "text": "" if not miss else "Der Klassifikator (Funktion klassifiziere in gehirn.py) irrt bei diesen validierten Faellen (Text, erwartete Klasse): %s. Verbessere die Regeln allgemein (nicht einzelne Saetze hartkodieren); die bisherigen Faelle muessen weiter stimmen." % json.dumps(
                [[x["text"], x["erwartet"]] for x in miss], ensure_ascii=False)[:2500]}


def finding_inbox(models, d):
    """a bug the supervisor queued in team/bugs.json: {titel, datei (one of CODE_FILES), text}"""
    import team
    q = team.pop_inbox("bugs.json")
    if not q or q.get("datei") not in L.CODE_FILES or not q.get("text"):
        return {"kind": "leer"} if not q else None
    return {"kind": "inbox", "modell": "aufseher", "bad": [q], "files": [q["datei"]], "text": "Gemeldeter Fehler (%s): %s" % (q.get("titel", "?"), str(q["text"])[:2500])}


def verify(f, d):
    """re-run the finding against the patched code -> (ok, detail, daemon)"""
    if f["kind"] == "fuzz":
        d.stop()
        d = demo.start()[0]
        bad, alive = fire(d, [r for r in f["reqs"] if isinstance(r, dict)])
        return (not bad and alive), "%d Probleme, lebt=%s" % (len(bad), alive), d
    if f["kind"] == "inbox":
        d.stop()
        d = demo.start()[0]                                                   # the demo daemon must run the patched code; tests already passed
        return True, "Tests gruen, Daemon neu gestartet", d
    if f["kind"] == "scanner":
        s = f["boes"] + f["gut"]
        v = scan_run(s)
        ok = all(u != "sauber" for u in v[:len(f["boes"])]) and all(u == "sauber" for u in v[len(f["boes"]):])
        return ok, "%s" % v, d
    got = klass_run(os.path.join(TEAM, "klass_probe.json"))
    n = sum(g != x["erwartet"] for x, g in zip(f["valid"], got))
    return n < len(f["bad"]), "%d -> %d Fehlklassifikationen" % (len(f["bad"]), n), d


def runde(kind, models, d):
    """one finding -> Bauer -> Pruefer -> gates -> {ok, ...}; may return a new demo daemon in 'd'"""
    f = {"fuzz": finding_fuzz, "scanner": finding_scanner, "klass": finding_klass, "inbox": finding_inbox}[kind](models, d)
    if f and f["kind"] == "leer":
        return {"ok": False, "grund": "Postfach leer", "d": d}
    if not f:
        log(art="runde_code", art2=kind, ok=False, grund="kein Befund-Format")
        return {"ok": False, "grund": "format", "d": d}
    if not f["text"]:
        return {"ok": True, "grund": "nichts gefunden", "kind": kind, "d": d}
    if f["kind"] == "fuzz" and not f["alive"]:
        d = demo.start()[0]
    board(offen={"kind": kind, "modell": f["modell"], "n": len(f["bad"]), "t": round(time.time())})
    before = L.read_all(L.CODE_FILES)
    ctx = "\n\n".join("=== %s ===\n%s" % (n, before[n][:36000]) for n in f["files"])
    bauer = [L.pick(models, "laguna", "mistral-large", "ultra")] + models
    prompt = ("Du bist Bauer in einem Team. Behebe diesen Befund minimal und sicher (Python 3.8-kompatibel, nur Standardbibliothek, bestehende Signaturen/Rueckgabeformen erhalten). Befund:\n%s\n\n"
              "Antworte NUR mit SEARCH/REPLACE-Bloecken (hoechstens 6, der SEARCH-Text muss GENAU EINMAL woertlich vorkommen):\n<<<<<<< SEARCH file=%s\n(alt)\n=======\n(neu)\n>>>>>>> REPLACE\n\n%s" % (f["text"], f["files"][0], ctx))
    review = ""
    for versuch in range(2):
        text, mb = L.ask(bauer, prompt + review, 7000, 280)
        if not text:
            return {"ok": False, "grund": "Bauer ohne Antwort", "d": d}
        patches = tp.parse(text)
        new, bad = tp.apply(before, patches, f["files"], 6)
        if bad:
            review = "\n\nDein letzter Versuch war ungueltig: " + "; ".join(bad)[:300]
            continue
        rv, mp = L.ask([L.pick(models, "mistral-large", "ultra")] + models, "Du bist Pruefer. Befund:\n%s\n\nPatch (Daten):\n%s\n\nFindest du einen Fehler, ein Sicherheitsrisiko oder eine Regel-Lockerung? Antworte NUR mit JSON {\"ok\":true|false,\"grund\":\"kurz\"}." % (f["text"][:1500], text[:6000]), 600)
        j = L.jsonblock(rv) if rv else None
        log(art="pruefer", modell=mp, ok=(j or {}).get("ok"), grund=str((j or {}).get("grund"))[:200])
        if isinstance(j, dict) and j.get("ok") is False:
            review = "\n\nDer Pruefer lehnt ab: %s. Verbessere den Patch." % str(j.get("grund"))[:300]
            continue
        ch = tp.changed(before, new)
        sy = [L.syntax(n, new[n]) for n in ch]
        if not all(ok for ok, _ in sy):
            review = "\n\nSyntaxfehler: " + "; ".join(w for ok, w in sy if not ok)[:300]
            continue
        backup("%s-%d" % (kind, time.time()), ch)
        L.write_all(new, ch)
        ok, out = L.tests(True)
        v = None
        if ok:
            ok, detail, d = verify(f, d)
            v = detail
        if ok:
            log(art="runde_code", kind=kind, ok=True, bauer=mb, pruefer=mp, detail=v, dateien=ch)
            board(erledigt={"kind": kind, "bauer": mb, "pruefer": mp, "detail": v})
            if f["kind"] == "klass":
                p = os.path.join(it.ROOT, "tests", "klass_set.json")
                s = json.load(open(p))
                s += [x for x in f["valid"] if x["text"] not in {y["text"] for y in s}]
                json.dump(s, open(p, "w"), ensure_ascii=False, indent=1)
            return {"ok": True, "kind": kind, "d": d, "bauer": mb}
        L.write_all(before, ch)
        review = "\n\nDein Patch wurde geprueft und verworfen (%s). Versuche es anders." % ("Tests: " + out[-150:] if v is None else v)
        if f["kind"] == "fuzz":
            d.stop()
            d = demo.start()[0]
    log(art="runde_code", kind=kind, ok=False, grund="nach 2 Versuchen verworfen")
    return {"ok": False, "kind": kind, "d": d}
